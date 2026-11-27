"""The sources checked for new directives (REQ-288)."""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("directives", "0001_initial"),
        ("organisations", "0010_reweigh_threshold"),
    ]

    operations = [
        migrations.CreateModel(
            name="Source",
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
                ("name", models.CharField(max_length=200, verbose_name="Source")),
                ("covers", models.CharField(max_length=300, verbose_name="Covers")),
                (
                    "note",
                    models.CharField(blank=True, max_length=200, verbose_name="Note"),
                ),
                (
                    "last_checked_on",
                    models.DateField(blank=True, null=True, verbose_name="Last Checked"),
                ),
                (
                    "next_check_on",
                    models.DateField(blank=True, null=True, verbose_name="Next Check"),
                ),
                (
                    "next_check_note",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="Next Check in Words"
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
                "ordering": ["name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("organisation", "name"),
                        name="directive_source_recorded_once",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("name", ""), _negated=True),
                            models.Q(("covers", ""), _negated=True),
                        ),
                        name="directive_source_has_a_name_and_what_it_covers",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("last_checked_on__isnull", True),
                                ("next_check_note", ""),
                                ("next_check_on__isnull", True),
                            ),
                            models.Q(
                                ("last_checked_on__isnull", False),
                                models.Q(
                                    models.Q(
                                        ("next_check_note", ""),
                                        (
                                            "next_check_on__gte",
                                            models.F("last_checked_on"),
                                        ),
                                        ("next_check_on__isnull", False),
                                    ),
                                    models.Q(
                                        ("next_check_on__isnull", True),
                                        models.Q(("next_check_note", ""), _negated=True),
                                    ),
                                    _connector="OR",
                                ),
                            ),
                            _connector="OR",
                        ),
                        name="directive_source_check_has_its_next_check",
                    ),
                ],
            },
        ),
        migrations.RunSQL(*sql.protect_record_table("directives_source")),
    ]
