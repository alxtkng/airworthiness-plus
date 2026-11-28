"""The export of records (REQ-134 to REQ-136; hazard H-012; threats TH-080 to TH-082).

The records are those of design-system/SampleData.md, with one of every
type of record so that every type is compared with the database.
"""

import csv
import hashlib
import importlib
import io
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import warnings
import zipfile
from base64 import b64encode
from collections.abc import Callable
from contextlib import closing
from copy import deepcopy
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter, sleep
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.acceptance import services as acceptance_services
from airworthiness_plus.acceptance.models import NoteKind
from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter, CounterKind
from airworthiness_plus.configuration import services as configuration_services
from airworthiness_plus.configuration.forecast import forecast_lines
from airworthiness_plus.configuration.models import Product
from airworthiness_plus.defects import services as defect_services
from airworthiness_plus.defects.models import Basis as DeferralBasis
from airworthiness_plus.defects.models import Decision as DefectDecision
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.directives.models import Decision
from airworthiness_plus.exports.build import _entry, build, neutralised
from airworthiness_plus.exports.registry import REGISTRY
from airworthiness_plus.exports.verify import entry_hash, verify
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.imports import services as import_services
from airworthiness_plus.imports.layouts import CERTIFICATES
from airworthiness_plus.imports.models import LoadKind
from airworthiness_plus.logistics import services as logistics_services
from airworthiness_plus.logistics.models import SubcontractorOutcome, Supplier
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.organisations.models import Approval, ApprovalType
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning import services as planning_services
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Basis
from airworthiness_plus.releases import services as release_services
from airworthiness_plus.releases.models import IssuedBy
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.sample import goods_in, phase1, stores, suppliers, tools
from airworthiness_plus.staffing import dispatch, roster
from airworthiness_plus.staffing import services as staffing_services
from airworthiness_plus.staffing.models import AbsenceType, Function
from airworthiness_plus.staffing.roster_models import (
    BankHoliday,
    Settings,
    ShiftPattern,
    StaffingMinimum,
)
from airworthiness_rules.intervals import Interval, Reading, TaskKind
from tests.conftest import as_owner, as_owner_who_is_not_a_superuser
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    get,
    signed_in,
)

pytestmark = pytest.mark.django_db
D = Decimal
FORMULA = "=HYPERLINK([Address])"
KEY = secrets.token_hex(16).upper()


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


def baseline_for_the_export(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """Sign a configuration baseline for G-ABCD, with one position recorded (REQ-274)."""
    with working_for(sample.ours.id, sample.lucy.id):
        abcd = Aircraft.objects.get(pk=fleet["G-ABCD"].pk)
        position = configuration_services.add_position(
            abcd, product=Product.AIRFRAME, chapter=34, name="[Altimeter]", tracked=True
        )
        configuration_services.record_position(position, source="[Airframe Logbook]")
        configuration_services.sign_baseline(abcd, by=sample.lucy)


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    """The sample fleet with at least one record of every type."""
    from airworthiness_plus.people import services as people_services
    from airworthiness_plus.people.models import StaffGroup

    with working_for(sample.ours.id, sample.administrator.id):
        engineer = people_services.add_person(
            organisation=sample.ours,
            full_name="Sample Certifying Engineer",
            staff_group=StaffGroup.CERTIFYING,
        )
        authorisation = people_services.record_maintenance_authorisation(
            engineer,
            reference="Sample Authorisation",
            scope="Sample Aircraft",
            valid_from=TODAY,
        )
        evidence = people_services.record_experience_evidence(
            authorisation,
            kind="Employment",
            evidence_reference="Sample Experience Ledger",
            qualification_basis="An approved maintenance organisation, sample aircraft",
            starts_on=date(2025, 1, 1),
            ends_on=date(2025, 6, 30),
            days=None,
            aircraft_type="",
            aircraft_registration="",
            licence_subcategory="",
        )
        people_services.withdraw_experience_evidence(evidence, reason="Sample correction")
        people_services.withdraw_maintenance_authorisation(
            authorisation, withdrawn_from=TODAY, reason="Sample withdrawal"
        )
    assert suppliers.add(sample.ours, sample.lucy) == 5
    assert tools.add(sample.ours, sample.administrator) == 5
    assert tools.add(sample.ours, sample.administrator) == 0
    from airworthiness_plus.tooling import services as tool_services
    from airworthiness_plus.tooling.models import ToolAction, ToolDelegation

    with working_for(sample.ours.id, sample.administrator.id):
        grant = ToolDelegation.objects.get(action=ToolAction.REINSTATE)
        tool_services.withdraw_delegation(
            sample.administrator, grant, evidence="Fictitious export withdrawal evidence"
        )
    with working_for(sample.ours.id, sample.lucy.id):
        workshop = Supplier.objects.create(organisation=sample.ours, name="Sample Workshop")
        logistics_services.assess_subcontractor(
            workshop,
            approval=ApprovalType.PART_CAO,
            assessed_on=TODAY,
            scope="Specialised Inspection",
            exposition_reference="CAE B.7",
            qualification_evidence="Qualification Record",
            controls="Review each inspection report",
            pre_audit_reference="",
            outcome=SubcontractorOutcome.CONTROLS_RECORDED,
        )
        logistics_services.assess_subcontractor(
            workshop,
            approval=ApprovalType.PART_CAO,
            assessed_on=TODAY,
            scope="Specialised Inspection",
            exposition_reference="",
            qualification_evidence="",
            controls="Qualification Withdrawn",
            pre_audit_reference="",
            outcome=SubcontractorOutcome.SUSPENDED,
        )

    assert goods_in.add(sample.ours, sample.lucy) == 5
    assert stores.add(sample.ours, sample.administrator) == 2
    assert stores.add(sample.ours, sample.administrator) == 0
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    reviews = add_sample_reviews(sample, fleet)
    ejkl = fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.lucy.id):
        airframe = Counter.objects.get(aircraft=ejkl, kind=CounterKind.AIRFRAME)
        # An entry that is corrected: both stay in the record.
        wrong = aircraft_services.enter_utilisation(airframe, Reading(TODAY, D("11208.6"), 0))
        aircraft_services.enter_utilisation(
            airframe, Reading(TODAY, D("11206.8"), 0), supersedes=wrong
        )
        programme_services.set_up_programme(
            ejkl, basis=Basis.INSTRUCTIONS, reference="[Programme Reference]"
        )
        directive = directive_services.record_directive(
            organisation=sample.ours,
            number="[Directive Number]",
            authority="Civil Aviation Authority",
            subject="[Directive Subject]",
            effective_date=date(2026, 6, 1),
        )
        decision = directive_services.decide(
            directive=directive,
            aircraft=ejkl,
            decision=Decision.APPLICABLE,
            basis="[Basis]",
            decided_by=sample.lucy,
            action=directive_services.Action(
                counter=airframe,
                starts=Reading(date(2026, 6, 1), D("11100.0"), 0),
                first=Interval(hours=D("200")),
            ),
        )
        directive_services.record_compliance(
            decision, method="[Method]", dated=date(2026, 9, 1), hours=D("11150.0"), cycles=0
        )
        data = data_services.record_data(
            organisation=sample.ours,
            title="[Maintenance Manual]",
            author=FORMULA,
            kind=Kind.INSTRUCTIONS,
            applies_to=[ejkl.type_rating],
            revision="[Revision 1]",
            revision_date=date(2025, 1, 1),
        )
        data_services.add_revision(data, revision="[Revision 2]", revision_date=date(2026, 1, 1))
        data_services.record_check(
            data,
            checked_by=sample.lucy,
            checked_on=date(2026, 11, 1),
            result="[Current]",
            next_due=date(2027, 2, 1),
        )
        User.objects.filter(pk=sample.reviewer.pk).update(second_factor_secret=KEY)
        problem = acceptance_services.add_problem(
            organisation=sample.ours, raised_by=sample.lucy, problem="[Problem]"
        )
        acceptance_services.add_note(
            problem, kind=NoteKind.SOLUTION, text="[Solution]", noted_by=sample.lucy
        )
        loaded = import_services.load(
            organisation=sample.ours,
            by=sample.lucy,
            kind=LoadKind.CERTIFICATES,
            source="[Logbooks]",
            file_name="certificates.csv",
            content=(
                ",".join(CERTIFICATES) + "\r\nG-ABCD,[Earlier Reference],2025-03-14,2026-03-14,"
                "[Issuing Organisation],,\r\n"
            ).encode(),
        )
        first = loaded.values.all()[0]
        import_services.record_checks(loaded, by=sample.lucy, agreed=[str(first.id)], differing={})
    with working_for(sample.ours.id, sample.reviewer.id):
        review = review_services.start_review(ejkl, staff=reviews.reviewer)
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = review_services.current_certificate(ejkl)
        assert certificate is not None
        review_services.extend_certificate(
            certificate,
            extended_by=sample.lucy,
            managed_for_12_months=True,
            maintained_by_approved_organisations=True,
            no_evidence_not_airworthy=True,
        )
    assert review is not None
    # Defects, and what was done about a repeat (REQ-220, REQ-227).
    phase1.add_defects(sample.ours, sample.planner, fleet)
    phase1.add_repeat_actions(sample.ours, sample.lucy)
    # Contracts and the work orders under them (REQ-240, REQ-244).
    phase1.add_contracts(sample.ours, sample.lucy, fleet)
    # Certificates of release to service (REQ-260).
    phase1.add_releases(sample.ours, sample.planner, fleet)
    # Components and where each has been fitted (REQ-230, REQ-231).
    phase1.add_components(sample.ours, sample.planner, fleet)
    # Service bulletins, changes, repairs, weighings and weight schedules (REQ-249 to REQ-254).
    phase1.add_modifications(sample.ours, sample.planner, fleet)
    # Departures, the annual review in progress and the sources of directives (REQ-284 to REQ-288).
    phase1.add_programme_records(sample.ours, sample.lucy, fleet)
    phase1.add_sources(sample.ours, sample.planner)
    # The transfer in of G-HKLM, its positions and a signed baseline (REQ-267 to REQ-274).
    phase1.add_set_up(sample.ours, sample.lucy, fleet)
    with working_for(sample.ours.id, sample.planner.id):
        aircraft = fleet["G-DGHI"]
        historical_work = programme_services.record_work(
            aircraft,
            description="Historical repair",
            dated=date(2026, 11, 16),
            hours=D("9869.5"),
            cycles=0,
            historical=True,
        )
        release_services.retain_historical_evidence(
            historical_work,
            reference="Sample Historic Release",
            issuer_name="Sample Issuer",
            issued_on=date(2026, 11, 17),
            source="Sample Signed Worksheet",
        )
        package = planning_services.build_package(
            aircraft,
            reference="WP-2026-046",
            title="Stabilator Trim Cable Rectification",
            location="Bay 1",
            starts_on=TODAY,
            ends_on=date(2026, 11, 19),
        )
        data_set = data_services.record_data(
            organisation=sample.ours,
            title="Piper Trim Maintenance Instructions",
            author="Piper",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="1",
            revision_date=TODAY,
            check_due=TODAY,
        )
        card = planning_services.add_card(
            package,
            title="Install New Stabilator Trim Cable",
            data_set=data_set,
            instruction="Maintenance Manual Chapter 27",
            planned_hours=Decimal("4.0"),
            critical=True,
        )
    with working_for(sample.ours.id, sample.administrator.id):
        from airworthiness_plus.organisations import approvals

        approvals.record(
            sample.ours,
            approval=ApprovalType.PART_145,
            reference="[Part-145 Reference]",
        )
        approval = Approval.objects.get(approval=ApprovalType.PART_145)
        demand = staffing_services.record_demand(
            actor=sample.planner,
            approval=approval,
            month=date(2026, 12, 1),
            function=Function.CERTIFYING,
            needed=D("290"),
            employed=D("192"),
            contracted=D("0"),
            basis="Certifying work and holiday cover",
        )
        staffing_services.record_report(
            demand,
            actor=sample.planner,
            reported_on=TODAY,
            reported_to="[Compliance Monitoring Manager] and [Accountable Manager]",
            action="Contracted cover booked",
        )
        staffing_services.review_plan(
            actor=sample.planner, approval=approval, reviewed_on=TODAY, outcome="Reviewed"
        )
        staffing_services.record_absence(
            actor=sample.planner,
            person=Person.objects.get(full_name="Sam Patel"),
            kind=AbsenceType.HOLIDAY,
            starts_on=date(2026, 12, 7),
            ends_on=date(2026, 12, 18),
        )
        Settings.objects.create(organisation=sample.ours)
        BankHoliday.objects.create(
            organisation=sample.ours, on=date(2026, 12, 25), name="Christmas Day"
        )
        ShiftPattern.objects.create(
            organisation=sample.ours,
            name="Day Shift",
            area="Hangar",
            days="Monday to Friday",
            starts_at=time(8),
            ends_at=time(16, 30),
            break_minutes=30,
        )
        StaffingMinimum.objects.create(
            organisation=sample.ours,
            approval=approval,
            function=Function.CERTIFYING,
            minimum=1,
            normal=2,
            applies_on="Hangar Working Days",
        )
        dispatch_shift = roster.add_shift(
            actor=sample.planner,
            approval=approval,
            person=Person.objects.get(full_name="Chris Moore"),
            area="Hangar",
            shift_name="Day Shift",
            starts_at=datetime(2026, 11, 18, 8, tzinfo=UTC),
            ends_at=datetime(2026, 11, 18, 16, 30, tzinfo=UTC),
            break_minutes=30,
            other_minutes=0,
            maintenance=True,
        )
        dispatch.assign(
            actor=sample.planner,
            card=card,
            shift=dispatch_shift,
            starts_at=datetime(2026, 11, 18, 10, tzinfo=UTC),
            ends_at=datetime(2026, 11, 18, 11, tzinfo=UTC),
            reason="Reserve time for cable installation",
        )
        dispatch.add_window(
            actor=sample.planner,
            shift=dispatch_shift,
            starts_at=datetime(2026, 11, 18, 12, tzinfo=UTC),
            ends_at=datetime(2026, 11, 18, 12, 30, tzinfo=UTC),
            note="Protected break",
        )
        roster.publish(actor=sample.planner, week=date(2026, 11, 16), note="Reviewed and Published")
        roster.record_handover(
            actor=sample.planner,
            package=package,
            outgoing=Person.objects.get(full_name="Sam Patel"),
            incoming=Person.objects.get(full_name="Chris Moore"),
            handed_at=datetime(2026, 11, 17, 16, 30, tzinfo=UTC),
            stage="Cable to Inspect",
            parts="Cable Checked In",
        )
    baseline_for_the_export(sample, fleet)
    return fleet


def opened(content: bytes) -> dict[str, Any]:
    """Return every file of an export, the JSON ones parsed."""
    archive = zipfile.ZipFile(io.BytesIO(content))
    files: dict[str, Any] = {}
    for name in archive.namelist():
        data = archive.read(name)
        files[name] = json.loads(data) if name.endswith(".json") else data.decode()
    return files


def rewritten(content: bytes, change: dict[str, bytes], *, fix_manifest: bool) -> bytes:
    """Return the export with some files replaced, as someone altering it would."""
    archive = zipfile.ZipFile(io.BytesIO(content))
    files = {name: archive.read(name) for name in archive.namelist()}
    files.update(change)
    if fix_manifest:
        manifest = json.loads(files["manifest.json"])
        for name in change:
            manifest["files"][name] = hashlib.sha256(files[name]).hexdigest()
        files["manifest.json"] = json.dumps(manifest).encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as new:
        for name, data in files.items():
            new.writestr(name, data)
    return out.getvalue()


def rows(table: str, organisation_column: str, organisation: Any, omitted: list[str]) -> Any:
    """Return every row of a table for one organisation, as the database holds it."""
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(
            f"SELECT (to_jsonb(t) - %s::text[])::text FROM {table} t "  # noqa: S608
            f"WHERE {organisation_column} = %s ORDER BY id",
            [omitted, organisation],
        )
        return [json.loads(row[0]) for row in cursor.fetchall()]


def post(client: Client, path: str) -> HttpResponse:
    return client.post(path, secure=True)  # type: ignore[return-value]


# Completeness


def test_every_type_of_record_is_in_the_export() -> None:
    """REQ-136, hazard H-012. A table of records that is not exported fails the build."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT c.relname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
            "WHERE t.tgname = 'history_write'"
        )
        with_history = {row[0] for row in cursor.fetchall()}
    exported = [one.table for one in REGISTRY]
    assert len(exported) == len(set(exported))
    assert set(exported) == with_history


def test_the_export_of_an_organisation_is_every_record_as_the_database_holds_it(
    sample: Sample, fleet: dict[str, Aircraft], monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-135. Every type of record, compared with the database, with its whole history."""
    from tests.test_calibration import (
        certificate,
        complete_results,
        create_custody,
        order_for,
        setup_workshop,
        submitted,
    )

    calibration = setup_workshop(sample, monkeypatch, "TEST-EXPORT")
    writer, _, _ = calibration
    order = order_for(calibration)
    create_custody(writer, order)
    cert = certificate(writer, order)
    complete_results(writer, cert)
    submitted(writer, cert + "decision/", outcome="Accepted", reason="Fictitious verified scope")
    submitted(writer, order + "reinstate/", evidence="Fictitious restored tool")
    from unittest.mock import patch
    from uuid import uuid4

    from airworthiness_plus.logistics import allocations
    from airworthiness_plus.logistics.models import AllocationKind
    from tests.test_stores import lot, place

    with working_for(sample.ours.id, sample.lucy.id):
        posting = lot("RX-007")
        with patch.object(aircraft_services, "today", return_value=posting.posted_on):
            allocations.record(
                sample.lucy,
                posting,
                AllocationKind.QUARANTINE,
                request_id=uuid4(),
                source=place("BAY-B"),
                destination=place("QUAR-1"),
                quantity=D("1"),
                evidence="Synthetic quarantine evidence",
            )
        export = build(sample.ours, by=sample.lucy)
    files = opened(export.content)
    manifest = files["manifest.json"]
    assert manifest["organisation"]["approval_reference"] == "UK.CAO.[Number]"
    assert manifest["aircraft"] is None
    assert manifest["exported_by"] == "Lucy Grant"
    for one in REGISTRY:
        column = "id" if one.table == "organisations_organisation" else "organisation_id"
        omitted = (
            ["password", "second_factor_secret", "passkeys"] if one.table == "accounts_user" else []
        )
        held = rows(one.table, column, sample.ours.id, omitted)
        # Individually seeded workflows have their own populated export tests.
        if one.table not in {
            "planning_workcardattestation",
            "defects_aircraftdrawing",
            "defects_damageentry",
            "defects_flightevent",
            "defects_flightreport",
            "defects_flightreportrelease",
            "planning_workcardsigningjob",
            "planning_workcardstepsignoff",
        }:
            assert held, one.table
        assert files[f"records/{one.table}.json"] == held, one.table
        with as_owner():
            entries = Event.objects.filter(
                organisation_id=sample.ours.id, record_type=one.table
            ).count()
        assert len(files[f"history/{one.table}.json"]) == entries, one.table
        assert manifest["counts"][one.table] == {"records": len(held), "history": entries}
    # Nothing of the other organisation.
    assert str(sample.other.id) not in export.content.decode("latin-1")
    text = json.dumps(files)
    assert str(sample.other.id) not in text
    assert "[Other Name]" not in text
    assert files["access-log.json"] == []
    assert "people.json" not in files


def test_upgraded_signed_records_export_blank_evidence_and_keep_original_history(
    sample: Sample,
) -> None:
    """REQ-302. Upgrade records made before the certification evidence fields existed."""
    aircraft = add_sample_fleet(sample)["G-CDEF"]
    old_targets = [
        ("history", "0004_hash_algorithm"),
        ("releases", "0003_keep_release_entry"),
        ("defects", "0002_closure_matches_defect"),
    ]
    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        executor.migrate(old_targets)
        old_apps = executor.loader.project_state(old_targets).apps
    release_model = old_apps.get_model("releases", "Release")
    defect_model = old_apps.get_model("defects", "Defect")
    with working_for(sample.ours.id, sample.planner.id):
        chris = Person.objects.get(full_name="Chris Moore")
        sam = Person.objects.get(full_name="Sam Patel")
        work = programme_services.record_work(
            aircraft,
            description="Propeller Spinner Replaced",
            dated=date(2026, 11, 4),
            hours=D("7715.0"),
            cycles=0,
        )
        work.release_reference = "[Release Reference WP-2026-043]"
        work.release_recorded_on = date(2026, 11, 5)
        work.save(update_fields=["release_reference", "release_recorded_on"])
        release = release_model.objects.create(
            organisation_id=sample.ours.id,
            work_id=work.id,
            reference=work.release_reference,
            kind=IssuedBy.ORGANISATION,
            issued_by_id=chris.id,
            issued_on=date(2026, 11, 4),
        )
        defect = defect_model.objects.create(
            organisation_id=sample.ours.id,
            aircraft_id=aircraft.id,
            title="Cabin Entry Step Loose",
            chapter=53,
            system="Fuselage",
            found_on=date(2026, 10, 27),
            decision=DefectDecision.DEFERRED,
            basis=DeferralBasis.CERTIFYING_STAFF,
            decided_by_id=sam.id,
            decided_on=date(2026, 10, 28),
            default_days=30,
            limit_on=date(2026, 11, 27),
            closed_on=date(2026, 10, 30),
            rectification="Step Secured",
        )
        original_entries = {
            row._meta.db_table: _entry(Event.of(row).get()) for row in (release, defect)
        }
        Person.objects.filter(pk=chris.id).update(full_name="Chris Moore Updated")
        Person.objects.filter(pk=sam.id).update(full_name="Sam Patel Updated")
    with as_owner_who_is_not_a_superuser(functions=("logistics_stock_on_hand(uuid, uuid)",)):
        MigrationExecutor(connection).migrate(latest)

    client = signed_in(sample.planner)
    evidence = {
        "legacy_evidence": "",
        "maintenance_authorisation_id": None,
        "scope_confirmed": False,
    }
    for path in (f"/aircraft/{aircraft.id}/export/", "/records-export/organisation/"):
        response = post(client, path)
        assert response.status_code == 200
        assert verify(response.content).problems == ()
        files = opened(response.content)
        for table, original in original_entries.items():
            old_snapshot = json.loads(original["after"])
            assert evidence.keys().isdisjoint(old_snapshot)
            (record,) = files[f"records/{table}.json"]
            assert record == old_snapshot | evidence
            (csv_record,) = csv.DictReader(io.StringIO(files[f"records/{table}.csv"]))
            assert {field: csv_record[field] for field in evidence} == {
                "legacy_evidence": "",
                "maintenance_authorisation_id": "",
                "scope_confirmed": "No",
            }
            for field in ("issuer_name", "decided_by_name", "issued_on", "decided_on", "closed_on"):
                if field in old_snapshot:
                    assert csv_record[field] == old_snapshot[field]
            first, added = files[f"history/{table}.json"]
            assert first == original
            assert added["previous_hash"] == original["hash"]
            assert added["before"] == original["after"]
            assert added["changed"] == sorted(evidence)
        (released,) = files["records/releases_release.json"]
        assert released["issuer_name"] == "Chris Moore"
        assert released["issued_on"] == "2026-11-04"
        (completed_work,) = files["records/programme_workdone.json"]
        assert completed_work["release_recorded_on"] == "2026-11-05"
        (csv_work,) = csv.DictReader(io.StringIO(files["records/programme_workdone.csv"]))
        assert csv_work["release_recorded_on"] == "2026-11-05"
        (deferred,) = files["records/defects_defect.json"]
        assert deferred["decided_by_name"] == "Sam Patel"
        assert deferred["decided_on"] == "2026-10-28"
        assert deferred["closed_on"] == "2026-10-30"


def test_an_export_carries_no_password_and_no_second_factor_key(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-132. That each changed is in the history; what it was is not."""
    with working_for(sample.ours.id, sample.lucy.id):
        export = build(sample.ours, by=sample.lucy)
    files = opened(export.content)
    assert all("password" not in user for user in files["records/accounts_user.json"])
    assert all("second_factor_secret" not in user for user in files["records/accounts_user.json"])
    text = json.dumps(files)
    assert KEY not in text
    changes = [
        entry["changed"]
        for entry in files["history/accounts_user.json"]
        if entry["record_id"] == str(sample.reviewer.id)
    ]
    assert ["second_factor_secret"] in changes


def test_the_export_of_an_aircraft_is_its_complete_record_and_no_other(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-134. Full history and superseded entries; nothing of any other aircraft."""
    ejkl = fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.planner.id):
        export = build(sample.ours, by=sample.planner, aircraft=ejkl)
    assert export.name == "G-EJKL-records-2026-11-18.zip"
    files = opened(export.content)
    assert files["manifest.json"]["aircraft"] == {"id": str(ejkl.id), "registration": "G-EJKL"}
    assert [one["registration"] for one in files["records/aircraft_aircraft.json"]] == ["G-EJKL"]
    text = json.dumps(files)
    for registration, other in fleet.items():
        if registration != "G-EJKL":
            assert str(other.id) not in text, registration
    # The corrected entry of hours is there with the entry that replaced it.
    entries = files["records/aircraft_utilisationentry.json"]
    assert sorted(entry["hours"] for entry in entries) == [11206.8, 11206.8, 11208.6]
    assert sum(1 for entry in entries if entry["supersedes_id"]) == 1
    expected = {
        "aircraft_counter": 1,
        "programme_programme": 1,
        "programme_task": 1,  # the action of the directive
        "programme_workdone": 1,  # the directive compliance
        "directives_directive": 1,
        "directives_applicability": 1,
        "directives_compliance": 1,
        "maintenance_data_dataset": 1,
        "maintenance_data_revision": 2,
        "maintenance_data_amendmentcheck": 1,
        "reviews_certificate": 1,
        "reviews_extension": 1,
        "reviews_review": 1,
        "reviews_reviewitem": 16,
    }
    for table, count in expected.items():
        assert len(files[f"records/{table}.json"]) == count, table
    # A record that was changed keeps both entries: the first revision, then superseded.
    revisions = files["history/maintenance_data_revision.json"]
    assert sorted(entry["action"] for entry in revisions) == ["Changed", "Created", "Created"]
    # The organisation's own records are not part of an aircraft's.
    for table in ("organisations_organisation", "accounts_user", "reviews_reviewstaff"):
        assert f"records/{table}.json" not in files
    assert {"id": str(sample.lucy.id), "full_name": "Lucy Grant"} in files["people.json"]["users"]
    assert "@" not in json.dumps(files["people.json"])  # names, not user names
    assert "access-log.json" not in files


def test_handover_archive_preserves_deferral_inspection_and_correction(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-134 and REQ-290. Reconcile one synthetic aircraft using only its archive."""
    aircraft = fleet["G-EJKL"]
    inspection_title = "Handover Trial Recurring Inspection"
    with working_for(sample.ours.id, sample.planner.id):
        counter = Counter.objects.get(aircraft=aircraft, kind=CounterKind.AIRFRAME)
        inspection = programme_services.add_task(
            aircraft.programme,
            title=inspection_title,
            kind=TaskKind.PROGRAMME_TASK,
            counter=counter,
            source="Synthetic inspection reference",
            interval=Interval(days=30),
        )
        programme_services.record_work(
            aircraft,
            task=inspection,
            description=inspection_title,
            dated=TODAY - timedelta(days=10),
            hours=D("11206.8"),
            cycles=0,
        )
        defect_title = "Right Headset Socket Crackle"
        forecast = {line.item: line for line in forecast_lines(aircraft, TODAY)}
        export = build(sample.ours, by=sample.planner, aircraft=aircraft)

    # Receiver checks the archive without reading the issuing database. The
    # expected digest represents the value received separately from the issuer.
    verdict = verify(export.content)
    assert verdict.problems == ()
    assert verdict.manifest_sha256 == export.manifest_sha256
    files = opened(export.content)
    defects = files["records/defects_defect.json"]
    (defect,) = [record for record in defects if record["title"] == defect_title]
    assert defect["aircraft_id"] == str(aircraft.pk)
    assert defect["closed_on"] is None
    assert defect["decision"] == DefectDecision.DEFERRED
    defect_due = forecast[f"Deferred Defect Limit, {defect_title}"]
    assert date.fromisoformat(defect["limit_on"]) == defect_due.forecast

    tasks = files["records/programme_task.json"]
    (task,) = [record for record in tasks if record["title"] == inspection_title]
    work = files["records/programme_workdone.json"]
    (completion,) = [record for record in work if record["task_id"] == task["id"]]
    next_due = date.fromisoformat(completion["dated"]) + timedelta(days=task["interval_days"])
    assert next_due == TODAY + timedelta(days=20) == forecast[inspection_title].forecast

    readings = files["records/aircraft_utilisationentry.json"]
    (correction,) = [record for record in readings if record["supersedes_id"]]
    (original,) = [record for record in readings if record["id"] == correction["supersedes_id"]]
    assert (original["hours"], correction["hours"]) == (11208.6, 11206.8)


def test_independent_receiver_imports_the_unsigned_trial_and_rejects_invalid_transfers(
    sample: Sample, fleet: dict[str, Aircraft], tmp_path: Path
) -> None:
    """REQ-134, REQ-290 and AMOS case 6. Reconstruct and replay on a separate database."""
    aircraft = fleet["G-EJKL"]
    title = "Receiver Trial Inspection"
    with working_for(sample.ours.id, sample.planner.id):
        counter = aircraft.counters.get(kind=CounterKind.AIRFRAME)
        task = programme_services.add_task(
            aircraft.programme,
            title=title,
            kind=TaskKind.PROGRAMME_TASK,
            counter=counter,
            source="Synthetic receiver trial reference",
            interval=Interval(days=30),
        )
        programme_services.record_work(
            aircraft,
            task=task,
            description=title,
            dated=TODAY - timedelta(days=10),
            hours=D("11206.8"),
            cycles=0,
        )
        sender_forecast = {line.item: line.forecast for line in forecast_lines(aircraft, TODAY)}
        export = build(sample.ours, by=sample.planner, aircraft=aircraft)

    files = opened(export.content)
    defect_title = "Right Headset Socket Crackle"
    (defect,) = [
        item for item in files["records/defects_defect.json"] if item["title"] == defect_title
    ]
    (correction,) = [
        row for row in files["records/aircraft_utilisationentry.json"] if row["supersedes_id"]
    ]
    database = tmp_path / "receiver.sqlite"
    archive_path = tmp_path / "transfer.zip"
    project = Path(__file__).resolve().parents[1]

    def receive(
        content: bytes, digest: str = export.manifest_sha256, aircraft_id: str = str(aircraft.id)
    ) -> subprocess.CompletedProcess[str]:
        archive_path.write_bytes(content)
        return subprocess.run(  # noqa: S603  fixed executable and synthetic fixture
            [
                sys.executable,
                str(project / "tools" / "receive_handover.py"),
                str(archive_path),
                str(database),
                "--manifest-digest",
                digest,
                "--aircraft-id",
                aircraft_id,
                "--defect-id",
                defect["id"],
                "--inspection-id",
                str(task.id),
                "--correction-id",
                correction["id"],
            ],
            env={"PYTHONPATH": str(project / "src")},
            capture_output=True,
            text=True,
            check=False,
        )

    first = receive(export.content)
    assert first.returncode == 0, first.stderr
    received = json.loads(first.stdout)
    assert received.pop("imported") is True
    assert date.fromisoformat(received["next_due"]) == sender_forecast[title]
    assert (
        date.fromisoformat(received["defect"]["limit_on"])
        == sender_forecast[f"Deferred Defect Limit, {defect_title}"]
    )
    assert received["defect"]["closed_on"] is None
    assert received["original_reading"]["hours"] == 11208.6
    assert received["corrected_reading"]["hours"] == 11206.8
    assert received["issuer_trust"] == "Indeterminate"
    assert received["history"]["defects_defect"] == [
        event
        for event in files["history/defects_defect.json"]
        if event["record_id"] == defect["id"]
    ]
    readings = received["history"]["aircraft_utilisationentry"]
    assert {entry["record_id"] for entry in readings} == {
        correction["id"],
        correction["supersedes_id"],
    }

    replay = receive(export.content)
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout) == {"imported": False, **received}

    def refused(result: subprocess.CompletedProcess[str], reason: str) -> None:
        assert result.returncode == 1
        assert reason in result.stderr

    forwarded_manifest = json.dumps({**files["manifest.json"], "exported_by": "Trial"}).encode()
    forwarded = rewritten(export.content, {"manifest.json": forwarded_manifest}, fix_manifest=False)
    refused(
        receive(forwarded, hashlib.sha256(forwarded_manifest).hexdigest()),
        "needs reconciliation",
    )
    refused(receive(export.content, aircraft_id=str(fleet["G-CDEF"].id)), "different aircraft")
    changed = rewritten(export.content, {"README.txt": b"Altered"}, fix_manifest=False)
    refused(receive(changed), "altered")

    for table in ("defects_defect", "programme_programme"):
        missing = rewritten(
            export.content,
            {f"records/{table}.json": b"[]", f"history/{table}.json": b"[]"},
            fix_manifest=True,
        )
        refused(receive(missing, verify(missing).manifest_sha256), "record or dependency")

    manifest = json.dumps({**files["manifest.json"], "version": 2}).encode()
    unsupported = rewritten(export.content, {"manifest.json": manifest}, fix_manifest=False)
    refused(receive(unsupported, hashlib.sha256(manifest).hexdigest()), "Unsupported")

    duplicate = io.BytesIO(export.content)
    with zipfile.ZipFile(duplicate, "a") as archive, pytest.warns(UserWarning, match="Duplicate"):
        archive.writestr("README.txt", files["README.txt"])
    refused(receive(duplicate.getvalue()), "more than once")

    with closing(sqlite3.connect(database)) as db:
        snapshots = db.execute("SELECT evidence FROM handover").fetchall()
        assert len(snapshots) == 1
        assert json.loads(snapshots[0][0]) == received


# The receiver process has only file inputs. It fails immediately if it attempts a network call.
OFFLINE_RECEIVER = """
import runpy, sys
from pathlib import Path

def offline(event, args):
    if event.startswith("socket."):
        raise RuntimeError("The trial receiver has no network access")

sys.addaudithook(offline)
script = sys.argv.pop(1)
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name="__main__")
"""
READING_TABLE = "aircraft_utilisationentry"
TRIAL_CORRECTION_REASON = "Reconciled the transcription against the synthetic airframe log."


def _whole_signing_time(earliest: datetime) -> datetime:
    next_second = earliest.replace(microsecond=0) + timedelta(seconds=1)
    delay = (next_second - datetime.now(UTC)).total_seconds()
    if delay > 0:
        sleep(delay)
    return datetime.now(UTC).replace(microsecond=0)


def _stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _signed_fixture_key(
    identity: dict[str, str], public_key: bytes, started_at: datetime, observed_at: datetime
) -> dict[str, Any]:
    """The fixture custodian supplies the enrolled public key and authority status."""
    bounds = {
        "valid_from": _stamp(started_at - timedelta(minutes=1)),
        "valid_to": _stamp(observed_at + timedelta(hours=1)),
        "revoked_at": None,
        "status_as_of": _stamp(observed_at),
    }
    subject = {name: identity[name] for name in ("signer_id", "organisation_id")}
    return {
        "format": "Airworthiness+ Synthetic Reading Trust",
        "version": 1,
        "keys": [
            {
                **subject,
                **bounds,
                "key_id": identity["key_id"],
                "public_key": b64encode(public_key).decode("ascii"),
            }
        ],
        "authorities": [
            {
                **subject,
                **bounds,
                "authority_id": identity["authority_id"],
                "aircraft_id": identity["aircraft_id"],
                "scope": "airworthiness-plus:synthetic-utilisation-reading:v1",
            }
        ],
    }


def _trial_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _receiver_archive_with_changed_reading(content: bytes, original_id: str) -> bytes:
    records_path = f"records/{READING_TABLE}.json"
    history_path = f"history/{READING_TABLE}.json"
    files = opened(content)
    records = files[records_path]
    history = files[history_path]
    record = next(row for row in records if row["id"] == original_id)
    event = next(row for row in history if row["record_id"] == original_id)
    record["hours"] = 11208.7
    event["after"] = json.dumps(record)
    event["hash"] = entry_hash(event)
    altered = rewritten(
        content,
        {records_path: _trial_json(records), history_path: _trial_json(history)},
        fix_manifest=True,
    )
    assert verify(altered).problems == ()
    return altered


def _exercise_trial_timestamps(
    command: list[str],
    run: Callable[[list[str]], subprocess.CompletedProcess[str]],
    signatures: list[dict[str, Any]],
    prior_verdict: dict[str, Any],
    receiver: Path,
    sender: Path,
    custodian: Path,
) -> None:
    issuer = importlib.import_module("timestamp_handover")
    with TemporaryDirectory(prefix="aw-trial-tsa-") as scratch:
        tsa = issuer.make_timestamp_authority(Path(scratch))
        root_pem = tsa.root_pem
        envelope = issuer.timestamp_envelope(tsa, signatures)
        wrong_imprint = issuer.issue_timestamp(tsa, bytes(64))
    with TemporaryDirectory(prefix="aw-trial-unrelated-tsa-") as scratch:
        unrelated_pem = issuer.make_timestamp_authority(Path(scratch)).root_pem

    root_pin = hashlib.sha256(root_pem).hexdigest()
    trust_root = custodian / "tsa-root.pem"
    trust_root.write_bytes(root_pem)
    (custodian / "tsa-root.sha256").write_text(root_pin + "\n")
    timestamp_file = sender / "03-timestamps.json"
    timestamp_file.write_bytes(_trial_json(envelope))

    database = receiver / "timestamped.sqlite"
    invocation = command.copy()
    invocation[command.index(str(receiver / "receiver.sqlite"))] = str(database)
    invocation += [
        "--timestamps",
        str(timestamp_file),
        "--tsa-root",
        str(trust_root),
        "--tsa-root-sha256",
        root_pin,
    ]
    if sandbox := shutil.which("sandbox-exec"):
        invocation = [sandbox, "-p", "(version 1)(allow default)(deny network*)", *invocation]

    missing = run(invocation[:-2])
    assert missing.returncode != 0
    assert "Timestamped import requires" in missing.stderr
    assert not database.exists()

    first = run(invocation)
    assert first.returncode == 0, first.stderr
    verdict = json.loads(first.stdout)
    assert verdict["imported"] is True
    assert verdict["tsa_root_sha256"] == root_pin
    assert verdict["signing_time"] == prior_verdict["signing_time"]
    assert verdict["maintenance_authorisation"] == prior_verdict["maintenance_authorisation"]
    assert verdict["signatures"] == signatures
    assert verdict["next_due"] == prior_verdict["next_due"]
    assert verdict["defect"] == prior_verdict["defect"]
    observed = verdict["trusted_timestamps"]
    assert [row["record_id"] for row in observed] == [
        item["claim"]["record_id"] for item in signatures
    ]
    assert [row["response"] for row in observed] == [
        item["response"] for item in envelope["timestamps"]
    ]
    observed_times = [datetime.fromisoformat(row["gen_time"]) for row in observed]
    assert observed_times == sorted(observed_times)
    for observed_time, signature in zip(observed_times, signatures, strict=True):
        assert observed_time >= datetime.fromisoformat(signature["claim"]["signed_at"])

    replay = run(invocation)
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout) == {**verdict, "imported": False}

    results = {"missing_pin": missing.stderr.strip().splitlines()[-1]}

    def refused(name: str, arguments: list[str]) -> None:
        result = run(arguments)
        assert result.returncode != 0, name
        assert result.stderr.strip(), name
        results[name] = result.stderr.strip().splitlines()[-1]

    refused("mismatched_root_pin", [*invocation[:-1], "0" * 64])
    unrelated = receiver / "unrelated-tsa.pem"
    unrelated.write_bytes(unrelated_pem)
    refused(
        "unrelated_pinned_root",
        [
            *invocation[:-3],
            str(unrelated),
            "--tsa-root-sha256",
            hashlib.sha256(unrelated_pem).hexdigest(),
        ],
    )

    rejected_file = receiver / "rejected-timestamps.json"
    rejected_invocation = invocation.copy()
    rejected_invocation[invocation.index("--timestamps") + 1] = str(rejected_file)
    original, correction = envelope["timestamps"]
    for name, rows in (
        ("missing_original", [correction]),
        (
            "swapped_responses",
            [
                {**original, "response": correction["response"]},
                {**correction, "response": original["response"]},
            ],
        ),
        (
            "same_tsa_wrong_imprint",
            [{**original, "response": b64encode(wrong_imprint).decode("ascii")}, correction],
        ),
        ("malformed_response", [{**original, "response": "AA=="}, correction]),
    ):
        rejected_file.write_bytes(_trial_json({**envelope, "timestamps": rows}))
        refused(name, rejected_invocation)

    with closing(sqlite3.connect(database)) as db:
        (row,) = db.execute("SELECT evidence FROM handover").fetchall()
        assert json.loads(row[0]) == {
            key: value for key, value in verdict.items() if key != "imported"
        }
    (receiver / "timestamp-verdict.json").write_bytes(_trial_json(verdict))
    (receiver / "timestamp-results.json").write_bytes(_trial_json(results))


def test_signed_gejkl_trial_reconstructs_and_verifies_both_readings_offline(
    sample: Sample, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(project / "tools"))
    signing = importlib.import_module("sign_handover")

    sender = tmp_path / "sender"
    custodian = tmp_path / "custodian"
    receiver = tmp_path / "receiver"
    for directory in (sender, custodian, receiver):
        directory.mkdir()

    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    aircraft = fleet["G-EJKL"]
    private_key = Ed25519PrivateKey.generate()
    enrolled_public_key = private_key.public_key().public_bytes_raw()
    started_at = datetime.now(UTC).replace(microsecond=0)
    identity = {
        "signer_id": str(sample.planner.id),
        "organisation_id": str(sample.ours.id),
        "aircraft_id": str(aircraft.id),
        "key_id": "GEJKL-TRIAL-KEY",
        "authority_id": "GEJKL-TRIAL-UTILISATION",
    }
    inspection_title = "Signed Handover Trial Recurring Inspection"
    with working_for(sample.ours.id, sample.planner.id):
        counter = aircraft.counters.get(kind=CounterKind.AIRFRAME)
        programme = programme_services.set_up_programme(
            aircraft, basis=Basis.INSTRUCTIONS, reference="Synthetic trial programme"
        )
        defect = defect_services.record_defect(
            aircraft,
            title="Right Headset Socket Crackle",
            note="Synthetic pilot report. Use the left socket during the deferral.",
            found_on=TODAY,
            chapter=23,
            system="Communications",
            decision=DefectDecision.DEFERRED,
            basis=DeferralBasis.PILOT_NON_REQUIRED,
            decided_on=TODAY,
            data_limit_on=TODAY + timedelta(days=7),
        )
        inspection = programme_services.add_task(
            programme,
            title=inspection_title,
            kind=TaskKind.PROGRAMME_TASK,
            counter=counter,
            source="Synthetic inspection instructions, revision 1",
            interval=Interval(days=30),
        )
        completion = programme_services.record_work(
            aircraft,
            task=inspection,
            description="Synthetic inspection completed. Airframe reading 11206.8 hours.",
            dated=TODAY - timedelta(days=10),
            hours=D("11206.8"),
            cycles=0,
            instruction_reference="Synthetic instruction AW-I-05",
            instruction_revision="2",
            completion_measurements="Clearance 1.2 mm",
        )
        original = aircraft_services.enter_utilisation(counter, Reading(TODAY, D("11208.6"), 0))
        before = build(sample.ours, by=sample.planner, aircraft=aircraft)
        original_at = _whole_signing_time(Event.of(original).get().at)
        original_record = next(
            row
            for row in opened(before.content)[f"records/{READING_TABLE}.json"]
            if row["id"] == str(original.id)
        )
        original_signature = signing.sign_original(
            original_record, private_key=private_key, signed_at=_stamp(original_at), **identity
        )
        (sender / "01-original.zip").write_bytes(before.content)
        (sender / "01-original-signature.json").write_bytes(_trial_json(original_signature))

        correction = aircraft_services.enter_utilisation(
            counter, Reading(TODAY, D("11206.8"), 0), supersedes=original
        )
        final = build(sample.ours, by=sample.planner, aircraft=aircraft)
        correction_at = _whole_signing_time(max(original_at, Event.of(correction).get().at))
        forecast = {line.item: line.forecast for line in forecast_lines(aircraft, TODAY)}

    readings = opened(final.content)[f"records/{READING_TABLE}.json"]
    assert original_record == next(row for row in readings if row["id"] == str(original.id))
    assert str(correction.id) not in {
        row["id"] for row in opened(before.content)[f"records/{READING_TABLE}.json"]
    }
    corrected_record = next(row for row in readings if row["id"] == str(correction.id))
    corrected_signature = signing.sign_correction(
        original_record,
        corrected_record,
        original_signature,
        private_key=private_key,
        signed_at=_stamp(correction_at),
        reason=TRIAL_CORRECTION_REASON,
        **identity,
    )
    envelope = signing.signature_envelope(original_signature, corrected_signature)
    (sender / "02-corrected.zip").write_bytes(final.content)
    (sender / "02-signatures.json").write_bytes(_trial_json(envelope))
    (sender / "identifiers.json").write_bytes(
        _trial_json(
            {
                "business_date": TODAY.isoformat(),
                "aircraft_id": identity["aircraft_id"],
                "defect_id": str(defect.id),
                "inspection_id": str(inspection.id),
                "correction_id": str(correction.id),
                "original_archive_manifest_sha256": before.manifest_sha256,
                "corrected_archive_manifest_sha256": final.manifest_sha256,
            }
        )
    )

    trust = _signed_fixture_key(identity, enrolled_public_key, started_at, correction_at)
    trust_bytes = _trial_json(trust)
    trust_digest = hashlib.sha256(trust_bytes).hexdigest()
    trust_file = custodian / "trust.json"
    trust_file.write_bytes(trust_bytes)
    (custodian / "trust.sha256").write_text(trust_digest + "\n")
    database = receiver / "receiver.sqlite"
    script = project / "tools" / "receive_handover.py"
    archive = sender / "02-corrected.zip"
    signatures = sender / "02-signatures.json"
    command = [
        sys.executable,
        "-c",
        OFFLINE_RECEIVER,
        str(script),
        str(archive),
        str(database),
        "--manifest-digest",
        final.manifest_sha256,
        "--aircraft-id",
        identity["aircraft_id"],
        "--defect-id",
        str(defect.id),
        "--inspection-id",
        str(inspection.id),
        "--correction-id",
        str(correction.id),
        "--signatures",
        str(signatures),
        "--trust",
        str(trust_file),
        "--trust-sha256",
        trust_digest,
    ]

    def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603  fixed Python receiver and synthetic file inputs
            arguments,
            env={"PYTHONPATH": str(project / "src"), "PATH": os.environ.get("PATH", os.defpath)},
            capture_output=True,
            check=False,
            text=True,
        )

    results: dict[str, Any] = {}
    without_trust = run(command[:-4])
    assert without_trust.returncode != 0
    assert "requires --signatures, --trust and --trust-sha256" in without_trust.stderr
    assert not database.exists()
    results["missing_trust"] = without_trust.stderr.strip().splitlines()[-1]

    comparison = sender / "comparison.json"
    report = receiver / "reconciliation.txt"
    defect_due = forecast["Deferred Defect Limit, Right Headset Socket Crackle"]
    inspection_due = forecast[inspection_title]
    assert defect_due is not None and inspection_due is not None
    expected: dict[str, Any] = {
        "format": "Airworthiness+ Aircraft Handover Reconciliation",
        "version": 1,
        "records": {
            "source_organisation_id": identity["organisation_id"],
            "aircraft_id": identity["aircraft_id"],
            "defect_id": str(defect.id),
            "defect_limit_on": defect_due.isoformat(),
            "inspection_id": str(inspection.id),
            "inspection_source": inspection.source,
            "completion_id": str(completion.id),
            "instruction_reference": "Synthetic instruction AW-I-05",
            "instruction_revision": "2",
            "completion_measurements": "Clearance 1.2 mm",
            "next_due": inspection_due.isoformat(),
            "original_reading_id": str(original.id),
            "corrected_reading_id": str(correction.id),
            "original_hours": 11208.6,
            "corrected_hours": 11206.8,
        },
    }
    comparison_command = [*command, "--compare", str(comparison), "--report", str(report)]
    comparison.write_bytes(_trial_json({**expected, "version": 2}))
    unsupported_comparison = run(comparison_command)
    assert unsupported_comparison.returncode == 1
    assert "Unsupported reconciliation format or version" in unsupported_comparison.stderr
    assert not database.exists()
    inconsistent = deepcopy(expected)
    inconsistent["records"]["next_due"] = "2026-12-31"
    comparison.write_bytes(_trial_json(inconsistent))
    changed_due = run(comparison_command)
    assert changed_due.returncode == 1
    assert "Reconciliation differs for next_due" in changed_due.stderr
    assert not database.exists()
    comparison.write_bytes(_trial_json(expected))

    began = perf_counter()
    first = run(comparison_command)
    elapsed = perf_counter() - began
    assert first.returncode == 0, first.stderr
    evidence = json.loads(first.stdout)
    assert evidence["imported"] is True
    assert evidence["trust_sha256"] == trust_digest
    assert evidence["signatures"] == envelope["signatures"]
    assert evidence["issuer_trust"] != "Indeterminate"
    assert evidence["signing_time"].lower().startswith("signer-asserted")
    assert evidence["correction_reason"] == TRIAL_CORRECTION_REASON
    assert (evidence["original_reading"]["hours"], evidence["corrected_reading"]["hours"]) == (
        11208.6,
        11206.8,
    )
    assert evidence["corrected_reading"]["supersedes_id"] == str(original.id)
    assert evidence["defect"]["closed_on"] is None
    assert (
        date.fromisoformat(evidence["defect"]["limit_on"])
        == forecast["Deferred Defect Limit, Right Headset Socket Crackle"]
    )
    assert date.fromisoformat(evidence["next_due"]) == forecast[inspection_title]
    (receiver / "verdict.json").write_bytes(_trial_json(evidence))
    report_text = report.read_text()
    assert "Imported in" in report_text
    assert "Rekeyed records: 0" in report_text
    assert "Missing or changed mapped fields: 0" in report_text
    assert "Completion measurements: Clearance 1.2 mm" in report_text
    assert "Operational maintenance authority: Unverified" in report_text

    if (node := os.environ.get("AIRWORTHINESS_NODE24")) is not None:
        _exercise_independent_node_receiver(node, receiver, archive, comparison, final)

    replay = run(command)
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout) == {**evidence, "imported": False}
    results["verification_and_import_seconds"] = round(elapsed, 3)
    results["replay"] = "One snapshot, replay reported imported=false"

    def refusal(name: str, args: list[str], expected: str) -> None:
        result = run(args)
        assert result.returncode != 0, name
        assert expected.casefold() in result.stderr.casefold(), (name, result.stderr)
        results[name] = result.stderr.strip().splitlines()[-1]

    refusal("trust_pin_mismatch", [*command[:-1], "0" * 64], "trust")
    for name, field, scope, value, outcome in (
        ("unknown_issuer", "keys", None, [], "Unknown"),
        ("expired_key", "keys", "valid_to", _stamp(original_at), "Inapplicable"),
        ("revoked_key", "keys", "revoked_at", _stamp(original_at), "Inapplicable"),
        ("missing_grant", "authorities", None, [], "Unknown"),
        ("expired_grant", "authorities", "valid_to", _stamp(correction_at), "Inapplicable"),
        (
            "wrong_aircraft_grant",
            "authorities",
            "aircraft_id",
            str(fleet["G-CDEF"].id),
            "Inapplicable",
        ),
        (
            "historical_status_unavailable",
            "keys",
            "status_as_of",
            _stamp(original_at - timedelta(seconds=1)),
            "Indeterminate",
        ),
    ):
        alternate = deepcopy(trust)
        if scope is None:
            alternate[field] = value
        else:
            alternate[field][0][scope] = value
        changed_trust = receiver / "negative-trust.json"
        synthetic = _trial_json(alternate)
        changed_trust.write_bytes(synthetic)
        refusal(
            name,
            [
                *command[:-3],
                str(changed_trust),
                "--trust-sha256",
                hashlib.sha256(synthetic).hexdigest(),
            ],
            outcome,
        )

    modified_archive = receiver / "negative-archive.zip"
    modified = _receiver_archive_with_changed_reading(final.content, str(original.id))
    modified_archive.write_bytes(modified)
    arguments = command.copy()
    arguments[command.index(str(archive))] = str(modified_archive)
    arguments[command.index("--manifest-digest") + 1] = verify(modified).manifest_sha256
    refusal("rehashed_altered_reading", arguments, "Invalid")

    changed_envelope = deepcopy(envelope)
    changed_envelope["signatures"][1]["claim"]["reason"] = "Changed after endorsement"
    modified_signatures = receiver / "negative-signatures.json"
    modified_signatures.write_bytes(_trial_json(changed_envelope))
    arguments = command.copy()
    arguments[command.index("--signatures") + 1] = str(modified_signatures)
    refusal("altered_correction_reason", arguments, "Invalid")

    changed_envelope = deepcopy(envelope)
    claim = changed_envelope["signatures"][1]["claim"]
    claim["supersedes_claim_sha256"] = "0" * 64
    payload = json.dumps(
        claim, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()
    changed_envelope["signatures"][1]["signature"] = b64encode(private_key.sign(payload)).decode()
    modified_signatures.write_bytes(_trial_json(changed_envelope))
    refusal("valid_signature_wrong_original_claim", arguments, "Invalid")

    with closing(sqlite3.connect(database)) as db:
        (row,) = db.execute("SELECT evidence FROM handover").fetchall()
        assert json.loads(row[0]) == {
            key: value for key, value in evidence.items() if key != "imported"
        }
    (receiver / "results.json").write_bytes(_trial_json(results))
    _exercise_trial_timestamps(
        command, run, envelope["signatures"], evidence, receiver, sender, custodian
    )


def _exercise_independent_node_receiver(
    node: str, receiver: Path, archive: Path, comparison: Path, export: Any
) -> None:
    script = Path(__file__).resolve().parents[1] / "tools" / "reconcile_handover.mjs"
    database = receiver / "node-receiver.sqlite"
    results: dict[str, Any] = {}
    signatures = archive.parent / "02-signatures.json"
    trust = archive.parent.parent / "custodian/trust.json"

    def run(
        path: Path,
        digest: str,
        sidecar: Path = comparison,
        trust_path: Path = trust,
        target: Path = database,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603  opted-in executable and fixed synthetic inputs
            [
                node,
                str(script),
                str(path),
                digest,
                str(sidecar),
                str(target),
                str(signatures),
                str(trust_path),
                hashlib.sha256(trust_path.read_bytes()).hexdigest(),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    for label, imported in (("valid", True), ("replay", False)):
        result = run(archive, export.manifest_sha256)
        assert result.returncode == 0, result.stderr
        evidence = json.loads(result.stdout)
        assert evidence["imported"] is imported
        assert evidence["checked"] == json.loads(comparison.read_bytes())["records"]
        assert evidence["issuer_trust"] == "Verified against recipient-pinned synthetic trust"
        assert evidence["content"] == "Both detached reading signatures verified"
        assert evidence["signing_time"] == "Signer-asserted"
        assert (
            evidence["maintenance_authority"]
            == "Synthetic authority verified at claimed signing times"
        )
        results[label] = evidence

    files = opened(export.content)
    manifest = _trial_json({**files["manifest.json"], "version": 2})
    table = "records/defects_defect.json"
    defects = files[table]
    assert defects
    broken_tasks = deepcopy(files["records/programme_task.json"])
    for row in broken_tasks:
        row["programme_id"] = row["id"]
    for label, changes, rehash, reason in (
        ("unsupported", {"manifest.json": manifest}, False, "Unsupported archive"),
        ("altered", {"README.txt": b"Altered"}, False, "Altered archive member"),
        ("missing", {"records/programme_programme.json": b"[]"}, True, "broken dependency"),
        ("duplicate", {table: _trial_json([*defects, defects[0]])}, True, "Duplicate record"),
        (
            "dangling",
            {"records/programme_task.json": _trial_json(broken_tasks)},
            True,
            "broken dependency",
        ),
    ):
        path = receiver / "node-refusal.zip"
        content = rewritten(export.content, changes, fix_manifest=rehash)
        path.write_bytes(content)
        with zipfile.ZipFile(io.BytesIO(content)) as staged:
            digest = hashlib.sha256(staged.read("manifest.json")).hexdigest()
        result = run(path, digest)
        assert result.returncode == 1 and reason in result.stderr, result.stderr
        results[label] = result.stderr.strip()

    wrong = json.loads(comparison.read_bytes())
    wrong["records"]["aircraft_id"] = wrong["records"]["defect_id"]
    path = receiver / "node-wrong-aircraft.json"
    path.write_bytes(_trial_json(wrong))
    result = run(archive, export.manifest_sha256, path)
    assert result.returncode == 1 and "Wrong organisation or aircraft" in result.stderr
    results["wrong_aircraft"] = result.stderr.strip()
    held = json.loads(trust.read_bytes())
    alternate = receiver / "node-trial-trust.json"
    for label, replaced, reason in (
        ("unknown_issuer", {**held, "keys": []}, "Issuer key is absent"),
        ("absent_authority", {**held, "authorities": []}, "Maintenance authority is absent"),
        (
            "expired_authority",
            {
                **held,
                "authorities": [
                    {**grant, "valid_to": grant["valid_from"]} for grant in held["authorities"]
                ],
            },
            "Maintenance authority is outside its validity",
        ),
    ):
        alternate.write_bytes(_trial_json(replaced))
        result = run(archive, export.manifest_sha256, trust_path=alternate)
        assert result.returncode == 1 and reason in result.stderr, result.stderr
        results[label] = result.stderr.strip()

    updated_trust = deepcopy(held)
    for entry in updated_trust["keys"] + updated_trust["authorities"]:
        entry["status_as_of"] = _stamp(
            datetime.fromisoformat(entry["status_as_of"]) + timedelta(seconds=10)
        )
    alternate.write_bytes(_trial_json(updated_trust))
    result = run(
        archive,
        export.manifest_sha256,
        trust_path=alternate,
        target=receiver / "node-updated-trust.sqlite",
    )
    assert result.returncode == 0, result.stderr
    results["updated_trust"] = json.loads(result.stdout)
    assert results["updated_trust"]["trust_sha256"] != results["valid"]["trust_sha256"]
    replay = run(archive, export.manifest_sha256)
    assert replay.returncode == 0, replay.stderr
    results["replay_after_refusals"] = json.loads(replay.stdout)
    assert results["replay_after_refusals"]["imported"] is False
    (receiver / "node-results.json").write_bytes(_trial_json(results))


# Verification (T-SEC-019)


def test_the_export_agrees_with_itself_and_with_the_chain_in_the_database(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-134, threat TH-081. The check in the export is the check the system makes."""
    with working_for(sample.ours.id, sample.lucy.id):
        export = build(sample.ours, by=sample.lucy)
        events = list(Event.objects.all())
        assert chain.problems(events) == []
        assert all(entry_hash(_entry(event)) == chain.expected_hash(event) for event in events)
    verdict = verify(export.content)
    assert verdict.problems == ()
    assert verdict.manifest_sha256 == export.manifest_sha256


def test_an_altered_export_fails_verification(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """Threat TH-081, planned test T-SEC-019."""
    with working_for(sample.ours.id, sample.lucy.id):
        export = build(sample.ours, by=sample.lucy, aircraft=fleet["G-EJKL"])
    archive = zipfile.ZipFile(io.BytesIO(export.content))
    records_name = "records/reviews_certificate.json"
    history_name = "history/reviews_certificate.json"
    records = archive.read(records_name).replace(b"2026-12-06", b"2028-12-06")
    assert records != archive.read(records_name)

    # A record changed, and nothing else.
    verdict = verify(rewritten(export.content, {records_name: records}, fix_manifest=False))
    assert verdict.problems[0] == f"{records_name}: has been altered since the export was made"
    assert len(verdict.problems) == 2  # and the record no longer agrees with its history

    # A record changed and the manifest made to match: the history disagrees.
    verdict = verify(rewritten(export.content, {records_name: records}, fix_manifest=True))
    assert len(verdict.problems) == 1
    assert "is not what the last entry of its history says" in verdict.problems[0]
    assert verdict.manifest_sha256 != export.manifest_sha256

    # The history changed to match as well: the hash of the entry disagrees.
    history = archive.read(history_name).replace(b"2026-12-06", b"2028-12-06")
    verdict = verify(
        rewritten(export.content, {records_name: records, history_name: history}, fix_manifest=True)
    )
    assert any("has been altered since it was written" in one for one in verdict.problems)

    # An entry removed from the middle of a record's history.
    entries = json.loads(archive.read("history/maintenance_data_revision.json"))
    changed = next(entry for entry in entries if entry["action"] == "Changed")
    first = next(
        entry
        for entry in entries
        if entry["record_id"] == changed["record_id"] and entry["sequence"] == 1
    )
    entries.remove(first)
    verdict = verify(
        rewritten(
            export.content,
            {"history/maintenance_data_revision.json": json.dumps(entries).encode()},
            fix_manifest=True,
        )
    )
    assert any("an entry is missing before this one" in one for one in verdict.problems)

    # An entry said to be hashed in a way this check does not know (OWASP ASVS 5.0, 11.2.2).
    entries = json.loads(archive.read(history_name))
    assert {entry["hash_algorithm"] for entry in entries} == {"sha256-fields-1"}
    entries[0]["hash_algorithm"] = "another"
    verdict = verify(
        rewritten(export.content, {history_name: json.dumps(entries).encode()}, fix_manifest=True)
    )
    assert len(verdict.problems) == 1
    assert "was hashed in a way this check does not know" in verdict.problems[0]

    # A file added, and something that is not an export at all. A file
    # removed is in test_a_file_removed_from_an_export_fails_verification.
    verdict = verify(rewritten(export.content, {"extra.json": b"[]"}, fix_manifest=False))
    assert verdict.problems == ("extra.json: is not in the manifest",)
    assert verify(b"not a zip").problems != ()


@pytest.mark.parametrize("name", ["records/reviews_certificate.json", "manifest.json"])
def test_an_export_holding_two_files_of_one_name_fails_verification(
    sample: Sample, fleet: dict[str, Aircraft], name: str
) -> None:
    """Threat TH-081; review of 20 November 2026, finding 3. A forged copy
    placed before the genuine file is what a reader taking the first of a
    name would open. The file is refused, whichever copy is checked."""
    with working_for(sample.ours.id, sample.lucy.id):
        export = build(sample.ours, by=sample.lucy, aircraft=fleet["G-EJKL"])
    archive = zipfile.ZipFile(io.BytesIO(export.content))
    genuine = archive.read(name)
    forged = genuine.replace(b"2026-12-06", b"2028-12-06").replace(b'"files"', b'"files" ')
    assert forged != genuine
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as new, warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # zipfile warns of the duplicate name
        new.writestr(name, forged)
        for member in archive.namelist():
            new.writestr(member, archive.read(member))
    verdict = verify(out.getvalue())
    assert f"{name}: is in the export more than once" in verdict.problems


def test_a_file_removed_from_an_export_fails_verification(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """Threat TH-081; review of 20 November 2026, a test that claimed this
    and did not do it."""
    with working_for(sample.ours.id, sample.lucy.id):
        export = build(sample.ours, by=sample.lucy, aircraft=fleet["G-EJKL"])
    archive = zipfile.ZipFile(io.BytesIO(export.content))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as new:
        for member in archive.namelist():
            if member != "people.json":
                new.writestr(member, archive.read(member))
    verdict = verify(out.getvalue())
    assert verdict.problems == ("people.json: is in the manifest and not in the export",)


def test_the_command_checks_an_export_without_the_database(
    sample: Sample, fleet: dict[str, Aircraft], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Threat TH-081. Whoever receives an export can check it."""
    with working_for(sample.ours.id, sample.lucy.id):
        export = build(sample.ours, by=sample.lucy, aircraft=fleet["G-EJKL"])
    good = tmp_path / export.name
    good.write_bytes(export.content)
    call_command("verify_export", str(good))
    assert f"Manifest SHA-256 {export.manifest_sha256}" in capsys.readouterr().out
    bad = tmp_path / "altered.zip"
    bad.write_bytes(rewritten(export.content, {"people.json": b"{}"}, fix_manifest=False))
    with pytest.raises(CommandError, match="does not agree with itself"):
        call_command("verify_export", str(bad))


# Spreadsheets (T-SEC-020)


def test_a_value_that_looks_like_a_formula_is_not_run_by_a_spreadsheet(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """Threat TH-082, planned test T-SEC-020. The JSON keeps the value as it was entered."""
    for value in ("=1+1", "+1", "-1", "@SUM(A1)", "\tx", "\rx"):
        assert neutralised(value) == "'" + value
    assert neutralised("G-EJKL") == "G-EJKL"
    assert neutralised(-1) == "-1"  # a number is not text
    assert neutralised(None) == ""
    assert neutralised(True) == "Yes"
    with working_for(sample.ours.id, sample.lucy.id):
        export = build(sample.ours, by=sample.lucy, aircraft=fleet["G-EJKL"])
    files = opened(export.content)
    assert files["records/maintenance_data_dataset.json"][0]["author"] == FORMULA
    assert f",'{FORMULA}," in files["records/maintenance_data_dataset.csv"]
    assert f",{FORMULA}," not in files["records/maintenance_data_dataset.csv"]


# The pages


def test_an_export_is_sent_as_a_file_and_logged_with_its_checksum(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-009, REQ-134, threats TH-080 and TH-081."""
    client = signed_in(sample.planner)
    response = post(client, f"/aircraft/{fleet['G-EJKL'].id}/export/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert response["Content-Disposition"] == 'attachment; filename="G-EJKL-records-2026-11-18.zip"'
    assert "no-store" in response["Cache-Control"]
    verdict = verify(response.content)
    assert verdict.problems == ()
    with working_for(sample.ours.id, sample.planner.id):
        entry = AccessEntry.objects.get(kind="Records Exported")
        assert entry.user == sample.planner
        assert entry.detail == f"G-EJKL, SHA-256 {verdict.manifest_sha256}"
    body = get(client, "/records-export/").content.decode()
    assert f"<td>G-EJKL, SHA-256 {verdict.manifest_sha256}</td>" in body
    assert "<td>[Planning and Records Name]</td>" in body
    assert "Export the Record of [Your Organisation]</button>" in body

    whole = post(client, "/records-export/organisation/")
    assert (
        whole["Content-Disposition"]
        == 'attachment; filename="Your-Organisation-records-2026-11-18.zip"'
    )
    files = opened(whole.content)
    # The export of the organisation includes the log of the export before it.
    assert [entry["kind"] for entry in files["access-log.json"]] == ["Records Exported"]
    assert verify(whole.content).problems == ()


def addresses(fleet: dict[str, Aircraft]):  # type: ignore[no-untyped-def]
    return [
        ("GET", "/records-export/", Action.EXPORT_RECORDS),
        ("POST", "/records-export/organisation/", Action.EXPORT_RECORDS),
        ("POST", f"/aircraft/{fleet['G-EJKL'].id}/export/", Action.EXPORT_RECORDS),
    ]


def call(client: Client, method: str, path: str) -> HttpResponse:
    return get(client, path) if method == "GET" else post(client, path)


def test_the_export_of_an_organisation_is_limited_to_6_in_an_hour(
    sample: Sample, fleet: dict[str, Aircraft], monkeypatch: pytest.MonkeyPatch
) -> None:
    """OWASP ASVS 5.0, 15.2.2; threat TH-007. It reads every record and its history,
    so it is the one thing a signed-in user could ask for again and again. The
    export of one aircraft, and the other organisation, are not held back by it."""
    client = signed_in(sample.planner)
    for _ in range(6):
        assert post(client, "/records-export/organisation/").status_code == 200
    refused = post(client, "/records-export/organisation/")
    assert refused.status_code == 429
    assert "No More Than 6 Exports of the Organisation in an Hour" in refused.content.decode()
    assert refused["Content-Type"].startswith("text/html")
    with working_for(sample.ours.id, sample.planner.id):
        made = AccessEntry.objects.filter(kind="Records Exported")
        assert made.count() == 6
    assert post(client, f"/aircraft/{fleet['G-EJKL'].id}/export/").status_code == 200
    assert post(signed_in(sample.stranger), "/records-export/organisation/").status_code == 200
    # It is 6 in an hour, not 6 for ever: 59 minutes on it is still refused, 61 it is not.
    real = sign_in.current_time

    def later(minutes: int) -> Client:
        """Return the planner signed in afresh, with the clock moved on."""
        monkeypatch.setattr(sign_in, "current_time", lambda: real() + timedelta(minutes=minutes))
        fresh = signed_in(sample.planner)
        session = fresh.session
        session["signed_in_at"] = session["last_seen"] = sign_in.current_time().isoformat()
        session.save()
        return fresh

    assert post(later(59), "/records-export/organisation/").status_code == 429
    assert post(later(61), "/records-export/organisation/").status_code == 200


def test_another_organisations_aircraft_cannot_be_exported(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-003, threats TH-020 and TH-080, planned test T-SEC-010."""
    stranger = signed_in(sample.stranger)
    assert post(stranger, f"/aircraft/{fleet['G-EJKL'].id}/export/").status_code == 404
    assert "G-EJKL" not in get(stranger, "/records-export/").content.decode()
    whole = post(stranger, "/records-export/organisation/")
    text = json.dumps(opened(whole.content))
    assert "G-EJKL" not in text
    assert "Lucy Grant" not in text
    assert str(sample.ours.id) not in text
    assert "[Other Organisation]" in text


@pytest.mark.parametrize(
    "role", ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"]
)
def test_the_export_pages_follow_the_role_matrix(
    sample: Sample, fleet: dict[str, Aircraft], role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    refusals = 0
    for method, path, action in addresses(fleet):
        status = call(client, method, path).status_code
        if permitted(user.roles, action):
            assert status == 200, f"{role} {method} {path}"
        else:
            assert status == 403, f"{role} {method} {path}"
            refusals += 1
    with working_for(sample.ours.id, user.id):
        logged = AccessEntry.objects.filter(user=user, kind="Action Refused").count()
    assert logged == refusals
    assert refusals == (3 if role == "Read Only" else 0)


def test_the_export_pages_need_sign_in_and_refuse_forged_requests(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    anonymous = Client()
    for method, path, _ in addresses(fleet):
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.lucy, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in addresses(fleet):
        if method == "POST":
            assert post(forged, path).status_code == 403, path
    with working_for(sample.ours.id, sample.lucy.id):
        assert AccessEntry.objects.filter(kind="Records Exported").count() == 0
