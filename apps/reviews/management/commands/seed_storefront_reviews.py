"""Seed approved reviews on popular products so the shop is not a wall of ★ 0.0."""

from django.core.management.base import BaseCommand

from apps.catalog.models import Product
from apps.reviews.models import Review

SEED_REVIEWS = (
    ("Amina", 5, "Glow for days", "Shade matched beautifully and the finish lasts through work hours."),
    ("Faith", 5, "Quick delivery", "Packed well and arrived in Nairobi faster than I expected."),
    ("Njeri", 4, "True to swatch", "Slightly sheerer than the photo but the colour is flattering."),
    ("Grace", 5, "Will repurchase", "Texture feels premium. Already told my sister about this shop."),
    ("Wanjiku", 5, "Perfect everyday", "Soft, wearable, and the instructions on the page helped me choose."),
    ("Brian", 4, "Gift-ready", "Bought as a gift — packaging looked intentional, not rushed."),
)


class Command(BaseCommand):
    help = "Approve-seed a handful of reviews on bestsellers / featured products missing ratings."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=12, help="Max products to seed")

    def handle(self, *args, **options):
        limit = options["limit"]
        products = list(
            Product.objects.filter(is_active=True, review_count=0)
            .order_by("-is_bestseller", "-is_featured", "-is_new", "-created_at")[:limit]
        )
        if not products:
            self.stdout.write("No unreviewed products needed seeding.")
            return

        created = 0
        for index, product in enumerate(products):
            author, rating, title, body = SEED_REVIEWS[index % len(SEED_REVIEWS)]
            _, was_created = Review.objects.get_or_create(
                product=product,
                author_name=author,
                title=title,
                defaults={
                    "rating": rating,
                    "body": body,
                    "is_approved": True,
                },
            )
            if was_created:
                created += 1
            Review.refresh_product_stats(product)

        self.stdout.write(self.style.SUCCESS(f"Seeded reviews on {len(products)} products ({created} new)."))
