"""A record may refer only to records of its own organisation."""

from django.db import migrations

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0002_protect_first_records"),
    ]

    operations = [
        migrations.RunSQL(sql.CREATE_SAME_ORGANISATION, sql.DROP_SAME_ORGANISATION),
    ]
