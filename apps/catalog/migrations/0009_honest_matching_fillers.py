"""Retire mismatched branded fillers; keep honest Pretty Affairs products with matching photos."""

from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


MISMATCHED_NAMES = (
    "Mediheal N.M.F Aquaring Ampoule Face Mask",
    "Innisfree Green Tea Seed Hyaluronic Serum Mask",
    "COSRX Advanced Snail Mucin Power Sheet Mask",
    "Real Techniques Dual-Ended Cleansing Brush",
    "Soft Silicone Facial Cleansing Brush",
    "Victoria's Secret Bare Vanilla Fragrance Mist 250ml",
    "Bath & Body Works Japanese Cherry Blossom Fine Fragrance Mist 236ml",
    "eos Cashmere Body Mist Fresh & Cozy 100ml",
    "Gold Rim Oval Sunglasses",
    "Tortoiseshell Cat-Eye Sunglasses",
    "Matte Black Round Sunglasses",
    "Velvet Travel Jewellery Box",
    "Rose Gold Ring & Earring Jewellery Case",
    "Acrylic Bangle Set — Clear Rose",
    "Acrylic Bangle Trio — Amber Glow",
    "Acrylic Bangle Duo — Soft Blush",
    "Victoria's Secret Bare Boob Tape",
    "Fashion Body Tape Roll — Nude",
    "eos Shea Better Cashmere Body Wash Vanilla Cashmere 473ml",
    "Dove Shea Butter Warm Vanilla Body Wash 500ml",
    "Dove Deeply Nourishing Body Wash 500ml",
    "eos Shea Better Hand Cream Vanilla Cashmere 74ml",
    "eos Shea Better Hand Cream Fresh & Cozy 74ml",
    "Maybelline Lash Sensational Sky High Mascara",
)

HONEST_PRODUCTS = (
    (
        "Pretty Affairs Hydrating Sheet Mask",
        "face-masks",
        "950",
        "products/2026/08/pretty-affairs-hydrating-sheet-mask-40fa86ec.png",
        "A hydrating sheet mask for a plump, dewy finish.",
        "Deep hydration\nSoft refreshed feel\nEasy at-home ritual",
        "Apply to clean skin for 10-20 minutes. Pat remaining essence in.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Green Tea Calm Mask",
        "face-masks",
        "1100",
        "products/2026/08/pretty-affairs-green-tea-calm-mask-7f7ed2de.png",
        "A green-tea sheet mask for calm, comforted skin.",
        "Soothing green tea\nSoft sheet fit\nFresh after-feel",
        "Leave on for 15-20 minutes, then pat remaining essence in.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Dual-Ended Cleansing Brush",
        "cleansing-brushes",
        "1850",
        "products/2026/08/pretty-affairs-dual-ended-cleansing-brush-48ff4376.png",
        "A dual-ended cleansing brush for a gentle everyday cleanse.",
        "Soft and firm sides\nBuilds a rich lather\nEasy to rinse",
        "Wet the brush, add cleanser, massage in circles, then rinse and air-dry.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Soft Silicone Cleansing Brush",
        "cleansing-brushes",
        "2200",
        "products/2026/08/pretty-affairs-soft-silicone-cleansing-brush-974be99d.png",
        "A soft silicone cleansing brush for a deeper daily cleanse.",
        "Gentle silicone bristles\nRich lather\nEasy to rinse",
        "Wet, add cleanser, massage in circles, rinse and air-dry.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Vanilla Soft Body Mist 200ml",
        "body-splash",
        "2800",
        "products/2026/08/pretty-affairs-vanilla-soft-body-mist-200ml-966746a8.png",
        "A light vanilla body mist for soft all-over scent.",
        "Soft everyday scent\nWeightless mist\nEasy reapply",
        "Mist over clean skin from a short distance.",
        (True, True, False, True),
    ),
    (
        "Pretty Affairs Cherry Blossom Body Mist 200ml",
        "body-splash",
        "2800",
        "products/2026/08/pretty-affairs-cherry-blossom-body-mist-200ml-4743c234.png",
        "A soft floral body mist with cherry-blossom notes.",
        "Fresh floral trail\nLight body scent\nEveryday polish",
        "Mist onto clean skin from a short distance.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Gold Rim Oval Sunglasses",
        "sunglasses",
        "2800",
        "products/2026/08/pretty-affairs-gold-rim-oval-sunglasses-713ef2fc.png",
        "Thin gold-rim oval sunglasses for polished daytime wear.",
        "Oval silhouette\nLightweight frame\nEveryday polish",
        "Wipe lenses with a soft cloth. Store in a pouch when not in wear.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Matte Black Round Sunglasses",
        "sunglasses",
        "2650",
        "products/2026/08/pretty-affairs-matte-black-round-sunglasses-ee45fa38.png",
        "Minimal matte-black round sunglasses.",
        "Clean silhouette\nComfortable fit\nGiftable staple",
        "Clean lenses gently. Avoid leaving in direct heat.",
        (False, False, False, True),
    ),
    (
        "Pretty Affairs Velvet Travel Jewellery Box",
        "jewellery-boxes",
        "2450",
        "products/2026/08/pretty-affairs-velvet-travel-jewellery-box-83de02ec.png",
        "A blush velvet travel jewellery box for rings and studs.",
        "Travel-friendly size\nSoft lined compartments\nGiftable finish",
        "Store jewellery dry and closed. Wipe the exterior with a soft cloth.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Rose Gold Jewellery Case",
        "jewellery-boxes",
        "2750",
        "products/2026/08/pretty-affairs-rose-gold-jewellery-case-320dcb2f.png",
        "A slim rose-gold jewellery case for everyday keepsakes.",
        "Compact case\nSoft lined interior\nGift-ready look",
        "Keep dry and closed. Wipe exterior with a soft cloth.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Acrylic Bangle Set - Clear Rose",
        "acrylic-bangles",
        "1200",
        "products/2026/08/pretty-affairs-acrylic-bangle-set-clear-rose-69bba07f.png",
        "Stackable clear-rose acrylic bangles for easy finishing touches.",
        "Lightweight acrylic\nStackable finish\nSoft rose tint",
        "Slide on and stack as you like. Wipe with a soft dry cloth.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Acrylic Bangle Duo - Soft Blush",
        "acrylic-bangles",
        "1100",
        "products/2026/08/pretty-affairs-acrylic-bangle-duo-soft-blush-ae0c58c3.png",
        "A soft-blush acrylic bangle duo for everyday colour.",
        "Pretty blush finish\nEasy to stack\nLight on the wrist",
        "Wear alone or stacked. Store flat when not in use.",
        (False, False, True, False),
    ),
    (
        "Pretty Affairs Body Tape - Nude",
        "boob-tape",
        "1650",
        "products/2026/08/pretty-affairs-body-tape-nude-1f1e9316.png",
        "Flexible nude body tape for strapless and backless looks.",
        "Flexible hold\nLow-profile finish\nEvent ready",
        "Apply to clean, dry skin. Remove gently after wear.",
        (True, False, True, False),
    ),
    (
        "Pretty Affairs Vanilla Cashmere Body Wash 500ml",
        "body-hand-care",
        "2100",
        "products/2026/08/pretty-affairs-vanilla-cashmere-body-wash-500ml-321087d9.png",
        "A creamy vanilla body wash for a soft, scented cleanse.",
        "Rich foamy cleanse\nSoft after-feel\nWarm vanilla notes",
        "Lather over wet skin, rinse thoroughly, and pat dry.",
        (True, True, True, False),
    ),
    (
        "Pretty Affairs Daily Nourish Body Wash 500ml",
        "body-hand-care",
        "1750",
        "products/2026/08/pretty-affairs-daily-nourish-body-wash-500ml-b0ddbb7e.png",
        "A gentle everyday body wash for soft, cared-for skin.",
        "Mild daily cleanse\nMoisturising feel\nFresh finish",
        "Massage onto wet skin, rinse well, and pat dry.",
        (False, True, False, False),
    ),
    (
        "Pretty Affairs Shea Soft Hand Cream 75ml",
        "body-hand-care",
        "950",
        "products/2026/08/pretty-affairs-shea-soft-hand-cream-75ml-a8f120fb.png",
        "A fast-absorbing shea hand cream for lasting softness.",
        "Shea softness\nNon-greasy finish\nEveryday comfort",
        "Massage into clean, dry hands whenever they need a boost.",
        (True, False, True, False),
    ),
)


def forwards(apps, schema_editor):
    Brand = apps.get_model("catalog", "Brand")
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductImage = apps.get_model("catalog", "ProductImage")

    Product.objects.filter(name__in=MISMATCHED_NAMES).update(is_active=False)
    # Catch encoding variants of acrylic / tape names from earlier seeds.
    Product.objects.filter(source_name="Pretty Affairs Edit", is_active=True).exclude(
        name__startswith="Pretty Affairs "
    ).update(is_active=False)

    brand, _ = Brand.objects.get_or_create(
        name="Pretty Affairs Edit",
        defaults={"slug": "pretty-affairs-edit", "is_active": True},
    )

    for (
        name,
        category_slug,
        price,
        image_path,
        short_description,
        benefits,
        directions,
        flags,
    ) in HONEST_PRODUCTS:
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
        if image_path and not product.images.filter(image__gt="").exists():
            ProductImage.objects.create(
                product=product,
                image=image_path,
                alt_text=f"{name} product image",
                sort_order=0,
            )


def backwards(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    names = [row[0] for row in HONEST_PRODUCTS]
    Product.objects.filter(name__in=names).update(is_active=False)
    Product.objects.filter(name__in=MISMATCHED_NAMES).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0008_imaged_category_fillers"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
