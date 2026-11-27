from django.db import migrations, models

INSTALL = """
CREATE FUNCTION reviews_keep_confirmed_authorisation_scope() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.confirmed_authorisation_scope IS DISTINCT FROM OLD.confirmed_authorisation_scope THEN
        RAISE EXCEPTION 'The authorisation scope confirmed at the start stays in the review record'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER review_keeps_confirmed_authorisation_scope
    BEFORE UPDATE ON reviews_review FOR EACH ROW
    EXECUTE FUNCTION reviews_keep_confirmed_authorisation_scope();
"""

UNINSTALL = """
DROP TRIGGER review_keeps_confirmed_authorisation_scope ON reviews_review;
DROP FUNCTION reviews_keep_confirmed_authorisation_scope();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0009_reviewstaff_authorisation_scope_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="confirmed_authorisation_scope",
            field=models.CharField(
                blank=True, max_length=400, verbose_name="Confirmed Authorisation Scope"
            ),
        ),
        migrations.RunSQL(INSTALL, UNINSTALL),
    ]
