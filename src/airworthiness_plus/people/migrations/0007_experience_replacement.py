import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql

INSTALL = """
CREATE FUNCTION people_check_experience_replacement() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.supersedes_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
          FROM people_experienceevidence predecessor
          JOIN people_experiencewithdrawal withdrawal ON withdrawal.evidence_id = predecessor.id
         WHERE predecessor.id = NEW.supersedes_id
           AND predecessor.organisation_id = NEW.organisation_id
           AND predecessor.authorisation_id = NEW.authorisation_id
           AND predecessor.evidence_reference = NEW.evidence_reference
    ) THEN
        RAISE EXCEPTION 'A replacement uses the same withdrawn evidence reference and authorisation'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER experience_replacement BEFORE INSERT ON people_experienceevidence
    FOR EACH ROW EXECUTE FUNCTION people_check_experience_replacement();
"""

UNINSTALL = """
DROP TRIGGER experience_replacement ON people_experienceevidence;
DROP FUNCTION people_check_experience_replacement();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0011_approval_for_activity"),
        ("people", "0006_experiencewithdrawal"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="experienceevidence",
            name="experience_evidence_reference_used_once",
        ),
        migrations.AddField(
            model_name="experienceevidence",
            name="supersedes",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="replacement",
                to="people.experienceevidence",
            ),
        ),
        migrations.AddConstraint(
            model_name="experienceevidence",
            constraint=models.UniqueConstraint(
                condition=models.Q(("supersedes__isnull", True)),
                fields=("authorisation", "evidence_reference"),
                name="experience_evidence_reference_starts_one_chain",
            ),
        ),
        migrations.RunSQL(
            *sql.same_organisation(
                "people_experienceevidence", "supersedes_id", "people_experienceevidence"
            )
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
