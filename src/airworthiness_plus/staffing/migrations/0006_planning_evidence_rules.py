"""Apply the record rules to additional planning settings and publication entries."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

RULES = """
CREATE FUNCTION staffing_published_shift_week() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM staffing_publishedroster publication
        JOIN staffing_shift shift ON shift.id = NEW.shift_id
        WHERE publication.id = NEW.publication_id
          AND (shift.starts_at AT TIME ZONE 'Europe/London')::date
                BETWEEN publication.week AND publication.week + 6
    ) THEN
        RAISE EXCEPTION 'The shift belongs to the published week'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER published_shift_week BEFORE INSERT ON staffing_publishedshift
    FOR EACH ROW EXECUTE FUNCTION staffing_published_shift_week();
"""

REVERSE = """
DROP TRIGGER published_shift_week ON staffing_publishedshift;
DROP FUNCTION staffing_published_shift_week();
"""


class Migration(migrations.Migration):
    dependencies = [("staffing", "0005_handover_overlap_handover_overlap_target_and_more")]
    operations = [
        migrations.RunSQL(*protect_record_table("staffing_bankholiday")),
        migrations.RunSQL(*protect_record_table("staffing_shiftpattern")),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_staffingminimum",
                parents=(("approval_id", "organisations_approval"),),
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "staffing_publishedshift",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("publication_id", "staffing_publishedroster"),
                    ("shift_id", "staffing_shift"),
                ),
            )
        ),
        migrations.RunSQL(RULES, REVERSE),
    ]
