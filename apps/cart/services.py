from decimal import Decimal

from django.db import transaction

from apps.catalog.models import Product, ProductVariant
from apps.cart.models import Cart, CartItem
from apps.cart.context_processors import refresh_cart_item_count


class InsufficientStockError(ValueError):
    """Raised when requested qty exceeds remaining stock."""

    def __init__(self, available: int, product_name: str = ""):
        self.available = max(0, int(available))
        self.product_name = product_name or "This item"
        if self.available <= 0:
            message = f"{self.product_name} is out of stock."
        elif self.available == 1:
            message = f"Only 1 left of {self.product_name} — reduce your quantity."
        else:
            message = (
                f"Only {self.available} left of {self.product_name} — "
                f"you can’t add more than that."
            )
        super().__init__(message)


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
    for item in source.items.select_related("product", "variant"):
        available = _stock_for(item.product, item.variant)
        existing = target.items.filter(product=item.product, variant=item.variant).first()
        if existing:
            merged = min(existing.quantity + item.quantity, max(available, 0))
            if merged <= 0:
                existing.delete()
            else:
                existing.quantity = merged
                existing.save(update_fields=["quantity"])
            item.delete()
        else:
            if available <= 0:
                item.delete()
                continue
            item.quantity = min(item.quantity, available)
            item.cart = target
            item.save(update_fields=["cart", "quantity"])
    source.delete()


def _stock_for(product, variant):
    if variant is not None:
        return int(variant.stock)
    return int(product.stock)


@transaction.atomic
def add_to_cart(request, product_id, quantity=1, variant_id=None):
    product = Product.objects.published().get(pk=product_id)
    variant = None
    if variant_id:
        variant = ProductVariant.objects.get(pk=variant_id, product=product, is_active=True)
        unit_price = variant.price
    else:
        unit_price = product.price

    quantity = max(1, int(quantity))
    available = _stock_for(product, variant)
    if available < quantity:
        raise InsufficientStockError(available, product.name)

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
            raise InsufficientStockError(available, product.name)
        item.quantity = new_qty
        item.unit_price = unit_price
        item.save(update_fields=["quantity", "unit_price"])
    refresh_cart_item_count(request, cart)
    return item, quantity


def update_cart_item(request, item_id, quantity):
    cart = get_or_create_cart(request)
    item = cart.items.select_related("product", "variant").get(pk=item_id)
    quantity = int(quantity)
    if quantity <= 0:
        item.delete()
        refresh_cart_item_count(request, cart)
        return None
    available = _stock_for(item.product, item.variant)
    if quantity > available:
        raise InsufficientStockError(available, item.product.name)
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
