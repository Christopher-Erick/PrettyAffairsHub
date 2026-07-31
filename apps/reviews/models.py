from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count


class Review(models.Model):
    product = models.ForeignKey(
        "catalog.Product", related_name="reviews", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="reviews",
        on_delete=models.SET_NULL,
    )
    author_name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=160, blank=True)
    body = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product} — {self.rating}★"

    @classmethod
    def refresh_product_stats(cls, product):
        stats = product.reviews.filter(is_approved=True).aggregate(
            avg=Avg("rating"), count=Count("id")
        )
        product.average_rating = stats["avg"] or 0
        product.review_count = stats["count"] or 0
        product.save(update_fields=["average_rating", "review_count"])
