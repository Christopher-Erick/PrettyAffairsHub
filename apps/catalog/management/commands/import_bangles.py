"""Import the studio bangle photos in media/products/2026/08/bangles as products.

Filenames in that folder carry the shop's asking price; the catalogue copy and
names here are written from what each photo actually shows.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import Brand, Category, Product, ProductImage, ProductVariant
from apps.core.smart_cache import invalidate_catalog_cache

SOURCE_DIR = Path(settings.MEDIA_ROOT) / "products" / "2026" / "08" / "bangles"
BRAND_NAME = "Pretty Affairs Edit"
SOURCE_NAME = "Pretty Affairs Studio"
DIRECTIONS = "Slide on over a relaxed hand. Wipe with a soft dry cloth and store away from heat."

# source filename, name, price, short description, benefits, flags
# flags = (is_featured, is_bestseller, is_new, is_trending)
BANGLES = (
    (
        "bangle 1- price 400.jpeg",
        "Marbled Resin Bangle Trio - Cocoa, Cream & Ivory",
        "400",
        "Three squared resin bangles in cocoa, cream marble and veined ivory.",
        "Soft neutral palette\nSquared sculpted shape\nWears alone or stacked",
        (True, False, True, True),
    ),
    (
        "bangle 2 - price 400.jpeg",
        "Tortoise & Gold Bangle Stack",
        "400",
        "A cream marble, polished gold and tortoiseshell bangle set for warm stacking.",
        "Mixed metal and resin\nWarm tortoiseshell finish\nEasy evening polish",
        (False, True, True, False),
    ),
    (
        "bangle 3 - price 400.jpeg",
        "Sculpted Bangle Duo - Cream & Merlot",
        "400",
        "Two chunky sculpted bangles in cream marble and deep merlot.",
        "Organic sculpted curve\nRich colour pairing\nSubstantial without weight",
        (False, False, True, False),
    ),
    (
        "bangle 4- price 600.jpeg",
        "Wide Amber Tortoise Bangle Set",
        "600",
        "A set of five wide glossy bangles in amber, tortoise and cream tones.",
        "Wide statement cuff shape\nHigh-gloss finish\nFive tones to mix",
        (False, False, True, False),
    ),
    (
        "bangle 5 - price 400.jpeg",
        "Glossy Colour Pop Chunky Bangle",
        "400",
        "A chunky high-shine bangle available across bright and neutral shades.",
        "Bold glossy colour\nRounded chunky profile\nMany shades to choose",
        (False, False, True, False),
    ),
    (
        "bangle 6 price 650.jpeg",
        "Pastel Marble Square Bangle",
        "650",
        "A squared marbled bangle in soft pastels, clear and amber finishes.",
        "Soft marbled pastels\nSquared silhouette\nLight on the wrist",
        (False, False, True, False),
    ),
    (
        "bangle 7- price 750.jpeg",
        "Sculpted Swirl Bangle Trio - Pearl, Cream & Coral",
        "750",
        "Three sculpted swirl bangles in pearl white, cream and coral orange.",
        "Hand-finished swirl effect\nSmooth sculpted curve\nStacks beautifully",
        (False, False, True, False),
    ),
)

# Shades taken from the photos for the two listings that come in a colour range.
SHADES = {
    "Glossy Colour Pop Chunky Bangle": (
        ("Hot Pink", "#FF62A5"),
        ("Plum Purple", "#7B3B8C"),
        ("Wine", "#6B2436"),
        ("Jet Black", "#1B1B1B"),
        ("Amber Orange", "#E9992F"),
        ("Caramel", "#A96A34"),
        ("Butter Cream", "#F1E4BC"),
        ("Ocean Teal", "#6FA2A0"),
    ),
    "Pastel Marble Square Bangle": (
        ("Olive Green", "#6E7D3A"),
        ("Clear Crystal", "#DCE3E6"),
        ("Blossom Pink", "#F2AEC0"),
        ("Powder Blue", "#A9BFE0"),
        ("Butter Yellow", "#E8D89A"),
        ("Ivory Marble", "#E4E1D6"),
        ("Amber Tortoise", "#8A4A20"),
    ),
}

# Generated stand-ins from the earlier filler pass — retired now that real photos exist.
PLACEHOLDER_NAMES = (
    "Pretty Affairs Acrylic Bangle Set - Clear Rose",
    "Pretty Affairs Acrylic Bangle Duo - Soft Blush",
    "Acrylic Bangle Set — Clear Rose",
    "Acrylic Bangle Trio — Amber Glow",
    "Acrylic Bangle Duo — Soft Blush",
)


class Command(BaseCommand):
    help = "Import the studio bangle photos as named, priced products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Replace images on products that already exist.",
        )

    def handle(self, *args, **options):
        refresh = options["refresh"]
        category = Category.objects.filter(slug="acrylic-bangles", is_active=True).first()
        if category is None:
            self.stderr.write("Missing acrylic-bangles category")
            return

        brand, _ = Brand.objects.get_or_create(
            name=BRAND_NAME,
            defaults={"slug": "pretty-affairs-edit", "is_active": True},
        )

        retired = Product.objects.filter(name__in=PLACEHOLDER_NAMES).update(is_active=False)
        self.stdout.write(f"Retired placeholder bangles: {retired}")

        created = 0
        updated = 0
        with transaction.atomic():
            for filename, name, price, short_description, benefits, flags in BANGLES:
                source = SOURCE_DIR / filename
                if not source.exists():
                    self.stderr.write(f"Missing photo {source}")
                    continue

                featured, bestseller, is_new, trending = flags
                product = Product.objects.filter(name=name).first()
                if product is None:
                    product = Product()
                    created += 1
                else:
                    updated += 1

                product.name = name[:200]
                product.brand = brand
                product.short_description = short_description[:255]
                product.description = f"{short_description} Curated for the Pretty Affairs Hub edit."
                product.benefits = benefits
                product.directions = DIRECTIONS
                product.specifications = "Resin bangle. One size, slip-on fit."
                product.ingredients = ""
                product.price = Decimal(price)
                product.sku = f"PAH-BANGLE-{hashlib.md5(name.encode()).hexdigest()[:7].upper()}"
                product.source_name = SOURCE_NAME
                product.is_active = True
                product.is_featured = featured
                product.is_bestseller = bestseller
                product.is_new = is_new
                product.is_trending = trending
                shades = SHADES.get(name, ())
                # Stock lives on the variants once a listing has shades to pick from.
                product.stock = 0 if shades else 15
                product.save()
                product.categories.set([category])

                for shade_name, color_hex in shades:
                    ProductVariant.objects.update_or_create(
                        product=product,
                        name=shade_name,
                        defaults={
                            "color_hex": color_hex,
                            "sku": f"{product.sku}-{slugify(shade_name)[:12].upper()}",
                            "stock": 6,
                            "is_active": True,
                        },
                    )
                if shades:
                    product.variants.exclude(
                        name__in=[shade for shade, _ in shades]
                    ).delete()

                if refresh or not product.images.exists():
                    product.images.all().delete()
                    image = ProductImage(
                        product=product,
                        alt_text=f"{name} product image",
                        sort_order=0,
                    )
                    dest = f"{slugify(name)[:60]}{source.suffix.lower()}"
                    with source.open("rb") as handle:
                        image.image.save(dest, File(handle), save=True)
                    self.stdout.write(f"OK {name}")
                else:
                    self.stdout.write(f"Kept existing image for {name}")

        invalidate_catalog_cache(reason="bangle import")
        self.stdout.write(
            self.style.SUCCESS(f"Bangles: created {created}, updated {updated}.")
        )
