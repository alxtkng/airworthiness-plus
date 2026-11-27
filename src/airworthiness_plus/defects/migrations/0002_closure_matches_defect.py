"""Prevent a new closure from predating the decision or naming another aircraft's work."""

from django.db import migrations

from airworthiness_plus.defects.sql import CREATE_DEFECT_RULES

FUNCTION = CREATE_DEFECT_RULES.split("CREATE TRIGGER", 1)[0].replace(
    "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1
)
INSTALL = FUNCTION.replace(
    "BEGIN",
    """BEGIN
    IF NEW.closed_on >= NEW.found_on AND NEW.closed_on < NEW.decided_on THEN
        RAISE EXCEPTION 'A defect is not closed before the decision was made'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.work_done_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM programme_workdone
         WHERE id = NEW.work_done_id AND aircraft_id = NEW.aircraft_id
    ) THEN
        RAISE EXCEPTION 'The work done belongs to another aircraft'
            USING ERRCODE = 'check_violation';
    END IF;""",
    1,
)


class Migration(migrations.Migration):
    dependencies = [("defects", "0001_initial")]
    operations = [migrations.RunSQL(INSTALL, FUNCTION)]
