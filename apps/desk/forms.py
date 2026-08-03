from django import forms

from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.content.models import (
    BlogPost,
    ContactMessage,
    FAQ,
    HomepageSection,
    SitePage,
    Testimonial,
)
from apps.core.smart_cache import get_or_set, versioned_key
from apps.discounts.models import FlashSale
from apps.orders.models import Order


def _desk_brand_choices():
    return get_or_set(
        versioned_key("desk:brand_choices"),
        lambda: [
            (b.pk, b.name)
            for b in Brand.objects.filter(is_active=True).order_by("name").only("id", "name")
        ],
    )


def _desk_category_choices():
    return get_or_set(
        versioned_key("desk:category_choices"),
        lambda: [
            (c.pk, c.name)
            for c in Category.objects.filter(is_active=True)
            .order_by("sort_order", "name")
            .only("id", "name")
        ],
    )


class ProductForm(forms.ModelForm):
    primary_image = forms.ImageField(
        required=False,
        help_text="Main photo customers see on the shop.",
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "brand",
            "categories",
            "short_description",
            "description",
            "benefits",
            "price",
            "compare_at_price",
            "stock",
            "sku",
            "is_active",
            "is_featured",
            "is_new",
            "is_bestseller",
        ]
        widgets = {
            "categories": forms.CheckboxSelectMultiple,
            "description": forms.Textarea(attrs={"rows": 5}),
            "benefits": forms.Textarea(attrs={"rows": 3}),
            "short_description": forms.TextInput(attrs={"placeholder": "One short line"}),
        }
        labels = {
            "is_active": "Show on the shop",
            "is_featured": "Featured on homepage",
            "is_new": "Mark as new",
            "is_bestseller": "Mark as bestseller",
            "compare_at_price": "Was price (optional)",
            "short_description": "Short line under the name",
            "benefits": "Benefits (one per line)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set cached choices BEFORE assigning queryset — queryset.setter syncs
        # widget.choices from field.choices, and would otherwise hit the DB.
        brand_choices = [("", "---------")] + list(_desk_brand_choices())
        category_choices = list(_desk_category_choices())
        self.fields["brand"]._choices = brand_choices
        self.fields["categories"]._choices = category_choices
        self.fields["brand"].queryset = Brand.objects.filter(is_active=True).only("id", "name")
        self.fields["categories"].queryset = Category.objects.filter(is_active=True).only("id", "name")
        for name, field in self.fields.items():
            if name in {"categories", "is_active", "is_featured", "is_new", "is_bestseller"}:
                continue
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} field".strip()


class VariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["name", "color_hex", "stock", "is_active"]
        labels = {
            "name": "Shade / option name",
            "color_hex": "Colour (#A94F5C)",
            "is_active": "Available",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "field"


class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "tracking_code", "notes"]
        labels = {
            "tracking_code": "Tracking number",
            "notes": "Internal notes",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "field", "rows": 3})
            else:
                field.widget.attrs["class"] = "field"


class HomepageSectionForm(forms.ModelForm):
    class Meta:
        model = HomepageSection
        fields = ["title", "subtitle", "body", "cta_label", "cta_url", "is_active", "sort_order"]
        labels = {"is_active": "Show on homepage", "cta_label": "Button text", "cta_url": "Button link"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == "is_active":
                continue
            field.widget.attrs["class"] = "field"


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = ["title", "excerpt", "body", "is_tutorial", "is_published"]
        labels = {
            "is_published": "Published on the Journal",
            "is_tutorial": "Mark as tutorial",
            "excerpt": "Short preview",
        }
        widgets = {"body": forms.Textarea(attrs={"rows": 10}), "excerpt": forms.TextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"is_tutorial", "is_published"}:
                continue
            field.widget.attrs["class"] = "field"


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ["question", "answer", "sort_order", "is_active"]
        labels = {"is_active": "Show on FAQ page"}
        widgets = {"answer": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "is_active":
                field.widget.attrs["class"] = "field"


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ["author_name", "quote", "rating", "is_featured", "sort_order"]
        labels = {"is_featured": "Show on homepage", "author_name": "Customer name"}
        widgets = {"quote": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "is_featured":
                field.widget.attrs["class"] = "field"


class SitePageForm(forms.ModelForm):
    class Meta:
        model = SitePage
        fields = ["title", "slug", "body", "is_published"]
        labels = {"is_published": "Published", "slug": "URL name (e.g. about)"}
        widgets = {"body": forms.Textarea(attrs={"rows": 10})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "is_published":
                field.widget.attrs["class"] = "field"


class FlashSaleForm(forms.ModelForm):
    class Meta:
        model = FlashSale
        fields = ["name", "percent_off", "starts_at", "ends_at", "is_active", "products"]
        labels = {
            "is_active": "Active",
            "percent_off": "Percent off",
            "starts_at": "Starts",
            "ends_at": "Ends",
        }
        widgets = {
            "products": forms.SelectMultiple(attrs={"size": 8, "class": "field"}),
            "starts_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "field"},
            ),
            "ends_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "field"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["products"].queryset = Product.objects.filter(is_active=True).order_by("name")
        self.fields["starts_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
        self.fields["ends_at"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
        for name, field in self.fields.items():
            if name not in {"is_active", "products", "starts_at", "ends_at"}:
                field.widget.attrs["class"] = "field"


class ContactReplyForm(forms.Form):
    reply_body = forms.CharField(
        label="Your reply",
        widget=forms.Textarea(
            attrs={
                "class": "field",
                "rows": 8,
                "placeholder": "Write a reply the customer will receive by email…",
            }
        ),
    )
