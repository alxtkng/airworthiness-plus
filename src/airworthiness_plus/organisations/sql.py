"""SQL for the approvals an organisation holds (REQ-200)."""

# Run once for each organisation by ``history.sql.for_each_organisation``: an
# organisation set up before approvals were records is given the record of the
# approval it was set up with. One that has it is left as it is.
APPROVAL_FOR_EACH_ORGANISATION = """
        INSERT INTO organisations_approval (id, organisation_id, approval, reference)
        SELECT gen_random_uuid(), one.id, one.approval_type, one.approval_reference
          FROM organisations_organisation one
         WHERE one.id = organisation
           AND NOT EXISTS (SELECT 1 FROM organisations_approval held
                            WHERE held.organisation_id = one.id
                              AND held.approval = one.approval_type);
"""

# The approval an organisation was set up with and its reference are set by
# Airworthiness Limited, as the owner of the tables, and by nobody else
# (REQ-004, REQ-200). Application code never
# changes them; the database now refuses the application's role as well, so
# that a fault in the application cannot (independent review of 24 November
# 2026, finding 11). The owner is told from the application as the history
# tells them: a superuser, or the owner of the table.
CREATE_SET_UP_APPROVAL_FIXED = """
CREATE FUNCTION organisations_is_owner() RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT (SELECT rolsuper FROM pg_roles WHERE rolname = current_user)
        OR current_user = (SELECT tableowner FROM pg_tables
                            WHERE schemaname = current_schema()
                              AND tablename = 'organisations_organisation')
$$;

CREATE FUNCTION organisations_set_up_approval_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.approval_type IS DISTINCT FROM OLD.approval_type
        OR NEW.approval_reference IS DISTINCT FROM OLD.approval_reference)
       AND NOT organisations_is_owner() THEN
        RAISE EXCEPTION
            'Only the owner of the records changes the approval an organisation was set up with'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER set_up_approval_guard BEFORE UPDATE ON organisations_organisation
    FOR EACH ROW EXECUTE FUNCTION organisations_set_up_approval_guard();

CREATE FUNCTION organisations_approval_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    set_up_with text;
BEGIN
    IF organisations_is_owner() THEN
        RETURN NEW;
    END IF;
    IF NEW.approval IS DISTINCT FROM OLD.approval THEN
        RAISE EXCEPTION 'The record of an approval is never made the record of another'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    SELECT approval_type INTO set_up_with
      FROM organisations_organisation
     WHERE id = OLD.organisation_id;
    IF OLD.approval = set_up_with AND NEW.reference IS DISTINCT FROM OLD.reference THEN
        RAISE EXCEPTION
            'Only the owner of the records changes the approval an organisation was set up with'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER approval_guard BEFORE UPDATE ON organisations_approval
    FOR EACH ROW EXECUTE FUNCTION organisations_approval_guard();
"""

DROP_SET_UP_APPROVAL_FIXED = """
DROP TRIGGER approval_guard ON organisations_approval;
DROP FUNCTION organisations_approval_guard();
DROP TRIGGER set_up_approval_guard ON organisations_organisation;
DROP FUNCTION organisations_set_up_approval_guard();
DROP FUNCTION organisations_is_owner();
"""
