"""A database rule for revisions of maintenance data (REQ-085, hazard H-005).

A superseded revision can never be made current again, whoever asks.
"""

CREATE_NEVER_CURRENT_AGAIN = """
CREATE FUNCTION maintenance_data_never_current_again() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.current = false AND NEW.current = true THEN
        RAISE EXCEPTION 'A superseded revision is never made current again'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER never_current_again BEFORE UPDATE ON maintenance_data_revision
    FOR EACH ROW EXECUTE FUNCTION maintenance_data_never_current_again();
"""

DROP_NEVER_CURRENT_AGAIN = """
DROP TRIGGER never_current_again ON maintenance_data_revision;
DROP FUNCTION maintenance_data_never_current_again();
"""
