"""Retain signed historical evidence from a period with a grounding defect."""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql

INSTALL = """
CREATE FUNCTION historical_release_period() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.issued_on >= (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/London')::date
        OR NOT EXISTS (
            SELECT 1 FROM programme_workdone AS work
            JOIN defects_defect AS defect ON defect.aircraft_id = work.aircraft_id
            WHERE work.id = NEW.work_id AND defect.id = NEW.grounding_defect_id
                AND work.dated <= NEW.issued_on
                AND defect.decision = 'Not Deferrable'
                AND defect.found_on <= NEW.issued_on
                AND (defect.closed_on IS NULL OR defect.closed_on > NEW.issued_on)
        )
    THEN
        RAISE EXCEPTION 'Signed historical evidence must cover completed work during a grounding period'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER historical_release_period BEFORE INSERT ON releases_historicalreleaseevidence
    FOR EACH ROW EXECUTE FUNCTION historical_release_period();
"""

UNINSTALL = """
DROP TRIGGER historical_release_period ON releases_historicalreleaseevidence;
DROP FUNCTION historical_release_period();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("defects", "0004_default_deferral_from_identified"),
        ("organisations", "0011_approval_for_activity"),
        ("programme", "0004_work_performed_by"),
        ("releases", "0004_certification_evidence"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalReleaseEvidence",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "reference",
                    models.CharField(max_length=100, verbose_name="Signed Release Reference"),
                ),
                (
                    "issuer_name",
                    models.CharField(max_length=200, verbose_name="Issuer Named in the Source"),
                ),
                ("issued_on", models.DateField(verbose_name="Date on the Signed Release")),
                (
                    "source",
                    models.CharField(max_length=200, verbose_name="Signed Evidence Reference"),
                ),
                (
                    "grounding_defect",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="defects.defect",
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organisations.organisation",
                    ),
                ),
                (
                    "work",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="historical_releases",
                        to="programme.workdone",
                    ),
                ),
            ],
            options={
                "ordering": ["-issued_on", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("work", "reference", "issued_on"),
                        name="historical_release_once_per_source",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("reference", ""), _negated=True),
                            models.Q(("issuer_name", ""), _negated=True),
                            models.Q(("source", ""), _negated=True),
                        ),
                        name="historical_release_has_evidence",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "releases_historicalreleaseevidence",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("work_id", "programme_workdone"),
                    ("grounding_defect_id", "defects_defect"),
                ),
            )
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
