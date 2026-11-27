"""A record for each person of an organisation (REQ-203, REQ-204).

Decisions.md, Canvas Build, decision 2: everyone in an organisation has a
person record. A person who uses the system also has a sign-in, linked to
that record. Not everyone signs in: certifying staff, mentors, assessors,
contracted engineers and auditors are people of the organisation too.
"""

from datetime import date

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation


class StaffGroup(models.TextChoices):
    """The groups of the Staff board."""

    MANAGEMENT = "Management", "Management"
    CERTIFYING = "Certifying Staff", "Certifying Staff"
    REVIEW = "Airworthiness Review Staff", "Airworthiness Review Staff"
    OTHER = "Other Staff", "Other Staff"


class Employment(models.TextChoices):
    """Whether a person is employed or contracted (Staff board)."""

    EMPLOYED = "Employed", "Employed"
    CONTRACTED = "Contracted", "Contracted"


class Person(Record):
    """One person of an organisation.

    A person who leaves is kept, with the day they left (REQ-131). The
    sign-in, where there is one, is the person's own and no other's.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    user = models.OneToOneField(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="person"
    )
    full_name = models.CharField("Name", max_length=200)
    role = models.CharField("Role", max_length=100, blank=True)
    staff_group = models.CharField(
        "Staff Group", max_length=40, choices=StaffGroup.choices, default=StaffGroup.OTHER
    )
    reports_to = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="reports"
    )
    employment = models.CharField(
        "Employment", max_length=20, choices=Employment.choices, default=Employment.EMPLOYED
    )
    licence = models.CharField("Licence", max_length=100, blank=True)
    joined_on = models.DateField("Joined", null=True, blank=True)
    left_on = models.DateField("Left", null=True, blank=True)

    class Meta:
        ordering = ["full_name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(staff_group__in=StaffGroup.values)
                & Q(employment__in=Employment.values)
                & ~Q(full_name=""),
                name="person_has_a_name_a_known_group_and_employment",
            ),
            models.CheckConstraint(
                condition=Q(reports_to__isnull=True) | ~Q(reports_to=F("id")),
                name="person_does_not_report_to_themselves",
            ),
            models.CheckConstraint(
                condition=Q(joined_on__isnull=True)
                | Q(left_on__isnull=True)
                | Q(left_on__gte=F("joined_on")),
                name="person_did_not_leave_before_joining",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name


class MaintenanceAuthorisation(Record):
    """A record of an organisation's existing authorisation for certifying staff (REQ-297)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    person = models.ForeignKey(
        Person, on_delete=models.PROTECT, related_name="maintenance_authorisations"
    )
    reference = models.CharField("Authorisation Reference", max_length=80)
    scope = models.CharField("Scope and Limitations", max_length=400)
    valid_from = models.DateField("Valid From")
    valid_to = models.DateField("Valid To", null=True, blank=True)

    class Meta:
        ordering = ["person__full_name", "-valid_from", "reference", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(reference="") & ~Q(scope=""),
                name="maintenance_authorisation_has_reference_and_scope",
            ),
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_to__gte=F("valid_from")),
                name="maintenance_authorisation_dates_in_order",
            ),
            models.UniqueConstraint(
                fields=["person", "reference", "valid_from"],
                name="maintenance_authorisation_recorded_once",
            ),
        ]

    def term_on(self, on: date) -> str:
        """Distinguish the terms of the evidence from assessed experience."""
        if on < self.valid_from:
            return "Not Yet In Force"
        if self.valid_to is not None and self.valid_to < on:
            return "Ended"
        return "Within Recorded Dates"


class RecurrentTraining(Record):
    """Documented completion and the renewal date set by the organisation (REQ-299)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="recurrent_training")
    subject = models.CharField("Training Subject", max_length=160)
    evidence_reference = models.CharField("Evidence Reference", max_length=160)
    completed_on = models.DateField("Completed On")
    due_on = models.DateField("Renewal Due On", null=True, blank=True)

    class Meta:
        ordering = ["-completed_on", "subject", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(subject="") & ~Q(evidence_reference=""),
                name="recurrent_training_has_subject_and_evidence",
            ),
            models.CheckConstraint(
                condition=Q(due_on__isnull=True) | Q(due_on__gt=F("completed_on")),
                name="recurrent_training_due_after_completion",
            ),
            models.UniqueConstraint(
                F("person"),
                Lower("subject"),
                F("completed_on"),
                name="recurrent_training_completion_recorded_once",
            ),
        ]


class ExperienceKind(models.TextChoices):
    MAINTENANCE = "Maintenance", "Maintenance"
    SUBSTITUTE = "Substitute", "Permitted Substitute Activity"
    EMPLOYMENT = "Employment", "Approved Maintenance Employment"


class ExperienceEvidence(Record):
    """Assessed maintenance experience for the stated authorisation scope (REQ-301)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    authorisation = models.ForeignKey(
        MaintenanceAuthorisation, on_delete=models.PROTECT, related_name="experience_evidence"
    )
    kind = models.CharField("Evidence Type", max_length=20, choices=ExperienceKind.choices)
    evidence_reference = models.CharField("Evidence Reference", max_length=160)
    qualification_basis = models.CharField("Basis for Counting the Experience", max_length=500)
    starts_on = models.DateField("Work Date or First Day of Employment")
    ends_on = models.DateField("Last Day of Employment", null=True, blank=True)
    days = models.DecimalField(
        "Days Credited", max_digits=3, decimal_places=2, null=True, blank=True
    )
    aircraft_type = models.CharField("Aircraft Type", max_length=150, blank=True)
    aircraft_registration = models.CharField("Aircraft Registration", max_length=16, blank=True)
    licence_subcategory = models.CharField(
        "Licence Category or Subcategory", max_length=30, blank=True
    )

    class Meta:
        ordering = ["-starts_on", "evidence_reference", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["authorisation", "evidence_reference"],
                name="experience_evidence_reference_used_once",
            ),
            models.CheckConstraint(
                condition=~Q(evidence_reference="") & ~Q(qualification_basis=""),
                name="experience_evidence_has_reference_and_basis",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        kind=ExperienceKind.EMPLOYMENT,
                        ends_on__gte=F("starts_on"),
                        ends_on__isnull=False,
                        days__isnull=True,
                    )
                    & Q(aircraft_type="", aircraft_registration="", licence_subcategory="")
                )
                | (
                    Q(
                        kind__in=[ExperienceKind.MAINTENANCE, ExperienceKind.SUBSTITUTE],
                        ends_on__isnull=True,
                        days__isnull=False,
                        days__gt=0,
                        days__lte=1,
                    )
                    & ~Q(aircraft_type="")
                    & (Q(kind=ExperienceKind.SUBSTITUTE) | ~Q(aircraft_registration=""))
                    & ~Q(licence_subcategory="")
                ),
                name="experience_evidence_matches_its_type",
            ),
        ]


class ExperienceWithdrawal(Record):
    """A withdrawal removes an assessment from duration while retaining its evidence."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    evidence = models.OneToOneField(
        ExperienceEvidence, on_delete=models.PROTECT, related_name="withdrawal"
    )
    reason = models.CharField("Reason", max_length=400)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(reason=""), name="experience_withdrawal_has_reason")
        ]
