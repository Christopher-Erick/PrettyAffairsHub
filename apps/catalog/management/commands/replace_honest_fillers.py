"""Replace mismatched filler SKUs with honest Pretty Affairs products and matching photos."""

from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import Brand, Category, Product, ProductImage

# Generated assets live in the Cursor assets folder for this project.
ASSETS_DIR = Path(
    r"C:\Users\CHRISTOPHER\.cursor\projects\c-Users-CHRISTOPHER-Desktop-project-PRETTY-AFFAIR-HUB\assets"
)

# Honest house-brand products whose photos match the packaging/name.
REPLACEMENTS = (
    (
        "Pretty Affairs Hydrating Sheet Mask",
        "face-masks",
        "950",
        "pa-hydrating-sheet-mask.png",
        "A hydrating sheet mask for a plump, dewy finish.",
        "Deep hydration\nSoft refreshed feel\nEasy at-home ritual",
        "Apply to clean skin for 10-20 minutes. Pat remaining essence in.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Green Tea Calm Mask",
        "face-masks",
        "1100",
        "pa-green-tea-mask.png",
        "A green-tea sheet mask for calm, comforted skin.",
        "Soothing green tea\nSoft sheet fit\nFresh after-feel",
        "Leave on for 15-20 minutes, then pat remaining essence in.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Dual-Ended Cleansing Brush",
        "cleansing-brushes",
        "1850",
        "pa-cleansing-brush.png",
        "A dual-ended cleansing brush for a gentle everyday cleanse.",
        "Soft and firm sides\nBuilds a rich lather\nEasy to rinse",
        "Wet the brush, add cleanser, massage in circles, then rinse and air-dry.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Soft Silicone Cleansing Brush",
        "cleansing-brushes",
        "2200",
        "pa-silicone-brush.png",
        "A soft silicone cleansing brush for a deeper daily cleanse.",
        "Gentle silicone bristles\nRich lather\nEasy to rinse",
        "Wet, add cleanser, massage in circles, rinse and air-dry.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Vanilla Soft Body Mist 200ml",
        "body-splash",
        "2800",
        "pa-vanilla-body-mist.png",
        "A light vanilla body mist for soft all-over scent.",
        "Soft everyday scent\nWeightless mist\nEasy reapply",
        "Mist over clean skin from a short distance.",
        (True, True, False, True),
    ),
    (
        "Pretty Affairs Cherry Blossom Body Mist 200ml",
        "body-splash",
        "2800",
        "pa-cherry-blossom-mist.png",
        "A soft floral body mist with cherry-blossom notes.",
        "Fresh floral trail\nLight body scent\nEveryday polish",
        "Mist onto clean skin from a short distance.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Gold Rim Oval Sunglasses",
        "sunglasses",
        "2800",
        "pa-gold-oval-sunglasses.png",
        "Thin gold-rim oval sunglasses for polished daytime wear.",
        "Oval silhouette\nLightweight frame\nEveryday polish",
        "Wipe lenses with a soft cloth. Store in a pouch when not in wear.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Matte Black Round Sunglasses",
        "sunglasses",
        "2650",
        "pa-black-round-sunglasses.png",
        "Minimal matte-black round sunglasses.",
        "Clean silhouette\nComfortable fit\nGiftable staple",
        "Clean lenses gently. Avoid leaving in direct heat.",
        (False, False, False, True),
    ),
    (
        "Pretty Affairs Velvet Travel Jewellery Box",
        "jewellery-boxes",
        "2450",
        "pa-velvet-jewellery-box.png",
        "A blush velvet travel jewellery box for rings and studs.",
        "Travel-friendly size\nSoft lined compartments\nGiftable finish",
        "Store jewellery dry and closed. Wipe the exterior with a soft cloth.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Rose Gold Jewellery Case",
        "jewellery-boxes",
        "2750",
        "pa-rosegold-jewellery-case.png",
        "A slim rose-gold jewellery case for everyday keepsakes.",
        "Compact case\nSoft lined interior\nGift-ready look",
        "Keep dry and closed. Wipe exterior with a soft cloth.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Acrylic Bangle Set - Clear Rose",
        "acrylic-bangles",
        "1200",
        "pa-clear-rose-bangles.png",
        "Stackable clear-rose acrylic bangles for easy finishing touches.",
        "Lightweight acrylic\nStackable finish\nSoft rose tint",
        "Slide on and stack as you like. Wipe with a soft dry cloth.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Acrylic Bangle Duo - Soft Blush",
        "acrylic-bangles",
        "1100",
        "pa-blush-bangles.png",
        "A soft-blush acrylic bangle duo for everyday colour.",
        "Pretty blush finish\nEasy to stack\nLight on the wrist",
        "Wear alone or stacked. Store flat when not in use.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Body Tape - Nude",
        "boob-tape",
        "1650",
        "pa-body-tape.png",
        "Flexible nude body tape for strapless and backless looks.",
        "Flexible hold\nLow-profile finish\nEvent ready",
        "Apply to clean, dry skin. Remove gently after wear.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Vanilla Cashmere Body Wash 500ml",
        "body-hand-care",
        "2100",
        "pa-vanilla-body-wash.png",
        "A creamy vanilla body wash for a soft, scented cleanse.",
        "Rich foamy cleanse\nSoft after-feel\nWarm vanilla notes",
        "Lather over wet skin, rinse thoroughly, and pat dry.",
        (True, True, True, False),
    ),
    (
        "Pretty Affairs Daily Nourish Body Wash 500ml",
        "body-hand-care",
        "1750",
        "pa-nourish-body-wash.png",
        "A gentle everyday body wash for soft, cared-for skin.",
        "Mild daily cleanse\nMoisturising feel\nFresh finish",
        "Massage onto wet skin, rinse well, and pat dry.",
        (False, True, False, False),
    ),
    (
        "Pretty Affairs Shea Soft Hand Cream 75ml",
        "body-hand-care",
        "950",
        "pa-shea-hand-cream.png",
        "A fast-absorbing shea hand cream for lasting softness.",
        "Shea softness\nNon-greasy finish\nEveryday comfort",
        "Massage into clean, dry hands whenever they need a boost.",
        (True, False, True, False),
    ),
)


class Command(BaseCommand):
    help = "Retire mismatched branded fillers and seed honest Pretty Affairs products with matching photos."

    def handle(self, *args, **options):
        brand, _ = Brand.objects.get_or_create(
            name="Pretty Affairs Edit",
            defaults={"slug": "pretty-affairs-edit", "is_active": True},
        )

        retired = Product.objects.filter(
            source_name="Pretty Affairs Edit",
            is_active=True,
        ).exclude(name__startswith="Pretty Affairs ").update(is_active=False)
        # Also retire any previous Pretty Affairs Edit fillers that still use wrong photos
        # from the earlier Unsplash seeding (names without the Pretty Affairs prefix).
        self.stdout.write(f"Retired mismatched fillers: {retired}")

        created = 0
        updated = 0
        with transaction.atomic():
            for (
                name,
                category_slug,
                price,
                asset_name,
                short_description,
                benefits,
                directions,
                flags,
            ) in REPLACEMENTS:
                category = Category.objects.filter(slug=category_slug, is_active=True).first()
                if category is None:
                    self.stderr.write(f"Missing category {category_slug}")
                    continue
                asset_path = ASSETS_DIR / asset_name
                if not asset_path.exists():
                    self.stderr.write(f"Missing asset {asset_path}")
                    continue
                featured, bestseller, is_new, trending = flags
                product, was_created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        "brand": brand,
                        "short_description": short_description,
                        "description": f"{short_description} Curated for the Pretty Affairs Hub edit.",
                        "benefits": benefits,
                        "directions": directions,
                        "specifications": "See packaging for net weight and full details.",
                        "ingredients": "See product packaging for the full ingredient list.",
                        "price": Decimal(price),
                        "stock": 30,
                        "sku": f"PAH-{slugify(category.name)[:6].upper()}-{hashlib.md5(name.encode()).hexdigest()[:7].upper()}",
                        "source_name": "Pretty Affairs Edit",
                        "is_active": True,
                        "is_featured": featured,
                        "is_bestseller": bestseller,
                        "is_new": is_new,
                        "is_trending": trending,
                    },
                )
                if was_created:
                    created += 1
                else:
                    product.is_active = True
                    product.price = Decimal(price)
                    product.short_description = short_description
                    product.description = f"{short_description} Curated for the Pretty Affairs Hub edit."
                    product.benefits = benefits
                    product.directions = directions
                    product.is_featured = featured
                    product.is_bestseller = bestseller
                    product.is_new = is_new
                    product.is_trending = trending
                    product.save()
                    updated += 1
                product.categories.set([category])

                # Replace any previous images with the matching generated photo.
                product.images.all().delete()
                dest_name = f"{slugify(name)[:50]}-{hashlib.md5(asset_name.encode()).hexdigest()[:8]}{asset_path.suffix}"
                image = ProductImage(
                    product=product,
                    alt_text=f"{name} product image",
                    sort_order=0,
                )
                with asset_path.open("rb") as handle:
                    image.image.save(dest_name, File(handle), save=True)
                self.stdout.write(f"OK {name}")

        self.stdout.write(
            self.style.SUCCESS(f"Created {created}, updated {updated}. Matching photos attached.")
        )
