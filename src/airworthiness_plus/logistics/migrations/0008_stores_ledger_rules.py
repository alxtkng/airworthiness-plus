"""Put the Stores ledger under ADR-0002 and enforce once-only posting in the database.

The posting is keyed by the immutable disposition. The database copies the persisted
quantity and the latest resolution, refuses an incompatible location or an unresolved
identity, and writes the opening movement in the same statement. Every movement takes
the lot's transaction lock, so two callers cannot overspend one position (REQ-358).
"""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

PERSON = "people_person"
LOCATION = "logistics_storelocation"

TABLES = (
    protect_record_table(LOCATION),
    protect_record_table(
        "logistics_stockresolution",
        privileges=("SELECT", "INSERT"),
        parents=(
            ("disposition_id", "logistics_receivingdisposition"),
            ("location_id", LOCATION),
            ("recorded_by_id", PERSON),
        ),
    ),
    protect_record_table(
        "logistics_stockposting",
        privileges=("SELECT", "INSERT"),
        parents=(
            ("disposition_id", "logistics_receivingdisposition"),
            ("resolution_id", "logistics_stockresolution"),
            ("location_id", LOCATION),
            ("actor_id", PERSON),
        ),
    ),
    protect_record_table(
        "logistics_stockcount",
        privileges=("SELECT", "INSERT"),
        parents=(
            ("lot_id", "logistics_stockposting"),
            ("location_id", LOCATION),
            ("counter_id", PERSON),
        ),
    ),
    protect_record_table(
        "logistics_stockmovement",
        privileges=("SELECT", "INSERT"),
        parents=(
            ("lot_id", "logistics_stockposting"),
            ("from_location_id", LOCATION),
            ("to_location_id", LOCATION),
            ("count_id", "logistics_stockcount"),
            ("actor_id", PERSON),
        ),
    ),
)

INSTALL = r"""
CREATE FUNCTION logistics_refuse(message text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '%', message USING ERRCODE = 'check_violation';
END
$$;

CREATE FUNCTION logistics_lock_stock(scope text, key uuid) RETURNS void LANGUAGE sql AS $$
    SELECT pg_advisory_xact_lock(hashtextextended(scope || ':' || key::text, 0));
$$;

CREATE FUNCTION logistics_stock_balance(lot uuid, place uuid) RETURNS numeric
LANGUAGE sql STABLE SET search_path = pg_catalog, public, pg_temp AS $$
    SELECT COALESCE(SUM(CASE WHEN to_location_id = place THEN quantity ELSE 0 END), 0)
         - COALESCE(SUM(CASE WHEN from_location_id = place THEN quantity ELSE 0 END), 0)
      FROM public.logistics_stockmovement WHERE lot_id = lot;
$$;

CREATE FUNCTION logistics_stock_custody(lot uuid) RETURNS numeric
LANGUAGE sql STABLE SET search_path = pg_catalog, public, pg_temp AS $$
    SELECT COALESCE(SUM(CASE WHEN to_location_id IS NOT NULL THEN quantity ELSE 0 END), 0)
         - COALESCE(SUM(CASE WHEN from_location_id IS NOT NULL THEN quantity ELSE 0 END), 0)
      FROM public.logistics_stockmovement WHERE lot_id = lot;
$$;

CREATE FUNCTION logistics_location_accepts(place public.logistics_storelocation, item_class text)
RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN item_class IN ('Unserviceable Component', 'Unsalvageable Component')
            THEN place.kind = 'Quarantine' AND place.holds_components
        WHEN item_class = 'Serviceable Component' THEN place.holds_components
        WHEN item_class = 'Standard Part' THEN place.holds_standard_parts
        WHEN item_class = 'Material' THEN place.holds_materials
        ELSE false
    END;
$$;

-- A location keeps its name, kind and rules. Only withdrawal or return to use is recorded.
CREATE FUNCTION logistics_store_location_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.name !~ '[^[:space:]]' THEN
        PERFORM logistics_refuse('A Stores location needs a name');
    END IF;
    IF TG_OP = 'UPDATE' AND (
        NEW.name IS DISTINCT FROM OLD.name OR NEW.kind IS DISTINCT FROM OLD.kind
        OR NEW.holds_components IS DISTINCT FROM OLD.holds_components
        OR NEW.holds_standard_parts IS DISTINCT FROM OLD.holds_standard_parts
        OR NEW.holds_materials IS DISTINCT FROM OLD.holds_materials
        OR NEW.secure IS DISTINCT FROM OLD.secure
        OR NEW.storage_conditions IS DISTINCT FROM OLD.storage_conditions
    ) THEN
        PERFORM logistics_refuse('A Stores location is withdrawn and replaced, not changed');
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER store_location_rules BEFORE INSERT OR UPDATE ON logistics_storelocation
    FOR EACH ROW EXECUTE FUNCTION logistics_store_location_rules();

CREATE FUNCTION logistics_stock_resolution_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.evidence !~ '[^[:space:]]' OR NEW.authority !~ '[^[:space:]]'
       OR NEW.evidence_on > (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date
    THEN
        PERFORM logistics_refuse('A stock resolution needs dated evidence and authority');
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER stock_resolution_rules BEFORE INSERT ON logistics_stockresolution
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_resolution_rules();

CREATE FUNCTION logistics_stock_posting_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    decision public.logistics_receivingdisposition%ROWTYPE;
    arrival public.logistics_receipt%ROWTYPE;
    reading public.logistics_stockresolution%ROWTYPE;
    place public.logistics_storelocation%ROWTYPE;
    wanted text;
    identified boolean;
BEGIN
    PERFORM logistics_lock_stock('posting', NEW.disposition_id);
    SELECT * INTO decision FROM public.logistics_receivingdisposition
     WHERE id = NEW.disposition_id AND organisation_id = NEW.organisation_id;
    IF NOT FOUND OR decision.outcome NOT IN ('Accepted into Stores', 'Quarantined') THEN
        PERFORM logistics_refuse('Only an acceptance or a quarantine decision is posted');
    END IF;
    SELECT * INTO STRICT arrival FROM public.logistics_receipt WHERE id = decision.receipt_id;
    IF decision.outcome = 'Accepted into Stores' AND (
        decision.document_kind = ''
        OR NOT EXISTS (SELECT 1 FROM public.logistics_stockentry WHERE disposition_id = decision.id)
    ) THEN
        PERFORM logistics_refuse('The acceptance evidence is not substantiated for posting');
    END IF;
    SELECT * INTO reading FROM public.logistics_stockresolution
     WHERE id = NEW.resolution_id AND disposition_id = decision.id;
    IF NOT FOUND OR EXISTS (
        SELECT 1 FROM public.logistics_stockresolution later
         WHERE later.disposition_id = decision.id AND later.recorded_at > reading.recorded_at
    ) THEN
        PERFORM logistics_refuse('Post from the latest resolution of this disposition');
    END IF;
    wanted := 'Serviceable Stores';
    IF decision.outcome = 'Quarantined' THEN
        wanted := 'Quarantine';
    END IF;
    SELECT * INTO place FROM public.logistics_storelocation
     WHERE id = reading.location_id AND organisation_id = NEW.organisation_id;
    IF NOT FOUND OR NOT place.active
       OR NOT logistics_location_accepts(place, arrival.classification)
       OR place.kind <> wanted
    THEN
        PERFORM logistics_refuse('The resolved location is not compatible with this item');
    END IF;
    -- The persisted records decide. Nothing submitted with the posting overrides them.
    NEW.held := decision.outcome = 'Quarantined';
    NEW.quantity := arrival.quantity;
    NEW.physical_on := decision.disposition_on;
    NEW.unit := reading.unit;
    NEW.part_number := reading.part_number;
    NEW.serial_number := reading.serial_number;
    NEW.batch_number := reading.batch_number;
    NEW.specification := reading.specification;
    NEW.location_id := place.id;
    NEW.location_name := place.name;
    NEW.location_kind := place.kind;
    NEW.shelf_life_basis := reading.shelf_life_basis;
    NEW.shelf_life_to := reading.shelf_life_to;
    NEW.shelf_life_rule := reading.shelf_life_rule;
    IF reading.shelf_life_basis = ''
       OR (arrival.shelf_life_to IS NOT NULL AND (
            reading.shelf_life_basis <> 'Dated' OR reading.shelf_life_to <> arrival.shelf_life_to))
    THEN
        PERFORM logistics_refuse('The shelf-life basis is not resolved from the evidence');
    END IF;
    IF arrival.classification = 'Standard Part' THEN
        identified := reading.specification ~ '[^[:space:]]'
            AND (reading.batch_number ~ '[^[:space:]]' OR reading.serial_number ~ '[^[:space:]]');
    ELSIF arrival.classification = 'Material' THEN
        identified := reading.specification ~ '[^[:space:]]'
            AND reading.batch_number ~ '[^[:space:]]';
    ELSE
        identified := reading.part_number ~ '[^[:space:]]'
            AND (reading.serial_number ~ '[^[:space:]]' OR reading.batch_number ~ '[^[:space:]]');
    END IF;
    IF NOT identified THEN
        PERFORM logistics_refuse('The traceable identity is not resolved for this class');
    END IF;
    IF reading.serial_number ~ '[^[:space:]]' AND EXISTS (
        SELECT 1 FROM public.logistics_stockposting other
         WHERE other.organisation_id = NEW.organisation_id
           AND lower(other.part_number) = lower(reading.part_number)
           AND lower(other.serial_number) = lower(reading.serial_number)
           AND logistics_stock_custody(other.id) > 0
    ) THEN
        PERFORM logistics_refuse('This serial already has a current custody position');
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER stock_posting_rules BEFORE INSERT ON logistics_stockposting
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_posting_rules();

CREATE FUNCTION logistics_stock_posting_intake() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO public.logistics_stockmovement (
        id, organisation_id, lot_id, kind, from_location_id, to_location_id, quantity,
        moved_on, count_id, actor_id, actor_name, authority, evidence, recorded_at
    ) VALUES (
        gen_random_uuid(), NEW.organisation_id, NEW.id, 'Intake', NULL, NEW.location_id,
        NEW.quantity, NEW.physical_on, NULL, NEW.actor_id, NEW.actor_name, NEW.authority,
        'Opening intake from the Goods In disposition', NEW.recorded_at
    );
    RETURN NULL;
END
$$;
CREATE TRIGGER stock_posting_intake AFTER INSERT ON logistics_stockposting
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_posting_intake();

CREATE FUNCTION logistics_stock_count_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    lot public.logistics_stockposting%ROWTYPE;
BEGIN
    PERFORM logistics_lock_stock('lot', NEW.lot_id);
    SELECT * INTO lot FROM public.logistics_stockposting
     WHERE id = NEW.lot_id AND organisation_id = NEW.organisation_id;
    IF NOT FOUND OR NEW.evidence !~ '[^[:space:]]'
       OR NEW.counted_on > (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date
       OR NEW.counted_on < lot.physical_on
       OR (lot.unit = 'Each' AND NEW.counted_quantity <> trunc(NEW.counted_quantity))
    THEN
        PERFORM logistics_refuse('A count needs a dated, evidenced quantity in the lot unit');
    END IF;
    -- The ledger quantity is read by the database at the moment of the count.
    NEW.ledger_quantity := logistics_stock_balance(NEW.lot_id, NEW.location_id);
    RETURN NEW;
END
$$;
CREATE TRIGGER stock_count_rules BEFORE INSERT ON logistics_stockcount
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_count_rules();

CREATE FUNCTION logistics_stock_movement_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    lot public.logistics_stockposting%ROWTYPE;
    item_class text;
    tally public.logistics_stockcount%ROWTYPE;
    destination public.logistics_storelocation%ROWTYPE;
    difference numeric;
BEGIN
    PERFORM logistics_lock_stock('lot', NEW.lot_id);
    SELECT * INTO lot FROM public.logistics_stockposting
     WHERE id = NEW.lot_id AND organisation_id = NEW.organisation_id;
    IF NOT FOUND THEN
        PERFORM logistics_refuse('A movement needs a posted lot of this organisation');
    END IF;
    SELECT receipt.classification INTO STRICT item_class
      FROM public.logistics_receivingdisposition decision
      JOIN public.logistics_receipt receipt ON receipt.id = decision.receipt_id
     WHERE decision.id = lot.disposition_id;
    IF NEW.quantity <= 0
       OR (lot.unit = 'Each' AND NEW.quantity <> trunc(NEW.quantity))
       OR (lot.serial_number <> '' AND NEW.quantity <> 1)
       OR NEW.moved_on < lot.physical_on
       OR NEW.moved_on > (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date
    THEN
        PERFORM logistics_refuse('The movement quantity or date does not suit the lot');
    END IF;
    IF NEW.kind = 'Intake' THEN
        IF EXISTS (SELECT 1 FROM public.logistics_stockmovement WHERE lot_id = lot.id)
           OR NEW.to_location_id IS DISTINCT FROM lot.location_id
           OR NEW.quantity <> lot.quantity
        THEN
            PERFORM logistics_refuse('Only the posting opens a lot');
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.kind = 'Adjustment' THEN
        SELECT * INTO tally FROM public.logistics_stockcount
         WHERE id = NEW.count_id AND lot_id = lot.id;
        difference := tally.counted_quantity - tally.ledger_quantity;
        IF NOT FOUND
           OR logistics_stock_balance(lot.id, tally.location_id) <> tally.ledger_quantity
           OR difference = 0
           OR NEW.moved_on < tally.counted_on
           OR (difference < 0 AND (NEW.from_location_id IS DISTINCT FROM tally.location_id
                                   OR NEW.quantity <> -difference))
           OR (difference > 0 AND (NEW.to_location_id IS DISTINCT FROM tally.location_id
                                   OR NEW.quantity <> difference))
        THEN
            PERFORM logistics_refuse('An adjustment must apply the variance of a current count');
        END IF;
    END IF;
    IF NEW.from_location_id IS NOT NULL
       AND logistics_stock_balance(lot.id, NEW.from_location_id) < NEW.quantity
    THEN
        PERFORM logistics_refuse('The source location does not hold that quantity');
    END IF;
    IF NEW.kind = 'Transfer' THEN
        SELECT * INTO destination FROM public.logistics_storelocation
         WHERE id = NEW.to_location_id AND organisation_id = NEW.organisation_id;
        IF NOT FOUND OR NOT destination.active
           OR NOT logistics_location_accepts(destination, item_class)
           OR (destination.kind = 'Serviceable Stores' AND lot.held)
        THEN
            PERFORM logistics_refuse('The destination is not compatible with this lot');
        END IF;
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER stock_movement_rules BEFORE INSERT ON logistics_stockmovement
    FOR EACH ROW EXECUTE FUNCTION logistics_stock_movement_rules();

CREATE TRIGGER history_refuse_update BEFORE UPDATE ON logistics_stockresolution
    FOR EACH ROW EXECUTE FUNCTION history_refuse();
CREATE TRIGGER history_refuse_update BEFORE UPDATE ON logistics_stockposting
    FOR EACH ROW EXECUTE FUNCTION history_refuse();
CREATE TRIGGER history_refuse_update BEFORE UPDATE ON logistics_stockcount
    FOR EACH ROW EXECUTE FUNCTION history_refuse();
CREATE TRIGGER history_refuse_update BEFORE UPDATE ON logistics_stockmovement
    FOR EACH ROW EXECUTE FUNCTION history_refuse();
"""

REMOVE = """
DROP TRIGGER history_refuse_update ON logistics_stockmovement;
DROP TRIGGER history_refuse_update ON logistics_stockcount;
DROP TRIGGER history_refuse_update ON logistics_stockposting;
DROP TRIGGER history_refuse_update ON logistics_stockresolution;
DROP TRIGGER stock_movement_rules ON logistics_stockmovement;
DROP FUNCTION logistics_stock_movement_rules();
DROP TRIGGER stock_count_rules ON logistics_stockcount;
DROP FUNCTION logistics_stock_count_rules();
DROP TRIGGER stock_posting_intake ON logistics_stockposting;
DROP FUNCTION logistics_stock_posting_intake();
DROP TRIGGER stock_posting_rules ON logistics_stockposting;
DROP FUNCTION logistics_stock_posting_rules();
DROP TRIGGER stock_resolution_rules ON logistics_stockresolution;
DROP FUNCTION logistics_stock_resolution_rules();
DROP TRIGGER store_location_rules ON logistics_storelocation;
DROP FUNCTION logistics_store_location_rules();
DROP FUNCTION logistics_location_accepts(public.logistics_storelocation, text);
DROP FUNCTION logistics_stock_custody(uuid);
DROP FUNCTION logistics_stock_balance(uuid, uuid);
DROP FUNCTION logistics_lock_stock(text, uuid);
DROP FUNCTION logistics_refuse(text);
"""


class Migration(migrations.Migration):
    dependencies = [
        ("logistics", "0007_stores_ledger"),
        ("people", "0001_initial"),
    ]

    operations = [
        *(migrations.RunSQL(forward, backward) for forward, backward in TABLES),
        migrations.RunSQL(INSTALL, REMOVE),
    ]
