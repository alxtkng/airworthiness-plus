import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql

INSTALL = """
CREATE FUNCTION programme_work_performer() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.performed_by_id IS NOT NULL THEN
            SELECT full_name INTO NEW.performed_by_name
              FROM people_person
             WHERE id = NEW.performed_by_id
               AND (joined_on IS NULL OR joined_on <= NEW.dated)
               AND (left_on IS NULL OR left_on >= NEW.dated)
               FOR SHARE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'The performer must have belonged to the organisation on the work date'
                    USING ERRCODE = 'check_violation';
            END IF;
        ELSE
            NEW.performed_by_name := '';
        END IF;
    ELSIF ROW(NEW.performed_by_id, NEW.performed_by_name)
       IS DISTINCT FROM ROW(OLD.performed_by_id, OLD.performed_by_name) THEN
        RAISE EXCEPTION 'The recorded performer of work is never overwritten'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER work_performer BEFORE INSERT OR UPDATE ON programme_workdone
    FOR EACH ROW EXECUTE FUNCTION programme_work_performer();
"""

UNINSTALL = """
DROP TRIGGER work_performer ON programme_workdone;
DROP FUNCTION programme_work_performer();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0003_maintenance_authorisation"),
        ("programme", "0003_departures_and_annual_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="workdone",
            name="performed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="people.person",
                verbose_name="Performed By",
            ),
        ),
        migrations.AddField(
            model_name="workdone",
            name="performed_by_name",
            field=models.CharField(
                blank=True, max_length=200, verbose_name="Performed By, Name at Entry"
            ),
        ),
        migrations.RunSQL(
            *sql.same_organisation("programme_workdone", "performed_by_id", "people_person")
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
