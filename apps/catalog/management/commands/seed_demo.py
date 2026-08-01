from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

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

        taxonomy = [
            (
                "Lips",
                1,
                [
                    ("Lip Oil", 1),
                    ("Lip Gloss", 2),
                    ("Lipstick", 3),
                ],
            ),
            (
                "Eyes & Lashes",
                2,
                [
                    ("Lashes", 1),
                ],
            ),
            (
                "Face Care",
                3,
                [
                    ("Face Masks", 1),
                    ("Cleansing Brushes", 2),
                ],
            ),
            (
                "Fragrance",
                4,
                [
                    ("Perfumes", 1),
                    ("Body Splash", 2),
                    ("Cologne", 3),
                ],
            ),
            (
                "Accessories",
                5,
                [
                    ("Pocket Mirrors", 1),
                    ("Sunglasses", 2),
                ],
            ),
            (
                "Jewellery & Gifting",
                6,
                [
                    ("Jewellery Boxes", 1),
                    ("Acrylic Bangles", 2),
                ],
            ),
            (
                "Body Essentials",
                7,
                [
                    ("Body & Hand Care", 1),
                    ("Boob Tape", 2),
                ],
            ),
        ]

        leaf_categories = {}
        parent_categories = {}
        keep_slugs = set()

        for parent_name, parent_order, children in taxonomy:
            parent, _ = Category.objects.update_or_create(
                slug=slugify(parent_name),
                defaults={
                    "name": parent_name,
                    "parent": None,
                    "is_active": True,
                    "sort_order": parent_order,
                    "description": f"Shop {parent_name.lower()} at Pretty Affairs Hub.",
                },
            )
            parent_categories[parent_name] = parent
            keep_slugs.add(parent.slug)
            for child_name, child_order in children:
                child, _ = Category.objects.update_or_create(
                    slug=slugify(child_name),
                    defaults={
                        "name": child_name,
                        "parent": parent,
                        "is_active": True,
                        "sort_order": child_order,
                        "description": f"{child_name} in the {parent_name} edit.",
                    },
                )
                leaf_categories[child_name] = child
                keep_slugs.add(child.slug)

        # Retire old demo categories that are outside the live assortment
        Category.objects.exclude(slug__in=keep_slugs).update(is_active=False)

        # Alias older names used by previous seed products
        lipstick = leaf_categories["Lipstick"]
        gloss = leaf_categories["Lip Gloss"]
        oils = leaf_categories["Lip Oil"]

        everyday, _ = Collection.objects.update_or_create(
            slug="everyday-essentials",
            defaults={
                "name": "Everyday Essentials",
                "is_featured": True,
                "is_active": True,
                "description": "Soft daily favourites for polished ease.",
            },
        )
        night_out, _ = Collection.objects.update_or_create(
            slug="night-out",
            defaults={
                "name": "Night Out",
                "is_featured": True,
                "is_active": True,
                "description": "Bolder finishes for evenings and events.",
            },
        )
        gift_sets, _ = Collection.objects.update_or_create(
            slug="gift-sets",
            defaults={
                "name": "Gift Sets",
                "is_featured": True,
                "is_active": True,
                "description": "Ready-to-give beauty moments.",
            },
        )
        Collection.objects.filter(slug__in=["bold-reds", "everyday-nudes"]).update(is_active=False)

        catalog = [
            ("Velvet Rose Lipstick", lipstick, night_out, "1600", True, True, False, False),
            ("Crimson Muse", lipstick, night_out, "1600", False, True, True, False),
            ("Silk Nude Gloss", gloss, everyday, "1300", True, False, True, False),
            ("Soft Sand Gloss", gloss, everyday, "1300", False, False, False, True),
            ("Amber Glow Lip Oil", oils, everyday, "1900", True, True, False, True),
            ("Berry Bloom Oil", oils, night_out, "1900", False, False, True, False),
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
            product.is_active = True
            product.save(update_fields=["is_active"])
            product.categories.clear()
            product.categories.add(category)
            product.collections.clear()
            product.collections.add(collection)
            if collection == night_out or featured:
                product.collections.add(gift_sets)
            products.append(product)

        # Retire discontinued demo eye products outside the live list
        Product.objects.filter(name__in=["Dusk Palette", "Morning Light Palette"]).update(is_active=False)

        # Showcase low-stock urgency on a few hero pieces
        low_stock_map = {
            "Velvet Rose Lipstick": 4,
            "Silk Nude Gloss": 6,
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

        demo_reviews = [
            ("Amina", 5, "Instant favourite", "Beautiful colour payoff and so comfortable."),
            ("Wanjiku", 5, "Everyday essential", "Soft finish and wears beautifully all day."),
            ("Brian", 4, "Gift-worthy", "Looked premium and arrived quickly."),
            ("Faith", 5, "True shade", "Exactly as expected — elegant and buildable."),
            ("Nelly", 4, "Lovely texture", "Smooth application with a flattering glow."),
            ("Otieno", 5, "Bought again", "My go-to for polished looks."),
            ("Grace", 4, "Great value", "Feels luxurious and lasts well."),
            ("Halima", 5, "Soft and chic", "Perfect for both day and evening."),
        ]
        for index, product in enumerate(products):
            author, rating, title, body = demo_reviews[index % len(demo_reviews)]
            Review.objects.get_or_create(
                product=product,
                author_name=author,
                defaults={
                    "rating": rating,
                    "title": title,
                    "body": body,
                    "is_approved": True,
                },
            )
            # Second review for variety on featured pieces
            if index % 2 == 0:
                Review.objects.get_or_create(
                    product=product,
                    author_name=f"{author} K.",
                    defaults={
                        "rating": 5 if rating == 4 else 4,
                        "title": "Would recommend",
                        "body": "Reliable quality and a beautiful finish.",
                        "is_approved": True,
                    },
                )
            Review.refresh_product_stats(product)

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
