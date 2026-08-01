"""Seed extra catalog products and attach free stock product photography.

Downloads Unsplash images (license: Unsplash License) for starter SKUs that
have no local product photo yet, and adds more items to thin categories.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.catalog.models import Brand, Category, Product, ProductImage

USER_AGENT = "PrettyAffairsHub/1.0 catalog image seeder"


def unsplash(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1000&q=80"


# Curated free product photography mapped to categories / products.
IMAGE_BY_KEY = {
    "face-mask-1": unsplash("1596755389378-c31d21fd1273"),
    "face-mask-2": unsplash("1616394584738-fc6e612e71b9"),
    "face-mask-3": unsplash("1608248543803-ba4f8c70ae0b"),
    "brush-1": unsplash("1522335789203-aabd1fc54bc9"),
    "brush-2": unsplash("1598440947619-2c35fc9aa908"),
    "mist-1": unsplash("1541643600914-78b084683601"),
    "mist-2": unsplash("1587017539504-67cfbddac569"),
    "mist-3": unsplash("1556228720-195a672e8a03"),
    "sunglasses-1": unsplash("1511499767150-a48a237f0083"),
    "sunglasses-2": unsplash("1512496015851-a90fb38ba796"),
    "sunglasses-3": unsplash("1596462502278-27bfdc403348"),
    "jewellery-1": unsplash("1515562141207-7a88fb7ce338"),
    "jewellery-2": unsplash("1612817288484-6f916006741a"),
    "bangle-1": unsplash("1515562141207-7a88fb7ce338"),
    "bangle-2": unsplash("1587017539504-67cfbddac569"),
    "bangle-3": unsplash("1598440947619-2c35fc9aa908"),
    "tape-1": unsplash("1556229010-6c3f2c9ca5f8"),
    "tape-2": unsplash("1571875257727-256c39da42af"),
    "wash-1": unsplash("1556229010-6c3f2c9ca5f8"),
    "wash-2": unsplash("1612817288484-6f916006741a"),
    "wash-3": unsplash("1571875257727-256c39da42af"),
    "hand-1": unsplash("1608248543803-ba4f8c70ae0b"),
    "hand-2": unsplash("1556228720-195a672e8a03"),
    "lash-1": unsplash("1522335789203-aabd1fc54bc9"),
}

# Existing products that need photos attached by exact name.
EXISTING_IMAGE_MAP = {
    "Mediheal N.M.F Aquaring Ampoule Face Mask": "face-mask-1",
    "Real Techniques Dual-Ended Cleansing Brush": "brush-1",
    "Victoria's Secret Bare Vanilla Fragrance Mist 250ml": "mist-1",
    "Gold Rim Oval Sunglasses": "sunglasses-1",
    "Velvet Travel Jewellery Box": "jewellery-1",
    "Acrylic Bangle Set — Clear Rose": "bangle-1",
    "Victoria's Secret Bare Boob Tape": "tape-1",
    "eos Shea Better Cashmere Body Wash Vanilla Cashmere 473ml": "wash-1",
    "Dove Shea Butter Warm Vanilla Body Wash 500ml": "wash-2",
    "eos Shea Better Hand Cream Vanilla Cashmere 74ml": "hand-1",
}

# New products: name, category slug, price, image key, short copy, flags
NEW_PRODUCTS = (
    (
        "Innisfree Green Tea Seed Hyaluronic Serum Mask",
        "face-masks",
        "1100",
        "face-mask-2",
        "A green-tea sheet mask for a calm, hydrated glow.",
        "Hydrating serum soak\nSoft sheet fit\nFresh after-feel",
        "Leave on for 15–20 minutes, then pat remaining essence in.",
        (False, False, True, False),
    ),
    (
        "COSRX Advanced Snail Mucin Power Sheet Mask",
        "face-masks",
        "1250",
        "face-mask-3",
        "A snail-mucin sheet mask for plump, comforted skin.",
        "Barrier-loving care\nPlumping moisture\nGentle everyday use",
        "Apply to clean skin for 10–20 minutes. Massage leftover essence.",
        (True, False, True, False),
    ),
    (
        "Soft Silicone Facial Cleansing Brush",
        "cleansing-brushes",
        "2200",
        "brush-2",
        "A soft silicone cleansing brush for a deeper everyday cleanse.",
        "Gentle on skin\nBuilds a rich lather\nEasy to rinse",
        "Wet, add cleanser, massage in circles, rinse and air-dry.",
        (False, False, True, False),
    ),
    (
        "Bath & Body Works Japanese Cherry Blossom Fine Fragrance Mist 236ml",
        "body-splash",
        "2900",
        "mist-2",
        "A soft floral body mist for light all-over scent.",
        "Everyday freshness\nSoft floral trail\nEasy reapply",
        "Mist onto clean skin from a short distance.",
        (False, True, False, True),
    ),
    (
        "eos Cashmere Body Mist Fresh & Cozy 100ml",
        "body-splash",
        "2400",
        "mist-3",
        "A cashmere-soft body mist with fresh, cozy notes.",
        "Light body scent\nLayers with body wash\nSoft finish",
        "Spray over pulse points and body after showering.",
        (True, False, True, False),
    ),
    (
        "Tortoiseshell Cat-Eye Sunglasses",
        "sunglasses",
        "3100",
        "sunglasses-2",
        "Classic cat-eye sunglasses with a warm tortoiseshell frame.",
        "Flattering cat-eye shape\nLightweight wear\nEveryday polish",
        "Wipe with a soft cloth and store in the pouch.",
        (True, False, True, False),
    ),
    (
        "Matte Black Round Sunglasses",
        "sunglasses",
        "2650",
        "sunglasses-3",
        "Minimal round sunglasses with a matte black finish.",
        "Clean silhouette\nComfortable fit\nGiftable staple",
        "Clean lenses gently. Avoid leaving in direct heat.",
        (False, False, False, True),
    ),
    (
        "Rose Gold Ring & Earring Jewellery Case",
        "jewellery-boxes",
        "2750",
        "jewellery-2",
        "A slim rose-gold jewellery case for rings and studs.",
        "Compact travel case\nSoft lined interior\nGift-ready look",
        "Keep dry and closed. Wipe exterior with a soft cloth.",
        (False, False, True, False),
    ),
    (
        "Acrylic Bangle Trio — Amber Glow",
        "acrylic-bangles",
        "1350",
        "bangle-2",
        "Three stackable amber acrylic bangles for warm colour play.",
        "Stackable set\nLightweight acrylic\nWarm amber tones",
        "Slide on and stack. Wipe with a soft dry cloth.",
        (True, False, True, False),
    ),
    (
        "Acrylic Bangle Duo — Soft Blush",
        "acrylic-bangles",
        "1100",
        "bangle-3",
        "A soft-blush acrylic bangle duo for everyday finishing touches.",
        "Pretty blush finish\nEasy to stack\nLight on the wrist",
        "Wear alone or stacked. Store flat when not in use.",
        (False, False, True, False),
    ),
    (
        "Fashion Body Tape Roll — Nude",
        "boob-tape",
        "1450",
        "tape-2",
        "A flexible nude body tape roll for strapless and backless looks.",
        "Flexible hold\nLow-profile finish\nEvent ready",
        "Apply to clean dry skin. Remove gently after wear.",
        (False, False, True, False),
    ),
    (
        "Dove Deeply Nourishing Body Wash 500ml",
        "body-hand-care",
        "1650",
        "wash-3",
        "A classic Dove body wash for soft, cared-for skin after every shower.",
        "Mild cleanse\nMoisturising feel\nEveryday essential",
        "Lather onto wet skin, rinse thoroughly, and pat dry.",
        (False, True, False, False),
    ),
    (
        "eos Shea Better Hand Cream Fresh & Cozy 74ml",
        "body-hand-care",
        "950",
        "hand-2",
        "A lightweight eos hand cream with fresh cozy notes and lasting moisture.",
        "24H moisture\nFast absorbing\nFresh cozy scent",
        "Massage into clean hands whenever they feel dry.",
        (False, False, True, False),
    ),
    (
        "Maybelline Lash Sensational Sky High Mascara",
        "lashes",
        "1850",
        "lash-1",
        "A lengthening mascara for lifted, defined lashes.",
        "Length and lift\nBuildable definition\nEveryday drama",
        "Sweep from root to tip. Build coats as desired.",
        (True, True, False, True),
    ),
)


class Command(BaseCommand):
    help = "Add more category products and download product images for SKUs without photos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-download",
            action="store_true",
            help="Create/update products without fetching remote images.",
        )

    def handle(self, *args, **options):
        skip_download = options["skip_download"]
        brand, _ = Brand.objects.get_or_create(
            name="Pretty Affairs Edit",
            defaults={"slug": "pretty-affairs-edit", "is_active": True},
        )

        created = 0
        imaged = 0
        failed = 0

        with transaction.atomic():
            for (
                name,
                category_slug,
                price,
                image_key,
                short_description,
                benefits,
                directions,
                flags,
            ) in NEW_PRODUCTS:
                category = Category.objects.filter(slug=category_slug, is_active=True).first()
                if not category:
                    self.stderr.write(f"Missing category: {category_slug}")
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
                    product.save(update_fields=["is_active", "price"])
                product.categories.set([category])
                if not skip_download:
                    ok = self.ensure_image(product, IMAGE_BY_KEY[image_key])
                    imaged += int(ok)
                    failed += int(not ok)

            for name, image_key in EXISTING_IMAGE_MAP.items():
                product = Product.objects.filter(name=name, is_active=True).first()
                if not product:
                    # Encoding may have mangled the em dash in acrylic bangles.
                    product = Product.objects.filter(name__startswith=name[:28], is_active=True).first()
                if not product:
                    self.stderr.write(f"Existing product not found: {name}")
                    continue
                if skip_download:
                    continue
                if product.images.filter(image__gt="").exists():
                    continue
                ok = self.ensure_image(product, IMAGE_BY_KEY[image_key])
                imaged += int(ok)
                failed += int(not ok)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} products. Attached {imaged} images. Failures: {failed}."
            )
        )

    def ensure_image(self, product: Product, url: str) -> bool:
        if product.images.filter(image__gt="").exists():
            return True
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"})
            with urlopen(request, timeout=45) as response:
                content = response.read()
                content_type = response.headers.get_content_type()
            suffix = ".jpg"
            if "png" in content_type:
                suffix = ".png"
            elif "webp" in content_type:
                suffix = ".webp"
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            filename = f"{slugify(product.name)[:50]}-{digest}{suffix}"
            image = ProductImage(
                product=product,
                alt_text=f"{product.name} product image",
                sort_order=0,
            )
            image.image.save(filename, ContentFile(content), save=True)
            self.stdout.write(f"  image -> {product.name}")
            return True
        except Exception as exc:
            self.stderr.write(f"  image failed for {product.name}: {exc}")
            return False
