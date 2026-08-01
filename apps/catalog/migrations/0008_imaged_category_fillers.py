"""Add imaged filler products for thin categories.

Creates Pretty Affairs Edit starter SKUs and attaches the committed media files
under media/products/2026/08/ so every leaf category has photo-backed stock.
"""

from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


PRODUCTS = (
    # name, category_slug, price, image_path, short_description, benefits, directions, flags
    (
        "Mediheal N.M.F Aquaring Ampoule Face Mask",
        "face-masks",
        "950",
        "products/2026/08/mediheal-nmf-aquaring-ampoule-face-mask-b92d1d4fbc3d.jpg",
        "A hydrating sheet mask selected for a plump, dewy finish in ten minutes.",
        "Deep hydration\nSoft, refreshed feel\nEasy at-home ritual",
        "Apply to clean skin for 10–20 minutes. Pat remaining essence in.",
        (False, False, True, False),
    ),
    (
        "Innisfree Green Tea Seed Hyaluronic Serum Mask",
        "face-masks",
        "1100",
        "products/2026/08/innisfree-green-tea-seed-hyaluronic-serum-mask-38bbb408fe29.jpg",
        "A green-tea sheet mask for a calm, hydrated glow.",
        "Hydrating serum soak\nSoft sheet fit\nFresh after-feel",
        "Leave on for 15–20 minutes, then pat remaining essence in.",
        (False, False, True, False),
    ),
    (
        "COSRX Advanced Snail Mucin Power Sheet Mask",
        "face-masks",
        "1250",
        "products/2026/08/cosrx-advanced-snail-mucin-power-sheet-mask-d9898016c6c3.jpg",
        "A snail-mucin sheet mask for plump, comforted skin.",
        "Barrier-loving care\nPlumping moisture\nGentle everyday use",
        "Apply to clean skin for 10–20 minutes. Massage leftover essence.",
        (True, False, True, False),
    ),
    (
        "Real Techniques Dual-Ended Cleansing Brush",
        "cleansing-brushes",
        "1850",
        "products/2026/08/real-techniques-dual-ended-cleansing-brush-e59d54267838.jpg",
        "A dual-sided cleansing brush for a thorough yet gentle everyday cleanse.",
        "Soft and firm sides\nBuilds a rich lather\nEasy to rinse clean",
        "Wet the brush, add cleanser, massage in circles, then rinse and air-dry.",
        (False, False, True, False),
    ),
    (
        "Soft Silicone Facial Cleansing Brush",
        "cleansing-brushes",
        "2200",
        "products/2026/08/soft-silicone-facial-cleansing-brush-3ca0be958e91.jpg",
        "A soft silicone cleansing brush for a deeper everyday cleanse.",
        "Gentle on skin\nBuilds a rich lather\nEasy to rinse",
        "Wet, add cleanser, massage in circles, rinse and air-dry.",
        (False, False, True, False),
    ),
    (
        "Victoria's Secret Bare Vanilla Fragrance Mist 250ml",
        "body-splash",
        "3200",
        "products/2026/08/victorias-secret-bare-vanilla-fragrance-mist-250ml-6484e399afeb.jpg",
        "A light body mist with warm vanilla notes for an easy all-over scent.",
        "Soft everyday scent\nLayers over fragrance\nWeightless mist",
        "Mist over clean skin from a short distance. Reapply as desired.",
        (True, True, False, True),
    ),
    (
        "Bath & Body Works Japanese Cherry Blossom Fine Fragrance Mist 236ml",
        "body-splash",
        "2900",
        "products/2026/08/bath-body-works-japanese-cherry-blossom-fine-fragr-189fdfb9195a.jpg",
        "A soft floral body mist for light all-over scent.",
        "Everyday freshness\nSoft floral trail\nEasy reapply",
        "Mist onto clean skin from a short distance.",
        (False, True, False, True),
    ),
    (
        "eos Cashmere Body Mist Fresh & Cozy 100ml",
        "body-splash",
        "2400",
        "products/2026/08/eos-cashmere-body-mist-fresh-cozy-100ml-c0ec2ba53e6c.jpg",
        "A cashmere-soft body mist with fresh, cozy notes.",
        "Light body scent\nLayers with body wash\nSoft finish",
        "Spray over pulse points and body after showering.",
        (True, False, True, False),
    ),
    (
        "Gold Rim Oval Sunglasses",
        "sunglasses",
        "2800",
        "products/2026/08/gold-rim-oval-sunglasses-a912cce4e30f.jpg",
        "Lightweight oval sunglasses with a soft gold rim for polished daytime polish.",
        "UV-ready lenses\nLightweight frame\nGiftable silhouette",
        "Wipe lenses with a soft cloth. Store in the pouch when not in wear.",
        (False, False, True, False),
    ),
    (
        "Tortoiseshell Cat-Eye Sunglasses",
        "sunglasses",
        "3100",
        "products/2026/08/tortoiseshell-cat-eye-sunglasses-5b371add3d09.jpg",
        "Classic cat-eye sunglasses with a warm tortoiseshell frame.",
        "Flattering cat-eye shape\nLightweight wear\nEveryday polish",
        "Wipe with a soft cloth and store in the pouch.",
        (True, False, True, False),
    ),
    (
        "Matte Black Round Sunglasses",
        "sunglasses",
        "2650",
        "products/2026/08/matte-black-round-sunglasses-69799f091a55.jpg",
        "Minimal round sunglasses with a matte black finish.",
        "Clean silhouette\nComfortable fit\nGiftable staple",
        "Clean lenses gently. Avoid leaving in direct heat.",
        (False, False, False, True),
    ),
    (
        "Velvet Travel Jewellery Box",
        "jewellery-boxes",
        "2450",
        "products/2026/08/velvet-travel-jewellery-box-fd6a2117e13c.jpg",
        "A compact velvet jewellery box for rings, earrings, and everyday keepsakes.",
        "Travel-friendly size\nSoft lined compartments\nGiftable finish",
        "Store jewellery dry and closed. Wipe the exterior with a soft cloth.",
        (False, False, False, True),
    ),
    (
        "Rose Gold Ring & Earring Jewellery Case",
        "jewellery-boxes",
        "2750",
        "products/2026/08/rose-gold-ring-earring-jewellery-case-086396b9f605.jpg",
        "A slim rose-gold jewellery case for rings and studs.",
        "Compact travel case\nSoft lined interior\nGift-ready look",
        "Keep dry and closed. Wipe exterior with a soft cloth.",
        (False, False, True, False),
    ),
    (
        "Acrylic Bangle Set — Clear Rose",
        "acrylic-bangles",
        "1200",
        "products/2026/08/acrylic-bangle-set-clear-rose-fd6a2117e13c.jpg",
        "A stackable clear-rose acrylic bangle set for easy finishing touches.",
        "Lightweight acrylic\nStackable finish\nEveryday colour pop",
        "Slide on and stack as you like. Wipe with a soft dry cloth.",
        (False, False, True, False),
    ),
    (
        "Acrylic Bangle Trio — Amber Glow",
        "acrylic-bangles",
        "1350",
        "products/2026/08/acrylic-bangle-trio-amber-glow-189fdfb9195a.jpg",
        "Three stackable amber acrylic bangles for warm colour play.",
        "Stackable set\nLightweight acrylic\nWarm amber tones",
        "Slide on and stack. Wipe with a soft dry cloth.",
        (True, False, True, False),
    ),
    (
        "Acrylic Bangle Duo — Soft Blush",
        "acrylic-bangles",
        "1100",
        "products/2026/08/acrylic-bangle-duo-soft-blush-3ca0be958e91.jpg",
        "A soft-blush acrylic bangle duo for everyday finishing touches.",
        "Pretty blush finish\nEasy to stack\nLight on the wrist",
        "Wear alone or stacked. Store flat when not in use.",
        (False, False, True, False),
    ),
    (
        "Victoria's Secret Bare Boob Tape",
        "boob-tape",
        "1650",
        "products/2026/08/victorias-secret-bare-boob-tape-ba5fc288f304.jpg",
        "Body tape selected for secure, flexible hold under backless and strapless looks.",
        "Flexible hold\nLow-profile finish\nEvent-ready support",
        "Apply to clean, dry skin. Remove gently and do not reuse on irritated skin.",
        (False, False, True, False),
    ),
    (
        "Fashion Body Tape Roll — Nude",
        "boob-tape",
        "1450",
        "products/2026/08/fashion-body-tape-roll-nude-2673875e18f4.jpg",
        "A flexible nude body tape roll for strapless and backless looks.",
        "Flexible hold\nLow-profile finish\nEvent ready",
        "Apply to clean dry skin. Remove gently after wear.",
        (False, False, True, False),
    ),
    (
        "eos Shea Better Cashmere Body Wash Vanilla Cashmere 473ml",
        "body-hand-care",
        "2100",
        "products/2026/08/eos-shea-better-cashmere-body-wash-vanilla-cashmer-ba5fc288f304.jpg",
        "A creamy, pH-balanced body wash with whipped vanilla and soft cashmere notes.",
        "Rich foamy cleanse\nShea-butter softness\nLong-wearing scent",
        "Lather over wet skin, rinse thoroughly, and follow with your favourite scent layer.",
        (True, True, True, False),
    ),
    (
        "Dove Shea Butter Warm Vanilla Body Wash 500ml",
        "body-hand-care",
        "1750",
        "products/2026/08/dove-shea-butter-warm-vanilla-body-wash-500ml-086396b9f605.jpg",
        "A nourishing Dove body wash with shea butter and warm vanilla for soft, cared-for skin.",
        "Mild daily cleanse\nShea butter care\nSoft after-shower feel",
        "Massage onto wet skin, rinse well, and pat dry.",
        (True, True, False, False),
    ),
    (
        "Dove Deeply Nourishing Body Wash 500ml",
        "body-hand-care",
        "1650",
        "products/2026/08/dove-deeply-nourishing-body-wash-500ml-2673875e18f4.jpg",
        "A classic Dove body wash for soft, cared-for skin after every shower.",
        "Mild cleanse\nMoisturising feel\nEveryday essential",
        "Lather onto wet skin, rinse thoroughly, and pat dry.",
        (False, True, False, False),
    ),
    (
        "eos Shea Better Hand Cream Vanilla Cashmere 74ml",
        "body-hand-care",
        "950",
        "products/2026/08/eos-shea-better-hand-cream-vanilla-cashmere-74ml-d9898016c6c3.jpg",
        "A fast-absorbing eos hand cream with 24-hour moisture that lasts through hand washing.",
        "24H moisture\nNon-greasy finish\nVanilla cashmere scent",
        "Massage into clean, dry hands whenever they need a boost.",
        (False, False, True, False),
    ),
    (
        "eos Shea Better Hand Cream Fresh & Cozy 74ml",
        "body-hand-care",
        "950",
        "products/2026/08/eos-shea-better-hand-cream-fresh-cozy-74ml-c0ec2ba53e6c.jpg",
        "A lightweight eos hand cream with fresh cozy notes and lasting moisture.",
        "24H moisture\nFast absorbing\nFresh cozy scent",
        "Massage into clean hands whenever they feel dry.",
        (False, False, True, False),
    ),
    (
        "Maybelline Lash Sensational Sky High Mascara",
        "lashes",
        "1850",
        "products/2026/08/maybelline-lash-sensational-sky-high-mascara-e59d54267838.jpg",
        "A lengthening mascara for lifted, defined lashes.",
        "Length and lift\nBuildable definition\nEveryday drama",
        "Sweep from root to tip. Build coats as desired.",
        (True, True, False, True),
    ),
)


def forwards(apps, schema_editor):
    Brand = apps.get_model("catalog", "Brand")
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductImage = apps.get_model("catalog", "ProductImage")

    brand, _ = Brand.objects.get_or_create(
        name="Pretty Affairs Edit",
        defaults={"slug": "pretty-affairs-edit", "is_active": True},
    )
    if not brand.slug:
        brand.slug = "pretty-affairs-edit"
        brand.save(update_fields=["slug"])

    for (
        name,
        category_slug,
        price,
        image_path,
        short_description,
        benefits,
        directions,
        flags,
    ) in PRODUCTS:
        category = Category.objects.filter(slug=category_slug, is_active=True).first()
        if category is None:
            continue
        featured, bestseller, is_new, trending = flags
        product, created = Product.objects.get_or_create(
            name=name,
            defaults={
                "slug": slugify(name)[:220],
                "brand_id": brand.id,
                "short_description": short_description,
                "description": f"{short_description} Curated for the Pretty Affairs Hub edit.",
                "benefits": benefits,
                "directions": directions,
                "specifications": "See packaging for net weight and full details.",
                "ingredients": "See product packaging for the full ingredient list.",
                "price": Decimal(price),
                "stock": 30,
                "sku": f"PAH-{slugify(category.name)[:6].upper()}-{slugify(name)[:8].upper()}",
                "source_name": "Pretty Affairs Edit",
                "is_active": True,
                "is_featured": featured,
                "is_bestseller": bestseller,
                "is_new": is_new,
                "is_trending": trending,
            },
        )
        if not created:
            product.is_active = True
            product.save(update_fields=["is_active"])
        product.categories.set([category])
        if image_path and not product.images.filter(image=image_path).exists():
            if not product.images.filter(image__gt="").exists():
                ProductImage.objects.create(
                    product=product,
                    image=image_path,
                    alt_text=f"{name} product image",
                    sort_order=0,
                )


def backwards(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    names = [row[0] for row in PRODUCTS]
    Product.objects.filter(name__in=names, source_name="Pretty Affairs Edit").update(
        is_active=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_fill_categories_drop_lotions"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
