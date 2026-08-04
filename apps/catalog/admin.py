from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Brand,
    Bundle,
    BundleItem,
    Category,
    Collection,
    Product,
    ProductImage,
    ProductRelation,
    ProductVariant,
)

admin.site.site_header = "Pretty Affairs Hub"
admin.site.site_title = "Pretty Affairs Hub admin"
admin.site.index_title = "Catalogue & store operations"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("preview", "image", "alt_text", "sort_order")
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" alt="" style="width:56px;height:56px;object-fit:cover;border-radius:8px;" />',
                obj.image.url,
            )
        return "—"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("swatch", "name", "color_hex", "image", "sku", "price_override", "stock", "is_active")
    readonly_fields = ("swatch",)

    @admin.display(description="Swatch")
    def swatch(self, obj):
        color = obj.color_hex or "#C9A39A"
        return format_html(
            '<span style="display:inline-block;width:1.25rem;height:1.25rem;border-radius:50%;'
            'background:{};box-shadow:inset 0 0 0 1px rgba(0,0,0,.25);" title="{}"></span>',
            color,
            color,
        )


class BundleItemInline(admin.TabularInline):
    model = BundleItem
    extra = 3
    min_num = 3
    max_num = 3
    validate_min = True
    validate_max = True
    autocomplete_fields = ("product",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_editable = ("is_active",)
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("parent",)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_featured", "is_active")
    list_editable = ("is_featured", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",
        "name",
        "brand",
        "price",
        "stock",
        "is_active",
        "is_featured",
        "is_bestseller",
        "average_rating",
        "source_name",
    )
    list_display_links = ("thumb", "name")
    list_editable = ("price", "stock", "is_active", "is_featured", "is_bestseller")
    list_filter = (
        "is_active",
        "is_featured",
        "is_new",
        "is_bestseller",
        "is_trending",
        "is_limited_offer",
        "brand",
        "categories",
        "source_name",
    )
    search_fields = ("name", "sku", "short_description", "source_name", "source_url", "variants__name")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("categories", "collections")
    autocomplete_fields = ("brand",)
    inlines = [ProductImageInline, ProductVariantInline]
    save_on_top = True
    list_per_page = 40
    readonly_fields = ("average_rating", "review_count", "created_at", "updated_at")
    fieldsets = (
        (
            "Basics",
            {
                "fields": (
                    "name",
                    "slug",
                    "brand",
                    "categories",
                    "collections",
                    "is_active",
                )
            },
        ),
        (
            "Copy customers see",
            {
                "fields": (
                    "short_description",
                    "description",
                    "benefits",
                    "directions",
                    "ingredients",
                    "specifications",
                ),
                "description": "Benefits: one line per bullet. These show on the product page and cards.",
            },
        ),
        (
            "Pricing & stock",
            {"fields": ("price", "compare_at_price", "sku", "stock")},
        ),
        (
            "Merchandising flags",
            {
                "fields": (
                    "is_featured",
                    "is_new",
                    "is_bestseller",
                    "is_trending",
                    "is_limited_offer",
                )
            },
        ),
        (
            "Source & ratings",
            {
                "classes": ("collapse",),
                "fields": (
                    "source_name",
                    "source_url",
                    "average_rating",
                    "review_count",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    @admin.display(description="")
    def thumb(self, obj):
        image = obj.primary_image
        if image and image.image:
            return format_html(
                '<img src="{}" alt="" style="width:40px;height:40px;object-fit:cover;border-radius:6px;" />',
                image.image.url,
            )
        return "—"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("brand").prefetch_related("images", "variants")

    def save_formset(self, request, form, formset, change):
        """Auto-fill blank shade colours from the shade name when possible."""
        instances = formset.save(commit=False)
        if formset.model is ProductVariant:
            from apps.catalog.shade_colors import resolve_shade_color

            for instance in instances:
                if not instance.color_hex:
                    instance.color_hex = resolve_shade_color(instance.name, instance.image or None)
                instance.save()
            formset.save_m2m()
            for obj in formset.deleted_objects:
                obj.delete()
            return
        super().save_formset(request, form, formset, change)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("swatch", "product", "name", "color_hex", "stock", "is_active", "price_override")
    list_editable = ("color_hex", "stock", "is_active", "price_override")
    list_filter = ("is_active", "product__categories")
    search_fields = ("name", "sku", "product__name", "color_hex")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)

    @admin.display(description="")
    def swatch(self, obj):
        color = obj.color_hex or "#C9A39A"
        return format_html(
            '<span style="display:inline-block;width:1.1rem;height:1.1rem;border-radius:50%;'
            'background:{};box-shadow:inset 0 0 0 1px rgba(0,0,0,.25);"></span>',
            color,
        )


@admin.register(ProductRelation)
class ProductRelationAdmin(admin.ModelAdmin):
    list_display = ("from_product", "to_product", "relation_type")
    list_filter = ("relation_type",)
    autocomplete_fields = ("from_product", "to_product")


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active")
    list_editable = ("price", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = [BundleItemInline]
    save_on_top = True
