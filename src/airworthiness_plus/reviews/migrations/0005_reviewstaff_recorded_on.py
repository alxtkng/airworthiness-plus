"""The day a person was recorded as review staff, which bounds their reviews before these records."""

import datetime

from django.db import migrations, models

from airworthiness_plus.reviews import sql


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0004_certificates_from_before"),
    ]

    operations = [
        # A person already recorded is taken as recorded today. Their last review
        # before these records was entered on or before today, so the rule holds.
        migrations.AddField(
            model_name="reviewstaff",
            name="recorded_on",
            field=models.DateField(
                default=datetime.date.today, verbose_name="Recorded as Review Staff"
            ),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name="reviewstaff",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("last_review_before_records__isnull", True),
                    ("last_review_before_records__lte", models.F("recorded_on")),
                    _connector="OR",
                ),
                name="reviewstaff_last_review_before_records_is_before_them",
            ),
        ),
        migrations.RunSQL(sql.RECORDED_ON_FIXED, sql.RECORDED_ON_NOT_FIXED),
    ]
