"""Database rules for components (REQ-231, REQ-235).

The application checks a fitting and a removal in ``components.services``.
The database repeats what must hold whatever the application does:

- the Aircraft Registration of a fitting is kept as it stood on the day
  the fitting was recorded: the database writes it;
- what was recorded of a fitting is never altered. The day a calendar
  life runs from may be given once, where it was not known;
- a removal is added once, and nothing of a removed fitting changes.
"""

CREATE_INSTALLATION_RULES = """
CREATE FUNCTION components_installation_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT registration INTO NEW.aircraft_registration
          FROM aircraft_aircraft
         WHERE id = NEW.aircraft_id;
        NEW.aircraft_registration := COALESCE(NEW.aircraft_registration, '');
        IF NEW.removed_on IS NOT NULL THEN
            RAISE EXCEPTION 'A removal is recorded after the fitting, not with it'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;

    IF OLD.removed_on IS NOT NULL THEN
        RAISE EXCEPTION 'A fitting that has been removed is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.component_id IS DISTINCT FROM OLD.component_id
       OR NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.aircraft_registration IS DISTINCT FROM OLD.aircraft_registration
       OR NEW.position IS DISTINCT FROM OLD.position
       OR NEW.fitted_on IS DISTINCT FROM OLD.fitted_on
       OR NEW.airframe_hours_fitted IS DISTINCT FROM OLD.airframe_hours_fitted
       OR NEW.airframe_cycles_fitted IS DISTINCT FROM OLD.airframe_cycles_fitted
       OR NEW.hours_at_fitting IS DISTINCT FROM OLD.hours_at_fitting
       OR NEW.cycles_at_fitting IS DISTINCT FROM OLD.cycles_at_fitting
       OR NEW.release_document IS DISTINCT FROM OLD.release_document
       OR (OLD.life_from IS NOT NULL AND NEW.life_from IS DISTINCT FROM OLD.life_from) THEN
        RAISE EXCEPTION 'What was recorded of a fitting is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER installation_rules BEFORE INSERT OR UPDATE ON components_installation
    FOR EACH ROW EXECUTE FUNCTION components_installation_rules();
"""

DROP_INSTALLATION_RULES = """
DROP TRIGGER installation_rules ON components_installation;
DROP FUNCTION components_installation_rules();
"""
