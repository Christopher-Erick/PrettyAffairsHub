"""Server-side ritual recommendation rules engine.

Uses quiz answers, Kenya daypart, browse/search/wishlist signals, and
frequently-bought-together relations — no third-party LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Q

from apps.catalog.cache import shop_product_qs
from apps.catalog.models import Product, ProductRelation
from apps.catalog.services import get_recent_searches, get_recently_viewed_ids

NAIROBI = ZoneInfo(getattr(settings, "TIME_ZONE", None) or "Africa/Nairobi")

OCCASION_VALUES = {"everyday", "evening", "bold"}
FOCUS_VALUES = {"lips", "eyes", "full"}
FINISH_VALUES = {"matte", "gloss", "soft"}

# Live catalogue slugs (aligned with seed / storefront taxonomy).
COLLECTION_EVERYDAY = "everyday-essentials"
COLLECTION_NIGHT = "night-out"
CAT_LIPS = {"lipstick", "lip-gloss", "lip-oil", "lips"}
CAT_EYES = {"lashes", "eyes-lashes", "eye-shadow", "eyes"}
CAT_MATTE = {"lipstick"}
CAT_GLOSS = {"lip-gloss"}
CAT_SOFT = {"lip-oil"}

LABELS = {
    "everyday": "everyday soft",
    "evening": "evening glow",
    "bold": "bold statement",
    "lips": "lips-first",
    "eyes": "eye-focused",
    "full": "full-face",
    "matte": "matte",
    "gloss": "gloss & shine",
    "soft": "soft & nourishing",
    "morning": "this morning",
    "afternoon": "this afternoon",
    "evening_day": "this evening",
    "late": "tonight",
}

POOL_CAP = 120
TRIO_SIZE = 3


@dataclass
class RitualSignals:
    occasion: str
    focus: str
    finish: str
    daypart: str
    viewed_ids: list[int] = field(default_factory=list)
    search_terms: list[str] = field(default_factory=list)
    wishlist_ids: list[int] = field(default_factory=list)
    fired: list[str] = field(default_factory=list)


def kenya_daypart(now: datetime | None = None) -> str:
    now = now or datetime.now(NAIROBI)
    hour = now.hour
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "late"


def _primary_category_slug(product: Product) -> str:
    cats = list(product.categories.all())
    if not cats:
        return ""
    # Prefer leaf categories (those with a parent).
    leaves = [c for c in cats if c.parent_id]
    chosen = leaves[0] if leaves else cats[0]
    return chosen.slug


def _category_slugs(product: Product) -> set[str]:
    return {c.slug for c in product.categories.all()}


def _collection_slugs(product: Product) -> set[str]:
    return {c.slug for c in product.collections.all()}


def _product_image_url(product: Product) -> str:
    img = product.primary_image
    if img and img.image:
        return img.image.url
    return ""


def build_signals(request, *, occasion: str, focus: str, finish: str) -> RitualSignals:
    occasion = occasion if occasion in OCCASION_VALUES else ""
    focus = focus if focus in FOCUS_VALUES else ""
    finish = finish if finish in FINISH_VALUES else ""
    daypart = kenya_daypart()
    viewed = [int(x) for x in get_recently_viewed_ids(request)[:12]]
    searches = get_recent_searches(request)[:8]
    wishlist_ids: list[int] = []
    if getattr(request.user, "is_authenticated", False):
        try:
            from apps.accounts.services import get_or_create_wishlist

            wishlist_ids = list(
                get_or_create_wishlist(request.user).products.values_list("id", flat=True)[:24]
            )
        except Exception:
            wishlist_ids = []

    signals = RitualSignals(
        occasion=occasion,
        focus=focus,
        finish=finish,
        daypart=daypart,
        viewed_ids=viewed,
        search_terms=searches,
        wishlist_ids=wishlist_ids,
    )
    return signals


def _candidate_queryset(signals: RitualSignals):
    qs = shop_product_qs().prefetch_related("collections", "relations_from")

    interest_q = Q()
    if signals.occasion == "everyday":
        interest_q |= Q(collections__slug=COLLECTION_EVERYDAY)
    if signals.occasion in {"evening", "bold"}:
        interest_q |= Q(collections__slug=COLLECTION_NIGHT)
    if signals.focus == "lips":
        interest_q |= Q(categories__slug__in=CAT_LIPS)
    if signals.focus == "eyes":
        interest_q |= Q(categories__slug__in=CAT_EYES)
    if signals.finish == "matte":
        interest_q |= Q(categories__slug__in=CAT_MATTE)
    if signals.finish == "gloss":
        interest_q |= Q(categories__slug__in=CAT_GLOSS)
    if signals.finish == "soft":
        interest_q |= Q(categories__slug__in=CAT_SOFT)

    interest_q |= Q(is_bestseller=True) | Q(is_featured=True) | Q(is_trending=True)
    if signals.viewed_ids:
        interest_q |= Q(pk__in=signals.viewed_ids)
    if signals.wishlist_ids:
        interest_q |= Q(pk__in=signals.wishlist_ids)
    for term in signals.search_terms[:5]:
        interest_q |= (
            Q(name__icontains=term)
            | Q(short_description__icontains=term)
            | Q(categories__slug__icontains=term.replace(" ", "-"))
        )

    matched = list(
        qs.filter(interest_q)
        .distinct()
        .order_by("-is_bestseller", "-is_featured", "-is_trending", "name")[:POOL_CAP]
    )
    # Always prefer in-stock; fall back if the store is thin.
    in_stock = [p for p in matched if p.in_stock]
    return in_stock or matched[:POOL_CAP]


def score_product(product: Product, signals: RitualSignals) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    cats = _category_slugs(product)
    cols = _collection_slugs(product)
    pid = product.pk

    if signals.occasion == "everyday" and COLLECTION_EVERYDAY in cols:
        score += 5
        reasons.append("everyday")
    if signals.occasion == "bold" and COLLECTION_NIGHT in cols:
        score += 5
        reasons.append("bold-night")
    if signals.occasion == "evening" and (
        COLLECTION_NIGHT in cols or product.is_bestseller or product.is_trending
    ):
        score += 4
        reasons.append("evening")

    if signals.focus == "lips" and cats & CAT_LIPS:
        score += 6
        reasons.append("lips")
    if signals.focus == "eyes" and cats & CAT_EYES:
        score += 7
        reasons.append("eyes")
    if signals.focus == "full":
        score += 2

    if signals.finish == "matte" and cats & CAT_MATTE:
        score += 5
        reasons.append("matte")
    if signals.finish == "gloss" and cats & CAT_GLOSS:
        score += 5
        reasons.append("gloss")
    if signals.finish == "soft" and cats & CAT_SOFT:
        score += 5
        reasons.append("soft")

    # Daypart soft nudges.
    if signals.daypart == "morning" and (
        COLLECTION_EVERYDAY in cols or cats & CAT_SOFT or cats & CAT_GLOSS
    ):
        score += 2
        reasons.append("daypart-morning")
    if signals.daypart in {"evening", "late"} and (
        COLLECTION_NIGHT in cols or product.is_bestseller or cats & CAT_MATTE
    ):
        score += 3
        reasons.append("daypart-evening")
    if signals.daypart == "afternoon" and (product.is_featured or cats & CAT_LIPS):
        score += 1

    if pid in signals.viewed_ids:
        # Stronger if recently viewed (earlier in list = more recent).
        boost = 4 if signals.viewed_ids.index(pid) < 4 else 2
        score += boost
        reasons.append("viewed")
    if pid in signals.wishlist_ids:
        score += 5
        reasons.append("wishlist")

    name_l = (product.name or "").lower()
    short_l = (product.short_description or "").lower()
    for term in signals.search_terms:
        if term in name_l or term in short_l or any(term in c for c in cats):
            score += 4
            reasons.append("search")
            break

    if product.is_featured:
        score += 1
    if product.is_bestseller:
        score += 2
    if product.is_trending:
        score += 1
    if product.in_stock:
        score += 2

    return score, reasons


def _fbt_map(product_ids: list[int]) -> dict[int, set[int]]:
    if not product_ids:
        return {}
    rows = ProductRelation.objects.filter(
        relation_type=ProductRelation.RELATION_FBT,
        from_product_id__in=product_ids,
    ).values_list("from_product_id", "to_product_id")
    out: dict[int, set[int]] = {pid: set() for pid in product_ids}
    for fr, to in rows:
        out.setdefault(fr, set()).add(to)
    return out


def assemble_trio(
    ranked: list[tuple[Product, int, list[str]]],
    *,
    focus: str,
) -> list[tuple[Product, int, list[str]]]:
    if not ranked:
        return []

    by_id = {p.pk: (p, sc, rs) for p, sc, rs in ranked}
    fbt = _fbt_map([p.pk for p, _, _ in ranked])

    picked: list[tuple[Product, int, list[str]]] = []
    used_cats: set[str] = set()
    used_ids: set[int] = set()

    def try_add(entry: tuple[Product, int, list[str]], *, force: bool = False) -> bool:
        product, score, reasons = entry
        if product.pk in used_ids:
            return False
        primary = _primary_category_slug(product) or product.name
        if not force and focus != "full" and primary in used_cats and len(picked) < 2:
            return False
        picked.append((product, score, reasons))
        used_ids.add(product.pk)
        used_cats.add(primary)
        return True

    # Anchor: highest score.
    try_add(ranked[0], force=True)
    anchor_id = picked[0][0].pk

    # Prefer FBT neighbors of the anchor for coherence.
    neighbors = sorted(
        (
            by_id[nid]
            for nid in fbt.get(anchor_id, set())
            if nid in by_id and nid not in used_ids
        ),
        key=lambda item: (-item[1], float(item[0].price)),
    )
    for entry in neighbors:
        if len(picked) >= TRIO_SIZE:
            break
        boosted = (entry[0], entry[1] + 3, entry[2] + ["fbt"])
        try_add(boosted)

    for entry in ranked[1:]:
        if len(picked) >= TRIO_SIZE:
            break
        try_add(entry)

    # Backfill without diversity constraint if still short.
    if len(picked) < TRIO_SIZE:
        for entry in ranked:
            if len(picked) >= TRIO_SIZE:
                break
            try_add(entry, force=True)

    return picked[:TRIO_SIZE]


def build_story(signals: RitualSignals, picked: list[tuple[Product, int, list[str]]]) -> str:
    day_label = LABELS.get(
        "evening_day" if signals.daypart == "evening" else signals.daypart,
        signals.daypart,
    )
    mood = LABELS.get(signals.occasion, signals.occasion)
    focus = LABELS.get(signals.focus, signals.focus)
    finish = LABELS.get(signals.finish, signals.finish)
    article = "an" if mood[:1].lower() in "aeiou" else "a"

    reason_set = {r for _, _, rs in picked for r in rs}
    extras: list[str] = []
    if "viewed" in reason_set:
        extras.append("pieces you've been looking at")
    if "search" in reason_set and signals.search_terms:
        extras.append(f'your "{signals.search_terms[0]}" searches')
    if "wishlist" in reason_set:
        extras.append("your wishlist")
    if "fbt" in reason_set:
        extras.append("items that finish each other")

    head = f"{day_label.capitalize()} · {article} {mood} mood · {focus} · {finish}"
    if extras:
        return f"{head} — shaped around {extras[0]}, with a trio that plays together."
    return f"{head} — a coherent trio chosen for how the pieces finish each other."


def serialize_product(product: Product, *, score: int = 0) -> dict[str, Any]:
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "url": product.get_absolute_url(),
        "price": float(product.price),
        "stock": product.available_stock,
        "in_stock": product.in_stock,
        "is_low_stock": product.is_low_stock,
        "categories": list(_category_slugs(product)),
        "image": _product_image_url(product),
        "score": score,
    }


def recommend_ritual(request, *, occasion: str, focus: str, finish: str) -> dict[str, Any]:
    signals = build_signals(request, occasion=occasion, focus=focus, finish=finish)
    if not (signals.occasion and signals.focus and signals.finish):
        return {
            "ok": False,
            "message": "Pick occasion, focus, and finish to build your ritual.",
            "products": [],
            "summary": "",
            "total": 0,
        }

    candidates = _candidate_queryset(signals)
    scored: list[tuple[Product, int, list[str]]] = []
    for product in candidates:
        score, reasons = score_product(product, signals)
        scored.append((product, score, reasons))
    scored.sort(key=lambda item: (-item[1], float(item[0].price), item[0].name))

    picked = assemble_trio(scored, focus=signals.focus)
    products = [serialize_product(p, score=sc) for p, sc, _ in picked]
    total = sum((Decimal(str(p["price"])) for p in products), Decimal("0"))
    summary = build_story(signals, picked)

    fired = sorted({r for _, _, rs in picked for r in rs})
    return {
        "ok": True,
        "message": "",
        "products": products,
        "summary": summary,
        "total": float(total),
        "daypart": signals.daypart,
        "signals": fired,
    }
