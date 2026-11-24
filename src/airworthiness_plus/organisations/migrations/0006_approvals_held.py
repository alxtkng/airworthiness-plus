"""The approvals an organisation holds, each a record with its reference (REQ-200)."""

import uuid

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.history import sql
from airworthiness_plus.organisations.sql import APPROVAL_FOR_EACH_ORGANISATION


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0005_certificate_serial_floor"),
        ("history", "0004_hash_algorithm"),
    ]

    operations = [
        migrations.CreateModel(
            name="Approval",
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
                    "approval",
                    models.CharField(
                        choices=[
                            ("Part-CAO", "Part-CAO"),
                            ("Part-CAMO", "Part-CAMO"),
                            ("Part-145", "Part-145"),
                        ],
                        max_length=20,
                        verbose_name="Approval",
                    ),
                ),
                (
                    "reference",
                    models.CharField(max_length=40, verbose_name="Approval Reference"),
                ),
                (
                    "no_longer_held_on",
                    models.DateField(blank=True, null=True, verbose_name="No Longer Held From"),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.RemoveConstraint(
            model_name="organisation",
            name="organisation_has_known_privileges",
        ),
        migrations.AlterField(
            model_name="organisation",
            name="approval_type",
            field=models.CharField(
                choices=[
                    ("Part-CAO", "Part-CAO"),
                    ("Part-CAMO", "Part-CAMO"),
                    ("Part-145", "Part-145"),
                ],
                default="Part-CAO",
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="organisation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("privileges__len__gte", 1),
                        models.Q(("approval_type", "Part-CAO"), _negated=True),
                        _connector="OR",
                    ),
                    ("approval_type__in", ["Part-CAO", "Part-CAMO", "Part-145"]),
                    (
                        "privileges__contained_by",
                        [
                            "Maintenance",
                            "Continuing Airworthiness Management",
                            "Airworthiness Review",
                            "Permit to Fly",
                        ],
                    ),
                ),
                name="organisation_has_known_privileges",
            ),
        ),
        migrations.AddField(
            model_name="approval",
            name="organisation",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="approvals",
                to="organisations.organisation",
            ),
        ),
        migrations.AddConstraint(
            model_name="approval",
            constraint=models.UniqueConstraint(
                fields=("organisation", "approval"), name="approval_held_once"
            ),
        ),
        migrations.AddConstraint(
            model_name="approval",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("approval__in", ["Part-CAO", "Part-CAMO", "Part-145"]),
                    models.Q(("reference", ""), _negated=True),
                ),
                name="approval_is_known_and_has_its_reference",
            ),
        ),
        migrations.RunSQL(*sql.protect_record_table("organisations_approval")),
        # An organisation set up before this is given the record of its approval.
        migrations.RunSQL(
            sql.for_each_organisation(APPROVAL_FOR_EACH_ORGANISATION), migrations.RunSQL.noop
        ),
    ]
