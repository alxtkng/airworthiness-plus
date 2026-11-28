"""Phase 4 tool register and control evidence acceptance cases."""

import re
from datetime import date
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from django.test import Client

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_plus.people.models import Person
from tests.support import Sample, get, post, signed_in

pytestmark = pytest.mark.django_db

APPROVAL = ApprovalType.PART_CAO
TOOLS = "/tools/"


@pytest.fixture(autouse=True)
def clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2026, 11, 18))


@pytest.fixture
def workshop(sample: Sample) -> Client:
    with working_for(sample.ours.id, sample.administrator.id):
        person = Person.objects.get(user=sample.lucy)
    admin = signed_in(sample.administrator)
    for action in ("Register", "Control", "Evidence", "Condition", "Reinstate"):
        result = post(
            admin,
            TOOLS + "delegations/add/",
            request_id=str(uuid4()),
            approval=APPROVAL,
            person=str(person.pk),
            action=action,
            site="Hangar",
            starts_on="2026-11-18",
            ends_on="2026-12-31",
            procedure="Sample CAE C.3 rev 1",
            authority="Fictitious signed tooling delegation",
        )
        assert result.status_code == 302, result.content
    return signed_in(sample.lucy)


def register(workshop: Client, asset: str, description: str, **extra: str) -> str:
    result = post(
        workshop,
        TOOLS + "add/",
        request_id=str(uuid4()),
        approval=APPROVAL,
        asset_id=asset,
        description=description,
        owner="Organisation",
        site="Hangar",
        location="Tool Board 1",
        **extra,
    )
    assert result.status_code == 302, result.content
    return urlsplit(result["Location"]).path


def basis(workshop: Client, address: str, kind: str, months: str = "") -> None:
    response = post(
        workshop,
        address + "control/",
        request_id=str(uuid4()),
        approval=APPROVAL,
        kind=kind,
        interval_months=months,
        instruction="Fictitious control instruction",
        instruction_revision="2",
        method="Follow the stated test method",
        limits="Satisfactory per the instruction",
        decision_basis="Fictitious approved interval and limits",
        standard="Sample control standard",
        scope="Full instrument range",
    )
    assert response.status_code == 302, response.content


def control_choice(workshop: Client, address: str, kind: str) -> str:
    page = get(workshop, address + "event/").content.decode()
    match = re.search(r'<option value="([0-9a-f-]{36})">' + re.escape(kind) + " · ", page)
    assert match, page
    return match.group(1)


def event(workshop: Client, address: str, kind: str, occurred_on: str, **extra: str) -> int:
    for event_prefix, control_kind in (
        ("Calibration", "Calibration"),
        ("Interim", "Calibration"),
        ("Servicing", "Servicing"),
        ("Pre-use", "Before each use"),
    ):
        if kind.startswith(event_prefix) and "control" not in extra:
            extra["control"] = control_choice(workshop, address, control_kind)
            break
    return post(
        workshop,
        address + "event/",
        request_id=extra.pop("request_id", str(uuid4())),
        approval=APPROVAL,
        kind=kind,
        occurred_on=occurred_on,
        evidence=extra.pop("evidence", "Fictitious signed workshop job card"),
        **extra,
    ).status_code


def test_register_is_one_physical_record_per_organisation(sample: Sample, workshop: Client) -> None:
    """REQ-360, 363. Duplicate IDs and cross-tenant URLs are refused."""
    address = register(workshop, "0201", "Grease Gun")
    assert b"0201" in get(workshop, TOOLS).content
    assert get(signed_in(sample.stranger), address).status_code == 404
    assert post(signed_in(sample.reader), TOOLS + "add/").status_code == 403
    duplicate = post(
        workshop,
        TOOLS + "add/",
        request_id=str(uuid4()),
        approval=APPROVAL,
        asset_id="0201",
        description="Duplicate",
        owner="Organisation",
        site="Hangar",
        location="Tool Board 1",
    )
    assert b"already recorded" in duplicate.content


def test_service_and_pre_use_evidence_remain_distinct(workshop: Client) -> None:
    """REQ-361, 362. Board date 3 August plus six calendar months is 3 February."""
    address = register(workshop, "0201", "Grease Gun")
    basis(workshop, address, "Servicing", "6")
    basis(workshop, address, "Before each use")
    assert event(workshop, address, "Servicing completed", "2026-08-03") == 302
    assert event(workshop, address, "Pre-use inspection", "2026-11-18") == 302
    detail = get(workshop, address).content
    assert b"3 February 2027" in detail and b"Before each use" in detail


def test_jack_repair_return_and_withdrawal(workshop: Client) -> None:
    """REQ-361. A repair entry alone leaves the physical restriction in force."""
    address = register(workshop, "0210", "Hydraulic Aircraft Jack")
    basis(workshop, address, "Servicing", "12")
    assert event(workshop, address, "Servicing completed", "2026-11-03") == 302
    assert event(workshop, address, "Unserviceable", "2026-11-10", evidence="Seal leaking") == 302
    assert event(workshop, address, "Return to use", "2026-11-18") == 200
    assert event(workshop, address, "Repair completed", "2026-11-17") == 302
    assert b"Unserviceable" in get(workshop, TOOLS).content
    token = str(uuid4())
    for _ in range(2):
        assert event(workshop, address, "Return to use", "2026-11-18", request_id=token) == 302
    assert b"Unserviceable" not in get(workshop, TOOLS).content
    assert event(workshop, address, "Withdrawn", "2026-11-18") == 302
    assert b"Withdrawn" in get(workshop, TOOLS).content
    assert b"Seal leaking" in get(workshop, address).content


def test_interim_check_does_not_move_calibration_deadline(workshop: Client) -> None:
    """REQ-362. 14 September plus six calendar months is 14 March."""
    address = register(workshop, "0142", "Torque Wrench")
    basis(workshop, address, "Calibration", "6")
    assert event(workshop, address, "Calibration completed", "2026-09-14") == 302
    assert (
        event(
            workshop,
            address,
            "Interim check passed",
            "2026-11-13",
            reference_instrument="Torque Tester 0145",
            result="100.8 Nm at 100 Nm",
            limit="±4%",
        )
        == 302
    )
    detail = get(workshop, address).content
    assert b"14 March 2027" in detail and b"Torque Tester 0145" in detail


def test_unidentified_loan_keeps_unknown_basis(workshop: Client) -> None:
    """REQ-362. Generic lender information gives no interval for the actual unit."""
    address = register(
        workshop,
        "LOAN-01",
        "Propeller Dynamic Balancing Kit",
        lender="[Propeller Organisation]",
    )
    assert b"Control basis to verify" in get(workshop, address).content
    response = post(
        workshop,
        address + "control/",
        request_id=str(uuid4()),
        approval=APPROVAL,
        kind="Calibration",
        interval_months="12",
        instruction="Generic manual",
        instruction_revision="1",
        method="Calibrate",
        limits="±5%",
        decision_basis="Generic certificate",
        scope="Balancing",
        standard="Generic standard",
    )
    assert b"actual loan" in response.content


@pytest.mark.parametrize(
    ("completed", "months", "deadline"),
    [
        ("2024-02-29", "12", "28 February 2025"),
        ("2024-01-31", "1", "29 February 2024"),
        ("2025-04-30", "1", "30 May 2025"),
    ],
)
def test_calendar_deadlines(workshop: Client, completed: str, months: str, deadline: str) -> None:
    """REQ-362. Use the completion anniversary, respecting short months."""
    address = register(workshop, "0201", "Grease Gun")
    basis(workshop, address, "Servicing", months)
    assert event(workshop, address, "Servicing completed", completed) == 302
    assert deadline.encode() in get(workshop, address).content


def test_due_day_is_inclusive(workshop: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    """REQ-362. At the end of its UK due day, the control has not yet expired."""
    address = register(workshop, "0201", "Grease Gun")
    basis(workshop, address, "Servicing", "6")
    assert event(workshop, address, "Servicing completed", "2026-08-03") == 302
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2027, 2, 3))
    assert b"Due today" in get(workshop, TOOLS).content
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2027, 2, 4))
    assert b"Overdue" in get(workshop, TOOLS).content


def test_control_revisions_preserve_accepted_evidence_and_interim_checks(workshop: Client) -> None:
    """REQ-361, 362. A new basis requires an explicit acceptance of the completion."""
    address = register(workshop, "0142", "Torque Wrench")
    basis(workshop, address, "Calibration", "12")
    old = control_choice(workshop, address, "Calibration")
    assert event(workshop, address, "Calibration completed", "2026-09-14") == 302
    assert b"14 September 2027" in get(workshop, address).content
    basis(workshop, address, "Calibration", "6")
    assert b"Completion evidence needed" in get(workshop, address).content
    assert event(workshop, address, "Calibration completed", "2026-09-14", control=old) == 200
    assert event(workshop, address, "Calibration completed", "2026-09-14") == 302
    detail = get(workshop, address).content
    assert b"14 March 2027" in detail and b"12 calendar months" in detail


def test_same_identity_and_separate_control_for_two_approvals(
    sample: Sample, workshop: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-360, 363. A CAO control decision supplies no current Part-145 decision."""
    from airworthiness_plus.organisations import approvals

    address = register(workshop, "0142", "Torque Wrench")
    basis(workshop, address, "Servicing", "6")
    assert event(workshop, address, "Servicing completed", "2026-08-03") == 302
    with working_for(sample.ours.id, sample.administrator.id):
        approvals.record(sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Test]")
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2026, 11, 29))
    detail = get(workshop, address + "?approval=Part-145").content
    assert b"Torque Wrench 0142" in detail and b"Control basis to verify" in detail
    assert b"UK.145.[Test]" in detail and b"3 February 2027" not in detail


def test_foreign_person_and_unrelated_control_are_refused_at_database(
    sample: Sample, workshop: Client
) -> None:
    """REQ-363. Even two valid IDs must point to the same tool and organisation."""
    from django.db import DatabaseError, IntegrityError, transaction

    from airworthiness_plus.history.models import Event
    from airworthiness_plus.tooling.models import Tool, ToolControlEvent, ToolDelegation

    first = register(workshop, "0201", "Grease Gun")
    other = register(workshop, "0210", "Jack")
    basis(workshop, first, "Servicing", "6")
    basis(workshop, other, "Servicing", "12")
    assert event(workshop, first, "Servicing completed", "2026-08-03") == 302
    with working_for(sample.other.id, sample.stranger.id):
        foreign = Person.objects.create(organisation=sample.other, full_name="Other Workshop")
    admin = signed_in(sample.administrator)
    invalid = post(
        admin,
        TOOLS + "delegations/add/",
        request_id=str(uuid4()),
        approval=APPROVAL,
        person=str(foreign.pk),
        action="Register",
        site="Hangar",
        starts_on="2026-11-18",
        ends_on="2026-12-31",
        procedure="Sample CAE C.3",
        authority="Outside organisation",
    )
    assert invalid.status_code == 200 and b"valid choice" in invalid.content
    with working_for(sample.ours.id, sample.lucy.id):
        recorded = ToolControlEvent.objects.get()
        assert Event.of(recorded).get().actor_id == sample.lucy.id
        other_tool = Tool.objects.get(asset_id="0210")
        with pytest.raises(IntegrityError), transaction.atomic():
            ToolControlEvent.objects.create(
                organisation=sample.ours,
                tool=other_tool,
                control=recorded.control,
                delegation=recorded.delegation,
                submission=uuid4(),
                kind=recorded.kind,
                occurred_on=recorded.occurred_on,
                signed_on=recorded.signed_on,
                evidence="Mismatch",
            )
        with pytest.raises(DatabaseError), transaction.atomic():
            ToolControlEvent.objects.filter(pk=recorded.pk).update(evidence="Overwrite")
        assert ToolDelegation.objects.filter(person=foreign).count() == 0


def test_actual_loan_sensor_serial_must_match(workshop: Client) -> None:
    """REQ-362. An identified kit gives no basis when its sensor evidence is mismatched."""
    address = register(
        workshop,
        "LOAN-02",
        "Test Balancer",
        lender="[Propeller Organisation]",
        serial="KIT-X",
        component_ids="SENSOR-X",
        is_assembly="on",
    )
    fields = dict(
        approval=APPROVAL,
        kind="Calibration",
        interval_months="12",
        instruction="Fictitious equipment instructions",
        instruction_revision="1",
        standard="Test standard",
        method="Calibration",
        limits="Test limit",
        decision_basis="Test procedure",
        scope="Employment fixture",
        loan_task="Test task and data revision",
        loan_evidence="Fictitious receipt evidence",
    )
    rejected = post(
        workshop,
        address + "control/",
        request_id=str(uuid4()),
        loan_identity="KIT-X / SENSOR-Y",
        **fields,
    )
    assert b"actual loan" in rejected.content
    assert b"Control basis to verify" in get(workshop, address).content
    accepted = post(
        workshop,
        address + "control/",
        request_id=str(uuid4()),
        loan_identity="KIT-X / SENSOR-X",
        **fields,
    )
    assert accepted.status_code == 302
    assert b"Completion evidence needed" in get(workshop, address).content


def test_withdrawn_delegation_protects_existing_signed_history(
    sample: Sample, workshop: Client
) -> None:
    """REQ-363. Withdrawal takes effect before the next technical decision."""
    from airworthiness_plus.tooling.models import ToolDelegation

    address = register(workshop, "0210", "Jack")
    basis(workshop, address, "Servicing", "12")
    with working_for(sample.ours.id, sample.administrator.id):
        grant = ToolDelegation.objects.get(action="Evidence")
    withdrawal = post(
        signed_in(sample.administrator),
        f"/tools/delegations/{grant.pk}/withdraw/",
        evidence="Fictitious withdrawn delegation",
    )
    assert withdrawal.status_code == 302
    assert event(workshop, address, "Servicing completed", "2026-11-18") == 200
    detail = get(workshop, address).content
    assert b"Fictitious approved interval and limits" in detail
    assert b"Completion evidence needed" in detail
