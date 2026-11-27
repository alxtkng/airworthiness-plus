"""Keep the reference and date used to measure a release entry deadline."""

from django.db import migrations

INSTALL = """
CREATE FUNCTION releases_work_entry_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.release_reference <> ''
       AND ROW(NEW.release_reference, NEW.release_recorded_on)
           IS DISTINCT FROM ROW(OLD.release_reference, OLD.release_recorded_on)
    THEN
        RAISE EXCEPTION 'A release entry is never overwritten'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER release_entry_fixed BEFORE UPDATE OF release_reference, release_recorded_on
    ON programme_workdone FOR EACH ROW EXECUTE FUNCTION releases_work_entry_fixed();
"""

UNINSTALL = """
DROP TRIGGER release_entry_fixed ON programme_workdone;
DROP FUNCTION releases_work_entry_fixed();
"""


class Migration(migrations.Migration):
    dependencies = [("releases", "0002_maintenance_approval")]
    operations = [migrations.RunSQL(INSTALL, UNINSTALL)]
