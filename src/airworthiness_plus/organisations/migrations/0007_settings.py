"""An earlier alert for review certificates, and default deferral limits (REQ-213, REQ-214)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0006_approvals_held"),
    ]

    operations = [
        migrations.AddField(
            model_name="organisation",
            name="deferral_days_certifying_staff",
            field=models.PositiveSmallIntegerField(db_default=30),
        ),
        migrations.AddField(
            model_name="organisation",
            name="deferral_days_non_required",
            field=models.PositiveSmallIntegerField(db_default=30),
        ),
        migrations.AddField(
            model_name="organisation",
            name="deferral_days_with_agreement",
            field=models.PositiveSmallIntegerField(db_default=30),
        ),
        migrations.AddField(
            model_name="organisation",
            name="review_alert_days",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="organisation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("review_alert_days__isnull", True),
                    ("review_alert_days__gt", models.F("due_soon_days")),
                    _connector="OR",
                ),
                name="organisation_review_alert_is_the_earlier",
            ),
        ),
        migrations.AddConstraint(
            model_name="organisation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("deferral_days_non_required__gte", 1),
                    ("deferral_days_with_agreement__gte", 1),
                    ("deferral_days_certifying_staff__gte", 1),
                ),
                name="organisation_deferral_limits_are_at_least_a_day",
            ),
        ),
    ]
