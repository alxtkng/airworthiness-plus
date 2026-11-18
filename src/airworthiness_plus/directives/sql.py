"""A database rule for applicability decisions (REQ-063, hazard H-002).

Not Applicable is decided one aircraft at a time. A single statement that
would set it for more than one aircraft is refused, whoever runs it.
"""

CREATE_NO_BULK = """
CREATE FUNCTION directives_no_bulk_not_applicable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT count(*) FROM changed WHERE decision = 'Not Applicable') > 1 THEN
        RAISE EXCEPTION 'Not Applicable is decided one aircraft at a time'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END
$$;

CREATE TRIGGER no_bulk_insert AFTER INSERT ON directives_applicability
    REFERENCING NEW TABLE AS changed
    FOR EACH STATEMENT EXECUTE FUNCTION directives_no_bulk_not_applicable();
CREATE TRIGGER no_bulk_update AFTER UPDATE ON directives_applicability
    REFERENCING NEW TABLE AS changed
    FOR EACH STATEMENT EXECUTE FUNCTION directives_no_bulk_not_applicable();
"""

DROP_NO_BULK = """
DROP TRIGGER no_bulk_update ON directives_applicability;
DROP TRIGGER no_bulk_insert ON directives_applicability;
DROP FUNCTION directives_no_bulk_not_applicable();
"""
