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

# A review is a record of what was verified. Once its certificate is issued,
# neither the review nor any point of it can be changed (REQ-107, REQ-109).
CREATE_REVIEW_FIXED = """
CREATE FUNCTION reviews_review_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.certificate_id IS NOT NULL THEN
        RAISE EXCEPTION 'A review is never altered once its certificate is issued'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE FUNCTION reviews_reviewitem_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM reviews_review
                WHERE id = NEW.review_id AND certificate_id IS NOT NULL) THEN
        RAISE EXCEPTION 'A review is never altered once its certificate is issued'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER review_fixed BEFORE UPDATE ON reviews_review
    FOR EACH ROW EXECUTE FUNCTION reviews_review_fixed();
CREATE TRIGGER reviewitem_fixed BEFORE INSERT OR UPDATE ON reviews_reviewitem
    FOR EACH ROW EXECUTE FUNCTION reviews_reviewitem_fixed();
"""

# After a restore from backup the records may no longer hold every certificate
# that was issued. The next serial then follows the highest serial the owner of
# the records has stated for the organisation, as well as the highest recorded
# (REQ-154, hazard H-007).
ALLOCATE_ABOVE_FLOOR = """
CREATE OR REPLACE FUNCTION reviews_allocate_serial(organisation uuid) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
    recorded integer;
    stated integer;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('review certificate ' || organisation::text, 0));
    SELECT COALESCE(max(serial_number), 0) INTO recorded
      FROM reviews_certificate
     WHERE organisation_id = organisation;
    SELECT COALESCE(max(certificate_serial_floor), 0) INTO stated
      FROM organisations_organisation
     WHERE id = organisation;
    RETURN GREATEST(recorded, stated) + 1;
END
$$;

CREATE FUNCTION organisations_serial_floor_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.certificate_serial_floor < OLD.certificate_serial_floor THEN
        RAISE EXCEPTION 'The highest certificate serial is never lowered'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.certificate_serial_floor <> OLD.certificate_serial_floor
       AND current_user = 'airworthiness_application' THEN
        RAISE EXCEPTION 'Only the owner of the records states the highest certificate serial'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER serial_floor_guard BEFORE UPDATE ON organisations_organisation
    FOR EACH ROW EXECUTE FUNCTION organisations_serial_floor_guard();
"""

ALLOCATE_AS_BEFORE = """
DROP TRIGGER serial_floor_guard ON organisations_organisation;
DROP FUNCTION organisations_serial_floor_guard();
CREATE OR REPLACE FUNCTION reviews_allocate_serial(organisation uuid) RETURNS integer
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
"""

# A certificate the organisation's own review staff issued before these records
# keeps its reference and takes no serial. It is dated no later than the last
# review recorded for the person from before these records, so that it cannot
# stand in for a review in these records or change whether the person has
# recent experience (REQ-109, REQ-110, REQ-113). The issuer written for a
# certificate issued elsewhere is fixed with the rest of what it says.
ALLOW_FROM_BEFORE = """
CREATE OR REPLACE FUNCTION reviews_certificate_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    approval text;
    last_before date;
BEGIN
    IF NEW.issued_by_id IS NULL THEN
        NEW.serial_number := NULL;
        RETURN NEW;
    END IF;
    IF NEW.from_before_records THEN
        SELECT last_review_before_records INTO last_before
          FROM reviews_reviewstaff
         WHERE id = NEW.issued_by_id;
        IF last_before IS NULL OR NEW.issued_on > last_before THEN
            RAISE EXCEPTION
                'No certificate from before these records is after the last review before them'
                USING ERRCODE = 'check_violation';
        END IF;
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

CREATE OR REPLACE FUNCTION reviews_certificate_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.serial_number IS DISTINCT FROM OLD.serial_number
       OR NEW.reference IS DISTINCT FROM OLD.reference
       OR NEW.issued_on IS DISTINCT FROM OLD.issued_on
       OR NEW.valid_to IS DISTINCT FROM OLD.valid_to
       OR NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.issued_by_id IS DISTINCT FROM OLD.issued_by_id
       OR NEW.issued_elsewhere_by IS DISTINCT FROM OLD.issued_elsewhere_by
       OR NEW.from_before_records IS DISTINCT FROM OLD.from_before_records
       OR (OLD.voided AND NOT NEW.voided) THEN
        RAISE EXCEPTION 'What a certificate says is never altered once recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
"""

FROM_BEFORE_NOT_ALLOWED = """
CREATE OR REPLACE FUNCTION reviews_certificate_before_insert() RETURNS trigger
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

CREATE OR REPLACE FUNCTION reviews_certificate_fixed() RETURNS trigger
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
"""

# The day a person was recorded as review staff is fixed, because their last
# review before these records is held to it. A certificate from before these
# records reads that date under a lock, so that it cannot be replaced while
# the certificate is being recorded (REQ-109, REQ-110).
RECORDED_ON_FIXED = """
CREATE FUNCTION reviews_reviewstaff_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.recorded_on IS DISTINCT FROM OLD.recorded_on THEN
        RAISE EXCEPTION 'The day a person was recorded as review staff is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER reviewstaff_fixed BEFORE UPDATE ON reviews_reviewstaff
    FOR EACH ROW EXECUTE FUNCTION reviews_reviewstaff_fixed();
""" + ALLOW_FROM_BEFORE.replace(
    """         WHERE id = NEW.issued_by_id;
        IF last_before IS NULL""",
    """         WHERE id = NEW.issued_by_id
           FOR SHARE;
        IF last_before IS NULL""",
)

RECORDED_ON_NOT_FIXED = (
    """
DROP TRIGGER reviewstaff_fixed ON reviews_reviewstaff;
DROP FUNCTION reviews_reviewstaff_fixed();
"""
    + ALLOW_FROM_BEFORE
)

# The point of a review is checked against the review read under a lock, so
# that a result recorded while the certificate is being issued waits for the
# issue and then sees it (independent review of 20 November 2026, finding 5).
REVIEW_ITEM_FIXED_LOCKED = """
CREATE OR REPLACE FUNCTION reviews_reviewitem_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    issued uuid;
BEGIN
    -- Locked by its id alone: a row left out by a condition on the
    -- certificate would not be locked, and would not wait for the issue.
    SELECT certificate_id INTO issued FROM reviews_review
     WHERE id = NEW.review_id
       FOR SHARE;
    IF issued IS NOT NULL THEN
        RAISE EXCEPTION 'A review is never altered once its certificate is issued'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
"""

REVIEW_ITEM_FIXED_UNLOCKED = """
CREATE OR REPLACE FUNCTION reviews_reviewitem_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM reviews_review
                WHERE id = NEW.review_id AND certificate_id IS NOT NULL) THEN
        RAISE EXCEPTION 'A review is never altered once its certificate is issued'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
"""

DROP_REVIEW_FIXED = """
DROP TRIGGER reviewitem_fixed ON reviews_reviewitem;
DROP TRIGGER review_fixed ON reviews_review;
DROP FUNCTION reviews_reviewitem_fixed();
DROP FUNCTION reviews_review_fixed();
"""

# What a certificate shows of who issued it is kept on the certificate, and an
# extension keeps what it shows too (REQ-110; independent review of
# 24 November 2026, finding 1). Run once for each organisation by
# ``history.sql.for_each_organisation``: a certificate or an extension recorded
# before these were kept is given the names as they stand on the day of the
# migration, which is the earliest day the records can speak for. The history
# trigger writes an entry for each, against the database role, naming what was
# set. One that has them is left as it is.
KEEP_WHAT_EACH_SHOWED = """
        UPDATE reviews_certificate certificate
           SET organisation_name = ours.name,
               organisation_address = ours.address,
               organisation_approval_reference = ours.approval_reference,
               review_staff_name = person.full_name
          FROM organisations_organisation ours, reviews_reviewstaff staff, accounts_user person
         WHERE certificate.organisation_id = organisation
           AND ours.id = organisation
           AND staff.id = certificate.issued_by_id
           AND person.id = staff.user_id
           AND certificate.organisation_name = ''
           AND certificate.review_staff_name = '';

        UPDATE reviews_extension extension
           SET extended_by_name = person.full_name,
               organisation_name = ours.name,
               organisation_approval_reference = ours.approval_reference
          FROM organisations_organisation ours, accounts_user person
         WHERE extension.organisation_id = organisation
           AND ours.id = organisation
           AND person.id = extension.extended_by_id
           AND extension.organisation_name = ''
           AND extension.extended_by_name = '';
"""

_CERTIFICATE_FIXED = """
CREATE OR REPLACE FUNCTION reviews_certificate_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.serial_number IS DISTINCT FROM OLD.serial_number
       OR NEW.reference IS DISTINCT FROM OLD.reference
       OR NEW.issued_on IS DISTINCT FROM OLD.issued_on
       OR NEW.valid_to IS DISTINCT FROM OLD.valid_to
       OR NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.issued_by_id IS DISTINCT FROM OLD.issued_by_id
       OR NEW.issued_elsewhere_by IS DISTINCT FROM OLD.issued_elsewhere_by
       OR NEW.from_before_records IS DISTINCT FROM OLD.from_before_records-- MORE
       OR (OLD.voided AND NOT NEW.voided) THEN
        RAISE EXCEPTION 'What a certificate says is never altered once recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
"""

# The database writes what a certificate of the organisation's own shows, from
# the organisation and the person as they stand when it is recorded, whatever
# the application sends. An extension is given what it shows in the same way.
_BEFORE_INSERT = """
CREATE OR REPLACE FUNCTION reviews_certificate_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    ours organisations_organisation%ROWTYPE;
    last_before date;
BEGIN
    IF NEW.issued_by_id IS NULL THEN
        NEW.serial_number := NULL;-- BLANK
        RETURN NEW;
    END IF;
    SELECT * INTO ours FROM organisations_organisation WHERE id = NEW.organisation_id;-- KEPT
    IF NEW.from_before_records THEN
        SELECT last_review_before_records INTO last_before
          FROM reviews_reviewstaff
         WHERE id = NEW.issued_by_id
           FOR SHARE;
        IF last_before IS NULL OR NEW.issued_on > last_before THEN
            RAISE EXCEPTION
                'No certificate from before these records is after the last review before them'
                USING ERRCODE = 'check_violation';
        END IF;
        NEW.serial_number := NULL;
        RETURN NEW;
    END IF;
    NEW.serial_number := reviews_allocate_serial(NEW.organisation_id);
    NEW.reference := ours.approval_reference || '-ARC-' || lpad(NEW.serial_number::text, 4, '0');
    RETURN NEW;
END
$$;
"""

WHAT_IT_SHOWED_FIXED = "\n".join(
    (
        _BEFORE_INSERT.replace(
            "-- BLANK",
            """
        NEW.organisation_name := '';
        NEW.organisation_address := '';
        NEW.organisation_approval_reference := '';
        NEW.review_staff_name := '';""",
        ).replace(
            "-- KEPT",
            """
    NEW.organisation_name := ours.name;
    NEW.organisation_address := ours.address;
    NEW.organisation_approval_reference := ours.approval_reference;
    SELECT person.full_name INTO NEW.review_staff_name
      FROM reviews_reviewstaff staff
      JOIN accounts_user person ON person.id = staff.user_id
     WHERE staff.id = NEW.issued_by_id;""",
        ),
        """
CREATE FUNCTION reviews_extension_before_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    SELECT name, approval_reference
      INTO NEW.organisation_name, NEW.organisation_approval_reference
      FROM organisations_organisation
     WHERE id = NEW.organisation_id;
    SELECT full_name INTO NEW.extended_by_name FROM accounts_user WHERE id = NEW.extended_by_id;
    RETURN NEW;
END
$$;

CREATE TRIGGER extension_keeps BEFORE INSERT ON reviews_extension
    FOR EACH ROW EXECUTE FUNCTION reviews_extension_before_insert();
""",
        _CERTIFICATE_FIXED.replace(
            "-- MORE",
            """
       OR NEW.organisation_name IS DISTINCT FROM OLD.organisation_name
       OR NEW.organisation_address IS DISTINCT FROM OLD.organisation_address
       OR NEW.organisation_approval_reference IS DISTINCT FROM OLD.organisation_approval_reference
       OR NEW.review_staff_name IS DISTINCT FROM OLD.review_staff_name""",
        ),
        """
CREATE FUNCTION reviews_extension_fixed() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.certificate_id IS DISTINCT FROM OLD.certificate_id
       OR NEW.extended_on IS DISTINCT FROM OLD.extended_on
       OR NEW.valid_to IS DISTINCT FROM OLD.valid_to
       OR NEW.extended_by_id IS DISTINCT FROM OLD.extended_by_id
       OR NEW.extended_by_name IS DISTINCT FROM OLD.extended_by_name
       OR NEW.organisation_name IS DISTINCT FROM OLD.organisation_name
       OR NEW.organisation_approval_reference
          IS DISTINCT FROM OLD.organisation_approval_reference THEN
        RAISE EXCEPTION 'What an extension says is never altered once recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER extension_fixed BEFORE UPDATE ON reviews_extension
    FOR EACH ROW EXECUTE FUNCTION reviews_extension_fixed();
""",
    )
)

WHAT_IT_SHOWED_NOT_FIXED = "\n".join(
    (
        """
DROP TRIGGER extension_fixed ON reviews_extension;
DROP FUNCTION reviews_extension_fixed();
DROP TRIGGER extension_keeps ON reviews_extension;
DROP FUNCTION reviews_extension_before_insert();
""",
        _CERTIFICATE_FIXED.replace("-- MORE", ""),
        _BEFORE_INSERT.replace("-- BLANK", "").replace("-- KEPT", ""),
    )
)
