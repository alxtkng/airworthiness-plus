"""Database rules for review certificates (REQ-110, hazards H-007 and H-010).

The serial of a certificate issued by the organisation is allocated by the
database, inside the transaction that issues it. One allocation at a time
for each organisation; the next number is one more than the highest ever
recorded, and a certificate is never deleted, so a number is never used
twice. What a certificate says, once recorded, cannot be altered.
"""

CREATE_SERIALS = """
CREATE FUNCTION reviews_allocate_serial(organisation uuid) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
    next_number integer;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('review certificate ' || organisation::text, 0));
    SELECT COALESCE(max(serial_number), 0) + 1 INTO next_number
      FROM reviews_certificate
     WHERE organisation_id = organisation;
    RETURN next_number;
END
$$;

CREATE FUNCTION reviews_certificate_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    approval text;
BEGIN
    IF NEW.issued_by_id IS NULL THEN
        NEW.serial_number := NULL;
        RETURN NEW;
    END IF;
    NEW.serial_number := reviews_allocate_serial(NEW.organisation_id);
    SELECT approval_reference INTO approval
      FROM organisations_organisation
     WHERE id = NEW.organisation_id;
    NEW.reference := approval || '-ARC-' || lpad(NEW.serial_number::text, 4, '0');
    RETURN NEW;
END
$$;

CREATE FUNCTION reviews_certificate_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.serial_number IS DISTINCT FROM OLD.serial_number
       OR NEW.reference IS DISTINCT FROM OLD.reference
       OR NEW.issued_on IS DISTINCT FROM OLD.issued_on
       OR NEW.valid_to IS DISTINCT FROM OLD.valid_to
       OR NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.issued_by_id IS DISTINCT FROM OLD.issued_by_id
       OR (OLD.voided AND NOT NEW.voided) THEN
        RAISE EXCEPTION 'What a certificate says is never altered once recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER certificate_serial BEFORE INSERT ON reviews_certificate
    FOR EACH ROW EXECUTE FUNCTION reviews_certificate_before_insert();
CREATE TRIGGER certificate_fixed BEFORE UPDATE ON reviews_certificate
    FOR EACH ROW EXECUTE FUNCTION reviews_certificate_fixed();
"""

DROP_SERIALS = """
DROP TRIGGER certificate_fixed ON reviews_certificate;
DROP TRIGGER certificate_serial ON reviews_certificate;
DROP FUNCTION reviews_certificate_fixed();
DROP FUNCTION reviews_certificate_before_insert();
DROP FUNCTION reviews_allocate_serial(uuid);
"""
