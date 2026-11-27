"""Every sign-in has a person after every change, not only when it is made (REQ-204).

Independent review of 24 November 2026, finding 11: as the application's
role, a person's sign-in could be taken off the person, and the sign-in was
left with no person. The database now refuses, whoever asks.
"""

from django.db import migrations

from airworthiness_plus.people import sql


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql.CREATE_SIGN_IN_KEEPS_ITS_PERSON, sql.DROP_SIGN_IN_KEEPS_ITS_PERSON),
    ]
