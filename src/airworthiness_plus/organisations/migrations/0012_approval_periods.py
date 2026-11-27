"""Keep gaps and earlier references when an approval is recorded as held again."""

from importlib import import_module

from django.db import migrations

OLD_ACTIVITY_RULE = import_module(
    "airworthiness_plus.organisations.migrations.0011_approval_for_activity"
).INSTALL.replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)

# A re-recording captures the previous end and reference in the immutable
# history. In the absence of an evidenced earlier restart date, the UK day
# of the re-recording is the first day of the new period.
INSTALL = """
CREATE FUNCTION organisations_approval_reference_on(approval_id uuid, on_day date)
RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT CASE
               WHEN renewal.ended_on IS NOT NULL THEN
                   CASE WHEN $2 < renewal.ended_on THEN renewal.reference END
               WHEN approval.no_longer_held_on IS NULL OR $2 < approval.no_longer_held_on THEN
                   approval.reference
           END
      FROM organisations_approval approval
      LEFT JOIN LATERAL (
          SELECT (event.before_json::jsonb ->> 'no_longer_held_on')::date AS ended_on,
                 event.before_json::jsonb ->> 'reference' AS reference
            FROM history_event event
           WHERE event.organisation_id = approval.organisation_id
             AND event.record_type = 'organisations_approval'
             AND event.record_id = approval.id
             AND 'no_longer_held_on' = ANY(event.changed)
             AND event.before_json::jsonb ->> 'no_longer_held_on' IS NOT NULL
             AND event.after_json::jsonb ->> 'no_longer_held_on' IS NULL
             AND $2 < (event.at AT TIME ZONE 'Europe/London')::date
           ORDER BY event.sequence
           LIMIT 1
      ) renewal ON true
     WHERE approval.id = $1
$$;
"""

ACTIVITY_RULE = """
CREATE OR REPLACE FUNCTION organisations_approval_for_activity(
    organisation_id uuid, on_day date, approval_type text, privilege text
) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT evidence.reference
      FROM organisations_approval approval
      JOIN organisations_organisation organisation ON organisation.id = approval.organisation_id
      CROSS JOIN LATERAL (
          SELECT organisations_approval_reference_on(approval.id, $2) AS reference
      ) evidence
     WHERE organisation.id = $1
       AND evidence.reference IS NOT NULL
       AND (approval.approval = $3
            OR (approval.approval = 'Part-CAO' AND $4 = ANY(organisation.privileges)))
     ORDER BY (approval.approval = organisation.approval_type) DESC, approval.approval
     LIMIT 1
$$;
"""

UNINSTALL = "DROP FUNCTION organisations_approval_reference_on(uuid, date);"


class Migration(migrations.Migration):
    dependencies = [("organisations", "0011_approval_for_activity")]
    operations = [
        migrations.RunSQL(INSTALL, UNINSTALL),
        migrations.RunSQL(ACTIVITY_RULE, OLD_ACTIVITY_RULE),
    ]
