"""Contracts with owners and the work orders placed under them (REQ-240 to REQ-249)."""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.contracts import sql as own_sql
from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("aircraft", "0003_owned_by_a_customer"),
        ("customers", "0001_initial"),
        ("organisations", "0009_set_up_approval_fixed"),
        ("programme", "0002_once_and_directive_kind"),
    ]

    operations = [
        migrations.CreateModel(
            name="Contract",
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
                    "scope",
                    models.CharField(
                        choices=[
                            (
                                "All Continuing Airworthiness Management Tasks",
                                "All Continuing Airworthiness Management Tasks",
                            ),
                            ("Limited Tasks", "Limited Tasks"),
                        ],
                        max_length=60,
                        verbose_name="Tasks Contracted",
                    ),
                ),
                (
                    "tasks",
                    models.CharField(blank=True, max_length=200, verbose_name="Limited Tasks"),
                ),
                (
                    "type_of_operation",
                    models.CharField(max_length=100, verbose_name="Type of Operation"),
                ),
                (
                    "owner_address",
                    models.CharField(max_length=300, verbose_name="Address of the Owner"),
                ),
                ("signed_on", models.DateField(verbose_name="Signed")),
                ("registration", models.CharField(blank=True, max_length=10)),
                ("type_rating", models.CharField(blank=True, max_length=200)),
                ("serial_number", models.CharField(blank=True, max_length=60)),
                ("owner_name", models.CharField(blank=True, max_length=200)),
                ("organisation_name", models.CharField(blank=True, max_length=200)),
                ("organisation_address", models.CharField(blank=True, max_length=300)),
                (
                    "organisation_approval_reference",
                    models.CharField(blank=True, max_length=40),
                ),
                (
                    "ended_on",
                    models.DateField(blank=True, null=True, verbose_name="Ended"),
                ),
                (
                    "end_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            (
                                "Non-Conformity With the Contract",
                                "Non-Conformity With the Contract",
                            ),
                            ("Denounced by Either Party", "Denounced by Either Party"),
                            ("Other", "Other"),
                        ],
                        max_length=40,
                        verbose_name="Reason",
                    ),
                ),
                (
                    "authority_told_on",
                    models.DateField(
                        blank=True,
                        null=True,
                        verbose_name="Civil Aviation Authority Told",
                    ),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="contracts",
                        to="aircraft.aircraft",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="contracts",
                        to="customers.customer",
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
                "ordering": ["signed_on", "id"],
            },
        ),
        migrations.CreateModel(
            name="WorkOrder",
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
                ("work", models.CharField(max_length=200, verbose_name="Work Ordered")),
                (
                    "ordered_by",
                    models.CharField(
                        choices=[
                            ("Owner", "Owner"),
                            (
                                "Continuing Airworthiness Manager",
                                "Continuing Airworthiness Manager",
                            ),
                        ],
                        max_length=40,
                        verbose_name="Ordered By",
                    ),
                ),
                ("agreed_on", models.DateField(verbose_name="Agreed")),
                ("owner_name", models.CharField(blank=True, max_length=200)),
                (
                    "closed_on",
                    models.DateField(blank=True, null=True, verbose_name="Closed"),
                ),
                (
                    "outcome",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("Completed", "Completed"),
                            ("Withdrawn", "Withdrawn"),
                        ],
                        max_length=20,
                        verbose_name="Outcome",
                    ),
                ),
                (
                    "aircraft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="work_orders",
                        to="aircraft.aircraft",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="work_orders",
                        to="contracts.contract",
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
                "ordering": ["agreed_on", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="contract",
            constraint=models.UniqueConstraint(
                condition=models.Q(("ended_on__isnull", True)),
                fields=("aircraft",),
                name="contract_one_in_force_for_each_aircraft",
            ),
        ),
        migrations.AddConstraint(
            model_name="contract",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        models.Q(
                            ("scope", "All Continuing Airworthiness Management Tasks"),
                            ("tasks", ""),
                        ),
                        models.Q(
                            ("scope", "Limited Tasks"),
                            models.Q(("tasks", ""), _negated=True),
                        ),
                        _connector="OR",
                    ),
                    models.Q(("type_of_operation", ""), _negated=True),
                    models.Q(("owner_address", ""), _negated=True),
                ),
                name="contract_says_its_tasks_operation_and_owner_address",
            ),
        ),
        migrations.AddConstraint(
            model_name="contract",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("authority_told_on__isnull", True),
                        ("end_reason", ""),
                        ("ended_on__isnull", True),
                    ),
                    models.Q(
                        (
                            "end_reason__in",
                            [
                                "Non-Conformity With the Contract",
                                "Denounced by Either Party",
                                "Other",
                            ],
                        ),
                        ("ended_on__gte", models.F("signed_on")),
                        ("ended_on__isnull", False),
                        models.Q(
                            ("authority_told_on__isnull", True),
                            ("authority_told_on__gte", models.F("ended_on")),
                            _connector="OR",
                        ),
                    ),
                    _connector="OR",
                ),
                name="contract_ended_has_a_reason_and_is_told_on_or_after",
            ),
        ),
        migrations.AddConstraint(
            model_name="workorder",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("work", ""), _negated=True),
                    ("ordered_by__in", ["Owner", "Continuing Airworthiness Manager"]),
                ),
                name="work_order_says_the_work_and_who_ordered_it",
            ),
        ),
        migrations.AddConstraint(
            model_name="workorder",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("closed_on__isnull", True),
                        ("outcome", ""),
                        ("work_done__isnull", True),
                    ),
                    models.Q(
                        ("closed_on__gte", models.F("agreed_on")),
                        ("closed_on__isnull", False),
                        ("outcome__in", ["Completed", "Withdrawn"]),
                        models.Q(
                            ("work_done__isnull", True),
                            ("outcome", "Completed"),
                            _connector="OR",
                        ),
                    ),
                    _connector="OR",
                ),
                name="work_order_closed_has_an_outcome",
            ),
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "contracts_contract",
                parents=(
                    ("aircraft_id", "aircraft_aircraft"),
                    ("customer_id", "customers_customer"),
                ),
            )
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "contracts_workorder",
                parents=(
                    ("aircraft_id", "aircraft_aircraft"),
                    ("contract_id", "contracts_contract"),
                    ("work_done_id", "programme_workdone"),
                ),
            )
        ),
        migrations.RunSQL(own_sql.CREATE_CONTRACT_RULES, own_sql.DROP_CONTRACT_RULES),
    ]
