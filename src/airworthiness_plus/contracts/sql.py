"""Database rules for contracts and work orders (REQ-241, REQ-245).

A signed contract is a document: what it says of the aircraft, the owner
and the organisation is kept as it stood on the day it was recorded. The
database writes those values itself, whatever the application sends, and
refuses any later change to them. Ending a contract, telling the Civil
Aviation Authority and closing a work order are each recorded once.
"""

CREATE_CONTRACT_RULES = """
CREATE FUNCTION contracts_contract_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT registration, type_rating, serial_number
          INTO NEW.registration, NEW.type_rating, NEW.serial_number
          FROM aircraft_aircraft WHERE id = NEW.aircraft_id;
        SELECT name INTO NEW.owner_name FROM customers_customer WHERE id = NEW.customer_id;
        SELECT name, address, approval_reference
          INTO NEW.organisation_name, NEW.organisation_address,
               NEW.organisation_approval_reference
          FROM organisations_organisation WHERE id = NEW.organisation_id;
        NEW.registration := COALESCE(NEW.registration, '');
        NEW.type_rating := COALESCE(NEW.type_rating, '');
        NEW.serial_number := COALESCE(NEW.serial_number, '');
        NEW.owner_name := COALESCE(NEW.owner_name, '');
        NEW.organisation_name := COALESCE(NEW.organisation_name, '');
        NEW.organisation_address := COALESCE(NEW.organisation_address, '');
        NEW.organisation_approval_reference := COALESCE(NEW.organisation_approval_reference, '');
        RETURN NEW;
    END IF;

    IF NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.customer_id IS DISTINCT FROM OLD.customer_id
       OR NEW.scope IS DISTINCT FROM OLD.scope
       OR NEW.tasks IS DISTINCT FROM OLD.tasks
       OR NEW.type_of_operation IS DISTINCT FROM OLD.type_of_operation
       OR NEW.owner_address IS DISTINCT FROM OLD.owner_address
       OR NEW.signed_on IS DISTINCT FROM OLD.signed_on
       OR NEW.registration IS DISTINCT FROM OLD.registration
       OR NEW.type_rating IS DISTINCT FROM OLD.type_rating
       OR NEW.serial_number IS DISTINCT FROM OLD.serial_number
       OR NEW.owner_name IS DISTINCT FROM OLD.owner_name
       OR NEW.organisation_name IS DISTINCT FROM OLD.organisation_name
       OR NEW.organisation_address IS DISTINCT FROM OLD.organisation_address
       OR NEW.organisation_approval_reference
          IS DISTINCT FROM OLD.organisation_approval_reference THEN
        RAISE EXCEPTION 'What a contract says is never altered once recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    IF (OLD.ended_on IS NOT NULL AND (NEW.ended_on IS DISTINCT FROM OLD.ended_on
                                      OR NEW.end_reason IS DISTINCT FROM OLD.end_reason))
       OR (OLD.authority_told_on IS NOT NULL
           AND NEW.authority_told_on IS DISTINCT FROM OLD.authority_told_on) THEN
        RAISE EXCEPTION 'The end of a contract is recorded once'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER contract_rules BEFORE INSERT OR UPDATE ON contracts_contract
    FOR EACH ROW EXECUTE FUNCTION contracts_contract_rules();

CREATE FUNCTION contracts_workorder_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT customer.name INTO NEW.owner_name
          FROM aircraft_aircraft aircraft
          JOIN customers_customer customer ON customer.id = aircraft.customer_id
         WHERE aircraft.id = NEW.aircraft_id;
        NEW.owner_name := COALESCE(NEW.owner_name, '');
        RETURN NEW;
    END IF;

    IF NEW.aircraft_id IS DISTINCT FROM OLD.aircraft_id
       OR NEW.contract_id IS DISTINCT FROM OLD.contract_id
       OR NEW.work IS DISTINCT FROM OLD.work
       OR NEW.ordered_by IS DISTINCT FROM OLD.ordered_by
       OR NEW.agreed_on IS DISTINCT FROM OLD.agreed_on
       OR NEW.owner_name IS DISTINCT FROM OLD.owner_name THEN
        RAISE EXCEPTION 'What a work order says is never altered once recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    IF OLD.closed_on IS NOT NULL THEN
        RAISE EXCEPTION 'A work order is closed once' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER workorder_rules BEFORE INSERT OR UPDATE ON contracts_workorder
    FOR EACH ROW EXECUTE FUNCTION contracts_workorder_rules();
"""

DROP_CONTRACT_RULES = """
DROP TRIGGER workorder_rules ON contracts_workorder;
DROP FUNCTION contracts_workorder_rules();
DROP TRIGGER contract_rules ON contracts_contract;
DROP FUNCTION contracts_contract_rules();
"""
