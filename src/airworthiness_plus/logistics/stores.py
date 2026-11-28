"""Post accepted and quarantined dispositions once, and keep the movement ledger (REQ-358).

Goods In owns the receipt, inspection and final disposition. Stores reads
the persisted decision by its identifier and posts it once, after dated
evidence resolves the unit, quantity, traceable identity, shelf-life basis
and a compatible location. Balances are derived from the movements, which
are appended and never changed. PostgreSQL holds the same rules
(migration 0008) so that a fault here cannot break them.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, connection, transaction
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.models import (
    QUANTITY_LIMIT,
    Destination,
    ItemClass,
    LocationKind,
    MovementKind,
    PostingEvidence,
    PostingKind,
    ReceivingDisposition,
    StockCount,
    StockMovement,
    StockPosting,
    StockUnit,
    StoresAction,
    StoresAppointment,
    StoresAppointmentWithdrawal,
    StoresLocation,
    StoresLocationWithdrawal,
)
from airworthiness_plus.logistics.services import RefusedError, maintenance_approvals
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Person
from airworthiness_rules import shelf_life

# The organisation's warning lead time is To Be Checked against its procedure.
SHELF_LIFE_WARNING_DAYS = 30
ZERO = Decimal(0)

AWAITING = "Awaiting Stock Posting"
POSTED = "Posted to Stock"
HELD = "Quarantine Hold"
HOLD_TO_VERIFY = "Quarantine Hold, Details to Verify"
RETURNED = "Returned to Supplier"


class PostingConflictError(RefusedError):
    """The disposition is already posted from other evidence. The original is kept."""


# Authority


def _authorise(user: User, role_action: Action, action: str, day: date) -> StoresAppointment:
    if not user.is_active or not user.may(role_action):
        raise ActionRefusedError(role_action)
    organisation = user.organisation
    held = {
        (approval.pk, approval.reference_on(day))
        for approval in maintenance_approvals(organisation, day)
    }
    grants = (
        StoresAppointment.objects.filter(
            organisation=organisation,
            person__user=user,
            action=action,
            starts_on__lte=day,
            ends_on__gte=day,
        )
        .exclude(withdrawal__withdrawn_on__lte=day)
        .filter(Q(person__joined_on__isnull=True) | Q(person__joined_on__lte=day))
        .filter(Q(person__left_on__isnull=True) | Q(person__left_on__gt=day))
        .select_related("person", "approval")
        .order_by("-starts_on", "-entered_at", "-id")
    )
    for grant in grants:
        if (grant.approval_id, grant.approval_reference) in held:
            return grant
    raise RefusedError(
        f"Your Person Record Needs a Current Stores Appointment To {StoresAction(action).label}"
    )


def may_act(user: User, role_action: Action, action: str, day: date) -> bool:
    """Return whether the controls for this action should be offered to the user."""
    try:
        _authorise(user, role_action, action, day)
    except (RefusedError, ActionRefusedError):
        return False
    return True


def _retry[RecordType: (StoresAppointment, StoresAppointmentWithdrawal, StoresLocation)](
    model: type[RecordType], organisation: Organisation, request_id: UUID
) -> RecordType | None:
    return model._default_manager.filter(organisation=organisation, submission=request_id).first()


def _lock_organisation(user: User) -> Organisation:
    return Organisation.objects.select_for_update(no_key=True).get(pk=user.organisation_id)


@transaction.atomic
def record_appointment(
    user: User,
    *,
    request_id: UUID,
    approval: str,
    person: Person,
    action: str,
    starts_on: date,
    ends_on: date,
    exposition_reference: str,
    authority: str,
) -> StoresAppointment:
    if not user.is_active or not user.may(Action.MANAGE_STORES_APPOINTMENTS):
        raise ActionRefusedError(Action.MANAGE_STORES_APPOINTMENTS)
    organisation = _lock_organisation(user)
    if (existing := _retry(StoresAppointment, organisation, request_id)) is not None:
        return existing
    today = aircraft_services.today()
    term = next(
        (one for one in maintenance_approvals(organisation, today) if one.approval == approval),
        None,
    )
    reference = term.reference_on(today) if term is not None else None
    if term is None or reference is None:
        raise RefusedError(f"The Organisation Holds No {approval} Maintenance Approval Today")
    if person.organisation_id != organisation.pk or person.user_id is None:
        raise RefusedError("Choose a Person of This Organisation With a Sign-In")
    if ends_on < starts_on or ends_on < today:
        raise RefusedError("Give a Period That Ends Today or Later")
    return StoresAppointment.objects.create(
        organisation=organisation,
        submission=request_id,
        person=person,
        approval=term,
        approval_reference=reference,
        action=action,
        starts_on=starts_on,
        ends_on=ends_on,
        exposition_reference=exposition_reference,
        authority=authority,
    )


@transaction.atomic
def withdraw_appointment(
    user: User, appointment: StoresAppointment, *, request_id: UUID, evidence: str
) -> StoresAppointmentWithdrawal:
    if not user.is_active or not user.may(Action.MANAGE_STORES_APPOINTMENTS):
        raise ActionRefusedError(Action.MANAGE_STORES_APPOINTMENTS)
    organisation = _lock_organisation(user)
    if (existing := _retry(StoresAppointmentWithdrawal, organisation, request_id)) is not None:
        return existing
    if StoresAppointmentWithdrawal.objects.filter(appointment=appointment).exists():
        raise RefusedError("This Appointment Is Already Withdrawn")
    return StoresAppointmentWithdrawal.objects.create(
        organisation=organisation,
        submission=request_id,
        appointment=appointment,
        withdrawn_on=aircraft_services.today(),
        evidence=evidence,
    )


# Locations


@transaction.atomic
def record_location(
    user: User,
    *,
    request_id: UUID,
    code: str,
    name: str,
    kind: str,
    classes: list[str],
    storage_conditions: str,
    secure: bool,
    station: str = "",
) -> StoresLocation:
    today = aircraft_services.today()
    grant = _authorise(user, Action.RECORD_STORES, StoresAction.LOCATIONS, today)
    organisation = _lock_organisation(user)
    if (existing := _retry(StoresLocation, organisation, request_id)) is not None:
        return existing
    if kind == LocationKind.QUARANTINE and not secure:
        raise RefusedError("A Quarantine Location Must Be Secure and Segregated")
    if StoresLocation.objects.filter(organisation=organisation, code__iexact=code).exists():
        raise RefusedError("This Location Code Is Already Recorded")
    return StoresLocation.objects.create(
        organisation=organisation,
        submission=request_id,
        code=code,
        station=station.strip().upper(),
        name=name,
        kind=kind,
        classes=sorted(set(classes), key=ItemClass.values.index),
        storage_conditions=storage_conditions,
        secure=secure,
        recorded_on=today,
        appointment=grant,
    )


@transaction.atomic
def withdraw_location(
    user: User, location: StoresLocation, *, request_id: UUID, evidence: str
) -> StoresLocationWithdrawal:
    today = aircraft_services.today()
    grant = _authorise(user, Action.RECORD_STORES, StoresAction.LOCATIONS, today)
    organisation = _lock_organisation(user)
    existing = StoresLocationWithdrawal.objects.filter(
        organisation=organisation, submission=request_id
    ).first()
    if existing is not None:
        return existing
    if StoresLocationWithdrawal.objects.filter(location=location).exists():
        raise RefusedError("This Location Is Already Withdrawn")
    if any(position.on_hand for position in positions(organisation, today, location=location)):
        raise RefusedError("Move the Stock Out Before Withdrawing the Location")
    return StoresLocationWithdrawal.objects.create(
        organisation=organisation,
        submission=request_id,
        location=location,
        withdrawn_on=today,
        evidence=evidence,
        appointment=grant,
    )


def active_locations(organisation: Organisation, day: date) -> list[StoresLocation]:
    return list(
        StoresLocation.objects.filter(organisation=organisation).exclude(
            withdrawal__withdrawn_on__lte=day
        )
    )


def accepts(location: StoresLocation, kind: str, classification: str, day: date) -> bool:
    withdrawal = getattr(location, "withdrawal", None)
    if withdrawal is not None and withdrawal.withdrawn_on <= day:
        return False
    if kind == PostingKind.HOLD:
        return location.kind == LocationKind.QUARANTINE and location.secure
    return location.kind == LocationKind.SERVICEABLE and classification in location.classes


def location_rules(location: StoresLocation) -> str:
    secure = "Secure and Segregated" if location.secure else "Not Secured"
    return (
        f"{location.code}, {location.name}. {location.kind}. Holds {', '.join(location.classes)}. "
        f"{location.storage_conditions}. {secure}"
    )


# Posting


def fits(unit: str, quantity: Decimal, serial: str = "") -> bool:
    """Return whether ``quantity`` is a valid amount of ``unit`` (mirrors the database)."""
    if not ZERO < quantity <= QUANTITY_LIMIT or quantity != quantity.quantize(Decimal("0.001")):
        return False
    if unit == StockUnit.EACH:
        return quantity == quantity.to_integral_value() and (not serial or quantity == 1)
    return unit == StockUnit.LITRE and not serial


def latest_evidence(disposition: ReceivingDisposition) -> PostingEvidence | None:
    return disposition.posting_evidence.select_related("location__withdrawal").first()


def posting_kind(disposition: ReceivingDisposition) -> str | None:
    return {
        Destination.STORES: PostingKind.STOCK,
        Destination.QUARANTINE: PostingKind.HOLD,
    }.get(Destination(disposition.outcome))


def blockers(
    disposition: ReceivingDisposition, evidence: PostingEvidence | None, day: date
) -> list[str]:
    """Return every reason the disposition cannot be posted yet, in a fixed order."""
    kind = posting_kind(disposition)
    if kind is None:
        return ["A Supplier Return Is Kept in History and Never Posted to Stock"]
    receipt = disposition.receipt
    reasons: list[str] = []
    unit = evidence.unit if evidence else ""
    quantity = evidence.quantity if evidence else None
    serial = evidence.serial if evidence else ""
    if not unit or quantity is None:
        reasons.append("Unit and Quantity Need Dated Evidence")
    elif not fits(unit, quantity, serial):
        reasons.append("The Quantity Does Not Fit Its Unit or the Serial Number")
    elif unit == StockUnit.EACH and quantity != receipt.quantity:
        reasons.append("The Quantity Differs From the Receipt. Review the Delivered Measure")
    location = evidence.location if evidence else None
    if location is None:
        reasons.append(
            "Quarantine Location to Verify"
            if kind == PostingKind.HOLD
            else "Stock Location Unknown"
        )
    elif not accepts(location, kind, receipt.classification, day):
        reasons.append("The Location Does Not Accept This Item")
    if kind == PostingKind.HOLD:
        if evidence is None or not evidence.tag.strip():
            reasons.append("Quarantine Tag Not Recorded")
        return reasons
    if evidence is None or not _identity_resolved(receipt.classification, evidence):
        reasons.append(_identity_reason(receipt.classification))
    basis = evidence.shelf_life_basis if evidence else ""
    last = shelf_life.last_day_of_use(basis, evidence.shelf_life_to if evidence else None)
    if not basis:
        reasons.append("Shelf-Life Basis Unknown")
    elif basis != shelf_life.Basis.NOT_APPLICABLE and (
        last is None or last < disposition.disposition_on
    ):
        reasons.append("Shelf Life Had Passed on Arrival in Stores")
    if evidence is not None and evidence.serial and _serial_in_custody(evidence):
        reasons.append("This Serial Number Already Has a Custody Position")
    return reasons


def _identity_resolved(classification: str, evidence: PostingEvidence) -> bool:
    if classification == ItemClass.SERVICEABLE:
        return bool(evidence.part_number and (evidence.serial or evidence.batch))
    return bool(evidence.specification and evidence.batch)


def _identity_reason(classification: str) -> str:
    if classification == ItemClass.SERVICEABLE:
        return "Traceable Identity Unresolved: Part Number With Serial or Lot"
    return "Traceable Identity Unresolved: Standard or Specification With Batch"


def _serial_in_custody(evidence: PostingEvidence) -> bool:
    return (
        StockPosting.objects.filter(
            kind=PostingKind.STOCK,
            evidence__serial__iexact=evidence.serial,
            evidence__part_number__iexact=evidence.part_number,
            evidence__manufacturer__iexact=evidence.manufacturer,
        )
        .exclude(disposition_id=evidence.disposition_id)
        .exists()
    )


@transaction.atomic
def record_posting_evidence(
    user: User,
    disposition: ReceivingDisposition,
    *,
    request_id: UUID,
    assessed_on: date,
    evidence: str,
    unit: str = "",
    quantity: Decimal | None = None,
    manufacturer: str = "",
    part_number: str = "",
    serial: str = "",
    batch: str = "",
    specification: str = "",
    shelf_life_basis: str = "",
    shelf_life_to: date | None = None,
    location: StoresLocation | None = None,
    tag: str = "",
) -> PostingEvidence:
    """Append a dated assessment. A later one supersedes it for posting; both are kept."""
    today = aircraft_services.today()
    if assessed_on > today or assessed_on < disposition.disposition_on:
        raise RefusedError("The Assessment Date Must Follow the Movement and Not Be in the Future")
    grant = _authorise(user, Action.RECORD_STORES, StoresAction.POST, assessed_on)
    existing = PostingEvidence.objects.filter(
        organisation_id=disposition.organisation_id, submission=request_id
    ).first()
    if existing is not None:
        return existing
    if posting_kind(disposition) is None:
        raise RefusedError("A Supplier Return Is Kept in History and Never Posted to Stock")
    if quantity is not None and unit and not fits(unit, quantity, serial):
        raise RefusedError("The Quantity Does Not Fit Its Unit or the Serial Number")
    dated = shelf_life_basis in (shelf_life.Basis.THROUGH, shelf_life.Basis.BEFORE)
    if dated != (shelf_life_to is not None):
        raise RefusedError("Give the Shelf-Life Date With a Dated Basis, and Only Then")
    return PostingEvidence.objects.create(
        organisation_id=disposition.organisation_id,
        submission=request_id,
        disposition=disposition,
        unit=unit,
        quantity=quantity,
        manufacturer=manufacturer,
        part_number=part_number,
        serial=serial,
        batch=batch,
        specification=specification,
        shelf_life_basis=shelf_life_basis,
        shelf_life_to=shelf_life_to,
        location=location,
        tag=tag,
        assessed_on=assessed_on,
        evidence=evidence,
        appointment=grant,
    )


def _lock(key: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [key])


@transaction.atomic
def post(user: User, disposition: ReceivingDisposition, *, request_id: UUID) -> StockPosting:
    """Post the disposition once, with its opening movement, in one transaction.

    The posting input is the disposition. A replay that would use the same
    evidence returns the original posting. One that would use other evidence
    is a conflict, and the original posting stands.
    """
    today = aircraft_services.today()
    grant = _authorise(user, Action.RECORD_STORES, StoresAction.POST, today)
    # The same lock the database takes, so a second caller waits and then reads.
    _lock(f"stores-posting:{disposition.pk}")
    evidence = latest_evidence(disposition)
    done = StockPosting.objects.filter(disposition=disposition).first()
    if done is not None:
        if evidence is not None and done.evidence_id == evidence.pk:
            return done
        raise PostingConflictError(
            "This Disposition Is Already Posted From Earlier Evidence. The Original Posting Stands"
        )
    reasons = blockers(disposition, evidence, today)
    kind = posting_kind(disposition)
    if reasons or evidence is None or kind is None or evidence.location is None:
        raise RefusedError(f"{AWAITING}: {'; '.join(reasons)}")
    assert evidence.quantity is not None  # noqa: S101  checked by blockers
    try:
        with transaction.atomic():
            # The database writes the opening movement in the same statement (migration 0008).
            posting = StockPosting.objects.create(
                organisation_id=disposition.organisation_id,
                submission=request_id,
                disposition=disposition,
                evidence=evidence,
                kind=kind,
                location_rules=location_rules(evidence.location),
                posted_on=today,
                appointment=grant,
            )
    except IntegrityError as error:
        raise RefusedError("This Disposition Could Not Be Posted. Reload the Entry") from error
    return posting


# Ledger


def on_hand(posting: StockPosting, location: StoresLocation) -> Decimal:
    with connection.cursor() as cursor:
        cursor.execute("SELECT logistics_stock_on_hand(%s, %s)", [posting.pk, location.pk])
        (value,) = cursor.fetchone()
    return Decimal(value)


def unreserved(posting: StockPosting, location: StoresLocation) -> Decimal:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT logistics_stock_on_hand(%s, %s) - logistics_stock_reserved(%s, %s)",
            [posting.pk, location.pk, posting.pk, location.pk],
        )
        (value,) = cursor.fetchone()
    return Decimal(value)


def _lock_stock(posting: StockPosting) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT logistics_lock_stock(%s)", [posting.pk])


def _movement_retry(posting: StockPosting, request_id: UUID) -> StockMovement | None:
    return StockMovement.objects.filter(
        organisation_id=posting.organisation_id, submission=request_id
    ).first()


@transaction.atomic
def move(
    user: User,
    posting: StockPosting,
    *,
    request_id: UUID,
    source: StoresLocation,
    destination: StoresLocation,
    quantity: Decimal,
    moved_on: date,
    evidence: str,
) -> StockMovement:
    today = aircraft_services.today()
    grant = _authorise(user, Action.RECORD_STORES, StoresAction.MOVE, today)
    _lock_stock(posting)
    if (existing := _movement_retry(posting, request_id)) is not None:
        return existing
    basis = posting.evidence
    if moved_on > today or moved_on < posting.disposition.disposition_on:
        raise RefusedError("The Movement Date Must Follow Arrival and Not Be in the Future")
    if source == destination:
        raise RefusedError("Choose a Different Destination")
    if (
        posting.kind == PostingKind.STOCK
        and source.kind == LocationKind.QUARANTINE
        and destination.kind == LocationKind.SERVICEABLE
    ):
        raise RefusedError(
            "Quarantined Stock Needs a New Receiving Decision Before Serviceable Use"
        )
    if not fits(basis.unit, quantity, basis.serial):
        raise RefusedError("The Quantity Does Not Fit Its Unit or the Serial Number")
    if not accepts(destination, posting.kind, posting.disposition.receipt.classification, today):
        raise RefusedError(
            "A Quarantine Hold Moves Only to Secure Quarantine"
            if posting.kind == PostingKind.HOLD
            else "The Destination Does Not Accept This Item"
        )
    if unreserved(posting, source) < quantity:
        raise RefusedError("The Source Location Holds Less Unreserved Stock Than This Quantity")
    return StockMovement.objects.create(
        organisation_id=posting.organisation_id,
        submission=request_id,
        posting=posting,
        kind=MovementKind.TRANSFER,
        source=source,
        destination=destination,
        quantity=quantity,
        moved_on=moved_on,
        evidence=evidence,
        recorded_on=today,
        appointment=grant,
    )


@transaction.atomic
def count(
    user: User,
    posting: StockPosting,
    *,
    request_id: UUID,
    location: StoresLocation,
    counted: Decimal,
    evidence: str,
) -> StockCount:
    today = aircraft_services.today()
    grant = _authorise(user, Action.RECORD_STORES, StoresAction.COUNT, today)
    _lock_stock(posting)
    existing = StockCount.objects.filter(
        organisation_id=posting.organisation_id, submission=request_id
    ).first()
    if existing is not None:
        return existing
    basis = posting.evidence
    if counted < 0 or (counted and not fits(basis.unit, counted, basis.serial)):
        raise RefusedError("The Count Does Not Fit the Unit")
    return StockCount.objects.create(
        organisation_id=posting.organisation_id,
        submission=request_id,
        posting=posting,
        location=location,
        counted=counted,
        on_hand=ZERO,  # The database writes the ledger value at the count.
        counted_on=today,
        evidence=evidence,
        appointment=grant,
    )


@transaction.atomic
def adjust(user: User, taken: StockCount, *, request_id: UUID, evidence: str) -> StockMovement:
    """Apply a count's variance as a separately authorised movement."""
    today = aircraft_services.today()
    grant = _authorise(user, Action.ADJUST_STOCK, StoresAction.ADJUST, today)
    posting = taken.posting
    _lock_stock(posting)
    if (existing := _movement_retry(posting, request_id)) is not None:
        return existing
    if not evidence.strip():
        raise RefusedError("Give the Evidence for the Adjustment")
    if StockMovement.objects.filter(count=taken).exists():
        raise RefusedError("This Count Has Already Been Applied")
    taken.refresh_from_db()
    variance = taken.variance
    if not variance:
        raise RefusedError("The Count Matches the Ledger. Nothing to Adjust")
    if on_hand(posting, taken.location) != taken.on_hand:
        raise RefusedError("The Ledger Has Moved Since the Count. Count Again")
    if variance < 0 and abs(variance) > unreserved(posting, taken.location):
        raise RefusedError("Release the Reservations Covering the Count Shortfall First")
    return StockMovement.objects.create(
        organisation_id=posting.organisation_id,
        submission=request_id,
        posting=posting,
        kind=MovementKind.ADJUSTMENT,
        source=taken.location if variance < 0 else None,
        destination=taken.location if variance > 0 else None,
        quantity=abs(variance),
        moved_on=taken.counted_on,
        evidence=evidence,
        count=taken,
        recorded_on=today,
        appointment=grant,
    )


# Reading the register


@dataclass(frozen=True)
class Position:
    posting: StockPosting
    location: StoresLocation
    on_hand: Decimal
    shelf: shelf_life.ShelfLife
    reserved: Decimal = ZERO

    @property
    def held(self) -> bool:
        return self.posting.kind == PostingKind.HOLD

    @property
    def available(self) -> Decimal:
        if self.held or not self.shelf.usable or self.location.kind != LocationKind.SERVICEABLE:
            return ZERO
        return max(self.on_hand - self.reserved, ZERO)

    @property
    def unit(self) -> str:
        return self.posting.evidence.unit


def shelf_of(evidence: PostingEvidence, day: date) -> shelf_life.ShelfLife:
    return shelf_life.evaluate(
        evidence.shelf_life_basis, evidence.shelf_life_to, day, SHELF_LIFE_WARNING_DAYS
    )


def positions(
    organisation: Organisation,
    day: date,
    *,
    posting: StockPosting | None = None,
    location: StoresLocation | None = None,
) -> list[Position]:
    """Return every custody position with a nonzero balance, derived from the ledger."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH custody_positions AS (
                SELECT posting_id, source_id, destination_id FROM logistics_stockmovement
                 WHERE organisation_id = %s AND (%s::uuid IS NULL OR posting_id = %s)
                UNION ALL
                SELECT posting_id, source_id, destination_id FROM logistics_stockallocation
                 WHERE organisation_id = %s AND (%s::uuid IS NULL OR posting_id = %s)
            ),
            places AS (
                SELECT posting_id, source_id AS place FROM custody_positions
                UNION
                SELECT posting_id, destination_id FROM custody_positions
            )
            SELECT posting_id, place, logistics_stock_on_hand(posting_id, place),
                   logistics_stock_reserved(posting_id, place)
              FROM places
             WHERE place IS NOT NULL AND (%s::uuid IS NULL OR place = %s)
            """,
            [
                organisation.pk,
                posting.pk if posting else None,
                posting.pk if posting else None,
                organisation.pk,
                posting.pk if posting else None,
                posting.pk if posting else None,
                location.pk if location else None,
                location.pk if location else None,
            ],
        )
        balances = [row for row in cursor.fetchall() if row[2]]
    lots = StockPosting.objects.select_related("evidence", "disposition__receipt").in_bulk(
        {lot for lot, _, _, _ in balances}
    )
    locations = StoresLocation.objects.in_bulk({place for _, place, _, _ in balances})
    result = [
        Position(lots[lot], locations[place], amount, shelf_of(lots[lot].evidence, day), reserved)
        for lot, place, amount, reserved in balances
    ]
    result.sort(
        key=lambda one: (one.location.code, one.posting.disposition.receipt.item, one.posting.pk)
    )
    return result


@dataclass
class Totals:
    unit: str
    on_hand: Decimal = ZERO
    reserved: Decimal = ZERO
    available: Decimal = ZERO


@dataclass(frozen=True)
class LocationTotal:
    location: StoresLocation
    totals: list[Totals] = field(default_factory=list)


def totals(lines: list[Position]) -> dict[str, Totals]:
    result: dict[str, Totals] = {}
    for line in lines:
        total = result.setdefault(line.unit, Totals(line.unit))
        total.on_hand += line.on_hand
        total.reserved += line.reserved
        total.available += line.available
    return result


def by_location(
    lines: list[Position],
    configured: Iterable[StoresLocation] = (),
) -> list[LocationTotal]:
    grouped: dict[UUID, list[Position]] = defaultdict(list)
    places = {location.pk: location for location in configured}
    units = sorted({line.unit for line in lines}) or [""]
    for line in lines:
        grouped[line.location.pk].append(line)
        places[line.location.pk] = line.location
    return [
        LocationTotal(
            location,
            list(totals(grouped[location.pk]).values()) or [Totals(unit) for unit in units],
        )
        for location in sorted(places.values(), key=lambda place: (place.station, place.code))
    ]


def by_station(places: list[LocationTotal]) -> dict[str, list[Totals]]:
    grouped: dict[str, dict[str, Totals]] = defaultdict(dict)
    for place in places:
        station = place.location.station
        if not station:
            continue
        for value in place.totals:
            total = grouped[station].setdefault(value.unit, Totals(value.unit))
            total.on_hand += value.on_hand
            total.reserved += value.reserved
            total.available += value.available
    return {station: list(group.values()) for station, group in sorted(grouped.items())}


def quantity_text(quantity: Decimal | None, unit: str) -> str:
    """Show a quantity exactly in its unit. With no unit only a zero can be shown."""
    if quantity is None:
        return ""
    shown = f"{quantity.normalize():f}"
    if not unit:
        return shown
    if unit == StockUnit.LITRE:
        return f"{shown} L"
    return shown
