"""Check certification evidence against the recorded person and decision date."""

from django.db import migrations

INSTALL = """
CREATE FUNCTION people_require_certification_evidence(
    certifier_id uuid, activity_on date, grant_id uuid,
    confirmed boolean, legacy_reference varchar
) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    IF certifier_id IS NULL THEN
        IF grant_id IS NOT NULL OR confirmed OR btrim(legacy_reference) <> '' THEN
            RAISE EXCEPTION 'Certification evidence applies to organisation certifying staff'
                USING ERRCODE = 'check_violation';
        END IF;
    ELSIF btrim(legacy_reference) <> '' THEN
        IF grant_id IS NOT NULL OR confirmed THEN
            RAISE EXCEPTION 'Choose verified authorisation or signed legacy evidence'
                USING ERRCODE = 'check_violation';
        END IF;
        IF activity_on >= (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date THEN
            RAISE EXCEPTION 'Signed legacy evidence predates today'
                USING ERRCODE = 'check_violation';
        END IF;
    ELSIF NOT confirmed OR NOT EXISTS (
        SELECT 1 FROM people_maintenanceauthorisation grant_record
        LEFT JOIN people_maintenanceauthorisationwithdrawal withdrawal
          ON withdrawal.authorisation_id = grant_record.id
        WHERE grant_record.id = grant_id
          AND grant_record.person_id = certifier_id
          AND grant_record.valid_from <= activity_on
          AND (withdrawal.withdrawn_from IS NULL OR activity_on < withdrawal.withdrawn_from)
          AND (grant_record.valid_to IS NULL OR activity_on <= grant_record.valid_to)
    ) THEN
        RAISE EXCEPTION 'Recorded authorisation must cover the person and activity date'
            USING ERRCODE = 'check_violation';
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    dependencies = [("people", "0007_experience_replacement")]
    operations = [
        migrations.RunSQL(
            INSTALL,
            "DROP FUNCTION people_require_certification_evidence(uuid,date,uuid,boolean,varchar);",
        )
    ]
