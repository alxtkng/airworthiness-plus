"""Keep receipts and inspection evidence in the tenant, under dated record rules."""

from django.db import migrations

from airworthiness_plus.history.sql import protect_record_table

INSTALL = """
CREATE FUNCTION logistics_receipt_rules() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.item !~ '[^[:space:]]' OR NEW.source !~ '[^[:space:]]'
       OR NEW.item_reference !~ '[^[:space:]]' OR NEW.delivery_reference !~ '[^[:space:]]'
       OR NEW.received_on > (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date
    THEN
        RAISE EXCEPTION 'A receipt needs item, traceability and a valid receipt date'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE FUNCTION logistics_receiving_check_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    arrival logistics_receipt%ROWTYPE;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.receipt_id::text, 0));
    SELECT * INTO arrival FROM logistics_receipt
     WHERE id = NEW.receipt_id AND organisation_id = NEW.organisation_id;
    IF NOT FOUND OR NEW.checked_on < arrival.received_on
       OR NEW.checked_on > (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date
       OR NEW.evidence !~ '[^[:space:]]'
       OR (NEW.kind = 'Shelf Life' AND NEW.outcome = 'Not Applicable'
           AND arrival.shelf_life_to IS NOT NULL)
    THEN
        RAISE EXCEPTION 'A receiving check needs dated, applicable evidence for its receipt'
            USING ERRCODE = 'check_violation';
    END IF;
    IF EXISTS (SELECT 1 FROM logistics_receivingdisposition WHERE receipt_id = arrival.id)
    THEN
        RAISE EXCEPTION 'Receiving checks are closed by the final disposition'
            USING ERRCODE = 'check_violation';
    END IF;
    NEW.recorded_at := clock_timestamp();
    RETURN NEW;
END
$$;

CREATE FUNCTION logistics_receiving_disposition_rules() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    arrival logistics_receipt%ROWTYPE;
    acceptable_count integer;
    suspected boolean;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.receipt_id::text, 0));
    SELECT * INTO arrival FROM logistics_receipt
     WHERE id = NEW.receipt_id AND organisation_id = NEW.organisation_id;
    IF NOT FOUND OR NEW.inspected_on < arrival.received_on
       OR NEW.disposition_on > (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date
       OR EXISTS (
           SELECT 1 FROM logistics_receivingcheck observed
            WHERE observed.receipt_id = arrival.id AND observed.checked_on > NEW.inspected_on
       )
       OR NEW.destination !~ '[^[:space:]]' OR NEW.evidence !~ '[^[:space:]]'
       OR NEW.inspector_authority !~ '[^[:space:]]'
    THEN
        RAISE EXCEPTION 'A disposition needs chronological inspection and movement evidence'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT official.full_name INTO NEW.inspector_name FROM people_person official
     WHERE official.id = NEW.inspector_id AND official.organisation_id = NEW.organisation_id
       AND (official.joined_on IS NULL OR official.joined_on <= NEW.inspected_on)
       AND (official.left_on IS NULL OR official.left_on >= NEW.inspected_on);
    IF NEW.inspector_name IS NULL THEN
        RAISE EXCEPTION 'The inspector must belong to this organisation on the inspection date'
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT organisations_approval_reference_on(term.id, NEW.inspected_on)
      INTO NEW.approval_reference
      FROM organisations_approval term
      JOIN organisations_organisation organisation ON organisation.id = term.organisation_id
     WHERE term.id = NEW.approval_id AND term.organisation_id = NEW.organisation_id
       AND (term.approval = 'Part-145'
         OR (term.approval = 'Part-CAO' AND 'Maintenance' = ANY(organisation.privileges)));
    IF NEW.approval_reference IS NULL THEN
        RAISE EXCEPTION 'No maintenance approval covers the inspection date'
            USING ERRCODE = 'check_violation';
    END IF;

    WITH latest AS (
        SELECT DISTINCT ON (observed.kind) observed.kind, observed.outcome
          FROM logistics_receivingcheck observed
         WHERE observed.receipt_id = arrival.id
         ORDER BY observed.kind, observed.checked_on DESC, observed.recorded_at DESC, observed.id DESC
    )
    SELECT count(*) FILTER (WHERE outcome IN ('Pass', 'Not Applicable')),
           coalesce(bool_or(kind = 'Suspected Unapproved Part Checks' AND outcome = 'Fail'), false)
      INTO acceptable_count, suspected FROM latest;
    IF suspected AND NEW.outcome <> 'Quarantined' THEN
        RAISE EXCEPTION 'A suspected unapproved part must go to quarantine'
            USING ERRCODE = 'check_violation';
    END IF;
    IF arrival.classification IN ('Unserviceable Component', 'Unsalvageable Component')
       AND NEW.outcome <> 'Quarantined' THEN
        RAISE EXCEPTION 'An unserviceable or unsalvageable item must go to quarantine'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.outcome = 'Accepted into Stores' AND (
        acceptable_count <> 6
        OR NEW.disposition_on > arrival.shelf_life_to
    ) THEN
        RAISE EXCEPTION 'The receiving evidence does not allow acceptance into stores'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER receipt_rules BEFORE INSERT ON logistics_receipt
    FOR EACH ROW EXECUTE FUNCTION logistics_receipt_rules();
CREATE TRIGGER receiving_check_rules BEFORE INSERT ON logistics_receivingcheck
    FOR EACH ROW EXECUTE FUNCTION logistics_receiving_check_rules();
CREATE TRIGGER receiving_disposition_rules BEFORE INSERT ON logistics_receivingdisposition
    FOR EACH ROW EXECUTE FUNCTION logistics_receiving_disposition_rules();
"""

UNINSTALL = """
DROP TRIGGER receiving_disposition_rules ON logistics_receivingdisposition;
DROP TRIGGER receiving_check_rules ON logistics_receivingcheck;
DROP TRIGGER receipt_rules ON logistics_receipt;
DROP FUNCTION logistics_receiving_disposition_rules();
DROP FUNCTION logistics_receiving_check_rules();
DROP FUNCTION logistics_receipt_rules();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("logistics", "0003_receiving_records"),
        ("organisations", "0012_approval_periods"),
    ]

    operations = [
        migrations.RunSQL(
            *protect_record_table("logistics_receipt", privileges=("SELECT", "INSERT"))
        ),
        migrations.RunSQL(
            *protect_record_table(
                "logistics_receivingcheck",
                privileges=("SELECT", "INSERT"),
                parents=(("receipt_id", "logistics_receipt"),),
            )
        ),
        migrations.RunSQL(
            *protect_record_table(
                "logistics_receivingdisposition",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("receipt_id", "logistics_receipt"),
                    ("approval_id", "organisations_approval"),
                    ("inspector_id", "people_person"),
                ),
            )
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
