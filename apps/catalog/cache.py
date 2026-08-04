"""Cached catalogue loaders — database only on cold miss / after writes."""

from __future__ import annotations

from django.db.models import Count, Prefetch, Q

from apps.catalog.models import (
    Bundle,
    BundleItem,
    Category,
    Collection,
    Product,
    ProductImage,
    ProductVariant,
)
from apps.core.smart_cache import get_or_set, versioned_key

ACTIVE_VARIANTS = Prefetch(
    "variants",
    queryset=ProductVariant.objects.filter(is_active=True).only(
        "id", "product_id", "name", "color_hex", "stock", "is_active", "price_override", "image"
    ),
)

# Cards only need the first image; still ordered so primary_image stays correct.
CARD_IMAGES = Prefetch(
    "images",
    queryset=ProductImage.objects.order_by("sort_order", "id").only(
        "id", "product_id", "image", "alt_text", "sort_order"
    ),
)

BUNDLE_ITEMS = Prefetch(
    "items",
    queryset=BundleItem.objects.select_related("product").order_by("id"),
)

BUNDLE_PRODUCT_IMAGES = Prefetch(
    "items__product__images",
    queryset=ProductImage.objects.order_by("sort_order", "id").only(
        "id", "product_id", "image", "alt_text", "sort_order"
    ),
)

BUNDLE_PRODUCT_VARIANTS = Prefetch(
    "items__product__variants",
    queryset=ProductVariant.objects.filter(is_active=True).only(
        "id", "product_id", "name", "color_hex", "stock", "is_active", "price_override", "image"
    ),
)


def shop_product_qs():
    return (
        Product.objects.published()
        .select_related("brand")
        .prefetch_related(CARD_IMAGES, "categories", ACTIVE_VARIANTS)
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


def cached_category_descendant_ids(slug: str):
    def producer():
        category = Category.objects.filter(slug=slug, is_active=True).first()
        if not category:
            return []
        return category.descendant_ids()

    return get_or_set(versioned_key("catalog:category_descendants", slug), producer)


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
        .order_by("parent__sort_order", "sort_order", "name")[:16]
    )
    leaf_ids = {c.id for c in leaf_categories}
    samples_by_category: dict[int, Product] = {}
    if leaf_ids:
        # Bound the scan — full catalogue walk was expensive on cold cache.
        for product in (
            shop_product_qs()
            .filter(categories__id__in=leaf_ids)
            .order_by("-is_featured", "-average_rating", "-created_at")
            .distinct()[: max(48, len(leaf_ids) * 3)]
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
        # Keep rails short — each card triggers an image download through Django.
        rail = 4
        featured = list(
            Product.objects.featured()
            .select_related("brand")
            .prefetch_related(CARD_IMAGES, ACTIVE_VARIANTS)[:rail]
        )
        featured = featured or list(card_qs[:rail])
        new_arrivals = list(
            Product.objects.new_arrivals()
            .select_related("brand")
            .prefetch_related(CARD_IMAGES, ACTIVE_VARIANTS)[:rail]
        )
        bestsellers = list(
            Product.objects.best_sellers()
            .select_related("brand")
            .prefetch_related(CARD_IMAGES, ACTIVE_VARIANTS)[:rail]
        )
        shade_picks = list(
            card_qs.annotate(
                shade_count=Count("variants", filter=Q(variants__is_active=True), distinct=True)
            )
            .filter(shade_count__gte=3)
            .order_by("-shade_count", "-average_rating", "-review_count")[:rail]
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
            .order_by("parent__sort_order", "sort_order", "name")[:8]
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


def cached_active_bundles():
    """Live bundles with a full 3-product trio — reused on the storefront list."""

    def producer():
        return list(
            Bundle.objects.filter(is_active=True)
            .annotate(_item_count=Count("items"))
            .filter(_item_count=3)
            .prefetch_related(BUNDLE_ITEMS, BUNDLE_PRODUCT_IMAGES)
            .order_by("name")
        )

    return get_or_set("catalog:bundles:active", producer)
