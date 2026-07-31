from django.contrib import admin

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


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class BundleItemInline(admin.TabularInline):
    model = BundleItem
    extra = 1


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_active", "sort_order")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "is_featured", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "stock",
        "is_active",
        "is_featured",
        "is_bestseller",
        "average_rating",
        "source_name",
    )
    list_filter = (
        "is_active",
        "is_featured",
        "is_new",
        "is_bestseller",
        "is_trending",
        "is_limited_offer",
        "brand",
        "categories",
    )
    search_fields = ("name", "sku", "source_name", "source_url")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("categories", "collections")
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(ProductRelation)
class ProductRelationAdmin(admin.ModelAdmin):
    list_display = ("from_product", "to_product", "relation_type")
    list_filter = ("relation_type",)


@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [BundleItemInline]
