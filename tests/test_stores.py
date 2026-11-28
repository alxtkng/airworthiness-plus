"""Stores PR 1: the receipt-to-stock contract as the consumer of Goods In (REQ-358).

The cases follow ``assurance/phase-4-stores-handoff.md``, approved by Alex King on
28 November 2026. Stock is posted once per immutable Goods In disposition when unit,
identity, location, shelf life and evidence are resolved. Balances come from movements.
"""

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import receiving, stock_appointments, stores
from airworthiness_plus.logistics.models import (
    CheckKind,
    CheckOutcome,
    Destination,
    DocumentKind,
    ItemClass,
    LocationKind,
    MovementKind,
    Receipt,
    ReceivingDisposition,
    StockAppointment,
    StockAppointmentWithdrawal,
    StockCount,
    StockDuty,
    StockEntry,
    StockMovement,
    StockPosting,
    StockResolution,
    StockUnit,
    StoreLocation,
)
from airworthiness_plus.logistics.services import RefusedError
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.people.models import Person
from tests.conftest import as_owner
from tests.support import Sample, appoint_for_stores, get, post, signed_in

pytestmark = pytest.mark.django_db

TODAY = date(2026, 11, 28)
ARRIVED = date(2026, 11, 16)


@pytest.fixture(autouse=True)
def today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


@pytest.fixture
def ours(sample: Sample) -> Iterator[Sample]:
    with working_for(sample.ours.id, sample.lucy.id):
        yield sample


def _lucy(sample: Sample) -> Person:
    return Person.objects.get(user=sample.lucy)


def _inspector(organisation: Organisation) -> Person:
    chosen = Person.objects.filter(organisation=organisation, full_name="Chris Moore").first()
    return chosen or Person.objects.filter(organisation=organisation).order_by("id")[0]


def receipt(
    organisation: Organisation,
    line: str,
    *,
    classification: str = ItemClass.SERVICEABLE,
    quantity: int = 1,
    item: str = "Synthetic Trim Cable",
    shelf_life_to: date | None = None,
    received_on: date = ARRIVED,
) -> Receipt:
    arrival = receiving.receive(
        organisation,
        item=item,
        received_on=received_on,
        classification=classification,
        source="Synthetic Supplier",
        item_reference=f"Synthetic reference {line}",
        quantity=quantity,
        delivery_reference=line,
        release_document="Synthetic release evidence",
        shelf_life_to=shelf_life_to,
    )
    for kind in CheckKind:
        shelf = kind == CheckKind.SHELF and shelf_life_to is None
        receiving.record_check(
            arrival,
            check=kind,
            outcome=CheckOutcome.NOT_APPLICABLE if shelf else CheckOutcome.PASS,
            checked_on=received_on,
            evidence=f"Synthetic {kind} evidence",
        )
    return arrival


def dispose(arrival: Receipt, outcome: str = Destination.STORES) -> ReceivingDisposition:
    evidence: dict[str, str] = {}
    if outcome == Destination.STORES:
        if arrival.classification == ItemClass.SERVICEABLE:
            evidence = {"document_kind": DocumentKind.CAA_FORM_1, "document_reference": "F1-1"}
        else:
            evidence = {
                "document_kind": DocumentKind.CONFORMITY,
                "document_reference": "COC-1",
                "evidence_basis": "Synthetic Specification 1",
                "manufacturing_source": "Synthetic Factory",
                "material_supplier_source": "Synthetic Supplier",
            }
    return receiving.dispose(
        arrival,
        approval=ApprovalType.PART_CAO,
        inspector=_inspector(arrival.organisation),
        inspector_authority="Synthetic RI-1",
        inspected_on=arrival.received_on,
        disposition_on=arrival.received_on,
        outcome=outcome,
        destination="Synthetic destination text",
        evidence="Synthetic decision evidence",
        **evidence,
    )


def location(
    organisation: Organisation,
    name: str,
    kind: str = LocationKind.SERVICEABLE,
    **holds: bool,
) -> StoreLocation:
    classes = holds or {"holds_components": True, "holds_standard_parts": True}
    return stores.add_location(
        organisation,
        name=name,
        kind=kind,
        holds_components=classes.get("holds_components", False),
        holds_standard_parts=classes.get("holds_standard_parts", False),
        holds_materials=classes.get("holds_materials", False),
        secure=kind == LocationKind.QUARANTINE or classes.get("secure", False),
    )


def resolve(
    decision: ReceivingDisposition,
    actor: Person,
    place: StoreLocation | None,
    **values: object,
) -> None:
    fields: dict[str, object] = {
        "unit": StockUnit.EACH,
        "part_number": "PN-713",
        "serial_number": "",
        "batch_number": "LOT-1",
        "specification": "",
        "shelf_life_basis": "Not Applicable",
        **values,
    }
    appoint_for_stores(actor)
    stores.resolve(
        decision,
        actor=actor,
        authority="Synthetic Stores Appointment ST-1",
        evidence="Original receipt and release reviewed on file",
        evidence_on=TODAY,
        location=place,
        **fields,  # type: ignore[arg-type]
    )


def posted(
    decision: ReceivingDisposition, actor: Person, place: StoreLocation, **values: object
) -> StockPosting:
    resolve(decision, actor, place, **values)
    return stores.post(decision, actor=actor, authority="Synthetic ST-1", posted_on=TODAY)


class Moved(TypedDict):
    moved_on: date
    actor: Person
    authority: str
    evidence: str


def on_hand(lot: StockPosting, place: StoreLocation) -> Decimal:
    return stores.balance(StockPosting.objects.get(pk=lot.pk), place)


# S01 Consumer outcomes


def test_s01_each_outcome_has_its_stock_state_and_no_other_organisation_data(
    ours: Sample,
) -> None:
    """REQ-357, REQ-358. Accepted, unresolved, quarantined, returned and awaiting lines."""
    actor = _lucy(ours)
    bay = location(ours.ours, "Synthetic Bay A")
    cage = location(ours.ours, "Synthetic Cage", LocationKind.QUARANTINE, holds_components=True)
    accepted = dispose(receipt(ours.ours, "S01-ACCEPTED"))
    unresolved = dispose(receipt(ours.ours, "S01-UNRESOLVED"))
    held = dispose(receipt(ours.ours, "S01-HELD"), Destination.QUARANTINE)
    returned = dispose(receipt(ours.ours, "S01-RETURNED"), Destination.RETURN)
    awaiting = receipt(ours.ours, "S01-AWAITING")

    lot = posted(accepted, actor, bay, serial_number="SN-1", batch_number="")
    assert (lot.quantity, lot.unit, lot.held) == (Decimal(1), StockUnit.EACH, False)
    assert stores.available(accepted, TODAY, 30) == 1
    assert lot.movements.get().kind == MovementKind.INTAKE

    reasons = stores.posting_blockers(unresolved, None)
    assert any("Identity" in one for one in reasons)
    assert any("Location" in one for one in reasons)
    assert stores.available(unresolved, TODAY, 30) == 0
    with pytest.raises(RefusedError, match="Not Ready to Post"):
        stores.post(unresolved, actor=actor, authority="ST-1", posted_on=TODAY)

    hold = posted(held, actor, cage, serial_number="SN-2", batch_number="")
    assert hold.held and on_hand(hold, cage) == 1
    assert stores.available(held, TODAY, 30) == 0

    with pytest.raises(RefusedError, match="Acceptance or a Quarantine"):
        resolve(returned, actor, bay)
    assert stores.posting_blockers(returned, None) == ["Returned to Supplier. Nothing Is Credited"]
    assert not StockPosting.objects.filter(disposition=returned).exists()
    assert not ReceivingDisposition.objects.filter(receipt=awaiting).exists()

    reader = signed_in(ours.reader)
    entry = StockEntry.objects.get(disposition=unresolved)
    page = get(reader, f"/stores/{entry.pk}/").content
    assert b"Awaiting Stock Posting" in page and b"Posting Blockers" in page
    register = get(reader, "/stores/").content
    for text in (b"Posted to Stock", b"Quarantine Hold", b"S01-RETURNED", b"Synthetic Bay A"):
        assert text in register
    stranger = signed_in(ours.stranger)
    assert get(stranger, f"/stores/{entry.pk}/").status_code == 404
    assert get(stranger, f"/stores/dispositions/{held.pk}/").status_code == 404
    assert b"S01-HELD" not in get(stranger, "/stores/").content
    with working_for(ours.other.id, ours.stranger.id):
        assert not StockPosting.objects.exists()
        assert not StoreLocation.objects.exists()
        foreign = location(ours.other, "Synthetic Bay A")
    with pytest.raises(RefusedError, match="This Organisation"):
        resolve(unresolved, actor, foreign)


# S02 Idempotency and atomicity


def test_s02_posting_is_once_only_and_a_failure_leaves_nothing(ours: Sample) -> None:
    """REQ-358. Replay returns the original; a conflicting replay keeps it; rollback is whole."""
    actor = _lucy(ours)
    bay = location(ours.ours, "Synthetic Bay B")
    decision = dispose(receipt(ours.ours, "S02-LINE", quantity=5))
    first = posted(decision, actor, bay, batch_number="LOT-5")
    again = stores.post(decision, actor=actor, authority="Synthetic ST-1", posted_on=TODAY)
    assert again.pk == first.pk
    assert StockPosting.objects.filter(disposition=decision).count() == 1
    assert StockMovement.objects.filter(lot=first).count() == 1
    with pytest.raises(RefusedError, match="Already Posted"):
        resolve(decision, actor, bay, batch_number="LOT-6")
    with pytest.raises(IntegrityError), transaction.atomic():
        StockPosting.objects.create(
            organisation=ours.ours,
            disposition=decision,
            resolution=first.resolution,
            held=False,
            unit=StockUnit.EACH,
            quantity=Decimal(500),
            location=bay,
            location_name="Changed",
            location_kind=bay.kind,
            shelf_life_basis="Not Applicable",
            physical_on=decision.disposition_on,
            posted_on=TODAY,
            actor=actor,
            actor_name=actor.full_name,
            authority="Conflicting replay",
        )
    first.refresh_from_db()
    assert first.quantity == 5 and on_hand(first, bay) == 5

    # Inject a failure between the posting record and its opening movement.
    failing = dispose(receipt(ours.ours, "S02-FAILING", quantity=3))
    resolve(failing, actor, bay, batch_number="LOT-3")
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(
            "CREATE FUNCTION test_fail_intake() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN RAISE EXCEPTION 'Injected intake failure' USING ERRCODE = 'check_violation'; "
            "END $$; CREATE TRIGGER test_fail_intake BEFORE INSERT ON logistics_stockmovement "
            "FOR EACH ROW EXECUTE FUNCTION test_fail_intake();"
        )
    events = Event.objects.count()
    with pytest.raises(RefusedError, match="Injected intake failure"):
        stores.post(failing, actor=actor, authority="Synthetic ST-1", posted_on=TODAY)
    assert not StockPosting.objects.filter(disposition=failing).exists()
    assert not StockMovement.objects.filter(lot__disposition=failing).exists()
    assert Event.objects.count() == events
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(
            "DROP TRIGGER test_fail_intake ON logistics_stockmovement; "
            "DROP FUNCTION test_fail_intake();"
        )
    retried = stores.post(failing, actor=actor, authority="Synthetic ST-1", posted_on=TODAY)
    assert on_hand(retried, bay) == 3


def test_s02_a_submitted_quantity_or_location_cannot_override_the_records(ours: Sample) -> None:
    """The database copies the persisted quantity and the latest resolution."""
    actor = _lucy(ours)
    bay = location(ours.ours, "Synthetic Bay C")
    other_bay = location(ours.ours, "Synthetic Bay D")
    decision = dispose(receipt(ours.ours, "S02-OVERRIDE", quantity=2))
    resolve(decision, actor, bay, batch_number="LOT-2")
    reading = stores.latest_resolution(decision)
    assert reading is not None
    lot = StockPosting.objects.create(
        organisation=ours.ours,
        disposition=decision,
        resolution=reading,
        held=True,
        unit=StockUnit.LITRE,
        quantity=Decimal(900),
        location=other_bay,
        location_name="Wrong",
        location_kind=LocationKind.QUARANTINE,
        shelf_life_basis="Dated",
        physical_on=decision.disposition_on,
        posted_on=TODAY,
        actor=actor,
        actor_name=actor.full_name,
        authority="Direct insert",
    )
    lot.refresh_from_db()
    assert (lot.quantity, lot.unit, lot.held, lot.location_id) == (
        Decimal(2),
        StockUnit.EACH,
        False,
        bay.pk,
    )
    assert lot.location_name == "Synthetic Bay C"


# S03 Quantities and identities


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        ("1", "Each", Decimal(1)),
        ("0.001", "Litre", Decimal("0.001")),
        ("2147483647", "Each", Decimal(2147483647)),
        ("2147483647", "Litre", Decimal(2147483647)),
        ("24.500", "Litre", Decimal("24.5")),
    ],
)
def test_s03_supported_quantities_are_exact(value: str, unit: str, expected: Decimal) -> None:
    assert stores.checked_quantity(value, unit) == expected


@pytest.mark.parametrize(
    ("value", "unit", "reason"),
    [
        ("0", "Each", "More Than Zero"),
        ("-1", "Litre", "More Than Zero"),
        ("0.0001", "Litre", "Three Decimal Places"),
        ("2147483648", "Each", "Cannot Exceed"),
        ("2147483647.001", "Litre", "Cannot Exceed"),
        ("", "Each", "Number"),
        ("1", "Kilogram", "Each or Litre"),
        ("1.5", "Each", "Whole Number"),
        ("NaN", "Litre", "Number"),
        ("1e3", "Each", "Number"),
        ("2,5", "Litre", "Number"),
    ],
)
def test_s03_unsupported_quantities_are_refused_not_rounded(
    value: str, unit: str, reason: str
) -> None:
    with pytest.raises(RefusedError, match=reason):
        stores.checked_quantity(value, unit)


def test_s03_identity_serial_and_exact_moves(ours: Sample) -> None:
    """Missing identity blocks posting. One serial has one custody position."""
    actor = _lucy(ours)
    bay = location(ours.ours, "Synthetic Bay E")
    shelf = location(ours.ours, "Synthetic Shelf F")
    first = dispose(receipt(ours.ours, "S03-SERIAL-1"))
    resolve(first, actor, bay, part_number="", batch_number="")
    assert any("Identity" in one for one in stores.posting_blockers(first, None))
    with pytest.raises(RefusedError, match="Identity"):
        stores.post(first, actor=actor, authority="ST-1", posted_on=TODAY)
    with pytest.raises(RefusedError, match="Each"):
        resolve(first, actor, bay, unit=StockUnit.LITRE, serial_number="SN-9")
    lot = posted(first, actor, bay, serial_number="SN-9", batch_number="")
    duplicate = dispose(receipt(ours.ours, "S03-SERIAL-2"))
    resolve(duplicate, actor, bay, part_number="pn-713", serial_number="sn-9", batch_number="")
    with pytest.raises(RefusedError, match="Current Custody"):
        stores.post(duplicate, actor=actor, authority="ST-1", posted_on=TODAY)
    with pytest.raises(RefusedError, match=r"Moves Whole|Whole Number"):
        stores.move(
            lot,
            from_location=bay,
            to_location=shelf,
            quantity="0.5",
            moved_on=TODAY,
            actor=actor,
            authority="ST-1",
            evidence="Synthetic move",
        )
    multi = dispose(receipt(ours.ours, "S03-LOT", quantity=10))
    batch = posted(multi, actor, bay, batch_number="LOT-10")
    common = Moved(moved_on=TODAY, actor=actor, authority="ST-1", evidence="Move")
    with pytest.raises(RefusedError, match="Does Not Hold"):
        stores.move(batch, from_location=bay, to_location=shelf, quantity="11", **common)
    assert on_hand(batch, bay) == 10
    stores.move(batch, from_location=bay, to_location=shelf, quantity="10", **common)
    assert (on_hand(batch, bay), on_hand(batch, shelf)) == (Decimal(0), Decimal(10))
    with pytest.raises(RefusedError, match="Does Not Hold"):
        stores.move(batch, from_location=bay, to_location=shelf, quantity="1", **common)


# S04 Locations and custody


def test_s04_oil_moves_between_permitted_locations_and_refusals_keep_custody(
    ours: Sample,
) -> None:
    """24 L received; 8 L moved. On hand 16 and 8, total 24, reserved 0, available 24."""
    actor = _lucy(ours)
    store = location(ours.ours, "Synthetic Oil Store", holds_materials=True)
    second = location(ours.ours, "Synthetic Line Store", holds_materials=True)
    parts_only = location(ours.ours, "Synthetic Parts Bay")
    cage = location(ours.ours, "Synthetic Oil Cage", LocationKind.QUARANTINE, holds_materials=True)
    withdrawn = stores.withdraw_location(
        location(ours.ours, "Synthetic Old Store", holds_materials=True)
    )
    oil = dispose(receipt(ours.ours, "S04-OIL", classification=ItemClass.MATERIAL, quantity=24))
    lot = posted(
        oil,
        actor,
        store,
        unit=StockUnit.LITRE,
        part_number="",
        batch_number="OIL-24",
        specification="Synthetic Oil Specification",
    )
    common = Moved(moved_on=TODAY, actor=actor, authority="ST-1", evidence="Move 8 L")
    move = stores.move(lot, from_location=store, to_location=second, quantity="8", **common)
    assert (move.from_location_id, move.to_location_id, move.actor_name) == (
        store.pk,
        second.pk,
        actor.full_name,
    )
    lines = stores.positions([StockPosting.objects.get(pk=lot.pk)], TODAY, 30)
    assert {(one.location.name, one.on_hand, one.reserved, one.available) for one in lines} == {
        ("Synthetic Oil Store", Decimal(16), Decimal(0), Decimal(16)),
        ("Synthetic Line Store", Decimal(8), Decimal(0), Decimal(8)),
    }
    assert sum(one.on_hand for one in lines) == 24
    for place, reason in (
        (withdrawn, "Withdrawn"),
        (parts_only, "Does Not Accept"),
    ):
        with pytest.raises(RefusedError, match=reason):
            stores.move(lot, from_location=store, to_location=place, quantity="1", **common)
    with pytest.raises(RefusedError, match="Secure"):
        stores.add_location(
            ours.ours,
            name="Synthetic Open Shelf",
            kind=LocationKind.QUARANTINE,
            holds_components=False,
            holds_standard_parts=False,
            holds_materials=True,
            secure=False,
        )
    with pytest.raises(DatabaseError), transaction.atomic():
        StoreLocation.objects.filter(pk=store.pk).update(name="Renamed")
    stores.move(lot, from_location=store, to_location=cage, quantity="1", **common)
    assert (on_hand(lot, store), on_hand(lot, cage)) == (Decimal(15), Decimal(1))
    with working_for(ours.other.id, ours.stranger.id):
        foreign = location(ours.other, "Synthetic Foreign Store", holds_materials=True)
    with pytest.raises(RefusedError, match="This Organisation"):
        stores.move(lot, from_location=store, to_location=foreign, quantity="1", **common)

    held = dispose(
        receipt(ours.ours, "S04-HELD", classification=ItemClass.MATERIAL, quantity=2),
        Destination.QUARANTINE,
    )
    hold = posted(
        held,
        actor,
        cage,
        unit=StockUnit.LITRE,
        part_number="",
        batch_number="OIL-2",
        specification="Synthetic Oil Specification",
    )
    with pytest.raises(RefusedError, match="Open Quarantine Hold"):
        stores.move(hold, from_location=cage, to_location=store, quantity="1", **common)
    assert on_hand(hold, cage) == 2


# S05 Shelf life


def _calendar_days(start: date, end: date) -> int:
    """Independent of the application: count days by ordinal arithmetic."""
    return end.toordinal() - start.toordinal()


@pytest.mark.parametrize(
    ("day", "inclusive", "start_of_day"),
    [
        (date(2026, 11, 17), "Current", "Current"),
        (date(2026, 11, 18), "Due Soon", "Due Soon"),
        (date(2026, 11, 29), "Due Soon", "Due Soon"),
        (date(2026, 11, 30), "Due Soon", "Expired"),
        (date(2026, 12, 1), "Expired", "Expired"),
    ],
)
def test_s05_shelf_life_boundaries(day: date, inclusive: str, start_of_day: str) -> None:
    """Valid through 30 November 2026 with a 12-day lead, and a start-of-day expiry."""
    label = date(2026, 11, 30)
    assert (_calendar_days(day, label) <= 12) == (inclusive != "Current")
    assert stores.shelf_status("Dated", label, "Valid Through the Date", day, 12) == inclusive
    assert (
        stores.shelf_status("Dated", label, "Expires at the Start of the Date", day, 12)
        == start_of_day
    )


def test_s05_unknown_and_not_applicable() -> None:
    day = date(2026, 11, 28)
    assert stores.shelf_status("", None, "", day, 12) == "Unknown"
    assert stores.shelf_status("Dated", date(2026, 12, 30), "", day, 12) == "Unknown"
    assert stores.shelf_status("Not Applicable", None, "", day, 12) == "Not Applicable"


def test_s05_expired_and_unresolved_shelf_life_have_no_availability(
    ours: Sample, monkeypatch: pytest.MonkeyPatch
) -> None:
    actor = _lucy(ours)
    store = location(ours.ours, "Synthetic Sealant Store", holds_materials=True)
    label = date(2026, 11, 30)
    sealant = dispose(
        receipt(
            ours.ours,
            "S05-SEALANT",
            classification=ItemClass.MATERIAL,
            quantity=4,
            shelf_life_to=label,
        )
    )
    values = {
        "unit": StockUnit.EACH,
        "part_number": "",
        "batch_number": "SEAL-4",
        "specification": "Synthetic Sealant Specification",
    }
    resolve(sealant, actor, store, **values, shelf_life_basis="")
    assert any("Shelf-Life" in one for one in stores.posting_blockers(sealant, None))
    with pytest.raises(RefusedError, match="Recorded Shelf Life"):
        resolve(sealant, actor, store, **values, shelf_life_basis="Not Applicable")
    resolve(
        sealant,
        actor,
        store,
        **values,
        shelf_life_basis="Dated",
        shelf_life_to=date(2026, 12, 31),
        shelf_life_rule="Valid Through the Date",
    )
    with pytest.raises(RefusedError, match="Does Not Match"):
        stores.post(sealant, actor=actor, authority="ST-1", posted_on=TODAY)
    lot = posted(
        sealant,
        actor,
        store,
        **values,
        shelf_life_basis="Dated",
        shelf_life_to=label,
        shelf_life_rule="Valid Through the Date",
    )
    assert stores.available(sealant, TODAY, 12) == 4
    assert stores.available(sealant, date(2026, 12, 1), 12) == 0
    expired = stores.positions([StockPosting.objects.get(pk=lot.pk)], date(2026, 12, 1), 12)
    assert [(one.on_hand, one.shelf) for one in expired] == [(Decimal(4), "Expired")]


# S06 Stock count and authorised adjustment


def test_s06_a_count_changes_nothing_until_an_authorised_adjustment(ours: Sample) -> None:
    """Count 46 against 50 bolts: variance -4, then one authorised -4 movement."""
    actor = _lucy(ours)
    bin_ = location(ours.ours, "Synthetic Bolt Bin")
    bolts = dispose(receipt(ours.ours, "S06-BOLTS", classification=ItemClass.STANDARD, quantity=50))
    lot = posted(
        bolts,
        actor,
        bin_,
        part_number="",
        batch_number="BOLT-50",
        specification="Synthetic NAS Standard",
    )
    tally = stores.count(
        lot,
        location=bin_,
        counted_quantity="46",
        counted_on=TODAY,
        counter=actor,
        evidence="Synthetic count sheet C-1",
    )
    assert (tally.ledger_quantity, tally.variance) == (Decimal(50), Decimal(-4))
    assert on_hand(lot, bin_) == 50

    planner = signed_in(ours.planner)
    assert post(planner, f"/stores/counts/{tally.pk}/adjust/").status_code == 403
    manager = signed_in(ours.lucy)
    refused = post(manager, f"/stores/counts/{tally.pk}/adjust/", moved_on="2026-11-28")
    assert refused.status_code == 200
    assert on_hand(lot, bin_) == 50
    values = {
        "moved_on": "2026-11-28",
        "evidence": "Synthetic variance investigation V-1",
        "authority": "Synthetic Adjustment Authority A-1",
    }
    assert post(manager, f"/stores/counts/{tally.pk}/adjust/", **values).status_code == 302
    assert post(manager, f"/stores/counts/{tally.pk}/adjust/", **values).status_code == 302
    adjustment = StockMovement.objects.get(count=tally)
    assert adjustment.kind == MovementKind.ADJUSTMENT
    assert (adjustment.from_location_id, adjustment.quantity) == (bin_.pk, Decimal(4))
    assert on_hand(lot, bin_) == 46
    assert StockMovement.objects.filter(lot=lot, kind=MovementKind.ADJUSTMENT).count() == 1

    stale = stores.count(
        lot, location=bin_, counted_quantity="40", counted_on=TODAY, counter=actor, evidence="C-2"
    )
    stores.move(
        lot,
        from_location=bin_,
        to_location=location(ours.ours, "Synthetic Bolt Bin 2"),
        quantity="1",
        moved_on=TODAY,
        actor=actor,
        authority="ST-1",
        evidence="Move",
    )
    with pytest.raises(RefusedError, match="Count Again"):
        stores.adjust(stale, actor=actor, authority="A-1", evidence="Stale", moved_on=TODAY)
    with pytest.raises(IntegrityError), transaction.atomic():
        StockMovement.objects.create(
            organisation=ours.ours,
            lot=lot,
            kind=MovementKind.ADJUSTMENT,
            from_location=bin_,
            quantity=Decimal(5),
            moved_on=TODAY,
            count=stale,
            actor=actor,
            actor_name=actor.full_name,
            authority="Direct",
            evidence="Direct",
        )
    assert StockCount.objects.filter(lot=lot).count() == 2


# S07 Upgrade and legacy reconciliation


def test_s07_legacy_dispositions_upgrade_and_reconcile_once(sample: Sample) -> None:
    """Historical decisions made before the ledger keep their IDs and evidence."""
    from django.db.migrations.executor import MigrationExecutor

    from airworthiness_plus.organisations.models import Approval

    with as_owner():
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old_apps = executor.migrate([("logistics", "0006_merge_receiving_and_subcontracting")]).apps
    old_receipt = old_apps.get_model("logistics", "Receipt")
    old_check = old_apps.get_model("logistics", "ReceivingCheck")
    old_decision = old_apps.get_model("logistics", "ReceivingDisposition")
    made: dict[str, UUID] = {}
    with working_for(sample.ours.id, sample.planner.id):
        approval = Approval.objects.get(approval=ApprovalType.PART_CAO).id
        inspector = Person.objects.get(full_name="Chris Moore").id
        for line, outcome, kind in (
            ("LEGACY-EVIDENCED", "Accepted into Stores", "CAA Form 1"),
            ("LEGACY-UNIT", "Accepted into Stores", "CAA Form 1"),
            ("LEGACY-IDENTITY", "Accepted into Stores", "CAA Form 1"),
            ("LEGACY-DESTINATION", "Accepted into Stores", "CAA Form 1"),
            ("LEGACY-HELD", "Quarantined", ""),
            ("LEGACY-RETURN", "Returned to Supplier", ""),
        ):
            arrival = old_receipt.objects.create(
                organisation_id=sample.ours.id,
                item=f"Synthetic {line}",
                received_on=ARRIVED,
                classification="Serviceable Component",
                source="Synthetic Supplier",
                item_reference="Free-text part and serial",
                quantity=1,
                delivery_reference=line,
            )
            for check in CheckKind:
                old_check.objects.create(
                    organisation_id=sample.ours.id,
                    receipt_id=arrival.id,
                    kind=check,
                    outcome="Not Applicable" if check == CheckKind.SHELF else "Pass",
                    evidence="Original evidence",
                    checked_on=ARRIVED,
                )
            made[line] = old_decision.objects.create(
                organisation_id=sample.ours.id,
                receipt_id=arrival.id,
                approval_id=approval,
                inspector_id=inspector,
                inspector_authority="Original RI-6",
                inspected_on=ARRIVED,
                disposition_on=ARRIVED,
                outcome=outcome,
                destination="[Free-Text Bay]",
                evidence="Original decision",
                document_kind=kind,
                document_reference="Original release folder" if kind else "",
            ).id
    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        MigrationExecutor(connection).migrate(latest)
    with working_for(sample.ours.id, sample.lucy.id):
        actor = _lucy(sample)
        bay = location(sample.ours, "Synthetic Mapped Bay")
        cage = location(sample.ours, "Synthetic Mapped Cage", LocationKind.QUARANTINE)
        decisions = {line: ReceivingDisposition.objects.get(pk=pk) for line, pk in made.items()}
        assert StockEntry.objects.filter(disposition__in=decisions.values()).count() == 4
        resolve(decisions["LEGACY-EVIDENCED"], actor, bay, serial_number="SN-L1", batch_number="")
        resolve(decisions["LEGACY-IDENTITY"], actor, bay, part_number="", batch_number="")
        resolve(decisions["LEGACY-DESTINATION"], actor, None, batch_number="LOT-L")
        resolve(decisions["LEGACY-HELD"], actor, cage, serial_number="SN-L5", batch_number="")
        first, _ = stores.reconcile(
            sample.ours, actor=actor, authority="Synthetic Reconciliation R-1", posted_on=TODAY
        )
        second, still = stores.reconcile(
            sample.ours, actor=actor, authority="Synthetic Reconciliation R-1", posted_on=TODAY
        )
        assert {lot.disposition.receipt.delivery_reference for lot in first} == {
            "LEGACY-EVIDENCED",
            "LEGACY-HELD",
        }
        assert second == []
        assert {d.receipt.delivery_reference for d in still} == {
            "LEGACY-UNIT",
            "LEGACY-IDENTITY",
            "LEGACY-DESTINATION",
        }
        assert any("Unit" in one for one in still[decisions["LEGACY-UNIT"]])
        assert any("Location" in one for one in still[decisions["LEGACY-DESTINATION"]])
        lot = StockPosting.objects.get(disposition=decisions["LEGACY-EVIDENCED"])
        assert (lot.physical_on, lot.posted_on) == (ARRIVED, TODAY)
        assert lot.disposition.inspector_authority == "Original RI-6"
        assert lot.disposition.destination == "[Free-Text Bay]"
        assert StockPosting.objects.count() == 2
        assert not StockPosting.objects.filter(disposition=decisions["LEGACY-RETURN"]).exists()
        Person.objects.filter(pk=actor.pk).update(full_name="Renamed Later")
        lot.refresh_from_db()
        assert lot.actor_name != "Renamed Later"


def test_s07_unsubstantiated_legacy_acceptance_stays_blocked(ours: Sample) -> None:
    """A legacy acceptance without structured evidence goes back to Goods In."""
    actor = _lucy(ours)
    bay = location(ours.ours, "Synthetic Bay G")
    decision = dispose(receipt(ours.ours, "S07-BLANK"))
    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("ALTER TABLE logistics_receivingdisposition DISABLE TRIGGER USER")
        cursor.execute(
            "UPDATE logistics_receivingdisposition SET document_kind = '' WHERE id = %s",
            [decision.pk],
        )
        cursor.execute("ALTER TABLE logistics_receivingdisposition ENABLE TRIGGER USER")
    decision.refresh_from_db()
    resolve(decision, actor, bay, serial_number="SN-B", batch_number="")
    reasons = stores.posting_blockers(decision, stores.latest_resolution(decision))
    assert reasons == [
        "Acceptance Evidence Not Substantiated: Needs a Fresh Linked Goods In Assessment"
    ]
    with pytest.raises(RefusedError, match="Fresh Linked Goods In"):
        stores.post(decision, actor=actor, authority="ST-1", posted_on=TODAY)


# S08 Permission rules


def test_s08_ui_and_server_permissions_agree(ours: Sample) -> None:
    actor = _lucy(ours)
    bay = location(ours.ours, "Synthetic Bay H")
    decision = dispose(receipt(ours.ours, "S08-LINE", quantity=3))
    entry = StockEntry.objects.get(disposition=decision)
    reader, planner, manager = (signed_in(user) for user in (ours.reader, ours.planner, ours.lucy))
    page = get(reader, f"/stores/{entry.pk}/").content
    assert b"Resolve for Stock" not in page
    # The role permits Stores work. Without a dated appointment there is no control,
    # and a direct request is refused with nothing recorded (REQ-358).
    assert b"Resolve for Stock" not in get(planner, f"/stores/{entry.pk}/").content
    values = {
        "unit": "Each",
        "part_number": "PN-8",
        "batch_number": "LOT-8",
        "location": str(bay.pk),
        "shelf_life_basis": "Not Applicable",
        "evidence": "Original release reviewed",
        "evidence_on": "2026-11-28",
        "authority": "Synthetic ST-8",
    }
    resolve_url = f"/stores/dispositions/{decision.pk}/resolve/"
    post_url = f"/stores/dispositions/{decision.pk}/post/"
    assert post(reader, resolve_url, **values).status_code == 403
    assert post(planner, "/stores/locations/add/", name="X", kind="Quarantine").status_code == 403
    refused = post(planner, resolve_url, **values)
    assert refused.status_code == 200
    assert b"Needs a Current Stores Appointment" in refused.content
    assert not StockResolution.objects.filter(disposition=decision).exists()
    appoint_for_stores(Person.objects.get(user=ours.planner))
    assert b"Resolve for Stock" in get(planner, f"/stores/{entry.pk}/").content
    assert post(planner, resolve_url, **values).status_code == 302
    assert post(reader, post_url, posted_on="2026-11-28", authority="ST").status_code == 403
    assert not StockPosting.objects.filter(disposition=decision).exists()
    assert post(planner, post_url, posted_on="2026-11-28", authority="ST").status_code == 302
    assert post(planner, post_url, posted_on="2026-11-28", authority="ST").status_code == 302
    lot = StockPosting.objects.get(disposition=decision)
    assert lot.actor == Person.objects.get(user=ours.planner)
    stranger = signed_in(ours.stranger)
    assert post(stranger, post_url, posted_on="2026-11-28", authority="ST").status_code == 404
    assert post(stranger, f"/stores/lots/{lot.pk}/count/").status_code == 404
    assert (
        post(
            manager,
            "/stores/locations/add/",
            name="Synthetic Cage H",
            kind="Quarantine",
            holds_components="on",
        ).status_code
        == 200
    )
    assert not StoreLocation.objects.filter(name="Synthetic Cage H").exists()
    left = Person.objects.get(user=ours.planner)
    Person.objects.filter(pk=left.pk).update(left_on=date(2026, 11, 20))
    left.refresh_from_db()
    with pytest.raises(RefusedError, match="Not Active"):
        stores.count(
            lot, location=bay, counted_quantity="3", counted_on=TODAY, counter=left, evidence="C"
        )
    assert actor.organisation_id == ours.ours.id


def test_s08_each_stores_action_needs_the_persons_own_dated_appointment(ours: Sample) -> None:
    """REQ-358. The service and PostgreSQL refuse posting, moves, counts and adjustments
    without a current appointment for the signed-in person, duty and date."""
    lucy = _lucy(ours)
    bay, shelf = location(ours.ours, "Synthetic Bay J"), location(ours.ours, "Synthetic Shelf J")
    decision = dispose(receipt(ours.ours, "APPOINT-LINE", quantity=4))
    with pytest.raises(RefusedError, match="Needs a Current Stores Appointment"):
        stores.resolve(
            decision,
            actor=lucy,
            authority="ST",
            unit=StockUnit.EACH,
            part_number="PN-J",
            batch_number="LOT-J",
            shelf_life_basis="Not Applicable",
            location=bay,
            evidence="Original release reviewed",
            evidence_on=TODAY,
        )
    # Post and Count only: moving and adjusting stay refused.
    appoint_for_stores(lucy, StockDuty.POST, StockDuty.COUNT)
    stores.resolve(
        decision,
        actor=lucy,
        authority="ST",
        unit=StockUnit.EACH,
        part_number="PN-J",
        batch_number="LOT-J",
        shelf_life_basis="Not Applicable",
        location=bay,
        evidence="Original release reviewed",
        evidence_on=TODAY,
    )
    lot = stores.post(decision, actor=lucy, authority="ST", posted_on=TODAY)
    moved: Moved = {"moved_on": TODAY, "actor": lucy, "authority": "ST", "evidence": "Note"}
    with pytest.raises(RefusedError, match="Move Stock Between Locations"):
        stores.move(lot, from_location=bay, to_location=shelf, quantity="1", **moved)
    tally = stores.count(
        lot, location=bay, counted_quantity="3", counted_on=TODAY, counter=lucy, evidence="C"
    )
    with pytest.raises(RefusedError, match="Adjust Stock From a Count"):
        stores.adjust(tally, actor=lucy, authority="ST", evidence="A", moved_on=TODAY)
    # PostgreSQL refuses the same move written directly, bypassing the service.
    with pytest.raises(DatabaseError, match="current Stores appointment"), transaction.atomic():
        StockMovement.objects.create(
            organisation_id=lot.organisation_id,
            lot=lot,
            kind=MovementKind.TRANSFER,
            from_location=bay,
            to_location=shelf,
            quantity=Decimal(1),
            moved_on=TODAY,
            actor=lucy,
            actor_name=lucy.full_name,
            authority="Direct",
            evidence="Direct",
        )
    # Another person's appointment does not authorise the signed-in user.
    planner = Person.objects.get(user=ours.planner)
    appoint_for_stores(planner, StockDuty.ADJUST)
    with pytest.raises(DatabaseError, match="current Stores appointment"), transaction.atomic():
        StockMovement.objects.create(
            organisation_id=lot.organisation_id,
            lot=lot,
            kind=MovementKind.ADJUSTMENT,
            from_location=bay,
            quantity=Decimal(1),
            moved_on=TODAY,
            count=tally,
            actor=planner,
            actor_name=planner.full_name,
            authority="Direct",
            evidence="Direct",
        )
    # The last day authorises; the day after and a withdrawal do not.
    grant = StockAppointment.objects.get(person=lucy, action=StockDuty.COUNT)
    assert stock_appointments.current(ours.lucy, StockDuty.COUNT, grant.ends_on) == grant
    assert (
        stock_appointments.current(ours.lucy, StockDuty.COUNT, grant.ends_on + timedelta(1)) is None
    )
    StockAppointmentWithdrawal.objects.create(
        organisation_id=lot.organisation_id,
        appointment=grant,
        withdrawn_on=TODAY,
        evidence="Synthetic withdrawal",
    )
    with pytest.raises(RefusedError, match="Count Stock"):
        stores.count(
            lot, location=bay, counted_quantity="4", counted_on=TODAY, counter=lucy, evidence="C"
        )
    assert stores.balance(lot, bay) == Decimal(4)
    assert StockMovement.objects.filter(lot=lot).count() == 1


# S09 Ledger invariants


@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@given(st.lists(st.tuples(st.integers(0, 2), st.integers(0, 2), st.integers(1, 30)), max_size=8))
def test_s09_generated_movements_conserve_and_never_go_negative(
    sample: Sample, steps: list[tuple[int, int, int]]
) -> None:
    with working_for(sample.ours.id, sample.lucy.id), transaction.atomic():
        actor = _lucy(sample)
        places = [
            StoreLocation.objects.filter(name=f"Synthetic Gen {index}").first()
            or location(sample.ours, f"Synthetic Gen {index}")
            for index in range(3)
        ]
        line = f"S09-{StockPosting.objects.count()}-{len(steps)}"
        lot = posted(dispose(receipt(sample.ours, line, quantity=20)), actor, places[0])
        model = [Decimal(20), Decimal(0), Decimal(0)]
        for source, target, amount in steps:
            values = Moved(moved_on=TODAY, actor=actor, authority="ST", evidence="Gen")
            try:
                stores.move(
                    lot,
                    from_location=places[source],
                    to_location=places[target],
                    quantity=str(amount),
                    **values,
                )
            except RefusedError:
                assert source == target or model[source] < amount
            else:
                model[source] -= amount
                model[target] += amount
        actual = [on_hand(lot, place) for place in places]
        assert actual == model
        assert all(value >= 0 for value in actual)
        assert sum(actual) == 20
        transaction.set_rollback(True)


def test_s09_the_database_refuses_an_overspend_that_bypasses_the_service(ours: Sample) -> None:
    actor = _lucy(ours)
    bay, shelf = location(ours.ours, "Synthetic Bay I"), location(ours.ours, "Synthetic Shelf I")
    lot = posted(dispose(receipt(ours.ours, "S09-DIRECT", quantity=2)), actor, bay)
    direct = {
        "organisation": ours.ours,
        "lot": lot,
        "moved_on": TODAY,
        "actor": actor,
        "actor_name": actor.full_name,
        "authority": "Direct",
        "evidence": "Direct",
    }
    for values, reason in (
        ({"kind": "Transfer", "from_location": bay, "to_location": shelf, "quantity": 3}, "hold"),
        ({"kind": "Intake", "to_location": bay, "quantity": 2}, "opens a lot"),
        (
            {"kind": "Transfer", "from_location": bay, "to_location": shelf, "quantity": 0},
            "does not suit",
        ),
    ):
        with pytest.raises(IntegrityError, match=reason), transaction.atomic():
            StockMovement.objects.create(**direct, **values)
    with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
        StockMovement.objects.filter(lot=lot).update(quantity=Decimal(9))
    assert on_hand(lot, bay) == 2


def test_the_sample_posts_oil_and_bolts_once_and_leaves_rx_002_awaiting(sample: Sample) -> None:
    """REQ-358. The test site can show a move of oil and an authorised count adjustment."""
    from airworthiness_plus.sample import goods_in
    from airworthiness_plus.sample import stores as stores_sample

    goods_in.add(sample.ours, sample.lucy)
    assert stores_sample.add(sample.ours, sample.administrator) == 2
    assert stores_sample.add(sample.ours, sample.administrator) == 0
    with working_for(sample.ours.id, sample.lucy.id):
        oil = StockPosting.objects.get(disposition__receipt__delivery_reference="RX-006")
        bolts = StockPosting.objects.get(disposition__receipt__delivery_reference="RX-007")
        (oil_line,) = stores.positions([oil], TODAY, 30)
        assert (oil.unit, oil_line.on_hand, oil_line.available) == (
            StockUnit.LITRE,
            Decimal(24),
            Decimal(24),
        )
        assert oil_line.location.name == "Bay C, Oils and Materials"
        (tally,) = bolts.counts.all()
        assert (tally.counted_quantity, tally.ledger_quantity) == (Decimal(46), Decimal(50))
        assert not StockMovement.objects.filter(count=tally).exists()
        rx002 = ReceivingDisposition.objects.get(receipt__delivery_reference="RX-002")
        assert not StockPosting.objects.filter(disposition=rx002).exists()
        keeper = Person.objects.get(user=sample.lucy)
        assert set(
            StockAppointment.objects.filter(person=keeper).values_list("action", flat=True)
        ) == set(StockDuty.values)
