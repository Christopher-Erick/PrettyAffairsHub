"""WhatsApp order leads — DB-backed queue until manager triage.

Pending carts are stored as WhatsAppLead(status=pending) so they survive
deploys and multi-worker hosts. Confirmed sales become Orders. True enquiries
stay as WhatsAppLead(status=true_enquiry). False alarms are deleted.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant
from apps.core.smart_cache import invalidate_catalog_cache
from apps.orders.models import Order, OrderEvent, OrderItem, WhatsAppLead

DEDUPE_WINDOW = timedelta(minutes=30)


def _fingerprint_for_items(items: list[dict]) -> str:
    normalized = [
        {
            "p": int(item.get("product_id") or 0),
            "v": int(item.get("variant_id") or 0),
            "q": int(item.get("quantity") or 0),
        }
        for item in items
    ]
    normalized.sort(key=lambda row: (row["p"], row["v"]))
    raw = json.dumps(normalized, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cart_items_snapshot(cart) -> tuple[list[dict], int, Decimal]:
    rows = []
    total = Decimal("0")
    count = 0
    for item in cart.items.select_related("product", "variant"):
        line_total = item.unit_price * item.quantity
        total += line_total
        count += item.quantity
        rows.append(
            {
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "product_name": item.product.name,
                "variant_name": item.variant.name if item.variant_id else "",
                "sku": (
                    item.variant.sku
                    if item.variant_id and item.variant.sku
                    else item.product.sku
                ),
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(line_total),
            }
        )
    return rows, count, total


def _user_or_session_q(user, session_key: str):
    q = Q()
    if user is not None:
        q |= Q(user=user)
    if session_key:
        q |= Q(session_key=session_key)
    if not q:
        q = Q(pk__in=[])
    return q


def pending_count() -> int:
    return WhatsAppLead.objects.filter(status=WhatsAppLead.STATUS_PENDING).count()


def capture_whatsapp_lead(request, cart, *, message: str = "") -> WhatsAppLead | None:
    """Save a pending lead in the database for manager review."""
    if cart is None:
        return None
    items, count, subtotal = cart_items_snapshot(cart)
    if not items:
        return None

    fingerprint = _fingerprint_for_items(items)
    session_key = ""
    session = getattr(request, "session", None)
    if session is not None:
        if not session.session_key:
            session.save()
        session_key = session.session_key or ""

    user = request.user if getattr(request.user, "is_authenticated", False) else None
    cutoff = timezone.now() - DEDUPE_WINDOW
    existing = (
        WhatsAppLead.objects.filter(
            status=WhatsAppLead.STATUS_PENDING,
            fingerprint=fingerprint,
            created_at__gte=cutoff,
        )
        .filter(_user_or_session_q(user, session_key))
        .order_by("-created_at")
        .first()
    )
    if existing:
        existing.items_json = items
        existing.item_count = count
        existing.subtotal = subtotal
        existing.message_preview = (message or "")[:4000]
        existing.save(
            update_fields=[
                "items_json",
                "item_count",
                "subtotal",
                "message_preview",
                "updated_at",
            ]
        )
        return existing

    return WhatsAppLead.objects.create(
        user=user,
        session_key=session_key,
        fingerprint=fingerprint,
        items_json=items,
        item_count=count,
        subtotal=subtotal,
        message_preview=(message or "")[:4000],
        status=WhatsAppLead.STATUS_PENDING,
    )


def mark_true_enquiry(lead: WhatsAppLead, *, manager, note: str = "") -> WhatsAppLead:
    lead.status = WhatsAppLead.STATUS_TRUE_ENQUIRY
    lead.manager_note = (note or "").strip()
    lead.handled_by = manager
    lead.handled_at = timezone.now()
    lead.save(
        update_fields=["status", "manager_note", "handled_by", "handled_at", "updated_at"]
    )
    return lead


def delete_false_alarm(lead: WhatsAppLead) -> None:
    """False alarm — delete the pending row; nothing else is kept."""
    lead.delete()


@transaction.atomic
def confirm_whatsapp_sale(lead: WhatsAppLead, *, manager, cleaned_data: dict) -> Order:
    """Confirm sale → Order in DB, then remove the lead."""
    items = list(lead.items_json or [])
    if not items:
        raise ValueError("This WhatsApp lead has no products.")

    product_ids = {int(row["product_id"]) for row in items if row.get("product_id")}
    variant_ids = {int(row["variant_id"]) for row in items if row.get("variant_id")}
    products = {
        p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
    }
    variants = {
        v.id: v
        for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    }

    for row in items:
        qty = int(row.get("quantity") or 0)
        if qty < 1:
            raise ValueError("Invalid quantity on a lead line.")
        variant_id = int(row["variant_id"]) if row.get("variant_id") else None
        product_id = int(row["product_id"])
        stock_obj = variants.get(variant_id) if variant_id else products.get(product_id)
        if stock_obj is None:
            raise ValueError(f"Missing product for “{row.get('product_name') or product_id}”.")
        if qty > stock_obj.stock:
            raise ValueError(
                f"Insufficient stock for {row.get('product_name') or stock_obj} "
                f"(need {qty}, have {stock_obj.stock})."
            )

    subtotal = sum(
        (Decimal(str(row.get("line_total") or 0)) for row in items),
        Decimal("0"),
    )
    shipping_amount = Decimal(str(cleaned_data.get("shipping_amount") or 0))
    order = Order.objects.create(
        user_id=lead.user_id,
        email=cleaned_data["email"],
        phone=cleaned_data.get("phone", ""),
        channel=Order.CHANNEL_WHATSAPP,
        shipping_name=cleaned_data["shipping_name"],
        shipping_line1=cleaned_data.get("shipping_line1") or "WhatsApp order",
        shipping_line2=cleaned_data.get("shipping_line2", ""),
        shipping_city=cleaned_data.get("shipping_city") or "Nairobi",
        shipping_county=cleaned_data.get("shipping_county", ""),
        shipping_postal_code=cleaned_data.get("shipping_postal_code", ""),
        shipping_country=cleaned_data.get("shipping_country") or "Kenya",
        notes=(cleaned_data.get("notes") or "").strip()
        or f"Confirmed from WhatsApp lead #{lead.pk}",
        subtotal=subtotal,
        discount_amount=Decimal("0"),
        shipping_amount=shipping_amount,
        tax_amount=Decimal("0"),
        total=subtotal + shipping_amount,
        status=cleaned_data.get("status") or Order.STATUS_PAID,
    )
    OrderEvent.objects.create(
        order=order,
        status=order.status,
        note=f"WhatsApp sale confirmed by {manager.get_username()}",
    )

    for row in items:
        qty = int(row["quantity"])
        variant_id = int(row["variant_id"]) if row.get("variant_id") else None
        product_id = int(row["product_id"])
        stock_obj = variants.get(variant_id) if variant_id else products[product_id]
        stock_obj.stock = max(0, stock_obj.stock - qty)
        stock_obj.save(update_fields=["stock"])
        unit_price = Decimal(str(row.get("unit_price") or 0))
        OrderItem.objects.create(
            order=order,
            product_id=product_id,
            product_name=row.get("product_name") or "",
            variant_name=row.get("variant_name") or "",
            sku=row.get("sku") or "",
            quantity=qty,
            unit_price=unit_price,
            line_total=Decimal(str(row.get("line_total") or unit_price * qty)),
        )

    lead_id = lead.pk
    lead.delete()
    invalidate_catalog_cache(reason=f"whatsapp sale lead={lead_id}")
    return order
