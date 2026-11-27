"""The transfer in of an aircraft, its positions and its baseline (REQ-267 to REQ-279)."""

from typing import Any

from django.db import models
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components.models import Component
from airworthiness_plus.history.models import Record, RecordsAreNeverDeletedError
from airworthiness_plus.modifications.models import Change
from airworthiness_plus.organisations.models import Organisation

# The ten items of the Transfers board, in its order: the item and what it holds.
TRANSFER_ITEMS: tuple[tuple[str, str], ...] = (
    ("Type Within Scope of Approval", "The Type Rating of the Aircraft"),
    ("Management Contract", "Signed With the Owner"),
    ("Import Checks", "Where the Aircraft Comes From Another Register"),
    ("Records Handover Plan", "Agreed With the Previous Organisation"),
    ("Records Received and Checked", "Every Record Expected"),
    ("Continuing Airworthiness Records Review", "By Whom"),
    ("Records Entered", "Configuration Baseline, Directives and Life Limits"),
    ("Maintenance Programme", "Owner Declared or Organisation Approved"),
    ("Bridging Check", "With Next 100-Hour Check if Programme Changes"),
    ("Exposition Scope of Work", "Updated on Completion"),
)

CONTRACT, RECORDS, ENTERED, PROGRAMME = 2, 5, 7, 8
"""The items that the records themselves answer."""

MAY_NOT_APPLY = frozenset({3, 4, 9, 10})
"""Ours: the items that may be recorded as Not Applicable, with the reason."""


class ItemState(models.TextChoices):
    """Where one item of a transfer stands."""

    OPEN = "Open", "Open"
    IN_PROGRESS = "In Progress", "In Progress"
    COMPLETE = "Complete", "Complete"
    NOT_APPLICABLE = "Not Applicable", "Not Applicable"


DONE = (ItemState.COMPLETE, ItemState.NOT_APPLICABLE)


class Transfer(Record):
    """The transfer in of one aircraft: the day it started (REQ-267). Never changed."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.OneToOneField(Aircraft, on_delete=models.PROTECT, related_name="transfer")
    started_on = models.DateField("Started")

    def __str__(self) -> str:
        return f"Transfer In, {self.aircraft_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the transfer. One that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("A transfer is added, never changed")
        super().save(*args, **kwargs)


class TransferItem(Record):
    """One of the ten items of a transfer in, with where it stands and a note (REQ-268)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    transfer = models.ForeignKey(Transfer, on_delete=models.PROTECT, related_name="items")
    number = models.PositiveSmallIntegerField("Item")
    state = models.CharField(
        "State", max_length=20, choices=ItemState.choices, default=ItemState.OPEN
    )
    note = models.CharField("Note", max_length=200, blank=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["transfer", "number"], name="transfer_item_one_of_each_number"
            ),
            models.CheckConstraint(
                condition=Q(number__gte=1, number__lte=len(TRANSFER_ITEMS))
                & Q(state__in=ItemState.values),
                name="transfer_item_is_one_of_the_ten_in_a_known_state",
            ),
            # Not Applicable only where it may be, and with the reason.
            models.CheckConstraint(
                condition=~Q(state=ItemState.NOT_APPLICABLE)
                | (Q(number__in=sorted(MAY_NOT_APPLY)) & ~Q(note="")),
                name="transfer_item_not_applicable_where_it_may_be_with_the_reason",
            ),
        ]

    def __str__(self) -> str:
        return self.label

    @property
    def label(self) -> str:
        """Return the item as the Transfers board names it."""
        return TRANSFER_ITEMS[self.number - 1][0]

    @property
    def holds(self) -> str:
        """Return what the item holds, as the board writes under an open item."""
        return TRANSFER_ITEMS[self.number - 1][1]

    @property
    def done(self) -> bool:
        """Return whether the item is complete, or does not apply."""
        return self.state in DONE


class Product(models.TextChoices):
    """The products of an aircraft, as the Set Up Configuration board lists them."""

    AIRFRAME = "Airframe", "Airframe"
    ENGINE = "Engine", "Engine"
    PROPELLER = "Propeller", "Propeller"


class Position(Record):
    """One position of an aircraft's configuration, and what is recorded as fitted (REQ-270)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="positions")
    product = models.CharField("Product", max_length=20, choices=Product.choices)
    chapter = models.PositiveSmallIntegerField("Chapter")
    name = models.CharField("Position", max_length=100)
    required = models.BooleanField("Required Equipment", default=False)
    tracked = models.BooleanField("Tracked by Serial Number", default=False)
    # The engine or the propeller itself: a major item of the Set Up Configuration board.
    major = models.BooleanField("Major Item", default=False)

    recorded = models.BooleanField("Recorded", default=False)
    part_number = models.CharField("Part Number", max_length=60, blank=True)
    serial_number = models.CharField("Serial Number", max_length=60, blank=True)
    source = models.CharField("Source", max_length=200, blank=True)
    # Not in the allowed configuration without a recorded change.
    needs_change = models.BooleanField("Needs a Recorded Change", default=False)
    change = models.ForeignKey(
        Change, on_delete=models.PROTECT, null=True, blank=True, related_name="positions"
    )
    component = models.ForeignKey(
        Component, on_delete=models.PROTECT, null=True, blank=True, related_name="positions"
    )

    class Meta:
        ordering = ["product", "chapter", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["aircraft", "product", "chapter", "name"],
                name="position_recorded_once_for_an_aircraft",
            ),
            models.CheckConstraint(
                condition=~Q(name="")
                & Q(product__in=Product.values)
                & Q(chapter__gte=1, chapter__lte=99),
                name="position_has_a_name_a_product_and_a_chapter",
            ),
            # What is recorded says where it was read; what is not recorded says nothing.
            models.CheckConstraint(
                condition=(Q(recorded=True) & ~Q(source=""))
                | Q(
                    recorded=False,
                    serial_number="",
                    needs_change=False,
                    change__isnull=True,
                    component__isnull=True,
                ),
                name="position_recorded_says_its_source",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def path(self) -> str:
        """Return where the position is: Engine, Chapter 74."""
        return f"{self.product}, Chapter {self.chapter}"

    @property
    def status(self) -> str:
        """Return Recorded, Not Recorded or Needs a Recorded Change, as the board does."""
        if not self.recorded:
            return "Not Recorded"
        if self.needs_change and (self.change is None or self.change.embodied_on is None):
            return "Needs a Recorded Change"
        return "Recorded"


class Baseline(Record):
    """A configuration baseline, signed (REQ-274). Added whole and never changed.

    What it shows is kept as it stood on the day it was signed: the
    database writes who signed, the aircraft, the organisation and every
    position and change, whatever the application sends.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="baselines")
    signed_on = models.DateField("Baseline Date")
    signed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    signed_by_name = models.CharField(max_length=200, blank=True)
    organisation_name = models.CharField(max_length=200, blank=True)
    aircraft_registration = models.CharField(max_length=10, blank=True)
    type_rating = models.CharField(max_length=200, blank=True)
    serial_number = models.CharField(max_length=60, blank=True)
    # Each position and each change of the aircraft on that day, as JSON.
    positions = models.TextField(blank=True)
    changes = models.TextField(blank=True)

    class Meta:
        ordering = ["signed_on", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["aircraft", "signed_on"], name="baseline_one_for_an_aircraft_on_a_day"
            ),
        ]

    def __str__(self) -> str:
        return f"Configuration Baseline, {self.aircraft_registration}, {self.signed_on}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the baseline. One that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("A signed baseline is never changed")
        super().save(*args, **kwargs)
