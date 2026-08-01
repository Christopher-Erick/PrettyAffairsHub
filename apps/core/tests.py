from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache, caches
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from apps.catalog.models import Product
from apps.core.middleware import CloudflareCacheMiddleware
from apps.core.smart_cache import catalog_version, get_or_set, invalidate_catalog_cache, versioned_key


class SmartCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_get_or_set_hits_cache_without_second_producer_call(self):
        calls = {"n": 0}

        def producer():
            calls["n"] += 1
            return "payload"

        self.assertEqual(get_or_set("t:key", producer), "payload")
        self.assertEqual(get_or_set("t:key", producer), "payload")
        self.assertEqual(calls["n"], 1)

    def test_product_save_bumps_catalog_version(self):
        before = catalog_version()
        Product.objects.create(name="Cache Probe Lip Oil", price="1200.00", stock=3)
        self.assertGreater(catalog_version(), before)

    def test_invalidate_changes_versioned_keys(self):
        first = versioned_key("catalog:product_list", "q=rose")
        invalidate_catalog_cache(reason="test")
        second = versioned_key("catalog:product_list", "q=rose")
        self.assertNotEqual(first, second)


class SessionResilienceTests(TestCase):
    """A dead Redis must degrade to database sessions, never a 500."""

    def setUp(self):
        User.objects.create_superuser("deskadmin", "desk@example.com", "PrettyAdmin2026!")

    @staticmethod
    def _dead_cache():
        def boom(*args, **kwargs):
            raise ConnectionError("cache unreachable")

        backend = caches["default"]
        return mock.patch.multiple(
            backend, get=boom, set=boom, delete=boom, has_key=boom, create=True
        )

    def test_admin_login_survives_a_dead_cache(self):
        with self._dead_cache():
            response = self.client.post(
                reverse("admin:login"),
                {"username": "deskadmin", "password": "PrettyAdmin2026!", "next": "/admin/"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_authenticated_page_survives_a_dead_cache(self):
        self.client.login(username="deskadmin", password="PrettyAdmin2026!")
        with self._dead_cache():
            self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)


class CloudflareCacheMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

        def get_response(request):
            from django.http import HttpResponse

            return HttpResponse("ok")  # text/html — must stay private (CSRF tokens)

        self.middleware = CloudflareCacheMiddleware(get_response)

    def test_html_pages_are_never_edge_cached(self):
        request = self.factory.get("/shop/")
        request.user = type("Anon", (), {"is_authenticated": False})()
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["CDN-Cache-Control"], "private, no-store")

    def test_cart_stays_private(self):
        request = self.factory.get("/cart/")
        request.user = type("Anon", (), {"is_authenticated": False})()
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response["Cache-Control"], "private, no-store")
