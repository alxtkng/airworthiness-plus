"""Service bulletin decisions, changes and repairs, weighings and weight schedules (REQ-249 to REQ-259)."""

import uuid
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql
from airworthiness_plus.modifications import sql as own_sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("aircraft", "0003_owned_by_a_customer"),
        ("organisations", "0010_reweigh_threshold"),
    ]

    operations = [
        migrations.CreateModel(
            name="Bulletin",
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
                ("title", models.CharField(max_length=200, verbose_name="Bulletin")),
                (
                    "reference",
                    models.CharField(max_length=100, verbose_name="Reference"),
                ),
                (
                    "classification",
                    models.CharField(
                        choices=[
                            ("Recommended", "Recommended"),
                            ("Optional", "Optional"),
                        ],
                        max_length=20,
                        verbose_name="Classification",
                    ),
                ),
                ("sent_on", models.DateField(verbose_name="Sent to the Owner")),
                (
                    "reminder_on",
                    models.DateField(blank=True, null=True, verbose_name="Reminder"),
                ),
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("Awaiting Owner", "Awaiting Owner"),
                            ("Accepted", "Accepted"),
                            ("Declined", "Declined"),
                        ],
                        default="Awaiting Owner",
                        max_length=20,
                        verbose_name="Owner Decision",
                    ),
                ),
                (
                    "detail",
                    models.CharField(blank=True, max_length=200, verbose_name="Decision in Detail"),
                ),
                (
                    "decided_on",
                    models.DateField(blank=True, null=True, verbose_name="Recorded"),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bulletins",
                        to="aircraft.aircraft",
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
                "ordering": ["aircraft__registration", "sent_on", "title", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("title", ""), _negated=True),
                            models.Q(("reference", ""), _negated=True),
                            ("classification__in", ["Recommended", "Optional"]),
                            models.Q(
                                ("reminder_on__isnull", True),
                                ("reminder_on__gte", models.F("sent_on")),
                                _connector="OR",
                            ),
                        ),
                        name="bulletin_has_a_title_a_reference_and_a_classification",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("decided_on__isnull", True),
                                ("decision", "Awaiting Owner"),
                                ("detail", ""),
                            ),
                            models.Q(
                                ("decided_on__gte", models.F("sent_on")),
                                ("decided_on__isnull", False),
                                ("decision__in", ["Accepted", "Declined"]),
                                models.Q(("detail", ""), _negated=True),
                            ),
                            _connector="OR",
                        ),
                        name="bulletin_decision_is_whole_or_awaited",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Change",
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
                    "title",
                    models.CharField(max_length=200, verbose_name="Change or Repair"),
                ),
                (
                    "route",
                    models.CharField(
                        choices=[
                            ("Standard Change", "Standard Change"),
                            ("Standard Repair", "Standard Repair"),
                            ("Minor Change", "Minor Change"),
                            (
                                "Manufacturer's Structural Repair Data",
                                "Manufacturer's Structural Repair Data",
                            ),
                            ("Other Approved Data", "Other Approved Data"),
                            (
                                "Maintenance, Same Part Number",
                                "Maintenance, Same Part Number",
                            ),
                        ],
                        max_length=60,
                        verbose_name="Approval Route",
                    ),
                ),
                (
                    "data",
                    models.CharField(
                        blank=True,
                        choices=[
                            (
                                "Approved by the Civil Aviation Authority",
                                "Approved by the Civil Aviation Authority",
                            ),
                            (
                                "Approved by a Design Organisation",
                                "Approved by a Design Organisation",
                            ),
                            (
                                "Contained in the Requirements of Point 21.A.90B or 21.A.431B",
                                "Contained in the Requirements of Point 21.A.90B or 21.A.431B",
                            ),
                        ],
                        max_length=80,
                        verbose_name="Data",
                    ),
                ),
                (
                    "reference",
                    models.CharField(blank=True, max_length=100, verbose_name="Reference"),
                ),
                (
                    "mass_effect",
                    models.DecimalField(
                        decimal_places=1,
                        max_digits=4,
                        verbose_name="Mass Effect, Kilograms",
                    ),
                ),
                (
                    "embodied_on",
                    models.DateField(blank=True, null=True, verbose_name="Embodied"),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="changes",
                        to="aircraft.aircraft",
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
                "ordering": ["aircraft__registration", "embodied_on", "title", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("title", ""), _negated=True),
                            (
                                "route__in",
                                [
                                    "Standard Change",
                                    "Standard Repair",
                                    "Minor Change",
                                    "Manufacturer's Structural Repair Data",
                                    "Other Approved Data",
                                    "Maintenance, Same Part Number",
                                ],
                            ),
                            ("mass_effect__gte", Decimal("-999.9")),
                            ("mass_effect__lte", Decimal("999.9")),
                        ),
                        name="change_has_a_title_a_route_and_a_mass_within_bounds",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                (
                                    "data",
                                    "Contained in the Requirements of Point 21.A.90B or 21.A.431B",
                                ),
                                ("route__in", ("Standard Change", "Standard Repair")),
                            ),
                            models.Q(
                                (
                                    "data__in",
                                    [
                                        "Approved by the Civil Aviation Authority",
                                        "Approved by a Design Organisation",
                                    ],
                                ),
                                (
                                    "route__in",
                                    (
                                        "Minor Change",
                                        "Manufacturer's Structural Repair Data",
                                        "Other Approved Data",
                                    ),
                                ),
                            ),
                            models.Q(("data", ""), ("route", "Maintenance, Same Part Number")),
                            _connector="OR",
                        ),
                        name="change_data_fits_its_route",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Weighing",
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
                ("weighed_on", models.DateField(verbose_name="Weighed")),
                (
                    "reference",
                    models.CharField(max_length=100, verbose_name="Weighing Report"),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="weighings",
                        to="aircraft.aircraft",
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
                "ordering": ["weighed_on", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("aircraft", "weighed_on"),
                        name="weighing_one_for_an_aircraft_on_a_day",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("reference", ""), _negated=True),
                        name="weighing_has_a_report",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="WeightSchedule",
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
                ("issue", models.PositiveSmallIntegerField(verbose_name="Issue")),
                ("issued_on", models.DateField(verbose_name="Issued")),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="weight_schedules",
                        to="aircraft.aircraft",
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
                "ordering": ["issue", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("aircraft", "issue"),
                        name="weight_schedule_one_of_each_issue",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("issue__gte", 1), ("issue__lte", 9999)),
                        name="weight_schedule_issue_from_1_to_9999",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "modifications_bulletin", parents=(("aircraft_id", "aircraft_aircraft"),)
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "modifications_change", parents=(("aircraft_id", "aircraft_aircraft"),)
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "modifications_weighing",
                privileges=("SELECT", "INSERT"),
                parents=(("aircraft_id", "aircraft_aircraft"),),
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "modifications_weightschedule",
                privileges=("SELECT", "INSERT"),
                parents=(("aircraft_id", "aircraft_aircraft"),),
            )
        ),
        migrations.RunSQL(own_sql.CREATE_RULES, own_sql.DROP_RULES),
    ]
