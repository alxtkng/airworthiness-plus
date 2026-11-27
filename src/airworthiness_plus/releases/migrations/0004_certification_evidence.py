import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql

INSTALL = """
CREATE FUNCTION release_check_certification_evidence() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM people_require_certification_evidence(
            CASE WHEN NEW.kind = 'Organisation Certifying Staff' THEN NEW.issued_by_id ELSE NULL END,
            NEW.issued_on, NEW.maintenance_authorisation_id, NEW.scope_confirmed,
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

CREATE TRIGGER release_certification_evidence BEFORE INSERT OR UPDATE ON releases_release
    FOR EACH ROW EXECUTE FUNCTION release_check_certification_evidence();
"""

UNINSTALL = """
DROP TRIGGER release_certification_evidence ON releases_release;
DROP FUNCTION release_check_certification_evidence();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0009_maintenance_authorisation_withdrawal"),
        ("releases", "0003_keep_release_entry"),
    ]

    operations = [
        migrations.AddField(
            model_name="release",
            name="legacy_evidence",
            field=models.CharField(
                blank=True, max_length=160, verbose_name="Signed Legacy Evidence Reference"
            ),
        ),
        migrations.AddField(
            model_name="release",
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
            model_name="release",
            name="scope_confirmed",
            field=models.BooleanField(default=False),
        ),
        migrations.RunSQL(
            *sql.same_organisation(
                "releases_release",
                "maintenance_authorisation_id",
                "people_maintenanceauthorisation",
            )
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
