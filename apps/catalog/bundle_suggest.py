"""Suggest a complementary bundle: 2 high-sellers + 1 slower mover.

Sales velocity prefers confirmed OrderItem totals. Manual is_bestseller /
low-stock flags fill gaps until WhatsApp sales are logged as orders.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from apps.catalog.models import Product, ProductRelation
from apps.orders.models import Order, OrderItem

COUNTED_STATUSES = (
    Order.STATUS_PAID,
    Order.STATUS_PROCESSING,
    Order.STATUS_SHIPPED,
    Order.STATUS_DELIVERED,
)


def product_units_sold() -> dict[int, int]:
    rows = (
        OrderItem.objects.filter(
            product_id__isnull=False,
            order__status__in=COUNTED_STATUSES,
        )
        .values("product_id")
        .annotate(units=Sum("quantity"))
    )
    return {int(row["product_id"]): int(row["units"] or 0) for row in rows}


def _primary_slug(product: Product) -> str:
    cats = list(product.categories.all())
    if not cats:
        return ""
    leaves = [c for c in cats if c.parent_id]
    return (leaves[0] if leaves else cats[0]).slug


def _fbt_neighbors(product_ids: list[int]) -> dict[int, set[int]]:
    if not product_ids:
        return {}
    rows = ProductRelation.objects.filter(
        relation_type=ProductRelation.RELATION_FBT,
        from_product_id__in=product_ids,
    ).values_list("from_product_id", "to_product_id")
    out: dict[int, set[int]] = {pid: set() for pid in product_ids}
    for fr, to in rows:
        out.setdefault(int(fr), set()).add(int(to))
    return out


def suggest_hot_and_slow_trio() -> dict:
    """
    Return {"products": [Product, Product, Product], "reasons": [...], "name": str, "price": Decimal, "compare_at": Decimal|None}
    or empty products if the catalogue is too thin.
    """
    sold = product_units_sold()
    candidates = list(
        Product.objects.published()
        .prefetch_related("categories", "collections")
        .filter(stock__gt=0)
        .order_by("name")
    )
    # Prefer truly available stock when variants exist.
    available = [p for p in candidates if p.in_stock]
    pool = available or candidates
    if len(pool) < 3:
        return {
            "products": pool[:3],
            "reasons": ["Not enough in-stock products to build a full trio."],
            "name": "Starter Edit",
            "price": sum((p.price for p in pool), Decimal("0")),
            "compare_at": None,
        }

    ranked = sorted(
        pool,
        key=lambda p: (
            -sold.get(p.id, 0),
            -int(p.is_bestseller),
            -int(p.is_featured),
            float(p.price),
        ),
    )
    hot = ranked[:2]
    hot_ids = {p.id for p in hot}
    fbt = _fbt_neighbors(list(hot_ids))
    neighbor_ids = set()
    for pid in hot_ids:
        neighbor_ids |= fbt.get(pid, set())

    hot_cats = {_primary_slug(p) for p in hot}

    def slow_score(p: Product) -> tuple:
        units = sold.get(p.id, 0)
        complements = 0
        if p.id in neighbor_ids:
            complements += 10
        primary = _primary_slug(p)
        # Prefer a different category so the edit feels like a set, not three of the same.
        if primary and primary not in hot_cats:
            complements += 4
        # Soft preference for non-bestsellers when lifting a quiet SKU.
        if not p.is_bestseller:
            complements += 1
        # Lower sales first, then stronger complement score.
        return (units, -complements, -int(p.is_featured), float(p.price))

    slow_pool = [p for p in ranked[2:] if p.id not in hot_ids]
    slow_pool.sort(key=slow_score)
    slow = slow_pool[0] if slow_pool else ranked[2]

    products = [hot[0], hot[1], slow]
    reasons = [
        f"Hot: “{hot[0].name}” ({sold.get(hot[0].id, 0)} sold / bestseller signal).",
        f"Hot: “{hot[1].name}” ({sold.get(hot[1].id, 0)} sold / bestseller signal).",
        f"Lift: “{slow.name}” ({sold.get(slow.id, 0)} sold) — complements the pair via "
        f"{'bought-together links' if slow.id in neighbor_ids else 'category contrast'}.",
    ]
    if not sold:
        reasons.append(
            "No confirmed website orders yet — ranking used bestseller flags. "
            "Log WhatsApp sales as orders so this stays accurate."
        )

    compare = sum((p.price for p in products), Decimal("0"))
    # Soft bundle price: 10% off the sum, rounded to whole shillings.
    price = (compare * Decimal("0.90")).quantize(Decimal("1"))
    name = f"{hot[0].name.split()[0]} + {hot[1].name.split()[0]} Edit"
    if len(name) > 80:
        name = "Hot Pair + Quiet Lift Edit"

    return {
        "products": products,
        "reasons": reasons,
        "name": name,
        "price": price,
        "compare_at": compare,
    }
