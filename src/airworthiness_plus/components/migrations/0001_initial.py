"""Components and where each has been fitted (REQ-230 to REQ-239)."""

import uuid
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.components import sql as own_sql
from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("aircraft", "0003_owned_by_a_customer"),
        ("organisations", "0009_set_up_approval_fixed"),
    ]

    operations = [
        migrations.CreateModel(
            name="Component",
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
                ("name", models.CharField(max_length=200, verbose_name="Component")),
                (
                    "part_number",
                    models.CharField(blank=True, max_length=60, verbose_name="Part Number"),
                ),
                (
                    "serial_number",
                    models.CharField(blank=True, max_length=60, verbose_name="Serial Number"),
                ),
                (
                    "basis",
                    models.CharField(
                        choices=[
                            ("Certified Life Limit", "Certified Life Limit"),
                            ("Service Life Limit", "Service Life Limit"),
                            (
                                "Manufacturer Recommendation",
                                "Manufacturer Recommendation",
                            ),
                            ("Date on the Component", "Date on the Component"),
                            ("On Condition", "On Condition"),
                            ("No Limit Recorded", "No Limit Recorded"),
                        ],
                        max_length=40,
                        verbose_name="Limit",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        blank=True, max_length=200, verbose_name="Source of the Limit"
                    ),
                ),
                (
                    "limit_hours",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=7,
                        null=True,
                        verbose_name="Limit in Hours",
                    ),
                ),
                (
                    "limit_cycles",
                    models.PositiveIntegerField(
                        blank=True, null=True, verbose_name="Limit in Cycles"
                    ),
                ),
                (
                    "limit_months",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="Limit in Months"
                    ),
                ),
                (
                    "limit_date",
                    models.DateField(blank=True, null=True, verbose_name="Date on the Component"),
                ),
                (
                    "date_label",
                    models.CharField(blank=True, max_length=60, verbose_name="What the Date Is"),
                ),
                (
                    "review_hours",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=6,
                        null=True,
                        verbose_name="Reviewed Every, Hours",
                    ),
                ),
                (
                    "last_review_hours",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=8,
                        null=True,
                        verbose_name="Airframe Hours at the Last Review",
                    ),
                ),
                (
                    "last_review_on",
                    models.DateField(blank=True, null=True, verbose_name="Last Reviewed"),
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
                "ordering": ["name", "serial_number", "id"],
            },
        ),
        migrations.CreateModel(
            name="Installation",
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
                ("aircraft_registration", models.CharField(blank=True, max_length=10)),
                ("position", models.CharField(max_length=100, verbose_name="Position")),
                ("fitted_on", models.DateField(verbose_name="Fitted")),
                (
                    "airframe_hours_fitted",
                    models.DecimalField(
                        decimal_places=1,
                        max_digits=8,
                        verbose_name="Airframe Hours When Fitted",
                    ),
                ),
                (
                    "airframe_cycles_fitted",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Airframe Cycles When Fitted"
                    ),
                ),
                (
                    "hours_at_fitting",
                    models.DecimalField(
                        decimal_places=1,
                        max_digits=8,
                        verbose_name="Hours Since New or Overhaul When Fitted",
                    ),
                ),
                (
                    "cycles_at_fitting",
                    models.PositiveIntegerField(
                        default=0,
                        verbose_name="Cycles Since New or Overhaul When Fitted",
                    ),
                ),
                (
                    "life_from",
                    models.DateField(blank=True, null=True, verbose_name="New or Last Overhauled"),
                ),
                (
                    "release_document",
                    models.CharField(blank=True, max_length=100, verbose_name="Release Document"),
                ),
                (
                    "removed_on",
                    models.DateField(blank=True, null=True, verbose_name="Removed"),
                ),
                (
                    "airframe_hours_removed",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=8,
                        null=True,
                        verbose_name="Airframe Hours When Removed",
                    ),
                ),
                (
                    "airframe_cycles_removed",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Airframe Cycles When Removed",
                    ),
                ),
                (
                    "removal_reason",
                    models.CharField(blank=True, max_length=200, verbose_name="Reason for Removal"),
                ),
                (
                    "sent_to",
                    models.CharField(blank=True, max_length=200, verbose_name="Sent To"),
                ),
                (
                    "due_back_on",
                    models.DateField(blank=True, null=True, verbose_name="Due Back"),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="installations",
                        to="aircraft.aircraft",
                    ),
                ),
                (
                    "component",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="installations",
                        to="components.component",
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
                "ordering": ["fitted_on", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="component",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("name", ""), _negated=True),
                    (
                        "basis__in",
                        [
                            "Certified Life Limit",
                            "Service Life Limit",
                            "Manufacturer Recommendation",
                            "Date on the Component",
                            "On Condition",
                            "No Limit Recorded",
                        ],
                    ),
                ),
                name="component_has_a_name_and_a_known_limit",
            ),
        ),
        migrations.AddConstraint(
            model_name="component",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        (
                            "basis__in",
                            (
                                "Certified Life Limit",
                                "Service Life Limit",
                                "Manufacturer Recommendation",
                            ),
                        ),
                        models.Q(
                            ("limit_cycles__isnull", True),
                            ("limit_hours__isnull", True),
                            ("limit_months__isnull", True),
                            _negated=True,
                        ),
                        ("date_label", ""),
                        ("limit_date__isnull", True),
                        ("last_review_hours__isnull", True),
                        ("last_review_on__isnull", True),
                        ("review_hours__isnull", True),
                    ),
                    models.Q(
                        ("basis", "Date on the Component"),
                        ("limit_date__isnull", False),
                        models.Q(("date_label", ""), _negated=True),
                        ("limit_cycles__isnull", True),
                        ("limit_hours__isnull", True),
                        ("limit_months__isnull", True),
                        ("last_review_hours__isnull", True),
                        ("last_review_on__isnull", True),
                        ("review_hours__isnull", True),
                    ),
                    models.Q(
                        ("basis", "On Condition"),
                        ("last_review_hours__isnull", False),
                        ("last_review_on__isnull", False),
                        ("review_hours__isnull", False),
                        ("limit_cycles__isnull", True),
                        ("limit_hours__isnull", True),
                        ("limit_months__isnull", True),
                        ("date_label", ""),
                        ("limit_date__isnull", True),
                    ),
                    models.Q(
                        ("basis", "No Limit Recorded"),
                        ("limit_cycles__isnull", True),
                        ("limit_hours__isnull", True),
                        ("limit_months__isnull", True),
                        ("date_label", ""),
                        ("limit_date__isnull", True),
                        ("last_review_hours__isnull", True),
                        ("last_review_on__isnull", True),
                        ("review_hours__isnull", True),
                    ),
                    _connector="OR",
                ),
                name="component_limit_fits_its_kind",
            ),
        ),
        migrations.AddConstraint(
            model_name="component",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("limit_hours__isnull", True),
                        models.Q(
                            ("limit_hours__gt", 0),
                            ("limit_hours__lte", Decimal("99999.9")),
                        ),
                        _connector="OR",
                    ),
                    models.Q(
                        ("limit_cycles__isnull", True),
                        models.Q(("limit_cycles__gte", 1), ("limit_cycles__lte", 999999)),
                        _connector="OR",
                    ),
                    models.Q(
                        ("limit_months__isnull", True),
                        models.Q(("limit_months__gte", 1), ("limit_months__lte", 1200)),
                        _connector="OR",
                    ),
                    models.Q(
                        ("review_hours__isnull", True),
                        models.Q(
                            ("review_hours__gt", 0),
                            ("review_hours__lte", Decimal("9999.9")),
                        ),
                        _connector="OR",
                    ),
                    models.Q(
                        ("last_review_hours__isnull", True),
                        models.Q(
                            ("last_review_hours__gte", 0),
                            ("last_review_hours__lte", Decimal("999999.9")),
                        ),
                        _connector="OR",
                    ),
                ),
                name="component_limits_within_bounds",
            ),
        ),
        migrations.AddConstraint(
            model_name="installation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("removed_on__isnull", True)),
                fields=("component",),
                name="installation_one_at_a_time_for_a_component",
            ),
        ),
        migrations.AddConstraint(
            model_name="installation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("position", ""), _negated=True),
                    ("airframe_hours_fitted__gte", 0),
                    ("airframe_hours_fitted__lte", Decimal("999999.9")),
                    ("hours_at_fitting__gte", 0),
                    ("hours_at_fitting__lte", Decimal("999999.9")),
                    ("airframe_cycles_fitted__lte", 9999999),
                    ("cycles_at_fitting__lte", 9999999),
                    models.Q(
                        ("life_from__isnull", True),
                        ("life_from__lte", models.F("fitted_on")),
                        _connector="OR",
                    ),
                ),
                name="installation_fitting_within_bounds",
            ),
        ),
        migrations.AddConstraint(
            model_name="installation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("airframe_cycles_removed__isnull", True),
                        ("airframe_hours_removed__isnull", True),
                        ("due_back_on__isnull", True),
                        ("removal_reason", ""),
                        ("removed_on__isnull", True),
                        ("sent_to", ""),
                    ),
                    models.Q(
                        (
                            "airframe_cycles_removed__gte",
                            models.F("airframe_cycles_fitted"),
                        ),
                        ("airframe_cycles_removed__isnull", False),
                        ("airframe_cycles_removed__lte", 9999999),
                        (
                            "airframe_hours_removed__gte",
                            models.F("airframe_hours_fitted"),
                        ),
                        ("airframe_hours_removed__isnull", False),
                        ("airframe_hours_removed__lte", Decimal("999999.9")),
                        ("removed_on__gte", models.F("fitted_on")),
                        ("removed_on__isnull", False),
                        models.Q(("removal_reason", ""), _negated=True),
                        models.Q(
                            ("due_back_on__isnull", True),
                            ("due_back_on__gte", models.F("removed_on")),
                            _connector="OR",
                        ),
                    ),
                    _connector="OR",
                ),
                name="installation_removal_is_complete_or_absent",
            ),
        ),
        migrations.RunSQL(*sql.protect_record_table("components_component")),
        migrations.RunSQL(
            *sql.protect_record_table(
                "components_installation",
                parents=(
                    ("component_id", "components_component"),
                    ("aircraft_id", "aircraft_aircraft"),
                ),
            )
        ),
        migrations.RunSQL(own_sql.CREATE_INSTALLATION_RULES, own_sql.DROP_INSTALLATION_RULES),
    ]
