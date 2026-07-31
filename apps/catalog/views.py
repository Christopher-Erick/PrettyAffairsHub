from django.contrib import messages
from django.core.cache import cache
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from django.conf import settings

from apps.catalog.models import Bundle, Category, Collection, Product, ProductVariant
from apps.catalog.services import get_recently_viewed_ids, track_product_view
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review

ACTIVE_VARIANTS = Prefetch(
    "variants",
    queryset=ProductVariant.objects.filter(is_active=True).order_by("id"),
)


def products_for_category_slug(qs, slug):
    """Filter products by category slug, including all nested children."""
    category = Category.objects.filter(slug=slug, is_active=True).first()
    if not category:
        return qs.none()
    return qs.filter(categories__id__in=category.descendant_ids())


def _shop_product_qs():
    return (
        Product.objects.published()
        .select_related("brand")
        .prefetch_related("images", "categories", ACTIVE_VARIANTS)
    )


class ProductListView(ListView):
    model = Product
    template_name = "catalog/shop.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        qs = _shop_product_qs()
        q = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category")
        collection = self.request.GET.get("collection")
        sort = self.request.GET.get("sort", "newest")
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        flag = self.request.GET.get("flag")

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(short_description__icontains=q)
                | Q(description__icontains=q)
            )
        if category:
            qs = products_for_category_slug(qs, category)
        if collection:
            qs = qs.filter(collections__slug=collection)
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if flag == "new":
            qs = qs.new_arrivals()
        elif flag == "bestsellers":
            qs = qs.best_sellers()
        elif flag == "trending":
            qs = qs.trending()
        elif flag == "featured":
            qs = qs.featured()
        elif flag == "offers":
            qs = qs.filter(is_limited_offer=True)

        sort_map = {
            "price_asc": "price",
            "price_desc": "-price",
            "name": "name",
            "newest": "-created_at",
            "rating": "-average_rating",
        }
        return qs.order_by(sort_map.get(sort, "-created_at")).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_tree"] = cache.get_or_set(
            "catalog:category_tree",
            lambda: list(Category.tree_for_filters()),
            120,
        )
        context["categories"] = cache.get_or_set(
            "catalog:categories_active",
            lambda: list(Category.objects.filter(is_active=True)),
            120,
        )
        context["collections"] = cache.get_or_set(
            "catalog:collections_active",
            lambda: list(Collection.objects.filter(is_active=True)),
            120,
        )
        context["current_filters"] = self.request.GET
        page_obj = context.get("page_obj")
        context["result_count"] = page_obj.paginator.count if page_obj is not None else len(context["products"])
        context["top_seller"] = (
            _shop_product_qs()
            .filter(is_bestseller=True)
            .order_by("-average_rating", "-review_count")
            .first()
            or _shop_product_qs().order_by("-average_rating", "-review_count").first()
        )

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
                _shop_product_qs()
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
        context["discovery_categories"] = discovery

        filters = self.request.GET
        show_shade_studio = not any(
            filters.get(key) for key in ("category", "collection", "flag", "q", "min_price", "max_price")
        )
        context["shade_studio"] = (
            _shop_product_qs()
            .annotate(
                shade_count=Count("variants", filter=Q(variants__is_active=True), distinct=True)
            )
            .filter(shade_count__gte=3)
            .order_by("-shade_count", "-average_rating", "-review_count")[:6]
            if show_shade_studio
            else []
        )
        return context


class CategoryDetailView(ProductListView):
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"], is_active=True)
        params = self.request.GET.copy()
        params["category"] = self.category.slug
        self.request.GET = params
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_category"] = self.category
        context["page_title"] = self.category.name
        return context


class CollectionDetailView(ProductListView):
    def get_queryset(self):
        self.collection = get_object_or_404(
            Collection, slug=self.kwargs["slug"], is_active=True
        )
        return super().get_queryset().filter(collections=self.collection)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_collection"] = self.collection
        context["page_title"] = self.collection.name
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = "catalog/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.published()
            .select_related("brand")
            .prefetch_related(
                "images",
                ACTIVE_VARIANTS,
                "categories",
                "relations_from__to_product__images",
            )
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        track_product_view(self.request, obj.pk)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        related_qs = _shop_product_qs()
        context["reviews"] = product.reviews.filter(is_approved=True)[:20]
        context["review_form"] = ReviewForm()
        context["similar"] = list(
            related_qs.filter(
                relations_to__from_product=product,
                relations_to__relation_type="similar",
            )[:4]
        )
        if not context["similar"]:
            context["similar"] = list(
                related_qs.filter(categories__in=product.categories.all())
                .exclude(pk=product.pk)
                .distinct()[:4]
            )
        context["fbt"] = list(
            related_qs.filter(
                relations_to__from_product=product,
                relations_to__relation_type="fbt",
            )[:3]
        )
        recent_ids = [pid for pid in get_recently_viewed_ids(self.request) if pid != product.pk]
        context["recently_viewed"] = list(related_qs.filter(pk__in=recent_ids)[:4])
        return context


class BundleListView(ListView):
    model = Bundle
    template_name = "catalog/bundles.html"
    context_object_name = "bundles"

    def get_queryset(self):
        return Bundle.objects.filter(is_active=True).prefetch_related("items__product")


class BundleDetailView(DetailView):
    model = Bundle
    template_name = "catalog/bundle_detail.html"
    context_object_name = "bundle"

    def get_queryset(self):
        return Bundle.objects.filter(is_active=True).prefetch_related("items__product__images")


def ritual_builder(request):
    products = list(
        _shop_product_qs()
        .prefetch_related("collections")
        .order_by("-is_bestseller", "-is_featured", "name")[:24]
    )
    catalog = []
    for product in products:
        catalog.append(
            {
                "id": product.id,
                "name": product.name,
                "slug": product.slug,
                "url": product.get_absolute_url(),
                "price": float(product.price),
                "stock": product.available_stock,
                "in_stock": product.in_stock,
                "is_low_stock": product.is_low_stock,
                "categories": list(product.categories.values_list("slug", flat=True)),
                "collections": list(product.collections.values_list("slug", flat=True)),
                "flags": {
                    "new": product.is_new,
                    "bestseller": product.is_bestseller,
                    "trending": product.is_trending,
                    "featured": product.is_featured,
                },
            }
        )
    return render(
        request,
        "catalog/ritual_builder.html",
        {
            "ritual_catalog": catalog,
            "currency_symbol": settings.SITE_CURRENCY_SYMBOL,
        },
    )


@require_POST
def submit_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        if request.user.is_authenticated:
            review.user = request.user
            if not review.author_name:
                review.author_name = request.user.get_full_name() or request.user.username
        review.is_approved = False
        review.save()
        messages.success(request, "Thank you — your review will appear after approval.")
    else:
        messages.error(request, "Please check your review and try again.")
    return redirect(product.get_absolute_url())
