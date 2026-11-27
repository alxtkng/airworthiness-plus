"""Snapshot the approval covering maintenance when a certificate was issued."""

from django.db import migrations

from airworthiness_plus.releases.sql import CREATE_RELEASE_RULES

FUNCTION = CREATE_RELEASE_RULES.split("CREATE TRIGGER", 1)[0]
INSTALL = (
    FUNCTION.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)
    .replace(
        "    IF NEW.kind = 'Organisation Certifying Staff' THEN",
        """    IF EXISTS (
        SELECT 1 FROM programme_workdone
         WHERE id = NEW.work_id AND (
             (by_pilot_owner IS DISTINCT FROM (NEW.kind = 'Pilot-Owner')
                 AND (NEW.kind <> 'Pilot-Owner' OR NEW.licence <> ''))
             OR (release_recorded_on IS NOT NULL AND (
                 release_recorded_on < NEW.issued_on OR release_reference <> NEW.reference
             ))
         )
    ) THEN
        RAISE EXCEPTION 'The certificate must match the recorded work and release entry'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.kind = 'Organisation Certifying Staff' THEN
        IF NEW.issued_by_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM people_person
             WHERE id = NEW.issued_by_id AND staff_group = 'Certifying Staff'
               AND (joined_on IS NULL OR joined_on <= NEW.issued_on)
               AND (left_on IS NULL OR left_on >= NEW.issued_on)
        ) THEN
            RAISE EXCEPTION 'The person named was not certifying staff on the day of issue'
                USING ERRCODE = 'check_violation';
        END IF;""",
    )
    .replace(
        """        SELECT approval_reference INTO NEW.approval_reference
          FROM organisations_organisation WHERE id = NEW.organisation_id;""",
        """        NEW.approval_reference := organisations_approval_for_activity(
            NEW.organisation_id, NEW.issued_on, 'Part-145', 'Maintenance'
        );
        IF NEW.approval_reference IS NULL THEN
            RAISE EXCEPTION 'No approval covers the maintenance on the date of issue'
                USING ERRCODE = 'check_violation';
        END IF;""",
    )
)


class Migration(migrations.Migration):
    dependencies = [
        ("releases", "0001_initial"),
        ("organisations", "0011_approval_for_activity"),
    ]
    operations = [
        migrations.RunSQL(
            INSTALL, FUNCTION.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)
        )
    ]
