"""Database rules for departures and the annual review of a programme (REQ-285, REQ-287).

The application checks each in ``programme.services``. The database
repeats what must hold whatever the application does:

- what was recorded of a departure is never altered; the day a copy went
  to the owner and the day it was withdrawn are each recorded once;
- an annual review keeps its programme and the day it was opened; once
  completed nothing of it changes, and it keeps the name of whoever
  completed it as that name then stood: the database writes it.
"""

CREATE_RULES = """
CREATE FUNCTION programme_departure_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.programme_id IS DISTINCT FROM OLD.programme_id
       OR NEW.task IS DISTINCT FROM OLD.task
       OR NEW.manufacturer IS DISTINCT FROM OLD.manufacturer
       OR NEW.programme_says IS DISTINCT FROM OLD.programme_says
       OR NEW.compensating_measures IS DISTINCT FROM OLD.compensating_measures
       OR NEW.justification IS DISTINCT FROM OLD.justification
       OR NEW.recorded_on IS DISTINCT FROM OLD.recorded_on
       OR (OLD.owner_copy_sent_on IS NOT NULL
           AND NEW.owner_copy_sent_on IS DISTINCT FROM OLD.owner_copy_sent_on)
       OR (OLD.withdrawn_on IS NOT NULL
           AND NEW.withdrawn_on IS DISTINCT FROM OLD.withdrawn_on) THEN
        RAISE EXCEPTION 'What was recorded of a departure is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER departure_rules BEFORE UPDATE ON programme_departure
    FOR EACH ROW EXECUTE FUNCTION programme_departure_rules();

CREATE FUNCTION programme_annualreview_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.completed_on IS NOT NULL THEN
            RAISE EXCEPTION 'An annual review is opened before it is completed'
                USING ERRCODE = 'check_violation';
        END IF;
        NEW.completed_by_name := '';
        RETURN NEW;
    END IF;
    IF OLD.completed_on IS NOT NULL THEN
        RAISE EXCEPTION 'A completed annual review is never altered'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.programme_id IS DISTINCT FROM OLD.programme_id
       OR NEW.opened_on IS DISTINCT FROM OLD.opened_on THEN
        RAISE EXCEPTION 'An annual review keeps its programme and the day it was opened'
            USING ERRCODE = 'check_violation';
    END IF;
    NEW.completed_by_name := '';
    IF NEW.completed_on IS NOT NULL THEN
        SELECT full_name INTO NEW.completed_by_name
          FROM accounts_user
         WHERE id = NEW.completed_by_id;
        NEW.completed_by_name := COALESCE(NEW.completed_by_name, '');
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER annualreview_rules BEFORE INSERT OR UPDATE ON programme_annualreview
    FOR EACH ROW EXECUTE FUNCTION programme_annualreview_rules();
"""

DROP_RULES = """
DROP TRIGGER annualreview_rules ON programme_annualreview;
DROP FUNCTION programme_annualreview_rules();
DROP TRIGGER departure_rules ON programme_departure;
DROP FUNCTION programme_departure_rules();
"""
