from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, TemplateView

from apps.catalog.models import Category, Product, ProductVariant
from apps.content.forms import ContactForm, NewsletterForm
from apps.content.models import BlogPost, FAQ, HomepageSection, SitePage, Testimonial
from apps.discounts.models import FlashSale

ACTIVE_VARIANTS = Prefetch(
    "variants",
    queryset=ProductVariant.objects.filter(is_active=True).order_by("id"),
)

GIFT_CARD_DENOMINATIONS = [1000, 2500, 5000, 10000]


def _card_qs():
    return Product.objects.published().select_related("brand").prefetch_related(
        "images", ACTIVE_VARIANTS
    )


class HomeView(TemplateView):
    template_name = "content/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        card_qs = _card_qs()
        featured = list(Product.objects.featured().select_related("brand").prefetch_related("images", ACTIVE_VARIANTS)[:8])
        context["featured_products"] = featured or list(card_qs[:8])
        context["new_arrivals"] = list(
            Product.objects.new_arrivals().select_related("brand").prefetch_related("images", ACTIVE_VARIANTS)[:8]
        )
        context["bestsellers"] = list(
            Product.objects.best_sellers().select_related("brand").prefetch_related("images", ACTIVE_VARIANTS)[:8]
        )
        context["shade_picks"] = list(
            card_qs.annotate(
                shade_count=Count("variants", filter=Q(variants__is_active=True), distinct=True)
            )
            .filter(shade_count__gte=3)
            .order_by("-shade_count", "-average_rating", "-review_count")[:8]
        )
        context["categories"] = list(
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
        context["testimonials"] = list(Testimonial.objects.filter(is_featured=True)[:3])
        context["sections"] = list(HomepageSection.objects.filter(is_active=True))
        context["flash_sales"] = [s for s in FlashSale.objects.filter(is_active=True) if s.is_live][:1]
        context["blog_posts"] = list(BlogPost.objects.filter(is_published=True)[:3])
        return context


class AboutView(TemplateView):
    template_name = "content/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page"] = SitePage.objects.filter(slug="about", is_published=True).first()
        return context


class FAQListView(ListView):
    template_name = "content/faq.html"
    context_object_name = "faqs"

    def get_queryset(self):
        return FAQ.objects.filter(is_active=True)


class BlogListView(ListView):
    template_name = "content/blog_list.html"
    context_object_name = "posts"
    paginate_by = 9

    def get_queryset(self):
        qs = BlogPost.objects.filter(is_published=True)
        if self.request.GET.get("tutorials") == "1":
            qs = qs.filter(is_tutorial=True)
        return qs


class BlogDetailView(DetailView):
    model = BlogPost
    template_name = "content/blog_detail.html"
    context_object_name = "post"

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True)


class SitePageDetailView(DetailView):
    model = SitePage
    template_name = "content/page.html"
    context_object_name = "page"

    def get_queryset(self):
        return SitePage.objects.filter(is_published=True)


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Message sent. We will reply soon.")
        return redirect("content:contact")
    return render(request, "content/contact.html", {"form": form})


def newsletter_subscribe(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            from apps.content.models import NewsletterSubscriber

            NewsletterSubscriber.objects.get_or_create(email=form.cleaned_data["email"])
            messages.success(request, "You are subscribed.")
        else:
            messages.error(request, "That email could not be subscribed.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


def gift_cards(request):
    # Issued gift cards are customer property and stay in the staff admin; shoppers
    # only see the denominations we sell.
    return render(
        request,
        "content/gift_cards.html",
        {"denominations": GIFT_CARD_DENOMINATIONS},
    )
