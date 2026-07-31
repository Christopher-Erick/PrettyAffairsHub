from decimal import Decimal

from django.conf import settings
from django.db import models


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
        return sum((item.line_total for item in self.items.select_related("product")), Decimal("0"))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    variant = models.ForeignKey(
        "catalog.ProductVariant", null=True, blank=True, on_delete=models.SET_NULL
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = [("cart", "product", "variant")]

    def __str__(self):
        return f"{self.product} x{self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
