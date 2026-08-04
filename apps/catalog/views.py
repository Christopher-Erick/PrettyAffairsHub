from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView
from django.conf import settings
import json

from apps.catalog.cache import (
    cached_active_bundles,
    cached_active_categories,
    cached_active_collections,
    cached_category_descendant_ids,
    cached_category_tree,
    cached_discovery_categories,
    cached_product_detail,
    cached_product_list,
    cached_shade_studio,
    shop_product_qs,
    BUNDLE_ITEMS,
    BUNDLE_PRODUCT_IMAGES,
    BUNDLE_PRODUCT_VARIANTS,
)
from apps.catalog.models import Bundle, Category, Collection, Product
from apps.catalog.ritual import recommend_ritual
from apps.catalog.services import get_recently_viewed_ids, track_product_view, track_shop_search
from apps.cart.services import build_whatsapp_bundle_enquiry
from apps.core.http import is_same_origin_request
from apps.core.ratelimit import rate_limit_exceeded
from apps.core.smart_cache import get_or_set, versioned_key
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review
from decimal import Decimal, InvalidOperation


def products_for_category_slug(qs, slug):
    """Filter products by category slug, including all nested children."""
    ids = cached_category_descendant_ids(slug)
    if not ids:
        return qs.none()
    return qs.filter(categories__id__in=ids)


def _shop_product_qs():
    return shop_product_qs()


class ProductListView(ListView):
    model = Product
    template_name = "catalog/shop.html"
    context_object_name = "products"
    paginate_by = 16

    def _filter_fingerprint(self) -> str:
        get = self.request.GET
        keys = (
            "q",
            "category",
            "collection",
            "sort",
            "min_price",
            "max_price",
            "flag",
        )
        return "&".join(f"{key}={get.get(key, '')}" for key in keys)

    def _parse_price(self, raw):
        """Return a non-negative Decimal price filter, or None if empty/invalid."""
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        try:
            value = Decimal(text)
        except (InvalidOperation, ValueError):
            return None
        if value < 0:
            return None
        return value

    def _build_queryset(self):
        qs = _shop_product_qs()
        q = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category")
        collection = self.request.GET.get("collection")
        sort = self.request.GET.get("sort", "newest")
        min_price = self._parse_price(self.request.GET.get("min_price"))
        max_price = self._parse_price(self.request.GET.get("max_price"))
        flag = self.request.GET.get("flag")

        if q:
            track_shop_search(self.request, q)
            # Keep search lean — variants__name blows up joins and forces DISTINCT.
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(short_description__icontains=q)
                | Q(brand__name__icontains=q)
            )
        if category:
            qs = products_for_category_slug(qs, category)
        if collection:
            qs = qs.filter(collections__slug=collection)
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
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
        qs = qs.order_by(sort_map.get(sort, "-created_at"))
        # DISTINCT is only needed when M2M / multi-row joins can duplicate products.
        if q or category or collection:
            qs = qs.distinct()
        return qs

    def get_queryset(self):
        # Real queryset for counting/slicing; page payloads are cached in paginate_queryset.
        return self._build_queryset()

    def paginate_queryset(self, queryset, page_size):
        from django.core.paginator import InvalidPage, Paginator

        page_kwarg = self.page_kwarg
        page_number = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = max(1, int(page_number))
        except (TypeError, ValueError):
            page_number = 1

        fingerprint = f"{self._filter_fingerprint()}|page={page_number}|size={page_size}"

        def producer():
            total = queryset.count()
            start = (page_number - 1) * page_size
            items = list(queryset[start : start + page_size])
            return {"count": total, "items": items, "page": page_number}

        payload = cached_product_list(fingerprint, producer)
        total = payload["count"]
        items = payload["items"]
        paginator = Paginator(range(total), page_size)
        try:
            page = paginator.page(page_number)
        except InvalidPage:
            page = paginator.page(1)
            items = list(queryset[0:page_size])
        page.object_list = items
        return (paginator, page, items, page.has_other_pages())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_tree"] = cached_category_tree()
        context["categories"] = cached_active_categories()
        context["collections"] = cached_active_collections()
        filters = self.request.GET.copy()
        for key in ("min_price", "max_price"):
            parsed = self._parse_price(filters.get(key))
            if parsed is None:
                filters[key] = ""
            else:
                filters[key] = format(parsed.normalize(), "f").rstrip("0").rstrip(".") or "0"
        context["current_filters"] = filters
        page_obj = context.get("page_obj")
        context["result_count"] = (
            page_obj.paginator.count if page_obj is not None else len(context["products"])
        )
        context["top_seller"] = get_or_set(
            "catalog:top_seller",
            lambda: (
                shop_product_qs()
                .filter(is_bestseller=True)
                .order_by("-average_rating", "-review_count")
                .first()
                or shop_product_qs().order_by("-average_rating", "-review_count").first()
            ),
        )
        browsing_clean = not any(
            filters.get(key)
            for key in ("category", "collection", "flag", "q", "min_price", "max_price")
        )
        context["discovery_categories"] = (
            cached_discovery_categories() if browsing_clean else []
        )
        context["shade_studio"] = cached_shade_studio() if browsing_clean else []
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
        params = self.request.GET.copy()
        params["collection"] = self.collection.slug
        self.request.GET = params
        return super().get_queryset()

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
        from apps.catalog.cache import ACTIVE_VARIANTS

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
        slug = self.kwargs.get(self.slug_url_kwarg)

        def producer():
            qs = queryset if queryset is not None else self.get_queryset()
            return get_object_or_404(qs, slug=slug)

        obj = cached_product_detail(slug, producer)
        track_product_view(self.request, obj.pk)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        related_qs = _shop_product_qs()

        def rails_producer():
            reviews = list(product.reviews.filter(is_approved=True)[:20])
            similar = list(
                related_qs.filter(
                    relations_to__from_product=product,
                    relations_to__relation_type="similar",
                )[:4]
            )
            if not similar:
                similar = list(
                    related_qs.filter(categories__in=product.categories.all())
                    .exclude(pk=product.pk)
                    .distinct()[:4]
                )
            fbt = list(
                related_qs.filter(
                    relations_to__from_product=product,
                    relations_to__relation_type="fbt",
                )[:3]
            )
            return {"reviews": reviews, "similar": similar, "fbt": fbt}

        rails = get_or_set(
            versioned_key("catalog:product_rails", product.slug),
            rails_producer,
        )
        context["reviews"] = rails["reviews"]
        context["similar"] = rails["similar"]
        context["fbt"] = rails["fbt"]
        context["review_form"] = ReviewForm()
        recent_ids = [pid for pid in get_recently_viewed_ids(self.request) if pid != product.pk]
        if recent_ids:
            # Preserve recency order from the session list.
            by_id = {
                p.pk: p
                for p in related_qs.filter(pk__in=recent_ids[:8])
            }
            context["recently_viewed"] = [by_id[pid] for pid in recent_ids if pid in by_id][:4]
        else:
            context["recently_viewed"] = []
        return context


class BundleListView(ListView):
    model = Bundle
    template_name = "catalog/bundles.html"
    context_object_name = "bundles"

    def get_queryset(self):
        # Cached until catalogue/bundle writes bump the smart-cache version.
        return cached_active_bundles()


class BundleDetailView(DetailView):
    model = Bundle
    template_name = "catalog/bundle_detail.html"
    context_object_name = "bundle"

    def get_queryset(self):
        return (
            Bundle.objects.filter(is_active=True)
            .annotate(_item_count=Count("items"))
            .filter(_item_count=3)
            .prefetch_related(
                BUNDLE_ITEMS,
                BUNDLE_PRODUCT_IMAGES,
                BUNDLE_PRODUCT_VARIANTS,
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        items = list(self.object.items.all())
        context["bundle_in_stock"] = bool(items) and all(
            item.product.in_stock for item in items
        )
        context["sticky_wa_text"] = build_whatsapp_bundle_enquiry(
            self.object, currency_symbol=settings.SITE_CURRENCY_SYMBOL
        )
        return context


def ritual_builder(request):
    return render(
        request,
        "catalog/ritual_builder.html",
        {
            "currency_symbol": settings.SITE_CURRENCY_SYMBOL,
            "ritual_recommend_url": reverse("catalog:ritual_recommend"),
        },
    )


@require_POST
def ritual_recommend(request):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"ok": False, "message": "Invalid request."}, status=403)
    if not is_same_origin_request(request):
        return JsonResponse({"ok": False, "message": "Invalid request."}, status=403)
    if rate_limit_exceeded(request, scope="ritual_recommend", limit=40, window_seconds=300):
        return JsonResponse(
            {"ok": False, "message": "Too many ritual builds — wait a moment and try again."},
            status=429,
        )

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (TypeError, ValueError, UnicodeDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    occasion = str(payload.get("occasion") or request.POST.get("occasion") or "").strip()
    focus = str(payload.get("focus") or request.POST.get("focus") or "").strip()
    finish = str(payload.get("finish") or request.POST.get("finish") or "").strip()

    result = recommend_ritual(request, occasion=occasion, focus=focus, finish=finish)
    status = 200 if result.get("ok") else 400
    return JsonResponse(result, status=status)


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
