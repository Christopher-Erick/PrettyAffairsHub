from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.catalog.models import Product, ProductImage, ProductVariant
from apps.content.models import (
    BlogPost,
    ContactMessage,
    FAQ,
    HomepageSection,
    SitePage,
    Testimonial,
)
from apps.desk.decorators import store_manager_required
from apps.desk.forms import (
    BlogPostForm,
    ContactReplyForm,
    FAQForm,
    FlashSaleForm,
    HomepageSectionForm,
    OrderUpdateForm,
    ProductForm,
    SitePageForm,
    TestimonialForm,
    VariantForm,
)
from apps.discounts.models import FlashSale
from apps.orders.models import Order, OrderEvent


@store_manager_required
def home(request):
    pending_orders = Order.objects.filter(
        status__in=[Order.STATUS_PENDING, Order.STATUS_PAID, Order.STATUS_PROCESSING]
    ).count()
    live_products = Product.objects.filter(is_active=True).count()
    low_stock = sum(1 for p in Product.objects.filter(is_active=True).prefetch_related("variants") if p.is_low_stock)
    unread = ContactMessage.objects.filter(is_handled=False).count()
    return render(
        request,
        "desk/home.html",
        {
            "pending_orders": pending_orders,
            "live_products": live_products,
            "low_stock": low_stock,
            "unread_messages": unread,
        },
    )


@store_manager_required
def product_list(request):
    from django.core.paginator import Paginator
    from django.db.models import Prefetch

    from apps.catalog.models import ProductImage

    q = request.GET.get("q", "").strip()
    show = request.GET.get("show", "all")
    # Slim rows for the table — first image + variant stock only.
    products = (
        Product.objects.only(
            "id",
            "name",
            "slug",
            "sku",
            "price",
            "stock",
            "is_active",
            "updated_at",
        )
        .prefetch_related(
            Prefetch(
                "images",
                queryset=ProductImage.objects.order_by("sort_order", "id").only(
                    "id", "product_id", "image", "sort_order"
                ),
            ),
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.only(
                    "id", "product_id", "stock", "is_active"
                ),
            ),
        )
        .order_by("-updated_at")
    )
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if show == "live":
        products = products.filter(is_active=True)
    elif show == "hidden":
        products = products.filter(is_active=False)
    paginator = Paginator(products, 40)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "desk/product_list.html",
        {
            "products": page_obj,
            "page_obj": page_obj,
            "q": q,
            "show": show,
        },
    )


def _save_product(request, product=None):
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        image = form.cleaned_data.get("primary_image")
        if image:
            ProductImage.objects.create(product=obj, image=image, alt_text=obj.name, sort_order=0)
        messages.success(request, f"Saved “{obj.name}”. It will show on the shop when active.")
        return redirect("desk:product_edit", pk=obj.pk)
    return form


@store_manager_required
def product_create(request):
    form = _save_product(request)
    if not isinstance(form, ProductForm):
        return form
    return render(request, "desk/product_form.html", {"form": form, "product": None, "variants": []})


@store_manager_required
def product_edit(request, pk):
    from django.db.models import Prefetch

    product = get_object_or_404(
        Product.objects.select_related("brand").prefetch_related(
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.only(
                    "id", "product_id", "name", "color_hex", "stock", "is_active"
                ).order_by("id"),
            ),
            "categories",
        ),
        pk=pk,
    )
    form = _save_product(request, product)
    if not isinstance(form, ProductForm):
        return form
    variant_form = VariantForm()
    return render(
        request,
        "desk/product_form.html",
        {
            "form": form,
            "product": product,
            "variants": product.variants.all(),
            "variant_form": variant_form,
        },
    )


@store_manager_required
@require_POST
def variant_add(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = VariantForm(request.POST)
    if form.is_valid():
        variant = form.save(commit=False)
        variant.product = product
        if not variant.sku:
            variant.sku = f"{product.sku or slugify(product.name)[:12].upper()}-{slugify(variant.name)[:10].upper()}"
        variant.save()
        messages.success(request, f"Added shade “{variant.name}”.")
    else:
        messages.error(request, "Could not add that shade — check the fields.")
    return redirect("desk:product_edit", pk=pk)


@store_manager_required
@require_POST
def variant_delete(request, pk, variant_id):
    product = get_object_or_404(Product, pk=pk)
    variant = get_object_or_404(ProductVariant, pk=variant_id, product=product)
    name = variant.name
    variant.delete()
    messages.success(request, f"Removed shade “{name}”.")
    return redirect("desk:product_edit", pk=pk)


@store_manager_required
def order_list(request):
    status = request.GET.get("status", "")
    orders = Order.objects.all()
    if status:
        orders = orders.filter(status=status)
    return render(
        request,
        "desk/order_list.html",
        {"orders": orders[:100], "status": status, "status_choices": Order.STATUS_CHOICES},
    )


@store_manager_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related("items", "events"), order_number=order_number)
    form = OrderUpdateForm(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid():
        old_status = order.status
        updated = form.save()
        if updated.status != old_status:
            OrderEvent.objects.create(
                order=updated,
                status=updated.status,
                note=f"Status updated by {request.user.get_username()}",
            )
        messages.success(request, f"Order {updated.order_number} updated.")
        return redirect("desk:order_detail", order_number=updated.order_number)
    return render(request, "desk/order_detail.html", {"order": order, "form": form})


@store_manager_required
def content_hub(request):
    return render(
        request,
        "desk/content_hub.html",
        {
            "sections": HomepageSection.objects.count(),
            "posts": BlogPost.objects.count(),
            "faqs": FAQ.objects.count(),
            "testimonials": Testimonial.objects.count(),
            "pages": SitePage.objects.count(),
            "flash_sales": FlashSale.objects.count(),
        },
    )


@store_manager_required
def section_list(request):
    return render(request, "desk/generic_list.html", {
        "items": HomepageSection.objects.all(),
        "label": "Homepage sections",
        "create_url": "desk:section_create",
        "edit_url_name": "desk:section_edit",
        "delete_url_name": "desk:section_delete",
        "help": "Titles and text blocks on the homepage.",
        "display": "title",
    })


@store_manager_required
def section_create(request):
    form = HomepageSectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if not getattr(obj, "key", None):
            base = slugify(obj.title)[:40] or "section"
            key = base
            n = 1
            while HomepageSection.objects.filter(key=key).exists():
                n += 1
                key = f"{base}-{n}"
            obj.key = key
        obj.save()
        messages.success(request, "Homepage section saved.")
        return redirect("desk:section_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "New homepage section", "back": "desk:section_list"})


@store_manager_required
def section_edit(request, pk):
    obj = get_object_or_404(HomepageSection, pk=pk)
    form = HomepageSectionForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Homepage section updated.")
        return redirect("desk:section_list")
    return render(
        request,
        "desk/generic_form.html",
        {
            "form": form,
            "label": "Edit homepage section",
            "back": "desk:section_list",
            "delete_url": reverse("desk:section_delete", args=[pk]),
            "object_name": obj.title,
        },
    )


@store_manager_required
@require_POST
def section_delete(request, pk):
    obj = get_object_or_404(HomepageSection, pk=pk)
    title = obj.title
    obj.delete()
    messages.success(request, f"Deleted homepage section “{title}”.")
    return redirect("desk:section_list")


@store_manager_required
def blog_list(request):
    return render(request, "desk/generic_list.html", {
        "items": BlogPost.objects.all(),
        "label": "Journal posts",
        "create_url": "desk:blog_create",
        "edit_url_name": "desk:blog_edit",
        "delete_url_name": "desk:blog_delete",
        "help": "Articles and tutorials on the Journal page.",
        "display": "title",
    })


@store_manager_required
def blog_create(request):
    form = BlogPostForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Journal post saved.")
        return redirect("desk:blog_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "New journal post", "back": "desk:blog_list"})


@store_manager_required
def blog_edit(request, pk):
    obj = get_object_or_404(BlogPost, pk=pk)
    form = BlogPostForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Journal post updated.")
        return redirect("desk:blog_list")
    return render(
        request,
        "desk/generic_form.html",
        {
            "form": form,
            "label": "Edit journal post",
            "back": "desk:blog_list",
            "delete_url": reverse("desk:blog_delete", args=[pk]),
            "object_name": obj.title,
        },
    )


@store_manager_required
@require_POST
def blog_delete(request, pk):
    obj = get_object_or_404(BlogPost, pk=pk)
    title = obj.title
    obj.delete()
    messages.success(request, f"Deleted journal post “{title}”.")
    return redirect("desk:blog_list")


@store_manager_required
def faq_list(request):
    return render(request, "desk/generic_list.html", {
        "items": FAQ.objects.all(),
        "label": "FAQs",
        "create_url": "desk:faq_create",
        "edit_url_name": "desk:faq_edit",
        "help": "Questions customers see on the FAQ page.",
        "display": "question",
    })


@store_manager_required
def faq_create(request):
    form = FAQForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "FAQ saved.")
        return redirect("desk:faq_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "New FAQ", "back": "desk:faq_list"})


@store_manager_required
def faq_edit(request, pk):
    obj = get_object_or_404(FAQ, pk=pk)
    form = FAQForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "FAQ updated.")
        return redirect("desk:faq_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "Edit FAQ", "back": "desk:faq_list"})


@store_manager_required
def testimonial_list(request):
    return render(request, "desk/generic_list.html", {
        "items": Testimonial.objects.all(),
        "label": "Customer quotes",
        "create_url": "desk:testimonial_create",
        "edit_url_name": "desk:testimonial_edit",
        "help": "Kind words shown on the homepage.",
        "display": "author_name",
    })


@store_manager_required
def testimonial_create(request):
    form = TestimonialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Quote saved.")
        return redirect("desk:testimonial_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "New customer quote", "back": "desk:testimonial_list"})


@store_manager_required
def testimonial_edit(request, pk):
    obj = get_object_or_404(Testimonial, pk=pk)
    form = TestimonialForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Quote updated.")
        return redirect("desk:testimonial_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "Edit customer quote", "back": "desk:testimonial_list"})


@store_manager_required
def page_list(request):
    return render(request, "desk/generic_list.html", {
        "items": SitePage.objects.all(),
        "label": "Site pages",
        "create_url": "desk:page_create",
        "edit_url_name": "desk:page_edit",
        "help": "About and other static pages.",
        "display": "title",
    })


@store_manager_required
def page_create(request):
    form = SitePageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Page saved.")
        return redirect("desk:page_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "New site page", "back": "desk:page_list"})


@store_manager_required
def page_edit(request, pk):
    obj = get_object_or_404(SitePage, pk=pk)
    form = SitePageForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Page updated.")
        return redirect("desk:page_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "Edit site page", "back": "desk:page_list"})


@store_manager_required
def flash_list(request):
    return render(request, "desk/generic_list.html", {
        "items": FlashSale.objects.all(),
        "label": "Flash sales",
        "create_url": "desk:flash_create",
        "edit_url_name": "desk:flash_edit",
        "help": "Limited-time offers shown on the homepage.",
        "display": "name",
    })


@store_manager_required
def flash_create(request):
    form = FlashSaleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Flash sale saved.")
        return redirect("desk:flash_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "New flash sale", "back": "desk:flash_list"})


@store_manager_required
def flash_edit(request, pk):
    obj = get_object_or_404(FlashSale, pk=pk)
    form = FlashSaleForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Flash sale updated.")
        return redirect("desk:flash_list")
    return render(request, "desk/generic_form.html", {"form": form, "label": "Edit flash sale", "back": "desk:flash_list"})


@store_manager_required
def message_list(request):
    items = ContactMessage.objects.all()[:100]
    return render(request, "desk/message_list.html", {"items": items})


@store_manager_required
def message_detail(request, pk):
    """Admins / store managers: Reply (email + handled) or Not reply (unhandled)."""
    obj = get_object_or_404(ContactMessage, pk=pk)
    reply_form = ContactReplyForm(initial={"reply_body": obj.reply_body})
    show_reply_form = request.GET.get("mode") == "reply"

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "reply":
            show_reply_form = True
            reply_form = ContactReplyForm(request.POST)
            if reply_form.is_valid():
                from smtplib import SMTPException

                from django.core.mail import BadHeaderError

                from apps.content.services import send_contact_reply

                try:
                    send_contact_reply(
                        obj,
                        reply_form.cleaned_data["reply_body"],
                        staff_user=request.user,
                    )
                except (BadHeaderError, SMTPException, OSError, ValueError, RuntimeError) as exc:
                    messages.error(
                        request,
                        f"Could not send the reply email. {exc}",
                    )
                else:
                    messages.success(
                        request,
                        f"Reply sent to {obj.email}. Marked as handled.",
                    )
                    return redirect("desk:message_detail", pk=obj.pk)
        elif action == "not_reply":
            obj.is_handled = False
            obj.save(update_fields=["is_handled"])
            messages.success(
                request,
                "Marked as not handled. No reply was sent.",
            )
            return redirect("desk:message_list")

    return render(
        request,
        "desk/message_detail.html",
        {
            "item": obj,
            "reply_form": reply_form,
            "show_reply_form": show_reply_form or bool(reply_form.errors),
        },
    )
