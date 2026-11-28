"""Keep the optional recorded section with a defect's original report."""

from django.db import migrations, models

INSTALL = """
CREATE FUNCTION defects_keep_ata_section() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'The recorded ATA section is never altered'
        USING ERRCODE = 'check_violation';
END;
$$;
CREATE TRIGGER keep_ata_section BEFORE UPDATE OF section ON defects_defect
    FOR EACH ROW WHEN (OLD.section IS DISTINCT FROM NEW.section)
    EXECUTE FUNCTION defects_keep_ata_section();
"""

REVERSE = """
DROP TRIGGER keep_ata_section ON defects_defect;
DROP FUNCTION defects_keep_ata_section();
"""


class Migration(migrations.Migration):
    dependencies = [("defects", "0004_default_deferral_from_identified")]

    operations = [
        migrations.AddField(
            model_name="defect",
            name="section",
            field=models.CharField(blank=True, max_length=2, verbose_name="ATA Section"),
        ),
        migrations.AddConstraint(
            model_name="defect",
            constraint=models.CheckConstraint(
                condition=models.Q(section="") | models.Q(section__regex=r"^[0-9]{2}$"),
                name="defect_ata_section_is_two_digits_or_blank",
            ),
        ),
        migrations.RunSQL(INSTALL, REVERSE),
    ]
