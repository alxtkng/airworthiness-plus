"""Keep the amendment check due date recorded on issue."""

from django.db import migrations

RULE = """
CREATE FUNCTION planning_check_evidence_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.issue_check_due IS DISTINCT FROM OLD.issue_check_due AND (
        EXISTS (SELECT 1 FROM planning_workpackage WHERE id = NEW.package_id AND issued_on IS NOT NULL)
        OR NEW.issue_check_due IS DISTINCT FROM (
            SELECT check_due FROM maintenance_data_dataset WHERE id = NEW.data_set_id
        )
    ) THEN
        RAISE EXCEPTION 'The amendment due date on an issued work card is fixed'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER work_card_amendment_evidence BEFORE UPDATE ON planning_workcard
    FOR EACH ROW EXECUTE FUNCTION planning_check_evidence_rules();
"""

REVERSE = """
DROP TRIGGER work_card_amendment_evidence ON planning_workcard;
DROP FUNCTION planning_check_evidence_rules();
"""


class Migration(migrations.Migration):
    dependencies = [("planning", "0003_workcard_issue_check_due")]
    operations = [migrations.RunSQL(RULE, REVERSE)]
