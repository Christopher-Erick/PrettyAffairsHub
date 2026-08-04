from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from apps.catalog.models import Bundle, Product, ProductVariant
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


def get_or_create_cart(request, guest_session_key=None):
    """Return the active cart, merging a guest cart when signing in.

    Pass ``guest_session_key`` when the browser session was just cycled
    (Django ``login()``) so the pre-login guest cart can still be found.
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        keys = []
        current = _ensure_session(request)
        if current:
            keys.append(current)
        if guest_session_key and guest_session_key not in keys:
            keys.append(guest_session_key)
        for key in keys:
            guest = Cart.objects.filter(session_key=key, user__isnull=True).first()
            if guest and guest.pk != cart.pk:
                _merge_carts(guest, cart)
                refresh_cart_item_count(request, cart)
                break
        else:
            refresh_cart_item_count(request, cart)
        return cart

    session_key = _ensure_session(request)
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


def _merge_carts(source, target):
    for item in source.items.select_related("product", "variant", "bundle"):
        if item.bundle_id:
            available = bundle_sets_available(item.bundle)
            existing = target.items.filter(bundle_id=item.bundle_id).first()
            if existing:
                merged = min(existing.quantity + item.quantity, max(available, 0))
                if merged <= 0:
                    existing.delete()
                else:
                    existing.quantity = merged
                    existing.unit_price = item.bundle.price
                    existing.save(update_fields=["quantity", "unit_price"])
                item.delete()
            else:
                if available <= 0:
                    item.delete()
                    continue
                item.quantity = min(item.quantity, available)
                item.cart = target
                item.unit_price = item.bundle.price
                item.save(update_fields=["cart", "quantity", "unit_price"])
            continue

        available = _stock_for(item.product, item.variant)
        existing = target.items.filter(
            product=item.product, variant=item.variant, bundle__isnull=True
        ).first()
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


def bundle_sets_available(bundle: Bundle) -> int:
    """How many full sets can be fulfilled from component stock."""
    caps = []
    for bi in bundle.items.select_related("product").prefetch_related("product__variants"):
        product = bi.product
        if not product.is_active:
            return 0
        variants = [v for v in product.variants.all() if v.is_active]
        variant = product.default_variant if variants else None
        if variants and variant is None:
            return 0
        stock = _stock_for(product, variant)
        need = max(1, int(bi.quantity or 1))
        caps.append(stock // need)
    return min(caps) if caps else 0


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
        bundle=None,
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


@transaction.atomic
def add_bundle_to_cart(request, bundle_slug, quantity=1):
    """Add a curated bundle as one cart line at the bundle price."""
    bundle = (
        Bundle.objects.filter(is_active=True, slug=bundle_slug)
        .prefetch_related("items__product__variants")
        .first()
    )
    if bundle is None:
        raise ValueError("That bundle is no longer available.")
    if bundle.items.count() != 3:
        raise ValueError("That bundle is incomplete.")

    quantity = max(1, int(quantity))
    available = bundle_sets_available(bundle)
    if available < quantity:
        raise InsufficientStockError(available, bundle.name)

    cart = get_or_create_cart(request)
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        bundle=bundle,
        product=None,
        variant=None,
        defaults={"quantity": quantity, "unit_price": bundle.price},
    )
    if not created:
        new_qty = item.quantity + quantity
        if new_qty > available:
            raise InsufficientStockError(available, bundle.name)
        item.quantity = new_qty
        item.unit_price = bundle.price
        item.save(update_fields=["quantity", "unit_price"])
    refresh_cart_item_count(request, cart)
    return item, quantity


def update_cart_item(request, item_id, quantity):
    cart = get_or_create_cart(request)
    item = cart.items.select_related("product", "variant", "bundle").get(pk=item_id)
    quantity = int(quantity)
    if quantity <= 0:
        item.delete()
        refresh_cart_item_count(request, cart)
        return None
    if item.bundle_id:
        available = bundle_sets_available(item.bundle)
        if quantity > available:
            raise InsufficientStockError(available, item.bundle.name)
        item.quantity = quantity
        item.unit_price = item.bundle.price
        item.save(update_fields=["quantity", "unit_price"])
    else:
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


def get_cart_if_exists(request):
    """Return the caller's cart without creating a session or cart row."""
    if request.user.is_authenticated:
        return Cart.objects.filter(user=request.user).first()
    key = getattr(request.session, "session_key", None)
    if not key:
        return None
    return Cart.objects.filter(session_key=key, user__isnull=True).first()


def clear_cart(request):
    """Remove every line from the active cart and refresh the header count.

    Does not create a cart when none exists.
    """
    from apps.cart.context_processors import SESSION_CART_COUNT_KEY

    cart = get_cart_if_exists(request)
    if cart is None:
        request.session[SESSION_CART_COUNT_KEY] = 0
        return 0
    deleted, _ = cart.items.all().delete()
    if cart.coupon_code:
        cart.coupon_code = ""
        cart.save(update_fields=["coupon_code"])
    refresh_cart_item_count(request, cart)
    return deleted


def build_whatsapp_order_message(cart, currency_symbol="KSh"):
    """Plain-text order draft for wa.me prefill."""
    items = list(cart.items.select_related("product", "variant", "bundle").prefetch_related("bundle__items__product"))
    if not items:
        return (
            "Hi Pretty Affairs Hub — I'd like to place an order.",
            0,
            Decimal("0"),
        )

    lines = ["Hi Pretty Affairs Hub — I'd like to order:", ""]
    total = Decimal("0")
    count = 0
    for item in items:
        if item.bundle_id:
            name = f"{item.bundle.name} (bundle)"
            includes = item.includes_label
            line_total = item.unit_price * item.quantity
            total += line_total
            count += item.quantity
            price = int(line_total) if line_total == line_total.to_integral_value() else line_total
            lines.append(f"- {name} x {item.quantity} — {currency_symbol} {price}")
            if includes:
                lines.append(f"  {includes}")
            continue
        name = item.product.name
        if item.variant_id:
            name = f"{name} ({item.variant.name})"
        line_total = item.unit_price * item.quantity
        total += line_total
        count += item.quantity
        price = int(line_total) if line_total == line_total.to_integral_value() else line_total
        lines.append(f"- {name} x {item.quantity} — {currency_symbol} {price}")
    total_fmt = int(total) if total == total.to_integral_value() else total
    lines.extend(["", f"Total: {currency_symbol} {total_fmt}", "", "Please confirm availability and payment. Thank you!"])
    return "\n".join(lines), count, total


def build_whatsapp_bundle_enquiry(bundle: Bundle, currency_symbol="KSh"):
    """WA draft when enquiring about a bundle without adding to cart."""
    price = bundle.price
    price_fmt = int(price) if price == price.to_integral_value() else price
    lines = [
        f"Hi Pretty Affairs Hub — I'm interested in the bundle “{bundle.name}”.",
        "",
        f"Bundle price: {currency_symbol} {price_fmt}",
    ]
    names = [bi.product.name for bi in bundle.items.select_related("product")]
    if names:
        lines.append("Includes: " + " · ".join(names))
    lines.extend(["", "Please confirm availability and how to order. Thank you!"])
    return "\n".join(lines)


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
