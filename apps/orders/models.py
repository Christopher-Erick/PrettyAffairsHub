import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    CHANNEL_WEBSITE = "website"
    CHANNEL_WHATSAPP = "whatsapp"
    CHANNEL_CHOICES = [
        (CHANNEL_WEBSITE, "Website checkout"),
        (CHANNEL_WHATSAPP, "WhatsApp"),
    ]

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="orders",
        on_delete=models.SET_NULL,
    )
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default=CHANNEL_WEBSITE,
        db_index=True,
    )
    tracking_code = models.CharField(max_length=64, blank=True)
    shipping_name = models.CharField(max_length=120)
    shipping_line1 = models.CharField(max_length=200)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_county = models.CharField(max_length=100, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=60, default="Kenya")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    coupon_code = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    is_gift = models.BooleanField(default=False)
    gift_note = models.TextField(blank=True, help_text="Message printed for gift orders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"PAH-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.SET_NULL
    )
    bundle = models.ForeignKey(
        "catalog.Bundle", null=True, blank=True, on_delete=models.SET_NULL
    )
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=120, blank=True)
    sku = models.CharField(max_length=64, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    @property
    def is_bundle(self):
        return bool(self.bundle_id) or self.sku.startswith("BUNDLE:")


class OrderEvent(models.Model):
    order = models.ForeignKey(Order, related_name="events", on_delete=models.CASCADE)
    status = models.CharField(max_length=20)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.status}"

    @property
    def status_label(self):
        return dict(Order.STATUS_CHOICES).get(self.status, self.status.replace("_", " ").title())


class WhatsAppLead(models.Model):
    """WhatsApp cart queue for manager triage.

    - pending: awaiting review (work queue, not a sale)
    - true_enquiry: manager confirmed real engagement, no sale
    Sales become Order rows; false alarms delete the pending row.
    """

    STATUS_PENDING = "pending"
    STATUS_TRUE_ENQUIRY = "true_enquiry"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Awaiting review"),
        (STATUS_TRUE_ENQUIRY, "True enquiry"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="whatsapp_leads",
        on_delete=models.SET_NULL,
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    fingerprint = models.CharField(max_length=64, db_index=True)
    items_json = models.JSONField(default=list)
    item_count = models.PositiveIntegerField(default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    message_preview = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    manager_note = models.TextField(blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="handled_whatsapp_leads",
        on_delete=models.SET_NULL,
    )
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"WA lead #{self.pk} ({self.status})"
