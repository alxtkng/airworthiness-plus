"""Require recorded cycle readings for each new component fitting."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("components", "0002_component_last_review_fitting"),
    ]

    operations = [
        migrations.AlterField(
            model_name="installation",
            name="airframe_cycles_fitted",
            field=models.PositiveIntegerField("Airframe Cycles When Fitted"),
        ),
        migrations.AlterField(
            model_name="installation",
            name="cycles_at_fitting",
            field=models.PositiveIntegerField("Cycles Since New or Overhaul When Fitted"),
        ),
    ]
