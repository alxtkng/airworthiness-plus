"""The transfer in of an aircraft, its positions and its configuration baseline (REQ-267 to REQ-279)."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from airworthiness_plus.configuration import sql as own_sql
from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("aircraft", "0003_owned_by_a_customer"),
        ("components", "0001_initial"),
        ("modifications", "0001_initial"),
        ("organisations", "0010_reweigh_threshold"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Transfer",
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
                ("started_on", models.DateField(verbose_name="Started")),
                (
                    "aircraft",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer",
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
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Baseline",
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
                ("signed_on", models.DateField(verbose_name="Baseline Date")),
                ("signed_by_name", models.CharField(blank=True, max_length=200)),
                ("organisation_name", models.CharField(blank=True, max_length=200)),
                ("aircraft_registration", models.CharField(blank=True, max_length=10)),
                ("type_rating", models.CharField(blank=True, max_length=200)),
                ("serial_number", models.CharField(blank=True, max_length=60)),
                ("positions", models.TextField(blank=True)),
                ("changes", models.TextField(blank=True)),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="baselines",
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
                (
                    "signed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["signed_on", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("aircraft", "signed_on"),
                        name="baseline_one_for_an_aircraft_on_a_day",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Position",
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
                    "product",
                    models.CharField(
                        choices=[
                            ("Airframe", "Airframe"),
                            ("Engine", "Engine"),
                            ("Propeller", "Propeller"),
                        ],
                        max_length=20,
                        verbose_name="Product",
                    ),
                ),
                ("chapter", models.PositiveSmallIntegerField(verbose_name="Chapter")),
                ("name", models.CharField(max_length=100, verbose_name="Position")),
                (
                    "required",
                    models.BooleanField(default=False, verbose_name="Required Equipment"),
                ),
                (
                    "tracked",
                    models.BooleanField(default=False, verbose_name="Tracked by Serial Number"),
                ),
                (
                    "major",
                    models.BooleanField(default=False, verbose_name="Major Item"),
                ),
                (
                    "recorded",
                    models.BooleanField(default=False, verbose_name="Recorded"),
                ),
                (
                    "part_number",
                    models.CharField(blank=True, max_length=60, verbose_name="Part Number"),
                ),
                (
                    "serial_number",
                    models.CharField(blank=True, max_length=60, verbose_name="Serial Number"),
                ),
                (
                    "source",
                    models.CharField(blank=True, max_length=200, verbose_name="Source"),
                ),
                (
                    "needs_change",
                    models.BooleanField(default=False, verbose_name="Needs a Recorded Change"),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="positions",
                        to="aircraft.aircraft",
                    ),
                ),
                (
                    "change",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="positions",
                        to="modifications.change",
                    ),
                ),
                (
                    "component",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="positions",
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
                "ordering": ["product", "chapter", "name", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("aircraft", "product", "chapter", "name"),
                        name="position_recorded_once_for_an_aircraft",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("name", ""), _negated=True),
                            ("product__in", ["Airframe", "Engine", "Propeller"]),
                            ("chapter__gte", 1),
                            ("chapter__lte", 99),
                        ),
                        name="position_has_a_name_a_product_and_a_chapter",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("recorded", True),
                                models.Q(("source", ""), _negated=True),
                            ),
                            models.Q(
                                ("change__isnull", True),
                                ("component__isnull", True),
                                ("needs_change", False),
                                ("recorded", False),
                                ("serial_number", ""),
                            ),
                            _connector="OR",
                        ),
                        name="position_recorded_says_its_source",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="TransferItem",
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
                ("number", models.PositiveSmallIntegerField(verbose_name="Item")),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("Open", "Open"),
                            ("In Progress", "In Progress"),
                            ("Complete", "Complete"),
                            ("Not Applicable", "Not Applicable"),
                        ],
                        default="Open",
                        max_length=20,
                        verbose_name="State",
                    ),
                ),
                (
                    "note",
                    models.CharField(blank=True, max_length=200, verbose_name="Note"),
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
                    "transfer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="configuration.transfer",
                    ),
                ),
            ],
            options={
                "ordering": ["number"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("transfer", "number"),
                        name="transfer_item_one_of_each_number",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("number__gte", 1),
                            ("number__lte", 10),
                            (
                                "state__in",
                                ["Open", "In Progress", "Complete", "Not Applicable"],
                            ),
                        ),
                        name="transfer_item_is_one_of_the_ten_in_a_known_state",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("state", "Not Applicable"), _negated=True),
                            models.Q(
                                ("number__in", [3, 4, 9, 10]),
                                models.Q(("note", ""), _negated=True),
                            ),
                            _connector="OR",
                        ),
                        name="transfer_item_not_applicable_where_it_may_be_with_the_reason",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "configuration_transfer",
                privileges=("SELECT", "INSERT"),
                parents=(("aircraft_id", "aircraft_aircraft"),),
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "configuration_transferitem",
                parents=(("transfer_id", "configuration_transfer"),),
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "configuration_position",
                parents=(
                    ("aircraft_id", "aircraft_aircraft"),
                    ("change_id", "modifications_change"),
                    ("component_id", "components_component"),
                ),
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "configuration_baseline",
                privileges=("SELECT", "INSERT"),
                parents=(
                    ("aircraft_id", "aircraft_aircraft"),
                    ("signed_by_id", "accounts_user"),
                ),
            )
        ),
        migrations.RunSQL(own_sql.CREATE_RULES, own_sql.DROP_RULES),
    ]
