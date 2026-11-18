"""Aircraft, their counters, and dated entries of hours and cycles (REQ-020 to REQ-028)."""

from typing import Any

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.history.models import Record, RecordsAreNeverDeletedError
from airworthiness_plus.organisations.models import Organisation
from airworthiness_rules.intervals import Reading


class Regime(models.TextChoices):
    """Which regime the aircraft is under (Decisions.md, National Regime)."""

    PART_21 = "Part 21", "Part 21"
    NON_PART_21 = "Non-Part 21", "Non-Part 21"


class Status(models.TextChoices):
    """Aircraft status (Decisions.md, Interface)."""

    SERVICEABLE = "Serviceable", "Serviceable"
    UNSERVICEABLE = "Unserviceable", "Unserviceable"


class Stage(models.TextChoices):
    """Whether the aircraft is under management or still being transferred in (REQ-027)."""

    FLEET = "Fleet", "Fleet"
    TRANSFER_IN = "Transfer In", "Transfer In"


class Aircraft(Record):
    """One aircraft (REQ-020).

    The type rating is the text of the SRG1782 entry, stored and shown
    exactly as given, never re-cased or shortened (REQ-021).
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    registration = models.CharField("Aircraft Registration", max_length=10)
    type_rating = models.CharField("Type Rating", max_length=200)
    serial_number = models.CharField("Serial Number", max_length=60, blank=True)
    owner = models.CharField("Owned By", max_length=200)
    regime = models.CharField("Regime", max_length=20, choices=Regime.choices)
    status = models.CharField(
        "Status", max_length=20, choices=Status.choices, default=Status.SERVICEABLE
    )
    unserviceable_reason = models.CharField("Reason", max_length=200, blank=True)
    unserviceable_since = models.DateField("Unserviceable Since", null=True, blank=True)
    stage = models.CharField("Stage", max_length=20, choices=Stage.choices, default=Stage.FLEET)
    records_received = models.PositiveSmallIntegerField("Records Received", null=True, blank=True)
    records_expected = models.PositiveSmallIntegerField("Records Expected", null=True, blank=True)

    class Meta:
        ordering = ["registration"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "registration"],
                name="aircraft_one_record_for_each_registration",
            ),
            models.CheckConstraint(
                condition=Q(regime__in=Regime.values)
                & Q(status__in=Status.values)
                & Q(stage__in=Stage.values),
                name="aircraft_has_known_regime_status_and_stage",
            ),
            # REQ-023: Unserviceable carries a reason and a date; Serviceable neither.
            models.CheckConstraint(
                condition=Q(
                    status=Status.SERVICEABLE,
                    unserviceable_reason="",
                    unserviceable_since__isnull=True,
                )
                | (
                    Q(status=Status.UNSERVICEABLE, unserviceable_since__isnull=False)
                    & ~Q(unserviceable_reason="")
                ),
                name="aircraft_unserviceable_has_a_reason_and_a_date",
            ),
            # REQ-027: a transfer counts the records received against those expected.
            models.CheckConstraint(
                condition=Q(
                    stage=Stage.FLEET,
                    records_received__isnull=True,
                    records_expected__isnull=True,
                )
                | Q(
                    stage=Stage.TRANSFER_IN,
                    records_expected__gte=1,
                    records_received__lte=F("records_expected"),
                ),
                name="aircraft_transfer_counts_its_records",
            ),
        ]

    def __str__(self) -> str:
        return self.registration

    @property
    def calculations_supported(self) -> bool:
        """Return whether due items are calculated for this aircraft (REQ-022, REQ-027).

        The slice calculates for Part 21 aircraft under Part-ML only, and
        only once an aircraft's records are complete and it is in the Fleet.
        """
        return self.regime == Regime.PART_21 and self.stage == Stage.FLEET


class CounterKind(models.TextChoices):
    """What a counter counts for (REQ-020, REQ-059)."""

    AIRFRAME = "Airframe", "Airframe"
    ENGINE = "Engine", "Engine"
    PROPELLER = "Propeller", "Propeller"


class Counter(Record):
    """Something that accumulates hours and cycles: the airframe, an engine or a propeller."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="counters")
    kind = models.CharField("Counter", max_length=20, choices=CounterKind.choices)
    position = models.CharField("Position", max_length=40, blank=True)
    serial_number = models.CharField("Serial Number", max_length=60, blank=True)

    class Meta:
        ordering = ["kind", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["aircraft", "kind", "position"],
                name="counter_one_for_each_position",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=CounterKind.values), name="counter_has_a_known_kind"
            ),
            # The airframe is one counter with no position; an engine or a
            # propeller is named by its position.
            models.CheckConstraint(
                condition=Q(kind=CounterKind.AIRFRAME, position="")
                | (~Q(kind=CounterKind.AIRFRAME) & ~Q(position="")),
                name="counter_airframe_has_no_position_and_others_have_one",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.position}".strip()


class UtilisationEntry(Record):
    """Total hours and cycles of a counter on a date (REQ-024).

    An entry is never changed. A wrong entry is superseded by a new one and
    stays in the record (REQ-025). The database gives the application no
    right to update this table.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    counter = models.ForeignKey(Counter, on_delete=models.PROTECT, related_name="entries")
    dated = models.DateField("Date")
    hours = models.DecimalField("Hours", max_digits=8, decimal_places=1)
    cycles = models.PositiveIntegerField("Cycles")
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by"
    )
    confirmed_unusual = models.BooleanField(default=False)

    class Meta:
        ordering = ["dated", "hours", "cycles"]
        constraints = [
            models.CheckConstraint(
                condition=Q(hours__gte=0), name="utilisation_hours_not_below_zero"
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the entry. An entry that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("An entry is superseded, never changed")
        super().save(*args, **kwargs)

    @property
    def reading(self) -> Reading:
        """Return the entry in the form the calculation rules take."""
        return Reading(self.dated, self.hours, self.cycles)
