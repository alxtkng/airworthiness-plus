"""Calibration evidence and holds through the normal record routes."""

from datetime import date
from uuid import uuid4

import pytest
from django.test import Client

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics.models import Supplier
from airworthiness_plus.people.models import Person
from tests.support import Sample, get, post, signed_in
from tests.test_tooling import basis, register

pytestmark = pytest.mark.django_db
PROVIDERS = "/tools/providers/"


def submitted(client: Client, address: str, **values: str) -> str:
    result = post(client, address, request_id=values.pop("request_id", str(uuid4())), **values)
    assert result.status_code == 302, result.content
    return result["Location"]


@pytest.fixture
def records(sample: Sample, monkeypatch: pytest.MonkeyPatch) -> tuple[Client, str, str]:
    return setup_workshop(sample, monkeypatch, "0142")


def setup_workshop(
    sample: Sample,
    monkeypatch: pytest.MonkeyPatch,
    asset: str,
    **tool_fields: str,
) -> tuple[Client, str, str]:
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2026, 11, 18))
    with working_for(sample.ours.id, sample.administrator.id):
        person = Person.objects.get(user=sample.lucy)
        supplier = Supplier.objects.create(organisation=sample.ours, name="Fictitious Laboratory")
    admin = signed_in(sample.administrator)
    for action in (
        "Register",
        "Control",
        "Evidence",
        "Provider",
        "Order",
        "Receipt",
        "Result",
        "Certificate",
        "Reinstate",
    ):
        submitted(
            admin,
            "/tools/delegations/add/",
            approval="Part-CAO",
            person=str(person.pk),
            action=action,
            site="Hangar",
            starts_on="2026-11-01",
            ends_on="2027-12-31",
            procedure="Fictitious CAE C.3 revision 1",
            authority="Fictitious signed delegation",
        )
    writer = signed_in(sample.lucy)
    tool = register(writer, asset, "Torque Tool", serial="TEST-0142", **tool_fields)
    basis(writer, tool, "Calibration", "6")
    return writer, tool, str(supplier.pk)


def order_for(records: tuple[Client, str, str]) -> str:
    writer, tool, supplier = records
    provider = submitted(
        writer,
        PROVIDERS + "authorise/",
        approval="Part-CAO",
        site="Hangar",
        supplier=supplier,
        facility="Sample Laboratory Site A",
        measurement="Torque",
        method="TEST Torque Method Rev 3",
        unit="Nm",
        range_from="20",
        range_to="100",
        valid_from="2026-09-01",
        valid_to="2026-12-31",
        evidence="Fictitious scope schedule",
    )
    return submitted(
        writer,
        tool + "calibration/",
        provider=provider.rsplit("/", 2)[-2],
        reference="TEST-C05",
        measurement="Torque",
        unit="Nm",
        range_from="20",
        range_to="100",
        points="20, 100",
        configuration="Clockwise",
        error_limit="4",
        error_unit="Percent",
        limits_source="Test instruction, revision 2",
        uncertainty_required="on",
    )


def certificate(writer: Client, order: str, revision: str = "1", **overrides: str) -> str:
    fields = dict(
        number="TEST-CERT",
        revision=revision,
        source="Fictitious certificate source",
        calibrated_on="2026-11-14",
        received_on="2026-11-16",
        serial="TEST-0142",
        facility="Sample Laboratory Site A",
        standard="Sample control standard",
        method="TEST Torque Method Rev 3",
        traceability="Fictitious documented chain",
        rule="Fictitious simple acceptance decision rule",
        configuration="Clockwise",
    )
    fields.update(overrides)
    return submitted(writer, order + "certificate/", **fields)


def point(writer: Client, cert: str, **overrides: str) -> str:
    fields = dict(
        phase="As found",
        reference_value="100",
        measured_value="105.2",
        error="5.2",
        uncertainty="0.2",
        coverage="k=2",
        convention="Indication less reference",
        statement="Nonconforming",
    )
    fields.update(overrides)
    return submitted(writer, cert + "result/", **fields)


def test_service_provider_board_is_linked(sample: Sample) -> None:
    assert get(signed_in(sample.reader), PROVIDERS).status_code == 200


def test_out_of_limits_opens_one_case_even_with_a_passing_correction(
    records: tuple[Client, str, str],
) -> None:
    writer, tool, _ = records
    order = order_for(records)
    submitted(
        writer,
        order + "movement/",
        kind="Despatched",
        occurred_on="2026-11-12",
        expected_on="2026-11-28",
        evidence="Fictitious courier tracking",
    )
    submitted(
        writer,
        order + "movement/",
        kind="Returned",
        occurred_on="2026-11-16",
        evidence="Fictitious physical receipt",
    )
    original = certificate(writer, order, traceability="", rule="")
    point(writer, original)
    point(
        writer,
        original,
        phase="As left",
        measured_value="100.5",
        error="0.5",
        statement="Conforming",
    )
    submitted(writer, original + "decision/", outcome="Rejected", reason="Missing traceability")
    corrected = certificate(writer, order, revision="2")
    point(writer, corrected)
    detail = get(writer, order).content
    assert detail.count(b"Open affected-work case") == 1
    assert b"Provisional" in detail and b"Missing traceability" in detail
    assert b"28 November 2026" in detail
    assert b"Calibration hold" in get(writer, tool).content


def test_accepted_certificate_and_reinstatement_are_distinct(
    records: tuple[Client, str, str],
) -> None:
    writer, tool, _ = records
    order = order_for(records)
    submitted(
        writer,
        order + "movement/",
        kind="Despatched",
        occurred_on="2026-11-12",
        expected_on="2026-11-28",
        evidence="Fictitious courier tracking",
    )
    submitted(
        writer,
        order + "movement/",
        kind="Returned",
        occurred_on="2026-11-16",
        evidence="Fictitious physical receipt",
    )
    cert = certificate(writer, order)
    point(writer, cert)
    point(
        writer,
        cert,
        phase="As found",
        reference_value="20",
        measured_value="20.2",
        error="1",
        statement="Conforming",
    )
    for ref, raw in (("100", "101"), ("20", "20.2")):
        point(
            writer,
            cert,
            phase="As left",
            reference_value=ref,
            measured_value=raw,
            error="1",
            statement="Conforming",
        )
    submitted(writer, cert + "decision/", outcome="Accepted", reason="Verified full scope")
    assert b"Calibration hold" in get(writer, tool).content
    assert b"14 May 2027" not in get(writer, tool).content
    submitted(writer, order + "reinstate/", evidence="Verified controls and physical condition")
    assert b"14 May 2027" in get(writer, tool).content
    assert b"Open affected-work case" in get(writer, order).content


def create_custody(writer: Client, order: str) -> None:
    submitted(
        writer,
        order + "movement/",
        kind="Despatched",
        occurred_on="2026-11-12",
        expected_on="2026-11-28",
        evidence="Fictitious despatch evidence",
    )
    submitted(
        writer,
        order + "movement/",
        kind="Returned",
        occurred_on="2026-11-16",
        evidence="Fictitious physical return evidence",
    )


def complete_results(writer: Client, cert: str, *, found_uncertainty: str = "0.2") -> None:
    point(writer, cert)
    point(
        writer,
        cert,
        phase="As found",
        reference_value="20",
        measured_value="20.2",
        error="1",
        uncertainty=found_uncertainty,
        statement="Conforming",
    )
    for ref, raw in (("100", "101"), ("20", "20.2")):
        point(
            writer,
            cert,
            phase="As left",
            reference_value=ref,
            measured_value=raw,
            error="1",
            statement="Conforming",
        )


def test_wrong_measurement_scope_refuses_order(records: tuple[Client, str, str]) -> None:
    writer, tool, supplier = records
    provider = submitted(
        writer,
        PROVIDERS + "authorise/",
        approval="Part-CAO",
        site="Hangar",
        supplier=supplier,
        facility="Sample Laboratory Site A",
        measurement="Pressure",
        method="Pressure Method",
        unit="psi",
        range_from="4",
        range_to="100",
        valid_from="2026-09-01",
        valid_to="2026-12-31",
        evidence="Pressure scope only",
    )
    result = post(
        writer,
        tool + "calibration/",
        provider=provider.rsplit("/", 2)[-2],
        request_id=str(uuid4()),
        reference="TEST-TORQUE",
        measurement="Torque",
        unit="Nm",
        range_from="20",
        range_to="100",
        points="20, 100",
        configuration="Clockwise",
        error_limit="4",
        error_unit="Percent",
        limits_source="Tool instruction",
    )
    assert result.status_code == 200 and b"outside the authorised provider scope" in result.content


@pytest.mark.parametrize(
    ("wrong", "message"),
    [
        ({"serial": "DIFFERENT"}, b"serial or controlled components do not match"),
        ({"facility": "Wrong laboratory site"}, b"outside the ordered scope"),
        ({"traceability": ""}, b"documented metrological traceability"),
        ({"rule": ""}, b"conformity claim has no decision rule"),
    ],
)
def test_unsupported_certificate_cannot_be_accepted(
    records: tuple[Client, str, str],
    wrong: dict[str, str],
    message: bytes,
) -> None:
    writer, tool, _ = records
    order = order_for(records)
    create_custody(writer, order)
    cert = certificate(writer, order, **wrong)
    complete_results(writer, cert)
    response = post(
        writer,
        cert + "decision/",
        request_id=str(uuid4()),
        outcome="Accepted",
        reason="Fictitious review attempt",
    )
    assert response.status_code == 200 and message in response.content
    assert b"Calibration hold" in get(writer, tool).content


def test_ordered_uncertainty_required_for_as_found_conformity(
    records: tuple[Client, str, str],
) -> None:
    writer, tool, _ = records
    order = order_for(records)
    create_custody(writer, order)
    cert = certificate(writer, order)
    complete_results(writer, cert, found_uncertainty="")
    response = post(
        writer,
        cert + "decision/",
        request_id=str(uuid4()),
        outcome="Accepted",
        reason="Fictitious review attempt",
    )
    assert response.status_code == 200
    assert b"The ordered scope requires uncertainty and coverage" in response.content
    assert b"Calibration hold" in get(writer, tool).content


def test_certificate_with_wrong_vibration_sensor_cannot_be_accepted(
    sample: Sample,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = setup_workshop(
        sample,
        monkeypatch,
        "TEST-KIT",
        is_assembly="on",
        component_ids="Vibration sensor TEST-01",
    )
    writer, tool, _ = records
    order = order_for(records)
    create_custody(writer, order)
    cert = certificate(writer, order, component_ids="Vibration sensor TEST-02")
    complete_results(writer, cert)
    response = post(
        writer,
        cert + "decision/",
        request_id=str(uuid4()),
        outcome="Accepted",
        reason="Fictitious review attempt",
    )
    assert response.status_code == 200
    assert b"serial or controlled components do not match" in response.content
    assert b"Calibration hold" in get(writer, tool).content


def test_case_and_result_rollback_together(
    sample: Sample,
    records: tuple[Client, str, str],
) -> None:
    from django.db import IntegrityError, connection, transaction

    from airworthiness_plus.tooling.calibration_models import CalibrationResult, ToolImpactCase
    from tests.conftest import as_owner

    writer, _, _ = records
    order = order_for(records)
    create_custody(writer, order)
    cert = certificate(writer, order)
    try:
        with as_owner(), connection.cursor() as cursor:
            cursor.execute(
                "ALTER TABLE tooling_toolimpactcase ADD CONSTRAINT test_refuse_case "
                "CHECK (false) NOT VALID"
            )
        with pytest.raises(IntegrityError, match="test_refuse_case"), transaction.atomic():
            point(writer, cert)
    finally:
        with as_owner(), connection.cursor() as cursor:
            cursor.execute("ALTER TABLE tooling_toolimpactcase DROP CONSTRAINT test_refuse_case")
    with working_for(sample.ours.pk, sample.lucy.pk):
        assert not CalibrationResult.objects.exists()
        assert not ToolImpactCase.objects.exists()
    token = str(uuid4())
    point(writer, cert, request_id=token)
    point(writer, cert, request_id=token)
    with working_for(sample.ours.pk, sample.lucy.pk):
        result = CalibrationResult.objects.get()
        case = ToolImpactCase.objects.get()
        assert case.trigger == result and not case.provisional


def test_boundary_remains_without_case_and_as_left_failure_opens_provisional_case(
    records: tuple[Client, str, str],
) -> None:
    writer, _, _ = records
    order = order_for(records)
    create_custody(writer, order)
    cert = certificate(writer, order)
    point(writer, cert, error="-4", measured_value="96", statement="Conforming")
    assert b"Open affected-work case" not in get(writer, order).content
    point(writer, cert, phase="As left", statement="Measurement only")
    assert b"Provisional finding" in get(writer, order).content


def test_provider_orders_keep_the_board_label_date_separate_from_custody(sample: Sample) -> None:
    from airworthiness_plus.sample import calibration, suppliers

    assert suppliers.add(sample.ours, sample.administrator) == 5
    assert calibration.add(sample.ours, sample.administrator) == 2
    assert calibration.add(sample.ours, sample.administrator) == 0
    writer = signed_in(sample.reader)
    body = get(writer, PROVIDERS).content
    assert b"2026-C07" in body and b"28 November 2026" in body
    from airworthiness_plus.tooling.calibration_models import CalibrationOrder

    with working_for(sample.ours.pk, sample.reader.pk):
        order = CalibrationOrder.objects.get(reference="2026-C07")
    body = get(writer, f"/tools/orders/{order.pk}/").content
    assert b"20 November 2026" in body and b"28 November 2026" in body
    assert b"2026-C07" in body
    assert get(signed_in(sample.stranger), f"/tools/orders/{order.pk}/").status_code == 404


def test_signed_interval_change_keeps_accepted_scope_and_uses_new_interval(
    records: tuple[Client, str, str],
) -> None:
    writer, tool, _ = records
    order = order_for(records)
    create_custody(writer, order)
    cert = certificate(writer, order)
    complete_results(writer, cert)
    submitted(writer, cert + "decision/", outcome="Accepted", reason="Verified full scope")
    basis(writer, tool, "Calibration", "3")
    submitted(writer, order + "reinstate/", evidence="Reinstated under revised 3-month interval")
    tool_body = get(writer, tool).content
    assert b"14 February 2027" in tool_body and b"14 May 2027" not in tool_body
    assert b"Open affected-work case" in get(writer, order).content


def test_dated_scope_suspension_blocks_acceptance_with_external_custody_retained(
    records: tuple[Client, str, str],
) -> None:
    writer, tool, supplier = records
    order = order_for(records)
    create_custody(writer, order)
    submitted(
        writer,
        PROVIDERS + "authorise/",
        approval="Part-CAO",
        site="Hangar",
        supplier=supplier,
        facility="Sample Laboratory Site A",
        measurement="Torque",
        method="TEST Torque Method Rev 3",
        unit="Nm",
        range_from="20",
        range_to="100",
        valid_from="2026-11-13",
        valid_to="2026-12-31",
        status="Suspended",
        evidence="Fictitious provider suspension effective before calibration",
    )
    cert = certificate(writer, order)
    complete_results(writer, cert)
    blocked = post(
        writer,
        cert + "decision/",
        request_id=str(uuid4()),
        outcome="Accepted",
        reason="Fictitious attempt after the scope was suspended",
    )
    assert b"outside the ordered scope" in blocked.content
    assert b"Calibration hold" in get(writer, tool).content
    assert b"Fictitious physical return evidence" in get(writer, order).content


def test_certificate_signer_needs_calibration_delegation(
    sample: Sample,
    records: tuple[Client, str, str],
) -> None:
    writer, _, _ = records
    order = order_for(records)
    create_custody(writer, order)
    cert = certificate(writer, order)
    complete_results(writer, cert)
    fields = dict(request_id=str(uuid4()), outcome="Accepted", reason="Fictitious full scope")
    assert (
        b"needs a current tooling delegation"
        in post(
            signed_in(sample.planner),
            cert + "decision/",
            **fields,
        ).content
    )
    assert post(signed_in(sample.reader), cert + "decision/", **fields).status_code == 403
    assert post(writer, cert + "decision/", **fields).status_code == 302


def test_repair_scope_cannot_authorise_calibration(records: tuple[Client, str, str]) -> None:
    writer, tool, supplier = records
    repair = submitted(
        writer,
        PROVIDERS + "authorise/",
        approval="Part-CAO",
        site="Hangar",
        supplier=supplier,
        service="Repair",
        facility="Sample Workshop A",
        method="Fictitious workshop instructions",
        valid_from="2026-09-01",
        valid_to="2026-12-31",
        evidence="Authorised repair scope only",
    )
    response = post(
        writer,
        tool + "calibration/",
        provider=repair.rsplit("/", 2)[-2],
        request_id=str(uuid4()),
        reference="TEST-REPAIR",
        measurement="Torque",
        unit="Nm",
        range_from="20",
        range_to="100",
        points="20, 100",
        configuration="Clockwise",
        error_limit="4",
        error_unit="Percent",
        limits_source="Tool instruction",
    )
    assert response.status_code == 200 and b"Select a valid choice" in response.content
