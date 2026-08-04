from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.cart.context_processors import refresh_cart_item_count
from apps.cart.services import (
    InsufficientStockError,
    add_to_cart,
    build_whatsapp_order_message,
    cart_totals,
    clear_cart,
    get_cart_if_exists,
    get_or_create_cart,
    remove_cart_item,
    update_cart_item,
)
from apps.core.http import is_same_origin_request, safe_redirect
from apps.core.ratelimit import rate_limit_exceeded
from apps.discounts.models import Coupon
from apps.orders.services import DEFAULT_SHIPPING, FREE_SHIPPING_THRESHOLD


def _wants_json(request):
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    accept = (request.headers.get("Accept") or "").lower()
    return "application/json" in accept


def _require_trusted_json(request):
    """CSRF is enforced by middleware; also require XHR + same-origin."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"ok": False, "message": "Invalid request."}, status=403)
    if not is_same_origin_request(request):
        return JsonResponse({"ok": False, "message": "Invalid request."}, status=403)
    return None


def _cart_count(request):
    return int(request.session.get("cart_item_count") or refresh_cart_item_count(request) or 0)


def cart_detail(request):
    cart = get_or_create_cart(request)
    discount = Decimal("0")
    if cart.coupon_code:
        coupon = Coupon.objects.filter(code__iexact=cart.coupon_code).first()
        if coupon:
            discount = coupon.calculate_discount(cart.subtotal)
    shipping = (
        Decimal("0")
        if cart.subtotal - discount >= FREE_SHIPPING_THRESHOLD
        else DEFAULT_SHIPPING
    )
    totals = cart_totals(cart, discount, shipping)
    toward_free = cart.subtotal - discount
    remaining = max(FREE_SHIPPING_THRESHOLD - toward_free, Decimal("0"))
    progress = min(100, int((toward_free / FREE_SHIPPING_THRESHOLD) * 100)) if FREE_SHIPPING_THRESHOLD else 100
    return render(
        request,
        "cart/cart.html",
        {
            "cart": cart,
            "items": cart.items.select_related("product", "variant").prefetch_related(
                "product__images"
            ),
            "totals": totals,
            "free_shipping_remaining": remaining,
            "free_shipping_progress": progress,
        },
    )


@require_POST
def cart_add(request):
    try:
        quantity = max(1, int(request.POST.get("quantity", 1) or 1))
    except (TypeError, ValueError):
        quantity = 1
    try:
        _item, added = add_to_cart(
            request,
            product_id=request.POST.get("product_id"),
            quantity=quantity,
            variant_id=request.POST.get("variant_id") or None,
        )
        if added == 1:
            msg = "Added 1 item to your cart."
        else:
            msg = f"Added {added} items to your cart."
        if _wants_json(request):
            return JsonResponse(
                {
                    "ok": True,
                    "message": msg,
                    "added": added,
                    "cart_count": _cart_count(request),
                    "level": "success",
                }
            )
        messages.success(request, msg)
    except InsufficientStockError as exc:
        if _wants_json(request):
            return JsonResponse(
                {
                    "ok": False,
                    "message": str(exc),
                    "available": exc.available,
                    "cart_count": _cart_count(request),
                    "level": "error",
                },
                status=400,
            )
        messages.error(request, str(exc), extra_tags="toast-fast")
    except Exception as exc:
        if _wants_json(request):
            return JsonResponse(
                {
                    "ok": False,
                    "message": str(exc),
                    "cart_count": _cart_count(request),
                    "level": "error",
                },
                status=400,
            )
        messages.error(request, str(exc), extra_tags="toast-fast")
    return safe_redirect(request, request.POST.get("next"), fallback="cart:detail")


@require_POST
def cart_add_many(request):
    ids = request.POST.getlist("product_id")
    added = 0
    errors = []
    for product_id in ids:
        try:
            add_to_cart(request, product_id=product_id, quantity=1)
            added += 1
        except InsufficientStockError as exc:
            errors.append(str(exc))
            if not _wants_json(request):
                messages.error(request, str(exc), extra_tags="toast-fast")
        except Exception as exc:
            errors.append(str(exc))
            if not _wants_json(request):
                messages.error(request, str(exc), extra_tags="toast-fast")
    if added == 1:
        msg = "Added 1 ritual piece to your cart."
    elif added > 1:
        msg = f"Added {added} ritual pieces to your cart."
    else:
        msg = errors[0] if errors else "Nothing was added."
    if _wants_json(request):
        return JsonResponse(
            {
                "ok": added > 0,
                "message": msg,
                "added": added,
                "errors": errors,
                "cart_count": _cart_count(request),
                "level": "success" if added else "error",
            },
            status=200 if added else 400,
        )
    if added == 1:
        messages.success(request, msg)
    elif added > 1:
        messages.success(request, msg)
    return safe_redirect(request, request.POST.get("next"), fallback="cart:detail")


@require_POST
def cart_update(request, item_id):
    try:
        update_cart_item(request, item_id, request.POST.get("quantity", 1))
        messages.success(request, "Cart totals updated.")
    except InsufficientStockError as exc:
        messages.error(request, str(exc), extra_tags="toast-fast")
    except Exception as exc:
        messages.error(request, str(exc), extra_tags="toast-fast")
    return redirect("cart:detail")


@require_POST
def cart_remove(request, item_id):
    remove_cart_item(request, item_id)
    messages.success(request, "Item removed from your cart.")
    return redirect("cart:detail")


@require_POST
def apply_coupon(request):
    cart = get_or_create_cart(request)
    code = request.POST.get("coupon_code", "").strip()
    coupon = Coupon.objects.filter(code__iexact=code).first()
    if coupon and coupon.is_valid(cart.subtotal):
        cart.coupon_code = coupon.code
        cart.save(update_fields=["coupon_code"])
        messages.success(request, f"Coupon {coupon.code} applied.")
    else:
        cart.coupon_code = ""
        cart.save(update_fields=["coupon_code"])
        messages.error(request, "Invalid or expired coupon.")
    return redirect("cart:detail")


@require_POST
def cart_order_preview(request):
    """CSRF-protected JSON draft for the Order button (never creates a cart)."""
    denied = _require_trusted_json(request)
    if denied:
        return denied
    if rate_limit_exceeded(request, scope="cart_order_preview", limit=30, window_seconds=300):
        return JsonResponse(
            {"ok": False, "message": "Too many requests. Please wait a moment."},
            status=429,
        )

    cart = get_cart_if_exists(request)
    if cart is None:
        message = "Hi Pretty Affairs Hub — I'd like to place an order."
        count = 0
        total = Decimal("0")
        lead_id = None
    else:
        message, count, total = build_whatsapp_order_message(
            cart, currency_symbol=settings.SITE_CURRENCY_SYMBOL
        )
        lead_id = None
        if count > 0:
            from apps.orders.whatsapp_leads import capture_whatsapp_lead

            lead = capture_whatsapp_lead(request, cart, message=message)
            lead_id = lead.pk if lead else None
    return JsonResponse(
        {
            "ok": True,
            "message": message,
            "count": count,
            "total": str(total),
            "cart_count": _cart_count(request),
            "has_items": count > 0,
            "lead_id": lead_id,
        }
    )


@require_POST
def cart_clear(request):
    """Clear the caller's cart only — CSRF + same-origin XHR required."""
    denied = _require_trusted_json(request)
    if denied:
        return denied
    if rate_limit_exceeded(request, scope="cart_clear", limit=20, window_seconds=300):
        return JsonResponse(
            {"ok": False, "message": "Too many requests. Please wait a moment."},
            status=429,
        )

    clear_cart(request)
    return JsonResponse(
        {
            "ok": True,
            "message": "Cart cleared.",
            "cart_count": 0,
            "level": "success",
        }
    )
