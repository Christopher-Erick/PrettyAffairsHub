from django.core.cache import cache
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


class CloudflareCacheMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

        def get_response(request):
            from django.http import HttpResponse

            return HttpResponse("ok")

        self.middleware = CloudflareCacheMiddleware(get_response)

    def test_public_shop_gets_edge_cache_headers(self):
        request = self.factory.get("/shop/")
        request.user = type("Anon", (), {"is_authenticated": False})()
        request.session = {}
        response = self.middleware(request)
        self.assertIn("s-maxage=86400", response["Cache-Control"])
        self.assertEqual(response["CDN-Cache-Control"], "public, max-age=86400")

    def test_cart_stays_private(self):
        request = self.factory.get("/cart/")
        request.user = type("Anon", (), {"is_authenticated": False})()
        request.session = {}
        response = self.middleware(request)
        self.assertEqual(response["Cache-Control"], "private, no-store")
