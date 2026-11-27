"""Keep package evidence within its organisation, aircraft and stage."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

RULES = """
CREATE FUNCTION planning_package_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.order_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM contracts_workorder WHERE id = NEW.order_id
         AND aircraft_id = NEW.aircraft_id
    ) OR NEW.defect_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM defects_defect WHERE id = NEW.defect_id AND aircraft_id = NEW.aircraft_id
    ) THEN
        RAISE EXCEPTION 'The order and defect must belong to the package aircraft'
            USING ERRCODE = 'check_violation';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF NEW.issued_on IS NOT NULL THEN
            RAISE EXCEPTION 'A work package starts as a draft'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.reference IS DISTINCT FROM OLD.reference
       OR (OLD.issued_on IS NOT NULL AND (
           (to_jsonb(NEW) - ARRAY['release_id', 'released_on', 'verification'])
           IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['release_id', 'released_on', 'verification'])
       ))
       OR (OLD.released_on IS NOT NULL AND NEW IS DISTINCT FROM OLD) THEN
        RAISE EXCEPTION 'Issued work package evidence is retained'
            USING ERRCODE = 'check_violation';
    END IF;
    IF OLD.issued_on IS NULL AND NEW.issued_on IS NOT NULL AND (
        NOT EXISTS (SELECT 1 FROM contracts_workorder
            WHERE id = NEW.order_id AND closed_on IS NULL AND agreed_on <= NEW.issued_on)
        OR NOT EXISTS (SELECT 1 FROM planning_workcard WHERE package_id = NEW.id)
        OR EXISTS (
            SELECT 1 FROM planning_workcard card
            JOIN maintenance_data_dataset data ON data.id = card.data_set_id
            LEFT JOIN maintenance_data_revision revision ON revision.id = card.revision_id
            JOIN aircraft_aircraft aircraft ON aircraft.id = NEW.aircraft_id
            WHERE card.package_id = NEW.id AND (
                revision.id IS NULL OR NOT revision.current OR data.holding <> 'Held'
                OR data.check_due IS NULL OR data.check_due < NEW.issued_on
                OR revision.revision_date > NEW.issued_on OR data.evidence_dated > NEW.issued_on
                OR (cardinality(data.applies_to) > 0
                    AND NOT (aircraft.type_rating = ANY(data.applies_to)))
            )
        )
    ) THEN
        RAISE EXCEPTION 'Issue needs an agreed order and current held data for every work card'
            USING ERRCODE = 'check_violation';
    END IF;
    IF OLD.released_on IS NULL AND NEW.released_on IS NOT NULL AND (
        NOT EXISTS (
            SELECT 1 FROM releases_release release
            JOIN planning_workcard card ON card.work_id = release.work_id
            WHERE release.id = NEW.release_id AND card.package_id = NEW.id
              AND release.issued_on = NEW.released_on
        ) OR EXISTS (
            SELECT 1 FROM planning_workcard card
            LEFT JOIN programme_workdone work ON work.id = card.work_id
            JOIN releases_release release ON release.id = NEW.release_id
            JOIN programme_workdone primary_work ON primary_work.id = release.work_id
            WHERE card.package_id = NEW.id AND (
                work.id IS NULL OR work.release_reference <> release.reference
                OR work.release_recorded_on IS DISTINCT FROM primary_work.release_recorded_on
                OR card.completed_on > NEW.released_on OR card.inspected_on > NEW.released_on
            )
        )
    ) THEN
        RAISE EXCEPTION 'Every card needs evidence and a release before package closure'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION planning_card_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    package planning_workpackage%ROWTYPE;
BEGIN
    SELECT * INTO package FROM planning_workpackage WHERE id = NEW.package_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'A work card needs a package in its own organisation'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.performed_revision_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM maintenance_data_revision
        WHERE id = NEW.performed_revision_id AND data_set_id = NEW.data_set_id
    ) OR NEW.revision_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM maintenance_data_revision
        WHERE id = NEW.revision_id AND data_set_id = NEW.data_set_id
    ) OR NEW.task_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM programme_task task JOIN programme_programme p ON task.programme_id = p.id
        WHERE task.id = NEW.task_id AND p.aircraft_id = package.aircraft_id
          AND task.kind <> 'Airworthiness Directive'
    ) OR NEW.directive_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM directives_applicability
        WHERE id = NEW.directive_id AND aircraft_id = package.aircraft_id
    ) THEN
        RAISE EXCEPTION 'A work card uses its own data and aircraft tasks'
            USING ERRCODE = 'check_violation';
    END IF;
    IF TG_OP = 'INSERT' THEN
        IF package.issued_on IS NOT NULL OR NEW.revision_id IS NOT NULL THEN
            RAISE EXCEPTION 'A work card is added to a draft package'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.package_id IS DISTINCT FROM OLD.package_id
       OR (package.issued_on IS NULL AND NEW.completed_on IS NOT NULL)
       OR NEW.completed_on < package.issued_on
       OR (package.released_on IS NOT NULL AND NEW IS DISTINCT FROM OLD)
       OR (OLD.work_id IS NOT NULL AND NEW.work_id IS DISTINCT FROM OLD.work_id)
       OR (package.issued_on IS NOT NULL AND (
           ROW(NEW.title, NEW.data_set_id, NEW.revision_id, NEW.instruction,
               NEW.planned_hours, NEW.inspection_hours, NEW.critical, NEW.task_id, NEW.directive_id)
           IS DISTINCT FROM
           ROW(OLD.title, OLD.data_set_id, OLD.revision_id, OLD.instruction,
               OLD.planned_hours, OLD.inspection_hours, OLD.critical, OLD.task_id, OLD.directive_id)
       ))
       OR (OLD.completed_on IS NOT NULL AND (
           ROW(NEW.performed_by_id, NEW.supervised_by_id, NEW.completed_on, NEW.performed_revision_id,
               NEW.sign_off_reference, NEW.hours, NEW.cycles)
           IS DISTINCT FROM
           ROW(OLD.performed_by_id, OLD.supervised_by_id, OLD.completed_on, OLD.performed_revision_id,
               OLD.sign_off_reference, OLD.hours, OLD.cycles)
       ))
       OR (OLD.inspected_on IS NOT NULL AND (
           ROW(NEW.inspector_id, NEW.inspected_on, NEW.qualification, NEW.inspection_evidence)
           IS DISTINCT FROM
           ROW(OLD.inspector_id, OLD.inspected_on, OLD.qualification, OLD.inspection_evidence)
       )) THEN
        RAISE EXCEPTION 'Issued work card evidence is retained'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.work_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM programme_workdone work
        WHERE work.id = NEW.work_id AND work.aircraft_id = package.aircraft_id
        AND work.dated = NEW.completed_on AND work.performed_by_id = NEW.performed_by_id
        AND work.hours = NEW.hours AND work.cycles = NEW.cycles
        AND (NEW.directive_id IS NOT NULL OR work.task_id IS NOT DISTINCT FROM NEW.task_id)
        AND (NEW.directive_id IS NULL OR EXISTS (
            SELECT 1 FROM directives_compliance
            WHERE work_id = NEW.work_id AND applicability_id = NEW.directive_id
        ))
    ) THEN
        RAISE EXCEPTION 'Aircraft work records must agree with signed card evidence'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION planning_release_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    package_title text;
BEGIN
    SELECT package.reference || ', ' || package.title INTO package_title
        FROM planning_workcard card
        JOIN planning_workpackage package ON package.id = card.package_id
        WHERE card.work_id = NEW.work_id;
    IF FOUND THEN
        NEW.maintenance := left(package_title, 200);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER release_work_package_snapshot BEFORE INSERT ON releases_release
    FOR EACH ROW EXECUTE FUNCTION planning_release_snapshot();

CREATE TRIGGER work_package_evidence BEFORE INSERT OR UPDATE ON planning_workpackage
    FOR EACH ROW EXECUTE FUNCTION planning_package_rules();
CREATE TRIGGER work_card_evidence BEFORE INSERT OR UPDATE ON planning_workcard
    FOR EACH ROW EXECUTE FUNCTION planning_card_rules();
"""

REVERSE = """
DROP TRIGGER release_work_package_snapshot ON releases_release;
DROP FUNCTION planning_release_snapshot();
DROP TRIGGER work_card_evidence ON planning_workcard;
DROP TRIGGER work_package_evidence ON planning_workpackage;
DROP FUNCTION planning_card_rules();
DROP FUNCTION planning_package_rules();
"""


class Migration(migrations.Migration):
    dependencies = [("planning", "0001_initial")]
    operations = [
        migrations.RunSQL(
            *protect_record_table(
                "planning_workpackage",
                parents=(
                    ("aircraft_id", "aircraft_aircraft"),
                    ("order_id", "contracts_workorder"),
                    ("defect_id", "defects_defect"),
                    ("release_id", "releases_release"),
                ),
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "planning_workcard",
                parents=(
                    ("package_id", "planning_workpackage"),
                    ("data_set_id", "maintenance_data_dataset"),
                    ("revision_id", "maintenance_data_revision"),
                    ("performed_revision_id", "maintenance_data_revision"),
                    ("task_id", "programme_task"),
                    ("directive_id", "directives_applicability"),
                    ("performed_by_id", "people_person"),
                    ("supervised_by_id", "people_person"),
                    ("inspector_id", "people_person"),
                    ("work_id", "programme_workdone"),
                ),
            )
        ),
        migrations.RunSQL(RULES, REVERSE),
    ]
