from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.discounts.models import GiftCard


class GiftCardPageTests(TestCase):
    def setUp(self):
        GiftCard.objects.create(
            code="PAH-SECRET-CODE",
            initial_balance=Decimal("5000.00"),
            current_balance=Decimal("4200.00"),
        )

    def test_issued_gift_cards_are_not_exposed_to_shoppers(self):
        response = self.client.get(reverse("content:gift_cards"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "PAH-SECRET-CODE")
        self.assertNotContains(response, "4200")

    def test_page_has_no_admin_jargon(self):
        response = self.client.get(reverse("content:gift_cards"))

        self.assertNotContains(response, "Django Admin")
        self.assertNotContains(response, "in-store / admin")
