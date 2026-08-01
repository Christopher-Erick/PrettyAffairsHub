"""Publish the sunglasses assortment with clean studio photos.

Frame names describe the pair itself, and each photo is house studio work, so no
supplier watermark or designer logo ever reaches a product page.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import Brand, Category, Product, ProductImage
from apps.core.smart_cache import invalidate_catalog_cache

ASSETS_DIR = Path(
    r"C:\Users\CHRISTOPHER\.cursor\projects\c-Users-CHRISTOPHER-Desktop-project-PRETTY-AFFAIR-HUB\assets"
)

BRAND_NAME = "Pretty Affairs Edit"
SOURCE_NAME = "Shade Edit"
DIRECTIONS = "Wipe lenses with a soft cloth. Store in a case and keep out of direct heat."

# legacy_key, name, price, asset, short description, benefits, flags
# legacy_key matches the source listing this pair came from, so a re-run renames
# the existing product instead of creating a duplicate.
SUNGLASSES = (
    (
        "DaYTKMYDIdr",
        "Classic Wayfarer Sunglasses - Matte Black, Green Lens",
        "12500",
        "pa-sun-wayfarer-black-green.png",
        "The classic wayfarer in matte black with deep green lenses. Unisex.",
        "Timeless wayfarer shape\nDeep green lens tint\nUnisex fit",
        (True, False, True, True),
    ),
    (
        "DZWlFbIjAKI",
        "Rimless Sport Sunglasses - Black, Grey Lens",
        "12450",
        "pa-sun-rimless-sport-black.png",
        "Featherlight rimless sport frames in black with polarised grey lenses. Unisex.",
        "Polarised glare control\nBarely-there weight\nWraps close to the face",
        (False, True, True, False),
    ),
    (
        "DZVOvy2DMWm",
        "Semi-Rimless Sunglasses - Dark Tortoise, Bronze Lens",
        "12450",
        "pa-sun-semi-rimless-tortoise-bronze.png",
        "Semi-rimless frames with a dark tortoise brow and warm bronze lenses.",
        "Warm bronze tint\nTortoise brow detail\nEasy everyday shape",
        (False, False, True, False),
    ),
    (
        "DZUYYokjL8D",
        "Featherweight Rimless Sunglasses - Brown, Bronze Lens",
        "12450",
        "pa-sun-rimless-brown-bronze.png",
        "Fully rimless brown frames with polarised bronze lenses. Unisex.",
        "Polarised bronze lenses\nRimless and featherlight\nUnisex fit",
        (False, False, True, False),
    ),
    (
        "DWTGY5dDKJu",
        "Rimless Cat-Eye Sunglasses - Black, Smoke Lens",
        "12450",
        "pa-sun-rimless-cateye-black.png",
        "Rimless frames with a softly upswept lens and smoke grey tint.",
        "Soft cat-eye lift\nRimless finish\nSmoke grey tint",
        (False, False, True, False),
    ),
    (
        "DWEu9fqDKdW",
        "Reverse Wayfarer Sunglasses - Transparent Blue",
        "12500",
        "pa-sun-reverse-wayfarer-blue.png",
        "Reverse wayfarers in a transparent blue frame with blue lenses.",
        "Transparent blue frame\nReverse wayfarer curve\nStatement colour",
        (False, False, True, False),
    ),
    (
        "DV-_uOAjHd-",
        "Rimless Rectangular Sunglasses - Black, Smoke Lens",
        "12450",
        "pa-sun-rimless-rect-black.png",
        "All-black rimless rectangular frames with polarised smoke lenses.",
        "Polarised smoke lenses\nClean rimless lines\nAll-black finish",
        (False, False, False, True),
    ),
    (
        "DM18yU3ofg_",
        "Sport Sunglasses - Amber Tortoise, Bronze Lens",
        "12450",
        "pa-sun-sport-amber-bronze.png",
        "Sport frames with amber tortoise temples and polarised bronze lenses.",
        "Polarised bronze lenses\nAmber tortoise temples\nSecure sport fit",
        (False, False, True, False),
    ),
)

# Earlier house placeholders and the watermarked source-photo listings they replaced.
RETIRED_NAMES = (
    "Pretty Affairs Gold Rim Oval Sunglasses",
    "Pretty Affairs Matte Black Round Sunglasses",
    "Gold Rim Oval Sunglasses",
    "Tortoiseshell Cat-Eye Sunglasses",
    "Matte Black Round Sunglasses",
)


class Command(BaseCommand):
    help = "Publish the sunglasses assortment with clean studio photos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Replace images on products that already exist.",
        )

    def handle(self, *args, **options):
        refresh = options["refresh"]
        category = Category.objects.filter(slug="sunglasses", is_active=True).first()
        if category is None:
            self.stderr.write("Missing sunglasses category")
            return

        brand, _ = Brand.objects.get_or_create(
            name=BRAND_NAME,
            defaults={"slug": "pretty-affairs-edit", "is_active": True},
        )

        retired = Product.objects.filter(name__in=RETIRED_NAMES).update(is_active=False)
        self.stdout.write(f"Retired placeholder sunglasses: {retired}")

        created = 0
        updated = 0
        with transaction.atomic():
            for (
                legacy_key,
                name,
                price,
                asset_name,
                short_description,
                benefits,
                flags,
            ) in SUNGLASSES:
                asset_path = ASSETS_DIR / asset_name
                if not asset_path.exists():
                    self.stderr.write(f"Missing asset {asset_path}")
                    continue

                featured, bestseller, is_new, trending = flags
                source_url = f"https://catalog-import/feed-shade/p/{legacy_key}"
                product = Product.objects.filter(source_url=source_url).first()
                if product is None:
                    product = Product.objects.filter(name=name).first()
                if product is None:
                    product = Product()
                    created += 1
                else:
                    updated += 1

                renamed = product.pk and product.name != name
                product.name = name[:200]
                if renamed:
                    # Let the model rebuild the slug from the new frame name.
                    product.slug = ""
                product.brand = brand
                product.short_description = short_description[:255]
                product.description = f"{short_description} Curated for the Pretty Affairs Hub edit."
                product.benefits = benefits
                product.directions = DIRECTIONS
                product.specifications = "Unisex fit. Full UV protection. Case included."
                product.ingredients = ""
                product.price = Decimal(price)
                product.stock = 8
                product.sku = f"PAH-SUNGLA-{hashlib.md5(source_url.encode()).hexdigest()[:7].upper()}"
                product.source_name = SOURCE_NAME
                product.source_url = source_url
                product.is_active = True
                product.is_featured = featured
                product.is_bestseller = bestseller
                product.is_new = is_new
                product.is_trending = trending
                product.save()
                product.categories.set([category])

                if refresh or not product.images.exists():
                    product.images.all().delete()
                    image = ProductImage(
                        product=product,
                        alt_text=f"{name} product image",
                        sort_order=0,
                    )
                    dest = f"{slugify(name)[:60]}{asset_path.suffix}"
                    with asset_path.open("rb") as handle:
                        image.image.save(dest, File(handle), save=True)
                    self.stdout.write(f"OK {name}")
                else:
                    self.stdout.write(f"Kept existing image for {name}")

        invalidate_catalog_cache(reason="sunglasses import")
        self.stdout.write(
            self.style.SUCCESS(f"Sunglasses: created {created}, updated {updated}.")
        )
