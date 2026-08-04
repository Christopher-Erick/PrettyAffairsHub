# Generated manually for bundle-as-single-cart-line

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0001_initial"),
        ("catalog", "0011_studio_bangles"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="cartitem",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="catalog.product",
            ),
        ),
        migrations.AddField(
            model_name="cartitem",
            name="bundle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="catalog.bundle",
            ),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("bundle__isnull", False),
                    ("product__isnull", True),
                )
                | models.Q(
                    ("bundle__isnull", True),
                    ("product__isnull", False),
                ),
                name="cartitem_product_xor_bundle",
            ),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(("bundle__isnull", True)),
                fields=("cart", "product", "variant"),
                name="uniq_cart_product_variant",
            ),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(("bundle__isnull", False)),
                fields=("cart", "bundle"),
                name="uniq_cart_bundle",
            ),
        ),
    ]
