"""Contracts with owners, and maintenance work orders (REQ-240 to REQ-249)."""

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.customers.models import Customer
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme.models import WorkDone


class Scope(models.TextChoices):
    """What the owner has contracted the organisation to do."""

    ALL = (
        "All Continuing Airworthiness Management Tasks",
        "All Continuing Airworthiness Management Tasks",
    )
    LIMITED = "Limited Tasks", "Limited Tasks"


class EndReason(models.TextChoices):
    """Why a contract ended (Appendix I to Part-ML)."""

    NON_CONFORMITY = "Non-Conformity With the Contract", "Non-Conformity With the Contract"
    DENOUNCED = "Denounced by Either Party", "Denounced by Either Party"
    OTHER = "Other", "Other"


class Contract(Record):
    """A contract between an owner and the organisation for one aircraft (REQ-240).

    What Appendix I to Part-ML has a contract contain is kept as it stood
    on the day the contract was recorded: the aircraft's registration, type
    and serial number, the owner's name and address, the organisation's
    name, address and approval reference, and the type of operation. The
    database writes what it can read itself and never lets any of it be
    altered. Ending the contract, and telling the Civil Aviation Authority,
    are each recorded once.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="contracts")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="contracts")
    scope = models.CharField("Tasks Contracted", max_length=60, choices=Scope.choices)
    tasks = models.CharField("Limited Tasks", max_length=200, blank=True)
    type_of_operation = models.CharField("Type of Operation", max_length=100)
    owner_address = models.CharField("Address of the Owner", max_length=300)
    signed_on = models.DateField("Signed")

    # As they stood when the contract was recorded, written by the database.
    registration = models.CharField(max_length=10, blank=True)
    type_rating = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=60, blank=True)
    owner_name = models.CharField(max_length=200, blank=True)
    organisation_name = models.CharField(max_length=200, blank=True)
    organisation_address = models.CharField(max_length=300, blank=True)
    organisation_approval_reference = models.CharField(max_length=40, blank=True)

    ended_on = models.DateField("Ended", null=True, blank=True)
    end_reason = models.CharField("Reason", max_length=40, choices=EndReason.choices, blank=True)
    authority_told_on = models.DateField("Civil Aviation Authority Told", null=True, blank=True)

    class Meta:
        ordering = ["signed_on", "id"]
        constraints = [
            # One contract in force for each aircraft.
            models.UniqueConstraint(
                fields=["aircraft"],
                condition=Q(ended_on__isnull=True),
                name="contract_one_in_force_for_each_aircraft",
            ),
            models.CheckConstraint(
                condition=(Q(scope=Scope.ALL, tasks="") | (Q(scope=Scope.LIMITED) & ~Q(tasks="")))
                & ~Q(type_of_operation="")
                & ~Q(owner_address=""),
                name="contract_says_its_tasks_operation_and_owner_address",
            ),
            models.CheckConstraint(
                condition=Q(ended_on__isnull=True, end_reason="", authority_told_on__isnull=True)
                | (
                    Q(
                        ended_on__isnull=False,
                        ended_on__gte=F("signed_on"),
                        end_reason__in=EndReason.values,
                    )
                    & (Q(authority_told_on__isnull=True) | Q(authority_told_on__gte=F("ended_on")))
                ),
                name="contract_ended_has_a_reason_and_is_told_on_or_after",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.registration} {self.signed_on}"

    @property
    def tasks_text(self) -> str:
        """Return what was contracted, as the Contracts board writes it."""
        return self.tasks if self.scope == Scope.LIMITED else str(self.scope)


class OrderedBy(models.TextChoices):
    """Who placed a work order (Contracts board)."""

    OWNER = "Owner", "Owner"
    MANAGER = "Continuing Airworthiness Manager", "Continuing Airworthiness Manager"


class Outcome(models.TextChoices):
    """How a work order was closed."""

    COMPLETED = "Completed", "Completed"
    WITHDRAWN = "Withdrawn", "Withdrawn"


class WorkOrder(Record):
    """A written request for maintenance on one aircraft (REQ-244).

    It sits under the contract in force for the aircraft on the day it was
    agreed, where there is one. The owner's name is kept as it stood,
    written by the database. Closing it is recorded once.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="work_orders")
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, null=True, blank=True, related_name="work_orders"
    )
    work = models.CharField("Work Ordered", max_length=200)
    ordered_by = models.CharField("Ordered By", max_length=40, choices=OrderedBy.choices)
    agreed_on = models.DateField("Agreed")
    # The owner on the day the order was recorded, written by the database.
    owner_name = models.CharField(max_length=200, blank=True)

    closed_on = models.DateField("Closed", null=True, blank=True)
    outcome = models.CharField("Outcome", max_length=20, choices=Outcome.choices, blank=True)
    work_done = models.ForeignKey(
        WorkDone, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["agreed_on", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(work="") & Q(ordered_by__in=OrderedBy.values),
                name="work_order_says_the_work_and_who_ordered_it",
            ),
            models.CheckConstraint(
                condition=Q(closed_on__isnull=True, outcome="", work_done__isnull=True)
                | (
                    Q(
                        closed_on__isnull=False,
                        closed_on__gte=F("agreed_on"),
                        outcome__in=Outcome.values,
                    )
                    & (Q(work_done__isnull=True) | Q(outcome=Outcome.COMPLETED))
                ),
                name="work_order_closed_has_an_outcome",
            ),
        ]

    def __str__(self) -> str:
        return self.work

    @property
    def ordered_by_text(self) -> str:
        """Return who ordered the work: the owner by name, or the manager's role."""
        if self.ordered_by == OrderedBy.OWNER:
            return self.owner_name or str(OrderedBy.OWNER)
        return str(self.ordered_by)
