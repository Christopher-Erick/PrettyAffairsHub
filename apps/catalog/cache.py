"""Cached catalogue loaders — database only on cold miss / after writes."""

from __future__ import annotations

from django.db.models import Count, Prefetch, Q

from apps.catalog.models import Category, Collection, Product, ProductVariant
from apps.core.smart_cache import get_or_set, versioned_key

ACTIVE_VARIANTS = Prefetch(
    "variants",
    queryset=ProductVariant.objects.filter(is_active=True).order_by("id"),
)


def shop_product_qs():
    return (
        Product.objects.published()
        .select_related("brand")
        .prefetch_related("images", "categories", ACTIVE_VARIANTS)
    )


def cached_category_tree():
    return get_or_set(
        "catalog:category_tree",
        lambda: list(Category.tree_for_filters()),
    )


def cached_active_categories():
    return get_or_set(
        "catalog:categories_active",
        lambda: list(Category.objects.filter(is_active=True)),
    )


def cached_active_collections():
    return get_or_set(
        "catalog:collections_active",
        lambda: list(Collection.objects.filter(is_active=True)),
    )


def _build_discovery():
    leaf_categories = list(
        Category.objects.filter(is_active=True, parent__isnull=False)
        .select_related("parent")
        .annotate(
            product_count=Count(
                "products",
                filter=Q(products__is_active=True),
                distinct=True,
            )
        )
        .filter(product_count__gt=0)
        .order_by("parent__sort_order", "sort_order", "name")
    )
    leaf_ids = {c.id for c in leaf_categories}
    samples_by_category: dict[int, Product] = {}
    if leaf_ids:
        for product in (
            shop_product_qs()
            .filter(categories__id__in=leaf_ids)
            .order_by("-is_featured", "-average_rating", "-created_at")
            .distinct()
        ):
            for category in product.categories.all():
                if category.id in leaf_ids and category.id not in samples_by_category:
                    samples_by_category[category.id] = product
            if len(samples_by_category) >= len(leaf_ids):
                break

    discovery = []
    for category in leaf_categories:
        sample = samples_by_category.get(category.id)
        swatches = list(sample.variants.all()[:5]) if sample else []
        discovery.append(
            {
                "category": category,
                "count": category.product_count,
                "sample": sample,
                "swatches": swatches,
            }
        )
    return discovery


def cached_discovery_categories():
    return get_or_set("catalog:shop:discovery", _build_discovery)


def cached_shade_studio():
    def producer():
        return list(
            shop_product_qs()
            .annotate(
                shade_count=Count("variants", filter=Q(variants__is_active=True), distinct=True)
            )
            .filter(shade_count__gte=3)
            .order_by("-shade_count", "-average_rating", "-review_count")[:6]
        )

    return get_or_set("catalog:shop:shade_studio", producer)


def cached_home_rails():
    """Featured / new / bestseller / shade rails for the homepage."""

    def producer():
        card_qs = shop_product_qs()
        featured = list(
            Product.objects.featured()
            .select_related("brand")
            .prefetch_related("images", ACTIVE_VARIANTS)[:8]
        )
        featured = featured or list(card_qs[:8])
        new_arrivals = list(
            Product.objects.new_arrivals()
            .select_related("brand")
            .prefetch_related("images", ACTIVE_VARIANTS)[:8]
        )
        bestsellers = list(
            Product.objects.best_sellers()
            .select_related("brand")
            .prefetch_related("images", ACTIVE_VARIANTS)[:8]
        )
        shade_picks = list(
            card_qs.annotate(
                shade_count=Count("variants", filter=Q(variants__is_active=True), distinct=True)
            )
            .filter(shade_count__gte=3)
            .order_by("-shade_count", "-average_rating", "-review_count")[:8]
        )
        categories = list(
            Category.objects.filter(is_active=True, parent__isnull=False)
            .select_related("parent")
            .annotate(
                product_count=Count(
                    "products",
                    filter=Q(products__is_active=True),
                    distinct=True,
                )
            )
            .filter(product_count__gt=0)
            .order_by("parent__sort_order", "sort_order", "name")[:10]
        )
        story_slugs = (
            "fenty-beauty-gloss-bomb-universal-lip-luminizer",
            "gisou-honey-infused-lip-oil",
            "laneige-lip-sleeping-mask",
        )
        story_products = {
            product.slug: product
            for product in card_qs.filter(slug__in=story_slugs)
        }
        return {
            "featured_products": featured,
            "new_arrivals": new_arrivals,
            "bestsellers": bestsellers,
            "shade_picks": shade_picks,
            "categories": categories,
            "story_products": story_products,
        }

    return get_or_set("catalog:home:rails", producer)


def cached_product_list(filter_fingerprint: str, producer):
    """Cache a page of product results for a stable filter fingerprint."""
    key = versioned_key("catalog:product_list", filter_fingerprint)
    return get_or_set(key, producer)


def cached_product_detail(slug: str, producer):
    key = versioned_key("catalog:product_detail", slug)
    return get_or_set(key, producer)
