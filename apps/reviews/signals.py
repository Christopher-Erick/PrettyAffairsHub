from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Review


@receiver(post_save, sender=Review)
def review_saved(sender, instance, **kwargs):
    if instance.is_approved:
        Review.refresh_product_stats(instance.product)


@receiver(post_delete, sender=Review)
def review_deleted(sender, instance, **kwargs):
    Review.refresh_product_stats(instance.product)
