"""The approval an organisation was set up with is changed only by the owner (REQ-200).

Independent review of 24 November 2026, finding 11: only application code
held "only Airworthiness Limited changes it". The application's role could
rewrite the reference in the record of the approval. The database now
refuses it a change to the approval an organisation was set up with or its
reference, on the organisation and on the record of the approval.
"""

from django.db import migrations

from airworthiness_plus.organisations import sql


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0008_settings_within_their_bounds"),
    ]

    operations = [
        migrations.RunSQL(sql.CREATE_SET_UP_APPROVAL_FIXED, sql.DROP_SET_UP_APPROVAL_FIXED),
    ]
