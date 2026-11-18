"""Put the organisation and user tables under the record rules."""

from django.db import migrations

from airworthiness_plus.history import sql

# An organisation is scoped by its own identifier. The application cannot
# create one: that is done when an organisation is set up (REQ-004).
ORGANISATION = sql.protect_record_table(
    "organisations_organisation", organisation_column="id", privileges=("SELECT", "UPDATE")
)

# The password is kept out of the history; that it changed is recorded.
USER = sql.protect_record_table("accounts_user", omitted=("password",))


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0001_initial"),
        ("organisations", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(*ORGANISATION),
        migrations.RunSQL(*USER),
    ]
