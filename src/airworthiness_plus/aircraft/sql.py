"""Database rules for hours and cycles entries (REQ-024, REQ-025).

The application checks an entry with ``airworthiness_rules.utilisation``.
The database repeats the part that must hold whatever the application
does: an entry is never below an earlier one or above a later one, and a
correction supersedes an entry of the same counter.
"""

CREATE_UTILISATION_FITS = """
CREATE FUNCTION aircraft_utilisation_fits() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    earlier record;
    later record;
BEGIN
    IF NEW.supersedes_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM aircraft_utilisationentry
         WHERE id = NEW.supersedes_id AND counter_id = NEW.counter_id
    ) THEN
        RAISE EXCEPTION 'A correction supersedes an entry of the same counter'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT hours, cycles INTO earlier
      FROM aircraft_utilisationentry entry
     WHERE entry.counter_id = NEW.counter_id
       AND entry.id IS DISTINCT FROM NEW.supersedes_id
       AND entry.dated <= NEW.dated
       AND NOT EXISTS (SELECT 1 FROM aircraft_utilisationentry newer
                        WHERE newer.supersedes_id = entry.id)
     ORDER BY entry.dated DESC, entry.hours DESC, entry.cycles DESC
     LIMIT 1;
    IF FOUND AND (NEW.hours < earlier.hours OR NEW.cycles < earlier.cycles) THEN
        RAISE EXCEPTION 'Lower than the previous entry' USING ERRCODE = 'check_violation';
    END IF;

    SELECT hours, cycles INTO later
      FROM aircraft_utilisationentry entry
     WHERE entry.counter_id = NEW.counter_id
       AND entry.id IS DISTINCT FROM NEW.supersedes_id
       AND entry.dated > NEW.dated
       AND NOT EXISTS (SELECT 1 FROM aircraft_utilisationentry newer
                        WHERE newer.supersedes_id = entry.id)
     ORDER BY entry.dated ASC, entry.hours ASC, entry.cycles ASC
     LIMIT 1;
    IF FOUND AND (NEW.hours > later.hours OR NEW.cycles > later.cycles) THEN
        RAISE EXCEPTION 'Higher than a later entry' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER utilisation_fits BEFORE INSERT ON aircraft_utilisationentry
    FOR EACH ROW EXECUTE FUNCTION aircraft_utilisation_fits();
"""

DROP_UTILISATION_FITS = """
DROP TRIGGER utilisation_fits ON aircraft_utilisationentry;
DROP FUNCTION aircraft_utilisation_fits();
"""
