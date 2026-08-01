from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import DetailView, ListView, TemplateView

from apps.catalog.cache import cached_home_rails
from apps.content.forms import ContactForm, NewsletterForm
from apps.content.models import BlogPost, FAQ, HomepageSection, SitePage, Testimonial
from apps.discounts.models import FlashSale
from apps.core.smart_cache import get_or_set

GIFT_CARD_DENOMINATIONS = [1000, 2500, 5000, 10000]


def _home_page_payload():
    """One cache fill for the whole homepage (rails + CMS blocks)."""
    rails = cached_home_rails()
    story_slugs = (
        "fenty-beauty-gloss-bomb-universal-lip-luminizer",
        "gisou-honey-infused-lip-oil",
        "laneige-lip-sleeping-mask",
    )
    story_products = rails.get("story_products") or {}
    story_fallbacks = iter(
        product
        for product in (
            rails["shade_picks"]
            + rails["featured_products"]
            + rails["new_arrivals"]
            + rails["bestsellers"]
        )
        if product.primary_image and product.primary_image.image
    )
    used_ids = set()
    selected_story_products = []
    for slug in story_slugs:
        product = story_products.get(slug)
        while product is None or product.id in used_ids:
            product = next(story_fallbacks, None)
            if product is None:
                break
        if product is not None:
            selected_story_products.append(product)
            used_ids.add(product.id)

    story_copy = (
        ("The gloss edit", "Glow in every shade", "Shop the shine", "coral"),
        ("Honeyed colour", "Juicy, glass-like lips", "Find your tint", "pink"),
        ("Night-time colour care", "Wake up to softer lips", "Meet the ritual", "citrus"),
    )
    return {
        "featured_products": rails["featured_products"],
        "new_arrivals": rails["new_arrivals"],
        "bestsellers": rails["bestsellers"],
        "shade_picks": rails["shade_picks"],
        "categories": rails["categories"],
        "story_panels": [
            {
                "product": product,
                "eyebrow": eyebrow,
                "title": title,
                "cta": cta,
                "tone": tone,
            }
            for product, (eyebrow, title, cta, tone) in zip(selected_story_products, story_copy)
        ],
            "testimonials": list(Testimonial.objects.filter(is_featured=True)[:4]),
        "sections": list(HomepageSection.objects.filter(is_active=True)),
        "flash_sales": [s for s in FlashSale.objects.filter(is_active=True) if s.is_live][:1],
        "blog_posts": list(BlogPost.objects.filter(is_published=True)[:2]),
    }


class HomeView(TemplateView):
    template_name = "content/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_or_set("content:home:page", _home_page_payload))
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
        return get_or_set(
            "content:faqs:active",
            lambda: list(FAQ.objects.filter(is_active=True)),
        )


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
    from apps.core.ratelimit import rate_limit_exceeded, too_many_requests

    if request.method == "POST" and rate_limit_exceeded(
        request, scope="contact", limit=8, window_seconds=600
    ):
        return too_many_requests()
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Message sent. We will reply soon.")
        return redirect("content:contact")
    return render(request, "content/contact.html", {"form": form})


def newsletter_subscribe(request):
    from apps.core.http import safe_redirect
    from apps.core.ratelimit import rate_limit_exceeded, too_many_requests

    if request.method == "POST":
        if rate_limit_exceeded(request, scope="newsletter", limit=12, window_seconds=600):
            return too_many_requests()
        form = NewsletterForm(request.POST)
        if form.is_valid():
            from apps.content.models import NewsletterSubscriber

            NewsletterSubscriber.objects.get_or_create(email=form.cleaned_data["email"])
            messages.success(request, "You are subscribed.")
        else:
            messages.error(request, "That email could not be subscribed.")
    return safe_redirect(request, request.META.get("HTTP_REFERER"), fallback="/")


def gift_cards(request):
    # Issued gift cards are customer property and stay in the staff admin; shoppers
    # only see the denominations we sell.
    return render(
        request,
        "content/gift_cards.html",
        {"denominations": GIFT_CARD_DENOMINATIONS},
    )
