"""A record that a part of the sample has been added to an organisation (REQ-218).

Independent review of 24 November 2026, finding 3: the test site's top-up
found people by name, so a person renamed was added again at every start.
What the top-up adds it now adds once, and this record says that it has.
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organisations", "0008_settings_within_their_bounds"),
        ("history", "0004_hash_algorithm"),
    ]

    operations = [
        migrations.CreateModel(
            name="Added",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "part",
                    models.CharField(
                        choices=[("People", "People")],
                        max_length=40,
                        verbose_name="Part of the Sample",
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
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organisation", "part"), name="sample_part_added_once"
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("part__in", ["People"])),
                        name="sample_part_is_known",
                    ),
                ],
            },
        ),
        # Added and never changed.
        migrations.RunSQL(
            *sql.protect_record_table("sample_added", privileges=("SELECT", "INSERT"))
        ),
    ]
