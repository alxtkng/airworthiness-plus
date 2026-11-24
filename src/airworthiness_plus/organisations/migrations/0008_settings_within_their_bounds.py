"""The most a lead time or a default limit may be is held by the database (REQ-212 to REQ-214).

Independent recompute of 24 November 2026: "at most 365" was held only by
the form. No value stored through the form is above its bound.
"""

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0007_settings"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="organisation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("due_soon_days__lte", 365),
                    ("due_soon_hours__lte", Decimal("999.9")),
                    ("due_soon_cycles__lte", 9999),
                    models.Q(
                        ("review_alert_days__isnull", True),
                        ("review_alert_days__lte", 365),
                        _connector="OR",
                    ),
                    ("deferral_days_non_required__lte", 365),
                    ("deferral_days_with_agreement__lte", 365),
                    ("deferral_days_certifying_staff__lte", 365),
                ),
                name="organisation_settings_are_within_their_bounds",
            ),
        ),
    ]
