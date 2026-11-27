"""Database rules for service bulletins and changes (REQ-250, REQ-252).

The application checks each in ``modifications.services``. The database
repeats what must hold whatever the application does:

- what was recorded of a service bulletin is never altered, and the
  owner's decision is recorded once;
- what was recorded of a change or repair is never altered, and the day
  it was embodied is recorded once.
"""

CREATE_RULES = """
CREATE FUNCTION modifications_bulletin_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.decision <> 'Awaiting Owner' THEN
        RAISE EXCEPTION 'A decision on a service bulletin is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.title IS DISTINCT FROM OLD.title
       OR NEW.reference IS DISTINCT FROM OLD.reference
       OR NEW.classification IS DISTINCT FROM OLD.classification
       OR NEW.sent_on IS DISTINCT FROM OLD.sent_on
       OR NEW.reminder_on IS DISTINCT FROM OLD.reminder_on THEN
        RAISE EXCEPTION 'What was recorded of a service bulletin is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER bulletin_rules BEFORE UPDATE ON modifications_bulletin
    FOR EACH ROW EXECUTE FUNCTION modifications_bulletin_rules();

CREATE FUNCTION modifications_change_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.embodied_on IS NOT NULL
       OR NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.title IS DISTINCT FROM OLD.title
       OR NEW.route IS DISTINCT FROM OLD.route
       OR NEW.data IS DISTINCT FROM OLD.data
       OR NEW.reference IS DISTINCT FROM OLD.reference
       OR NEW.mass_effect IS DISTINCT FROM OLD.mass_effect THEN
        RAISE EXCEPTION 'What was recorded of a change or repair is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER change_rules BEFORE UPDATE ON modifications_change
    FOR EACH ROW EXECUTE FUNCTION modifications_change_rules();
"""

DROP_RULES = """
DROP TRIGGER change_rules ON modifications_change;
DROP FUNCTION modifications_change_rules();
DROP TRIGGER bulletin_rules ON modifications_bulletin;
DROP FUNCTION modifications_bulletin_rules();
"""
