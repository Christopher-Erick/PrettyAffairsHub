from django.contrib import admin

from .models import Order, OrderEvent, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_name", "sku", "quantity", "unit_price", "line_total")


class OrderEventInline(admin.TabularInline):
    model = OrderEvent
    extra = 0
    readonly_fields = ("status", "note", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "email", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "email", "tracking_code", "shipping_name")
    inlines = [OrderItemInline, OrderEventInline]
    readonly_fields = ("order_number", "created_at", "updated_at")
