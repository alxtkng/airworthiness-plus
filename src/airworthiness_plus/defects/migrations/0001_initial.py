"""Defects and the action taken on a repeat defect (REQ-220 to REQ-229)."""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.defects import sql as defect_sql
from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("aircraft", "0003_owned_by_a_customer"),
        ("organisations", "0009_set_up_approval_fixed"),
        ("people", "0002_sign_in_keeps_its_person"),
        ("programme", "0002_once_and_directive_kind"),
        ("history", "0004_hash_algorithm"),
    ]

    operations = [
        migrations.CreateModel(
            name="Defect",
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
                ("title", models.CharField(max_length=200, verbose_name="Defect")),
                (
                    "note",
                    models.CharField(blank=True, max_length=200, verbose_name="Note"),
                ),
                ("found_on", models.DateField(verbose_name="Found")),
                ("chapter", models.PositiveSmallIntegerField(verbose_name="Chapter")),
                ("system", models.CharField(max_length=100, verbose_name="System")),
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("Not Deferrable", "Not Deferrable"),
                            ("Deferred", "Deferred"),
                        ],
                        max_length=20,
                        verbose_name="Decision",
                    ),
                ),
                (
                    "basis",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("Pilot-in-Command", "Pilot-in-Command"),
                            (
                                "Pilot-in-Command, Minimum Equipment List",
                                "Pilot-in-Command, Minimum Equipment List",
                            ),
                            (
                                "Pilot-in-Command, With Agreement",
                                "Pilot-in-Command, With Agreement",
                            ),
                            ("Certifying Staff", "Certifying Staff"),
                        ],
                        max_length=60,
                        verbose_name="Deferred By",
                    ),
                ),
                ("decided_on", models.DateField(verbose_name="Decided")),
                ("decided_by_name", models.CharField(blank=True, max_length=200)),
                ("decided_by_licence", models.CharField(blank=True, max_length=100)),
                (
                    "default_days",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                (
                    "data_limit_on",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Limit in the Maintenance Data",
                    ),
                ),
                (
                    "limit_on",
                    models.DateField(blank=True, null=True, verbose_name="Limit"),
                ),
                (
                    "rectification",
                    models.CharField(blank=True, max_length=200, verbose_name="Rectification"),
                ),
                (
                    "closed_on",
                    models.DateField(blank=True, null=True, verbose_name="Closed"),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="defects",
                        to="aircraft.aircraft",
                    ),
                ),
                (
                    "decided_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="people.person",
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
                    "work_done",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="programme.workdone",
                    ),
                ),
            ],
            options={
                "ordering": ["found_on", "title", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("title", ""), _negated=True),
                            models.Q(("system", ""), _negated=True),
                            ("chapter__gte", 1),
                            ("chapter__lte", 99),
                            ("decided_on__gte", models.F("found_on")),
                        ),
                        name="defect_has_a_title_a_system_and_a_decision_not_before_it_was_found",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("basis", ""),
                                ("data_limit_on__isnull", True),
                                ("decision", "Not Deferrable"),
                                ("default_days__isnull", True),
                                ("limit_on__isnull", True),
                            ),
                            models.Q(
                                (
                                    "basis__in",
                                    [
                                        "Pilot-in-Command",
                                        "Pilot-in-Command, Minimum Equipment List",
                                        "Pilot-in-Command, With Agreement",
                                        "Certifying Staff",
                                    ],
                                ),
                                ("decision", "Deferred"),
                                ("limit_on__gte", models.F("decided_on")),
                                ("limit_on__isnull", False),
                            ),
                            _connector="OR",
                        ),
                        name="defect_deferred_has_a_basis_and_a_limit",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("default_days__isnull", True),
                            models.Q(("default_days__gte", 1), ("default_days__lte", 365)),
                            _connector="OR",
                        ),
                        name="defect_default_limit_from_1_to_365_days",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("decision", "Deferred"), _negated=True),
                            models.Q(
                                ("basis", "Pilot-in-Command, Minimum Equipment List"),
                                ("data_limit_on__isnull", False),
                                ("default_days__isnull", True),
                            ),
                            models.Q(
                                models.Q(
                                    (
                                        "basis",
                                        "Pilot-in-Command, Minimum Equipment List",
                                    ),
                                    _negated=True,
                                ),
                                ("default_days__isnull", False),
                            ),
                            _connector="OR",
                        ),
                        name="defect_limit_comes_from_the_list_or_the_default",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("basis", "Certifying Staff"),
                                ("decided_by__isnull", False),
                            ),
                            ("basis", ""),
                            models.Q(
                                (
                                    "basis__in",
                                    [
                                        "Pilot-in-Command",
                                        "Pilot-in-Command, Minimum Equipment List",
                                        "Pilot-in-Command, With Agreement",
                                    ],
                                ),
                                ("decided_by__isnull", True),
                            ),
                            _connector="OR",
                        ),
                        name="defect_certifying_staff_are_named_and_a_pilot_is_not",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("closed_on__isnull", True),
                                ("rectification", ""),
                                ("work_done__isnull", True),
                            ),
                            models.Q(
                                ("closed_on__gte", models.F("found_on")),
                                ("closed_on__isnull", False),
                                models.Q(("rectification", ""), _negated=True),
                            ),
                            _connector="OR",
                        ),
                        name="defect_closed_has_a_rectification_and_a_day",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="RepeatAction",
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
                    "type_rating",
                    models.CharField(max_length=200, verbose_name="Type Rating"),
                ),
                ("chapter", models.PositiveSmallIntegerField(verbose_name="Chapter")),
                ("action", models.CharField(max_length=200, verbose_name="Action")),
                ("recorded_on", models.DateField(verbose_name="Recorded")),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organisations.organisation",
                    ),
                ),
                (
                    "supersedes",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="superseded_by",
                        to="defects.repeataction",
                    ),
                ),
            ],
            options={
                "ordering": ["type_rating", "chapter", "recorded_on", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("type_rating", ""), _negated=True),
                            models.Q(("action", ""), _negated=True),
                            ("chapter__gte", 1),
                            ("chapter__lte", 99),
                        ),
                        name="repeat_action_has_a_type_a_chapter_and_an_action",
                    )
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "defects_defect",
                parents=(
                    ("aircraft_id", "aircraft_aircraft"),
                    ("decided_by_id", "people_person"),
                    ("work_done_id", "programme_workdone"),
                ),
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "defects_repeataction",
                privileges=("SELECT", "INSERT"),
                parents=(("supersedes_id", "defects_repeataction"),),
            )
        ),
        migrations.RunSQL(defect_sql.CREATE_DEFECT_RULES, defect_sql.DROP_DEFECT_RULES),
    ]
