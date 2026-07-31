import re

from django.db import migrations

SOURCE_SENTENCE = re.compile(
    r"\s*Selected from .{1,120}? for the Pretty Affairs Hub edit\.", re.IGNORECASE
)
REPLACEMENT = " Curated for the Pretty Affairs Hub edit."


def strip_source_mentions(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for product in Product.objects.filter(description__contains="Selected from").iterator():
        cleaned = SOURCE_SENTENCE.sub(REPLACEMENT, product.description).strip()
        if cleaned != product.description:
            product.description = cleaned
            product.save(update_fields=["description"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_product_sources_and_variant_swatches"),
    ]

    operations = [
        migrations.RunPython(strip_source_mentions, noop),
    ]
