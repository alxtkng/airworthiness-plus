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
