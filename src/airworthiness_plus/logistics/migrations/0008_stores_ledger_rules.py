"""Put the Stores records under ADR-0002 and hold the ledger rules in PostgreSQL (REQ-358).

The application checks the same rules first and explains a refusal. These
triggers are the backstop: a fault or a direct request cannot post a
disposition twice, credit a return, move more than is held, mix units or
act without a current Stores appointment.
"""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

TABLES = {
    "logistics_storesappointment": (
        ("person_id", "people_person"),
        ("approval_id", "organisations_approval"),
    ),
    "logistics_storesappointmentwithdrawal": (("appointment_id", "logistics_storesappointment"),),
    "logistics_storeslocation": (("appointment_id", "logistics_storesappointment"),),
    "logistics_storeslocationwithdrawal": (
        ("location_id", "logistics_storeslocation"),
        ("appointment_id", "logistics_storesappointment"),
    ),
    "logistics_postingevidence": (
        ("disposition_id", "logistics_receivingdisposition"),
        ("location_id", "logistics_storeslocation"),
        ("appointment_id", "logistics_storesappointment"),
    ),
    "logistics_stockposting": (
        ("disposition_id", "logistics_receivingdisposition"),
        ("evidence_id", "logistics_postingevidence"),
        ("appointment_id", "logistics_storesappointment"),
    ),
    "logistics_stockcount": (
        ("posting_id", "logistics_stockposting"),
        ("location_id", "logistics_storeslocation"),
        ("appointment_id", "logistics_storesappointment"),
    ),
    "logistics_stockmovement": (
        ("posting_id", "logistics_stockposting"),
        ("source_id", "logistics_storeslocation"),
        ("destination_id", "logistics_storeslocation"),
        ("count_id", "logistics_stockcount"),
        ("appointment_id", "logistics_storesappointment"),
    ),
}

FORWARD = r"""
CREATE FUNCTION logistics_stores_authority(appointment uuid, wanted text, signed date)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
    grant_record logistics_storesappointment%ROWTYPE;
    signer uuid := NULLIF(current_setting('airworthiness.user', true), '')::uuid;
BEGIN
    SELECT * INTO grant_record FROM logistics_storesappointment WHERE id = appointment;
    IF NOT FOUND OR grant_record.action <> wanted
       OR signed NOT BETWEEN grant_record.starts_on AND grant_record.ends_on
       OR grant_record.approval_reference IS DISTINCT FROM
            organisations_approval_reference_on(grant_record.approval_id, signed)
       OR EXISTS (SELECT 1 FROM logistics_storesappointmentwithdrawal
                   WHERE appointment_id = grant_record.id AND withdrawn_on <= signed)
       OR NOT EXISTS (
            SELECT 1 FROM people_person
             WHERE id = grant_record.person_id AND user_id = signer
               AND (joined_on IS NULL OR joined_on <= signed)
               AND (left_on IS NULL OR left_on > signed))
    THEN
        RAISE EXCEPTION 'The signed-in person needs a current Stores appointment for this action'
            USING ERRCODE = 'insufficient_privilege';
    END IF;
END
$$;

CREATE FUNCTION logistics_stock_on_hand(lot uuid, place uuid) RETURNS numeric
LANGUAGE sql STABLE AS $$
    SELECT COALESCE(sum(CASE WHEN destination_id = place THEN quantity ELSE 0 END), 0)
         - COALESCE(sum(CASE WHEN source_id = place THEN quantity ELSE 0 END), 0)
      FROM logistics_stockmovement
     WHERE posting_id = lot AND (destination_id = place OR source_id = place)
$$;

CREATE FUNCTION logistics_lock_stock(lot uuid) RETURNS void LANGUAGE sql AS $$
    SELECT pg_advisory_xact_lock(hashtextextended('stores-lot:' || lot::text, 0))
$$;

CREATE FUNCTION logistics_location_accepts(
    place uuid, posting_kind text, item_class text, day date
) RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1 FROM logistics_storeslocation location
         WHERE location.id = place
           AND NOT EXISTS (SELECT 1 FROM logistics_storeslocationwithdrawal gone
                            WHERE gone.location_id = location.id AND gone.withdrawn_on <= day)
           AND CASE posting_kind
                 WHEN 'Stock' THEN location.kind = 'Serviceable Store'
                                   AND item_class = ANY (location.classes)
                 WHEN 'Hold' THEN location.kind = 'Quarantine' AND location.secure
                 ELSE false
               END)
$$;

CREATE FUNCTION logistics_quantity_fits(unit text, quantity numeric, serial text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
    SELECT quantity > 0 AND quantity <= 2147483647
       AND CASE unit
             WHEN 'Each' THEN quantity = trunc(quantity) AND (serial = '' OR quantity = 1)
             WHEN 'Litre' THEN serial = ''
             ELSE false
           END
$$;

CREATE FUNCTION logistics_posting_evidence_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM logistics_stores_authority(NEW.appointment_id, 'Post', NEW.assessed_on);
    IF NOT EXISTS (
        SELECT 1 FROM logistics_receivingdisposition
         WHERE id = NEW.disposition_id
           AND outcome IN ('Accepted into Stores', 'Quarantined')
           AND disposition_on <= NEW.assessed_on
    ) THEN
        RAISE EXCEPTION 'Posting evidence follows a Stores acceptance or quarantine decision'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.quantity IS NOT NULL AND NEW.unit <> ''
       AND NOT logistics_quantity_fits(NEW.unit, NEW.quantity, NEW.serial) THEN
        RAISE EXCEPTION 'The quantity does not fit its unit' USING ERRCODE = 'check_violation';
    END IF;
    IF (NEW.shelf_life_basis IN ('Usable Through the Date', 'Expires at the Start of the Date'))
       <> (NEW.shelf_life_to IS NOT NULL) THEN
        RAISE EXCEPTION 'A dated shelf-life basis needs its date, and only that basis has one'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER stores_posting_evidence_rules BEFORE INSERT ON logistics_postingevidence
    FOR EACH ROW EXECUTE FUNCTION logistics_posting_evidence_rules();

CREATE FUNCTION logistics_stock_posting_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    decision logistics_receivingdisposition%ROWTYPE;
    item logistics_receipt%ROWTYPE;
    basis logistics_postingevidence%ROWTYPE;
    last_day date;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended('stores-posting:' || NEW.disposition_id, 0));
    PERFORM logistics_stores_authority(NEW.appointment_id, 'Post', NEW.posted_on);
    SELECT * INTO STRICT decision FROM logistics_receivingdisposition
     WHERE id = NEW.disposition_id;
    SELECT * INTO STRICT item FROM logistics_receipt WHERE id = decision.receipt_id;
    SELECT * INTO basis FROM logistics_postingevidence
     WHERE id = NEW.evidence_id AND disposition_id = NEW.disposition_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'The posting must use evidence recorded for this disposition'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NOT ((decision.outcome = 'Accepted into Stores' AND NEW.kind = 'Stock')
            OR (decision.outcome = 'Quarantined' AND NEW.kind = 'Hold')) THEN
        RAISE EXCEPTION 'Only a Stores acceptance or a quarantine is posted. A return is not'
            USING ERRCODE = 'check_violation';
    END IF;
    IF basis.unit = '' OR basis.quantity IS NULL
       OR NOT logistics_quantity_fits(basis.unit, basis.quantity, basis.serial)
       OR (basis.unit = 'Each' AND basis.quantity <> item.quantity)
       OR NOT logistics_location_accepts(basis.location_id, NEW.kind, item.classification,
                                         NEW.posted_on)
       OR NEW.posted_on < decision.disposition_on THEN
        RAISE EXCEPTION 'The unit, quantity and a compatible location must be resolved'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.kind = 'Hold' THEN
        IF basis.tag !~ '[^[:space:]]' THEN
            RAISE EXCEPTION 'A quarantine hold needs its tag' USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF (CASE item.classification
         WHEN 'Serviceable Component' THEN basis.part_number = ''
              OR (basis.serial = '' AND basis.batch = '')
         WHEN 'Standard Part' THEN basis.specification = '' OR basis.batch = ''
         WHEN 'Material' THEN basis.specification = '' OR basis.batch = ''
         ELSE true
       END) THEN
        RAISE EXCEPTION 'The traceable identity for the class must be resolved'
            USING ERRCODE = 'check_violation';
    END IF;
    last_day := CASE basis.shelf_life_basis
        WHEN 'Usable Through the Date' THEN basis.shelf_life_to
        WHEN 'Expires at the Start of the Date' THEN basis.shelf_life_to - 1
    END;
    IF basis.shelf_life_basis = ''
       OR (basis.shelf_life_basis <> 'Not Applicable' AND last_day < decision.disposition_on) THEN
        RAISE EXCEPTION 'The shelf-life basis must be resolved and valid on arrival in Stores'
            USING ERRCODE = 'check_violation';
    END IF;
    IF basis.serial <> '' AND EXISTS (
        SELECT 1 FROM logistics_stockposting other
          JOIN logistics_postingevidence seen ON seen.id = other.evidence_id
         WHERE other.kind = 'Stock'
           AND lower(seen.serial) = lower(basis.serial)
           AND lower(seen.part_number) = lower(basis.part_number)
           AND lower(seen.manufacturer) = lower(basis.manufacturer)
    ) THEN
        RAISE EXCEPTION 'This serial number already has a custody position'
            USING ERRCODE = 'unique_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER stores_posting_rules BEFORE INSERT ON logistics_stockposting
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_posting_rules();

CREATE FUNCTION logistics_stock_posting_opening() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    basis logistics_postingevidence%ROWTYPE;
    decision logistics_receivingdisposition%ROWTYPE;
BEGIN
    -- The opening movement is written by the same statement as the posting, so
    -- neither can exist without the other.
    SELECT * INTO STRICT basis FROM logistics_postingevidence WHERE id = NEW.evidence_id;
    SELECT * INTO STRICT decision FROM logistics_receivingdisposition
     WHERE id = NEW.disposition_id;
    INSERT INTO logistics_stockmovement (
        id, organisation_id, submission, entered_at, posting_id, kind, source_id,
        destination_id, quantity, moved_on, evidence, count_id, recorded_on, appointment_id
    ) VALUES (
        gen_random_uuid(), NEW.organisation_id, NEW.submission, now(), NEW.id,
        CASE NEW.kind WHEN 'Stock' THEN 'Intake' ELSE 'Hold' END, NULL,
        basis.location_id, basis.quantity, decision.disposition_on,
        'Opening posting from disposition ' || NEW.disposition_id, NULL, NEW.posted_on,
        NEW.appointment_id
    );
    RETURN NULL;
END
$$;
CREATE TRIGGER stores_posting_opening AFTER INSERT ON logistics_stockposting
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_posting_opening();

CREATE FUNCTION logistics_stock_count_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    basis logistics_postingevidence%ROWTYPE;
BEGIN
    PERFORM logistics_lock_stock(NEW.posting_id);
    PERFORM logistics_stores_authority(NEW.appointment_id, 'Count', NEW.counted_on);
    SELECT evidence.* INTO STRICT basis FROM logistics_stockposting posting
      JOIN logistics_postingevidence evidence ON evidence.id = posting.evidence_id
     WHERE posting.id = NEW.posting_id;
    IF NEW.counted < 0 OR (basis.unit = 'Each' AND NEW.counted <> trunc(NEW.counted))
       OR (basis.serial <> '' AND NEW.counted > 1) THEN
        RAISE EXCEPTION 'The count does not fit the unit' USING ERRCODE = 'check_violation';
    END IF;
    NEW.on_hand := logistics_stock_on_hand(NEW.posting_id, NEW.location_id);
    RETURN NEW;
END
$$;
CREATE TRIGGER stores_count_rules BEFORE INSERT ON logistics_stockcount
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_count_rules();

CREATE FUNCTION logistics_stock_movement_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    posting logistics_stockposting%ROWTYPE;
    basis logistics_postingevidence%ROWTYPE;
    item_class text;
    taken logistics_stockcount%ROWTYPE;
    held numeric;
BEGIN
    PERFORM logistics_lock_stock(NEW.posting_id);
    SELECT * INTO STRICT posting FROM logistics_stockposting WHERE id = NEW.posting_id;
    SELECT * INTO STRICT basis FROM logistics_postingevidence WHERE id = posting.evidence_id;
    SELECT receipt.classification INTO STRICT item_class
      FROM logistics_receivingdisposition decision
      JOIN logistics_receipt receipt ON receipt.id = decision.receipt_id
     WHERE decision.id = posting.disposition_id;
    IF NOT logistics_quantity_fits(basis.unit, NEW.quantity, basis.serial)
       OR NEW.moved_on > NEW.recorded_on THEN
        RAISE EXCEPTION 'The movement quantity or date does not fit'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.kind IN ('Intake', 'Hold') THEN
        PERFORM logistics_stores_authority(NEW.appointment_id, 'Post', NEW.recorded_on);
        IF pg_trigger_depth() < 2 OR EXISTS (SELECT 1 FROM logistics_stockmovement WHERE posting_id = NEW.posting_id)
           OR NEW.kind <> (CASE posting.kind WHEN 'Stock' THEN 'Intake' ELSE 'Hold' END)
           OR NEW.destination_id IS DISTINCT FROM basis.location_id
           OR NEW.quantity <> basis.quantity THEN
            RAISE EXCEPTION 'The opening movement is made once, from the posting evidence'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.kind = 'Transfer' THEN
        PERFORM logistics_stores_authority(NEW.appointment_id, 'Move', NEW.recorded_on);
        IF NOT logistics_location_accepts(NEW.destination_id, posting.kind, item_class,
                                          NEW.recorded_on) THEN
            RAISE EXCEPTION 'The destination does not accept this item'
                USING ERRCODE = 'check_violation';
        END IF;
    ELSE
        PERFORM logistics_stores_authority(NEW.appointment_id, 'Adjust', NEW.recorded_on);
        SELECT * INTO taken FROM logistics_stockcount
         WHERE id = NEW.count_id AND posting_id = NEW.posting_id;
        IF NOT FOUND
           OR COALESCE(NEW.source_id, NEW.destination_id) <> taken.location_id
           OR taken.on_hand <> logistics_stock_on_hand(NEW.posting_id, taken.location_id)
           OR NEW.quantity <> abs(taken.counted - taken.on_hand)
           OR (NEW.source_id IS NULL) <> (taken.counted > taken.on_hand) THEN
            RAISE EXCEPTION 'An adjustment applies the variance of a count the ledger still matches'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    IF NEW.source_id IS NOT NULL THEN
        held := logistics_stock_on_hand(NEW.posting_id, NEW.source_id);
        IF held < NEW.quantity THEN
            RAISE EXCEPTION 'The source location holds less than this movement'
                USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER stores_movement_rules BEFORE INSERT ON logistics_stockmovement
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_movement_rules();

CREATE FUNCTION logistics_stores_location_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'logistics_storeslocation' THEN
        PERFORM logistics_stores_authority(NEW.appointment_id, 'Locations', NEW.recorded_on);
        IF EXISTS (SELECT 1 FROM unnest(NEW.classes) AS held(name)
                    WHERE held.name NOT IN ('Serviceable Component', 'Unserviceable Component',
                                            'Unsalvageable Component', 'Standard Part', 'Material'))
        THEN
            RAISE EXCEPTION 'Unknown item class' USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    PERFORM logistics_stores_authority(NEW.appointment_id, 'Locations', NEW.withdrawn_on);
    IF EXISTS (
        SELECT 1 FROM logistics_stockmovement
         WHERE destination_id = NEW.location_id OR source_id = NEW.location_id
         GROUP BY posting_id
        HAVING logistics_stock_on_hand(posting_id, NEW.location_id) <> 0
    ) THEN
        RAISE EXCEPTION 'A location is withdrawn only when it holds no stock'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER stores_location_rules BEFORE INSERT ON logistics_storeslocation
    FOR EACH ROW EXECUTE FUNCTION logistics_stores_location_rules();
CREATE TRIGGER stores_location_withdrawal_rules BEFORE INSERT ON logistics_storeslocationwithdrawal
    FOR EACH ROW EXECUTE FUNCTION logistics_stores_location_rules();
"""

REVERSE = """
DROP TRIGGER stores_location_withdrawal_rules ON logistics_storeslocationwithdrawal;
DROP TRIGGER stores_location_rules ON logistics_storeslocation;
DROP FUNCTION logistics_stores_location_rules();
DROP TRIGGER stores_movement_rules ON logistics_stockmovement;
DROP FUNCTION logistics_stock_movement_rules();
DROP TRIGGER stores_count_rules ON logistics_stockcount;
DROP FUNCTION logistics_stock_count_rules();
DROP TRIGGER stores_posting_opening ON logistics_stockposting;
DROP FUNCTION logistics_stock_posting_opening();
DROP TRIGGER stores_posting_rules ON logistics_stockposting;
DROP FUNCTION logistics_stock_posting_rules();
DROP TRIGGER stores_posting_evidence_rules ON logistics_postingevidence;
DROP FUNCTION logistics_posting_evidence_rules();
DROP FUNCTION logistics_quantity_fits(text, numeric, text);
DROP FUNCTION logistics_location_accepts(uuid, text, text, date);
DROP FUNCTION logistics_lock_stock(uuid);
DROP FUNCTION logistics_stock_on_hand(uuid, uuid);
DROP FUNCTION logistics_stores_authority(uuid, text, date);
"""


def retain(table: str) -> migrations.RunSQL:
    # TABLES supplies the same fixed names as protect_record_table.
    return migrations.RunSQL(
        f"CREATE TRIGGER history_refuse_update BEFORE UPDATE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION history_refuse();",
        f"DROP TRIGGER history_refuse_update ON {table};",
    )


class Migration(migrations.Migration):
    dependencies = [("logistics", "0007_stores_ledger")]

    operations = [
        migrations.RunSQL(
            *protect_record_table(table, privileges=("SELECT", "INSERT"), parents=parents)
        )
        for table, parents in TABLES.items()
    ]
    operations.extend(retain(table) for table in TABLES)
    operations.append(migrations.RunSQL(FORWARD, REVERSE))
