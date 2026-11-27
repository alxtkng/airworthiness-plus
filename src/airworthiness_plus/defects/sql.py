"""Database rules for defects (REQ-220, REQ-221, REQ-224, REQ-225).

The application checks a defect in ``defects.services``. The database
repeats what must hold whatever the application does:

- who decided is kept as their record stood on the day the defect was
  recorded: the database writes the name and the licence itself;
- what was recorded of a defect and its decision is never altered, and
  nothing of a closed defect changes;
- a limit is at most 365 days after the decision;
- a defect that is Not Deferrable is recorded against an aircraft that is
  Unserviceable, and the aircraft is not made Serviceable while such a
  defect is open (ML.A.403(a)).
"""

CREATE_DEFECT_RULES = """
CREATE FUNCTION defects_defect_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.decided_by_name := '';
        NEW.decided_by_licence := '';
        IF NEW.decided_by_id IS NOT NULL THEN
            SELECT full_name, licence INTO NEW.decided_by_name, NEW.decided_by_licence
              FROM people_person
             WHERE id = NEW.decided_by_id;
        END IF;
        NEW.decided_by_name := COALESCE(NEW.decided_by_name, '');
        NEW.decided_by_licence := COALESCE(NEW.decided_by_licence, '');
        IF NEW.limit_on IS NOT NULL AND NEW.limit_on > NEW.decided_on + 365 THEN
            RAISE EXCEPTION 'A limit is at most 365 days after the decision'
                USING ERRCODE = 'check_violation';
        END IF;
        IF NEW.decision = 'Not Deferrable' AND NEW.closed_on IS NULL AND NOT EXISTS (
            SELECT 1 FROM aircraft_aircraft
             WHERE id = NEW.aircraft_id AND status = 'Unserviceable'
        ) THEN
            RAISE EXCEPTION 'A defect that is not deferrable is recorded against an aircraft '
                'that is Unserviceable'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;

    IF OLD.closed_on IS NOT NULL THEN
        RAISE EXCEPTION 'A closed defect is never altered' USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.title IS DISTINCT FROM OLD.title
       OR NEW.note IS DISTINCT FROM OLD.note
       OR NEW.found_on IS DISTINCT FROM OLD.found_on
       OR NEW.chapter IS DISTINCT FROM OLD.chapter
       OR NEW.system IS DISTINCT FROM OLD.system
       OR NEW.decision IS DISTINCT FROM OLD.decision
       OR NEW.basis IS DISTINCT FROM OLD.basis
       OR NEW.decided_on IS DISTINCT FROM OLD.decided_on
       OR NEW.decided_by_id IS DISTINCT FROM OLD.decided_by_id
       OR NEW.decided_by_name IS DISTINCT FROM OLD.decided_by_name
       OR NEW.decided_by_licence IS DISTINCT FROM OLD.decided_by_licence
       OR NEW.default_days IS DISTINCT FROM OLD.default_days
       OR NEW.data_limit_on IS DISTINCT FROM OLD.data_limit_on
       OR NEW.limit_on IS DISTINCT FROM OLD.limit_on THEN
        RAISE EXCEPTION 'What was recorded of a defect and its decision is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER defect_rules BEFORE INSERT OR UPDATE ON defects_defect
    FOR EACH ROW EXECUTE FUNCTION defects_defect_rules();

CREATE FUNCTION defects_aircraft_serviceable_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = 'Serviceable' AND OLD.status IS DISTINCT FROM NEW.status AND EXISTS (
        SELECT 1 FROM defects_defect
         WHERE aircraft_id = NEW.id AND decision = 'Not Deferrable' AND closed_on IS NULL
    ) THEN
        RAISE EXCEPTION 'An aircraft with an open defect that is not deferrable '
            'is not made Serviceable'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER open_defect_guard BEFORE UPDATE OF status ON aircraft_aircraft
    FOR EACH ROW EXECUTE FUNCTION defects_aircraft_serviceable_guard();
"""

DROP_DEFECT_RULES = """
DROP TRIGGER open_defect_guard ON aircraft_aircraft;
DROP FUNCTION defects_aircraft_serviceable_guard();
DROP TRIGGER defect_rules ON defects_defect;
DROP FUNCTION defects_defect_rules();
"""
