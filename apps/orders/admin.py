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
    list_display = ("order_number", "email", "status", "is_gift", "total", "created_at")
    list_filter = ("status", "is_gift", "created_at")
    search_fields = ("order_number", "email", "tracking_code", "shipping_name", "gift_note")
    inlines = [OrderItemInline, OrderEventInline]
    readonly_fields = ("order_number", "created_at", "updated_at")
    fields = (
        "order_number",
        "user",
        "email",
        "phone",
        "status",
        "tracking_code",
        "shipping_name",
        "shipping_line1",
        "shipping_line2",
        "shipping_city",
        "shipping_county",
        "shipping_postal_code",
        "shipping_country",
        "subtotal",
        "discount_amount",
        "shipping_amount",
        "tax_amount",
        "total",
        "coupon_code",
        "notes",
        "is_gift",
        "gift_note",
        "created_at",
        "updated_at",
    )