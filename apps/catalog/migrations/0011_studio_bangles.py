"""Retire stand-in bangles; publish the studio bangle photos with shop prices."""

from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


PLACEHOLDER_NAMES = (
    "Pretty Affairs Acrylic Bangle Set - Clear Rose",
    "Pretty Affairs Acrylic Bangle Duo - Soft Blush",
    "Acrylic Bangle Set — Clear Rose",
    "Acrylic Bangle Trio — Amber Glow",
    "Acrylic Bangle Duo — Soft Blush",
)

DIRECTIONS = "Slide on over a relaxed hand. Wipe with a soft dry cloth and store away from heat."

# name, price, image_path, short description, benefits, flags
BANGLES = (
    (
        "Marbled Resin Bangle Trio - Cocoa, Cream & Ivory",
        "400",
        "products/2026/08/marbled-resin-bangle-trio-cocoa-cream-ivory.jpeg",
        "Three squared resin bangles in cocoa, cream marble and veined ivory.",
        "Soft neutral palette\nSquared sculpted shape\nWears alone or stacked",
        (True, False, True, True),
    ),
    (
        "Tortoise & Gold Bangle Stack",
        "400",
        "products/2026/08/tortoise-gold-bangle-stack.jpeg",
        "A cream marble, polished gold and tortoiseshell bangle set for warm stacking.",
        "Mixed metal and resin\nWarm tortoiseshell finish\nEasy evening polish",
        (False, True, True, False),
    ),
    (
        "Sculpted Bangle Duo - Cream & Merlot",
        "400",
        "products/2026/08/sculpted-bangle-duo-cream-merlot.jpeg",
        "Two chunky sculpted bangles in cream marble and deep merlot.",
        "Organic sculpted curve\nRich colour pairing\nSubstantial without weight",
        (False, False, True, False),
    ),
    (
        "Wide Amber Tortoise Bangle Set",
        "600",
        "products/2026/08/wide-amber-tortoise-bangle-set.jpeg",
        "A set of five wide glossy bangles in amber, tortoise and cream tones.",
        "Wide statement cuff shape\nHigh-gloss finish\nFive tones to mix",
        (False, False, True, False),
    ),
    (
        "Glossy Colour Pop Chunky Bangle",
        "400",
        "products/2026/08/glossy-colour-pop-chunky-bangle.jpeg",
        "A chunky high-shine bangle available across bright and neutral shades.",
        "Bold glossy colour\nRounded chunky profile\nMany shades to choose",
        (False, False, True, False),
    ),
    (
        "Pastel Marble Square Bangle",
        "650",
        "products/2026/08/pastel-marble-square-bangle.jpeg",
        "A squared marbled bangle in soft pastels, clear and amber finishes.",
        "Soft marbled pastels\nSquared silhouette\nLight on the wrist",
        (False, False, True, False),
    ),
    (
        "Sculpted Swirl Bangle Trio - Pearl, Cream & Coral",
        "750",
        "products/2026/08/sculpted-swirl-bangle-trio-pearl-cream-coral.jpeg",
        "Three sculpted swirl bangles in pearl white, cream and coral orange.",
        "Hand-finished swirl effect\nSmooth sculpted curve\nStacks beautifully",
        (False, False, True, False),
    ),
)


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


def forwards(apps, schema_editor):
    Brand = apps.get_model("catalog", "Brand")
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductImage = apps.get_model("catalog", "ProductImage")
    ProductVariant = apps.get_model("catalog", "ProductVariant")

    Product.objects.filter(name__in=PLACEHOLDER_NAMES).update(is_active=False)

    category = Category.objects.filter(slug="acrylic-bangles", is_active=True).first()
    if category is None:
        return

    brand, _ = Brand.objects.get_or_create(
        name="Pretty Affairs Edit",
        defaults={"slug": "pretty-affairs-edit", "is_active": True},
    )

    for name, price, image_path, short_description, benefits, flags in BANGLES:
        featured, bestseller, is_new, trending = flags
        shades = SHADES.get(name, ())
        # Stock lives on the variants once a listing has shades to pick from.
        stock = 0 if shades else 15
        product = Product.objects.filter(name=name).first()
        if product is None:
            product = Product(
                name=name,
                slug=slugify(name)[:220],
                brand_id=brand.id,
                short_description=short_description,
                description=f"{short_description} Curated for the Pretty Affairs Hub edit.",
                benefits=benefits,
                directions=DIRECTIONS,
                specifications="Resin bangle. One size, slip-on fit.",
                ingredients="",
                price=Decimal(price),
                stock=stock,
                sku=f"PAH-BANGLE-{slugify(name)[:7].upper()}",
                source_name="Pretty Affairs Studio",
                is_active=True,
                is_featured=featured,
                is_bestseller=bestseller,
                is_new=is_new,
                is_trending=trending,
            )
            product.save()
        else:
            product.is_active = True
            product.price = Decimal(price)
            product.short_description = short_description
            product.source_name = "Pretty Affairs Studio"
            product.stock = stock
            product.save()
        product.categories.set([category])
        if image_path and not product.images.filter(image__gt="").exists():
            ProductImage.objects.create(
                product=product,
                image=image_path,
                alt_text=f"{name} product image",
                sort_order=0,
            )
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


def backwards(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Product.objects.filter(name__in=[row[0] for row in BANGLES]).update(is_active=False)
    Product.objects.filter(name__in=PLACEHOLDER_NAMES).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0010_shade_edit_sunglasses"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
