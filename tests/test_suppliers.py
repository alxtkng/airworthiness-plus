"""Phase 4 Suppliers, using the sample organisation and its normal record pages."""

from datetime import date, timedelta

import pytest

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_plus.sample import suppliers
from tests.support import Sample, get, post, signed_in

pytestmark = pytest.mark.django_db

SAMPLE = {
    "name": "Test Propeller Organisation",
    "approval": ApprovalType.PART_CAO,
    "evaluated_on": "2026-11-18",
    "supplies": "Propeller Overhaul and Repair",
    "release_documents": "CAA Form 1",
    "status": "Approved",
    "next_evaluation_on": "2026-11-30",
    "evidence": "[Evaluation Reference]",
}


def test_supplier_evaluation_is_recorded_and_retained(sample: Sample) -> None:
    """REQ-340 to REQ-342. The register shows current evidence and keeps the original."""
    manager = signed_in(sample.lucy)
    created = post(manager, "/suppliers/evaluate/", **SAMPLE)
    assert created.status_code == 302
    address = created["Location"]
    assert address.startswith("/suppliers/")

    register = get(signed_in(sample.reader), "/suppliers/")
    assert register.status_code == 200
    assert b"Test Propeller Organisation" in register.content
    assert b"30 November 2026" in register.content
    assert b"CAA Form 1" in register.content
    assert b"Evaluate a Supplier" not in register.content

    updated = dict(SAMPLE)
    updated.pop("name")
    updated.update(status="Suspended", evidence="Batch Without Conformity", next_evaluation_on="")
    assert post(manager, address + "evaluate/", **updated).status_code == 302
    detail = get(signed_in(sample.reader), address)
    assert detail.status_code == 200
    assert b"Suspended" in detail.content and b"Batch Without Conformity" in detail.content
    assert b"[Evaluation Reference]" in detail.content
    with working_for(sample.ours.id, sample.lucy.id):
        assert Event.objects.filter(record_type="logistics_supplierevaluation").count() == 2


def test_supplier_write_and_tenant_boundaries(sample: Sample) -> None:
    """REQ-343. A hidden action cannot be called directly, and records are tenant-scoped."""
    owner = signed_in(sample.lucy)
    assert post(signed_in(sample.reader), "/suppliers/evaluate/", **SAMPLE).status_code == 403
    result = post(owner, "/suppliers/evaluate/", **SAMPLE)
    assert result.status_code == 302
    assert get(signed_in(sample.stranger), "/suppliers/").status_code == 200
    assert get(signed_in(sample.stranger), result["Location"]).status_code == 404

    foreign_approval = dict(SAMPLE, approval=ApprovalType.PART_145)
    refused = post(owner, "/suppliers/evaluate/", **foreign_approval)
    assert refused.status_code == 200
    assert b"Part-145" in refused.content
    assert b"Test Propeller Organisation" in refused.content


def test_an_earlier_evaluation_does_not_replace_the_current_evaluation(sample: Sample) -> None:
    """REQ-342. Entry order never takes priority over the recorded evaluation date."""
    manager = signed_in(sample.lucy)
    initial = post(manager, "/suppliers/evaluate/", **SAMPLE)
    assert initial.status_code == 302
    address = initial["Location"]
    old = dict(SAMPLE)
    old.pop("name")
    old.update(evaluated_on="2026-11-17", status="Suspended", next_evaluation_on="")
    assert post(manager, address + "evaluate/", **old).status_code == 302
    current = get(manager, "/suppliers/")
    assert b"Approved" in current.content
    assert b"Suspended" not in current.content


def test_supplier_dates_and_duplicate_identity_are_refused(sample: Sample) -> None:
    """REQ-340 and REQ-341. An evaluation needs a valid date and one supplier identity."""
    manager = signed_in(sample.lucy)
    missing = post(manager, "/suppliers/evaluate/", **dict(SAMPLE, next_evaluation_on=""))
    assert b"Record the Next Evaluation" in missing.content
    earlier = post(manager, "/suppliers/evaluate/", **dict(SAMPLE, next_evaluation_on="2026-11-17"))
    assert b"The Next Evaluation Must Be After" in earlier.content
    assert post(manager, "/suppliers/evaluate/", **SAMPLE).status_code == 302
    duplicate = post(manager, "/suppliers/evaluate/", **dict(SAMPLE, name=SAMPLE["name"].lower()))
    assert b"This Supplier Is Already Recorded" in duplicate.content
    with working_for(sample.ours.id, sample.lucy.id):
        assert Event.objects.filter(record_type="logistics_supplierevaluation").count() == 1


def test_each_approval_has_its_own_supplier_decision(sample: Sample) -> None:
    """REQ-340 and REQ-342. A new approval reference cannot borrow an older decision."""
    # Approval renewal is dated using the real database clock, so dates in this case
    # are relative to the same UK day used by the application.
    today = aircraft_services.today()
    first_evaluation = dict(
        SAMPLE,
        evaluated_on=(today - timedelta(days=9)).isoformat(),
        next_evaluation_on=(today + timedelta(days=3)).isoformat(),
    )
    with working_for(sample.ours.id, sample.administrator.id):
        second_approval = approvals.record(
            sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[First]"
        )
    manager = signed_in(sample.lucy)
    created = post(manager, "/suppliers/evaluate/", **first_evaluation)
    assert created.status_code == 302
    register = get(manager, "/suppliers/")
    assert b"No Current Evaluation" in register.content
    assert b"Due Soon" in register.content
    address = created["Location"]
    next_evaluation = dict(first_evaluation)
    next_evaluation.pop("name")
    next_evaluation["approval"] = ApprovalType.PART_145
    assert post(manager, address + "evaluate/", **next_evaluation).status_code == 302
    assert b"No Current Evaluation" not in get(manager, "/suppliers/").content
    with working_for(sample.ours.id, sample.administrator.id):
        approvals.end(second_approval, on=today - timedelta(days=8))
        approvals.record(sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[New]")
    assert b"No Current Evaluation" in get(manager, "/suppliers/").content
    assert b"UK.145.[First]" in get(manager, address).content
    gap_day = (today - timedelta(days=7)).isoformat()
    gap = post(manager, address + "evaluate/", **dict(next_evaluation, evaluated_on=gap_day))
    assert b"The Organisation Held No Part-145 Maintenance Approval" in gap.content
    backdated = post(
        manager,
        address + "evaluate/",
        **dict(
            next_evaluation,
            evaluated_on=(today - timedelta(days=10)).isoformat(),
            evidence="Earlier Part-145 Evaluation",
        ),
    )
    assert backdated.status_code == 302
    history = get(manager, address).content
    assert history.count(b"UK.145.[First]") == 2
    assert b"UK.145.[New]" not in history
    assert b"No Current Evaluation" in get(manager, "/suppliers/").content


def test_sample_suppliers_are_added_once(sample: Sample, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2026, 11, 27))
    assert suppliers.add(sample.ours, sample.administrator) == 5
    assert suppliers.add(sample.ours, sample.administrator) == 0
    register = get(signed_in(sample.reader), "/suppliers/")
    assert b"[Propeller Organisation]" in register.content
    assert b"[Oil Supplier]" in register.content
    assert b"Suspended" in register.content
