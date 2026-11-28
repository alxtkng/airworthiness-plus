"""Reservation and issue against issued work, with segregated returns."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import IntegrityError, transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.contracts.models import WorkOrder
from airworthiness_plus.logistics import stores
from airworthiness_plus.logistics.models import (
    AllocationKind,
    LocationKind,
    PostingKind,
    StockAllocation,
    StockPosting,
    StoresAction,
    StoresLocation,
)
from airworthiness_plus.logistics.services import RefusedError
from airworthiness_plus.planning.models import WorkCard, WorkPackage


def _check_work(card: WorkCard, today: date) -> None:
    package = WorkPackage.objects.select_for_update(no_key=True).get(pk=card.package_id)
    current = WorkCard.objects.get(pk=card.pk)
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


def _check_serviceable(
    posting: StockPosting, source: StoresLocation, required_identity: str, today: date
) -> None:
    receipt = posting.disposition.receipt
    if not stores.accepts(source, PostingKind.STOCK, receipt.classification, today):
        raise RefusedError("This Location Does Not Hold Serviceable Stock for Issue")
    if not stores.shelf_of(posting.evidence, today).usable:
        raise RefusedError("The Lot's Shelf Life Blocks Issue")
    if (
        not required_identity
        or required_identity
        != (posting.evidence.part_number or posting.evidence.specification).strip().upper()
    ):
        raise RefusedError("The Required Part Number or Specification Must Match the Received Lot")


def appointment_action(kind: AllocationKind) -> StoresAction:
    return StoresAction.RESERVE if kind == AllocationKind.RELEASE else StoresAction(kind)


@transaction.atomic
def record(
    user: User,
    posting: StockPosting,
    kind: AllocationKind,
    *,
    request_id: UUID,
    evidence: str,
    source: StoresLocation | None = None,
    destination: StoresLocation | None = None,
    card: WorkCard | None = None,
    preceding: StockAllocation | None = None,
    quantity: Decimal | None = None,
    required_identity: str = "",
    applicable_source: str = "",
) -> StockAllocation:
    today = aircraft_services.today()
    action = appointment_action(kind)
    grant = stores._authorise(user, Action.RECORD_STORES, action, today)
    organisation = user.organisation_id
    if any(
        one is not None and one.organisation_id != organisation
        for one in (posting, preceding, source, destination, card)
    ):
        raise RefusedError("Choose Records of This Organisation")
    if preceding is not None:
        expected = AllocationKind.ISSUE if kind == AllocationKind.RETURN else AllocationKind.RESERVE
        if preceding.kind != expected or preceding.posting_id != posting.pk:
            raise RefusedError("Continue the Original Custody Record")
        quantity = preceding.quantity
        source = preceding.source if kind != AllocationKind.RETURN else None
        card = preceding.card
        required_identity = preceding.required_identity
        applicable_source = preceding.applicable_source
    evidence = evidence.strip()
    required_identity = required_identity.strip().upper()
    applicable_source = applicable_source.strip()
    if not evidence or quantity is None:
        raise RefusedError("Give the Quantity and Custody Evidence")
    stores._lock(f"stores-allocation-submission:{organisation}:{request_id}")
    stores._lock_stock(posting)
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
    if posting.kind != PostingKind.STOCK or today < posting.posted_on:
        raise RefusedError("Only a Serviceable Stock Posting Can Be Allocated")
    basis = posting.evidence
    if not stores.fits(basis.unit, quantity, basis.serial):
        raise RefusedError("The Quantity Does Not Fit Its Unit or the Serial Number")
    if kind in (AllocationKind.RESERVE, AllocationKind.ISSUE):
        if source is None or card is None or not applicable_source:
            raise RefusedError("Identify the Source, Work Card and Applicable Parts Data")
        _check_serviceable(posting, source, required_identity, today)
        _check_work(card, today)
    if kind in (AllocationKind.RESERVE, AllocationKind.QUARANTINE):
        if source is None or stores.unreserved(posting, source) < quantity:
            raise RefusedError("The Source Holds Less Unreserved Stock Than This Quantity")
    if kind in (AllocationKind.RETURN, AllocationKind.QUARANTINE):
        if (
            destination is None
            or destination == source
            or destination.kind != LocationKind.QUARANTINE
            or not stores.accepts(
                destination, PostingKind.HOLD, posting.disposition.receipt.classification, today
            )
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
