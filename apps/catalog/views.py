from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from django.conf import settings

from apps.catalog.models import Bundle, Category, Collection, Product
from apps.catalog.services import get_recently_viewed_ids, track_product_view
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review


class ProductListView(ListView):
    model = Product
    template_name = "catalog/shop.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        qs = Product.objects.published().prefetch_related("images", "categories")
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
            qs = qs.filter(categories__slug=category)
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
        context["categories"] = Category.objects.filter(is_active=True)
        context["collections"] = Collection.objects.filter(is_active=True)
        context["current_filters"] = self.request.GET
        context["top_seller"] = (
            Product.objects.published()
            .filter(is_bestseller=True)
            .prefetch_related("images")
            .order_by("-average_rating", "-review_count")
            .first()
            or Product.objects.published()
            .prefetch_related("images")
            .order_by("-average_rating", "-review_count")
            .first()
        )
        return context


class CategoryDetailView(ProductListView):
    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"], is_active=True)
        return super().get_queryset().filter(categories=self.category)

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
        return Product.objects.published().prefetch_related(
            "images", "variants", "categories", "relations_from__to_product__images"
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        track_product_view(self.request, obj.pk)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        context["reviews"] = product.reviews.filter(is_approved=True)[:20]
        context["review_form"] = ReviewForm()
        context["similar"] = Product.objects.published().filter(
            relations_to__from_product=product,
            relations_to__relation_type="similar",
        )[:4]
        if not context["similar"]:
            context["similar"] = (
                Product.objects.published()
                .filter(categories__in=product.categories.all())
                .exclude(pk=product.pk)
                .distinct()[:4]
            )
        context["fbt"] = Product.objects.published().filter(
            relations_to__from_product=product,
            relations_to__relation_type="fbt",
        )[:3]
        recent_ids = [pid for pid in get_recently_viewed_ids(self.request) if pid != product.pk]
        context["recently_viewed"] = Product.objects.published().filter(pk__in=recent_ids)[:4]
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
        Product.objects.published()
        .prefetch_related("images", "categories", "collections")
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
