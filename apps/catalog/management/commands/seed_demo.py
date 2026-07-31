from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import (
    Brand,
    Bundle,
    BundleItem,
    Category,
    Collection,
    Product,
    ProductRelation,
)
from apps.content.models import BlogPost, FAQ, HomepageSection, SitePage, Testimonial
from apps.discounts.models import Coupon, FlashSale, GiftCard
from apps.reviews.models import Review


class Command(BaseCommand):
    help = "Seed demo catalog, content, and promotions for Pretty Affairs Hub"

    def handle(self, *args, **options):
        brand, _ = Brand.objects.get_or_create(name="Pretty Affairs")
        lips, _ = Category.objects.get_or_create(name="Lipstick", defaults={"sort_order": 1})
        gloss, _ = Category.objects.get_or_create(name="Lip Gloss", defaults={"sort_order": 2})
        oils, _ = Category.objects.get_or_create(name="Lip Oils", defaults={"sort_order": 3})
        eyes, _ = Category.objects.get_or_create(name="Eye shadow", defaults={"sort_order": 4})

        bold, _ = Collection.objects.get_or_create(
            name="Bold Reds", defaults={"is_featured": True, "description": "Statement colour."}
        )
        nudes, _ = Collection.objects.get_or_create(
            name="Everyday Nudes", defaults={"is_featured": True}
        )

        catalog = [
            ("Velvet Rose Lipstick", lips, bold, "1600", True, True, False, False),
            ("Crimson Muse", lips, bold, "1600", False, True, True, False),
            ("Silk Nude Gloss", gloss, nudes, "1300", True, False, True, False),
            ("Soft Sand Gloss", gloss, nudes, "1300", False, False, False, True),
            ("Amber Glow Lip Oil", oils, nudes, "1900", True, True, False, True),
            ("Berry Bloom Oil", oils, bold, "1900", False, False, True, False),
            ("Dusk Palette", eyes, bold, "2800", True, False, False, True),
            ("Morning Light Palette", eyes, nudes, "2800", False, True, False, False),
        ]

        products = []
        for name, category, collection, price, featured, best, new, trending in catalog:
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "brand": brand,
                    "short_description": f"{name} crafted for everyday luxury.",
                    "description": f"{name} delivers a refined finish with a comfortable wear.",
                    "benefits": "Long-wearing colour\nComfortable feel\nFlattering finish",
                    "ingredients": "Emollient oils, pigments, vitamin E",
                    "directions": "Apply to clean lips or lids. Build for intensity.",
                    "specifications": "Net wt. as labelled. Made for daily wear.",
                    "price": Decimal(price),
                    "compare_at_price": Decimal(price) + Decimal("300") if trending else None,
                    "stock": 40,
                    "sku": name[:3].upper() + price,
                    "is_active": True,
                    "is_featured": featured,
                    "is_bestseller": best,
                    "is_new": new,
                    "is_trending": trending,
                    "is_limited_offer": trending,
                },
            )
            product.categories.add(category)
            product.collections.add(collection)
            products.append(product)

        # Showcase low-stock urgency on a few hero pieces
        low_stock_map = {
            "Velvet Rose Lipstick": 4,
            "Dusk Palette": 3,
            "Amber Glow Lip Oil": 5,
        }
        for product in products:
            if product.name in low_stock_map:
                product.stock = low_stock_map[product.name]
                product.save(update_fields=["stock"])

        if len(products) >= 4:
            ProductRelation.objects.get_or_create(
                from_product=products[0],
                to_product=products[2],
                relation_type=ProductRelation.RELATION_FBT,
            )
            ProductRelation.objects.get_or_create(
                from_product=products[0],
                to_product=products[1],
                relation_type=ProductRelation.RELATION_SIMILAR,
            )

        bundle, _ = Bundle.objects.get_or_create(
            name="Evening Edit Bundle",
            defaults={
                "description": "Lipstick, gloss, and oil — an evening-ready trio.",
                "price": Decimal("4200"),
                "compare_at_price": Decimal("4800"),
                "is_active": True,
            },
        )
        for product in products[:3]:
            BundleItem.objects.get_or_create(bundle=bundle, product=product, defaults={"quantity": 1})

        Coupon.objects.get_or_create(
            code="PRETTY10",
            defaults={
                "discount_type": Coupon.PERCENT,
                "amount": Decimal("10"),
                "min_order_amount": Decimal("1000"),
                "is_active": True,
            },
        )
        GiftCard.objects.get_or_create(
            code="GIFT2900",
            defaults={
                "initial_balance": Decimal("2900"),
                "current_balance": Decimal("2900"),
                "is_active": True,
            },
        )
        GiftCard.objects.get_or_create(
            code="GIFT3200",
            defaults={
                "initial_balance": Decimal("3200"),
                "current_balance": Decimal("3200"),
                "is_active": True,
            },
        )
        sale, _ = FlashSale.objects.get_or_create(
            name="Weekend Glow",
            defaults={
                "percent_off": 15,
                "starts_at": timezone.now() - timedelta(days=1),
                "ends_at": timezone.now() + timedelta(days=7),
                "is_active": True,
            },
        )
        sale.products.set(products[:3])

        Review.objects.get_or_create(
            product=products[0],
            author_name="Amina",
            defaults={
                "rating": 5,
                "title": "Instant favourite",
                "body": "Beautiful colour payoff and so comfortable.",
                "is_approved": True,
            },
        )
        Review.refresh_product_stats(products[0])

        SitePage.objects.get_or_create(
            slug="about",
            defaults={
                "title": "About Pretty Affairs Hub",
                "body": (
                    "Pretty Affairs Hub is your one stop beauty destination. "
                    "We curate elegant cosmetics with a focus on trust, quality, and effortless shopping."
                ),
                "is_published": True,
            },
        )
        FAQ.objects.get_or_create(
            question="Do you deliver nationwide?",
            defaults={"answer": "Yes. Delivery is available across Kenya. Free over KSh 5,000.", "sort_order": 1},
        )
        FAQ.objects.get_or_create(
            question="What is your return policy?",
            defaults={"answer": "Unopened items can be returned within 7 days of delivery.", "sort_order": 2},
        )
        Testimonial.objects.get_or_create(
            author_name="Wanjiru",
            defaults={"quote": "Packaging feels premium and the shades are stunning.", "rating": 5},
        )
        Testimonial.objects.get_or_create(
            author_name="Faith",
            defaults={"quote": "Checkout was simple and delivery was quick.", "rating": 5},
        )
        BlogPost.objects.get_or_create(
            slug="everyday-nude-edit",
            defaults={
                "title": "Building an everyday nude edit",
                "excerpt": "Soft tones that flatter from desk to dinner.",
                "body": "Start with a hydrating lip oil, layer a nude gloss, and finish with a soft liner.",
                "is_published": True,
            },
        )
        BlogPost.objects.get_or_create(
            slug="bold-lip-tutorial",
            defaults={
                "title": "Bold lip tutorial",
                "excerpt": "A five-minute statement lip.",
                "body": "Exfoliate lightly, apply balm, blot, then layer your bold lipstick from the centre out.",
                "is_tutorial": True,
                "is_published": True,
            },
        )
        HomepageSection.objects.get_or_create(
            key="promise",
            defaults={
                "title": "The Pretty Affairs promise",
                "subtitle": "Elegant shopping, grounded in trust",
                "body": "Clear ingredients, thoughtful packaging, calm checkout.",
                "cta_label": "Shop now",
                "cta_url": "/shop/",
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Seed data ready."))
