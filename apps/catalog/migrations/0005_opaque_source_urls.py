import re

from django.db import migrations

HANDLE_PATTERNS = (
    (re.compile(r"https?://[^/]+/products/(?P<handle>[^/?#]+)", re.I), "feed-a/products/{handle}"),
    (re.compile(r"https?://[^/]+/product-page/(?P<slug>[^/?#]+)", re.I), "feed-b/product-page/{slug}"),
)


def rewrite_source_urls(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for product in Product.objects.exclude(source_url="").iterator():
        url = product.source_url
        if url.startswith("https://catalog-import/"):
            continue
        for pattern, template in HANDLE_PATTERNS:
            match = pattern.search(url)
            if match:
                product.source_url = f"https://catalog-import/{template.format(**match.groupdict())}"[:500]
                product.save(update_fields=["source_url"])
                break


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_rename_supplier_labels"),
    ]

    operations = [
        migrations.RunPython(rewrite_source_urls, noop),
    ]
