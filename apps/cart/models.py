from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="carts",
        on_delete=models.CASCADE,
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    coupon_code = models.CharField(max_length=40, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    abandoned_email_sent = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["session_key"])]

    def __str__(self):
        owner = self.user or self.session_key or "anon"
        return f"Cart {self.pk} ({owner})"

    @property
    def subtotal(self):
        return sum(
            (item.line_total for item in self.items.select_related("product", "bundle")),
            Decimal("0"),
        )

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        "catalog.Product", null=True, blank=True, on_delete=models.CASCADE
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, on_delete=models.SET_NULL
    )
    bundle = models.ForeignKey(
        "catalog.Bundle", null=True, blank=True, on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(bundle__isnull=False, product__isnull=True)
                    | Q(bundle__isnull=True, product__isnull=False)
                ),
                name="cartitem_product_xor_bundle",
            ),
            models.UniqueConstraint(
                fields=["cart", "product", "variant"],
                condition=Q(bundle__isnull=True),
                name="uniq_cart_product_variant",
            ),
            models.UniqueConstraint(
                fields=["cart", "bundle"],
                condition=Q(bundle__isnull=False),
                name="uniq_cart_bundle",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} x{self.quantity}"

    @property
    def is_bundle(self):
        return self.bundle_id is not None

    @property
    def display_name(self):
        if self.bundle_id:
            return self.bundle.name
        return self.product.name if self.product_id else "Item"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def includes_label(self):
        if not self.bundle_id:
            return ""
        names = [bi.product.name for bi in self.bundle.items.all()]
        return "Includes: " + " · ".join(names)
