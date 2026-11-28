"""Post Goods In dispositions to stock once, and keep the location ledger (REQ-358).

The approved receipt-to-stock contract is in ``assurance/phase-4-stores-handoff.md``.
Goods In owns the receipt, inspection and final disposition. Stores reads those persisted
records, records a dated structured resolution of unit, identity, location and shelf life,
and posts once per disposition. The database enforces the same rules
(migration 0008): this module gives the reasons in words and keeps the actor's evidence.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID

from django.db import DatabaseError, IntegrityError, connection, transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.models import (
    STOCK_QUANTITY_LIMIT,
    Destination,
    ItemClass,
    LocationKind,
    MovementKind,
    ReceivingDisposition,
    ShelfLifeBasis,
    ShelfLifeRule,
    StockCount,
    StockMovement,
    StockPosting,
    StockResolution,
    StockUnit,
    StoreLocation,
)
from airworthiness_plus.logistics.services import RefusedError
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Person
from airworthiness_rules.dates import days_between


class ConflictError(RefusedError):
    """A replay disagrees with the record already made. The original is kept."""


class ShelfStatus(StrEnum):
    CURRENT = "Current"
    DUE_SOON = "Due Soon"
    EXPIRED = "Expired"
    UNKNOWN = "Unknown"
    NOT_APPLICABLE = "Not Applicable"


PLAIN_NUMBER = re.compile(r"-?[0-9]+(\.[0-9]+)?")
USABLE = frozenset({ShelfStatus.CURRENT, ShelfStatus.DUE_SOON, ShelfStatus.NOT_APPLICABLE})


def shelf_status(basis: str, until: date | None, rule: str, today: date, lead_days: int) -> str:
    """The shelf-life state on ``today`` from the evidenced basis and its boundary.

    ``Valid Through the Date`` is usable on the date itself. ``Expires at the Start of
    the Date`` is not. A missing or unknown boundary is Unknown and prevents use.
    """
    if basis == ShelfLifeBasis.NOT_APPLICABLE:
        return ShelfStatus.NOT_APPLICABLE
    if basis != ShelfLifeBasis.DATED or until is None:
        return ShelfStatus.UNKNOWN
    if rule == ShelfLifeRule.THROUGH:
        last = until
    elif rule == ShelfLifeRule.START_OF_DAY:
        last = date.fromordinal(until.toordinal() - 1)
    else:
        return ShelfStatus.UNKNOWN
    if today > last:
        return ShelfStatus.EXPIRED
    if days_between(today, until) <= lead_days:
        return ShelfStatus.DUE_SOON
    return ShelfStatus.CURRENT


def checked_quantity(value: Decimal | str | int, unit: str, *, allow_zero: bool = False) -> Decimal:
    """Refuse a quantity outside the supported unit, scale or range. Never round."""
    if not PLAIN_NUMBER.fullmatch(str(value).strip()):
        raise RefusedError("Give the Quantity as a Number")
    try:
        quantity = Decimal(str(value).strip())
    except InvalidOperation as error:
        raise RefusedError("Give the Quantity as a Number") from error
    if not quantity.is_finite():
        raise RefusedError("Give the Quantity as a Number")
    if unit not in StockUnit.values:
        raise RefusedError("Choose Each or Litre")
    exponent = quantity.normalize().as_tuple().exponent
    assert isinstance(exponent, int)  # noqa: S101  a finite value has an integer exponent
    if unit == StockUnit.EACH and exponent < 0:
        raise RefusedError("A Quantity in Each Must Be a Whole Number")
    if exponent < -3:
        raise RefusedError("Give Litres to No More Than Three Decimal Places")
    if quantity < 0 or (quantity == 0 and not allow_zero):
        raise RefusedError("The Quantity Must Be More Than Zero")
    if quantity > STOCK_QUANTITY_LIMIT:
        raise RefusedError(f"The Quantity Cannot Exceed {STOCK_QUANTITY_LIMIT:,}")
    return quantity


def _active_on(person: Person, organisation_id: UUID, day: date) -> None:
    if (
        person.organisation_id != organisation_id
        or (person.joined_on is not None and person.joined_on > day)
        or (person.left_on is not None and person.left_on < day)
    ):
        raise RefusedError("The Signed-In Person Is Not Active in the Organisation on That Date")


def _text(value: str) -> str:
    return value.strip()


def _refused(error: DatabaseError) -> RefusedError:
    cause = getattr(error, "__cause__", None)
    diagnostic = getattr(cause, "diag", None)
    message = getattr(diagnostic, "message_primary", None) or "The Database Refused the Change"
    return RefusedError(str(message)[:1].upper() + str(message)[1:])


# Locations


@transaction.atomic
def add_location(
    organisation: Organisation,
    *,
    name: str,
    kind: str,
    holds_components: bool,
    holds_standard_parts: bool,
    holds_materials: bool,
    secure: bool,
    storage_conditions: str = "",
    station: str = "",
) -> StoreLocation:
    name = _text(name)
    station = station.strip().upper()
    if station and not re.fullmatch(r"[A-Z0-9-]{1,12}", station):
        raise RefusedError("Use up to 12 letters, numbers or hyphens for the Station Code")
    if not name:
        raise RefusedError("Give the Location a Name")
    if kind not in LocationKind.values:
        raise RefusedError("Choose Serviceable Stores or Quarantine")
    if not (holds_components or holds_standard_parts or holds_materials):
        raise RefusedError("Choose at Least One Class the Location May Hold")
    if kind == LocationKind.QUARANTINE and not secure:
        raise RefusedError("A Quarantine Location Must Be Secure and Segregated")
    if StoreLocation.objects.filter(organisation=organisation, name__iexact=name).exists():
        raise RefusedError("A Location With This Name Is Already Recorded")
    try:
        with transaction.atomic():
            return StoreLocation.objects.create(
                organisation=organisation,
                name=name,
                station=station,
                kind=kind,
                holds_components=holds_components,
                holds_standard_parts=holds_standard_parts,
                holds_materials=holds_materials,
                secure=secure,
                storage_conditions=_text(storage_conditions),
            )
    except IntegrityError as error:
        raise RefusedError("A Location With This Name Is Already Recorded") from error


@transaction.atomic
def withdraw_location(location: StoreLocation) -> StoreLocation:
    StoreLocation.objects.filter(pk=location.pk).update(active=False)
    location.refresh_from_db()
    return location


# Resolution and posting


def identity_blockers(
    classification: str, part_number: str, serial_number: str, batch: str, specification: str
) -> list[str]:
    """The approved identity rule for each received class."""
    part, serial, lot, spec = (
        _text(value) for value in (part_number, serial_number, batch, specification)
    )
    if classification == ItemClass.STANDARD:
        if not spec or not (lot or serial):
            return ["Traceable Identity Not Resolved: Give the Standard and the Received Lot"]
    elif classification == ItemClass.MATERIAL:
        if not spec or not lot:
            return ["Traceable Identity Not Resolved: Give the Specification and Batch"]
    elif not part or not (serial or lot):
        return ["Traceable Identity Not Resolved: Give the Part Number and Serial or Lot"]
    return []


def latest_resolution(disposition: ReceivingDisposition) -> StockResolution | None:
    return disposition.stock_resolutions.select_related("location").first()


def _serial_in_custody(organisation_id: UUID, part_number: str, serial_number: str) -> bool:
    if not _text(serial_number):
        return False
    lots = StockPosting.objects.filter(
        organisation_id=organisation_id,
        part_number__iexact=_text(part_number),
        serial_number__iexact=_text(serial_number),
    )
    return any(custody(lot) > 0 for lot in lots)


def posting_blockers(
    disposition: ReceivingDisposition, resolution: StockResolution | None
) -> list[str]:
    """Every reason the disposition cannot be posted yet, in words. Empty when ready."""
    if disposition.outcome == Destination.RETURN:
        return ["Returned to Supplier. Nothing Is Credited"]
    receipt = disposition.receipt
    reasons: list[str] = []
    if disposition.outcome == Destination.STORES and not disposition.document_kind:
        reasons.append(
            "Acceptance Evidence Not Substantiated: Needs a Fresh Linked Goods In Assessment"
        )
    if resolution is None:
        return [
            *reasons,
            "Unit Not Resolved",
            "Traceable Identity Not Resolved",
            "Stock Location Not Resolved",
            "Shelf-Life Basis Not Resolved",
        ]
    reasons += identity_blockers(
        receipt.classification,
        resolution.part_number,
        resolution.serial_number,
        resolution.batch_number,
        resolution.specification,
    )
    if resolution.serial_number and receipt.quantity != 1:
        reasons.append("A Serialised Line Must Be Exactly One Each")
    place = resolution.location
    wanted = (
        LocationKind.QUARANTINE
        if disposition.outcome == Destination.QUARANTINE
        else LocationKind.SERVICEABLE
    )
    if place is None:
        reasons.append("Stock Location Not Resolved")
    elif not place.active:
        reasons.append("Stock Location Is Withdrawn")
    elif place.kind != wanted:
        reasons.append(f"Stock Location Must Be {wanted}")
    elif not place.accepts(receipt.classification):
        reasons.append("Stock Location Does Not Accept This Class")
    if not resolution.shelf_life_basis:
        reasons.append("Shelf-Life Basis Not Resolved")
    elif receipt.shelf_life_to is not None and (
        resolution.shelf_life_basis != ShelfLifeBasis.DATED
        or resolution.shelf_life_to != receipt.shelf_life_to
    ):
        reasons.append("Shelf-Life Basis Does Not Match the Received Shelf Life")
    if _serial_in_custody(
        disposition.organisation_id, resolution.part_number, resolution.serial_number
    ):
        reasons.append("This Serial Already Has a Current Custody Position")
    return reasons


@transaction.atomic
def resolve(
    disposition: ReceivingDisposition,
    *,
    actor: Person,
    authority: str,
    unit: str,
    evidence: str,
    evidence_on: date,
    part_number: str = "",
    serial_number: str = "",
    batch_number: str = "",
    specification: str = "",
    location: StoreLocation | None = None,
    shelf_life_basis: str = "",
    shelf_life_to: date | None = None,
    shelf_life_rule: str = "",
) -> StockResolution:
    """Record a dated structured reading from the original evidence. Earlier ones stay."""
    _lock(disposition)
    if disposition.outcome not in (Destination.STORES, Destination.QUARANTINE):
        raise RefusedError("Only an Acceptance or a Quarantine Decision Is Resolved for Stock")
    if StockPosting.objects.filter(disposition=disposition).exists():
        raise RefusedError("This Disposition Is Already Posted. Correct It by a Later Movement")
    today = aircraft_services.today()
    if not disposition.disposition_on <= evidence_on <= today:
        raise RefusedError("The Assessment Date Must Be on or After the Disposition, Not Later")
    _active_on(actor, disposition.organisation_id, evidence_on)
    if not _text(evidence) or not _text(authority):
        raise RefusedError("Give the Evidence Relied On and the Authority")
    if unit not in StockUnit.values:
        raise RefusedError("Choose Each or Litre")
    if _text(serial_number) and unit != StockUnit.EACH:
        raise RefusedError("A Serialised Item Is Counted in Each")
    checked_quantity(disposition.receipt.quantity, unit)
    if location is not None and location.organisation_id != disposition.organisation_id:
        raise RefusedError("Choose a Location of This Organisation")
    if shelf_life_basis == ShelfLifeBasis.DATED:
        if shelf_life_to is None or shelf_life_rule not in ShelfLifeRule.values:
            raise RefusedError("Give the Shelf-Life Date and Its Boundary")
    elif shelf_life_to is not None or shelf_life_rule:
        raise RefusedError("A Shelf-Life Date Needs the Dated Basis")
    if (
        shelf_life_basis == ShelfLifeBasis.NOT_APPLICABLE
        and disposition.receipt.shelf_life_to is not None
    ):
        raise RefusedError("The Receipt Has a Recorded Shelf Life")
    return StockResolution.objects.create(
        organisation_id=disposition.organisation_id,
        disposition=disposition,
        unit=unit,
        part_number=_text(part_number),
        serial_number=_text(serial_number),
        batch_number=_text(batch_number),
        specification=_text(specification),
        location=location,
        shelf_life_basis=shelf_life_basis,
        shelf_life_to=shelf_life_to,
        shelf_life_rule=shelf_life_rule,
        evidence=_text(evidence),
        evidence_on=evidence_on,
        recorded_by=actor,
        recorded_by_name=actor.full_name,
        authority=_text(authority),
    )


def _lock(disposition: ReceivingDisposition) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT logistics_lock_stock('posting', %s)", [disposition.pk])


def post(
    disposition: ReceivingDisposition, *, actor: Person, authority: str, posted_on: date
) -> StockPosting:
    """Post once by disposition. A same-request replay returns the original posting."""
    with transaction.atomic():
        _lock(disposition)
        resolution = latest_resolution(disposition)
        existing = StockPosting.objects.filter(disposition=disposition).first()
        if existing is not None:
            if resolution is not None and existing.resolution_id == resolution.pk:
                return existing
            raise ConflictError("This Disposition Was Already Posted. The Original Is Kept")
        reasons = posting_blockers(disposition, resolution)
        if reasons:
            raise RefusedError("Not Ready to Post: " + "; ".join(reasons))
        assert resolution is not None  # noqa: S101  no blockers means a resolution exists
        if posted_on > aircraft_services.today() or posted_on < disposition.disposition_on:
            raise RefusedError("The Posting Date Must Be on or After the Movement, Not Later")
        _active_on(actor, disposition.organisation_id, posted_on)
        if not _text(authority):
            raise RefusedError("Give the Authority Relied On")
        place = resolution.location
        assert place is not None  # noqa: S101  checked by posting_blockers
        try:
            with transaction.atomic():
                created = StockPosting.objects.create(
                    organisation_id=disposition.organisation_id,
                    disposition=disposition,
                    resolution=resolution,
                    held=disposition.outcome == Destination.QUARANTINE,
                    unit=resolution.unit,
                    quantity=Decimal(disposition.receipt.quantity),
                    location=place,
                    location_name=place.name,
                    location_kind=place.kind,
                    shelf_life_basis=resolution.shelf_life_basis,
                    physical_on=disposition.disposition_on,
                    posted_on=posted_on,
                    actor=actor,
                    actor_name=actor.full_name,
                    authority=_text(authority),
                )
                # The database fills the posting from the persisted records. Return those.
                created.refresh_from_db()
                return created
        except DatabaseError as error:
            if isinstance(error, IntegrityError) and (
                StockPosting.objects.filter(disposition=disposition).exists()
            ):
                raise ConflictError(
                    "This Disposition Was Already Posted. The Original Is Kept"
                ) from error
            raise _refused(error) from error


def reconcile(
    organisation: Organisation, *, actor: Person, authority: str, posted_on: date
) -> tuple[list[StockPosting], dict[ReceivingDisposition, list[str]]]:
    """Post every resolved, unblocked disposition through the same path. Restartable."""
    posted: list[StockPosting] = []
    blocked: dict[ReceivingDisposition, list[str]] = {}
    decisions = (
        ReceivingDisposition.objects.filter(
            organisation=organisation,
            outcome__in=(Destination.STORES, Destination.QUARANTINE),
            stock_posting__isnull=True,
        )
        .select_related("receipt")
        .order_by("disposition_on", "id")
    )
    for decision in decisions:
        reasons = posting_blockers(decision, latest_resolution(decision))
        if reasons:
            blocked[decision] = reasons
            continue
        posted.append(post(decision, actor=actor, authority=authority, posted_on=posted_on))
    return posted, blocked


# Ledger


def balance(lot: StockPosting, location: StoreLocation) -> Decimal:
    with connection.cursor() as cursor:
        cursor.execute("SELECT logistics_stock_balance(%s, %s)", [lot.pk, location.pk])
        (amount,) = cursor.fetchone()
    return Decimal(amount)


def unreserved(lot: StockPosting, location: StoreLocation) -> Decimal:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT logistics_stock_balance(%s, %s) - logistics_stock_reserved(%s, %s)",
            [lot.pk, location.pk, lot.pk, location.pk],
        )
        (amount,) = cursor.fetchone()
    return Decimal(amount)


def custody(lot: StockPosting) -> Decimal:
    total = Decimal(0)
    for movement in lot.movements.all():
        if movement.to_location_id is not None:
            total += movement.quantity
        if movement.from_location_id is not None:
            total -= movement.quantity
    return total


def _write(**values: object) -> StockMovement:
    try:
        with transaction.atomic():
            return StockMovement.objects.create(**values)
    except DatabaseError as error:
        raise _refused(error) from error


@transaction.atomic
def move(
    lot: StockPosting,
    *,
    from_location: StoreLocation,
    to_location: StoreLocation,
    quantity: Decimal | str,
    moved_on: date,
    actor: Person,
    authority: str,
    evidence: str,
) -> StockMovement:
    """Move part or all of a position between two compatible locations of the organisation."""
    amount = checked_quantity(quantity, lot.unit)
    if lot.serial_number and amount != 1:
        raise RefusedError("A Serialised Item Moves as Exactly One Each")
    if from_location.pk == to_location.pk:
        raise RefusedError("Choose a Different Destination")
    for place in (from_location, to_location):
        if place.organisation_id != lot.organisation_id:
            raise RefusedError("Choose a Location of This Organisation")
    classification = lot.disposition.receipt.classification
    if not to_location.active:
        raise RefusedError("The Destination Is Withdrawn")
    if not to_location.accepts(classification):
        raise RefusedError("The Destination Does Not Accept This Class")
    if to_location.kind == LocationKind.SERVICEABLE and lot.held:
        raise RefusedError("An Open Quarantine Hold Cannot Move to Serviceable Stores")
    if (
        from_location.kind == LocationKind.QUARANTINE
        and to_location.kind == LocationKind.SERVICEABLE
    ):
        raise RefusedError(
            "Quarantined Stock Needs a New Receiving Decision Before Serviceable Use"
        )
    if not lot.physical_on <= moved_on <= aircraft_services.today():
        raise RefusedError("The Movement Date Must Be on or After Intake, Not Later")
    _active_on(actor, lot.organisation_id, moved_on)
    if not _text(authority) or not _text(evidence):
        raise RefusedError("Give the Authority and the Movement Evidence")
    _lock_lot(lot)
    if balance(lot, from_location) < amount:
        raise RefusedError("The Source Location Does Not Hold That Quantity")
    if unreserved(lot, from_location) < amount:
        raise RefusedError("The Source Location Holds Less Unreserved Stock Than This Quantity")
    return _write(
        organisation_id=lot.organisation_id,
        lot=lot,
        kind=MovementKind.TRANSFER,
        from_location=from_location,
        to_location=to_location,
        quantity=amount,
        moved_on=moved_on,
        actor=actor,
        actor_name=actor.full_name,
        authority=_text(authority),
        evidence=_text(evidence),
    )


def _lock_lot(lot: StockPosting) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT logistics_lock_stock('lot', %s)", [lot.pk])


@transaction.atomic
def count(
    lot: StockPosting,
    *,
    location: StoreLocation,
    counted_quantity: Decimal | str,
    counted_on: date,
    counter: Person,
    evidence: str,
) -> StockCount:
    """Record what was counted. The ledger is unchanged until an authorised adjustment."""
    amount = checked_quantity(counted_quantity, lot.unit, allow_zero=True)
    if location.organisation_id != lot.organisation_id:
        raise RefusedError("Choose a Location of This Organisation")
    if not lot.physical_on <= counted_on <= aircraft_services.today():
        raise RefusedError("The Count Date Must Be on or After Intake, Not Later")
    _active_on(counter, lot.organisation_id, counted_on)
    if not _text(evidence):
        raise RefusedError("Give the Count Evidence")
    _lock_lot(lot)
    try:
        with transaction.atomic():
            return StockCount.objects.create(
                organisation_id=lot.organisation_id,
                lot=lot,
                location=location,
                counted_quantity=amount,
                ledger_quantity=balance(lot, location),
                counted_on=counted_on,
                counter=counter,
                counter_name=counter.full_name,
                evidence=_text(evidence),
            )
    except DatabaseError as error:
        raise _refused(error) from error


@transaction.atomic
def adjust(
    tally: StockCount, *, actor: Person, authority: str, evidence: str, moved_on: date
) -> StockMovement:
    """Apply a count's variance once, by an authorised person, with evidence."""
    lot = tally.lot
    _lock_lot(lot)
    existing = StockMovement.objects.filter(count=tally).first()
    if existing is not None:
        return existing
    variance = tally.variance
    if variance == 0:
        raise RefusedError("The Count Agrees With the Ledger. Nothing to Adjust")
    if balance(lot, tally.location) != tally.ledger_quantity:
        raise RefusedError("The Ledger Has Moved Since This Count. Count Again")
    if variance < 0 and abs(variance) > unreserved(lot, tally.location):
        raise RefusedError("Release the Reservations Covering the Count Shortfall First")
    if not tally.counted_on <= moved_on <= aircraft_services.today():
        raise RefusedError("The Adjustment Date Must Be on or After the Count, Not Later")
    _active_on(actor, lot.organisation_id, moved_on)
    if not _text(authority) or not _text(evidence):
        raise RefusedError("Give the Authority and the Adjustment Evidence")
    return _write(
        organisation_id=lot.organisation_id,
        lot=lot,
        kind=MovementKind.ADJUSTMENT,
        from_location=tally.location if variance < 0 else None,
        to_location=tally.location if variance > 0 else None,
        quantity=abs(variance),
        moved_on=moved_on,
        count=tally,
        actor=actor,
        actor_name=actor.full_name,
        authority=_text(authority),
        evidence=_text(evidence),
    )


# Reading


@dataclass(frozen=True)
class Position:
    lot: StockPosting
    location: StoreLocation
    on_hand: Decimal
    reserved: Decimal
    available: Decimal
    shelf: str


def lot_shelf(lot: StockPosting, today: date, lead_days: int) -> str:
    return shelf_status(
        lot.shelf_life_basis, lot.shelf_life_to, lot.shelf_life_rule, today, lead_days
    )


def positions(lots: list[StockPosting], today: date, lead_days: int) -> list[Position]:
    """Read physical custody and reservations together from the protected ledger."""
    indexed = {lot.pk: lot for lot in lots}
    if not indexed:
        return []
    identifiers = list(indexed)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH ledger_positions(lot, place) AS (
                SELECT lot_id, to_location_id FROM logistics_stockmovement WHERE lot_id = ANY(%s)
                UNION
                SELECT lot_id, from_location_id FROM logistics_stockmovement WHERE lot_id = ANY(%s)
                UNION
                SELECT posting_id, destination_id FROM logistics_stockallocation
                 WHERE posting_id = ANY(%s)
                UNION
                SELECT posting_id, source_id FROM logistics_stockallocation
                 WHERE posting_id = ANY(%s)
            )
            SELECT lot, place, logistics_stock_balance(lot, place),
                   logistics_stock_reserved(lot, place)
              FROM ledger_positions WHERE place IS NOT NULL
            """,
            [identifiers, identifiers, identifiers, identifiers],
        )
        balances = [row for row in cursor.fetchall() if row[2]]
    places = StoreLocation.objects.in_bulk({place for _, place, _, _ in balances})
    result = []
    for lot_id, place_id, amount, reserved in balances:
        lot, place = indexed[lot_id], places[place_id]
        shelf = lot_shelf(lot, today, lead_days)
        usable = (
            not lot.held
            and place.kind == LocationKind.SERVICEABLE
            and place.active
            and shelf in USABLE
        )
        result.append(
            Position(
                lot,
                place,
                amount,
                reserved,
                max(amount - reserved, Decimal(0)) if usable else Decimal(0),
                shelf,
            )
        )
    return sorted(result, key=lambda one: (one.location.name, str(one.lot.pk)))


def available(disposition: ReceivingDisposition, today: date, lead_days: int) -> Decimal:
    lot = StockPosting.objects.filter(disposition=disposition).first()
    if lot is None:
        return Decimal(0)
    return sum((one.available for one in positions([lot], today, lead_days)), Decimal(0))


def display(value: Decimal) -> str:
    """Show an exact quantity without trailing zeros, never in exponent form."""
    text = f"{value:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
