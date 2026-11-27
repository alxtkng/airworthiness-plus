"""Keep the evidence fields of upgraded releases and defects in their exports."""

from django.db import migrations

from airworthiness_plus.history.sql import for_each_organisation

# Export records come from the last event, while adding columns only changes the
# live row. Append an event without rewriting history or updating a signed row.
# The temporary trigger uses the normal database history chain and actor.
# Hold record writes so a defect closure cannot overtake the migration snapshot.
PREPARE = """
LOCK TABLE organisations_organisation IN ACCESS EXCLUSIVE MODE;
LOCK TABLE releases_release, defects_defect IN SHARE ROW EXCLUSIVE MODE;

CREATE TABLE certification_export_backfill (
    organisation_id uuid,
    record_type text,
    record_id uuid,
    snapshot text
);
REVOKE ALL ON certification_export_backfill FROM PUBLIC;

CREATE FUNCTION record_certification_export_backfill() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO history_event (
        organisation_id, record_type, record_id, action, changed, before_json, after_json
    )
    VALUES (
        NEW.organisation_id, NEW.record_type, NEW.record_id, 'Changed',
        ARRAY['legacy_evidence', 'maintenance_authorisation_id', 'scope_confirmed'],
        NEW.snapshot,
        (NEW.snapshot::jsonb || jsonb_build_object(
            'legacy_evidence', '', 'maintenance_authorisation_id', NULL, 'scope_confirmed', false
        ))::text
    );
    RETURN NULL;
END
$$;

CREATE TRIGGER record_certification_export_backfill
    AFTER INSERT ON certification_export_backfill
    FOR EACH ROW EXECUTE FUNCTION record_certification_export_backfill();
"""

BACKFILL = for_each_organisation("""
    INSERT INTO certification_export_backfill
        (organisation_id, record_type, record_id, snapshot)
    SELECT organisation, record_type, record_id, after_json
      FROM (
          SELECT DISTINCT ON (record_type, record_id) record_type, record_id, after_json
            FROM history_event
           WHERE organisation_id = organisation
             AND record_type IN ('releases_release', 'defects_defect')
           ORDER BY record_type, record_id, sequence DESC
      ) AS latest
     WHERE NOT (after_json::jsonb ? 'legacy_evidence');
""")

CLEANUP = """
DROP TABLE certification_export_backfill;
DROP FUNCTION record_certification_export_backfill();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("releases", "0004_certification_evidence"),
        ("defects", "0003_certification_evidence"),
    ]

    operations = [migrations.RunSQL([PREPARE, BACKFILL, CLEANUP], migrations.RunSQL.noop)]
