"""The maintenance subcontractor evidence kept on a supplier's record."""

from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics.models import SupplierEvaluation
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import ApprovalType
from tests.conftest import as_owner, as_owner_who_is_not_a_superuser
from tests.support import Sample, get, post, signed_in
from tests.test_suppliers import SAMPLE

pytestmark = pytest.mark.django_db


def assessment() -> dict[str, str]:
    return {
        "approval": ApprovalType.PART_CAO,
        "assessed_on": aircraft_services.today().isoformat(),
        "scope": "Inspection of Welded Steel Parts",
        "exposition_reference": "CAE B.7 Revision 4",
        "qualification_evidence": "Qualification Register Entry 7",
        "controls": "Witness Inspection and Review Test Report",
        "pre_audit_reference": "",
        "outcome": "Controls Recorded",
    }


def test_subcontractor_records_remain_separate_from_supplier_evaluations(sample: Sample) -> None:
    manager = signed_in(sample.lucy)
    created = post(manager, "/suppliers/evaluate/", **SAMPLE)
    assert created.status_code == 302
    address = created["Location"]
    form = address + "subcontracting/"
    reader = signed_in(sample.reader)
    stranger = signed_in(sample.stranger)
    assert post(reader, form, **assessment()).status_code == 403
    assert post(stranger, form, **assessment()).status_code == 404
    missing = dict(assessment(), qualification_evidence="")
    assert (
        b"Record the Exposition Reference and Qualification Evidence"
        in post(manager, form, **missing).content
    )
    assert post(manager, form, **assessment()).status_code == 302
    suspended = dict(missing, outcome="Suspended", controls="Qualification Withdrawn")
    assert post(manager, form, **suspended).status_code == 302
    detail = get(reader, address).content
    assert b"Maintenance Subcontracting Evidence" in detail
    assert b"CAE B.7 Revision 4" in detail
    assert b"Qualification Withdrawn" in detail
    assert b"Controls Recorded" in detail
    assert b"Record Subcontractor Assessment" not in detail
    register = get(reader, "/suppliers/").content
    assert b"Approved" in register and b"Suspended" not in register


def test_part_145_controls_need_pre_audit_and_a_held_approval(sample: Sample) -> None:
    manager = signed_in(sample.lucy)
    created = post(manager, "/suppliers/evaluate/", **SAMPLE)
    assert created.status_code == 302
    form = created["Location"] + "subcontracting/"
    fields = dict(assessment(), approval=ApprovalType.PART_145)
    assert b"Held No Part-145 Maintenance Approval" in post(manager, form, **fields).content
    with working_for(sample.ours.id, sample.administrator.id):
        approvals.record(
            sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Our Approval]"
        )
    assert b"Record the Pre-Audit Reference" in post(manager, form, **fields).content
    fields["pre_audit_reference"] = "Compliance Monitoring Audit 12"
    assert post(manager, form, **fields).status_code == 302
    tomorrow = (aircraft_services.today() + timedelta(days=1)).isoformat()
    assert (
        b"Cannot Be Dated in the Future"
        in post(manager, form, **dict(fields, assessed_on=tomorrow)).content
    )


def test_subcontractor_migration_preserves_existing_supplier_evidence(sample: Sample) -> None:
    """Add subcontractor evidence without rewriting existing supplier history."""
    with as_owner():
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        executor.migrate([("logistics", "0002_supplier_record_rules")])

    manager = signed_in(sample.lucy)
    created = post(manager, "/suppliers/evaluate/", **SAMPLE)
    assert created.status_code == 302
    with working_for(sample.ours.id, sample.lucy.id):
        evaluation = SupplierEvaluation.objects.get()
        original_event = Event.of(evaluation).values().get()

    with as_owner_who_is_not_a_superuser():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        MigrationExecutor(connection).migrate(latest)

    with working_for(sample.ours.id, sample.lucy.id):
        assert SupplierEvaluation.objects.get() == evaluation
        evaluation.refresh_from_db()
        assert evaluation.evidence == SAMPLE["evidence"]
        assert Event.of(evaluation).values().get() == original_event
    address = created["Location"]
    assert post(manager, address + "subcontracting/", **assessment()).status_code == 302
    assert b"Controls Recorded" in get(manager, address).content
