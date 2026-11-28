"""Record incoming items, the checks made on them, and their first disposition."""

from datetime import date

from django.db import IntegrityError, connection, transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.models import (
    CheckKind,
    CheckOutcome,
    Destination,
    ItemClass,
    Receipt,
    ReceivingCheck,
    ReceivingDisposition,
)
from airworthiness_plus.logistics.services import RefusedError, maintenance_approvals
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Person


@transaction.atomic
def receive(
    organisation: Organisation,
    *,
    item: str,
    received_on: date,
    classification: str,
    source: str,
    item_reference: str,
    quantity: int,
    delivery_reference: str,
    release_document: str = "",
    intended_use: str = "",
    shelf_life_to: date | None = None,
) -> Receipt:
    """Record the item as received. Inspection and disposition follow separately."""
    if received_on > aircraft_services.today():
        raise RefusedError("The Receipt Date Cannot Be in the Future")
    try:
        with transaction.atomic():
            return Receipt.objects.create(
                organisation=organisation,
                item=item,
                received_on=received_on,
                classification=classification,
                source=source,
                item_reference=item_reference,
                quantity=quantity,
                delivery_reference=delivery_reference,
                release_document=release_document,
                intended_use=intended_use,
                shelf_life_to=shelf_life_to,
            )
    except IntegrityError as error:
        if Receipt.objects.filter(
            organisation=organisation, delivery_reference__iexact=delivery_reference
        ).exists():
            raise RefusedError(
                "This Delivery Line Is Already Recorded. Open Its Receipt"
            ) from error
        raise


def _lock_open_receipt(receipt: Receipt) -> None:
    # The two insert triggers take this same transaction lock. The receipt itself is immutable.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [str(receipt.pk)])
    if ReceivingDisposition.objects.filter(receipt=receipt).exists():
        raise RefusedError("This Receipt Already Has a Final Disposition")


@transaction.atomic
def record_check(
    receipt: Receipt,
    *,
    check: str,
    outcome: str,
    checked_on: date,
    evidence: str,
) -> ReceivingCheck:
    """Append an observation. Keep earlier observations visible."""
    _lock_open_receipt(receipt)
    if not receipt.received_on <= checked_on <= aircraft_services.today():
        raise RefusedError("The Check Date Must Be on or After Receipt and No Later Than Today")
    if outcome == CheckOutcome.NOT_APPLICABLE and check != CheckKind.SHELF:
        raise RefusedError("Choose Pass or Fail for This Check")
    if (
        check == CheckKind.SHELF
        and outcome == CheckOutcome.NOT_APPLICABLE
        and receipt.shelf_life_to
    ):
        raise RefusedError("The Receipt Has a Recorded Shelf Life")
    if receipt.checks.filter(
        kind=check, outcome=outcome, checked_on=checked_on, evidence=evidence
    ).exists():
        raise RefusedError("This Check Is Already Recorded")
    return ReceivingCheck.objects.create(
        organisation_id=receipt.organisation_id,
        receipt=receipt,
        kind=check,
        outcome=outcome,
        checked_on=checked_on,
        evidence=evidence,
    )


def current_checks(checks: list[ReceivingCheck]) -> dict[str, ReceivingCheck]:
    """Select the latest observation of each check from the model's ordered history."""
    current: dict[str, ReceivingCheck] = {}
    for record in checks:
        current.setdefault(record.kind, record)
    return current


def _check_stores(receipt: Receipt, checks: dict[str, ReceivingCheck], moved_on: date) -> None:
    if receipt.shelf_life_to is not None and moved_on > receipt.shelf_life_to:
        raise RefusedError("The Recorded Shelf Life Has Passed by the Movement Date")
    for kind in CheckKind:
        record = checks.get(kind)
        if record is None or record.outcome == CheckOutcome.FAIL:
            raise RefusedError("All Applicable Checks Must Pass Before Acceptance into Stores")


@transaction.atomic
def dispose(
    receipt: Receipt,
    *,
    approval: str,
    inspector: Person,
    inspector_authority: str,
    inspected_on: date,
    disposition_on: date,
    outcome: str,
    destination: str,
    evidence: str,
) -> ReceivingDisposition:
    """Keep once-only disposition and the dated inspector and approval evidence."""
    _lock_open_receipt(receipt)
    if not receipt.received_on <= inspected_on <= disposition_on <= aircraft_services.today():
        raise RefusedError("Give Receipt, Inspection and Movement in Date Order")
    if (
        inspector.organisation_id != receipt.organisation_id
        or (inspector.joined_on is not None and inspector.joined_on > inspected_on)
        or (inspector.left_on is not None and inspector.left_on < inspected_on)
    ):
        raise RefusedError("Choose a Person of the Organisation on the Inspection Date")
    term = next(
        (
            one
            for one in maintenance_approvals(receipt.organisation, inspected_on)
            if one.approval == approval
        ),
        None,
    )
    reference = term.reference_on(inspected_on) if term is not None else None
    if term is None or reference is None:
        raise RefusedError(f"The Organisation Held No {approval} Maintenance Approval on This Day")
    recorded = list(receipt.checks.all())
    if recorded and recorded[0].checked_on > inspected_on:
        raise RefusedError("The Inspection Decision Cannot Precede a Recorded Check")
    checks = current_checks(recorded)
    suspect = checks.get(CheckKind.SUSPECT)
    if suspect is not None and suspect.outcome == CheckOutcome.FAIL:
        if outcome != Destination.QUARANTINE:
            raise RefusedError("A Suspected Unapproved Part Must Go to Quarantine")
    if (
        receipt.classification in (ItemClass.UNSERVICEABLE, ItemClass.UNSALVAGEABLE)
        and outcome != Destination.QUARANTINE
    ):
        raise RefusedError("An Unserviceable or Unsalvageable Item Must Go to Quarantine")
    if outcome == Destination.STORES:
        _check_stores(receipt, checks, disposition_on)
    return ReceivingDisposition.objects.create(
        organisation_id=receipt.organisation_id,
        receipt=receipt,
        approval=term,
        approval_reference=reference,
        inspector=inspector,
        inspector_name=inspector.full_name,
        inspector_authority=inspector_authority,
        inspected_on=inspected_on,
        disposition_on=disposition_on,
        outcome=outcome,
        destination=destination,
        evidence=evidence,
    )
