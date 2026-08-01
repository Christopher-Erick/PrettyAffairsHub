"""Retire placeholder sunglasses; publish the assortment with clean studio photos."""

from decimal import Decimal

from django.db import migrations
from django.utils.text import slugify


PLACEHOLDER_NAMES = (
    "Pretty Affairs Gold Rim Oval Sunglasses",
    "Pretty Affairs Matte Black Round Sunglasses",
    "Gold Rim Oval Sunglasses",
    "Tortoiseshell Cat-Eye Sunglasses",
    "Matte Black Round Sunglasses",
)

DIRECTIONS = "Wipe lenses with a soft cloth. Store in a case and keep out of direct heat."

# legacy_key, name, price, image_path, short description, benefits, flags
SUNGLASSES = (
    (
        "DaYTKMYDIdr",
        "Classic Wayfarer Sunglasses - Matte Black, Green Lens",
        "12500",
        "products/2026/08/classic-wayfarer-sunglasses-matte-black-green-lens.png",
        "The classic wayfarer in matte black with deep green lenses. Unisex.",
        "Timeless wayfarer shape\nDeep green lens tint\nUnisex fit",
        (True, False, True, True),
    ),
    (
        "DZWlFbIjAKI",
        "Rimless Sport Sunglasses - Black, Grey Lens",
        "12450",
        "products/2026/08/rimless-sport-sunglasses-black-grey-lens.png",
        "Featherlight rimless sport frames in black with polarised grey lenses. Unisex.",
        "Polarised glare control\nBarely-there weight\nWraps close to the face",
        (False, True, True, False),
    ),
    (
        "DZVOvy2DMWm",
        "Semi-Rimless Sunglasses - Dark Tortoise, Bronze Lens",
        "12450",
        "products/2026/08/semi-rimless-sunglasses-dark-tortoise-bronze-lens.png",
        "Semi-rimless frames with a dark tortoise brow and warm bronze lenses.",
        "Warm bronze tint\nTortoise brow detail\nEasy everyday shape",
        (False, False, True, False),
    ),
    (
        "DZUYYokjL8D",
        "Featherweight Rimless Sunglasses - Brown, Bronze Lens",
        "12450",
        "products/2026/08/featherweight-rimless-sunglasses-brown-bronze-lens.png",
        "Fully rimless brown frames with polarised bronze lenses. Unisex.",
        "Polarised bronze lenses\nRimless and featherlight\nUnisex fit",
        (False, False, True, False),
    ),
    (
        "DWTGY5dDKJu",
        "Rimless Cat-Eye Sunglasses - Black, Smoke Lens",
        "12450",
        "products/2026/08/rimless-cat-eye-sunglasses-black-smoke-lens.png",
        "Rimless frames with a softly upswept lens and smoke grey tint.",
        "Soft cat-eye lift\nRimless finish\nSmoke grey tint",
        (False, False, True, False),
    ),
    (
        "DWEu9fqDKdW",
        "Reverse Wayfarer Sunglasses - Transparent Blue",
        "12500",
        "products/2026/08/reverse-wayfarer-sunglasses-transparent-blue.png",
        "Reverse wayfarers in a transparent blue frame with blue lenses.",
        "Transparent blue frame\nReverse wayfarer curve\nStatement colour",
        (False, False, True, False),
    ),
    (
        "DV-_uOAjHd-",
        "Rimless Rectangular Sunglasses - Black, Smoke Lens",
        "12450",
        "products/2026/08/rimless-rectangular-sunglasses-black-smoke-lens.png",
        "All-black rimless rectangular frames with polarised smoke lenses.",
        "Polarised smoke lenses\nClean rimless lines\nAll-black finish",
        (False, False, False, True),
    ),
    (
        "DM18yU3ofg_",
        "Sport Sunglasses - Amber Tortoise, Bronze Lens",
        "12450",
        "products/2026/08/sport-sunglasses-amber-tortoise-bronze-lens.png",
        "Sport frames with amber tortoise temples and polarised bronze lenses.",
        "Polarised bronze lenses\nAmber tortoise temples\nSecure sport fit",
        (False, False, True, False),
    ),
)


def forwards(apps, schema_editor):
    Brand = apps.get_model("catalog", "Brand")
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductImage = apps.get_model("catalog", "ProductImage")

    Product.objects.filter(name__in=PLACEHOLDER_NAMES).update(is_active=False)

    category = Category.objects.filter(slug="sunglasses", is_active=True).first()
    if category is None:
        return

    brand, _ = Brand.objects.get_or_create(
        name="Pretty Affairs Edit",
        defaults={"slug": "pretty-affairs-edit", "is_active": True},
    )

    for (
        legacy_key,
        name,
        price,
        image_path,
        short_description,
        benefits,
        flags,
    ) in SUNGLASSES:
        featured, bestseller, is_new, trending = flags
        source_url = f"https://catalog-import/feed-shade/p/{legacy_key}"
        product = Product.objects.filter(source_url=source_url).first()
        if product is None:
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
                specifications="Unisex fit. Full UV protection. Case included.",
                ingredients="",
                price=Decimal(price),
                stock=8,
                sku=f"PAH-SUNGLA-{slugify(name)[:7].upper()}",
                source_name="Shade Edit",
                source_url=source_url,
                is_active=True,
                is_featured=featured,
                is_bestseller=bestseller,
                is_new=is_new,
                is_trending=trending,
            )
            product.save()
        else:
            product.name = name
            product.slug = slugify(name)[:220]
            product.short_description = short_description
            product.price = Decimal(price)
            product.source_name = "Shade Edit"
            product.source_url = source_url
            product.is_active = True
            product.save()
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
    Product.objects.filter(name__in=[row[1] for row in SUNGLASSES]).update(is_active=False)
    Product.objects.filter(name__in=PLACEHOLDER_NAMES).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0009_honest_matching_fillers"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
