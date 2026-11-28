"""Fictitious Stores appointments, locations and postings for the primary sample (REQ-358).

RX-002 stays Awaiting Stock Posting and RX-004 stays a quarantine hold with details
to verify, as the Goods In sample left them. RX-006 is engine oil posted to Bay C, so
a move between oil stores can be shown. RX-007 is a batch of bolts posted at 50 and
counted at 46, with the adjustment left for the person who holds that appointment.
"""

from datetime import date, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import receiving, stock_appointments, stores
from airworthiness_plus.logistics.models import (
    CheckKind,
    CheckOutcome,
    Destination,
    DocumentKind,
    ItemClass,
    LocationKind,
    Receipt,
    ShelfLifeBasis,
    ShelfLifeRule,
    StockDuty,
    StockUnit,
    StoreLocation,
)
from airworthiness_plus.logistics.services import maintenance_approvals
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.people.models import Person, StaffGroup

DAY = date(2026, 11, 18)
RECEIVED = DAY - timedelta(days=1)
KEEPER = "lucy.grant@your-organisation.example"
AUTHORITY = "Fictitious sample exposition, Stores procedure 2.4, demonstration revision"

# Name, kind, components, standard parts, materials, conditions.
LOCATIONS = (
    (
        "Bay B, Standard Parts Drawers",
        LocationKind.SERVICEABLE,
        False,
        True,
        False,
        "Dry, labelled drawers",
    ),
    (
        "Bay C, Oils and Materials",
        LocationKind.SERVICEABLE,
        False,
        False,
        True,
        "Bunded shelving, 5 to 30 °C",
    ),
    (
        "Hangar Oil Store",
        LocationKind.SERVICEABLE,
        False,
        False,
        True,
        "Bunded cabinet, 5 to 30 °C",
    ),
    (
        "Quarantine Store, Locked",
        LocationKind.QUARANTINE,
        True,
        True,
        True,
        "Locked cage, key held by Stores",
    ),
)


def submission(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"airworthiness-plus/sample/stores/{key}")


def _accepted(
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
) -> Receipt:
    arrival = receiving.receive(
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
            arrival,
            check=kind,
            outcome=CheckOutcome.PASS,
            checked_on=RECEIVED,
            evidence=f"Sample {kind.label} Checked for {line}",
        )
    receiving.dispose(
        arrival,
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
        material_supplier_source=source if manufacturing else "",
    )
    return arrival


def add(organisation: Organisation, administrator: User) -> int:
    """Add the missing fictitious Stores records without changing existing ones."""
    with working_for(organisation.pk, administrator.pk), transaction.atomic():
        organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
        if organisation.approval_reference != "UK.CAO.[Number]":
            return 0
        if StoreLocation.objects.filter(name__iexact=LOCATIONS[0][0]).exists():
            return 0
        if Receipt.objects.filter(delivery_reference__in=["RX-006", "RX-007"]).exists():
            return 0
        keeper = (
            Person.objects.select_related("user")
            .filter(user__username=KEEPER, user__is_active=True)
            .first()
        )
        inspectors = list(
            Person.objects.filter(full_name="Chris Moore", staff_group=StaffGroup.CERTIFYING)
        )
        approval = next(
            (
                one
                for one in maintenance_approvals(organisation, DAY)
                if one.approval == ApprovalType.PART_CAO
            ),
            None,
        )
        user = keeper.user if keeper is not None else None
        if (
            keeper is None
            or user is None
            or approval is None
            or len(inspectors) != 1
            or not all(
                user.may(action)
                for action in (
                    Action.MANAGE_STORE_LOCATIONS,
                    Action.POST_STOCK,
                    Action.COUNT_STOCK,
                    Action.ADJUST_STOCK,
                )
            )
        ):
            return 0
    with working_for(organisation.pk, user.pk), transaction.atomic():
        for duty in StockDuty:
            stock_appointments.appoint(
                user,
                request_id=submission(f"appointment-{duty}"),
                person=keeper,
                approval=approval,
                action=duty,
                starts_on=date(2026, 11, 1),
                ends_on=date(2099, 12, 31),
                evidence="Fictitious example of a signed Stores appointment",
            )
        places = {
            name: stores.add_location(
                organisation,
                name=name,
                kind=kind,
                holds_components=components,
                holds_standard_parts=standard,
                holds_materials=materials,
                secure=kind == LocationKind.QUARANTINE,
                storage_conditions=conditions,
            )
            for name, kind, components, standard, materials, conditions in LOCATIONS
        }
        oil = _accepted(
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
        )
        bolts = _accepted(
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
        for arrival, values in (
            (
                oil,
                {
                    "unit": StockUnit.LITRE,
                    "specification": "[Oil Specification]",
                    "batch_number": "[Oil Batch Number]",
                    "shelf_life_basis": ShelfLifeBasis.DATED,
                    "shelf_life_to": date(2029, 8, 31),
                    "shelf_life_rule": ShelfLifeRule.THROUGH,
                    "location": places["Bay C, Oils and Materials"],
                },
            ),
            (
                bolts,
                {
                    "unit": StockUnit.EACH,
                    "specification": "[Bolt Standard]",
                    "batch_number": "[Bolt Batch Number]",
                    "shelf_life_basis": ShelfLifeBasis.NOT_APPLICABLE,
                    "location": places["Bay B, Standard Parts Drawers"],
                },
            ),
        ):
            decision = arrival.disposition
            stores.resolve(
                decision,
                actor=keeper,
                authority=AUTHORITY,
                evidence=f"Fictitious example. Conformity evidence and label for "
                f"{arrival.delivery_reference} checked against the receipt",
                evidence_on=DAY,
                **values,  # type: ignore[arg-type]
            )
            stores.post(decision, actor=keeper, authority=AUTHORITY, posted_on=DAY)
        stores.count(
            bolts.disposition.stock_posting,
            location=places["Bay B, Standard Parts Drawers"],
            counted_quantity="46",
            counted_on=DAY,
            counter=keeper,
            evidence="Fictitious example. Drawer counted at 46. Adjustment to be authorised",
        )
    return 2
