import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0011_approval_for_activity"),
        ("people", "0005_experienceevidence"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExperienceWithdrawal",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("reason", models.CharField(max_length=400, verbose_name="Reason")),
                (
                    "evidence",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="withdrawal",
                        to="people.experienceevidence",
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
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("reason", ""), _negated=True),
                        name="experience_withdrawal_has_reason",
                    )
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "people_experiencewithdrawal",
                privileges=("SELECT", "INSERT"),
                parents=(("evidence_id", "people_experienceevidence"),),
            )
        ),
    ]
