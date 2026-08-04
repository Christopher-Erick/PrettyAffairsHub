from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0002_cartitem_bundle_line"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartitem",
            name="ritual_group",
            field=models.CharField(blank=True, db_index=True, default="", max_length=36),
        ),
    ]
