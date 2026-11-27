"""Database rules for hours and cycles entries (REQ-024, REQ-025), and the
statements that turned what was typed as Owned By into customer records (REQ-209).

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

# What was typed as Owned By becomes a customer record (REQ-209; Decisions.md,
# Canvas Build, decision 3). Run in this order by migration 0003, each loop by
# ``history.sql.for_each_organisation``:
#
# 1. two tables that last only for the migration say which customer each text
#    and each aircraft is given;
# 2. for each organisation, one customer is made for each different text, named
#    as it was typed, with no kind. The spaces around a text are taken off
#    first, so that texts that differ only in them make one customer; an
#    aircraft with no text is given a customer named Not Recorded (independent
#    review of 24 November 2026, finding 13);
# 3. the column of free text is removed;
# 4. for each organisation, each aircraft is given its customer, so that the
#    entry this writes in its history is of the record as it now stands;
# 5. the two tables are removed.
#
# The text itself stays in every earlier entry of the aircraft's history.
OWNERS_TO_CUSTOMERS_BEGIN = """
CREATE TABLE aircraft_owner_migration (
    organisation_id uuid NOT NULL,
    owner text NOT NULL,
    customer_id uuid NOT NULL
);
CREATE TABLE aircraft_customer_migration (
    organisation_id uuid NOT NULL,
    aircraft_id uuid NOT NULL,
    customer_id uuid NOT NULL
);
"""

CUSTOMER_FOR_EACH_OWNER = """
        INSERT INTO aircraft_owner_migration (organisation_id, owner, customer_id)
        SELECT organisation, typed.owner, gen_random_uuid()
          FROM (SELECT DISTINCT btrim(COALESCE(owner, '')) AS owner
                  FROM aircraft_aircraft
                 WHERE organisation_id = organisation) typed;

        INSERT INTO customers_customer (id, organisation_id, name, kind)
        SELECT made.customer_id, made.organisation_id,
               COALESCE(NULLIF(made.owner, ''), 'Not Recorded'), ''
          FROM aircraft_owner_migration made
         WHERE made.organisation_id = organisation
         ORDER BY made.owner;

        INSERT INTO aircraft_customer_migration (organisation_id, aircraft_id, customer_id)
        SELECT one.organisation_id, one.id, made.customer_id
          FROM aircraft_aircraft one
          JOIN aircraft_owner_migration made
            ON made.organisation_id = one.organisation_id
           AND made.owner = btrim(COALESCE(one.owner, ''))
         WHERE one.organisation_id = organisation;
"""

AIRCRAFT_TAKE_THEIR_CUSTOMER = """
        UPDATE aircraft_aircraft one
           SET customer_id = given.customer_id
          FROM aircraft_customer_migration given
         WHERE given.aircraft_id = one.id
           AND given.organisation_id = organisation
           AND one.organisation_id = organisation;
"""

OWNERS_TO_CUSTOMERS_END = """
DROP TABLE aircraft_customer_migration;
DROP TABLE aircraft_owner_migration;
"""
