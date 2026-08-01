from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalog.models import Product
from apps.orders.models import Order


class OrderAccessTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Access Test Lip Oil",
            price=Decimal("1500.00"),
            stock=10,
            is_active=True,
        )
        self.owner = User.objects.create_user("buyer", "buyer@example.com", "PrettyBuyer2026!")
        self.other = User.objects.create_user("other", "other@example.com", "PrettyOther2026!")
        self.order = Order.objects.create(
            user=self.owner,
            email="buyer@example.com",
            phone="0712345678",
            shipping_name="Buyer",
            shipping_line1="1 Test Street",
            shipping_city="Nairobi",
            shipping_country="Kenya",
            subtotal=Decimal("1500.00"),
            total=Decimal("1800.00"),
        )
        self.guest_order = Order.objects.create(
            user=None,
            email="guest@example.com",
            phone="0700000000",
            shipping_name="Guest",
            shipping_line1="2 Guest Lane",
            shipping_city="Nairobi",
            shipping_country="Kenya",
            subtotal=Decimal("1500.00"),
            total=Decimal("1800.00"),
        )

    def test_stranger_cannot_open_confirmation(self):
        response = self.client.get(
            reverse("orders:confirmation", args=[self.order.order_number])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("orders:track"))

    def test_owner_can_open_confirmation(self):
        self.client.login(username="buyer", password="PrettyBuyer2026!")
        response = self.client.get(
            reverse("orders:confirmation", args=[self.order.order_number])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_other_user_cannot_open_owner_confirmation(self):
        self.client.login(username="other", password="PrettyOther2026!")
        response = self.client.get(
            reverse("orders:confirmation", args=[self.order.order_number])
        )
        self.assertEqual(response.status_code, 302)

    def test_session_grant_allows_guest_confirmation(self):
        session = self.client.session
        from apps.orders.services import ORDER_CONFIRMATION_SESSION_KEY

        session[ORDER_CONFIRMATION_SESSION_KEY] = [self.guest_order.order_number]
        session.save()
        response = self.client.get(
            reverse("orders:confirmation", args=[self.guest_order.order_number])
        )
        self.assertEqual(response.status_code, 200)

    def test_anonymous_cannot_open_guest_confirmation_without_grant(self):
        response = self.client.get(
            reverse("orders:confirmation", args=[self.guest_order.order_number])
        )
        self.assertEqual(response.status_code, 302)


class OpenRedirectTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Redirect Probe Serum",
            price=Decimal("2000.00"),
            stock=5,
            is_active=True,
        )

    def test_cart_add_rejects_external_next(self):
        response = self.client.post(
            reverse("cart:add"),
            {
                "product_id": self.product.id,
                "quantity": 1,
                "next": "https://evil.example/phish",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("cart:detail"))

    def test_cart_add_allows_same_host_next(self):
        response = self.client.post(
            reverse("cart:add"),
            {
                "product_id": self.product.id,
                "quantity": 1,
                "next": "/shop/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/shop/")


class DeskAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_superuser(
            "deskstaff", "desk@example.com", "PrettyAdmin2026!"
        )
        self.client_user = User.objects.create_user(
            "shopper", "shopper@example.com", "PrettyClient2026!"
        )

    def test_anonymous_manage_redirects_to_login(self):
        response = self.client.get(reverse("desk:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_client_cannot_open_manage(self):
        self.client.login(username="shopper", password="PrettyClient2026!")
        response = self.client.get(reverse("desk:home"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_open_manage(self):
        self.client.login(username="deskstaff", password="PrettyAdmin2026!")
        response = self.client.get(reverse("desk:home"))
        self.assertEqual(response.status_code, 200)

    def test_logout_requires_post(self):
        self.client.login(username="deskstaff", password="PrettyAdmin2026!")
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
