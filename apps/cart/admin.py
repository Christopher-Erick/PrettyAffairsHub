from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "coupon_code", "updated_at", "abandoned_email_sent")
    search_fields = ("session_key", "user__username", "coupon_code")
    inlines = [CartItemInline]
