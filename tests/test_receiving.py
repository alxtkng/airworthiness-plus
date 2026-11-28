"""Goods In receiving and disposition against the primary sample organisation."""

import pytest

from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics.models import StockEntry
from airworthiness_plus.people.models import Person
from tests.support import Sample, get, post, signed_in

pytestmark = pytest.mark.django_db

RECEIPT = {
    "item": "Stabilator Trim Cable Assembly",
    "received_on": "2026-11-16",
    "classification": "Serviceable Component",
    "source": "Owner Supplied",
    "item_reference": "PN-713, SN-863",
    "quantity": "1",
    "release_document": "Release evidence A-26",
    "intended_use": "G-DGHI, WP-2026-046",
    "delivery_reference": "DELIVERY-26",
}

CHECKS = (
    "Supplier",
    "Release Document",
    "Part Number and Modification Status",
    "Condition and Packaging",
    "Shelf Life",
    "Suspected Unapproved Part Checks",
)


def test_receiving_retains_each_check_and_decision_and_requires_evidence(sample: Sample) -> None:
    """REQ-353 to REQ-355. Pending checks prevent a receipt entering stores."""
    recorder = signed_in(sample.planner)
    created = post(recorder, "/goods-in/receive/", **RECEIPT)
    assert created.status_code == 302
    receipt = created["Location"]
    page = get(recorder, receipt)
    assert b"Awaiting Inspection" in page.content
    with working_for(sample.ours.id, sample.lucy.id):
        inspector = Person.objects.get(full_name="Chris Moore")
    decision = {
        "approval": "Part-CAO",
        "inspector": str(inspector.pk),
        "inspector_authority": "Receiving Inspection Authorisation RI-6",
        "inspected_on": "2026-11-16",
        "disposition_on": "2026-11-17",
        "outcome": "Accepted into Stores",
        "destination": "Store Bay B",
        "evidence": "Receiving inspection record RI-26",
        "document_kind": "CAA Form 1",
        "document_reference": "Checked release register RI-26 / Form 1",
    }
    refused = post(recorder, receipt + "dispose/", **decision)
    assert refused.status_code == 200
    assert b"All Applicable Checks Must Pass" in refused.content
    for check in CHECKS:
        outcome = "Not Applicable" if check == "Shelf Life" else "Pass"
        response = post(
            recorder,
            receipt + "check/",
            check=check,
            outcome=outcome,
            checked_on="2026-11-16",
            evidence=f"Recorded source for {check}",
        )
        assert response.status_code == 302
    done = post(recorder, receipt + "dispose/", **decision)
    assert done.status_code == 302
    read = get(signed_in(sample.reader), receipt)
    assert b"Store Bay B" in read.content
    assert b"Receiving inspection record RI-26" in read.content
    assert b"Receiving Inspection Authorisation RI-6" in read.content
    assert b"Recorded source for Shelf Life" in read.content
    assert b"Chris Moore" in read.content
    assert b"UK.CAO.[Number]" in read.content
    assert b"Accepted into Stores" in get(recorder, "/goods-in/").content
    assert b"View Stores Entry" in read.content
    with working_for(sample.ours.id, sample.lucy.id):
        entry = StockEntry.objects.get()
        assert f"/goods-in/{entry.disposition.receipt_id}/" == receipt
    stock_url = f"/stores/{entry.pk}/"
    stock = get(signed_in(sample.reader), stock_url)
    for value in (b"Store Bay B", b"Checked release register", b"PN-713, SN-863", b"DELIVERY-26"):
        assert value in stock.content
    other = signed_in(sample.stranger)
    assert get(other, stock_url).status_code in {403, 404}
    assert b"DELIVERY-26" not in get(other, "/stores/").content
    assert post(recorder, receipt + "dispose/", **decision).status_code != 302
    assert (
        post(
            recorder,
            receipt + "check/",
            check=CHECKS[0],
            outcome="Pass",
            checked_on="2026-11-17",
            evidence="Later check",
        ).status_code
        != 302
    )
    with working_for(sample.ours.id, sample.lucy.id):
        audit = Event.objects.filter(
            record_type__in=(
                "logistics_receipt",
                "logistics_receivingcheck",
                "logistics_receivingdisposition",
                "logistics_stockentry",
            )
        )
        assert audit.count() == 9
        assert StockEntry.objects.count() == 1
        stock_event = audit.get(record_type="logistics_stockentry", record_id=entry.id)
        assert stock_event.actor_id is None
        assert stock_event.actor_name.startswith("Database Role ")
        assert str(entry.disposition_id) in (stock_event.after_json or "")
        decisions = audit.exclude(pk=stock_event.pk)
        assert set(decisions.values_list("actor_id", flat=True)) == {sample.planner.id}


def test_receiving_is_tenant_scoped_and_reserved_to_recording_roles(sample: Sample) -> None:
    """REQ-356. Rights and tenant isolation hold even behind a direct URL."""
    reader = signed_in(sample.reader)
    assert post(reader, "/goods-in/receive/", **RECEIPT).status_code == 403
    created = post(signed_in(sample.lucy), "/goods-in/receive/", **RECEIPT)
    assert created.status_code == 302
    detail = created["Location"]
    assert get(reader, detail).status_code == 200
    assert b"Record a Check" not in get(reader, detail).content
    assert post(reader, detail + "check/").status_code == 403
    assert post(reader, detail + "dispose/").status_code == 403
    assert get(signed_in(sample.stranger), detail).status_code in {403, 404}


def test_a_failed_suspect_part_check_requires_quarantine(sample: Sample) -> None:
    """REQ-355. A second attempted movement cannot rewrite the quarantine."""
    from airworthiness_plus.logistics.models import Receipt, ReceivingDisposition

    recorder = signed_in(sample.planner)
    made = post(recorder, "/goods-in/receive/", **{**RECEIPT, "item": "Owner Supplied Alternator"})
    assert made.status_code == 302
    detail = made["Location"]
    assert (
        post(
            recorder,
            detail + "check/",
            check=CHECKS[-1],
            outcome="Fail",
            checked_on="2026-11-16",
            evidence="The CAA Form 1 and the item have different serial numbers",
        ).status_code
        == 302
    )
    with working_for(sample.ours.id, sample.planner.id):
        inspector = Person.objects.get(full_name="Chris Moore")
    evidence = {
        "approval": "Part-CAO",
        "inspector": str(inspector.pk),
        "inspector_authority": "Receiving Inspection Authorisation RI-6",
        "inspected_on": "2026-11-16",
        "disposition_on": "2026-11-16",
        "outcome": "Returned to Supplier",
        "destination": "Goods Out",
        "evidence": "Decided after finding a serial number mismatch",
    }
    assert b"Must Go to Quarantine" in post(recorder, detail + "dispose/", **evidence).content
    evidence.update(
        outcome="Quarantined",
        destination="Secure Quarantine Bay Q2",
        document_kind="CAA Form 1",
        document_reference="Retained mismatched release",
    )
    assert post(recorder, detail + "dispose/", **evidence).status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        assert Receipt.objects.count() == 1
        decision = ReceivingDisposition.objects.get()
        assert decision.outcome == "Quarantined"
        assert decision.destination == "Secure Quarantine Bay Q2"
        assert decision.document_reference == "Retained mismatched release"
        assert decision.receipt.item_reference == RECEIPT["item_reference"]
        assert not StockEntry.objects.exists()


def test_database_blocks_invalid_disposition_and_preserves_the_record(sample: Sample) -> None:
    """REQ-355, REQ-356. The application database role cannot bypass inspection."""
    from datetime import date

    from django.db import DatabaseError, IntegrityError, transaction

    from airworthiness_plus.logistics.models import (
        CheckKind,
        Destination,
        Receipt,
        ReceivingCheck,
        ReceivingDisposition,
    )
    from airworthiness_plus.organisations.models import Approval, ApprovalType

    with working_for(sample.ours.id, sample.lucy.id):
        assert post(signed_in(sample.lucy), "/goods-in/receive/", **RECEIPT).status_code == 302
        receipt = Receipt.objects.get()
        inspector = Person.objects.get(full_name="Chris Moore")
        term = Approval.objects.get(approval=ApprovalType.PART_CAO)
        decision = {
            "organisation": sample.ours,
            "receipt": receipt,
            "approval": term,
            "approval_reference": "Supplied Reference",
            "inspector": inspector,
            "inspector_name": "Supplied Name",
            "inspector_authority": "RI-06",
            "inspected_on": date(2026, 11, 16),
            "disposition_on": date(2026, 11, 17),
            "destination": "Segregated Bay",
            "evidence": "Awaiting acceptable evidence",
        }
        with pytest.raises(IntegrityError, match="does not allow acceptance"), transaction.atomic():
            ReceivingDisposition.objects.create(**decision, outcome=Destination.STORES)
        with pytest.raises(IntegrityError, match="needs dated"), transaction.atomic():
            ReceivingCheck.objects.create(
                organisation=sample.ours,
                receipt=receipt,
                kind=CheckKind.DOCUMENT,
                outcome="Pass",
                checked_on=date(2026, 11, 16),
                evidence="   ",
            )
        for kind in CheckKind:
            ReceivingCheck.objects.create(
                organisation=sample.ours,
                receipt=receipt,
                kind=kind,
                outcome="Pass",
                checked_on=date(2026, 11, 16),
                evidence="Synthetic check evidence",
            )
        with pytest.raises(IntegrityError, match="traceable evidence"), transaction.atomic():
            ReceivingDisposition.objects.create(**decision, outcome=Destination.STORES)
        kept = ReceivingDisposition.objects.create(**decision, outcome=Destination.QUARANTINE)
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            StockEntry.objects.create(organisation=sample.ours, disposition=kept)
        kept.refresh_from_db()
        assert kept.inspector_name == "Chris Moore"
        assert kept.approval_reference == term.reference
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            ReceivingDisposition.objects.filter(pk=kept.pk).update(outcome=Destination.STORES)
        with pytest.raises(IntegrityError, match="closed by the final"), transaction.atomic():
            ReceivingCheck.objects.create(
                organisation=sample.ours,
                receipt=receipt,
                kind=CheckKind.DOCUMENT,
                outcome="Pass",
                checked_on=date(2026, 11, 16),
                evidence="Evidence checked",
            )
    with working_for(sample.other.id, sample.stranger.id):
        assert not Receipt.objects.filter(pk=receipt.pk).exists()


def test_goods_in_sample_records_pending_returned_accepted_and_quarantined(
    sample: Sample,
) -> None:
    """REQ-218 and REQ-353 to REQ-355. Canvas examples are traceable and added only once."""
    from airworthiness_plus.logistics.models import Receipt
    from airworthiness_plus.sample import goods_in

    assert goods_in.add(sample.ours, sample.administrator) == 5
    assert goods_in.add(sample.ours, sample.administrator) == 0
    body = get(signed_in(sample.reader), "/goods-in/").content
    for text in (b"Awaiting Inspection", b"Accepted into Stores", b"Returned", b"Quarantined"):
        assert text in body
    with working_for(sample.ours.id, sample.lucy.id):
        battery = Receipt.objects.get(delivery_reference="RX-001")
        assert battery.checks.count() == 2
        oil = Receipt.objects.get(delivery_reference="RX-005")
        assert oil.disposition.inspected_on.isoformat() == "2026-10-28"
        assert oil.disposition.disposition_on.isoformat() == "2026-10-29"
        assert oil.item_reference == "[Oil Batch Number]"
        assert oil.disposition.evidence.startswith("Batch Without Conformity Evidence")
        assert StockEntry.objects.get().disposition.receipt.delivery_reference == "RX-002"


@pytest.mark.parametrize("received_class", ["Unserviceable Component", "Unsalvageable Component"])
def test_an_unusable_receipt_must_stay_in_quarantine(sample: Sample, received_class: str) -> None:
    from datetime import date

    from django.db import IntegrityError, transaction

    from airworthiness_plus.logistics.models import Destination, Receipt, ReceivingDisposition
    from airworthiness_plus.organisations.models import Approval, ApprovalType

    recorder = signed_in(sample.planner)
    made = post(
        recorder,
        "/goods-in/receive/",
        **{**RECEIPT, "classification": received_class},
    )
    assert made.status_code == 302
    detail = made["Location"]
    with working_for(sample.ours.id, sample.planner.id):
        inspector = Person.objects.get(full_name="Chris Moore")
        arrival = Receipt.objects.get()
        term = Approval.objects.get(approval=ApprovalType.PART_CAO)
        with pytest.raises(IntegrityError, match="must go to quarantine"), transaction.atomic():
            ReceivingDisposition.objects.create(
                organisation=sample.ours,
                receipt=arrival,
                approval=term,
                inspector=inspector,
                inspector_authority="RI-6",
                inspected_on=date(2026, 11, 16),
                disposition_on=date(2026, 11, 17),
                outcome=Destination.RETURN,
                destination="Supplier",
                evidence="Damage recorded on inspection",
            )
    args = {
        "approval": "Part-CAO",
        "inspector": str(inspector.pk),
        "inspector_authority": "RI-6",
        "inspected_on": "2026-11-16",
        "disposition_on": "2026-11-17",
        "outcome": "Returned to Supplier",
        "destination": "Supplier",
        "evidence": "Damage recorded on inspection",
    }
    assert b"Must Go to Quarantine" in post(recorder, detail + "dispose/", **args).content
    args.update(outcome="Quarantined", destination="Secured quarantine")
    assert post(recorder, detail + "dispose/", **args).status_code == 302


def test_expired_shelf_life_and_a_later_failed_check_stop_acceptance(sample: Sample) -> None:
    recorder = signed_in(sample.planner)
    made = post(recorder, "/goods-in/receive/", **{**RECEIPT, "shelf_life_to": "2026-11-17"})
    assert made.status_code == 302
    detail = made["Location"]
    for check in CHECKS:
        assert (
            post(
                recorder,
                detail + "check/",
                check=check,
                outcome="Pass",
                checked_on="2026-11-16",
                evidence=f"Initial evidence for {check}",
            ).status_code
            == 302
        )
    with working_for(sample.ours.id, sample.planner.id):
        inspector = Person.objects.get(full_name="Chris Moore")
    args = {
        "approval": "Part-CAO",
        "inspector": str(inspector.pk),
        "inspector_authority": "RI-6",
        "inspected_on": "2026-11-17",
        "disposition_on": "2026-11-18",
        "outcome": "Accepted into Stores",
        "destination": "Store",
        "evidence": "Intake inspection evidence",
        "document_kind": "CAA Form 1",
        "document_reference": "Synthetic release",
    }
    assert b"Shelf Life Has Passed" in post(recorder, detail + "dispose/", **args).content
    args["disposition_on"] = "2026-11-17"
    assert (
        post(
            recorder,
            detail + "check/",
            check=CHECKS[2],
            outcome="Fail",
            checked_on="2026-11-17",
            evidence="Later identification check no longer agrees",
        ).status_code
        == 302
    )
    assert b"All Applicable Checks Must Pass" in post(recorder, detail + "dispose/", **args).content
    assert (
        b"Initial evidence for Part Number and Modification Status" in get(recorder, detail).content
    )
    assert (
        post(
            recorder,
            detail + "check/",
            check=CHECKS[2],
            outcome="Pass",
            checked_on="2026-11-17",
            evidence="Correction checked against traced manufacturer evidence",
        ).status_code
        == 302
    )
    assert post(recorder, detail + "dispose/", **args).status_code == 302


@pytest.mark.parametrize(
    ("classification", "kind", "basis", "manufacturer", "error"),
    [
        ("Serviceable Component", "Conformity Evidence", "SYN-1", "", "Choose the Release"),
        ("Serviceable Component", "Equivalent Release", "", "", "Give the Applicable Basis"),
        ("Serviceable Component", "Equivalent Release", "Sample bilateral basis", "", ""),
        ("Serviceable Component", "Permitted Exception", "Sample documented exception", "", ""),
        ("Standard Part", "CAA Form 1", "SYN-1", "", "Give the Conformity Evidence"),
        ("Standard Part", "Conformity Evidence", "", "", "Give the Conformity Evidence"),
        ("Standard Part", "Conformity Evidence", "SYN-1", "", ""),
        ("Material", "Conformity Evidence", "SYN-2", "", "Give the Manufacturing Source"),
        ("Material", "Conformity Evidence", "SYN-2", "Sample Factory", ""),
    ],
)
def test_stores_evidence_depends_on_the_received_class(
    sample: Sample, classification: str, kind: str, basis: str, manufacturer: str, error: str
) -> None:
    """REQ-355 and REQ-357. Successful and refused cases use the real form and database."""
    recorder = signed_in(sample.planner)
    response = post(recorder, "/goods-in/receive/", **{**RECEIPT, "classification": classification})
    assert response.status_code == 302
    detail = response["Location"]
    for check in CHECKS:
        result = post(
            recorder,
            detail + "check/",
            check=check,
            outcome="Pass",
            checked_on="2026-11-16",
            evidence=f"Synthetic evidence for {check}",
        )
        assert result.status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        inspector = Person.objects.get(full_name="Chris Moore")
    decision = {
        "approval": "Part-CAO",
        "inspector": str(inspector.pk),
        "inspector_authority": "Sample RI-6",
        "inspected_on": "2026-11-16",
        "disposition_on": "2026-11-17",
        "outcome": "Accepted into Stores",
        "destination": "Sample Bay",
        "evidence": "Synthetic inspection record",
        "document_kind": kind,
        "document_reference": "Synthetic evidence register",
        "evidence_basis": basis,
        "manufacturing_source": manufacturer,
        "material_supplier_source": "Supplier on Sample Statement",
    }
    refused = post(recorder, detail + "dispose/", **{**decision, "document_reference": ""})
    assert b"Give a Traceable Evidence Reference" in refused.content
    if classification == "Material" and manufacturer:
        missing_supplier = post(
            recorder, detail + "dispose/", **{**decision, "material_supplier_source": ""}
        )
        assert b"Give the Manufacturing Source and Supplier Source" in missing_supplier.content
    result = post(recorder, detail + "dispose/", **decision)
    with working_for(sample.ours.id, sample.planner.id):
        if error:
            assert error.encode() in result.content
            assert not StockEntry.objects.exists()
        else:
            assert result.status_code == 302
            disposition = StockEntry.objects.get().disposition
            assert disposition.document_kind == kind
            assert disposition.evidence_basis == basis
            assert disposition.manufacturing_source == manufacturer


def test_stock_migration_keeps_prior_acceptance_and_its_original_evidence(sample: Sample) -> None:
    """REQ-357. Upgrade a receipt accepted before structured evidence was available."""
    from datetime import date

    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    from airworthiness_plus.exports.build import build
    from airworthiness_plus.exports.verify import verify
    from airworthiness_plus.organisations.models import Approval, ApprovalType
    from tests.conftest import as_owner

    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old_apps = executor.migrate([("logistics", "0004_receiving_record_rules")]).apps
    old_receipt = old_apps.get_model("logistics", "Receipt")
    old_check = old_apps.get_model("logistics", "ReceivingCheck")
    old_decision = old_apps.get_model("logistics", "ReceivingDisposition")
    day = date(2026, 11, 16)
    with working_for(sample.ours.id, sample.planner.id):
        arrival = old_receipt.objects.create(
            organisation_id=sample.ours.id,
            item="Synthetic Test Assembly",
            received_on=day,
            classification="Serviceable Component",
            source="Synthetic Supplier",
            item_reference="Test Serial 262",
            quantity=1,
            delivery_reference="MIGRATION-262",
            release_document="Original Sample Release Reference",
        )
        for check in CHECKS:
            old_check.objects.create(
                organisation_id=sample.ours.id,
                receipt_id=arrival.id,
                kind=check,
                outcome="Pass",
                evidence="Sample evidence retained by the original procedure",
                checked_on=day,
            )
        decision = old_decision.objects.create(
            organisation_id=sample.ours.id,
            receipt_id=arrival.id,
            approval_id=Approval.objects.get(approval=ApprovalType.PART_CAO).id,
            inspector_id=Person.objects.get(full_name="Chris Moore").id,
            inspector_authority="Sample RI-6",
            inspected_on=day,
            disposition_on=day,
            outcome="Accepted into Stores",
            destination="Sample Bay",
            evidence="Original inspection decision",
        )
    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        MigrationExecutor(connection).migrate(latest)
    with working_for(sample.ours.id, sample.planner.id):
        entry = StockEntry.objects.get()
        assert entry.disposition_id == decision.id
        assert entry.disposition.receipt.release_document == "Original Sample Release Reference"
        assert entry.disposition.document_reference == ""
        assert (
            Event.objects.filter(
                record_type="logistics_receivingdisposition", record_id=decision.id
            ).count()
            == 1
        )
        assert not verify(build(sample.ours, by=sample.planner).content).problems
