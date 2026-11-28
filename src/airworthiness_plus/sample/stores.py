"""Fictitious Stores locations, appointments and postings for the primary sample (REQ-358).

RX-002 stays Awaiting Stock Posting and RX-004 stays a quarantine hold with
details to verify, as the Goods In sample left them. RX-006 is engine oil
posted to Bay C. RX-007 is a batch of bolts posted at 50 and counted at 46,
with the adjustment left for a separately authorised person.
"""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import receiving, stores
from airworthiness_plus.logistics.models import (
    CheckKind,
    CheckOutcome,
    Destination,
    DocumentKind,
    ItemClass,
    LocationKind,
    Receipt,
    ShelfLifeBasis,
    StockUnit,
    StoresAction,
    StoresAppointment,
    StoresLocation,
)
from airworthiness_plus.logistics.services import maintenance_approvals
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.people.models import Person, StaffGroup

STARTS = date(2026, 11, 1)
RECEIVED = date(2026, 11, 17)
STORES_PERSON = "lucy.grant@your-organisation.example"
PLANNER = "planning@your-organisation.example"
EXPOSITION = "Fictitious sample exposition, Stores procedure 2.4, demonstration revision"

LOCATIONS = (
    ("BAY-A", "Bay A, Serviceable Components", LocationKind.SERVICEABLE,
     [ItemClass.SERVICEABLE, ItemClass.STANDARD], "Dry, 10 to 25 °C, racked", False),
    ("BAY-B", "Bay B, Standard Parts Drawers", LocationKind.SERVICEABLE,
     [ItemClass.STANDARD], "Dry, labelled drawers", False),
    ("BAY-C", "Bay C, Oils and Materials", LocationKind.SERVICEABLE,
     [ItemClass.MATERIAL], "Bunded shelving, 5 to 30 °C, away from heat", False),
    ("OIL-2", "Hangar Oil Store", LocationKind.SERVICEABLE,
     [ItemClass.MATERIAL], "Bunded cabinet, 5 to 30 °C", False),
    ("QUAR-1", "Quarantine Store, Locked", LocationKind.QUARANTINE,
     list(ItemClass.values), "Locked cage, key held by Stores", True),
    ("BAY-D", "Former Bay D", LocationKind.SERVICEABLE,
     [ItemClass.SERVICEABLE], "Dry shelving", False),
)  # fmt: skip


def submission(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"airworthiness-plus/sample/stores/{key}")


def _person(username: str) -> Person | None:
    return (
        Person.objects.select_related("user")
        .filter(user__username=username, user__is_active=True)
        .first()
    )


def _receipt(
    organisation: Organisation,
    inspector: Person,
    *,
    line: str,
    item: str,
    classification: ItemClass,
    quantity: int,
    source: str,
    reference: str,
    basis: str,
    manufacturing: str = "",
    supplier_source: str = "",
) -> Receipt:
    receipt = receiving.receive(
        organisation,
        item=item,
        received_on=RECEIVED,
        classification=classification,
        source=source,
        item_reference=reference,
        quantity=quantity,
        delivery_reference=line,
        release_document="Certificate of Conformity With the Delivery",
    )
    for kind in CheckKind:
        receiving.record_check(
            receipt,
            check=kind,
            outcome=CheckOutcome.PASS,
            checked_on=RECEIVED,
            evidence=f"Sample {kind.label} Checked for {line}",
        )
    receiving.dispose(
        receipt,
        approval=ApprovalType.PART_CAO,
        inspector=inspector,
        inspector_authority="[Sample Receiving Inspection Authorisation]",
        inspected_on=RECEIVED,
        disposition_on=RECEIVED,
        outcome=Destination.STORES,
        destination="[Stores]",
        evidence=f"Sample Conformity Evidence Matched to {line}",
        document_kind=DocumentKind.CONFORMITY,
        document_reference=f"[Sample Conformity Folder / {line}]",
        evidence_basis=basis,
        manufacturing_source=manufacturing,
        material_supplier_source=supplier_source,
    )
    return receipt


def add(organisation: Organisation, administrator: User) -> int:
    """Add the missing fictitious Stores records without changing existing ones."""
    with working_for(organisation.pk, administrator.pk), transaction.atomic():
        organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
        if organisation.approval_reference != "UK.CAO.[Number]":
            return 0
        if StoresLocation.objects.filter(code__iexact="BAY-A").exists():
            return 0
        today = aircraft_services.today()
        term = next(
            (
                one
                for one in maintenance_approvals(organisation, today)
                if one.approval == ApprovalType.PART_CAO
            ),
            None,
        )
        reference = term.reference_on(today) if term else None
        keeper, planner = _person(STORES_PERSON), _person(PLANNER)
        inspectors = list(
            Person.objects.filter(full_name="Chris Moore", staff_group=StaffGroup.CERTIFYING)
        )
        if (
            term is None
            or reference is None
            or keeper is None
            or keeper.user is None
            or not keeper.user.may(Action.RECORD_STORES)
            or not keeper.user.may(Action.ADJUST_STOCK)
            or len(inspectors) != 1
        ):
            return 0
        for action in StoresAction:
            StoresAppointment.objects.create(
                organisation=organisation,
                submission=submission(action),
                person=keeper,
                approval=term,
                approval_reference=reference,
                action=action,
                starts_on=STARTS,
                ends_on=date(2099, 12, 31),
                exposition_reference=EXPOSITION,
                authority="Fictitious example of a signed Stores appointment",
            )
        if planner is not None:
            ended = StoresAppointment.objects.create(
                organisation=organisation,
                submission=submission("planner-move"),
                person=planner,
                approval=term,
                approval_reference=reference,
                action=StoresAction.MOVE,
                starts_on=STARTS,
                ends_on=date(2099, 12, 31),
                exposition_reference=EXPOSITION,
                authority="Fictitious example of a temporary Stores appointment",
            )
            stores.withdraw_appointment(
                administrator,
                ended,
                request_id=submission("planner-move-withdrawn"),
                evidence="Fictitious example. Temporary cover ended",
            )
        with working_for(organisation.pk, keeper.user.pk):
            user = keeper.user
            places = {
                code: stores.record_location(
                    user,
                    request_id=submission(f"location-{code}"),
                    code=code,
                    name=name,
                    kind=kind,
                    classes=list(classes),
                    storage_conditions=conditions,
                    secure=secure,
                )
                for code, name, kind, classes, conditions, secure in LOCATIONS
            }
            stores.withdraw_location(
                user,
                places["BAY-D"],
                request_id=submission("location-BAY-D-withdrawn"),
                evidence="Fictitious example. Bay D emptied and taken out of use",
            )
            oil = _receipt(
                organisation,
                inspectors[0],
                line="RX-006",
                item="Engine Oil",
                classification=ItemClass.MATERIAL,
                quantity=24,
                source="[Oil Supplier]",
                reference="[Oil Specification], Batch [Oil Batch Number], 24 One-Litre Bottles",
                basis="[Oil Specification]",
                manufacturing="[Oil Manufacturer]",
                supplier_source="[Oil Supplier]",
            )
            bolts = _receipt(
                organisation,
                inspectors[0],
                line="RX-007",
                item="Bolts",
                classification=ItemClass.STANDARD,
                quantity=50,
                source="[Parts Distributor]",
                reference="[Bolt Standard], Batch [Bolt Batch Number]",
                basis="[Bolt Standard]",
            )
            postings: tuple[tuple[Receipt, dict[str, Any]], ...] = (
                (
                    oil,
                    {
                        "unit": StockUnit.LITRE,
                        "quantity": Decimal(24),
                        "manufacturer": "[Oil Manufacturer]",
                        "specification": "[Oil Specification]",
                        "batch": "[Oil Batch Number]",
                        "shelf_life_basis": ShelfLifeBasis.THROUGH,
                        "shelf_life_to": date(2029, 8, 31),
                        "location": places["BAY-C"],
                    },
                ),
                (
                    bolts,
                    {
                        "unit": StockUnit.EACH,
                        "quantity": Decimal(50),
                        "specification": "[Bolt Standard]",
                        "batch": "[Bolt Batch Number]",
                        "shelf_life_basis": ShelfLifeBasis.NOT_APPLICABLE,
                        "location": places["BAY-B"],
                    },
                ),
            )
            for receipt, values in postings:
                decision = receipt.disposition
                stores.record_posting_evidence(
                    user,
                    decision,
                    request_id=submission(f"evidence-{receipt.delivery_reference}"),
                    assessed_on=today,
                    evidence=f"Fictitious example. Conformity evidence and label for "
                    f"{receipt.delivery_reference} checked against the receipt",
                    **values,
                )
                stores.post(
                    user, decision, request_id=submission(f"post-{receipt.delivery_reference}")
                )
            stores.count(
                user,
                bolts.disposition.posting,
                request_id=submission("count-RX-007"),
                location=places["BAY-B"],
                counted=Decimal(46),
                evidence="Fictitious example. Drawer 7 counted at 46. Adjustment to be authorised",
            )
        return 2
