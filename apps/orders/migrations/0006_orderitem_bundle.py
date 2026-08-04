# Generated manually for bundle-as-single-order-line

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_studio_bangles"),
        ("orders", "0005_whatsapp_lead_pending_queue"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="bundle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="catalog.bundle",
            ),
        ),
    ]
