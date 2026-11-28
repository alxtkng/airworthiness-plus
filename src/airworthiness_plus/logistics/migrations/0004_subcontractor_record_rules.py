"""Scope maintenance subcontractor assessments to their organisation and retain them."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table


class Migration(migrations.Migration):
    dependencies = [("logistics", "0003_subcontractor_assessment")]

    operations = [
        migrations.RunSQL(
            *protect_record_table(
                "logistics_subcontractorassessment",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("supplier_id", "logistics_supplier"),
                    ("approval_id", "organisations_approval"),
                ),
            )
        ),
    ]
