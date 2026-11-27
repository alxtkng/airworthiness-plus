"""Certificates of release to service (REQ-260 to REQ-268)."""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql
from airworthiness_plus.releases import sql as own_sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("history", "0004_hash_algorithm"),
        ("organisations", "0009_set_up_approval_fixed"),
        ("people", "0002_sign_in_keeps_its_person"),
        ("programme", "0002_once_and_directive_kind"),
    ]

    operations = [
        migrations.CreateModel(
            name="Release",
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
                    "reference",
                    models.CharField(max_length=100, verbose_name="Certificate Reference"),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            (
                                "Organisation Certifying Staff",
                                "Organisation Certifying Staff",
                            ),
                            (
                                "Independent Certifying Staff",
                                "Independent Certifying Staff",
                            ),
                            ("Pilot-Owner", "Pilot-Owner"),
                        ],
                        max_length=40,
                        verbose_name="Issued By",
                    ),
                ),
                (
                    "issuer_name",
                    models.CharField(blank=True, max_length=200, verbose_name="Name"),
                ),
                (
                    "licence",
                    models.CharField(blank=True, max_length=100, verbose_name="Licence Number"),
                ),
                ("approval_reference", models.CharField(blank=True, max_length=40)),
                ("issued_on", models.DateField(verbose_name="Issued")),
                (
                    "incomplete",
                    models.BooleanField(
                        default=False, verbose_name="Maintenance Could Not Be Completed"
                    ),
                ),
                (
                    "limitations",
                    models.CharField(blank=True, max_length=200, verbose_name="Limitations"),
                ),
                ("registration", models.CharField(blank=True, max_length=10)),
                ("maintenance", models.CharField(blank=True, max_length=200)),
                ("completed_on", models.DateField(blank=True, null=True)),
                (
                    "issued_by",
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
                    "work",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="certificate",
                        to="programme.workdone",
                    ),
                ),
            ],
            options={
                "ordering": ["issued_on", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("reference", ""), _negated=True),
                            (
                                "kind__in",
                                [
                                    "Organisation Certifying Staff",
                                    "Independent Certifying Staff",
                                    "Pilot-Owner",
                                ],
                            ),
                        ),
                        name="release_has_a_reference_and_a_known_issuer",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("issued_by__isnull", False),
                                ("kind", "Organisation Certifying Staff"),
                            ),
                            models.Q(
                                ("issued_by__isnull", True),
                                (
                                    "kind__in",
                                    ["Independent Certifying Staff", "Pilot-Owner"],
                                ),
                                models.Q(("issuer_name", ""), _negated=True),
                            ),
                            _connector="OR",
                        ),
                        name="release_names_who_issued_it",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("kind", "Pilot-Owner"), _negated=True),
                            models.Q(("licence", ""), _negated=True),
                            _connector="OR",
                        ),
                        name="release_by_a_pilot_owner_has_the_licence_number",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("incomplete", False),
                            models.Q(("limitations", ""), _negated=True),
                            _connector="OR",
                        ),
                        name="release_of_incomplete_maintenance_states_its_limitations",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "releases_release",
                privileges=("SELECT", "INSERT"),
                parents=(("work_id", "programme_workdone"), ("issued_by_id", "people_person")),
            )
        ),
        migrations.RunSQL(own_sql.CREATE_RELEASE_RULES, own_sql.DROP_RELEASE_RULES),
    ]
