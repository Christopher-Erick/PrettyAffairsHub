from decimal import Decimal

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.cart.services import (
    add_to_cart,
    cart_totals,
    get_or_create_cart,
    remove_cart_item,
    update_cart_item,
)
from apps.discounts.models import Coupon
from apps.orders.services import DEFAULT_SHIPPING, FREE_SHIPPING_THRESHOLD


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
        add_to_cart(
            request,
            product_id=request.POST.get("product_id"),
            quantity=request.POST.get("quantity", 1),
            variant_id=request.POST.get("variant_id") or None,
        )
        messages.success(request, "Added to cart.")
    except Exception as exc:
        messages.error(request, str(exc))
    next_url = request.POST.get("next") or "cart:detail"
    if next_url == "cart:detail":
        return redirect("cart:detail")
    return redirect(next_url)


@require_POST
def cart_add_many(request):
    ids = request.POST.getlist("product_id")
    added = 0
    errors = []
    for product_id in ids:
        try:
            add_to_cart(request, product_id=product_id, quantity=1)
            added += 1
        except Exception as exc:
            errors.append(str(exc))
    if added:
        messages.success(request, f"Added {added} ritual piece{'s' if added != 1 else ''} to your cart.")
    for err in errors[:2]:
        messages.error(request, err)
    next_url = request.POST.get("next") or "cart:detail"
    if next_url == "cart:detail":
        return redirect("cart:detail")
    return redirect(next_url)


@require_POST
def cart_update(request, item_id):
    try:
        update_cart_item(request, item_id, request.POST.get("quantity", 1))
        messages.success(request, "Cart updated.")
    except Exception as exc:
        messages.error(request, str(exc))
    return redirect("cart:detail")


@require_POST
def cart_remove(request, item_id):
    remove_cart_item(request, item_id)
    messages.success(request, "Item removed.")
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
