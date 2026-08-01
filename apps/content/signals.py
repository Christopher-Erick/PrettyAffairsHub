"""Invalidate homepage content caches when CMS rows change."""

from django.db.models.signals import post_delete, post_save

from apps.content.models import BlogPost, FAQ, HomepageSection, SitePage, Testimonial
from apps.core.smart_cache import invalidate_catalog_cache
from apps.discounts.models import FlashSale


def _bump(sender, **kwargs):
    invalidate_catalog_cache(reason=f"{sender.__name__} content changed")


for model in (BlogPost, FAQ, HomepageSection, SitePage, Testimonial, FlashSale):
    post_save.connect(_bump, sender=model, dispatch_uid=f"smart_cache_content_save_{model.__name__}")
    post_delete.connect(
        _bump, sender=model, dispatch_uid=f"smart_cache_content_delete_{model.__name__}"
    )
