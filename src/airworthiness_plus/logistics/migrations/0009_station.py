"""Add an optional station reference without reclassifying existing Stores locations."""

from django.db import migrations, models

ADD_GUARD = """
CREATE FUNCTION logistics_keep_store_location_station() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.station IS DISTINCT FROM OLD.station THEN
        PERFORM logistics_refuse('A Stores location is withdrawn and replaced, not changed');
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER keep_store_location_station BEFORE UPDATE OF station ON logistics_storelocation
    FOR EACH ROW EXECUTE FUNCTION logistics_keep_store_location_station();
"""

REMOVE_GUARD = """
DROP TRIGGER keep_store_location_station ON logistics_storelocation;
DROP FUNCTION logistics_keep_store_location_station();
"""


class Migration(migrations.Migration):
    dependencies = [("logistics", "0008_stores_ledger_rules")]

    operations = [
        migrations.AddField(
            model_name="storelocation",
            name="station",
            field=models.CharField("Station", max_length=12, blank=True, db_default=""),
        ),
        migrations.AddConstraint(
            model_name="storelocation",
            constraint=models.CheckConstraint(
                condition=models.Q(station="") | models.Q(station__regex=r"^[A-Z0-9-]{1,12}$"),
                name="store_location_station_is_a_code",
            ),
        ),
        migrations.RunSQL(ADD_GUARD, REMOVE_GUARD),
    ]
