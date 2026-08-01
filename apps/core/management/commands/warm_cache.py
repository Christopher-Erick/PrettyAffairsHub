from django.core.management.base import BaseCommand

from apps.catalog.cache import (
    cached_active_categories,
    cached_active_collections,
    cached_category_tree,
    cached_discovery_categories,
    cached_home_rails,
    cached_product_list,
    cached_shade_studio,
    shop_product_qs,
)
from apps.content.models import BlogPost, FAQ, HomepageSection, Testimonial
from apps.content.views import _home_page_payload
from apps.core.smart_cache import get_or_set
from apps.discounts.models import FlashSale


class Command(BaseCommand):
    help = "Warm catalogue and homepage caches so the first visitor is not a cold miss."

    def handle(self, *args, **options):
        self.stdout.write("Warming smart cache...")
        get_or_set("content:home:page", _home_page_payload)
        cached_home_rails()
        cached_category_tree()
        cached_active_categories()
        cached_active_collections()
        cached_discovery_categories()
        cached_shade_studio()
        get_or_set(
            "catalog:top_seller",
            lambda: (
                shop_product_qs()
                .filter(is_bestseller=True)
                .order_by("-average_rating", "-review_count")
                .first()
            ),
        )
        get_or_set(
            "content:testimonials:featured",
            lambda: list(Testimonial.objects.filter(is_featured=True)[:3]),
        )
        get_or_set(
            "content:homepage_sections",
            lambda: list(HomepageSection.objects.filter(is_active=True)),
        )
        get_or_set(
            "content:flash_sales:live",
            lambda: [s for s in FlashSale.objects.filter(is_active=True) if s.is_live][:1],
        )
        get_or_set(
            "content:blog_posts:home",
            lambda: list(BlogPost.objects.filter(is_published=True)[:2]),
        )
        get_or_set("content:faqs:active", lambda: list(FAQ.objects.filter(is_active=True)))

        def first_page():
            qs = shop_product_qs().order_by("-created_at")
            return {"count": qs.count(), "items": list(qs[:16]), "page": 1}

        cached_product_list(
            "q=&category=&collection=&sort=&min_price=&max_price=&flag=|page=1|size=16",
            first_page,
        )
        self.stdout.write(self.style.SUCCESS("Cache warm complete."))
