"""Protect roster records and preserve acknowledgements."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

RULES = """
CREATE FUNCTION staffing_handover_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
        (to_jsonb(NEW) - ARRAY['acknowledged_at', 'actor_id'])
            IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['acknowledged_at', 'actor_id'])
        OR (OLD.acknowledged_at IS NOT NULL AND NEW IS DISTINCT FROM OLD)
    ) THEN
        RAISE EXCEPTION 'Handover evidence and its acknowledgement are retained'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.actor_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM people_person WHERE id = NEW.incoming_id AND user_id = NEW.actor_id
    ) THEN
        RAISE EXCEPTION 'The incoming person acknowledges the handover'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER handover_rules BEFORE INSERT OR UPDATE ON staffing_handover
    FOR EACH ROW EXECUTE FUNCTION staffing_handover_rules();

CREATE FUNCTION staffing_shift_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW) - ARRAY['withdrawn_on', 'withdrawal_reason'])
            IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['withdrawn_on', 'withdrawal_reason'])
        OR (OLD.withdrawn_on IS NOT NULL AND NEW IS DISTINCT FROM OLD)
    THEN
        RAISE EXCEPTION 'The original shift and its withdrawal are retained'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER roster_shift_rules BEFORE UPDATE ON staffing_shift
    FOR EACH ROW EXECUTE FUNCTION staffing_shift_rules();

CREATE FUNCTION staffing_publication_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.supersedes_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM staffing_publishedroster
         WHERE id = NEW.supersedes_id AND week = NEW.week AND published_on <= NEW.published_on
    ) THEN
        RAISE EXCEPTION 'A replacement follows publication for the same week'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER publication_rules BEFORE INSERT ON staffing_publishedroster
    FOR EACH ROW EXECUTE FUNCTION staffing_publication_rules();
"""

REVERSE = """
DROP TRIGGER publication_rules ON staffing_publishedroster;
DROP FUNCTION staffing_publication_rules();
DROP TRIGGER roster_shift_rules ON staffing_shift;
DROP FUNCTION staffing_shift_rules();
DROP TRIGGER handover_rules ON staffing_handover;
DROP FUNCTION staffing_handover_rules();
"""


class Migration(migrations.Migration):
    dependencies = [("staffing", "0003_handover_publishedroster_settings_shift")]
    operations = [
        migrations.RunSQL(*protect_record_table("staffing_settings")),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_publishedroster",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("published_by_id", "accounts_user"),
                    ("supersedes_id", "staffing_publishedroster"),
                ),
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_shift",
                parents=(("approval_id", "organisations_approval"), ("person_id", "people_person")),
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_handover",
                parents=(
                    ("package_id", "planning_workpackage"),
                    ("incoming_id", "people_person"),
                    ("outgoing_id", "people_person"),
                    ("actor_id", "accounts_user"),
                ),
            )
        ),
        migrations.RunSQL(RULES, REVERSE),
    ]
