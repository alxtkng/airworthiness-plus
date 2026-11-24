"""A record for each owner or operator (REQ-207)."""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organisations", "0006_approvals_held"),
        ("history", "0004_hash_algorithm"),
    ]

    operations = [
        migrations.CreateModel(
            name="Customer",
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
                ("name", models.CharField(max_length=200, verbose_name="Customer")),
                (
                    "kind",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("Pilot-Owner", "Pilot-Owner"),
                            ("Syndicate", "Syndicate"),
                            ("Flying Club", "Flying Club"),
                            ("Operator", "Operator"),
                        ],
                        max_length=20,
                        verbose_name="Kind",
                    ),
                ),
                (
                    "members",
                    models.PositiveSmallIntegerField(
                        blank=True, null=True, verbose_name="Members of the Syndicate"
                    ),
                ),
                (
                    "customer_since",
                    models.DateField(blank=True, null=True, verbose_name="Customer Since"),
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
                "ordering": ["name", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("name", ""), _negated=True),
                            (
                                "kind__in",
                                ["", "Pilot-Owner", "Syndicate", "Flying Club", "Operator"],
                            ),
                        ),
                        name="customer_has_a_name_and_a_known_kind",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("members__isnull", True),
                            models.Q(("kind", "Syndicate"), ("members__gte", 1)),
                            _connector="OR",
                        ),
                        name="customer_members_are_of_a_syndicate",
                    ),
                ],
            },
        ),
        migrations.RunSQL(*sql.protect_record_table("customers_customer")),
    ]
