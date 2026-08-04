from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.catalog.models import Bundle, Product, ProductImage, ProductVariant
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
    BundleForm,
    BundleItemFormSet,
    ContactReplyForm,
    FAQForm,
    FlashSaleForm,
    HomepageSectionForm,
    OrderUpdateForm,
    ProductForm,
    SitePageForm,
    TestimonialForm,
    VariantForm,
    WhatsAppConfirmSaleForm,
    WhatsAppTrueEnquiryForm,
)
from apps.discounts.models import FlashSale
from apps.orders.models import Order, OrderEvent, WhatsAppLead
from apps.orders.whatsapp_leads import (
    confirm_whatsapp_sale,
    delete_false_alarm,
    mark_true_enquiry,
    pending_count,
)

@store_manager_required
def home(request):
    pending_orders = Order.objects.filter(
        status__in=[Order.STATUS_PENDING, Order.STATUS_PAID, Order.STATUS_PROCESSING]
    ).count()
    live_products = Product.objects.filter(is_active=True).count()
    low_stock = sum(1 for p in Product.objects.filter(is_active=True).prefetch_related("variants") if p.is_low_stock)
    unread = ContactMessage.objects.filter(is_handled=False).count()
    wa_pending = pending_count()
    return render(
        request,
        "desk/home.html",
        {
            "pending_orders": pending_orders,
            "live_products": live_products,
            "low_stock": low_stock,
            "unread_messages": unread,
            "wa_pending": wa_pending,
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
    q = (request.GET.get("q") or "").strip()
    kind = (request.GET.get("kind") or "all").strip().lower()
    items = BlogPost.objects.all()
    if kind == "tutorials":
        items = items.filter(is_tutorial=True)
    elif kind == "journal":
        items = items.filter(is_tutorial=False)
    if q:
        items = items.filter(
            Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(body__icontains=q)
        )
    return render(
        request,
        "desk/blog_list.html",
        {
            "items": items,
            "label": "Journal posts",
            "create_url": "desk:blog_create",
            "edit_url_name": "desk:blog_edit",
            "delete_url_name": "desk:blog_delete",
            "help": "Articles and tutorials on the Journal page.",
            "q": q,
            "kind": kind if kind in {"tutorials", "journal", "all"} else "all",
        },
    )


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


@store_manager_required
def bundle_list(request):
    q = (request.GET.get("q") or "").strip()
    show = (request.GET.get("show") or "all").strip().lower()
    bundles = Bundle.objects.prefetch_related("items").order_by("name")
    if q:
        bundles = bundles.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if show == "live":
        bundles = bundles.filter(is_active=True)
    elif show == "hidden":
        bundles = bundles.filter(is_active=False)
    return render(
        request,
        "desk/bundle_list.html",
        {
            "bundles": bundles,
            "q": q,
            "show": show,
        },
    )


def _save_bundle(request, bundle=None):
    form = BundleForm(request.POST or None, instance=bundle)
    formset = BundleItemFormSet(request.POST or None, instance=bundle)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        obj = form.save()
        formset.instance = obj
        formset.save()
        messages.success(request, f"Saved bundle “{obj.name}”.")
        return redirect("desk:bundle_edit", pk=obj.pk), None, None
    return None, form, formset


@store_manager_required
def bundle_create(request):
    redirect_response, form, formset = _save_bundle(request)
    if redirect_response:
        return redirect_response
    return render(
        request,
        "desk/bundle_form.html",
        {"form": form, "formset": formset, "bundle": None},
    )


@store_manager_required
def bundle_edit(request, pk):
    bundle = get_object_or_404(
        Bundle.objects.prefetch_related("items__product"),
        pk=pk,
    )
    redirect_response, form, formset = _save_bundle(request, bundle)
    if redirect_response:
        return redirect_response
    return render(
        request,
        "desk/bundle_form.html",
        {
            "form": form,
            "formset": formset,
            "bundle": bundle,
            "delete_url": reverse("desk:bundle_delete", args=[pk]),
        },
    )


@store_manager_required
@require_POST
def bundle_suggest(request):
    """Create a draft bundle: 2 hot sellers + 1 slower complementary lift."""
    from apps.catalog.bundle_suggest import suggest_hot_and_slow_trio
    from apps.catalog.models import BundleItem

    suggestion = suggest_hot_and_slow_trio()
    products = suggestion.get("products") or []
    if len(products) < 2:
        messages.error(request, "Need more in-stock products before we can suggest a bundle.")
        return redirect("desk:bundle_list")

    bundle = Bundle.objects.create(
        name=suggestion["name"],
        description="\n".join(suggestion.get("reasons") or []),
        price=suggestion["price"],
        compare_at_price=suggestion.get("compare_at"),
        is_active=False,
    )
    for product in products:
        BundleItem.objects.create(bundle=bundle, product=product, quantity=1)

    messages.success(
        request,
        "Draft bundle suggested (hidden). Review the products and price, then set it live.",
    )
    return redirect("desk:bundle_edit", pk=bundle.pk)


@store_manager_required
@require_POST
def bundle_delete(request, pk):
    bundle = get_object_or_404(Bundle, pk=pk)
    name = bundle.name
    bundle.delete()
    messages.success(request, f"Deleted bundle “{name}”.")
    return redirect("desk:bundle_list")


@store_manager_required
def whatsapp_lead_list(request):
    show = (request.GET.get("show") or "pending").strip().lower()
    leads = WhatsAppLead.objects.select_related("user", "handled_by")
    if show == "enquiry":
        leads = leads.filter(status=WhatsAppLead.STATUS_TRUE_ENQUIRY)
    else:
        show = "pending"
        leads = leads.filter(status=WhatsAppLead.STATUS_PENDING)
    return render(
        request,
        "desk/whatsapp_lead_list.html",
        {
            "leads": leads[:100],
            "show": show,
            "pending_count": pending_count(),
        },
    )


@store_manager_required
def whatsapp_lead_detail(request, pk):
    lead = get_object_or_404(
        WhatsAppLead.objects.select_related("user", "handled_by"),
        pk=pk,
    )
    is_pending = lead.status == WhatsAppLead.STATUS_PENDING
    sale_form = WhatsAppConfirmSaleForm(
        initial={
            "shipping_name": (
                lead.user.get_full_name()
                if lead.user_id and lead.user.get_full_name()
                else ""
            ),
            "email": lead.user.email if lead.user_id and lead.user.email else "",
        }
    )
    enquiry_form = WhatsAppTrueEnquiryForm()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "false_alarm":
            if not is_pending:
                messages.error(request, "Only awaiting leads can be cleared as false alarms.")
            else:
                delete_false_alarm(lead)
                messages.success(
                    request,
                    "False alarm deleted — removed from the queue.",
                )
            return redirect("desk:whatsapp_lead_list")

        if action == "true_enquiry":
            if not is_pending:
                messages.error(request, "Only awaiting leads can be saved as true enquiries.")
                return redirect("desk:whatsapp_lead_detail", pk=pk)
            enquiry_form = WhatsAppTrueEnquiryForm(request.POST)
            if enquiry_form.is_valid():
                mark_true_enquiry(
                    lead,
                    manager=request.user,
                    note=enquiry_form.cleaned_data.get("manager_note") or "",
                )
                messages.success(
                    request,
                    "Marked as a true enquiry. Kept for history — not counted as a sale.",
                )
                return redirect("desk:whatsapp_lead_list")
            messages.error(request, "Could not save the enquiry note.")

        elif action == "confirm_sale":
            if lead.status not in {
                WhatsAppLead.STATUS_PENDING,
                WhatsAppLead.STATUS_TRUE_ENQUIRY,
            }:
                messages.error(request, "This lead cannot be confirmed as a sale.")
                return redirect("desk:whatsapp_lead_list")
            sale_form = WhatsAppConfirmSaleForm(request.POST)
            if sale_form.is_valid():
                try:
                    order = confirm_whatsapp_sale(
                        lead,
                        manager=request.user,
                        cleaned_data=sale_form.cleaned_data,
                    )
                except ValueError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request,
                        f"WhatsApp sale confirmed as {order.order_number}. "
                        "Saved as an order — counts for ritual and bundles.",
                    )
                    return redirect("desk:order_detail", order_number=order.order_number)
            else:
                messages.error(request, "Check the sale details and try again.")

    return render(
        request,
        "desk/whatsapp_lead_detail.html",
        {
            "lead": lead,
            "is_pending": is_pending,
            "created_at": lead.created_at,
            "sale_form": sale_form,
            "enquiry_form": enquiry_form,
            "items": lead.items_json or [],
        },
    )
