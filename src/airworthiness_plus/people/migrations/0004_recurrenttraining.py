import uuid

import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0011_approval_for_activity"),
        ("people", "0003_maintenance_authorisation"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecurrentTraining",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("subject", models.CharField(max_length=160, verbose_name="Training Subject")),
                (
                    "evidence_reference",
                    models.CharField(max_length=160, verbose_name="Evidence Reference"),
                ),
                ("completed_on", models.DateField(verbose_name="Completed On")),
                ("due_on", models.DateField(blank=True, null=True, verbose_name="Renewal Due On")),
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
                        related_name="recurrent_training",
                        to="people.person",
                    ),
                ),
            ],
            options={
                "ordering": ["-completed_on", "subject", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("subject", ""), _negated=True),
                            models.Q(("evidence_reference", ""), _negated=True),
                        ),
                        name="recurrent_training_has_subject_and_evidence",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("due_on__isnull", True),
                            ("due_on__gt", models.F("completed_on")),
                            _connector="OR",
                        ),
                        name="recurrent_training_due_after_completion",
                    ),
                    models.UniqueConstraint(
                        models.F("person"),
                        django.db.models.functions.text.Lower("subject"),
                        models.F("completed_on"),
                        name="recurrent_training_completion_recorded_once",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "people_recurrenttraining",
                privileges=("SELECT", "INSERT"),
                parents=(("person_id", "people_person"),),
            )
        ),
    ]
