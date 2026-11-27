"""Keep the aircraft identity and review authorisation shown at issue.

Existing certificates take the values available at upgrade. The history
records the backfill. Earlier values cannot be inferred from the certificate.
"""

from django.db import migrations, models

from airworthiness_plus.history.sql import for_each_organisation

BACKFILL = for_each_organisation("""
    UPDATE reviews_certificate certificate
       SET aircraft_registration = aircraft.registration,
           aircraft_type_rating = aircraft.type_rating,
           aircraft_manufacturer = aircraft.manufacturer,
           aircraft_designation = aircraft.designation,
           aircraft_serial_number = aircraft.serial_number,
           review_staff_authorisation = COALESCE(
               (SELECT staff.authorisation_reference FROM reviews_reviewstaff staff
                 WHERE staff.id = certificate.issued_by_id), '')
      FROM aircraft_aircraft aircraft
     WHERE certificate.organisation_id = organisation
       AND aircraft.id = certificate.aircraft_id;
""")

INSTALL = """
CREATE FUNCTION reviews_certificate_identity() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT registration, type_rating, manufacturer, designation, serial_number
          INTO NEW.aircraft_registration, NEW.aircraft_type_rating, NEW.aircraft_manufacturer,
               NEW.aircraft_designation, NEW.aircraft_serial_number
          FROM aircraft_aircraft WHERE id = NEW.aircraft_id;
        NEW.review_staff_authorisation := COALESCE(
            (SELECT authorisation_reference FROM reviews_reviewstaff WHERE id = NEW.issued_by_id),
            '');
    ELSIF ROW(NEW.aircraft_registration, NEW.aircraft_type_rating, NEW.aircraft_manufacturer,
              NEW.aircraft_designation, NEW.aircraft_serial_number, NEW.review_staff_authorisation)
       IS DISTINCT FROM
          ROW(OLD.aircraft_registration, OLD.aircraft_type_rating, OLD.aircraft_manufacturer,
              OLD.aircraft_designation, OLD.aircraft_serial_number, OLD.review_staff_authorisation)
    THEN
        RAISE EXCEPTION 'What a certificate says is never altered once recorded'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER certificate_identity BEFORE INSERT OR UPDATE ON reviews_certificate
    FOR EACH ROW EXECUTE FUNCTION reviews_certificate_identity();
"""

UNINSTALL = """
DROP TRIGGER certificate_identity ON reviews_certificate;
DROP FUNCTION reviews_certificate_identity();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0007_keep_what_each_showed"),
    ]

    operations = [
        migrations.AddField(
            model_name="certificate",
            name="aircraft_designation",
            field=models.CharField(
                blank=True, max_length=100, verbose_name="Manufacturer's Designation"
            ),
        ),
        migrations.AddField(
            model_name="certificate",
            name="aircraft_manufacturer",
            field=models.CharField(
                blank=True, max_length=100, verbose_name="Aircraft Manufacturer"
            ),
        ),
        migrations.AddField(
            model_name="certificate",
            name="aircraft_registration",
            field=models.CharField(blank=True, max_length=10, verbose_name="Aircraft Registration"),
        ),
        migrations.AddField(
            model_name="certificate",
            name="aircraft_serial_number",
            field=models.CharField(
                blank=True, max_length=60, verbose_name="Aircraft Serial Number"
            ),
        ),
        migrations.AddField(
            model_name="certificate",
            name="aircraft_type_rating",
            field=models.CharField(blank=True, max_length=200, verbose_name="Aircraft Type Rating"),
        ),
        migrations.AddField(
            model_name="certificate",
            name="review_staff_authorisation",
            field=models.CharField(
                blank=True, max_length=60, verbose_name="Authorisation Reference"
            ),
        ),
        migrations.RunSQL(BACKFILL, migrations.RunSQL.noop),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
