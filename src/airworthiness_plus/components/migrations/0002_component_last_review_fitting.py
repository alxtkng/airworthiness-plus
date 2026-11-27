"""Protect component review provenance and accrued usage when refitting."""

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history.sql import same_organisation

CREATE_REVIEW_FITTING_RULES = """
CREATE FUNCTION components_review_fitting_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.last_review_fitting_id IS NOT NULL AND (
        NEW.basis <> 'On Condition' OR NOT EXISTS (
            SELECT 1 FROM components_installation
            WHERE id = NEW.last_review_fitting_id AND component_id = NEW.id
        )
    ) THEN
        RAISE EXCEPTION 'A review uses a fitting of the same on-condition component'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER review_fitting_rules BEFORE INSERT OR UPDATE ON components_component
    FOR EACH ROW EXECUTE FUNCTION components_review_fitting_rules();

CREATE FUNCTION components_fitting_usage_rules() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    prior components_installation%ROWTYPE;
BEGIN
    SELECT * INTO prior
    FROM components_installation
    WHERE component_id = NEW.component_id AND removed_on IS NOT NULL
    ORDER BY fitted_on DESC, removed_on DESC, id DESC
    LIMIT 1;
    IF FOUND AND (
        NEW.hours_at_fitting < prior.hours_at_fitting
            + prior.airframe_hours_removed - prior.airframe_hours_fitted
        OR NEW.cycles_at_fitting < prior.cycles_at_fitting
            + prior.airframe_cycles_removed - prior.airframe_cycles_fitted
    ) AND NOT (
        NEW.life_from IS NOT NULL AND NEW.life_from >= prior.removed_on
        AND NEW.life_from IS DISTINCT FROM prior.life_from
    ) THEN
        RAISE EXCEPTION 'Earlier accumulated hours or cycles need a new or overhaul date'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER fitting_usage_rules BEFORE INSERT ON components_installation
    FOR EACH ROW EXECUTE FUNCTION components_fitting_usage_rules();
"""

DROP_REVIEW_FITTING_RULES = """
DROP TRIGGER fitting_usage_rules ON components_installation;
DROP FUNCTION components_fitting_usage_rules();
DROP TRIGGER review_fitting_rules ON components_component;
DROP FUNCTION components_review_fitting_rules();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("components", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="component",
            name="last_review_fitting",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="components.installation",
            ),
        ),
        migrations.RunSQL(
            *same_organisation(
                "components_component", "last_review_fitting_id", "components_installation"
            )
        ),
        migrations.RunSQL(CREATE_REVIEW_FITTING_RULES, DROP_REVIEW_FITTING_RULES),
    ]
