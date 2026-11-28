"""Stores PR 1 consumer contract (REQ-357, REQ-358), against the primary sample.

Cases follow the approved handoff in ``assurance/phase-4-stores-handoff.md``:
S01 outcomes, S02 once-only posting and rollback, S03 quantities and identity,
S04 locations and custody, S05 shelf life, S06 counts, S07 upgrade, S08
permissions and S10 exports. The independent-session cases of S02 and S09
are in ``tests/test_stores_postgres.py``.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.db import DatabaseError, connection, transaction
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts import services as contracts
from airworthiness_plus.contracts.models import OrderedBy
from airworthiness_plus.exports.build import build
from airworthiness_plus.exports.verify import verify
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import allocations, stores
from airworthiness_plus.logistics.models import (
    AllocationKind,
    ItemClass,
    LocationKind,
    MovementKind,
    PostingEvidence,
    PostingKind,
    Receipt,
    ReceivingDisposition,
    ShelfLifeBasis,
    StockAllocation,
    StockCount,
    StockEntry,
    StockMovement,
    StockPosting,
    StockUnit,
    StoresAction,
    StoresAppointment,
    StoresLocation,
)
from airworthiness_plus.logistics.services import RefusedError
from airworthiness_plus.maintenance_data import services as data
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning import services as planning
from airworthiness_plus.planning.models import WorkCard
from airworthiness_plus.sample import goods_in
from airworthiness_plus.sample import stores as stores_sample
from airworthiness_rules import shelf_life
from tests.support import Sample, add_sample_fleet, get, post, signed_in
from tests.test_exports import opened

pytestmark = pytest.mark.django_db

TODAY = date(2026, 11, 18)


@dataclass
class Day:
    today: date = TODAY


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    held = Day()
    monkeypatch.setattr(aircraft_services, "today", lambda: held.today)
    return held


@pytest.fixture
def stocked(sample: Sample) -> Sample:
    assert goods_in.add(sample.ours, sample.lucy) == 5
    assert stores_sample.add(sample.ours, sample.administrator) == 2
    return sample


@pytest.fixture
def as_lucy(stocked: Sample) -> Iterator[User]:
    with working_for(stocked.ours.id, stocked.lucy.id):
        yield stocked.lucy


def decision(line: str) -> ReceivingDisposition:
    return ReceivingDisposition.objects.select_related("receipt").get(
        receipt__delivery_reference=line
    )


def place(code: str) -> StoresLocation:
    return StoresLocation.objects.get(code=code)


def lot(line: str) -> StockPosting:
    return StockPosting.objects.select_related("evidence", "disposition__receipt").get(
        disposition__receipt__delivery_reference=line
    )


def held(line: str) -> dict[str, Decimal]:
    return {
        one.location.code: one.on_hand
        for one in stores.positions(
            lot(line).organisation, aircraft_services.today(), posting=lot(line)
        )
    }


def evidence_for(user: User, line: str, **values: Any) -> PostingEvidence:
    base: dict[str, Any] = {
        "assessed_on": aircraft_services.today(),
        "evidence": f"Synthetic evidence for {line}",
    }
    return stores.record_posting_evidence(
        user, decision(line), request_id=uuid4(), **{**base, **values}
    )


def accepted(sample: Sample, line: str, classification: str, quantity: int, item: str) -> None:
    """Record a fresh synthetic acceptance through the Goods In services."""
    from airworthiness_plus.logistics import receiving
    from airworthiness_plus.logistics.models import CheckKind, CheckOutcome, DocumentKind

    with working_for(sample.ours.id, sample.planner.id):
        receipt = receiving.receive(
            sample.ours,
            item=item,
            received_on=date(2026, 11, 17),
            classification=classification,
            source="Synthetic Supplier",
            item_reference="Synthetic reference",
            quantity=quantity,
            delivery_reference=line,
        )
        for kind in CheckKind:
            receiving.record_check(
                receipt,
                check=kind,
                outcome=CheckOutcome.PASS,
                checked_on=date(2026, 11, 17),
                evidence="Synthetic check",
            )
        serviceable = classification == ItemClass.SERVICEABLE
        receiving.dispose(
            receipt,
            approval="Part-CAO",
            inspector=Person.objects.get(full_name="Chris Moore"),
            inspector_authority="Synthetic RI",
            inspected_on=date(2026, 11, 17),
            disposition_on=date(2026, 11, 17),
            outcome="Accepted into Stores",
            destination="Synthetic Bay",
            evidence="Synthetic decision",
            document_kind="CAA Form 1" if serviceable else DocumentKind.CONFORMITY,
            document_reference="Synthetic Folder",
            evidence_basis="" if serviceable else "Synthetic Standard",
            manufacturing_source="Synthetic Maker" if classification == ItemClass.MATERIAL else "",
            material_supplier_source="Synthetic Supplier"
            if classification == ItemClass.MATERIAL
            else "",
        )


# S01 Consumer outcomes


def test_s01_each_final_result_has_its_stores_state(as_lucy: User) -> None:
    """REQ-357, REQ-358. Accepted unresolved, accepted posted, quarantine, return, awaiting."""
    day = aircraft_services.today()
    rx002 = decision("RX-002")
    assert not hasattr(rx002, "posting")
    assert StockEntry.objects.filter(disposition=rx002).exists()
    reasons = stores.blockers(rx002, stores.latest_evidence(rx002), day)
    assert reasons == [
        "Unit and Quantity Need Dated Evidence",
        "Stock Location Unknown",
        "Traceable Identity Unresolved: Part Number With Serial or Lot",
        "Shelf-Life Basis Unknown",
    ]
    with pytest.raises(RefusedError, match="Awaiting Stock Posting"):
        stores.post(as_lucy, rx002, request_id=uuid4())

    assert held("RX-006") == {"BAY-C": Decimal(24)}
    oil = stores.positions(as_lucy.organisation, day, posting=lot("RX-006"))
    assert [(one.on_hand, one.reserved, one.available) for one in oil] == [
        (Decimal(24), Decimal(0), Decimal(24))
    ]

    rx004 = decision("RX-004")
    assert rx004.outcome == "Quarantined"
    assert stores.blockers(rx004, None, day) == [
        "Unit and Quantity Need Dated Evidence",
        "Quarantine Location to Verify",
        "Quarantine Tag Not Recorded",
    ]
    for line in ("RX-003", "RX-005"):
        returned = decision(line)
        with pytest.raises(RefusedError, match="Never Posted to Stock"):
            evidence_for(as_lucy, line, unit=StockUnit.EACH, quantity=Decimal(1))
        assert stores.blockers(returned, None, day) == [
            "A Supplier Return Is Kept in History and Never Posted to Stock"
        ]
    assert not ReceivingDisposition.objects.filter(receipt__delivery_reference="RX-001").exists()
    assert StockPosting.objects.count() == 2


def test_s01_register_pages_show_states_and_keep_other_organisations_out(stocked: Sample) -> None:
    """REQ-358, REQ-002. The register shows the backlog reasons, holds and returns."""
    reader = signed_in(stocked.reader)
    register = get(reader, "/stores/").content.decode()
    for text in (
        "Awaiting Stock Posting",
        "Stock Location Unknown",
        "Quarantine Holds",
        "Quarantine Hold, Details to Verify",
        "Return History",
        "RX-003",
        "RX-005",
        "Engine Oil",
        "Bolts",
    ):
        assert text in register
    with working_for(stocked.ours.id, stocked.lucy.id):
        entry = StockEntry.objects.get(disposition__receipt__delivery_reference="RX-002")
        quarantine = decision("RX-004")
        returned = decision("RX-003")
        oil = StockEntry.objects.get(disposition__receipt__delivery_reference="RX-006")
    page = get(reader, f"/stores/{entry.pk}/").content.decode()
    assert "Awaiting Stock Posting" in page
    assert "<dt>Available Quantity</dt><dd>0</dd>" in page
    assert "Record Posting Evidence" not in page  # Read Only has no control
    hold = get(reader, f"/stores/holds/{quarantine.pk}/").content.decode()
    assert "Quarantine Hold, Details to Verify" in hold
    assert "<dt>Available Quantity</dt><dd>0</dd>" in hold
    assert get(reader, f"/stores/holds/{returned.pk}/").status_code == 404
    oil_page = get(reader, f"/stores/{oil.pk}/").content.decode()
    assert "<dt>On Hand</dt><dd>24 L (Litre)</dd>" in oil_page
    assert "<dt>Available Quantity</dt><dd>24 L</dd>" in oil_page
    stranger = signed_in(stocked.stranger)
    assert get(stranger, f"/stores/{entry.pk}/").status_code == 404
    assert get(stranger, f"/stores/holds/{quarantine.pk}/").status_code == 404
    assert "Engine Oil" not in get(stranger, "/stores/").content.decode()
    lucy = signed_in(stocked.lucy)
    assert get(lucy, f"/stores/dispositions/{uuid4()}/evidence/").status_code == 404
    assert get(lucy, f"/stores/dispositions/{returned.pk}/evidence/").status_code == 404


# S02 Idempotency and atomicity


def _resolve_rx002(user: User, **override: Any) -> PostingEvidence:
    values: dict[str, Any] = {
        "unit": StockUnit.EACH,
        "quantity": Decimal(1),
        "manufacturer": "Synthetic Cable Maker",
        "part_number": "PN-713",
        "serial": "SN-863",
        "shelf_life_basis": ShelfLifeBasis.NOT_APPLICABLE,
        "location": place("BAY-A"),
    }
    return evidence_for(user, "RX-002", **{**values, **override})


def test_s02_posting_is_once_only_and_a_conflicting_replay_keeps_the_original(
    as_lucy: User,
) -> None:
    """REQ-358. The same request returns the posting. Other evidence is a conflict."""
    _resolve_rx002(as_lucy)
    rx002 = decision("RX-002")
    first = stores.post(as_lucy, rx002, request_id=uuid4())
    again = stores.post(as_lucy, decision("RX-002"), request_id=uuid4())
    assert again.pk == first.pk
    assert StockMovement.objects.filter(posting=first).count() == 1
    opening = StockMovement.objects.get(posting=first)
    assert (opening.kind, opening.quantity, opening.destination_id) == (
        MovementKind.INTAKE,
        Decimal(1),
        place("BAY-A").pk,
    )
    assert opening.moved_on == rx002.disposition_on
    assert opening.recorded_on == aircraft_services.today()
    _resolve_rx002(as_lucy, location=place("BAY-B"), part_number="PN-713A")
    with pytest.raises(stores.PostingConflictError, match="Original Posting Stands"):
        stores.post(as_lucy, decision("RX-002"), request_id=uuid4())
    kept = StockPosting.objects.get(disposition=rx002)
    assert kept.pk == first.pk and kept.evidence_id == first.evidence_id
    assert held("RX-002") == {"BAY-A": Decimal(1)}
    with pytest.raises(DatabaseError), transaction.atomic():
        StockPosting.objects.create(
            organisation_id=rx002.organisation_id,
            submission=uuid4(),
            disposition=rx002,
            evidence=first.evidence,
            kind=PostingKind.STOCK,
            location_rules="Direct second posting",
            posted_on=aircraft_services.today(),
            appointment=first.appointment,
        )


def test_s02_a_failure_after_the_posting_row_leaves_no_posting_movement_or_history(
    as_lucy: User,
) -> None:
    """REQ-358. One transaction. A retry after the failure posts once."""
    _resolve_rx002(as_lucy)
    original = StockPosting.objects.create

    def fail_after(*args: Any, **kwargs: Any) -> StockPosting:
        original(*args, **kwargs)
        raise RuntimeError("Injected failure after the posting and its opening movement")

    events_before = Event.objects.filter(
        record_type__in=("logistics_stockposting", "logistics_stockmovement")
    ).count()
    with (
        patch.object(StockPosting.objects, "create", side_effect=fail_after),
        pytest.raises(RuntimeError, match="Injected"),
    ):
        stores.post(as_lucy, decision("RX-002"), request_id=uuid4())
    rx002 = decision("RX-002")
    assert not StockPosting.objects.filter(disposition=rx002).exists()
    assert not StockMovement.objects.filter(posting__disposition=rx002).exists()
    assert (
        Event.objects.filter(
            record_type__in=("logistics_stockposting", "logistics_stockmovement")
        ).count()
        == events_before
    )
    retried = stores.post(as_lucy, rx002, request_id=uuid4())
    assert held("RX-002") == {"BAY-A": Decimal(1)}
    assert StockMovement.objects.filter(posting=retried).count() == 1


def test_s02_the_database_refuses_an_opening_movement_written_directly(as_lucy: User) -> None:
    """REQ-358. Only the posting writes the opening movement."""
    oil = lot("RX-006")
    with pytest.raises(DatabaseError, match="opening movement"), transaction.atomic():
        StockMovement.objects.create(
            organisation_id=oil.organisation_id,
            submission=uuid4(),
            posting=oil,
            kind=MovementKind.INTAKE,
            destination=place("BAY-C"),
            quantity=Decimal(24),
            moved_on=TODAY,
            evidence="A second opening",
            recorded_on=TODAY,
            appointment=oil.appointment,
        )
    with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
        StockMovement.objects.filter(posting=oil).update(quantity=Decimal(30))


# S03 Quantities and identities


@pytest.mark.parametrize(
    ("unit", "quantity", "serial", "valid"),
    [
        (StockUnit.LITRE, Decimal(0), "", False),
        (StockUnit.LITRE, Decimal(-1), "", False),
        (StockUnit.LITRE, Decimal("0.001"), "", True),
        (StockUnit.LITRE, Decimal("0.0005"), "", False),
        (StockUnit.LITRE, Decimal(2_147_483_647), "", True),
        (StockUnit.LITRE, Decimal("2147483647.001"), "", False),
        (StockUnit.EACH, Decimal("1.5"), "", False),
        (StockUnit.EACH, Decimal(3), "", True),
        (StockUnit.EACH, Decimal(1), "SN-1", True),
        (StockUnit.EACH, Decimal(2), "SN-1", False),
        (StockUnit.LITRE, Decimal(1), "SN-1", False),
        ("", Decimal(1), "", False),
        ("Kilogram", Decimal(1), "", False),
    ],
)
def test_s03_quantity_boundaries_match_the_database(
    as_lucy: User, unit: str, quantity: Decimal, serial: str, valid: bool
) -> None:
    """REQ-358. Exact decimals to 0.001 L, whole each, one each for a serial."""
    assert stores.fits(unit, quantity, serial) is valid
    with connection.cursor() as cursor:
        cursor.execute("SELECT logistics_quantity_fits(%s, %s, %s)", [unit, quantity, serial])
        (database,) = cursor.fetchone()
    expected_in_database = valid if quantity == quantity.quantize(Decimal("0.001")) else database
    assert database is expected_in_database


def test_s03_refused_quantities_and_identities_change_nothing(stocked: Sample) -> None:
    """REQ-358. Refusals leave the ledger unchanged. A duplicate active serial is blocked."""
    lucy = signed_in(stocked.lucy)
    with working_for(stocked.ours.id, stocked.lucy.id):
        rx002 = decision("RX-002")
        before = PostingEvidence.objects.count()
    form = {
        "request_id": str(uuid4()),
        "assessed_on": "2026-11-18",
        "unit": "Each",
        "quantity": "1.5",
        "evidence": "Synthetic",
    }
    for quantity in ("1.5", "0", "-1", "0.0005", "2147483647000"):
        refused = post(
            lucy, f"/stores/dispositions/{rx002.pk}/evidence/", **{**form, "quantity": quantity}
        )
        assert refused.status_code == 200
    with working_for(stocked.ours.id, stocked.lucy.id):
        assert PostingEvidence.objects.count() == before
        _resolve_rx002(stocked.lucy)
        stores.post(stocked.lucy, decision("RX-002"), request_id=uuid4())
    accepted(stocked, "SYN-SERIAL", ItemClass.SERVICEABLE, 1, "Synthetic Cable")
    with working_for(stocked.ours.id, stocked.lucy.id):
        evidence_for(
            stocked.lucy,
            "SYN-SERIAL",
            unit=StockUnit.EACH,
            quantity=Decimal(1),
            manufacturer="synthetic cable maker",
            part_number="pn-713",
            serial="sn-863",
            shelf_life_basis=ShelfLifeBasis.NOT_APPLICABLE,
            location=place("BAY-A"),
        )
        second = decision("SYN-SERIAL")
        assert "This Serial Number Already Has a Custody Position" in stores.blockers(
            second, stores.latest_evidence(second), TODAY
        )
        with pytest.raises(RefusedError, match="Serial Number Already"):
            stores.post(stocked.lucy, second, request_id=uuid4())
        with pytest.raises(RefusedError, match="Does Not Fit"):
            evidence_for(
                stocked.lucy, "SYN-SERIAL", unit=StockUnit.EACH, quantity=Decimal(2), serial="X"
            )
        assert StockPosting.objects.count() == 3


def test_s03_a_quantity_for_each_must_match_the_receipt(as_lucy: User) -> None:
    """REQ-358. Submitted quantity cannot override the persisted receipt."""
    _resolve_rx002(as_lucy, quantity=Decimal(1), serial="", batch="LOT-1")
    rx002 = decision("RX-002")
    assert stores.blockers(rx002, stores.latest_evidence(rx002), TODAY) == []
    bolts = lot("RX-007")
    assert bolts.evidence.quantity == bolts.disposition.receipt.quantity == 50
    receipt = Receipt.objects.get(delivery_reference="RX-002")
    assert receipt.quantity == 1


# S04 Locations and custody


def test_s04_moving_8_litres_of_24_conserves_custody(as_lucy: User) -> None:
    """REQ-358. 16 L at the source and 8 L at the destination, 24 L in total."""
    oil = lot("RX-006")
    moved = stores.move(
        as_lucy,
        oil,
        request_id=(request := uuid4()),
        source=place("BAY-C"),
        destination=place("OIL-2"),
        quantity=Decimal(8),
        moved_on=TODAY,
        evidence="Synthetic transfer note T-1",
    )
    again = stores.move(
        as_lucy,
        oil,
        request_id=request,
        source=place("BAY-C"),
        destination=place("OIL-2"),
        quantity=Decimal(8),
        moved_on=TODAY,
        evidence="Synthetic transfer note T-1",
    )
    assert again.pk == moved.pk
    assert held("RX-006") == {"BAY-C": Decimal(16), "OIL-2": Decimal(8)}
    lines = stores.positions(as_lucy.organisation, TODAY, posting=oil)
    total = stores.totals(lines)[StockUnit.LITRE]
    assert (total.on_hand, total.reserved, total.available) == (
        Decimal(24),
        Decimal(0),
        Decimal(24),
    )
    assert (moved.source_id, moved.destination_id, moved.appointment.person.user_id) == (
        place("BAY-C").pk,
        place("OIL-2").pk,
        as_lucy.pk,
    )
    assert moved.evidence == "Synthetic transfer note T-1"


@pytest.mark.parametrize(
    ("destination", "reason"),
    [
        ("BAY-D", "Does Not Accept"),  # withdrawn
        ("BAY-A", "Does Not Accept"),  # does not hold material
        ("QUAR-1", "Does Not Accept"),  # quarantine for serviceable stock
    ],
)
def test_s04_refused_destinations_leave_the_position_intact(
    as_lucy: User, destination: str, reason: str
) -> None:
    """REQ-358. Inactive and incompatible destinations are refused here and in PostgreSQL."""
    oil = lot("RX-006")
    with pytest.raises(RefusedError, match=reason):
        stores.move(
            as_lucy,
            oil,
            request_id=uuid4(),
            source=place("BAY-C"),
            destination=place(destination),
            quantity=Decimal(1),
            moved_on=TODAY,
            evidence="Synthetic",
        )
    with pytest.raises(DatabaseError, match="does not accept"), transaction.atomic():
        StockMovement.objects.create(
            organisation_id=oil.organisation_id,
            submission=uuid4(),
            posting=oil,
            kind=MovementKind.TRANSFER,
            source=place("BAY-C"),
            destination=place(destination),
            quantity=Decimal(1),
            moved_on=TODAY,
            evidence="Direct",
            recorded_on=TODAY,
            appointment=StoresAppointment.objects.get(
                person__user=as_lucy, action=StoresAction.MOVE
            ),
        )
    assert held("RX-006") == {"BAY-C": Decimal(24)}


def test_s04_a_move_of_the_whole_balance_passes_and_one_increment_more_is_refused(
    as_lucy: User,
) -> None:
    """REQ-358. Boundary at the source balance."""
    oil = lot("RX-006")
    common: dict[str, Any] = {
        "source": place("BAY-C"),
        "destination": place("OIL-2"),
        "moved_on": TODAY,
    }
    with pytest.raises(RefusedError, match="Holds Less"):
        stores.move(
            as_lucy, oil, request_id=uuid4(), quantity=Decimal("24.001"), evidence="x", **common
        )
    stores.move(as_lucy, oil, request_id=uuid4(), quantity=Decimal(24), evidence="All", **common)
    assert held("RX-006") == {"OIL-2": Decimal(24)}


def test_s04_quarantine_is_secure_and_a_hold_never_moves_to_serviceable_stock(
    as_lucy: User,
) -> None:
    """REQ-358, CAO.A.030(b). Verified blocked custody has zero availability."""
    with pytest.raises(RefusedError, match="Secure"):
        stores.record_location(
            as_lucy,
            request_id=uuid4(),
            code="Q-OPEN",
            name="Open Shelf",
            kind=LocationKind.QUARANTINE,
            classes=[ItemClass.UNSERVICEABLE],
            storage_conditions="Open",
            secure=False,
        )
    evidence_for(
        as_lucy,
        "RX-004",
        unit=StockUnit.EACH,
        quantity=Decimal(1),
        location=place("QUAR-1"),
        tag="Q-TAG-0042",
    )
    hold = stores.post(as_lucy, decision("RX-004"), request_id=uuid4())
    assert hold.kind == PostingKind.HOLD
    [position] = stores.positions(as_lucy.organisation, TODAY, posting=hold)
    assert (position.on_hand, position.available) == (Decimal(1), Decimal(0))
    with pytest.raises(RefusedError, match="Only to Secure Quarantine"):
        stores.move(
            as_lucy,
            hold,
            request_id=uuid4(),
            source=place("QUAR-1"),
            destination=place("BAY-A"),
            quantity=Decimal(1),
            moved_on=TODAY,
            evidence="Synthetic",
        )


def test_s04_a_location_with_stock_cannot_be_withdrawn(as_lucy: User) -> None:
    with pytest.raises(RefusedError, match="Move the Stock Out"):
        stores.withdraw_location(as_lucy, place("BAY-C"), request_id=uuid4(), evidence="Synthetic")
    with pytest.raises(RefusedError, match="Already Withdrawn"):
        stores.withdraw_location(as_lucy, place("BAY-D"), request_id=uuid4(), evidence="Synthetic")


def test_s04_network_station_and_store_totals_add_up(as_lucy: User) -> None:
    """AMOS stock-by-location scenario. Each location total and the network total agree."""
    stores.move(
        as_lucy,
        lot("RX-006"),
        request_id=uuid4(),
        source=place("BAY-C"),
        destination=place("OIL-2"),
        quantity=Decimal("8.5"),
        moved_on=TODAY,
        evidence="Synthetic",
    )
    lines = stores.positions(as_lucy.organisation, TODAY)
    by_place = {
        one.location.code: {total.unit: total.on_hand for total in one.totals}
        for one in stores.by_location(lines)
    }
    assert by_place == {
        "BAY-B": {"Each": Decimal(50)},
        "BAY-C": {"Litre": Decimal("15.5")},
        "OIL-2": {"Litre": Decimal("8.5")},
    }
    network = stores.totals(lines)
    assert network["Litre"].on_hand == Decimal(24)
    assert network["Each"].on_hand == Decimal(50)


# S05 Shelf life


@pytest.mark.parametrize(
    ("day", "status", "left"),
    [
        (date(2026, 11, 17), shelf_life.Status.CURRENT, 13),
        (date(2026, 11, 18), shelf_life.Status.DUE_SOON, 12),
        (date(2026, 11, 29), shelf_life.Status.DUE_SOON, 1),
        (date(2026, 11, 30), shelf_life.Status.DUE_SOON, 0),
        (date(2026, 12, 1), shelf_life.Status.EXPIRED, -1),
    ],
)
def test_s05_usable_through_the_date_with_a_12_day_lead(
    day: date, status: shelf_life.Status, left: int
) -> None:
    """REQ-358. Synthetic label valid through 30 November 2026."""
    result = shelf_life.evaluate(shelf_life.Basis.THROUGH, date(2026, 11, 30), day, 12)
    assert (result.status, result.days_left) == (status, left)
    # Independent calendar arithmetic by ordinal day number.
    assert date(2026, 11, 30).toordinal() - day.toordinal() == left


def test_s05_start_of_day_expiry_missing_basis_and_inapplicability() -> None:
    rule = shelf_life.Basis.BEFORE
    assert shelf_life.evaluate(rule, date(2026, 11, 30), date(2026, 11, 29), 12).usable
    assert shelf_life.evaluate(rule, date(2026, 11, 30), date(2026, 11, 30), 12).status == (
        shelf_life.Status.EXPIRED
    )
    unknown = shelf_life.evaluate("", date(2026, 11, 30), date(2026, 11, 1), 12)
    assert (unknown.status, unknown.usable) == (shelf_life.Status.UNKNOWN, False)
    assert shelf_life.evaluate(shelf_life.Basis.NOT_APPLICABLE, None, TODAY, 12).usable
    with pytest.raises(ValueError, match="negative"):
        shelf_life.evaluate(rule, TODAY, TODAY, -1)


def test_s05_expired_stock_stays_on_hand_with_nothing_available(
    stocked: Sample, as_lucy: User, day: Day
) -> None:
    """REQ-358. Valid on arrival, reconciled after expiry, current availability zero."""
    accepted(stocked, "SYN-SEALANT", ItemClass.MATERIAL, 2, "Synthetic Sealant")
    evidence_for(
        as_lucy,
        "SYN-SEALANT",
        unit=StockUnit.EACH,
        quantity=Decimal(2),
        specification="Synthetic Specification",
        batch="B-1",
        shelf_life_basis=ShelfLifeBasis.THROUGH,
        shelf_life_to=date(2026, 11, 30),
        location=place("BAY-C"),
    )
    day.today = date(2026, 12, 2)
    posting = stores.post(as_lucy, decision("SYN-SEALANT"), request_id=uuid4())
    [position] = stores.positions(as_lucy.organisation, day.today, posting=posting)
    assert position.shelf.status == shelf_life.Status.EXPIRED
    assert (position.on_hand, position.available) == (Decimal(2), Decimal(0))


def test_s05_a_shelf_life_passed_on_arrival_or_unknown_blocks_posting(
    stocked: Sample, as_lucy: User
) -> None:
    accepted(stocked, "SYN-OLD", ItemClass.MATERIAL, 1, "Synthetic Old Batch")
    evidence_for(
        as_lucy,
        "SYN-OLD",
        unit=StockUnit.EACH,
        quantity=Decimal(1),
        specification="Spec",
        batch="B",
        shelf_life_basis=ShelfLifeBasis.BEFORE,
        shelf_life_to=date(2026, 11, 17),
        location=place("BAY-C"),
    )
    old = decision("SYN-OLD")
    assert stores.blockers(old, stores.latest_evidence(old), TODAY) == [
        "Shelf Life Had Passed on Arrival in Stores"
    ]
    with pytest.raises(RefusedError, match="Dated Basis"):
        evidence_for(as_lucy, "SYN-OLD", shelf_life_basis=ShelfLifeBasis.THROUGH)


# S06 Stock count


def test_s06_a_count_records_variance_and_only_an_authorised_adjustment_moves_stock(
    stocked: Sample,
) -> None:
    """REQ-358. Count 46 against 50. The ledger shows 50 until the authorised -4."""
    with working_for(stocked.ours.id, stocked.lucy.id):
        taken = StockCount.objects.get(posting=lot("RX-007"))
        assert (taken.counted, taken.on_hand, taken.variance) == (
            Decimal(46),
            Decimal(50),
            Decimal(-4),
        )
        assert held("RX-007") == {"BAY-B": Decimal(50)}
        with pytest.raises(RefusedError, match="Evidence"):
            stores.adjust(stocked.lucy, taken, request_id=uuid4(), evidence=" ")
    with working_for(stocked.ours.id, stocked.planner.id), pytest.raises(ActionRefusedError):
        stores.adjust(stocked.planner, taken, request_id=uuid4(), evidence="Synthetic")
    planner_page = signed_in(stocked.planner)
    assert post(planner_page, f"/stores/counts/{taken.pk}/adjust/", evidence="x").status_code == 403
    lucy = signed_in(stocked.lucy)
    request = str(uuid4())
    form = {"request_id": request, "evidence": "Synthetic adjustment approval A-7"}
    assert post(lucy, f"/stores/counts/{taken.pk}/adjust/", **form).status_code == 302
    assert post(lucy, f"/stores/counts/{taken.pk}/adjust/", **form).status_code == 302
    with working_for(stocked.ours.id, stocked.lucy.id):
        assert held("RX-007") == {"BAY-B": Decimal(46)}
        adjustment = StockMovement.objects.get(count=taken)
        assert (adjustment.kind, adjustment.quantity, adjustment.source_id) == (
            MovementKind.ADJUSTMENT,
            Decimal(4),
            place("BAY-B").pk,
        )
        assert StockMovement.objects.filter(kind=MovementKind.ADJUSTMENT).count() == 1
        with pytest.raises(RefusedError, match="Already Been Applied"):
            stores.adjust(stocked.lucy, taken, request_id=uuid4(), evidence="Again")


def test_s06_a_stale_count_cannot_be_applied(as_lucy: User) -> None:
    oil = lot("RX-006")
    taken = stores.count(
        as_lucy,
        oil,
        request_id=uuid4(),
        location=place("BAY-C"),
        counted=Decimal(23),
        evidence="Synthetic count",
    )
    stores.move(
        as_lucy,
        oil,
        request_id=uuid4(),
        source=place("BAY-C"),
        destination=place("OIL-2"),
        quantity=Decimal(1),
        moved_on=TODAY,
        evidence="Synthetic",
    )
    with pytest.raises(RefusedError, match="Count Again"):
        stores.adjust(as_lucy, taken, request_id=uuid4(), evidence="Synthetic")


# S07 Upgrade


def test_s07_upgrade_keeps_legacy_decisions_and_reconciles_once(sample: Sample) -> None:
    """REQ-357, REQ-358. Decisions recorded before Stores PR 1 keep their IDs and evidence."""
    from django.db.migrations.executor import MigrationExecutor

    from airworthiness_plus.organisations.models import Approval, ApprovalType
    from tests.conftest import as_owner

    with as_owner():
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old_apps = executor.migrate([("logistics", "0006_merge_receiving_and_subcontracting")]).apps
    old_receipt = old_apps.get_model("logistics", "Receipt")
    old_check = old_apps.get_model("logistics", "ReceivingCheck")
    old_decision = old_apps.get_model("logistics", "ReceivingDisposition")
    legacy = {}
    with working_for(sample.ours.id, sample.planner.id):
        approval = Approval.objects.get(approval=ApprovalType.PART_CAO).id
        inspector = Person.objects.get(full_name="Chris Moore").id
        for line, outcome, kind in (
            ("LEGACY-MAPPED", "Accepted into Stores", "CAA Form 1"),
            ("LEGACY-NO-UNIT", "Accepted into Stores", "CAA Form 1"),
            ("LEGACY-QUARANTINE", "Quarantined", ""),
            ("LEGACY-RETURN", "Returned to Supplier", ""),
        ):
            arrival = old_receipt.objects.create(
                organisation_id=sample.ours.id,
                item=f"Synthetic {line}",
                received_on=date(2026, 11, 10),
                classification="Serviceable Component",
                source="Synthetic Supplier",
                item_reference="Synthetic part and serial",
                quantity=1,
                delivery_reference=line,
            )
            for check in (
                "Supplier",
                "Release Document",
                "Part Number and Modification Status",
                "Condition and Packaging",
                "Shelf Life",
                "Suspected Unapproved Part Checks",
            ):
                old_check.objects.create(
                    organisation_id=sample.ours.id,
                    receipt_id=arrival.id,
                    kind=check,
                    outcome="Not Applicable" if check == "Shelf Life" else "Pass",
                    evidence="Synthetic legacy check",
                    checked_on=date(2026, 11, 10),
                )
            legacy[line] = old_decision.objects.create(
                organisation_id=sample.ours.id,
                receipt_id=arrival.id,
                approval_id=approval,
                inspector_id=inspector,
                inspector_name="Chris Moore",
                inspector_authority="Synthetic RI",
                inspected_on=date(2026, 11, 10),
                disposition_on=date(2026, 11, 10),
                outcome=outcome,
                destination="Synthetic free-text bay",
                evidence="Original legacy decision",
                document_kind=kind,
                document_reference="Legacy folder" if kind else "",
            ).id
    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        MigrationExecutor(connection).migrate(latest)
    with working_for(sample.ours.id, sample.administrator.id):
        from airworthiness_plus.sample.stores import submission

        lucy_person = Person.objects.get(user=sample.lucy)
        for action in StoresAction:
            StoresAppointment.objects.create(
                organisation=sample.ours,
                submission=submission(f"upgrade-{action}"),
                person=lucy_person,
                approval_id=approval,
                approval_reference="UK.CAO.[Number]",
                action=action,
                starts_on=date(2026, 11, 1),
                ends_on=date(2099, 12, 31),
                exposition_reference="Synthetic exposition",
                authority="Synthetic appointment",
            )
    with working_for(sample.ours.id, sample.lucy.id):
        bay = stores.record_location(
            sample.lucy,
            request_id=uuid4(),
            code="LEG-A",
            name="Legacy Bay",
            kind=LocationKind.SERVICEABLE,
            classes=[ItemClass.SERVICEABLE],
            storage_conditions="Dry",
            secure=False,
        )
        entries = {entry.disposition_id for entry in StockEntry.objects.all()}
        assert entries == {legacy["LEGACY-MAPPED"], legacy["LEGACY-NO-UNIT"]}
        assert not StockPosting.objects.exists()
        mapped = ReceivingDisposition.objects.get(pk=legacy["LEGACY-MAPPED"])
        values: dict[str, Any] = {
            "assessed_on": TODAY,
            "evidence": "Dated legacy mapping. The original Form 1 identifies PN and SN",
            "unit": StockUnit.EACH,
            "quantity": Decimal(1),
            "part_number": "PN-L1",
            "serial": "SN-L1",
            "shelf_life_basis": ShelfLifeBasis.NOT_APPLICABLE,
            "location": bay,
        }
        stores.record_posting_evidence(sample.lucy, mapped, request_id=uuid4(), **values)
        for _ in range(2):  # reconciliation is restartable through the same path
            stores.post(
                sample.lucy, ReceivingDisposition.objects.get(pk=mapped.pk), request_id=uuid4()
            )
        assert StockPosting.objects.count() == 1
        assert StockMovement.objects.get().moved_on == date(2026, 11, 10)
        no_unit = ReceivingDisposition.objects.get(pk=legacy["LEGACY-NO-UNIT"])
        assert "Unit and Quantity Need Dated Evidence" in stores.blockers(no_unit, None, TODAY)
        mapped.refresh_from_db()
        assert (mapped.evidence, mapped.inspector_name, mapped.document_reference) == (
            "Original legacy decision",
            "Chris Moore",
            "Legacy folder",
        )
        Person.objects.filter(pk=lucy_person.pk).update(full_name="Lucy Grant-Renamed")
        posted = StockPosting.objects.get()
        assert posted.appointment.person.full_name == "Lucy Grant-Renamed"
        event = Event.objects.get(record_type="logistics_stockposting", record_id=posted.pk)
        assert event.actor_name == "Lucy Grant"  # history keeps the name at the time


# S08 Permission rules


def test_s08_role_and_appointment_must_both_permit_each_action(stocked: Sample, day: Day) -> None:
    """REQ-358, ASVS V8. UI visibility and server enforcement agree."""
    with working_for(stocked.ours.id, stocked.lucy.id):
        entry = StockEntry.objects.get(disposition__receipt__delivery_reference="RX-002")
        rx002 = decision("RX-002")
        oil = lot("RX-006")
    routes = (
        f"/stores/dispositions/{rx002.pk}/evidence/",
        f"/stores/dispositions/{rx002.pk}/post/",
        f"/stores/lots/{oil.pk}/move/",
        f"/stores/lots/{oil.pk}/count/",
        "/stores/locations/add/",
    )
    for user in (stocked.reader, stocked.reviewer, stocked.administrator):
        client = signed_in(user)
        for route in routes:
            assert post(client, route, request_id=str(uuid4())).status_code == 403
        assert "Record Posting Evidence" not in get(client, f"/stores/{entry.pk}/").content.decode()
    # The planner's role permits Stores work, but the only appointment was withdrawn.
    planner = signed_in(stocked.planner)
    page = get(planner, f"/stores/{entry.pk}/").content.decode()
    assert "Record Posting Evidence" not in page
    refused = post(
        planner,
        f"/stores/lots/{oil.pk}/move/",
        request_id=str(uuid4()),
        source=str(oil.evidence.location_id),
        destination=str(StoresLocation.objects.none().model.objects.none().first() or ""),
    )
    assert refused.status_code == 200
    with working_for(stocked.ours.id, stocked.planner.id):
        with pytest.raises(RefusedError, match="Current Stores Appointment"):
            stores.move(
                stocked.planner,
                oil,
                request_id=uuid4(),
                source=place("BAY-C"),
                destination=place("OIL-2"),
                quantity=Decimal(1),
                moved_on=TODAY,
                evidence="x",
            )
    lucy = signed_in(stocked.lucy)
    assert "Record Posting Evidence" in get(lucy, f"/stores/{entry.pk}/").content.decode()
    # Last valid day, then expiry, then a withdrawal and a person who has left.
    with working_for(stocked.ours.id, stocked.lucy.id):
        grant = StoresAppointment.objects.get(person__user=stocked.lucy, action=StoresAction.MOVE)
        assert stores.may_act(stocked.lucy, Action.RECORD_STORES, StoresAction.MOVE, grant.ends_on)
        assert not stores.may_act(
            stocked.lucy,
            Action.RECORD_STORES,
            StoresAction.MOVE,
            grant.ends_on + timedelta(days=1),
        )
        assert not stores.may_act(
            stocked.lucy,
            Action.RECORD_STORES,
            StoresAction.MOVE,
            grant.starts_on - timedelta(days=1),
        )
    with working_for(stocked.ours.id, stocked.administrator.id):
        stores.withdraw_appointment(
            stocked.administrator, grant, request_id=uuid4(), evidence="Synthetic withdrawal"
        )
    with working_for(stocked.ours.id, stocked.lucy.id):
        assert not stores.may_act(stocked.lucy, Action.RECORD_STORES, StoresAction.MOVE, TODAY)
        with pytest.raises(RefusedError, match="Current Stores Appointment"):
            stores.move(
                stocked.lucy,
                oil,
                request_id=uuid4(),
                source=place("BAY-C"),
                destination=place("OIL-2"),
                quantity=Decimal(1),
                moved_on=TODAY,
                evidence="x",
            )
        # The database refuses the withdrawn appointment directly too.
        with pytest.raises(DatabaseError, match="current Stores appointment"), transaction.atomic():
            StockMovement.objects.create(
                organisation_id=oil.organisation_id,
                submission=uuid4(),
                posting=oil,
                kind=MovementKind.TRANSFER,
                source=place("BAY-C"),
                destination=place("OIL-2"),
                quantity=Decimal(1),
                moved_on=TODAY,
                evidence="Direct",
                recorded_on=TODAY,
                appointment=grant,
            )
        count_grant = StoresAppointment.objects.get(
            person__user=stocked.lucy, action=StoresAction.COUNT
        )
        Person.objects.filter(user=stocked.lucy).update(left_on=TODAY)
        assert not stores.may_act(stocked.lucy, Action.RECORD_STORES, StoresAction.COUNT, TODAY)
        with pytest.raises(DatabaseError, match="current Stores appointment"), transaction.atomic():
            StockCount.objects.create(
                organisation_id=oil.organisation_id,
                submission=uuid4(),
                posting=oil,
                location=place("BAY-C"),
                counted=Decimal(24),
                on_hand=Decimal(0),
                counted_on=TODAY,
                evidence="Direct",
                appointment=count_grant,
            )
        assert held("RX-006") == {"BAY-C": Decimal(24)}


def test_s08_another_organisation_cannot_be_referenced(stocked: Sample) -> None:
    """REQ-002, ADR-0002. Cross-organisation parents are refused by PostgreSQL."""
    with working_for(stocked.ours.id, stocked.lucy.id):
        oil = lot("RX-006")
        grant = StoresAppointment.objects.get(person__user=stocked.lucy, action=StoresAction.MOVE)
        ours = place("OIL-2")
    with working_for(stocked.other.id, stocked.stranger.id):
        assert not StockPosting.objects.exists()
        with pytest.raises(DatabaseError), transaction.atomic():
            StockMovement.objects.create(
                organisation_id=stocked.other.id,
                submission=uuid4(),
                posting_id=oil.pk,
                kind=MovementKind.TRANSFER,
                source_id=ours.pk,
                destination_id=ours.pk,
                quantity=Decimal(1),
                moved_on=TODAY,
                evidence="Foreign",
                recorded_on=TODAY,
                appointment_id=grant.pk,
            )
    stranger = signed_in(stocked.stranger)
    assert post(stranger, f"/stores/lots/{oil.pk}/move/", request_id=str(uuid4())).status_code in {
        403,
        404,
    }


def test_s08_appointments_are_recorded_by_the_administrator_for_people_with_a_sign_in(
    stocked: Sample,
) -> None:
    admin = signed_in(stocked.administrator)
    with working_for(stocked.ours.id, stocked.administrator.id):
        planner = Person.objects.get(user=stocked.planner)
        before = StoresAppointment.objects.count()
    form = {
        "request_id": str(uuid4()),
        "approval": "Part-CAO",
        "person": str(planner.pk),
        "action": StoresAction.COUNT,
        "starts_on": "2026-11-18",
        "ends_on": "2027-11-17",
        "exposition_reference": "Synthetic Stores procedure",
        "authority": "Synthetic signed appointment",
    }
    assert post(admin, "/stores/appointments/add/", **form).status_code == 302
    assert post(admin, "/stores/appointments/add/", **form).status_code == 302  # double submit
    assert post(signed_in(stocked.lucy), "/stores/appointments/add/", **form).status_code == 403
    with working_for(stocked.ours.id, stocked.administrator.id):
        assert StoresAppointment.objects.count() == before + 1


# S10 Exports


def test_s10_the_organisation_archive_carries_the_ledger_and_verifies(as_lucy: User) -> None:
    """REQ-135, REQ-358. Intended use alone creates no aircraft record."""
    from airworthiness_plus.aircraft.models import Aircraft
    from airworthiness_plus.exports.build import build
    from airworthiness_plus.exports.registry import REGISTRY
    from airworthiness_plus.exports.verify import verify

    export = build(as_lucy.organisation, by=as_lucy)
    assert verify(export.content).problems == ()
    names = {one.table for one in REGISTRY if one.of_aircraft is None}
    for table in (
        "logistics_stockposting",
        "logistics_stockmovement",
        "logistics_stockcount",
        "logistics_postingevidence",
        "logistics_storeslocation",
        "logistics_storesappointment",
    ):
        assert table in names
    # No movement, posting or archive link is made for the receipt's intended aircraft.
    assert not Aircraft.objects.filter(registration="G-DGHI").exists()
    rx002 = decision("RX-002")
    assert "G-DGHI" in rx002.receipt.intended_use
    assert not StockPosting.objects.filter(disposition=rx002).exists()


# S09 Ledger invariants over generated movement sequences

PLACES = ("BAY-C", "OIL-2", "BAY-A", "BAY-D", "QUAR-1")
MOVES = st.lists(
    st.tuples(
        st.sampled_from(PLACES),
        st.sampled_from(PLACES),
        st.decimals(min_value=Decimal("-1"), max_value=Decimal(30), places=3),
    ),
    max_size=8,
)


@settings(
    max_examples=40,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@given(moves=MOVES)
def test_s09_generated_movements_conserve_custody_and_never_go_negative(
    as_lucy: User, moves: list[tuple[str, str, Decimal]]
) -> None:
    """REQ-358. Only intake and authorised adjustments change total custody in PR 1."""
    with transaction.atomic():
        oil = lot("RX-006")
        accepting = {"BAY-C", "OIL-2"}
        for source, destination, quantity in moves:
            before = held("RX-006")
            try:
                stores.move(
                    as_lucy,
                    oil,
                    request_id=uuid4(),
                    source=place(source),
                    destination=place(destination),
                    quantity=quantity,
                    moved_on=TODAY,
                    evidence="Generated movement",
                )
            except RefusedError:
                assert held("RX-006") == before
                expected_refusal = (
                    destination not in accepting
                    or source == destination
                    or not stores.fits(StockUnit.LITRE, quantity)
                    or before.get(source, Decimal(0)) < quantity
                )
                assert expected_refusal
            after = held("RX-006")
            assert all(amount > 0 for amount in after.values())
            assert set(after) <= accepting
            assert sum(after.values()) == Decimal(24)
        transaction.set_rollback(True)


def _grant_allocation_actions(sample: Sample) -> None:
    with working_for(sample.ours.pk, sample.administrator.pk):
        person = Person.objects.get(user=sample.lucy)
        for action in (
            StoresAction.RESERVE,
            StoresAction.ISSUE,
            StoresAction.RETURN,
            StoresAction.QUARANTINE,
        ):
            stores.record_appointment(
                sample.administrator,
                request_id=uuid4(),
                approval="Part-CAO",
                person=person,
                action=action,
                starts_on=TODAY,
                ends_on=TODAY + timedelta(days=30),
                exposition_reference="Synthetic Stores procedure, revision 1",
                authority="Synthetic appointment",
            )


def _allocation_card(sample: Sample, aircraft: Aircraft) -> WorkCard:
    with working_for(sample.ours.pk, sample.lucy.pk):
        package = planning.build_package(
            aircraft,
            reference="WP-STORES-ALLOC",
            title="Check installation",
            location="Bay B",
            starts_on=TODAY,
            ends_on=TODAY + timedelta(days=1),
        )
        dataset = data.record_data(
            organisation=sample.ours,
            title="Synthetic Parts Manual",
            author="Maker",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="1",
            revision_date=TODAY,
            check_due=TODAY + timedelta(days=7),
        )
        card = planning.add_card(
            package,
            title="Replace hardware",
            data_set=dataset,
            instruction="Chapter 53",
            planned_hours=Decimal(1),
        )
        order = contracts.add_work_order(
            aircraft,
            work=package.title,
            ordered_by=OrderedBy.MANAGER,
            agreed_on=TODAY,
        )
        planning.link_order(package, order)
        return card


def test_allocation_rechecks_issue_eligibility_and_preserves_quarantined_custody(
    stocked: Sample,
    day: Day,
) -> None:
    aircraft = add_sample_fleet(stocked)["G-ABCD"]
    _grant_allocation_actions(stocked)
    card = _allocation_card(stocked, aircraft)
    with working_for(stocked.ours.pk, stocked.lucy.pk):
        user = stocked.lucy
        bolts = lot("RX-007")
        source = place("BAY-B")
        quarantine = place("QUAR-1")
        reservation: dict[str, Any] = {
            "source": source,
            "card": card,
            "quantity": Decimal(4),
            "required_identity": "[Bolt Standard]",
            "applicable_source": "Synthetic Parts Manual revision 1, Figure 53",
            "evidence": "Match installation request and reservation label",
        }
        with pytest.raises(RefusedError, match="Unfinished Card on an Issued Package"):
            allocations.record(
                user, bolts, AllocationKind.RESERVE, request_id=uuid4(), **reservation
            )
        planning.issue_package(card.package)
        with pytest.raises(RefusedError, match="Must Match the Received Lot"):
            allocations.record(
                user,
                bolts,
                AllocationKind.RESERVE,
                request_id=uuid4(),
                **{**reservation, "required_identity": "Unapproved alternate"},
            )
        reserve_id = uuid4()
        reserved = allocations.record(
            user, bolts, AllocationKind.RESERVE, request_id=reserve_id, **reservation
        )
        assert (
            allocations.record(
                user, bolts, AllocationKind.RESERVE, request_id=reserve_id, **reservation
            )
            == reserved
        )
        with pytest.raises(RefusedError, match="Different Custody Evidence"):
            allocations.record(
                user,
                bolts,
                AllocationKind.RESERVE,
                request_id=reserve_id,
                **{**reservation, "quantity": Decimal(1)},
            )
        (position,) = stores.positions(user.organisation, day.today, posting=bolts)
        assert (position.on_hand, position.reserved, position.available) == (
            Decimal(50),
            Decimal(4),
            Decimal(46),
        )
        with pytest.raises(RefusedError, match="Less Unreserved Stock"):
            stores.move(
                user,
                bolts,
                request_id=uuid4(),
                source=source,
                destination=place("BAY-A"),
                quantity=Decimal(47),
                moved_on=day.today,
                evidence="Would move reserved bolts",
            )
        with pytest.raises(DatabaseError), transaction.atomic():
            StockAllocation.objects.filter(pk=reserved.pk).update(evidence="Rewritten")
        issue_id = uuid4()
        issued = allocations.record(
            user,
            bolts,
            AllocationKind.ISSUE,
            preceding=reserved,
            request_id=issue_id,
            evidence="Transferred to workshop against authorised card",
        )
        assert (
            allocations.record(
                user,
                bolts,
                AllocationKind.ISSUE,
                preceding=reserved,
                request_id=issue_id,
                evidence="Transferred to workshop against authorised card",
            )
            == issued
        )
        with pytest.raises(RefusedError, match="Already Been Continued"):
            allocations.record(
                user,
                bolts,
                AllocationKind.ISSUE,
                preceding=reserved,
                request_id=uuid4(),
                evidence="Retry with a new request",
            )
        assert stores.on_hand(bolts, source) == 46
        returned = allocations.record(
            user,
            bolts,
            AllocationKind.RETURN,
            preceding=issued,
            request_id=uuid4(),
            destination=quarantine,
            evidence="Packaging opened; retain for receiving inspection",
        )
        allocations.record(
            user,
            bolts,
            AllocationKind.QUARANTINE,
            request_id=uuid4(),
            source=source,
            destination=quarantine,
            quantity=Decimal(1),
            evidence="Label damaged",
        )
        position_by_code = {
            item.location.code: item
            for item in stores.positions(user.organisation, day.today, posting=bolts)
        }
        assert position_by_code["BAY-B"].on_hand == position_by_code["BAY-B"].available == 45
        assert position_by_code["QUAR-1"].on_hand == 5
        assert position_by_code["QUAR-1"].available == 0
        with pytest.raises(RefusedError, match="New Receiving Decision"):
            stores.move(
                user,
                bolts,
                request_id=uuid4(),
                source=quarantine,
                destination=source,
                quantity=Decimal(1),
                moved_on=day.today,
                evidence="Forged clearing of quarantine",
            )
        with pytest.raises(RefusedError, match="Does Not Hold Serviceable Stock"):
            allocations.record(
                user,
                bolts,
                AllocationKind.RESERVE,
                request_id=uuid4(),
                **{**reservation, "source": quarantine},
            )
        assert Event.of(returned).get().actor_id == user.pk
        exported = build(stocked.ours, by=user)
        assert verify(exported.content).problems == ()
        records = opened(exported.content)["records/logistics_stockallocation.json"]
        assert {row["kind"] for row in records} == {"Reserve", "Issue", "Return", "Quarantine"}
        assert any(row["preceding_id"] == str(issued.pk) for row in records)
    with working_for(stocked.other.pk, stocked.stranger.pk):
        assert not StockAllocation.objects.exists()


def test_issue_rechecks_lot_expiry_after_reservation(stocked: Sample, day: Day) -> None:
    _grant_allocation_actions(stocked)
    card = _allocation_card(stocked, add_sample_fleet(stocked)["G-ABCD"])
    with working_for(stocked.ours.pk, stocked.lucy.pk):
        planner = stocked.lucy
        planning.issue_package(card.package)
        source = place("BAY-A")
        evidence_for(
            planner,
            "RX-002",
            unit=StockUnit.EACH,
            quantity=Decimal(1),
            part_number="PN-EXPIRY",
            serial="SN-EXPIRY",
            shelf_life_basis=ShelfLifeBasis.THROUGH,
            shelf_life_to=TODAY,
            location=source,
        )
        posting = stores.post(planner, decision("RX-002"), request_id=uuid4())
        reservation = allocations.record(
            planner,
            posting,
            AllocationKind.RESERVE,
            request_id=uuid4(),
            source=source,
            card=card,
            quantity=Decimal(1),
            required_identity="PN-EXPIRY",
            applicable_source="Synthetic applicable manual and revision",
            evidence="Booked",
        )
        day.today += timedelta(days=1)
        with pytest.raises(RefusedError, match="Shelf Life Blocks Issue"):
            allocations.record(
                planner,
                posting,
                AllocationKind.ISSUE,
                request_id=uuid4(),
                preceding=reservation,
                evidence="Request after expiry",
            )
        assert StockAllocation.objects.filter(posting=posting).count() == 1
        (position,) = stores.positions(stocked.ours, day.today, posting=posting)
        assert position.on_hand == position.reserved == Decimal(1)
        assert position.available == Decimal(0)


def test_real_ledger_reconciles_zrh_stores_and_network_totals(stocked: Sample) -> None:
    identity = "PN-AMOS-STATION"
    accepted(stocked, "RX-STATION", ItemClass.SERVICEABLE, 10, "Synthetic station component")
    with working_for(stocked.ours.pk, stocked.lucy.pk):
        user = stocked.lucy
        places = {
            code: stores.record_location(
                user,
                request_id=uuid4(),
                code=code,
                station=station,
                name=name,
                kind=LocationKind.SERVICEABLE,
                classes=[ItemClass.SERVICEABLE],
                storage_conditions="Synthetic compatible storage",
                secure=False,
            )
            for station, code, name in (
                ("zrh", "ZRH-MAIN", "ZRH Main"),
                ("ZRH", "ZRH-LINE", "ZRH Line"),
                ("BSL", "BSL-MAIN", "BSL Main"),
                ("LUG", "LUG-MAIN", "LUG Main"),
                ("GVA", "GVA-MAIN", "GVA Main"),
            )
        }
        evidence_for(
            user,
            "RX-STATION",
            unit=StockUnit.EACH,
            quantity=Decimal(10),
            manufacturer="Synthetic manufacturer",
            part_number=identity,
            batch="LOT-AMOS-04",
            shelf_life_basis=ShelfLifeBasis.NOT_APPLICABLE,
            location=places["ZRH-MAIN"],
        )
        posting = stores.post(user, decision("RX-STATION"), request_id=uuid4())
        for code in ("ZRH-LINE", "BSL-MAIN", "LUG-MAIN"):
            stores.move(
                user,
                posting,
                request_id=uuid4(),
                source=places["ZRH-MAIN"],
                destination=places[code],
                quantity=Decimal(1),
                moved_on=TODAY,
                evidence="Synthetic aircraft network stock allocation",
            )
        lines = stores.positions(stocked.ours, TODAY, posting=posting)
        locations = stores.by_location(lines, places.values())
        assert {item.location.code: item.totals[0].on_hand for item in locations} == {
            "ZRH-MAIN": Decimal(7),
            "ZRH-LINE": Decimal(1),
            "BSL-MAIN": Decimal(1),
            "LUG-MAIN": Decimal(1),
            "GVA-MAIN": Decimal(0),
        }
        totals = stores.by_station(locations)
        assert {station: values[0].available for station, values in totals.items()} == {
            "ZRH": Decimal(8),
            "BSL": Decimal(1),
            "LUG": Decimal(1),
            "GVA": Decimal(0),
        }
        assert stores.totals(lines)[StockUnit.EACH].on_hand == Decimal(10)
    page = get(signed_in(stocked.reader), f"/stores/?identity={identity.lower()}")
    assert page.status_code == 200
    body = page.content.decode()
    assert '<tr><th scope="row">ZRH</th><td>Each</td><td>8</td><td>0</td><td>8</td>' in body
    assert '<tr><th scope="row">GVA</th><td>Each</td><td>0</td><td>0</td><td>0</td>' in body
    assert (
        '<tr><th scope="row" colspan="2">All Locations</th><td></td><td>Each</td>'
        "<td>10</td><td>0</td><td>10</td>"
    ) in body
    assert "ZRH-MAIN, ZRH Main" in body
    assert "ZRH-LINE, ZRH Line" in body
    assert "Bay B, Standard Parts Drawers" not in body
