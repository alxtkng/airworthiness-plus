"""Keep suppliers tenant-scoped and their evaluations append-only."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table


class Migration(migrations.Migration):
    dependencies = [("logistics", "0001_initial")]

    operations = [
        migrations.RunSQL(
            *protect_record_table("logistics_supplier", privileges=("SELECT", "INSERT"))
        ),
        migrations.RunSQL(
            *protect_record_table(
                "logistics_supplierevaluation",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("supplier_id", "logistics_supplier"),
                    ("approval_id", "organisations_approval"),
                ),
            )
        ),
    ]
