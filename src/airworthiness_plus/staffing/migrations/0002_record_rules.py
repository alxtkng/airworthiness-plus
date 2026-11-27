"""Apply tenant scoping and hashed history to the staffing records."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table


class Migration(migrations.Migration):
    dependencies = [("staffing", "0001_initial")]
    operations = [
        migrations.RunSQL(
            *protect_record_table(
                "staffing_demand", parents=(("approval_id", "organisations_approval"),)
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_review",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("approval_id", "organisations_approval"),
                    ("reviewed_by_id", "accounts_user"),
                ),
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_report",
                privileges=("SELECT", "INSERT"),
                parents=(("demand_id", "staffing_demand"), ("reported_by_id", "accounts_user")),
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_absence",
                privileges=("SELECT", "INSERT"),
                parents=(("person_id", "people_person"),),
            )
        ),
    ]
