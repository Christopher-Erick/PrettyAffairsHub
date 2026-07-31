from django.contrib import admin

from .models import Coupon, FlashSale, GiftCard


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "amount", "used_count", "is_active", "ends_at")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)


@admin.register(GiftCard)
class GiftCardAdmin(admin.ModelAdmin):
    list_display = ("code", "initial_balance", "current_balance", "is_active", "created_at")
    search_fields = ("code",)


@admin.register(FlashSale)
class FlashSaleAdmin(admin.ModelAdmin):
    list_display = ("name", "percent_off", "starts_at", "ends_at", "is_active")
    filter_horizontal = ("products",)
