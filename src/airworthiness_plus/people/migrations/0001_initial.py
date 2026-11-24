"""A record for each person of an organisation, and one for each sign-in (REQ-203, REQ-204)."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from airworthiness_plus.history import sql
from airworthiness_plus.people import sql as people_sql


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organisations", "0006_approvals_held"),
        ("accounts", "0007_first_password_and_code"),
        ("history", "0004_hash_algorithm"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Person",
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
                ("full_name", models.CharField(max_length=200, verbose_name="Name")),
                (
                    "role",
                    models.CharField(blank=True, max_length=100, verbose_name="Role"),
                ),
                (
                    "staff_group",
                    models.CharField(
                        choices=[
                            ("Management", "Management"),
                            ("Certifying Staff", "Certifying Staff"),
                            (
                                "Airworthiness Review Staff",
                                "Airworthiness Review Staff",
                            ),
                            ("Other Staff", "Other Staff"),
                        ],
                        default="Other Staff",
                        max_length=40,
                        verbose_name="Staff Group",
                    ),
                ),
                (
                    "employment",
                    models.CharField(
                        choices=[
                            ("Employed", "Employed"),
                            ("Contracted", "Contracted"),
                        ],
                        default="Employed",
                        max_length=20,
                        verbose_name="Employment",
                    ),
                ),
                (
                    "licence",
                    models.CharField(blank=True, max_length=100, verbose_name="Licence"),
                ),
                (
                    "joined_on",
                    models.DateField(blank=True, null=True, verbose_name="Joined"),
                ),
                (
                    "left_on",
                    models.DateField(blank=True, null=True, verbose_name="Left"),
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
                    "reports_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reports",
                        to="people.person",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="person",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["full_name", "id"],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            (
                                "staff_group__in",
                                [
                                    "Management",
                                    "Certifying Staff",
                                    "Airworthiness Review Staff",
                                    "Other Staff",
                                ],
                            ),
                            ("employment__in", ["Employed", "Contracted"]),
                            models.Q(("full_name", ""), _negated=True),
                        ),
                        name="person_has_a_name_a_known_group_and_employment",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("reports_to__isnull", True),
                            models.Q(("reports_to", models.F("id")), _negated=True),
                            _connector="OR",
                        ),
                        name="person_does_not_report_to_themselves",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("joined_on__isnull", True),
                            ("left_on__isnull", True),
                            ("left_on__gte", models.F("joined_on")),
                            _connector="OR",
                        ),
                        name="person_did_not_leave_before_joining",
                    ),
                ],
            },
        ),
        migrations.RunSQL(
            *sql.protect_record_table(
                "people_person",
                parents=(("user_id", "accounts_user"), ("reports_to_id", "people_person")),
            )
        ),
        # A sign-in from before person records is given its person.
        migrations.RunSQL(
            sql.for_each_organisation(people_sql.PERSON_FOR_EACH_USER), migrations.RunSQL.noop
        ),
        # From here on the database refuses a sign-in that has no person (REQ-204).
        migrations.RunSQL(people_sql.CREATE_USER_HAS_A_PERSON, people_sql.DROP_USER_HAS_A_PERSON),
    ]
