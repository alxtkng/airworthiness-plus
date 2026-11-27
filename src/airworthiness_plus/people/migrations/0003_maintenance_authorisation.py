import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0011_approval_for_activity"),
        ("people", "0002_sign_in_keeps_its_person"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceAuthorisation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "reference",
                    models.CharField(max_length=80, verbose_name="Authorisation Reference"),
                ),
                ("scope", models.CharField(max_length=400, verbose_name="Scope and Limitations")),
                ("valid_from", models.DateField(verbose_name="Valid From")),
                ("valid_to", models.DateField(blank=True, null=True, verbose_name="Valid To")),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organisations.organisation",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="maintenance_authorisations",
                        to="people.person",
                    ),
                ),
            ],
            options={
                "ordering": ["person__full_name", "-valid_from", "reference", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("reference", ""), _negated=True),
                            models.Q(("scope", ""), _negated=True),
                        ),
                        name="maintenance_authorisation_has_reference_and_scope",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("valid_to__isnull", True),
                            ("valid_to__gte", models.F("valid_from")),
                            _connector="OR",
                        ),
                        name="maintenance_authorisation_dates_in_order",
                    ),
                    models.UniqueConstraint(
                        fields=("person", "reference", "valid_from"),
                        name="maintenance_authorisation_recorded_once",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "people_maintenanceauthorisation",
                privileges=("SELECT", "INSERT"),
                parents=(("person_id", "people_person"),),
            )
        ),
    ]
