"""A certificate and an extension keep what they showed when they were recorded (REQ-110).

Independent review of 24 November 2026, finding 1. Until now the certificate
page read the organisation's name, address and approval reference and the
signatory's name as they stood when the page was opened, so a later change
to the organisation or the person changed an issued certificate.

The values are now columns of the certificate and of the extension, set
when each is recorded and never altered. Certificates and extensions that
exist are given the values as they stand on the day this migration runs:
the records hold nothing earlier. The history of each then has an entry by
the database role, naming the columns that were set (REQ-130).
"""

from django.db import migrations, models

from airworthiness_plus.history.sql import for_each_organisation
from airworthiness_plus.reviews import sql


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0006_review_item_reads_review_under_lock"),
        ("history", "0004_hash_algorithm"),
        ("organisations", "0007_settings"),
        ("accounts", "0007_first_password_and_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="certificate",
            name="organisation_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="Organisation Name"),
        ),
        migrations.AddField(
            model_name="certificate",
            name="organisation_address",
            field=models.CharField(blank=True, max_length=300, verbose_name="Address"),
        ),
        migrations.AddField(
            model_name="certificate",
            name="organisation_approval_reference",
            field=models.CharField(blank=True, max_length=40, verbose_name="Approval Reference"),
        ),
        migrations.AddField(
            model_name="certificate",
            name="review_staff_name",
            field=models.CharField(
                blank=True, max_length=200, verbose_name="Airworthiness Review Staff"
            ),
        ),
        migrations.AddField(
            model_name="extension",
            name="extended_by_name",
            field=models.CharField(default="", max_length=200, verbose_name="Extended By"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="extension",
            name="organisation_name",
            field=models.CharField(default="", max_length=200, verbose_name="Company Name"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="extension",
            name="organisation_approval_reference",
            field=models.CharField(default="", max_length=40, verbose_name="Approval Reference"),
            preserve_default=False,
        ),
        migrations.RunSQL(for_each_organisation(sql.KEEP_WHAT_EACH_SHOWED), migrations.RunSQL.noop),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("issued_by__isnull", True),
                    models.Q(
                        models.Q(("organisation_name", ""), _negated=True),
                        models.Q(("organisation_approval_reference", ""), _negated=True),
                        models.Q(("review_staff_name", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="certificate_issued_here_keeps_what_it_showed",
            ),
        ),
        migrations.AddConstraint(
            model_name="extension",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("extended_by_name", ""), _negated=True),
                    models.Q(("organisation_name", ""), _negated=True),
                    models.Q(("organisation_approval_reference", ""), _negated=True),
                ),
                name="extension_keeps_what_it_showed",
            ),
        ),
        migrations.RunSQL(sql.WHAT_IT_SHOWED_FIXED, sql.WHAT_IT_SHOWED_NOT_FIXED),
    ]
