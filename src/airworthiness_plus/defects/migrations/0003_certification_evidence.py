import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql

INSTALL = """
CREATE FUNCTION defect_check_certification_evidence() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM people_require_certification_evidence(
            CASE WHEN NEW.basis = 'Certifying Staff' THEN NEW.decided_by_id ELSE NULL END,
            NEW.decided_on, NEW.maintenance_authorisation_id, NEW.scope_confirmed,
            NEW.legacy_evidence
        );
    ELSIF ROW(NEW.maintenance_authorisation_id, NEW.scope_confirmed, NEW.legacy_evidence)
       IS DISTINCT FROM ROW(OLD.maintenance_authorisation_id, OLD.scope_confirmed, OLD.legacy_evidence)
    THEN
        RAISE EXCEPTION 'Recorded certification evidence never changes'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER defect_certification_evidence BEFORE INSERT OR UPDATE ON defects_defect
    FOR EACH ROW EXECUTE FUNCTION defect_check_certification_evidence();
"""

UNINSTALL = """
DROP TRIGGER defect_certification_evidence ON defects_defect;
DROP FUNCTION defect_check_certification_evidence();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("defects", "0002_closure_matches_defect"),
        ("people", "0009_maintenance_authorisation_withdrawal"),
    ]

    operations = [
        migrations.AddField(
            model_name="defect",
            name="legacy_evidence",
            field=models.CharField(
                blank=True, max_length=160, verbose_name="Signed Legacy Evidence Reference"
            ),
        ),
        migrations.AddField(
            model_name="defect",
            name="maintenance_authorisation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="people.maintenanceauthorisation",
            ),
        ),
        migrations.AddField(
            model_name="defect",
            name="scope_confirmed",
            field=models.BooleanField(default=False),
        ),
        migrations.RunSQL(
            *sql.same_organisation(
                "defects_defect", "maintenance_authorisation_id", "people_maintenanceauthorisation"
            )
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
