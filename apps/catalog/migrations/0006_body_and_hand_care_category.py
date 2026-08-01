"""Give body lotions, hand creams, and shower oils a category of their own.

The importer used to match scent-line names such as "Rose Envoutante" under Perfumes
before it looked for the product form, so body care items from a fragrance line were
filed as perfumes. The rest landed in Body Splash, which is a mist, not a lotion.
"""

from django.db import migrations


PARENT_NAME = "Body Essentials"
LEAF_NAME = "Body & Hand Care"
LEAF_SLUG = "body-hand-care"

MISFILED_IN = ("perfumes", "body-splash", "cologne")

BODY_CARE_FORMS = (
    "body lotion",
    "body milk",
    "body cream",
    "body butter",
    "body scrub",
    "body wash",
    "hand cream",
    "hand lotion",
    "hand balm",
    "shower oil",
    "shower gel",
    "shower cream",
    "bath oil",
)

COPY = (
    "A nourishing body and hand treat selected for softness that lasts.",
    "Deeply conditioning\nSilky, non-greasy finish\nSubtle lingering scent",
    "Massage into clean, dry skin and allow to absorb. Reapply as often as you like.",
)


def move_body_care(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")

    parent = Category.objects.filter(slug="body-essentials").first()
    if parent is None:
        parent = Category.objects.create(
            name=PARENT_NAME,
            slug="body-essentials",
            is_active=True,
            sort_order=7,
            description=f"Shop {PARENT_NAME.lower()} at Pretty Affairs Hub.",
        )

    leaf, _ = Category.objects.update_or_create(
        slug=LEAF_SLUG,
        defaults={
            "name": LEAF_NAME,
            "parent": parent,
            "is_active": True,
            "sort_order": 1,
            "description": f"{LEAF_NAME} in the {PARENT_NAME} edit.",
        },
    )
    Category.objects.filter(slug="boob-tape").update(sort_order=2)

    description, benefits, directions = COPY
    candidates = Product.objects.filter(categories__slug__in=MISFILED_IN).distinct()
    for product in candidates:
        lowered = product.name.lower()
        if not any(form in lowered for form in BODY_CARE_FORMS):
            continue
        product.categories.set([leaf])
        product.short_description = description[:255]
        product.description = f"{description} Curated for the Pretty Affairs Hub edit."
        product.benefits = benefits
        product.directions = directions
        product.save(
            update_fields=["short_description", "description", "benefits", "directions"]
        )


def reverse_body_care(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")

    leaf = Category.objects.filter(slug=LEAF_SLUG).first()
    if leaf is None:
        return
    perfumes = Category.objects.filter(slug="perfumes").first()
    if perfumes is not None:
        for product in Product.objects.filter(categories=leaf):
            product.categories.set([perfumes])
    Category.objects.filter(slug="boob-tape").update(sort_order=1)
    leaf.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_opaque_source_urls"),
    ]

    operations = [
        migrations.RunPython(move_body_care, reverse_body_care),
    ]
