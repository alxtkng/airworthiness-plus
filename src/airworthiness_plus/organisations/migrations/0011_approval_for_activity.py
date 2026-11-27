"""Find the approval covering the activity on the date recorded."""

from django.db import migrations

INSTALL = """
CREATE FUNCTION organisations_approval_for_activity(
    organisation_id uuid, on_day date, approval_type text, privilege text
) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT approval.reference
      FROM organisations_approval approval
      JOIN organisations_organisation organisation ON organisation.id = approval.organisation_id
     WHERE organisation.id = $1
       AND (approval.no_longer_held_on IS NULL OR approval.no_longer_held_on > $2)
       AND (approval.approval = $3
            OR (approval.approval = 'Part-CAO' AND $4 = ANY(organisation.privileges)))
     ORDER BY (approval.approval = organisation.approval_type) DESC, approval.approval
     LIMIT 1
$$;
"""

UNINSTALL = "DROP FUNCTION organisations_approval_for_activity(uuid, date, text, text);"


class Migration(migrations.Migration):
    dependencies = [("organisations", "0010_reweigh_threshold")]
    operations = [migrations.RunSQL(INSTALL, UNINSTALL)]
