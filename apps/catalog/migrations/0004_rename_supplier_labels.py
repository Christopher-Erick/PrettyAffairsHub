from django.db import migrations


SOURCE_MAP = {
    "The Lip Tribe": "Atelier Edit",
    "Lintons Beauty": "Harbour Edit",
}

BRAND_MAP = {
    "The Lip Tribe": "Pretty Affairs Edit",
    "The Lip Tribe Edit": "Pretty Affairs Edit",
    "Lintons Beauty": "Pretty Affairs Edit",
}


def rename_sources(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Brand = apps.get_model("catalog", "Brand")
    for old, new in SOURCE_MAP.items():
        Product.objects.filter(source_name=old).update(source_name=new)
    for old, new in BRAND_MAP.items():
        Brand.objects.filter(name=old).update(name=new)


def reverse_sources(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Brand = apps.get_model("catalog", "Brand")
    for old, new in SOURCE_MAP.items():
        Product.objects.filter(source_name=new).update(source_name=old)
    # Brands may have been merged by name; reverse best-effort only.
    Brand.objects.filter(name="Pretty Affairs Edit").update(name="The Lip Tribe")


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_strip_source_from_descriptions"),
    ]

    operations = [
        migrations.RunPython(rename_sources, reverse_sources),
    ]
