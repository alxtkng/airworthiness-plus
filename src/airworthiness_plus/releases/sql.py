"""Database rules for certificates of release to service (REQ-261).

A certificate is added and never changed: the application has no right to
update the table. What it says of the work, of the certifying staff of the
organisation and of the organisation's approval is written here, as each
stood on the day it was recorded, whatever the application sends. It is
not issued before the work was completed.
"""

CREATE_RELEASE_RULES = """
CREATE FUNCTION releases_release_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    SELECT aircraft.registration, work.description, work.dated
      INTO NEW.registration, NEW.maintenance, NEW.completed_on
      FROM programme_workdone work
      JOIN aircraft_aircraft aircraft ON aircraft.id = work.aircraft_id
     WHERE work.id = NEW.work_id;
    IF NEW.kind = 'Organisation Certifying Staff' THEN
        SELECT full_name, licence INTO NEW.issuer_name, NEW.licence
          FROM people_person WHERE id = NEW.issued_by_id;
        SELECT approval_reference INTO NEW.approval_reference
          FROM organisations_organisation WHERE id = NEW.organisation_id;
    ELSE
        NEW.approval_reference := '';
    END IF;
    NEW.registration := COALESCE(NEW.registration, '');
    NEW.maintenance := COALESCE(NEW.maintenance, '');
    NEW.issuer_name := COALESCE(NEW.issuer_name, '');
    NEW.licence := COALESCE(NEW.licence, '');
    NEW.approval_reference := COALESCE(NEW.approval_reference, '');
    IF NEW.issued_on < NEW.completed_on THEN
        RAISE EXCEPTION 'A certificate is not issued before the work was completed'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER release_rules BEFORE INSERT ON releases_release
    FOR EACH ROW EXECUTE FUNCTION releases_release_rules();
"""

DROP_RELEASE_RULES = """
DROP TRIGGER release_rules ON releases_release;
DROP FUNCTION releases_release_rules();
"""
