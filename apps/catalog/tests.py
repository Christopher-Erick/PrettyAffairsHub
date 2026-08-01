from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.catalog.management.commands.import_authorized_catalog import (
    category_for,
    feed_b_category,
)
from apps.catalog.models import Product


class ProductDetailPageTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Statement Lip Colour",
            short_description="Rich payoff and a refined finish.",
            description="A statement lip colour selected for rich payoff.",
            benefits="Buildable colour\nComfortable wear\nDefined finish",
            directions="Apply from the centre outward.",
            ingredients="Selected cosmetic ingredients.",
            specifications="3.5 g",
            price="2500.00",
            stock=5,
        )

    def test_product_information_is_rendered_once_in_right_column(self):
        response = self.client.get(
            reverse("catalog:product_detail", kwargs={"slug": self.product.slug})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<h2>Description</h2>", count=1, html=True)
        self.assertContains(response, "<h2>Benefits</h2>", count=1, html=True)
        self.assertContains(response, "<h2>Directions</h2>", count=1, html=True)
        self.assertContains(response, "<li>Buildable colour</li>", html=True)
        self.assertContains(response, "<li>Comfortable wear</li>", html=True)
        self.assertContains(response, "<li>Defined finish</li>", html=True)

        content = response.content.decode()
        info_start = content.index('<div class="pdp__info">')
        info_end = content.index("</article>")
        details_start = content.index('<div class="pdp__details">')
        self.assertLess(info_start, details_start)
        self.assertLess(details_start, info_end)
        self.assertGreater(
            content.index('<h2 class="section__title">Ingredients</h2>'),
            info_end,
        )


class InternalCatalogDataTests(TestCase):
    """Sourcing and stock-keeping fields are operational data, not shopper copy."""

    def setUp(self):
        self.product = Product.objects.create(
            name="Velvet Lip Oil",
            price="1800.00",
            stock=4,
            sku="PAH-LIPS-A1B2C3D",
            source_name="Atelier Edit",
            source_url="https://example.com/products/velvet-lip-oil",
        )

    def assert_no_internal_fields(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.product.sku)
        self.assertNotContains(response, self.product.source_name)
        self.assertNotContains(response, "example.com/products/velvet-lip-oil")

    def test_product_detail_hides_source_and_sku(self):
        self.assert_no_internal_fields(
            self.client.get(
                reverse("catalog:product_detail", kwargs={"slug": self.product.slug})
            )
        )

    def test_shop_listing_hides_source_and_sku(self):
        self.assert_no_internal_fields(self.client.get(reverse("catalog:shop")))

    def test_shop_empty_state_avoids_importer_jargon(self):
        response = self.client.get(reverse("catalog:shop"), {"q": "zzzzzznomatch"})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "authorized")

    def test_shop_search_appears_before_category_rails(self):
        response = self.client.get(reverse("catalog:shop"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        search_index = content.index('role="search"')
        for marker in ("shop-mood-rail", "shade-studio"):
            if marker in content:
                self.assertLess(search_index, content.index(marker))
                break
        else:
            self.assertIn('class="shop-search"', content)


class CategoryRuleTests(SimpleTestCase):
    """A product's form decides its category; a shared scent line never does."""

    def test_body_lotions_are_skipped(self):
        self.assertIsNone(
            feed_b_category("Jeanne En Provence Rose Envoutante Body Lotion 200ml")
        )

    def test_hand_cream_and_body_wash_resolve_to_body_care(self):
        cases = {
            "Jeanne En Provence Jasmin Secret Hand Cream 75ml": "Body & Hand Care",
            "Jeanne En Provence Orange Blossom Shower Oil 250ml": "Body & Hand Care",
            "eos Shea Better Cashmere Body Wash Vanilla Cashmere": "Body & Hand Care",
            "Dove Shea Butter Warm Vanilla Body Wash 500ml": "Body & Hand Care",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(feed_b_category(title), expected)

    def test_fragrance_forms_still_resolve(self):
        cases = {
            "Jeanne En Provence Jasmin Secret Eau De Parfum 60ml": "Perfumes",
            "Versace Eros Najim Parfum 100ml": "Perfumes",
            "Jeanne Arthes Sultan Men Oud Eau De Toilette 100ml": "Cologne",
            "Orange Blossom Body Mist 250ml": "Body Splash",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(feed_b_category(title), expected)

    def test_scent_line_name_alone_falls_back_to_perfume(self):
        self.assertEqual(feed_b_category("Gucci Bloom Ambrosia dOro 100ml"), "Perfumes")

    def test_lip_products_are_unaffected(self):
        self.assertEqual(category_for("Gisou Honey Infused Lip Oil"), "Lip Oil")
        self.assertEqual(category_for("Fenty Beauty Gloss Bomb"), "Lip Gloss")
