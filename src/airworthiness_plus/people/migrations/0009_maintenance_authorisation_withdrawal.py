import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql

INSTALL = """
CREATE FUNCTION people_check_maintenance_authorisation_replacement() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.supersedes_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM people_maintenanceauthorisation predecessor
          JOIN people_maintenanceauthorisationwithdrawal withdrawal
            ON withdrawal.authorisation_id = predecessor.id
         WHERE predecessor.id = NEW.supersedes_id
           AND predecessor.person_id = NEW.person_id
           AND predecessor.reference = NEW.reference
           AND predecessor.valid_from = NEW.valid_from
    ) THEN
        RAISE EXCEPTION 'A replacement keeps the withdrawn authorisation identity'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER maintenance_authorisation_replacement BEFORE INSERT ON people_maintenanceauthorisation
    FOR EACH ROW EXECUTE FUNCTION people_check_maintenance_authorisation_replacement();
"""

UNINSTALL = """
DROP TRIGGER maintenance_authorisation_replacement ON people_maintenanceauthorisation;
DROP FUNCTION people_check_maintenance_authorisation_replacement();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0011_approval_for_activity"),
        ("people", "0008_certification_evidence_rules"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceAuthorisationWithdrawal",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("withdrawn_from", models.DateField(verbose_name="Withdrawn From")),
                ("reason", models.CharField(max_length=400, verbose_name="Reason")),
            ],
        ),
        migrations.RemoveConstraint(
            model_name="maintenanceauthorisation",
            name="maintenance_authorisation_recorded_once",
        ),
        migrations.AddField(
            model_name="maintenanceauthorisation",
            name="supersedes",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="replacement",
                to="people.maintenanceauthorisation",
            ),
        ),
        migrations.AddConstraint(
            model_name="maintenanceauthorisation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("supersedes__isnull", True)),
                fields=("person", "reference", "valid_from"),
                name="maintenance_authorisation_starts_one_chain",
            ),
        ),
        migrations.AddField(
            model_name="maintenanceauthorisationwithdrawal",
            name="authorisation",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="withdrawal",
                to="people.maintenanceauthorisation",
            ),
        ),
        migrations.AddField(
            model_name="maintenanceauthorisationwithdrawal",
            name="organisation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="organisations.organisation",
            ),
        ),
        migrations.AddConstraint(
            model_name="maintenanceauthorisationwithdrawal",
            constraint=models.CheckConstraint(
                condition=models.Q(("reason", ""), _negated=True),
                name="maintenance_withdrawal_has_reason",
            ),
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "people_maintenanceauthorisationwithdrawal",
                privileges=("SELECT", "INSERT"),
                parents=(("authorisation_id", "people_maintenanceauthorisation"),),
            )
        ),
        migrations.RunSQL(
            *sql.same_organisation(
                "people_maintenanceauthorisation",
                "supersedes_id",
                "people_maintenanceauthorisation",
            )
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
