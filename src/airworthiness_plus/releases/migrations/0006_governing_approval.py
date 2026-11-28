"""Retain the selected approval on new organisation releases."""

from django.db import migrations, models

from airworthiness_plus.history.sql import same_organisation

FORWARD = """
CREATE FUNCTION release_governing_approval() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog, public, pg_temp AS $$
DECLARE
    ref text;
BEGIN
    IF NEW.governing_approval_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT organisations_approval_reference_on(approval.id, NEW.issued_on)
      INTO ref
      FROM organisations_approval approval
      JOIN organisations_organisation organisation ON organisation.id=approval.organisation_id
      WHERE approval.id=NEW.governing_approval_id
        AND approval.organisation_id=NEW.organisation_id
        AND (approval.approval='Part-145'
            OR (approval.approval='Part-CAO' AND 'Maintenance'=ANY(organisation.privileges)));
    IF NEW.kind <> 'Organisation Certifying Staff' OR ref IS NULL THEN
        RAISE EXCEPTION 'The selected maintenance approval must cover the release'
            USING ERRCODE='23514';
    END IF;
    NEW.approval_reference := ref;
    RETURN NEW;
END $$;

-- The existing release_rules trigger snapshots the earlier approval rule.
-- For verified prospective releases, apply the explicit selection afterwards.
CREATE TRIGGER release_selected_approval BEFORE INSERT ON releases_release
FOR EACH ROW EXECUTE FUNCTION release_governing_approval();
"""

REVERSE = """
DROP TRIGGER release_selected_approval ON releases_release;
DROP FUNCTION release_governing_approval();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("releases", "0005_historical_release_evidence"),
        ("organisations", "0012_approval_periods"),
    ]

    operations = [
        migrations.AddField(
            model_name="release",
            name="governing_approval",
            field=models.ForeignKey(
                null=True,
                on_delete=models.PROTECT,
                related_name="+",
                to="organisations.approval",
            ),
        ),
        migrations.RunSQL(
            *same_organisation(
                "releases_release", "governing_approval_id", "organisations_approval"
            ),
        ),
        migrations.RunSQL(FORWARD, REVERSE),
    ]
