# Generated manually for appointment pricing and appointment-backed payments

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_timelog_appointment"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="payment",
            name="appointment",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="payment",
                to="core.appointment",
            ),
        ),
    ]
