"""Database rules for person records (REQ-204).

Every sign-in belongs to a person. The application makes the person with
the sign-in. The database refuses a sign-in that has no person, whoever
made it: the check runs when the transaction ends, so that the two can be
made in either order within it.

By then the organisation the work was for may no longer be set on the
session, and row-level security would hide the person from the check. So
the check sets the organisation of the sign-in it is checking, looks, and
puts back what was set before.
"""

CREATE_USER_HAS_A_PERSON = """
CREATE FUNCTION people_user_has_a_person() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    before text := COALESCE(current_setting('airworthiness.organisation', true), '');
    found boolean;
BEGIN
    PERFORM set_config('airworthiness.organisation', NEW.organisation_id::text, true);
    found := EXISTS (SELECT 1 FROM people_person
                      WHERE user_id = NEW.id AND organisation_id = NEW.organisation_id);
    PERFORM set_config('airworthiness.organisation', before, true);
    IF NOT found THEN
        RAISE EXCEPTION 'A sign-in belongs to a person: % has no person record', NEW.username
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END
$$;

CREATE CONSTRAINT TRIGGER user_has_a_person AFTER INSERT ON accounts_user
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION people_user_has_a_person();
"""

DROP_USER_HAS_A_PERSON = """
DROP TRIGGER user_has_a_person ON accounts_user;
DROP FUNCTION people_user_has_a_person();
"""

# Run once for each organisation by ``history.sql.for_each_organisation``: a
# sign-in from before person records is given its person, named as the sign-in
# is. One that has a person is left as it is.
PERSON_FOR_EACH_USER = """
        INSERT INTO people_person
            (id, organisation_id, user_id, full_name, role, staff_group, employment, licence)
        SELECT gen_random_uuid(), one.organisation_id, one.id, one.full_name, '',
               'Other Staff', 'Employed', ''
          FROM accounts_user one
         WHERE one.organisation_id = organisation
           AND NOT EXISTS (SELECT 1 FROM people_person held WHERE held.user_id = one.id);
"""

# The check above runs when a sign-in is made. A sign-in must have its person
# after every change, not only then: a person's sign-in cannot be taken off the
# person, or given to nothing, so that a sign-in is left with no person. This
# runs when a person's sign-in changes, at the end of the transaction, so that
# a sign-in may be moved within it (independent review of 24 November 2026,
# finding 11). A person is never deleted: the database refuses.
CREATE_SIGN_IN_KEEPS_ITS_PERSON = """
CREATE FUNCTION people_sign_in_keeps_its_person() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    before text := COALESCE(current_setting('airworthiness.organisation', true), '');
    found boolean;
BEGIN
    IF OLD.user_id IS NULL OR NEW.user_id IS NOT DISTINCT FROM OLD.user_id THEN
        RETURN NULL;
    END IF;
    PERFORM set_config('airworthiness.organisation', OLD.organisation_id::text, true);
    found := EXISTS (SELECT 1 FROM people_person
                      WHERE user_id = OLD.user_id AND organisation_id = OLD.organisation_id);
    PERFORM set_config('airworthiness.organisation', before, true);
    IF NOT found THEN
        RAISE EXCEPTION
            'A sign-in belongs to a person: the sign-in of % is left with no person record',
            OLD.full_name
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END
$$;

CREATE CONSTRAINT TRIGGER sign_in_keeps_its_person AFTER UPDATE OF user_id ON people_person
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION people_sign_in_keeps_its_person();
"""

DROP_SIGN_IN_KEEPS_ITS_PERSON = """
DROP TRIGGER sign_in_keeps_its_person ON people_person;
DROP FUNCTION people_sign_in_keeps_its_person();
"""
