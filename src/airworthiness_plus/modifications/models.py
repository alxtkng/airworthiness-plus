"""Service bulletin decisions, changes and repairs, and weighings (REQ-249 to REQ-259)."""

from typing import Any

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Record, RecordsAreNeverDeletedError
from airworthiness_plus.organisations.models import Organisation
from airworthiness_rules.mass import MOST_MASS


class Classification(models.TextChoices):
    """How the design approval holder classes a service bulletin, as the board writes it."""

    RECOMMENDED = "Recommended", "Recommended"
    OPTIONAL = "Optional", "Optional"


class OwnerDecision(models.TextChoices):
    """What the owner has decided of a service bulletin."""

    AWAITING = "Awaiting Owner", "Awaiting Owner"
    ACCEPTED = "Accepted", "Accepted"
    DECLINED = "Declined", "Declined"


class Bulletin(Record):
    """The owner's decision on one service bulletin for one aircraft (REQ-249).

    ML.A.305(d): the records hold the current status of the design approval
    holder's maintenance recommendations. The decision is recorded once
    and never altered.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="bulletins")
    title = models.CharField("Bulletin", max_length=200)
    reference = models.CharField("Reference", max_length=100)
    classification = models.CharField(
        "Classification", max_length=20, choices=Classification.choices
    )
    sent_on = models.DateField("Sent to the Owner")
    reminder_on = models.DateField("Reminder", null=True, blank=True)
    decision = models.CharField(
        "Owner Decision",
        max_length=20,
        choices=OwnerDecision.choices,
        default=OwnerDecision.AWAITING,
    )
    # What was decided: Every 50-Hour Check, or why it was declined.
    detail = models.CharField("Decision in Detail", max_length=200, blank=True)
    decided_on = models.DateField("Recorded", null=True, blank=True)

    class Meta:
        ordering = ["aircraft__registration", "sent_on", "title", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title="")
                & ~Q(reference="")
                & Q(classification__in=Classification.values)
                & (Q(reminder_on__isnull=True) | Q(reminder_on__gte=F("sent_on"))),
                name="bulletin_has_a_title_a_reference_and_a_classification",
            ),
            models.CheckConstraint(
                condition=Q(decision=OwnerDecision.AWAITING, detail="", decided_on__isnull=True)
                | (
                    Q(
                        decision__in=[OwnerDecision.ACCEPTED, OwnerDecision.DECLINED],
                        decided_on__isnull=False,
                        decided_on__gte=F("sent_on"),
                    )
                    & ~Q(detail="")
                ),
                name="bulletin_decision_is_whole_or_awaited",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def awaiting(self) -> bool:
        """Return whether the owner has still to decide."""
        return self.decision == OwnerDecision.AWAITING


class Route(models.TextChoices):
    """The approval route of a change or repair, as the Modifications board writes them.

    Standard Repair is added from ML.A.304, which names point 21.A.431B
    beside point 21.A.90B.
    """

    STANDARD_CHANGE = "Standard Change", "Standard Change"
    STANDARD_REPAIR = "Standard Repair", "Standard Repair"
    MINOR_CHANGE = "Minor Change", "Minor Change"
    STRUCTURAL_REPAIR_DATA = (
        "Manufacturer's Structural Repair Data",
        "Manufacturer's Structural Repair Data",
    )
    OTHER = "Other Approved Data", "Other Approved Data"
    SAME_PART = "Maintenance, Same Part Number", "Maintenance, Same Part Number"


class Data(models.TextChoices):
    """The data a modification or repair is carried out with, ML.A.304."""

    AUTHORITY = (
        "Approved by the Civil Aviation Authority",
        "Approved by the Civil Aviation Authority",
    )
    DESIGN_ORGANISATION = (
        "Approved by a Design Organisation",
        "Approved by a Design Organisation",
    )
    STANDARD = (
        "Contained in the Requirements of Point 21.A.90B or 21.A.431B",
        "Contained in the Requirements of Point 21.A.90B or 21.A.431B",
    )


STANDARD_ROUTES = (Route.STANDARD_CHANGE, Route.STANDARD_REPAIR)
APPROVED_ROUTES = (Route.MINOR_CHANGE, Route.STRUCTURAL_REPAIR_DATA, Route.OTHER)


class Change(Record):
    """One change or repair embodied on an aircraft, or in progress (REQ-251).

    What was recorded is never altered. The day it was embodied is added
    once, where it was recorded as in progress.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="changes")
    title = models.CharField("Change or Repair", max_length=200)
    route = models.CharField("Approval Route", max_length=60, choices=Route.choices)
    data = models.CharField("Data", max_length=80, choices=Data.choices, blank=True)
    reference = models.CharField("Reference", max_length=100, blank=True)
    mass_effect = models.DecimalField("Mass Effect, Kilograms", max_digits=4, decimal_places=1)
    embodied_on = models.DateField("Embodied", null=True, blank=True)

    class Meta:
        ordering = ["aircraft__registration", "embodied_on", "title", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title="")
                & Q(route__in=Route.values)
                & Q(mass_effect__gte=-MOST_MASS, mass_effect__lte=MOST_MASS),
                name="change_has_a_title_a_route_and_a_mass_within_bounds",
            ),
            # ML.A.304: the data fits the route. Maintenance with the same part
            # number is neither a modification nor a repair, and names none.
            models.CheckConstraint(
                condition=Q(route__in=STANDARD_ROUTES, data=Data.STANDARD)
                | Q(route__in=APPROVED_ROUTES, data__in=[Data.AUTHORITY, Data.DESIGN_ORGANISATION])
                | Q(route=Route.SAME_PART, data=""),
                name="change_data_fits_its_route",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def route_text(self) -> str:
        """Return the route with its reference: Standard Change, [Reference]."""
        return f"{self.route}, {self.reference}" if self.reference else str(self.route)


class Weighing(Record):
    """One weighing of an aircraft. Added and never changed (REQ-254)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="weighings")
    weighed_on = models.DateField("Weighed")
    reference = models.CharField("Weighing Report", max_length=100)

    class Meta:
        ordering = ["weighed_on", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["aircraft", "weighed_on"], name="weighing_one_for_an_aircraft_on_a_day"
            ),
            models.CheckConstraint(condition=~Q(reference=""), name="weighing_has_a_report"),
        ]

    def __str__(self) -> str:
        return self.reference

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the weighing. One that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("A weighing is added, never changed")
        super().save(*args, **kwargs)


class WeightSchedule(Record):
    """One issue of an aircraft's weight schedule. Added and never changed (REQ-254)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(
        Aircraft, on_delete=models.PROTECT, related_name="weight_schedules"
    )
    issue = models.PositiveSmallIntegerField("Issue")
    issued_on = models.DateField("Issued")

    class Meta:
        ordering = ["issue", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["aircraft", "issue"], name="weight_schedule_one_of_each_issue"
            ),
            models.CheckConstraint(
                condition=Q(issue__gte=1, issue__lte=9999),
                name="weight_schedule_issue_from_1_to_9999",
            ),
        ]

    def __str__(self) -> str:
        return f"Issue {self.issue}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the issue. One that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("An issue of the schedule is added, never changed")
        super().save(*args, **kwargs)
