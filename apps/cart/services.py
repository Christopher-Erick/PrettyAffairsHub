from decimal import Decimal

from django.db import transaction

from apps.catalog.models import Product, ProductVariant
from apps.cart.models import Cart, CartItem
from apps.cart.context_processors import refresh_cart_item_count


def _ensure_session(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        session_key = _ensure_session(request)
        guest = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
        if guest and guest.pk != cart.pk:
            _merge_carts(guest, cart)
            refresh_cart_item_count(request, cart)
        return cart

    session_key = _ensure_session(request)
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


def _merge_carts(source, target):
    for item in source.items.all():
        existing = target.items.filter(product=item.product, variant=item.variant).first()
        if existing:
            existing.quantity += item.quantity
            existing.save(update_fields=["quantity"])
        else:
            item.cart = target
            item.save(update_fields=["cart"])
    source.delete()


@transaction.atomic
def add_to_cart(request, product_id, quantity=1, variant_id=None):
    product = Product.objects.published().get(pk=product_id)
    variant = None
    if variant_id:
        variant = ProductVariant.objects.get(pk=variant_id, product=product, is_active=True)
        available = variant.stock
        unit_price = variant.price
    else:
        available = product.stock
        unit_price = product.price

    quantity = max(1, int(quantity))
    if available < quantity:
        raise ValueError("Not enough stock available.")

    cart = get_or_create_cart(request)
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        defaults={"quantity": quantity, "unit_price": unit_price},
    )
    if not created:
        new_qty = item.quantity + quantity
        if new_qty > available:
            raise ValueError("Not enough stock available.")
        item.quantity = new_qty
        item.unit_price = unit_price
        item.save(update_fields=["quantity", "unit_price"])
    refresh_cart_item_count(request, cart)
    return item


def update_cart_item(request, item_id, quantity):
    cart = get_or_create_cart(request)
    item = cart.items.select_related("product", "variant").get(pk=item_id)
    quantity = int(quantity)
    if quantity <= 0:
        item.delete()
        refresh_cart_item_count(request, cart)
        return None
    available = item.variant.stock if item.variant else item.product.stock
    if quantity > available:
        raise ValueError("Not enough stock available.")
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    refresh_cart_item_count(request, cart)
    return item


def remove_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    cart.items.filter(pk=item_id).delete()
    refresh_cart_item_count(request, cart)


def cart_totals(cart, discount_amount=Decimal("0"), shipping_amount=Decimal("0"), tax_rate=Decimal("0")):
    subtotal = cart.subtotal
    taxable = max(subtotal - discount_amount, Decimal("0"))
    tax_amount = (taxable * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
    total = taxable + shipping_amount + tax_amount
    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "shipping_amount": shipping_amount,
        "tax_amount": tax_amount,
        "total": total,
    }
