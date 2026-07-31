from django.test import TestCase
from django.urls import reverse

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
