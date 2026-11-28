"""Scope retained records and enforce the same-tool and delegation relationships."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

TABLES = {
    "tooling_tooldelegation": (
        ("person_id", "people_person"),
        ("approval_id", "organisations_approval"),
    ),
    "tooling_tooldelegationwithdrawal": (("delegation_id", "tooling_tooldelegation"),),
    "tooling_tool": (("delegation_id", "tooling_tooldelegation"),),
    "tooling_toolcontrolrevision": (
        ("tool_id", "tooling_tool"),
        ("delegation_id", "tooling_tooldelegation"),
    ),
    "tooling_toolcontrolevent": (
        ("tool_id", "tooling_tool"),
        ("control_id", "tooling_toolcontrolrevision"),
        ("delegation_id", "tooling_tooldelegation"),
    ),
}

FORWARD = """
CREATE FUNCTION tooling_check_linked_evidence() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    grant_record tooling_tooldelegation%ROWTYPE;
    tool_site text;
    expected_action text;
    expected_control text;
    signed date;
    signer uuid;
    asset tooling_tool%ROWTYPE;
BEGIN
    SELECT * INTO STRICT grant_record FROM tooling_tooldelegation WHERE id = NEW.delegation_id;

    IF TG_TABLE_NAME = 'tooling_tool' THEN
        signed := NEW.registered_on;
        tool_site := NEW.site;
        expected_action := 'Register';
    ELSE
        SELECT * INTO STRICT asset FROM tooling_tool WHERE id = NEW.tool_id;
        tool_site := asset.site;
        IF TG_TABLE_NAME = 'tooling_toolcontrolrevision' THEN
            expected_action := 'Control';
            signed := NEW.effective_on;
            IF asset.lender <> '' AND (
                asset.serial = '' OR (asset.is_assembly AND asset.component_ids = '')
                OR NEW.loan_task = '' OR NEW.loan_evidence = ''
                OR NEW.loan_identity <> concat_ws(' / ', asset.serial, NULLIF(asset.component_ids, ''))
            ) THEN
                RAISE EXCEPTION 'The control basis requires evidence for the actual loan'
                    USING ERRCODE = '23514';
            END IF;
        ELSE
            signed := NEW.signed_on;
            expected_control := CASE NEW.kind
                WHEN 'Calibration completed' THEN 'Calibration'
                WHEN 'Servicing completed' THEN 'Servicing'
                WHEN 'Pre-use inspection' THEN 'Before each use'
                WHEN 'Interim check passed' THEN 'Calibration'
                WHEN 'Interim check failed' THEN 'Calibration'
            END;
            expected_action := CASE
                WHEN expected_control IS NOT NULL THEN 'Evidence'
                WHEN NEW.kind = 'Return to use' THEN 'Reinstate'
                ELSE 'Condition'
            END;
            IF expected_control IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM tooling_toolcontrolrevision basis
                JOIN tooling_tooldelegation grant_basis ON grant_basis.id = basis.delegation_id
                WHERE basis.id = NEW.control_id AND basis.tool_id = NEW.tool_id
                  AND basis.kind = expected_control AND basis.effective_on <= signed
                  AND grant_basis.approval_id = grant_record.approval_id
                  AND grant_basis.approval_reference = grant_record.approval_reference
            ) THEN
                RAISE EXCEPTION 'Control evidence must match its tool, control and approval'
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;

    signer := NULLIF(current_setting('airworthiness.user', true), '')::uuid;
    IF expected_action <> grant_record.action OR lower(tool_site) <> lower(grant_record.site)
       OR signed NOT BETWEEN grant_record.starts_on AND grant_record.ends_on
       OR grant_record.approval_reference IS DISTINCT FROM
            organisations_approval_reference_on(grant_record.approval_id, signed)
       OR EXISTS (SELECT 1 FROM tooling_tooldelegationwithdrawal WHERE delegation_id = grant_record.id)
       OR NOT EXISTS (
            SELECT 1 FROM people_person
            WHERE id = grant_record.person_id AND user_id = signer
              AND (joined_on IS NULL OR joined_on <= signed)
              AND (left_on IS NULL OR left_on > signed)
       ) THEN
        RAISE EXCEPTION 'The signer needs a current delegation for this action, approval and site'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER tooling_tool_a_check_evidence BEFORE INSERT ON tooling_tool
    FOR EACH ROW EXECUTE FUNCTION tooling_check_linked_evidence();
CREATE TRIGGER tooling_revision_a_check_evidence BEFORE INSERT ON tooling_toolcontrolrevision
    FOR EACH ROW EXECUTE FUNCTION tooling_check_linked_evidence();
CREATE TRIGGER tooling_event_a_check_evidence BEFORE INSERT ON tooling_toolcontrolevent
    FOR EACH ROW EXECUTE FUNCTION tooling_check_linked_evidence();
"""

REVERSE = """
DROP TRIGGER tooling_event_a_check_evidence ON tooling_toolcontrolevent;
DROP TRIGGER tooling_revision_a_check_evidence ON tooling_toolcontrolrevision;
DROP TRIGGER tooling_tool_a_check_evidence ON tooling_tool;
DROP FUNCTION tooling_check_linked_evidence();
"""


def retain_signed_record(table: str) -> migrations.RunSQL:
    # TABLES supplies the same fixed names as protect_record_table.
    return migrations.RunSQL(
        f"CREATE TRIGGER history_refuse_update BEFORE UPDATE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION history_refuse();",
        f"DROP TRIGGER history_refuse_update ON {table};",
    )


class Migration(migrations.Migration):
    dependencies = [("tooling", "0001_initial")]

    operations = [
        migrations.RunSQL(
            *protect_record_table(table, privileges=("SELECT", "INSERT"), parents=parents)
        )
        for table, parents in TABLES.items()
    ]
    operations.extend(retain_signed_record(table) for table in TABLES)
    operations.append(migrations.RunSQL(FORWARD, REVERSE))
