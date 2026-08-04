from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F

from apps.accounts.roles import is_store_admin
from apps.cart.services import cart_totals, get_or_create_cart
from apps.catalog.models import Product, ProductVariant
from apps.core.smart_cache import invalidate_catalog_cache
from apps.discounts.models import Coupon
from apps.orders.models import Order, OrderEvent, OrderItem


DEFAULT_SHIPPING = Decimal("300.00")
FREE_SHIPPING_THRESHOLD = Decimal("5000.00")
TAX_RATE = Decimal("0")  # configurable later
ORDER_CONFIRMATION_SESSION_KEY = "viewable_order_numbers"


def grant_order_confirmation_access(request, order_number: str) -> None:
    """Allow this browser session to open the confirmation page for order_number."""
    session = getattr(request, "session", None)
    if session is None:
        return
    viewed = list(session.get(ORDER_CONFIRMATION_SESSION_KEY, []))
    if order_number not in viewed:
        viewed.append(order_number)
        session[ORDER_CONFIRMATION_SESSION_KEY] = viewed[-30:]
        session.modified = True


def can_view_order_confirmation(request, order: Order) -> bool:
    """Confirmation shows PII — only the buyer (or store staff) may open it."""
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        if order.user_id and order.user_id == user.id:
            return True
        if is_store_admin(user):
            return True
    session = getattr(request, "session", None)
    if session is None:
        return False
    return order.order_number in (session.get(ORDER_CONFIRMATION_SESSION_KEY) or [])


@transaction.atomic
def create_order_from_cart(request, cleaned_data):
    cart = get_or_create_cart(request)
    items = list(cart.items.select_related("product", "variant"))
    if not items:
        raise ValueError("Your cart is empty.")

    product_ids = {item.product_id for item in items}
    variant_ids = {item.variant_id for item in items if item.variant_id}
    products = {
        p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
    }
    variants = {
        v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    }

    for item in items:
        available_obj = variants.get(item.variant_id) if item.variant_id else products[item.product_id]
        if item.quantity > available_obj.stock:
            raise ValueError(f"Insufficient stock for {item.product.name}.")

    subtotal = cart.subtotal
    discount_amount = Decimal("0")
    coupon_code = cleaned_data.get("coupon_code") or cart.coupon_code
    if coupon_code:
        coupon = (
            Coupon.objects.select_for_update()
            .filter(code__iexact=coupon_code)
            .first()
        )
        if coupon and coupon.is_valid(subtotal):
            discount_amount = coupon.calculate_discount(subtotal)
            Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)
        else:
            coupon_code = ""

    shipping_amount = (
        Decimal("0") if subtotal - discount_amount >= FREE_SHIPPING_THRESHOLD else DEFAULT_SHIPPING
    )
    totals = cart_totals(cart, discount_amount, shipping_amount, TAX_RATE)

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        email=cleaned_data["email"],
        phone=cleaned_data.get("phone", ""),
        channel=Order.CHANNEL_WEBSITE,
        shipping_name=cleaned_data["shipping_name"],
        shipping_line1=cleaned_data["shipping_line1"],
        shipping_line2=cleaned_data.get("shipping_line2", ""),
        shipping_city=cleaned_data["shipping_city"],
        shipping_county=cleaned_data.get("shipping_county", ""),
        shipping_postal_code=cleaned_data.get("shipping_postal_code", ""),
        shipping_country=cleaned_data.get("shipping_country", "Kenya"),
        notes=cleaned_data.get("notes", ""),
        is_gift=bool(cleaned_data.get("is_gift")),
        gift_note=(cleaned_data.get("gift_note") or "").strip() if cleaned_data.get("is_gift") else "",
        coupon_code=coupon_code or "",
        subtotal=totals["subtotal"],
        discount_amount=totals["discount_amount"],
        shipping_amount=totals["shipping_amount"],
        tax_amount=totals["tax_amount"],
        total=totals["total"],
        status=Order.STATUS_PENDING,
    )
    OrderEvent.objects.create(order=order, status=Order.STATUS_PENDING, note="Order placed")

    for item in items:
        available_obj = variants.get(item.variant_id) if item.variant_id else products[item.product_id]
        available_obj.stock = max(0, available_obj.stock - item.quantity)
        available_obj.save(update_fields=["stock"])
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            variant_name=item.variant.name if item.variant else "",
            sku=item.variant.sku if item.variant and item.variant.sku else item.product.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
        )

    cart.items.all().delete()
    cart.coupon_code = ""
    cart.save(update_fields=["coupon_code"])

    # Stock changed — drop stale "in stock" catalogue payloads.
    invalidate_catalog_cache(reason="order placed")
    send_order_confirmation(order)
    return order


def send_order_confirmation(order):
    subject = f"Order confirmed — {order.order_number}"
    lines = [
        f"Thank you for shopping with {settings.SITE_NAME}.",
        f"Order number: {order.order_number}",
        f"Total: {settings.SITE_CURRENCY_SYMBOL} {order.total}",
        "",
        "Items:",
    ]
    for item in order.items.all():
        lines.append(f"- {item.product_name} x{item.quantity}")
    send_mail(
        subject,
        "\n".join(lines),
        settings.DEFAULT_FROM_EMAIL,
        [order.email],
        fail_silently=True,
    )
