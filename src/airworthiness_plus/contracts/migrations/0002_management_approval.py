"""Snapshot the approval covering continuing airworthiness management."""

from django.db import migrations

from airworthiness_plus.contracts.sql import CREATE_CONTRACT_RULES

FUNCTION = CREATE_CONTRACT_RULES.split("CREATE TRIGGER", 1)[0].replace(
    "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1
)
INSTALL = FUNCTION.replace(
    """        SELECT name, address, approval_reference
          INTO NEW.organisation_name, NEW.organisation_address,
               NEW.organisation_approval_reference
          FROM organisations_organisation WHERE id = NEW.organisation_id;""",
    """        SELECT name, address INTO NEW.organisation_name, NEW.organisation_address
          FROM organisations_organisation WHERE id = NEW.organisation_id;
        NEW.organisation_approval_reference := organisations_approval_for_activity(
            NEW.organisation_id, NEW.signed_on, 'Part-CAMO', 'Continuing Airworthiness Management'
        );
        IF NEW.organisation_approval_reference IS NULL THEN
            RAISE EXCEPTION 'No approval covers continuing airworthiness management on this date'
                USING ERRCODE = 'check_violation';
        END IF;""",
)

WORK_ORDER = (
    "CREATE FUNCTION contracts_workorder_rules"
    + CREATE_CONTRACT_RULES.split("CREATE FUNCTION contracts_workorder_rules", 1)[1].split(
        "CREATE TRIGGER workorder_rules", 1
    )[0]
).replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)
CHECK_WORK_ORDER = WORK_ORDER.replace(
    "BEGIN",
    """BEGIN
    IF NEW.contract_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM contracts_contract
         WHERE id = NEW.contract_id AND aircraft_id = NEW.aircraft_id
    ) THEN
        RAISE EXCEPTION 'The work order and contract must belong to the same aircraft'
            USING ERRCODE = 'check_violation';
    END IF;""",
    1,
)


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0001_initial"),
        ("organisations", "0011_approval_for_activity"),
    ]
    operations = [
        migrations.RunSQL(INSTALL, FUNCTION),
        migrations.RunSQL(CHECK_WORK_ORDER, WORK_ORDER),
    ]
