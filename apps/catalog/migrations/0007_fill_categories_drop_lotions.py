"""Retire body lotions and ensure every live leaf category has stock.

Body lotions are out of assortment; hand creams stay. Empty leaves get one
researched starter SKU each, plus eos and Dove body washes under Body & Hand Care.
"""

from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


LOTION_NAME_FRAGMENTS = (
    "body lotion",
    "body milk",
    "body cream",
    "body butter",
)

# (name, category_slug, price, short_description, benefits, directions, specs, flags)
# flags: featured, bestseller, new, trending
STARTER_PRODUCTS = (
    (
        "Mediheal N.M.F Aquaring Ampoule Face Mask",
        "face-masks",
        "950",
        "A hydrating sheet mask selected for a plump, dewy finish in ten minutes.",
        "Deep hydration\nSoft, refreshed feel\nEasy at-home ritual",
        "Apply to clean skin for 10–20 minutes. Pat remaining essence in.",
        "1 sheet mask · Suitable for most skin types",
        (False, False, True, False),
    ),
    (
        "Real Techniques Dual-Ended Cleansing Brush",
        "cleansing-brushes",
        "1850",
        "A dual-sided cleansing brush for a thorough yet gentle everyday cleanse.",
        "Soft and firm sides\nBuilds a rich lather\nEasy to rinse clean",
        "Wet the brush, add cleanser, massage in circles, then rinse and air-dry.",
        "Dual-ended brush · Synthetic fibres",
        (False, False, True, False),
    ),
    (
        "Victoria's Secret Bare Vanilla Fragrance Mist 250ml",
        "body-splash",
        "3200",
        "A light body mist with warm vanilla notes for an easy all-over scent.",
        "Soft everyday scent\nLayers over fragrance\nWeightless mist",
        "Mist over clean skin from a short distance. Reapply as desired.",
        "250 ml fragrance mist",
        (True, True, False, True),
    ),
    (
        "Gold Rim Oval Sunglasses",
        "sunglasses",
        "2800",
        "Lightweight oval sunglasses with a soft gold rim for polished daytime polish.",
        "UV-ready lenses\nLightweight frame\nGiftable silhouette",
        "Wipe lenses with a soft cloth. Store in the pouch when not in wear.",
        "One size · Includes soft pouch",
        (False, False, True, False),
    ),
    (
        "Velvet Travel Jewellery Box",
        "jewellery-boxes",
        "2450",
        "A compact velvet jewellery box for rings, earrings, and everyday keepsakes.",
        "Travel-friendly size\nSoft lined compartments\nGiftable finish",
        "Store jewellery dry and closed. Wipe the exterior with a soft cloth.",
        "Compact travel jewellery box",
        (False, False, False, True),
    ),
    (
        "Acrylic Bangle Set — Clear Rose",
        "acrylic-bangles",
        "1200",
        "A stackable clear-rose acrylic bangle set for easy finishing touches.",
        "Lightweight acrylic\nStackable finish\nEveryday colour pop",
        "Slide on and stack as you like. Wipe with a soft dry cloth.",
        "Set of stackable acrylic bangles",
        (False, False, True, False),
    ),
    (
        "Victoria's Secret Bare Boob Tape",
        "boob-tape",
        "1650",
        "Body tape selected for secure, flexible hold under backless and strapless looks.",
        "Flexible hold\nLow-profile finish\nEvent-ready support",
        "Apply to clean, dry skin. Remove gently and do not reuse on irritated skin.",
        "One-size boob tape roll",
        (False, False, True, False),
    ),
    (
        "eos Shea Better Cashmere Body Wash Vanilla Cashmere 473ml",
        "body-hand-care",
        "2100",
        "A creamy, pH-balanced body wash with whipped vanilla and soft cashmere notes.",
        "Rich foamy cleanse\nShea-butter softness\nLong-wearing scent",
        "Lather over wet skin, rinse thoroughly, and follow with your favourite scent layer.",
        "16 fl oz / 473 ml body wash",
        (True, True, True, False),
    ),
    (
        "Dove Shea Butter Warm Vanilla Body Wash 500ml",
        "body-hand-care",
        "1750",
        "A nourishing Dove body wash with shea butter and warm vanilla for soft, cared-for skin.",
        "Mild daily cleanse\nShea butter care\nSoft after-shower feel",
        "Massage onto wet skin, rinse well, and pat dry.",
        "500 ml body wash",
        (True, True, False, False),
    ),
    (
        "eos Shea Better Hand Cream Vanilla Cashmere 74ml",
        "body-hand-care",
        "950",
        "A fast-absorbing eos hand cream with 24-hour moisture that lasts through hand washing.",
        "24H moisture\nNon-greasy finish\nVanilla cashmere scent",
        "Massage into clean, dry hands whenever they need a boost.",
        "2.5 oz / 74 ml hand cream",
        (False, False, True, False),
    ),
)


def _retire_lotions(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for product in Product.objects.filter(is_active=True):
        lowered = product.name.lower()
        if any(fragment in lowered for fragment in LOTION_NAME_FRAGMENTS):
            product.is_active = False
            product.save(update_fields=["is_active"])


def _seed_starters(apps, schema_editor):
    Brand = apps.get_model("catalog", "Brand")
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")

    brand, created = Brand.objects.get_or_create(
        name="Pretty Affairs Edit",
        defaults={"is_active": True, "slug": "pretty-affairs-edit"},
    )
    if not brand.slug:
        brand.slug = "pretty-affairs-edit"
        brand.save(update_fields=["slug"])

    for (
        name,
        category_slug,
        price,
        short_description,
        benefits,
        directions,
        specs,
        flags,
    ) in STARTER_PRODUCTS:
        category = Category.objects.filter(slug=category_slug, is_active=True).first()
        if category is None:
            continue
        featured, bestseller, is_new, trending = flags
        product_slug = slugify(name)[:220]
        product, created = Product.objects.get_or_create(
            name=name,
            defaults={
                "slug": product_slug,
                "brand_id": brand.id,
                "short_description": short_description,
                "description": f"{short_description} Curated for the Pretty Affairs Hub edit.",
                "benefits": benefits,
                "directions": directions,
                "specifications": specs,
                "ingredients": "See product packaging for the full ingredient list.",
                "price": Decimal(price),
                "stock": 35,
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
            product.price = Decimal(price)
            product.short_description = short_description
            product.description = f"{short_description} Curated for the Pretty Affairs Hub edit."
            product.benefits = benefits
            product.directions = directions
            product.specifications = specs
            product.is_featured = featured
            product.is_bestseller = bestseller
            product.is_new = is_new
            product.is_trending = trending
            product.save()
        product.categories.set([category])


def forwards(apps, schema_editor):
    _retire_lotions(apps, schema_editor)
    _seed_starters(apps, schema_editor)


def backwards(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    names = [row[0] for row in STARTER_PRODUCTS]
    Product.objects.filter(name__in=names).update(is_active=False)
    for product in Product.objects.filter(is_active=False):
        lowered = product.name.lower()
        if any(fragment in lowered for fragment in LOTION_NAME_FRAGMENTS):
            product.is_active = True
            product.save(update_fields=["is_active"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_body_and_hand_care_category"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
