from decimal import Decimal
import uuid

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
                update_fields = ["quantity"]
                if item.ritual_group and not existing.ritual_group:
                    existing.ritual_group = item.ritual_group
                    update_fields.append("ritual_group")
                existing.save(update_fields=update_fields)
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


def _resolve_line_variant(product, variant_id=None):
    """Match cart stock to Product.in_stock: use an in-stock variant when shades exist."""
    if variant_id:
        return ProductVariant.objects.get(pk=variant_id, product=product, is_active=True)
    active = [v for v in product.variants.all() if v.is_active]
    if not active:
        return None
    variant = product.default_variant
    if variant is None:
        raise InsufficientStockError(0, product.name)
    return variant


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
def add_to_cart(request, product_id, quantity=1, variant_id=None, *, ritual_group="", refresh=True):
    product = Product.objects.published().prefetch_related("variants").get(pk=product_id)
    variant = _resolve_line_variant(product, variant_id)
    unit_price = variant.price if variant is not None else product.price

    quantity = max(1, int(quantity))
    available = _stock_for(product, variant)
    if available < quantity:
        raise InsufficientStockError(available, product.name)

    cart = get_or_create_cart(request)
    group = (ritual_group or "").strip()[:36]
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        variant=variant,
        bundle=None,
        defaults={
            "quantity": quantity,
            "unit_price": unit_price,
            "ritual_group": group,
        },
    )
    if not created:
        new_qty = item.quantity + quantity
        if new_qty > available:
            raise InsufficientStockError(available, product.name)
        item.quantity = new_qty
        item.unit_price = unit_price
        update_fields = ["quantity", "unit_price"]
        if group:
            item.ritual_group = group
            update_fields.append("ritual_group")
        item.save(update_fields=update_fields)
    if refresh:
        refresh_cart_item_count(request, cart)
    return item, quantity


@transaction.atomic
def add_ritual_to_cart(request, product_ids):
    """Add ritual pieces as one linked set. All-or-nothing; remove clears the whole set."""
    ids = []
    seen = set()
    for raw in product_ids or []:
        try:
            pk = int(raw)
        except (TypeError, ValueError):
            continue
        if pk < 1 or pk in seen:
            continue
        seen.add(pk)
        ids.append(pk)

    if not ids:
        raise ValueError("Nothing to add.")

    products = list(
        Product.objects.published().filter(id__in=ids).prefetch_related("variants")
    )
    by_id = {p.id: p for p in products}
    if len(by_id) != len(ids):
        raise ValueError("One or more ritual pieces are no longer available.")

    cart = get_or_create_cart(request)
    # Validate every piece can be fulfilled before mutating the cart.
    for pid in ids:
        product = by_id[pid]
        variant = _resolve_line_variant(product, None)
        available = _stock_for(product, variant)
        existing = cart.items.filter(
            product=product, variant=variant, bundle__isnull=True
        ).first()
        need = 1 + (existing.quantity if existing else 0)
        if need > available:
            raise InsufficientStockError(available, product.name)

    group = str(uuid.uuid4())
    added = 0
    for pid in ids:
        add_to_cart(
            request, product_id=pid, quantity=1, ritual_group=group, refresh=False
        )
        added += 1
    refresh_cart_item_count(request, cart)
    return added, group


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
        if item.ritual_group:
            cart.items.filter(ritual_group=item.ritual_group).delete()
        else:
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
    """Remove a line; ritual pieces sharing ritual_group are cleared together."""
    cart = get_or_create_cart(request)
    item = cart.items.filter(pk=item_id).first()
    if item is None:
        refresh_cart_item_count(request, cart)
        return 0
    if item.ritual_group:
        deleted, _ = cart.items.filter(ritual_group=item.ritual_group).delete()
    else:
        deleted, _ = cart.items.filter(pk=item_id).delete()
    refresh_cart_item_count(request, cart)
    return deleted


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


def build_whatsapp_ritual_order(
    products,
    *,
    occasion: str = "",
    focus: str = "",
    finish: str = "",
    currency_symbol="KSh",
):
    """WA draft for a completed ritual trio — prices/names from the DB only."""
    labels = {
        "everyday": "Everyday soft",
        "evening": "Evening glow",
        "bold": "Bold statement",
        "lips": "Lips first",
        "eyes": "Eye story",
        "full": "Full face",
        "matte": "Matte",
        "gloss": "Gloss & shine",
        "soft": "Soft & nourishing",
    }
    mood = " · ".join(
        labels.get(key, key)
        for key in (occasion, focus, finish)
        if key
    )
    lines = ["Hi Pretty Affairs Hub — I'd like to order my ritual edit:", ""]
    if mood:
        lines.append(f"Mood: {mood}")
        lines.append("")
    total = Decimal("0")
    for product in products:
        unit = product.price
        total += unit
        price = int(unit) if unit == unit.to_integral_value() else unit
        lines.append(f"- {product.name} x 1 — {currency_symbol} {price}")
    total_fmt = int(total) if total == total.to_integral_value() else total
    lines.extend(
        [
            "",
            f"Total: {currency_symbol} {total_fmt}",
            "",
            "Please confirm availability and payment. Thank you!",
        ]
    )
    return "\n".join(lines), len(products), total


def ritual_products_snapshot(products) -> tuple[list[dict], int, Decimal]:
    """Lead snapshot rows for a ritual trio (no cart mutation)."""
    rows = []
    total = Decimal("0")
    for product in products:
        variant = product.default_variant
        unit = variant.price if variant is not None else product.price
        total += unit
        rows.append(
            {
                "product_id": product.id,
                "variant_id": variant.id if variant is not None else None,
                "product_name": product.name,
                "variant_name": variant.name if variant is not None else "",
                "sku": (variant.sku if variant is not None and variant.sku else product.sku) or "",
                "quantity": 1,
                "unit_price": str(unit),
                "line_total": str(unit),
                "is_bundle": False,
                "is_ritual": True,
            }
        )
    return rows, len(rows), total


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
