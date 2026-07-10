# Generated manually for appointment-backed time logs

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_payment"),
    ]

    operations = [
        migrations.AddField(
            model_name="timelog",
            name="appointment",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="time_log",
                to="core.appointment",
            ),
        ),
    ]
