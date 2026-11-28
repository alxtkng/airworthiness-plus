"""Protect retained tooling decisions and their parent relationships."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

CARD = ("card_id", "planning_workcard")
WORK = ("work_id", "programme_workdone")
APPROVAL = ("approval_id", "organisations_approval")
TOOL = ("tool_id", "tooling_tool")
GRANT = ("delegation_id", "tooling_tooldelegation")
ISSUE = ("issue_id", "tooling_toolissue")
REVISION = ("revision_id", "maintenance_data_revision")
ASSIGNMENT = ("work_approval_id", "tooling_workpackageapproval")
TABLES = {
    "tooling_workpackageapproval": (("package_id", "planning_workpackage"), APPROVAL),
    "tooling_toolissue": (TOOL, GRANT, ASSIGNMENT, ("custodian_id", "people_person")),
    "tooling_toolpreuseinspection": (
        ISSUE,
        GRANT,
        CARD,
        REVISION,
        ("control_id", "tooling_toolcontrolrevision"),
    ),
    "tooling_tooluse": (
        ISSUE,
        GRANT,
        CARD,
        REVISION,
        ("inspection_id", "tooling_toolpreuseinspection"),
    ),
    "tooling_toolreturn": (ISSUE, GRANT, ("returned_by_id", "people_person")),
    "tooling_historicaltoolclaim": (TOOL, CARD, WORK),
    "tooling_releasegeneralverification": (
        ("release_id", "releases_release"),
        APPROVAL,
        ASSIGNMENT,
    ),
}

FORWARD = """
CREATE FUNCTION tooling_check_custody_links() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE
    assignment tooling_workpackageapproval%ROWTYPE;
    issue tooling_toolissue%ROWTYPE;
    grant_record tooling_tooldelegation%ROWTYPE;
    stamp timestamptz;
BEGIN
    IF TG_TABLE_NAME = 'tooling_workpackageapproval' THEN
        IF NEW.reference IS DISTINCT FROM
            organisations_approval_reference_on(NEW.approval_id, NEW.assigned_on)
          OR NOT EXISTS (
            SELECT 1 FROM organisations_approval
            WHERE id=NEW.approval_id AND approval IN ('Part-CAO', 'Part-145')
          ) OR NOT EXISTS (
            SELECT 1 FROM planning_workpackage WHERE id=NEW.package_id
              AND issued_on <= NEW.assigned_on AND released_on IS NULL
          ) THEN
            RAISE EXCEPTION 'Assignment needs an issued package and its dated maintenance approval'
                USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END IF;
    IF TG_TABLE_NAME = 'tooling_historicaltoolclaim' THEN
        IF NEW.card_id IS NOT NULL AND NEW.work_id IS NOT NULL AND NOT EXISTS (
            SELECT 1 FROM planning_workcard WHERE id=NEW.card_id AND work_id=NEW.work_id
        ) THEN
            RAISE EXCEPTION 'The claim work must match its work card' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END IF;

    IF TG_TABLE_NAME = 'tooling_toolissue' THEN
        issue.tool_id := NEW.tool_id;
        issue.work_approval_id := NEW.work_approval_id;
    ELSE
        SELECT * INTO STRICT issue FROM tooling_toolissue WHERE id=NEW.issue_id;
    END IF;
    -- Serialize all physical issue, return and approval transitions.
    PERFORM id FROM organisations_organisation WHERE id=NEW.organisation_id FOR NO KEY UPDATE;
    SELECT * INTO STRICT assignment FROM tooling_workpackageapproval WHERE id=issue.work_approval_id;
    SELECT * INTO STRICT grant_record FROM tooling_tooldelegation WHERE id=NEW.delegation_id;
    IF grant_record.action <> TG_ARGV[0]
      OR NEW.occurred_on NOT BETWEEN grant_record.starts_on AND grant_record.ends_on
      OR grant_record.approval_reference IS DISTINCT FROM
        organisations_approval_reference_on(grant_record.approval_id, NEW.occurred_on)
      OR EXISTS (SELECT 1 FROM tooling_tooldelegationwithdrawal WHERE delegation_id=NEW.delegation_id)
      OR NOT EXISTS (
        SELECT 1 FROM people_person WHERE id=grant_record.person_id
          AND user_id=NULLIF(current_setting('airworthiness.user', true), '')::uuid
          AND (joined_on IS NULL OR joined_on <= NEW.occurred_on)
          AND (left_on IS NULL OR left_on > NEW.occurred_on)
      ) OR NOT EXISTS (
        SELECT 1 FROM tooling_tool WHERE id=issue.tool_id AND lower(site)=lower(grant_record.site)
      ) THEN
        RAISE EXCEPTION 'Current tooling delegation required for this signer, site and action'
            USING ERRCODE='23514';
    END IF;

    IF TG_TABLE_NAME = 'tooling_toolreturn' THEN
        IF NEW.occurred_on < issue.occurred_on THEN
            RAISE EXCEPTION 'Return must follow issue' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END IF;
    IF grant_record.approval_id <> assignment.approval_id
      OR grant_record.approval_reference <> assignment.reference
      OR NEW.occurred_on < assignment.assigned_on OR NOT EXISTS (
        SELECT 1 FROM planning_workpackage package
        JOIN contracts_workorder work_order ON work_order.id=package.order_id
        WHERE package.id=assignment.package_id
          AND package.released_on IS NULL AND work_order.outcome <> 'Withdrawn'
      ) THEN
        RAISE EXCEPTION 'An open package and its governing approval are required' USING ERRCODE='23514';
    END IF;

    IF TG_TABLE_NAME = 'tooling_toolissue' THEN
        IF EXISTS (
            SELECT 1 FROM tooling_toolissue previous
            WHERE previous.tool_id=NEW.tool_id AND NOT EXISTS (
                SELECT 1 FROM tooling_toolreturn WHERE issue_id=previous.id
            )
        ) THEN
            RAISE EXCEPTION 'The tool already has an open issue' USING ERRCODE='23505';
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.occurred_on < issue.occurred_on
      OR EXISTS (SELECT 1 FROM tooling_toolreturn WHERE issue_id=issue.id)
      OR NOT EXISTS (
        SELECT 1 FROM planning_workcard card
        JOIN maintenance_data_revision revision ON revision.data_set_id=card.data_set_id
        WHERE card.id=NEW.card_id AND card.package_id=assignment.package_id
          AND card.completed_on IS NULL AND revision.id=NEW.revision_id AND revision.current
      ) THEN
        RAISE EXCEPTION 'Use evidence needs the open issue, card and current revision'
            USING ERRCODE='23514';
    END IF;
    IF TG_TABLE_NAME = 'tooling_toolpreuseinspection' THEN
        IF NOT EXISTS (
            SELECT 1 FROM tooling_toolcontrolrevision control
            JOIN tooling_tooldelegation basis ON basis.id=control.delegation_id
            WHERE control.id=NEW.control_id AND control.tool_id=issue.tool_id
              AND control.kind='Before each use' AND control.effective_on <= NEW.occurred_on
              AND (basis.approval_id, basis.approval_reference) =
                  (assignment.approval_id, assignment.reference)
        ) THEN
            RAISE EXCEPTION 'Inspection needs the applicable control' USING ERRCODE='23514';
        END IF;
    ELSIF NEW.inspection_id IS NOT NULL THEN
        SELECT inspection.entered_at INTO stamp
        FROM tooling_toolpreuseinspection inspection
        JOIN tooling_tooldelegation inspector ON inspector.id=inspection.delegation_id
        WHERE inspection.id=NEW.inspection_id
          AND (inspection.issue_id, inspection.card_id, inspection.revision_id) =
              (NEW.issue_id, NEW.card_id, NEW.revision_id)
          AND inspection.occurred_on=NEW.occurred_on AND inspection.passed
          AND inspector.person_id=grant_record.person_id;
        IF stamp IS NULL OR stamp >= NEW.entered_at THEN
            RAISE EXCEPTION 'Use needs its own satisfactory prior inspection' USING ERRCODE='23514';
        END IF;
    ELSIF EXISTS (
        SELECT 1 FROM tooling_toolcontrolrevision control
        JOIN tooling_tooldelegation basis ON basis.id=control.delegation_id
        WHERE control.tool_id=issue.tool_id AND control.kind='Before each use'
          AND control.effective_on <= NEW.occurred_on
          AND (basis.approval_id, basis.approval_reference) =
              (assignment.approval_id, assignment.reference)
    ) THEN
        RAISE EXCEPTION 'Use needs a separate inspection under the applicable control' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION tooling_check_release_verification() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE
    certificate releases_release%ROWTYPE;
    work programme_workdone%ROWTYPE;
BEGIN
    SELECT * INTO STRICT certificate FROM releases_release WHERE id=NEW.release_id;
    SELECT * INTO STRICT work FROM programme_workdone WHERE id=certificate.work_id;
    IF certificate.maintenance_authorisation_id IS NULL
      OR certificate.governing_approval_id IS DISTINCT FROM NEW.approval_id
      OR certificate.approval_reference IS DISTINCT FROM NEW.approval_reference
      OR NEW.performed_on NOT BETWEEN work.dated AND certificate.issued_on
      OR NEW.approval_reference IS DISTINCT FROM
        organisations_approval_reference_on(NEW.approval_id, certificate.issued_on)
      OR NOT EXISTS (
        SELECT 1 FROM organisations_approval WHERE id=NEW.approval_id AND
          (approval, NEW.rule) IN (('Part-CAO','CAO.A.060(i)'), ('Part-145','145.A.48(c)(1)'))
      ) OR (NEW.work_approval_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM tooling_workpackageapproval assignment
        JOIN planning_workcard card ON card.package_id=assignment.package_id
        WHERE assignment.id=NEW.work_approval_id AND card.work_id=certificate.work_id
          AND (assignment.approval_id, assignment.reference) = (NEW.approval_id, NEW.approval_reference)
      )) OR EXISTS (
        SELECT 1 FROM tooling_toolissue issue
        JOIN tooling_workpackageapproval assignment ON assignment.id=issue.work_approval_id
        JOIN planning_workpackage package ON package.id=assignment.package_id
        WHERE package.aircraft_id=work.aircraft_id AND issue.occurred_on <= certificate.issued_on
          AND NOT EXISTS (SELECT 1 FROM tooling_toolreturn
            WHERE issue_id=issue.id AND occurred_on <= NEW.performed_on)
      ) THEN
        RAISE EXCEPTION 'Release needs signed verification with reconciled custody' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION tooling_require_general_verification() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE
    previous_organisation text;
    verified boolean;
BEGIN
    IF NEW.maintenance_authorisation_id IS NULL THEN
        RETURN NULL;
    END IF;
    -- Deferred checks can run after the request has restored its RLS setting.
    previous_organisation := current_setting('airworthiness.organisation', true);
    PERFORM set_config('airworthiness.organisation', NEW.organisation_id::text, true);
    SELECT EXISTS (
        SELECT 1 FROM tooling_releasegeneralverification
        WHERE release_id=NEW.id AND organisation_id=NEW.organisation_id
    ) INTO verified;
    PERFORM set_config('airworthiness.organisation', coalesce(previous_organisation, ''), true);
    IF NOT verified THEN
        RAISE EXCEPTION 'Organisation release needs signed general verification' USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END $$;

CREATE CONSTRAINT TRIGGER tooling_release_needs_verification
AFTER INSERT ON releases_release DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW WHEN (NEW.maintenance_authorisation_id IS NOT NULL)
EXECUTE FUNCTION tooling_require_general_verification();
CREATE TRIGGER tooling_validate_release_verification BEFORE INSERT ON tooling_releasegeneralverification
FOR EACH ROW EXECUTE FUNCTION tooling_check_release_verification();
"""

TRIGGERS = {
    "tooling_workpackageapproval": "",
    "tooling_toolissue": "Issue",
    "tooling_toolpreuseinspection": "Use",
    "tooling_tooluse": "Use",
    "tooling_toolreturn": "Return",
    "tooling_historicaltoolclaim": "",
}

REVERSE = """
DROP TRIGGER tooling_release_needs_verification ON releases_release;
DROP TRIGGER tooling_validate_release_verification ON tooling_releasegeneralverification;
DROP FUNCTION tooling_require_general_verification();
DROP FUNCTION tooling_check_release_verification();
DROP FUNCTION tooling_check_custody_links();
"""


class Migration(migrations.Migration):
    dependencies = [("tooling", "0005_custody_and_release_evidence")]

    operations = (
        [
            migrations.RunSQL(
                *protect_record_table(table, privileges=("SELECT", "INSERT"), parents=parents)
            )
            for table, parents in TABLES.items()
        ]
        + [
            migrations.RunSQL(
                f"CREATE TRIGGER history_refuse_update BEFORE UPDATE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION history_refuse();",
                f"DROP TRIGGER history_refuse_update ON {table};",
            )
            for table in TABLES
        ]
        + [
            migrations.RunSQL(FORWARD, REVERSE),
            *[
                migrations.RunSQL(
                    f"CREATE TRIGGER tooling_custody_links BEFORE INSERT ON {table} "
                    f"FOR EACH ROW EXECUTE FUNCTION tooling_check_custody_links('{action}');",
                    f"DROP TRIGGER tooling_custody_links ON {table};",
                )
                for table, action in TRIGGERS.items()
            ],
        ]
    )
