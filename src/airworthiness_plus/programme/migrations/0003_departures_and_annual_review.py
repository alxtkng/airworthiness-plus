"""Departures from the manufacturer's instructions, and the annual review point by point (REQ-284 to REQ-287)."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from airworthiness_plus.history import sql
from airworthiness_plus.programme import sql as own_sql


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("organisations", "0010_reweigh_threshold"),
        ("programme", "0002_once_and_directive_kind"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AnnualReview",
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
                ("opened_on", models.DateField(verbose_name="Opened")),
                ("results_note", models.CharField(blank=True, max_length=300)),
                ("results_done", models.BooleanField(default=False)),
                (
                    "airworthiness_review_note",
                    models.CharField(blank=True, max_length=300),
                ),
                ("airworthiness_review_done", models.BooleanField(default=False)),
                ("revisions_note", models.CharField(blank=True, max_length=300)),
                ("revisions_done", models.BooleanField(default=False)),
                ("configuration_note", models.CharField(blank=True, max_length=300)),
                ("configuration_done", models.BooleanField(default=False)),
                ("pilot_owners_note", models.CharField(blank=True, max_length=300)),
                ("pilot_owners_done", models.BooleanField(default=False)),
                ("mandatory_note", models.CharField(blank=True, max_length=300)),
                ("mandatory_done", models.BooleanField(default=False)),
                (
                    "completed_on",
                    models.DateField(blank=True, null=True, verbose_name="Completed"),
                ),
                ("completed_by_name", models.CharField(blank=True, max_length=200)),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
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
                (
                    "programme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="annual_reviews",
                        to="programme.programme",
                    ),
                ),
            ],
            options={
                "ordering": ["opened_on", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("completed_on__isnull", True)),
                        fields=("programme",),
                        name="annual_review_one_in_progress_for_a_programme",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("results_done", False),
                                models.Q(("results_note", ""), _negated=True),
                                _connector="OR",
                            ),
                            models.Q(
                                ("airworthiness_review_done", False),
                                models.Q(("airworthiness_review_note", ""), _negated=True),
                                _connector="OR",
                            ),
                            models.Q(
                                ("revisions_done", False),
                                models.Q(("revisions_note", ""), _negated=True),
                                _connector="OR",
                            ),
                            models.Q(
                                ("configuration_done", False),
                                models.Q(("configuration_note", ""), _negated=True),
                                _connector="OR",
                            ),
                            models.Q(
                                ("pilot_owners_done", False),
                                models.Q(("pilot_owners_note", ""), _negated=True),
                                _connector="OR",
                            ),
                            models.Q(
                                ("mandatory_done", False),
                                models.Q(("mandatory_note", ""), _negated=True),
                                _connector="OR",
                            ),
                        ),
                        name="annual_review_point_complete_says_what_was_found",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("completed_by__isnull", True),
                                ("completed_on__isnull", True),
                            ),
                            models.Q(
                                ("airworthiness_review_done", True),
                                ("completed_by__isnull", False),
                                ("completed_on__gte", models.F("opened_on")),
                                ("completed_on__isnull", False),
                                ("configuration_done", True),
                                ("mandatory_done", True),
                                ("pilot_owners_done", True),
                                ("results_done", True),
                                ("revisions_done", True),
                            ),
                            _connector="OR",
                        ),
                        name="annual_review_completed_with_every_point_complete",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Departure",
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
                ("task", models.CharField(max_length=200, verbose_name="Task")),
                (
                    "manufacturer",
                    models.CharField(max_length=200, verbose_name="Manufacturer"),
                ),
                (
                    "programme_says",
                    models.CharField(max_length=200, verbose_name="Programme"),
                ),
                (
                    "compensating_measures",
                    models.CharField(max_length=300, verbose_name="Compensating Measures"),
                ),
                (
                    "justification",
                    models.CharField(max_length=300, verbose_name="Justification"),
                ),
                ("recorded_on", models.DateField(verbose_name="Recorded")),
                (
                    "owner_copy_sent_on",
                    models.DateField(blank=True, null=True, verbose_name="Owner Copy Sent"),
                ),
                (
                    "withdrawn_on",
                    models.DateField(blank=True, null=True, verbose_name="Withdrawn"),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organisations.organisation",
                    ),
                ),
                (
                    "programme",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="departures",
                        to="programme.programme",
                    ),
                ),
            ],
            options={
                "ordering": ["recorded_on", "task", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("task", ""), _negated=True),
                            models.Q(("manufacturer", ""), _negated=True),
                            models.Q(("programme_says", ""), _negated=True),
                            models.Q(("compensating_measures", ""), _negated=True),
                            models.Q(("justification", ""), _negated=True),
                        ),
                        name="departure_says_what_it_departs_from_and_why",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("owner_copy_sent_on__isnull", True),
                                ("owner_copy_sent_on__gte", models.F("recorded_on")),
                                _connector="OR",
                            ),
                            models.Q(
                                ("withdrawn_on__isnull", True),
                                ("withdrawn_on__gte", models.F("recorded_on")),
                                _connector="OR",
                            ),
                        ),
                        name="departure_dates_follow_its_recording",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "programme_departure", parents=(("programme_id", "programme_programme"),)
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "programme_annualreview",
                parents=(
                    ("programme_id", "programme_programme"),
                    ("completed_by_id", "accounts_user"),
                ),
            )
        ),
        migrations.RunSQL(own_sql.CREATE_RULES, own_sql.DROP_RULES),
    ]
