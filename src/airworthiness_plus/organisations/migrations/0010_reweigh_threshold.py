"""The reweigh threshold: a setting the organisation keeps, with no default (REQ-257)."""

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0009_set_up_approval_fixed"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="reweigh_threshold_kilograms",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True),
        ),
        migrations.AddConstraint(
            model_name="organisation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("reweigh_threshold_kilograms__isnull", True),
                    models.Q(
                        ("reweigh_threshold_kilograms__gt", 0),
                        ("reweigh_threshold_kilograms__lte", Decimal("999.9")),
                    ),
                    _connector="OR",
                ),
                name="organisation_reweigh_threshold_above_zero_and_within_bounds",
            ),
        ),
    ]
