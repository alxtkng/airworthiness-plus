"""The next certificate serial follows the highest serial stated for the organisation (REQ-154)."""

from django.db import migrations

from airworthiness_plus.reviews import sql


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0002_review_checklist"),
        ("organisations", "0005_certificate_serial_floor"),
    ]

    operations = [migrations.RunSQL(sql.ALLOCATE_ABOVE_FLOOR, sql.ALLOCATE_AS_BEFORE)]
