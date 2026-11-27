"""Database rules for transfers, positions and baselines (REQ-268, REQ-269, REQ-274).

The application checks each in ``configuration.services``. The database
repeats what must hold whatever the application does:

- an item of a transfer keeps its transfer and its number, and nothing of
  it changes once the aircraft is in the Fleet;
- an aircraft with a transfer checklist is not moved to the Fleet while an
  item of it is open or in progress;
- a position keeps its aircraft, and a change it is given is a change of
  that aircraft;
- a baseline is not signed with an item still open: a tracked position not
  recorded, or one that needs a recorded change and has none. What it
  shows is written by the database, as it stood: who signed, the
  organisation, the aircraft and every position and change.
"""

CREATE_RULES = """
CREATE FUNCTION configuration_transferitem_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.transfer_id IS DISTINCT FROM OLD.transfer_id
       OR NEW.number IS DISTINCT FROM OLD.number THEN
        RAISE EXCEPTION 'An item of a transfer keeps its transfer and its number'
            USING ERRCODE = 'check_violation';
    END IF;
    IF EXISTS (
        SELECT 1 FROM configuration_transfer t
          JOIN aircraft_aircraft a ON a.id = t.aircraft_id
         WHERE t.id = OLD.transfer_id AND a.stage = 'Fleet'
    ) THEN
        RAISE EXCEPTION 'The checklist of an aircraft in the Fleet is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER transferitem_rules BEFORE UPDATE ON configuration_transferitem
    FOR EACH ROW EXECUTE FUNCTION configuration_transferitem_rules();

CREATE FUNCTION configuration_transfer_complete_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.stage = 'Fleet' AND OLD.stage IS DISTINCT FROM NEW.stage AND EXISTS (
        SELECT 1 FROM configuration_transferitem i
          JOIN configuration_transfer t ON t.id = i.transfer_id
         WHERE t.aircraft_id = NEW.id AND i.state NOT IN ('Complete', 'Not Applicable')
    ) THEN
        RAISE EXCEPTION 'An aircraft is not moved to the Fleet with an item of its '
            'transfer checklist still open'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER transfer_complete_guard BEFORE UPDATE OF stage ON aircraft_aircraft
    FOR EACH ROW EXECUTE FUNCTION configuration_transfer_complete_guard();

CREATE FUNCTION configuration_position_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id THEN
        RAISE EXCEPTION 'A position keeps its aircraft' USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.change_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM modifications_change
         WHERE id = NEW.change_id AND aircraft_id = NEW.aircraft_id
    ) THEN
        RAISE EXCEPTION 'A position is given a change of its own aircraft'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER position_rules BEFORE INSERT OR UPDATE ON configuration_position
    FOR EACH ROW EXECUTE FUNCTION configuration_position_rules();

CREATE FUNCTION configuration_baseline_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM configuration_position WHERE aircraft_id = NEW.aircraft_id
    ) THEN
        RAISE EXCEPTION 'A baseline is signed for an aircraft with positions recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    IF EXISTS (
        SELECT 1 FROM configuration_position
         WHERE aircraft_id = NEW.aircraft_id
           AND ((tracked AND NOT recorded) OR (needs_change AND change_id IS NULL))
    ) THEN
        RAISE EXCEPTION 'A configuration baseline is not signed with items still open'
            USING ERRCODE = 'check_violation';
    END IF;
    SELECT full_name INTO NEW.signed_by_name FROM accounts_user WHERE id = NEW.signed_by_id;
    SELECT name INTO NEW.organisation_name
      FROM organisations_organisation WHERE id = NEW.organisation_id;
    SELECT registration, type_rating, serial_number
      INTO NEW.aircraft_registration, NEW.type_rating, NEW.serial_number
      FROM aircraft_aircraft WHERE id = NEW.aircraft_id;
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
               'product', p.product, 'chapter', p.chapter, 'name', p.name,
               'required', p.required, 'tracked', p.tracked, 'recorded', p.recorded,
               'part_number', p.part_number, 'serial_number', p.serial_number,
               'source', p.source, 'change', COALESCE(c.title, ''))
               ORDER BY p.product, p.chapter, p.name, p.id), '[]'::jsonb)::text
      INTO NEW.positions
      FROM configuration_position p
      LEFT JOIN modifications_change c ON c.id = p.change_id
     WHERE p.aircraft_id = NEW.aircraft_id;
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
               'title', title, 'route', route, 'reference', reference,
               'mass_effect', mass_effect, 'embodied_on', embodied_on)
               ORDER BY embodied_on, title, id), '[]'::jsonb)::text
      INTO NEW.changes
      FROM modifications_change
     WHERE aircraft_id = NEW.aircraft_id AND embodied_on IS NOT NULL;
    NEW.signed_by_name := COALESCE(NEW.signed_by_name, '');
    NEW.organisation_name := COALESCE(NEW.organisation_name, '');
    RETURN NEW;
END
$$;

CREATE TRIGGER baseline_keeps BEFORE INSERT ON configuration_baseline
    FOR EACH ROW EXECUTE FUNCTION configuration_baseline_before_insert();
"""

DROP_RULES = """
DROP TRIGGER baseline_keeps ON configuration_baseline;
DROP FUNCTION configuration_baseline_before_insert();
DROP TRIGGER position_rules ON configuration_position;
DROP FUNCTION configuration_position_rules();
DROP TRIGGER transfer_complete_guard ON aircraft_aircraft;
DROP FUNCTION configuration_transfer_complete_guard();
DROP TRIGGER transferitem_rules ON configuration_transferitem;
DROP FUNCTION configuration_transferitem_rules();
"""
