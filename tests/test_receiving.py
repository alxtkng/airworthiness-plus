"""Goods In receiving and disposition against the primary sample organisation."""

import pytest

from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
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
    """REQ-344 to REQ-346. Pending checks prevent a receipt entering stores."""
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
            )
        )
        assert audit.count() == 8
        assert set(audit.values_list("actor_id", flat=True)) == {sample.planner.id}


def test_receiving_is_tenant_scoped_and_reserved_to_recording_roles(sample: Sample) -> None:
    """REQ-347. Rights and tenant isolation hold even behind a direct URL."""
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
    """REQ-346. A second attempted movement cannot rewrite the quarantine."""
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
    evidence.update(outcome="Quarantined", destination="Secure Quarantine Bay Q2")
    assert post(recorder, detail + "dispose/", **evidence).status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        assert Receipt.objects.count() == 1
        decision = ReceivingDisposition.objects.get()
        assert decision.outcome == "Quarantined"
        assert decision.destination == "Secure Quarantine Bay Q2"


def test_database_blocks_invalid_disposition_and_preserves_the_record(sample: Sample) -> None:
    """REQ-346, REQ-347. The application database role cannot bypass inspection."""
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
        kept = ReceivingDisposition.objects.create(**decision, outcome=Destination.QUARANTINE)
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
    """REQ-218 and REQ-344 to REQ-346. Canvas examples are traceable and added only once."""
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
