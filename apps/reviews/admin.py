from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "author_name", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating")
    search_fields = ("author_name", "title", "body", "product__name")
    actions = ["approve_reviews"]

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        for review in queryset:
            review.is_approved = True
            review.save(update_fields=["is_approved"])
            Review.refresh_product_stats(review.product)
