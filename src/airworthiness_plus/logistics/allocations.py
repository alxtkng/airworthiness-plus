"""Reservation and issue against issued work, with segregated returns."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.contracts.models import WorkOrder
from airworthiness_plus.logistics import stock_appointments, stores
from airworthiness_plus.logistics.models import (
    AllocationKind,
    LocationKind,
    StockAllocation,
    StockDuty,
    StockPosting,
    StockSubstitution,
    StoreLocation,
)
from airworthiness_plus.logistics.services import RefusedError
from airworthiness_plus.planning.models import WorkCard, WorkPackage


def check_eligible_work(card: WorkCard, today: date) -> WorkCard:
    package = WorkPackage.objects.select_for_update(no_key=True).get(pk=card.package_id)
    current = WorkCard.objects.select_related("revision").get(pk=card.pk)
    order = (
        WorkOrder.objects.select_for_update(no_key=True).get(pk=package.order_id)
        if package.order_id is not None
        else None
    )
    if (
        not current.revision_id
        or current.completed_on is not None
        or package.issued_on is None
        or package.issued_on > today
        or package.released_on is not None
        or order is None
        or order.agreed_on > today
        or order.closed_on is not None
        or order.aircraft_id != package.aircraft_id
    ):
        raise RefusedError(
            "Choose an Unfinished Card on an Issued Package With an Open Written Order"
        )

    return current


def _check_serviceable(posting: StockPosting, source: StoreLocation, today: date) -> str:
    receipt = posting.disposition.receipt
    if (
        not source.active
        or source.kind != LocationKind.SERVICEABLE
        or not source.accepts(receipt.classification)
    ):
        raise RefusedError("This Location Does Not Hold Serviceable Stock for Issue")
    if stores.lot_shelf(posting, today, 0) not in stores.USABLE:
        raise RefusedError("The Lot's Shelf Life Blocks Issue")
    return (posting.part_number or posting.specification).strip().upper()


def check_substitution(
    approval: StockSubstitution,
    card: WorkCard,
    posting: StockPosting,
    identity: str,
    required: str,
    reference: str,
    on: date,
) -> None:
    if (
        approval.posting_id != posting.pk
        or approval.card_id != card.pk
        or approval.required_identity != required
        or approval.substitute_identity != identity
        or approval.applicable_source != reference
        or approval.recorded_on > on
    ):
        raise RefusedError(
            "The Alternate Approval Must Match This Work Card, Lot and Applicable Data"
        )
    if (
        card.revision is None
        or approval.revision_id != card.revision_id
        or not card.revision.current
    ):
        raise RefusedError("The Approved Alternate Belongs to a Stale Work Card Revision")
    if approval.authorisation.term_on(on) != "Within Recorded Dates":
        raise RefusedError(
            "The Alternate's Maintenance Authorisation Has Expired or Been Withdrawn"
        )


def appointment_action(kind: AllocationKind) -> StockDuty:
    return StockDuty.RESERVE if kind == AllocationKind.RELEASE else StockDuty(kind)


@transaction.atomic
def record(
    user: User,
    posting: StockPosting,
    kind: AllocationKind,
    *,
    request_id: UUID,
    evidence: str,
    source: StoreLocation | None = None,
    destination: StoreLocation | None = None,
    card: WorkCard | None = None,
    preceding: StockAllocation | None = None,
    substitution: StockSubstitution | None = None,
    quantity: Decimal | None = None,
    required_identity: str = "",
    applicable_source: str = "",
) -> StockAllocation:
    today = aircraft_services.today()
    action = appointment_action(kind)
    grant = stock_appointments.current(user, action, today)
    if grant is None:
        raise RefusedError("A Current Stores Appointment Is Required for This Action")
    organisation = user.organisation_id
    if any(
        one is not None and one.organisation_id != organisation
        for one in (posting, preceding, source, destination, card, substitution)
    ):
        raise RefusedError("Choose Records of This Organisation")
    if preceding is not None:
        expected = AllocationKind.ISSUE if kind == AllocationKind.RETURN else AllocationKind.RESERVE
        if preceding.kind != expected or preceding.posting_id != posting.pk:
            raise RefusedError("Continue the Original Custody Record")
        quantity = preceding.quantity
        source = preceding.source if kind != AllocationKind.RETURN else None
        card = preceding.card
        substitution = preceding.substitution
        required_identity = preceding.required_identity
        applicable_source = preceding.applicable_source
    evidence = evidence.strip()
    required_identity = required_identity.strip().upper()
    applicable_source = applicable_source.strip()
    if not evidence or quantity is None:
        raise RefusedError("Give the Quantity and Custody Evidence")
    stock_appointments.lock_submission(f"stores-allocation:{organisation}", request_id)
    stores._lock_lot(posting)
    posting = StockPosting.objects.select_related("disposition__receipt").get(pk=posting.pk)
    existing = StockAllocation.objects.filter(
        organisation_id=organisation, submission=request_id
    ).first()
    if existing is not None:
        if (
            existing.posting_id != posting.pk
            or existing.kind != kind
            or existing.preceding_id != (preceding.pk if preceding else None)
            or existing.source_id != (source.pk if source else None)
            or existing.destination_id != (destination.pk if destination else None)
            or existing.card_id != (card.pk if card else None)
            or existing.substitution_id != (substitution.pk if substitution else None)
            or existing.quantity != quantity
            or existing.required_identity != required_identity
            or existing.applicable_source != applicable_source
            or existing.evidence != evidence
            or existing.appointment.person.user_id != user.pk
        ):
            raise RefusedError("This Submission Was Already Used for Different Custody Evidence")
        return existing
    if preceding is not None and StockAllocation.objects.filter(preceding=preceding).exists():
        raise RefusedError("This Custody Record Has Already Been Continued")
    if posting.held or today < posting.posted_on:
        raise RefusedError("Only a Serviceable Stock Posting Can Be Allocated")
    quantity = stores.checked_quantity(quantity, posting.unit)
    if posting.serial_number and quantity != 1:
        raise RefusedError("A Serialised Item Moves Whole")
    if kind in (AllocationKind.RESERVE, AllocationKind.ISSUE):
        if source is None or card is None or not applicable_source:
            raise RefusedError("Identify the Source, Work Card and Applicable Parts Data")
        identity = _check_serviceable(posting, source, today)
        current_card = check_eligible_work(card, today)
        if substitution is None:
            if not identity or identity != required_identity:
                raise RefusedError(
                    "The Required Part Number or Specification Must Match the Received Lot"
                )
        else:
            substitution = StockSubstitution.objects.select_related(
                "authorisation__withdrawal"
            ).get(pk=substitution.pk)
            check_substitution(
                substitution,
                current_card,
                posting,
                identity,
                required_identity,
                applicable_source,
                today,
            )
    if kind in (AllocationKind.RESERVE, AllocationKind.QUARANTINE):
        if source is None or stores.unreserved(posting, source) < quantity:
            raise RefusedError("The Source Holds Less Unreserved Stock Than This Quantity")
    if kind in (AllocationKind.RETURN, AllocationKind.QUARANTINE):
        if (
            destination is None
            or destination == source
            or destination.kind != LocationKind.QUARANTINE
            or not destination.active
            or not destination.secure
            or not destination.accepts(posting.disposition.receipt.classification)
        ):
            raise RefusedError("Choose a Different Active, Secure Quarantine Location")
    try:
        with transaction.atomic():
            return StockAllocation.objects.create(
                organisation_id=organisation,
                posting=posting,
                kind=kind,
                source=source,
                destination=destination,
                card=card,
                preceding=preceding,
                substitution=substitution,
                required_identity=required_identity,
                applicable_source=applicable_source,
                quantity=quantity,
                evidence=evidence,
                recorded_on=today,
                submission=request_id,
                appointment=grant,
            )
    except IntegrityError as error:
        raise RefusedError(
            "Custody Changed or Its Evidence Is Incomplete. Reload the Lot."
        ) from error
