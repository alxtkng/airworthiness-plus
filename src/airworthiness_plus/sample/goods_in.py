"""The illustrative Goods In receipt and inspection histories."""

from dataclasses import dataclass
from datetime import date

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import receiving, services
from airworthiness_plus.logistics.models import (
    CheckKind,
    CheckOutcome,
    Destination,
    ItemClass,
    Receipt,
)
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.people.models import Person, StaffGroup
from airworthiness_plus.sample.models import Added, Part


@dataclass(frozen=True)
class Example:
    line: str
    item: str
    day: date
    item_reference: str
    release_document: str = "CAA Form 1, Sample Tracking Number"
    source: str = "[Parts Distributor]"
    intended_use: str = ""
    classification: ItemClass = ItemClass.SERVICEABLE
    disposition: Destination | None = None
    location: str = ""
    evidence: str = ""
    failed_checks: tuple[CheckKind, ...] = ()
    inspector: str = "Chris Moore"
    moved_on: date | None = None


RECEIPTS = (
    Example(
        "RX-001",
        "Emergency Locator Transmitter Battery",
        date(2026, 11, 18),
        "[Battery Part and Serial Number]",
        intended_use="G-ABCD, 100-Hour Check",
    ),
    Example(
        "RX-002",
        "Stabilator Trim Cable Assembly",
        date(2026, 11, 16),
        "[Eligible Cable Part and Serial Number]",
        intended_use="G-DGHI, WP-2026-046",
        disposition=Destination.STORES,
        location="[Serviceable Stores Bay]",
        evidence="Replacement Suffix Checked Against the G-DGHI Configuration",
    ),
    Example(
        "RX-003",
        "Stabilator Trim Cable Assembly",
        date(2026, 11, 15),
        "[Ineligible Cable Part and Serial Number]",
        intended_use="G-DGHI, WP-2026-046",
        disposition=Destination.RETURN,
        location="[Parts Distributor]",
        evidence="Part Number Suffix Does Not Match G-DGHI Modification Status",
        failed_checks=(CheckKind.IDENTITY,),
    ),
    Example(
        "RX-004",
        "Alternator",
        date(2026, 11, 6),
        "[Alternator Part and Serial Number]",
        source="Owner Supplied",
        intended_use="G-FMNO",
        disposition=Destination.QUARANTINE,
        location="[Secure Quarantine Store]",
        evidence="Serial Number Mismatch. Separate Sample CAA Report Dated 7 November 2026",
        failed_checks=(CheckKind.DOCUMENT, CheckKind.SUSPECT),
    ),
    Example(
        "RX-005",
        "Engine Oil",
        date(2026, 10, 28),
        "[Oil Batch Number]",
        source="[Oil Supplier]",
        release_document="",
        classification=ItemClass.MATERIAL,
        disposition=Destination.RETURN,
        location="[Oil Supplier]",
        evidence="Batch Without Conformity Evidence. Returned 29 October",
        failed_checks=(CheckKind.DOCUMENT,),
        inspector="Sam Patel",
        moved_on=date(2026, 10, 29),
    ),
)
PASSED = {
    CheckKind.SOURCE: "Sample Delivery and Order Matched",
    CheckKind.DOCUMENT: "Sample Release Evidence Matched to the Item",
    CheckKind.IDENTITY: "Sample Reference Checked Against the Intended Application",
    CheckKind.CONDITION: "Sample Condition and Packaging Satisfactory",
    CheckKind.SHELF: "No Shelf Life Recorded for This Sample Assembly",
    CheckKind.SUSPECT: "Sample Markings, Evidence and Source Checked",
}


def _add_receipt(
    organisation: Organisation, example: Example, inspectors: dict[str, Person]
) -> None:
    receipt = receiving.receive(
        organisation,
        item=example.item,
        received_on=example.day,
        classification=example.classification,
        source=example.source,
        item_reference=example.item_reference,
        quantity=1,
        delivery_reference=example.line,
        release_document=example.release_document,
        intended_use=example.intended_use,
    )
    checks = (
        PASSED
        if example.disposition == Destination.STORES
        else {
            CheckKind.SOURCE: PASSED[CheckKind.SOURCE],
            CheckKind.DOCUMENT: PASSED[CheckKind.DOCUMENT],
        }
    )
    checks = {**checks, **dict.fromkeys(example.failed_checks, example.evidence)}
    for kind, evidence in checks.items():
        outcome = CheckOutcome.PASS
        if kind in example.failed_checks:
            outcome = CheckOutcome.FAIL
        elif kind == CheckKind.SHELF:
            outcome = CheckOutcome.NOT_APPLICABLE
        receiving.record_check(
            receipt,
            check=kind,
            outcome=outcome,
            checked_on=example.day,
            evidence=evidence,
        )
    person = inspectors.get(example.inspector)
    if example.disposition is not None and person is not None:
        receiving.dispose(
            receipt,
            approval=ApprovalType.PART_CAO,
            inspector=person,
            inspector_authority="[Sample Receiving Inspection Authorisation]",
            inspected_on=example.day,
            disposition_on=example.moved_on or example.day,
            outcome=example.disposition,
            destination=example.location,
            evidence=example.evidence,
        )


def add(organisation: Organisation, actor: User) -> int:
    """Bring the primary sample up to date without changing existing receipts."""
    with working_for(organisation.id, actor.id), transaction.atomic():
        organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
        if Added.objects.filter(part=Part.GOODS_IN).exists():
            return 0
        if not any(
            approval.approval == ApprovalType.PART_CAO
            for approval in services.maintenance_approvals(organisation, RECEIPTS[0].day)
        ):
            return 0
        # If a sample staff member was renamed or left there is no assumed match.
        inspectors = {}
        for name in {example.inspector for example in RECEIPTS}:
            matches = list(Person.objects.filter(full_name=name, staff_group=StaffGroup.CERTIFYING))
            if len(matches) == 1 and matches[0].left_on is None:
                inspectors[name] = matches[0]
        existing = {
            key.lower() for key in Receipt.objects.values_list("delivery_reference", flat=True)
        }
        count = 0
        for example in RECEIPTS:
            if example.line.lower() not in existing:
                _add_receipt(organisation, example, inspectors)
                count += 1
        Added.objects.create(organisation=organisation, part=Part.GOODS_IN)
        return count
