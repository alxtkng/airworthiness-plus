"""What can be done with a transfer in, the positions of an aircraft and its baseline.

Views check the role first, then call these. ML.A.305 and ML.A.307, read
in the UK text on 27 November 2026 (Decisions.md, Regulation Facts in
Use): the records of an aircraft are transferred to the organisation that
is contracted to manage it, and hold the current status of its
modifications, repairs and service-life-limited components. The ten items
of a transfer and the six steps of setting up a configuration are the
Transfers and Set Up Configuration boards'; no rule read lists them.
"""

import json
from dataclasses import dataclass
from datetime import date

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Stage
from airworthiness_plus.components import services as component_services
from airworthiness_plus.components.models import Component
from airworthiness_plus.configuration.models import (
    CONTRACT,
    ENTERED,
    MAY_NOT_APPLY,
    PROGRAMME,
    RECORDS,
    TRANSFER_ITEMS,
    Baseline,
    ItemState,
    Position,
    Product,
    Transfer,
    TransferItem,
)
from airworthiness_plus.contracts import services as contract_services
from airworthiness_plus.interface import formatting
from airworthiness_plus.modifications.models import Change
from airworthiness_plus.programme.models import Programme


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


# The transfer in


@transaction.atomic
def start_transfer(aircraft: Aircraft, *, started_on: date | None = None) -> Transfer:
    """Start the checklist of a transfer in, with its ten items open (REQ-267). Once."""
    today = aircraft_services.today()
    started_on = started_on or today
    if started_on > today:
        raise RefusedError("A Transfer Is Not Started After Today")
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    if aircraft.stage != Stage.TRANSFER_IN:
        raise RefusedError("Only an Aircraft Being Transferred In Has a Checklist")
    if Transfer.objects.filter(aircraft=aircraft).exists():
        raise RefusedError("The Checklist of This Transfer Is Already Started")
    transfer = Transfer.objects.create(
        organisation_id=aircraft.organisation_id, aircraft=aircraft, started_on=started_on
    )
    for number in range(1, len(TRANSFER_ITEMS) + 1):
        TransferItem.objects.create(
            organisation_id=aircraft.organisation_id, transfer=transfer, number=number
        )
    return transfer


def what_the_records_say(aircraft: Aircraft, number: int, today: date) -> tuple[bool, str] | None:
    """Return whether the records bear an item out, and what they say, for the four they answer.

    The management contract, the records received, the configuration
    baseline and the maintenance programme are each read from their own
    record, so that the checklist cannot say what the records do not.
    """
    if number == CONTRACT:
        contract = contract_services.in_force_on(aircraft, today)
        if contract is None:
            return False, "No Contract in Force"
        return True, f"Signed {formatting.long_date(contract.signed_on)}"
    if number == RECORDS:
        received, expected = aircraft.records_received, aircraft.records_expected
        return received == expected, f"{received} of {expected} Received"
    if number == ENTERED:
        baseline = last_baseline(aircraft)
        if baseline is None:
            return False, "Configuration Baseline Not Signed"
        return True, f"Configuration Baseline Signed {formatting.long_date(baseline.signed_on)}"
    if number == PROGRAMME:
        programme = Programme.objects.filter(aircraft=aircraft).first()
        if programme is None:
            return False, "No Maintenance Programme Set Up"
        return True, str(programme.basis)
    return None


@transaction.atomic
def set_item(item: TransferItem, *, state: ItemState | str, note: str = "") -> TransferItem:
    """Record where an item of a transfer stands (REQ-268).

    Complete is refused for the four items the records answer until the
    records bear it out. Not Applicable is for the items that may not
    apply, with the reason. The same state and note sent twice is refused.
    """
    item = TransferItem.objects.select_for_update().get(pk=item.pk)
    aircraft = item.transfer.aircraft
    if aircraft.stage != Stage.TRANSFER_IN:
        raise RefusedError("The Checklist of an Aircraft in the Fleet Is Never Altered")
    if state not in ItemState.values:
        raise RefusedError("Choose Where the Item Stands")
    note = note.strip()
    if state == ItemState.NOT_APPLICABLE:
        if item.number not in MAY_NOT_APPLY:
            raise RefusedError(f"{item.label} Always Applies")
        if not note:
            raise RefusedError("Say Why the Item Does Not Apply")
    if state == ItemState.COMPLETE:
        found = what_the_records_say(aircraft, item.number, aircraft_services.today())
        if found is not None and not found[0]:
            raise RefusedError(f"{item.label} Is Not Complete: {found[1]}")
    if (item.state, item.note) == (state, note):
        raise RefusedError("This Is Already Recorded")
    item.state = state
    item.note = note
    item.save(update_fields=["state", "note"])
    return item


@dataclass(frozen=True)
class ItemLine:
    """One item of a transfer, with what the records say of it."""

    item: TransferItem
    records: str

    @property
    def status(self) -> str:
        """Return the word of the status mark: an item in progress is to assess."""
        return "To Assess" if self.item.state == ItemState.IN_PROGRESS else ""


@dataclass(frozen=True)
class TransferLine:
    """One transfer in: its aircraft, its items and how many are complete."""

    transfer: Transfer
    items: tuple[ItemLine, ...]

    @property
    def complete(self) -> int:
        """Return how many items are complete or do not apply."""
        return sum(1 for line in self.items if line.item.done)

    @property
    def progress(self) -> str:
        """Return the progress as the board writes it: 4 of 10 Complete."""
        return f"{self.complete} of {len(self.items)} Complete"


def transfer_line(aircraft: Aircraft, today: date) -> TransferLine | None:
    """Return the checklist of an aircraft's transfer in, if one is started."""
    transfer = Transfer.objects.filter(aircraft=aircraft).first()
    if transfer is None:
        return None
    lines = []
    for item in transfer.items.all():
        found = what_the_records_say(aircraft, item.number, today)
        lines.append(ItemLine(item, found[1] if found is not None else ""))
    return TransferLine(transfer, tuple(lines))


def stops_the_fleet(aircraft: Aircraft) -> list[str]:
    """Return the items of an aircraft's checklist that are still open (REQ-269)."""
    transfer = Transfer.objects.filter(aircraft=aircraft).first()
    if transfer is None:
        return []
    return [item.label for item in transfer.items.all() if not item.done]


# Positions


@transaction.atomic
def add_position(
    aircraft: Aircraft,
    *,
    product: Product | str,
    chapter: int,
    name: str,
    required: bool = False,
    tracked: bool = False,
    major: bool = False,
    part_number: str = "",
    source: str = "",
) -> Position:
    """Add a position to an aircraft's configuration (REQ-270). Once for each."""
    name = name.strip()
    if not name:
        raise RefusedError("A Position Has a Name")
    if product not in Product.values:
        raise RefusedError("A Position Is of the Airframe, an Engine or a Propeller")
    if not 1 <= chapter <= 99:
        raise RefusedError("A Chapter Is From 1 to 99")
    if major and product == Product.AIRFRAME:
        raise RefusedError("A Major Item Is an Engine or a Propeller")
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    if Position.objects.filter(
        aircraft=aircraft, product=product, chapter=chapter, name=name
    ).exists():
        raise RefusedError("This Position Is Already Recorded for the Aircraft")
    return Position.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        product=product,
        chapter=chapter,
        name=name,
        required=required,
        tracked=tracked,
        major=major,
        part_number=part_number.strip(),
        source=source.strip(),
    )


@transaction.atomic
def record_position(
    position: Position,
    *,
    source: str,
    part_number: str = "",
    serial_number: str = "",
    needs_change: bool = False,
    change: Change | None = None,
    component: Component | None = None,
) -> Position:
    """Record what is fitted at a position, and where that was read (REQ-271).

    A change given is a change of the same aircraft; a component given is
    fitted to it now. The same record sent twice is refused.
    """
    position = Position.objects.select_for_update().get(pk=position.pk)
    source = source.strip()
    if not source:
        raise RefusedError("Say Where What Is Fitted Was Read")
    if change is not None and change.aircraft_id != position.aircraft_id:
        raise RefusedError("The Change Belongs to Another Aircraft")
    if component is not None:
        fitting = component_services.current_installation(component)
        if fitting is None or fitting.aircraft_id != position.aircraft_id:
            raise RefusedError("The Component Is Not Fitted to This Aircraft")
    values = {
        "recorded": True,
        "source": source,
        "part_number": part_number.strip(),
        "serial_number": serial_number.strip(),
        "needs_change": needs_change,
        "change": change,
        "component": component,
    }
    if all(getattr(position, field) == value for field, value in values.items()):
        raise RefusedError("This Is Already Recorded")
    for field, value in values.items():
        setattr(position, field, value)
    position.save(update_fields=list(values))
    return position


# The configuration baseline


def last_baseline(aircraft: Aircraft) -> Baseline | None:
    """Return the latest signed baseline of an aircraft, if it has one."""
    return Baseline.objects.filter(aircraft=aircraft).order_by("-signed_on", "-id").first()


def _major_problem(position: Position, today: date) -> str:
    """Return what is missing of a major item, or nothing."""
    if not position.recorded:
        return ""  # Already an open item: the position is not recorded.
    if position.component is None:
        return f"{position.name}, No Component Recorded"
    problem = component_services.component_line(position.component, today).problem
    return f"{position.name}, {problem}" if problem else ""


@dataclass(frozen=True)
class SetUp:
    """Where the configuration of an aircraft stands: its positions and what is open."""

    aircraft: Aircraft
    positions: tuple[Position, ...]
    changes: tuple[Change, ...]
    open_items: tuple[str, ...]
    baseline: Baseline | None

    @property
    def tracked(self) -> tuple[Position, ...]:
        """Return the positions tracked by serial number."""
        return tuple(position for position in self.positions if position.tracked)

    @property
    def major(self) -> tuple[Position, ...]:
        """Return the major items: the engines and propellers themselves."""
        return tuple(position for position in self.positions if position.major)

    @property
    def recorded_text(self) -> str:
        """Return the board's Positions Recorded: 8 of 12 Tracked, 41 in Template."""
        tracked = self.tracked
        recorded = sum(1 for position in tracked if position.recorded)
        return f"{recorded} of {len(tracked)} Tracked, {len(self.positions)} in Template"

    @property
    def template(self) -> list[tuple[str, str, int, int, int]]:
        """Return each product with its chapters and how many positions it has."""
        rows = []
        for product in Product.values:
            found = [position for position in self.positions if position.product == product]
            if not found:
                continue
            chapters = ", ".join(str(chapter) for chapter in sorted({p.chapter for p in found}))
            rows.append(
                (
                    product,
                    chapters,
                    len(found),
                    sum(1 for p in found if p.required),
                    sum(1 for p in found if p.tracked),
                )
            )
        return rows


def set_up(aircraft: Aircraft, today: date) -> SetUp:
    """Return the positions, changes and open items of an aircraft's configuration (REQ-272).

    An open item is a tracked position not recorded, a position that needs
    a recorded change and has none, or a major item with no component or
    whose limit cannot be worked out.
    """
    positions = tuple(
        Position.objects.filter(aircraft=aircraft).select_related("change", "component")
    )
    open_items = []
    for position in positions:
        if position.tracked and not position.recorded:
            open_items.append(f"{position.name}, Not Recorded")
        elif position.needs_change and position.change_id is None:
            open_items.append(f"{position.name}, Needs a Recorded Change")
        if position.major:
            problem = _major_problem(position, today)
            if problem:
                open_items.append(problem)
    changes = tuple(
        Change.objects.filter(aircraft=aircraft, embodied_on__isnull=False).order_by(
            "embodied_on", "title"
        )
    )
    return SetUp(aircraft, positions, changes, tuple(open_items), last_baseline(aircraft))


@transaction.atomic
def sign_baseline(aircraft: Aircraft, *, by: User) -> Baseline:
    """Sign the configuration baseline of an aircraft, today (REQ-273, REQ-274).

    Ours: not with an item still open, and not without a position. One
    baseline a day for an aircraft, so the same form sent twice signs one.
    What the baseline shows is written by the database, as it stands.
    """
    today = aircraft_services.today()
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    found = set_up(aircraft, today)
    if not found.positions:
        raise RefusedError("A Baseline Is Signed for an Aircraft With Positions Recorded")
    if found.open_items:
        raise RefusedError("Items Still Open: " + "; ".join(found.open_items))
    if Baseline.objects.filter(aircraft=aircraft, signed_on=today).exists():
        raise RefusedError("A Baseline Is Already Signed for This Aircraft Today")
    baseline = Baseline.objects.create(
        organisation_id=aircraft.organisation_id, aircraft=aircraft, signed_on=today, signed_by=by
    )
    baseline.refresh_from_db()
    return baseline


def signed_positions(baseline: Baseline) -> list[dict[str, object]]:
    """Return the positions a baseline was signed with, as it kept them."""
    found: list[dict[str, object]] = json.loads(baseline.positions or "[]")
    return found


def signed_changes(baseline: Baseline) -> list[dict[str, object]]:
    """Return the changes and repairs a baseline was signed with, as it kept them."""
    found: list[dict[str, object]] = json.loads(baseline.changes or "[]")
    return found
