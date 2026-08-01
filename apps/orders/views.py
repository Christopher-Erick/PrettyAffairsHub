from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.roles import is_store_admin
from apps.cart.services import cart_totals, get_or_create_cart
from apps.discounts.models import Coupon
from apps.orders.forms import CheckoutForm, KENYA_CITIES
from apps.orders.models import Order
from apps.orders.services import (
    DEFAULT_SHIPPING,
    FREE_SHIPPING_THRESHOLD,
    can_view_order_confirmation,
    create_order_from_cart,
    grant_order_confirmation_access,
)


def _checkout_shipping_name(user):
    """Customer-facing delivery name — never leak staff usernames like 'admin'."""
    full_name = (user.get_full_name() or "").strip()
    if full_name:
        return full_name
    if is_store_admin(user):
        return ""
    username = (user.username or "").strip()
    if username.lower() in {"admin", "administrator", "root", "staff", "superuser"}:
        return ""
    return username


def checkout(request):
    cart = get_or_create_cart(request)
    items = cart.items.select_related("product", "variant")
    if not items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("cart:detail")

    initial = {"shipping_city": "Nairobi"}
    staff_shopping = False
    if request.user.is_authenticated:
        staff_shopping = is_store_admin(request.user)
        # Staff accounts keep store emails private from the delivery form autofill.
        if not staff_shopping:
            initial["email"] = request.user.email
        initial["shipping_name"] = _checkout_shipping_name(request.user)
        default_address = request.user.addresses.filter(is_default=True).first()
        if default_address:
            known_cities = {c[0] for c in KENYA_CITIES}
            city = default_address.city if default_address.city in known_cities else "Other"
            initial.update(
                {
                    "phone": default_address.phone,
                    "shipping_name": default_address.full_name,
                    "shipping_line1": default_address.line1,
                    "shipping_line2": default_address.line2,
                    "shipping_city": city,
                    "shipping_county": default_address.county,
                    "shipping_postal_code": default_address.postal_code,
                    "shipping_country": default_address.country or "Kenya",
                }
            )

    form = CheckoutForm(request.POST or None, initial=initial)
    discount = Decimal("0")
    code = cart.coupon_code
    if request.method == "POST" and form.is_valid():
        try:
            order = create_order_from_cart(request, form.cleaned_data)
            grant_order_confirmation_access(request, order.order_number)
            messages.success(request, f"Order {order.order_number} placed successfully.")
            return redirect("orders:confirmation", order_number=order.order_number)
        except ValueError as exc:
            messages.error(request, str(exc))
    if code:
        coupon = Coupon.objects.filter(code__iexact=code).first()
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
    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "cart": cart,
            "items": items.prefetch_related("product__images"),
            "totals": totals,
            "free_shipping_remaining": remaining,
            "staff_shopping": staff_shopping,
        },
    )


def order_confirmation(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not can_view_order_confirmation(request, order):
        messages.error(request, "You cannot view that order.")
        return redirect("orders:track")
    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "orders/history.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, "orders/detail.html", {"order": order})


def track_order(request):
    order = None
    error = ""
    if request.method == "POST":
        number = request.POST.get("order_number", "").strip()
        email = request.POST.get("email", "").strip()
        order = Order.objects.filter(order_number__iexact=number, email__iexact=email).first()
        if order:
            grant_order_confirmation_access(request, order.order_number)
        else:
            error = "No order found with that number and email."
    return render(request, "orders/track.html", {"order": order, "error": error})
