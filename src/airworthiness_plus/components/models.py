"""Components, their life limits and where each has been fitted (REQ-230 to REQ-239)."""

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation
from airworthiness_rules.components import (
    MOST_CYCLES,
    MOST_HOURS,
    MOST_LIMIT_CYCLES,
    MOST_LIMIT_HOURS,
    MOST_LIMIT_MONTHS,
    MOST_REVIEW_HOURS,
)
from airworthiness_rules.intervals import Interval


class Basis(models.TextChoices):
    """What the limit of a component is.

    The first two are those of ML.A.503. The others are as the Components
    board writes them.
    """

    CERTIFIED = "Certified Life Limit", "Certified Life Limit"
    SERVICE = "Service Life Limit", "Service Life Limit"
    RECOMMENDATION = "Manufacturer Recommendation", "Manufacturer Recommendation"
    DATE = "Date on the Component", "Date on the Component"
    ON_CONDITION = "On Condition", "On Condition"
    NONE = "No Limit Recorded", "No Limit Recorded"


LIFE = (Basis.CERTIFIED, Basis.SERVICE, Basis.RECOMMENDATION)
"""A life in hours, cycles or calendar time, counted since new or overhaul."""

_NO_LIFE = Q(limit_hours__isnull=True, limit_cycles__isnull=True, limit_months__isnull=True)
_NO_DATE = Q(limit_date__isnull=True, date_label="")
_NO_REVIEW = Q(
    review_hours__isnull=True, last_review_hours__isnull=True, last_review_on__isnull=True
)


class Component(Record):
    """One component that is tracked: what it is and the limit it has (REQ-230)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    name = models.CharField("Component", max_length=200)
    part_number = models.CharField("Part Number", max_length=60, blank=True)
    serial_number = models.CharField("Serial Number", max_length=60, blank=True)
    basis = models.CharField("Limit", max_length=40, choices=Basis.choices)
    source = models.CharField("Source of the Limit", max_length=200, blank=True)

    # A life since new or overhaul (ML.A.503: calendar time, flight hours, landings or cycles).
    limit_hours = models.DecimalField(
        "Limit in Hours", max_digits=7, decimal_places=1, null=True, blank=True
    )
    limit_cycles = models.PositiveIntegerField("Limit in Cycles", null=True, blank=True)
    limit_months = models.PositiveSmallIntegerField("Limit in Months", null=True, blank=True)
    # A date printed on the component, such as a battery date.
    limit_date = models.DateField("Date on the Component", null=True, blank=True)
    date_label = models.CharField("What the Date Is", max_length=60, blank=True)
    # On condition: reviewed every so many airframe hours.
    review_hours = models.DecimalField(
        "Reviewed Every, Hours", max_digits=6, decimal_places=1, null=True, blank=True
    )
    last_review_hours = models.DecimalField(
        "Airframe Hours at the Last Review", max_digits=8, decimal_places=1, null=True, blank=True
    )
    last_review_on = models.DateField("Last Reviewed", null=True, blank=True)

    class Meta:
        ordering = ["name", "serial_number", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(name="") & Q(basis__in=Basis.values),
                name="component_has_a_name_and_a_known_limit",
            ),
            # Each kind of limit has its own values and no others.
            models.CheckConstraint(
                condition=(Q(basis__in=LIFE) & ~_NO_LIFE & _NO_DATE & _NO_REVIEW)
                | (
                    Q(basis=Basis.DATE, limit_date__isnull=False)
                    & ~Q(date_label="")
                    & _NO_LIFE
                    & _NO_REVIEW
                )
                | (
                    Q(
                        basis=Basis.ON_CONDITION,
                        review_hours__isnull=False,
                        last_review_hours__isnull=False,
                        last_review_on__isnull=False,
                    )
                    & _NO_LIFE
                    & _NO_DATE
                )
                | (Q(basis=Basis.NONE) & _NO_LIFE & _NO_DATE & _NO_REVIEW),
                name="component_limit_fits_its_kind",
            ),
            models.CheckConstraint(
                condition=(
                    Q(limit_hours__isnull=True)
                    | Q(limit_hours__gt=0, limit_hours__lte=MOST_LIMIT_HOURS)
                )
                & (
                    Q(limit_cycles__isnull=True)
                    | Q(limit_cycles__gte=1, limit_cycles__lte=MOST_LIMIT_CYCLES)
                )
                & (
                    Q(limit_months__isnull=True)
                    | Q(limit_months__gte=1, limit_months__lte=MOST_LIMIT_MONTHS)
                )
                & (
                    Q(review_hours__isnull=True)
                    | Q(review_hours__gt=0, review_hours__lte=MOST_REVIEW_HOURS)
                )
                & (
                    Q(last_review_hours__isnull=True)
                    | Q(last_review_hours__gte=0, last_review_hours__lte=MOST_HOURS)
                ),
                name="component_limits_within_bounds",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def life(self) -> Interval | None:
        """Return the life since new or overhaul, where the limit is one."""
        if self.basis not in LIFE:
            return None
        return Interval(hours=self.limit_hours, cycles=self.limit_cycles, months=self.limit_months)

    @property
    def identity(self) -> str:
        """Return the part number and serial number as the board writes them."""
        parts = []
        if self.part_number:
            parts.append(f"Part Number {self.part_number}")
        if self.serial_number:
            parts.append(f"Serial Number {self.serial_number}")
        return ", ".join(parts)


class Installation(Record):
    """One fitting of a component to an aircraft, and its removal (REQ-231; ML.A.305(e)).

    What was recorded of the fitting is never altered, and the Aircraft
    Registration is kept as it stood: the database writes it. The removal
    is added once; after that nothing of the record changes.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    component = models.ForeignKey(Component, on_delete=models.PROTECT, related_name="installations")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="installations")
    # As it stood on the day the fitting was recorded, written by the database.
    aircraft_registration = models.CharField(max_length=10, blank=True)
    position = models.CharField("Position", max_length=100)
    fitted_on = models.DateField("Fitted")
    airframe_hours_fitted = models.DecimalField(
        "Airframe Hours When Fitted", max_digits=8, decimal_places=1
    )
    airframe_cycles_fitted = models.PositiveIntegerField("Airframe Cycles When Fitted", default=0)
    # The component's own since new or overhaul, when it was fitted.
    hours_at_fitting = models.DecimalField(
        "Hours Since New or Overhaul When Fitted", max_digits=8, decimal_places=1
    )
    cycles_at_fitting = models.PositiveIntegerField(
        "Cycles Since New or Overhaul When Fitted", default=0
    )
    # The day a calendar life runs from: new, or last overhauled.
    life_from = models.DateField("New or Last Overhauled", null=True, blank=True)
    release_document = models.CharField("Release Document", max_length=100, blank=True)

    removed_on = models.DateField("Removed", null=True, blank=True)
    airframe_hours_removed = models.DecimalField(
        "Airframe Hours When Removed", max_digits=8, decimal_places=1, null=True, blank=True
    )
    airframe_cycles_removed = models.PositiveIntegerField(
        "Airframe Cycles When Removed", null=True, blank=True
    )
    removal_reason = models.CharField("Reason for Removal", max_length=200, blank=True)
    sent_to = models.CharField("Sent To", max_length=200, blank=True)
    due_back_on = models.DateField("Due Back", null=True, blank=True)

    class Meta:
        ordering = ["fitted_on", "id"]
        constraints = [
            # A component is fitted in one place at a time.
            models.UniqueConstraint(
                fields=["component"],
                condition=Q(removed_on__isnull=True),
                name="installation_one_at_a_time_for_a_component",
            ),
            models.CheckConstraint(
                condition=~Q(position="")
                & Q(airframe_hours_fitted__gte=0, airframe_hours_fitted__lte=MOST_HOURS)
                & Q(hours_at_fitting__gte=0, hours_at_fitting__lte=MOST_HOURS)
                & Q(airframe_cycles_fitted__lte=MOST_CYCLES, cycles_at_fitting__lte=MOST_CYCLES)
                & (Q(life_from__isnull=True) | Q(life_from__lte=F("fitted_on"))),
                name="installation_fitting_within_bounds",
            ),
            models.CheckConstraint(
                condition=Q(
                    removed_on__isnull=True,
                    airframe_hours_removed__isnull=True,
                    airframe_cycles_removed__isnull=True,
                    removal_reason="",
                    sent_to="",
                    due_back_on__isnull=True,
                )
                | (
                    Q(
                        removed_on__isnull=False,
                        airframe_hours_removed__isnull=False,
                        airframe_cycles_removed__isnull=False,
                        removed_on__gte=F("fitted_on"),
                        airframe_hours_removed__gte=F("airframe_hours_fitted"),
                        airframe_hours_removed__lte=MOST_HOURS,
                        airframe_cycles_removed__gte=F("airframe_cycles_fitted"),
                        airframe_cycles_removed__lte=MOST_CYCLES,
                    )
                    & ~Q(removal_reason="")
                    & (Q(due_back_on__isnull=True) | Q(due_back_on__gte=F("removed_on")))
                ),
                name="installation_removal_is_complete_or_absent",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.component} on {self.aircraft_registration}"

    @property
    def fitted(self) -> bool:
        """Return whether the component is still fitted here."""
        return self.removed_on is None
