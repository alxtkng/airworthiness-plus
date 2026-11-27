import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0011_approval_for_activity"),
        ("people", "0004_recurrenttraining"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExperienceEvidence",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("Maintenance", "Maintenance"),
                            ("Substitute", "Permitted Substitute Activity"),
                            ("Employment", "Approved Maintenance Employment"),
                        ],
                        max_length=20,
                        verbose_name="Evidence Type",
                    ),
                ),
                (
                    "evidence_reference",
                    models.CharField(max_length=160, verbose_name="Evidence Reference"),
                ),
                (
                    "qualification_basis",
                    models.CharField(
                        max_length=500, verbose_name="Basis for Counting the Experience"
                    ),
                ),
                (
                    "starts_on",
                    models.DateField(verbose_name="Work Date or First Day of Employment"),
                ),
                (
                    "ends_on",
                    models.DateField(blank=True, null=True, verbose_name="Last Day of Employment"),
                ),
                (
                    "days",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=3,
                        null=True,
                        verbose_name="Days Credited",
                    ),
                ),
                (
                    "aircraft_type",
                    models.CharField(blank=True, max_length=150, verbose_name="Aircraft Type"),
                ),
                (
                    "aircraft_registration",
                    models.CharField(
                        blank=True, max_length=16, verbose_name="Aircraft Registration"
                    ),
                ),
                (
                    "licence_subcategory",
                    models.CharField(
                        blank=True, max_length=30, verbose_name="Licence Category or Subcategory"
                    ),
                ),
                (
                    "authorisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="experience_evidence",
                        to="people.maintenanceauthorisation",
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
                "ordering": ["-starts_on", "evidence_reference", "id"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("authorisation", "evidence_reference"),
                        name="experience_evidence_reference_used_once",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("evidence_reference", ""), _negated=True),
                            models.Q(("qualification_basis", ""), _negated=True),
                        ),
                        name="experience_evidence_has_reference_and_basis",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(
                                ("days__isnull", True),
                                ("ends_on__gte", models.F("starts_on")),
                                ("ends_on__isnull", False),
                                ("kind", "Employment"),
                                ("aircraft_registration", ""),
                                ("aircraft_type", ""),
                                ("licence_subcategory", ""),
                            ),
                            models.Q(
                                ("days__gt", 0),
                                ("days__isnull", False),
                                ("days__lte", 1),
                                ("ends_on__isnull", True),
                                ("kind__in", ["Maintenance", "Substitute"]),
                                models.Q(("aircraft_type", ""), _negated=True),
                                models.Q(
                                    ("kind", "Substitute"),
                                    models.Q(("aircraft_registration", ""), _negated=True),
                                    _connector="OR",
                                ),
                                models.Q(("licence_subcategory", ""), _negated=True),
                            ),
                            _connector="OR",
                        ),
                        name="experience_evidence_matches_its_type",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "people_experienceevidence",
                privileges=("SELECT", "INSERT"),
                parents=(("authorisation_id", "people_maintenanceauthorisation"),),
            )
        ),
    ]
