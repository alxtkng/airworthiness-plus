"""A certificate issued by the organisation's own review staff before these records (REQ-110)."""

from django.db import migrations, models

from airworthiness_plus.reviews import sql


class Migration(migrations.Migration):
    dependencies = [
        ("aircraft", "0002_aircraft_designation_aircraft_manufacturer"),
        ("organisations", "0005_certificate_serial_floor"),
        ("reviews", "0003_allocate_above_floor"),
    ]

    operations = [
        migrations.AddField(
            model_name="certificate",
            name="from_before_records",
            field=models.BooleanField(
                default=False, verbose_name="Recorded From Before These Records"
            ),
        ),
        # It takes no serial and is held to the person's last review before these records.
        migrations.RunSQL(sql.ALLOW_FROM_BEFORE, sql.FROM_BEFORE_NOT_ALLOWED),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("from_before_records", False),
                    models.Q(
                        ("issued_by__isnull", False),
                        ("serial_number__isnull", True),
                        models.Q(("reference", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="certificate_from_before_has_its_reference_and_no_serial",
            ),
        ),
        migrations.AddConstraint(
            model_name="certificate",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("issued_by__isnull", True),
                    ("from_before_records", True),
                    ("serial_number__isnull", False),
                    _connector="OR",
                ),
                name="certificate_issued_in_these_records_has_its_serial",
            ),
        ),
    ]
