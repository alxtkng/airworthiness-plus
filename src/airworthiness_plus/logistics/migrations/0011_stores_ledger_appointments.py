"""Authorise Stores posting, moves, counts and adjustments by dated appointment (REQ-358)."""

from django.db import migrations, models

FORWARD = """
CREATE FUNCTION logistics_stores_person_authority(person_id uuid, wanted text, signed date)
RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    -- The person acting must be the signed-in user and hold a current appointment for the
    -- duty on the record's date, under a maintenance approval held that day (REQ-358).
    IF NOT EXISTS (
        SELECT 1 FROM logistics_stockappointment grant_record
        JOIN people_person person ON person.id = grant_record.person_id
        WHERE grant_record.person_id = logistics_stores_person_authority.person_id
          AND grant_record.action = wanted
          AND signed BETWEEN grant_record.starts_on AND grant_record.ends_on
          AND organisations_approval_reference_on(grant_record.approval_id, signed) IS NOT NULL
          AND person.user_id = NULLIF(current_setting('airworthiness.user', true), '')::uuid
          AND (person.joined_on IS NULL OR person.joined_on <= signed)
          AND (person.left_on IS NULL OR person.left_on >= signed)
          AND NOT EXISTS (
            SELECT 1 FROM logistics_stockappointmentwithdrawal gone
             WHERE gone.appointment_id = grant_record.id AND gone.withdrawn_on <= signed
          )
    ) THEN
        PERFORM logistics_refuse('The signed-in person needs a current Stores appointment for this action');
    END IF;
END
$$;

CREATE FUNCTION logistics_stores_ledger_authority() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    CASE TG_TABLE_NAME
        WHEN 'logistics_stockresolution' THEN
            PERFORM logistics_stores_person_authority(NEW.recorded_by_id, 'Post', NEW.evidence_on);
        WHEN 'logistics_stockposting' THEN
            PERFORM logistics_stores_person_authority(NEW.actor_id, 'Post', NEW.posted_on);
        WHEN 'logistics_stockcount' THEN
            PERFORM logistics_stores_person_authority(NEW.counter_id, 'Count', NEW.counted_on);
        WHEN 'logistics_stockmovement' THEN
            -- The intake is written by its posting, which was checked for Post.
            IF NEW.kind = 'Transfer' THEN
                PERFORM logistics_stores_person_authority(NEW.actor_id, 'Move', NEW.moved_on);
            ELSIF NEW.kind = 'Adjustment' THEN
                PERFORM logistics_stores_person_authority(NEW.actor_id, 'Adjust', NEW.moved_on);
            END IF;
    END CASE;
    RETURN NEW;
END
$$;

CREATE TRIGGER stores_ledger_authority BEFORE INSERT ON logistics_stockresolution
    FOR EACH ROW EXECUTE FUNCTION logistics_stores_ledger_authority();
CREATE TRIGGER stores_ledger_authority BEFORE INSERT ON logistics_stockposting
    FOR EACH ROW EXECUTE FUNCTION logistics_stores_ledger_authority();
CREATE TRIGGER stores_ledger_authority BEFORE INSERT ON logistics_stockcount
    FOR EACH ROW EXECUTE FUNCTION logistics_stores_ledger_authority();
CREATE TRIGGER stores_ledger_authority BEFORE INSERT ON logistics_stockmovement
    FOR EACH ROW EXECUTE FUNCTION logistics_stores_ledger_authority();
"""

REVERSE = """
DROP TRIGGER stores_ledger_authority ON logistics_stockmovement;
DROP TRIGGER stores_ledger_authority ON logistics_stockcount;
DROP TRIGGER stores_ledger_authority ON logistics_stockposting;
DROP TRIGGER stores_ledger_authority ON logistics_stockresolution;
DROP FUNCTION logistics_stores_ledger_authority();
DROP FUNCTION logistics_stores_person_authority(uuid, text, date);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("logistics", "0010_maintenance_custody"),
        ("organisations", "0012_approval_periods"),
        ("people", "0009_maintenance_authorisation_withdrawal"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="stockappointment",
            name="stock_appointment_has_dated_scope_and_evidence",
        ),
        migrations.AlterField(
            model_name="stockappointment",
            name="action",
            field=models.CharField(
                choices=[
                    ("Reserve", "Reserve Stock for a Work Card"),
                    ("Issue", "Issue Stock to Maintenance"),
                    ("Return", "Accept Maintenance Returns to Quarantine"),
                    ("Quarantine", "Move Unreserved Stock to Quarantine"),
                    ("Post", "Resolve and Post Stock"),
                    ("Move", "Move Stock Between Locations"),
                    ("Count", "Count Stock"),
                    ("Adjust", "Adjust Stock From a Count"),
                ],
                max_length=12,
            ),
        ),
        migrations.AddConstraint(
            model_name="stockappointment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "action__in",
                        [
                            "Reserve",
                            "Issue",
                            "Return",
                            "Quarantine",
                            "Post",
                            "Move",
                            "Count",
                            "Adjust",
                        ],
                    ),
                    ("ends_on__gte", models.F("starts_on")),
                    models.Q(("evidence", ""), _negated=True),
                ),
                name="stock_appointment_has_dated_scope_and_evidence",
            ),
        ),
        migrations.RunSQL(FORWARD, REVERSE),
    ]
