"""Maintenance work packages and their work cards (REQ-320 to REQ-323)."""

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts.models import Outcome, WorkOrder
from airworthiness_plus.defects.models import Defect
from airworthiness_plus.directives.models import Applicability
from airworthiness_plus.history.models import Record
from airworthiness_plus.maintenance_data.models import DataSet, Revision
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.programme.models import Task, WorkDone
from airworthiness_plus.releases.models import Release


class WorkPackage(Record):
    """Planned maintenance on one aircraft, under an agreed written order at issue."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="work_packages")
    order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT, null=True, blank=True, related_name="packages"
    )
    defect = models.ForeignKey(
        Defect, on_delete=models.PROTECT, null=True, blank=True, related_name="work_packages"
    )
    reference = models.CharField("Reference", max_length=40)
    title = models.CharField("Work", max_length=200)
    location = models.CharField("Location", max_length=100)
    starts_on = models.DateField("Planned Start")
    ends_on = models.DateField("Planned End")
    issued_on = models.DateField("Issued", null=True, blank=True)
    released_on = models.DateField("Released", null=True, blank=True)
    release = models.OneToOneField(
        Release, on_delete=models.PROTECT, null=True, related_name="work_package"
    )
    verification = models.CharField("General Verification Evidence", max_length=200, blank=True)

    class Meta:
        ordering = ["-starts_on", "reference"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "reference"], name="work_package_unique_reference"
            ),
            models.CheckConstraint(
                condition=Q(ends_on__gte=F("starts_on")) & ~Q(reference="") & ~Q(title=""),
                name="work_package_scope_and_planned_dates",
            ),
            models.CheckConstraint(
                condition=Q(issued_on__isnull=True) | Q(order__isnull=False),
                name="work_package_issued_with_order",
            ),
            models.CheckConstraint(
                condition=Q(released_on__isnull=True, release__isnull=True, verification="")
                | (
                    Q(
                        released_on__gte=F("issued_on"),
                        issued_on__isnull=False,
                        release__isnull=False,
                    )
                    & ~Q(verification="")
                ),
                name="work_package_release_has_verification",
            ),
        ]

    def __str__(self) -> str:
        return self.reference

    @property
    def status(self) -> str:
        if self.released_on is not None:
            return "Released"
        if (
            self.order_id is not None
            and self.order is not None
            and self.order.outcome == Outcome.WITHDRAWN
        ):
            return "Work Order Withdrawn"
        if self.issued_on is None:
            return "Draft"
        if any(card.completed_on is not None for card in self.cards.all()):
            return "In Work"
        return "Issued"


class WorkCard(Record):
    """A planned task, its data at issue and its evidence before release."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    package = models.ForeignKey(WorkPackage, on_delete=models.PROTECT, related_name="cards")
    title = models.CharField("Task", max_length=200)
    data_set = models.ForeignKey(DataSet, on_delete=models.PROTECT, related_name="+")
    revision = models.ForeignKey(Revision, on_delete=models.PROTECT, null=True, related_name="+")
    issue_check_due = models.DateField("Amendment Check Due at Issue", null=True)
    performed_revision = models.ForeignKey(
        Revision, on_delete=models.PROTECT, null=True, related_name="+"
    )
    instruction = models.CharField("Instruction Reference", max_length=200)
    planned_hours = models.DecimalField("Planned Hours", max_digits=6, decimal_places=1)
    inspection_hours = models.DecimalField(
        "Planned Inspection Hours", max_digits=6, decimal_places=1, default=0
    )
    critical = models.BooleanField("Critical Task", default=False)
    task = models.ForeignKey(
        Task, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    directive = models.ForeignKey(
        Applicability, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    performed_by = models.ForeignKey(Person, on_delete=models.PROTECT, null=True, related_name="+")
    supervised_by = models.ForeignKey(Person, on_delete=models.PROTECT, null=True, related_name="+")
    completed_on = models.DateField("Completed", null=True)
    sign_off_reference = models.CharField("Signed Work Evidence", max_length=200, blank=True)
    hours = models.DecimalField("Counter Hours", max_digits=8, decimal_places=1, null=True)
    cycles = models.PositiveIntegerField("Counter Cycles", null=True)
    inspector = models.ForeignKey(Person, on_delete=models.PROTECT, null=True, related_name="+")
    inspected_on = models.DateField("Inspected", null=True)
    qualification = models.CharField("Inspector Qualification Evidence", max_length=200, blank=True)
    inspection_evidence = models.CharField(
        "Satisfactory Inspection Evidence", max_length=500, blank=True
    )
    work = models.OneToOneField(
        WorkDone, on_delete=models.PROTECT, null=True, related_name="work_card"
    )

    class Meta:
        ordering = ["package", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(task__isnull=True) | Q(directive__isnull=True))
                & Q(planned_hours__gt=0, inspection_hours__gte=0)
                & (Q(critical=True) | Q(inspection_hours=0))
                & ~Q(title="")
                & ~Q(instruction=""),
                name="work_card_has_one_scope_and_valid_hours",
            ),
            models.CheckConstraint(
                condition=Q(
                    completed_on__isnull=True,
                    performed_by__isnull=True,
                    performed_revision__isnull=True,
                    supervised_by__isnull=True,
                    sign_off_reference="",
                    hours__isnull=True,
                    cycles__isnull=True,
                )
                | (
                    Q(
                        completed_on__isnull=False,
                        performed_by__isnull=False,
                        performed_revision__isnull=False,
                        hours__gte=0,
                        hours__isnull=False,
                        cycles__isnull=False,
                        revision__isnull=False,
                    )
                    & ~Q(sign_off_reference="")
                    & (Q(supervised_by__isnull=True) | ~Q(supervised_by=F("performed_by")))
                ),
                name="work_card_completion_has_signed_evidence",
            ),
            models.CheckConstraint(
                condition=Q(
                    inspector__isnull=True,
                    inspected_on__isnull=True,
                    qualification="",
                    inspection_evidence="",
                )
                | (
                    Q(
                        critical=True,
                        inspector__isnull=False,
                        inspected_on__isnull=False,
                        completed_on__isnull=False,
                        inspected_on__gte=F("completed_on"),
                    )
                    & ~Q(inspector=F("performed_by"))
                    & (Q(supervised_by__isnull=True) | ~Q(inspector=F("supervised_by")))
                    & ~Q(qualification="")
                    & ~Q(inspection_evidence="")
                ),
                name="work_card_inspection_is_independent_and_evidenced",
            ),
            models.CheckConstraint(
                condition=Q(work__isnull=True)
                | (
                    Q(completed_on__isnull=False)
                    & (Q(critical=False) | Q(inspected_on__isnull=False))
                ),
                name="work_card_evidence_before_recording_work",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def signed(self) -> bool:
        return self.completed_on is not None and (
            not self.critical or self.inspected_on is not None
        )


class WorkCardAttestation(Record):
    """The synthetic actor's explicit consent and the exact evidence archived."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    card = models.OneToOneField(WorkCard, on_delete=models.PROTECT, related_name="attestation")
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    authorisation = models.ForeignKey(
        "people.MaintenanceAuthorisation", on_delete=models.PROTECT, related_name="+"
    )
    evidence = models.TextField()
    sha256 = models.CharField(max_length=64)
