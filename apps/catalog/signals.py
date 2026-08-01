"""Invalidate smart catalog cache whenever catalogue rows change."""

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import (
    Brand,
    Category,
    Collection,
    Product,
    ProductImage,
    ProductRelation,
    ProductVariant,
)
from apps.core.smart_cache import invalidate_catalog_cache


def _bump(sender, **kwargs):
    invalidate_catalog_cache(reason=f"{sender.__name__} changed")


for model in (Brand, Category, Collection, Product, ProductImage, ProductVariant, ProductRelation):
    post_save.connect(_bump, sender=model, dispatch_uid=f"smart_cache_save_{model.__name__}")
    post_delete.connect(_bump, sender=model, dispatch_uid=f"smart_cache_delete_{model.__name__}")


@receiver(m2m_changed, sender=Product.categories.through, dispatch_uid="smart_cache_m2m_categories")
@receiver(m2m_changed, sender=Product.collections.through, dispatch_uid="smart_cache_m2m_collections")
def _bump_m2m(sender, **kwargs):
    if kwargs.get("action") in {"post_add", "post_remove", "post_clear"}:
        invalidate_catalog_cache(reason="product m2m changed")
