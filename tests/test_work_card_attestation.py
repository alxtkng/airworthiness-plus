"""Synthetic work card completion attestation through the normal form."""

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.db import DatabaseError
from django.urls import reverse

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.middleware import VERIFIED_AT_KEY
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.contracts import services as contract_services
from airworthiness_plus.contracts.models import OrderedBy
from airworthiness_plus.exports.build import build
from airworthiness_plus.exports.verify import verify
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person, StaffGroup
from airworthiness_plus.planning import services, signing_provider
from airworthiness_plus.planning.models import (
    SigningState,
    WorkCard,
    WorkCardAttestation,
    WorkCardSigningJob,
)
from tests.support import TODAY, Sample, add_sample_fleet, get, make_sample, post, signed_in

pytestmark = pytest.mark.django_db


def _draft_card(
    settings: Any, monkeypatch: pytest.MonkeyPatch, *, steps: str = ""
) -> tuple[Sample, WorkCard]:
    settings.SYNTHETIC_WORK_CARD_ATTESTATION = True
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    sample = make_sample()
    aircraft = add_sample_fleet(sample)["G-DGHI"]
    with working_for(sample.ours.id, sample.administrator.id):
        Person.objects.filter(user=sample.planner).update(staff_group=StaffGroup.CERTIFYING)
    with working_for(sample.ours.id, sample.planner.id):
        package = services.build_package(
            aircraft,
            reference="WP-SYNTHETIC-COMPLETION-1",
            title="Synthetic Functional Check",
            location="Training Bench",
            starts_on=TODAY,
            ends_on=TODAY,
        )
        order = contract_services.add_work_order(
            aircraft, work=package.title, ordered_by=OrderedBy.MANAGER, agreed_on=TODAY
        )
        services.link_order(package, order)
        manual = data_services.record_data(
            organisation=sample.ours,
            title="Synthetic Training Instructions",
            author="Training Team",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="1",
            revision_date=TODAY,
            check_due=TODAY,
        )
        card = services.add_card(
            package,
            title="Check Indicator",
            data_set=manual,
            instruction="Synthetic step 1",
            planned_hours=Decimal("1.0"),
            critical=True,
            structured_steps=steps,
        )
    return sample, card


@pytest.fixture
def completed_card(settings: Any, monkeypatch: pytest.MonkeyPatch) -> tuple[Sample, WorkCard]:
    sample, card = _draft_card(settings, monkeypatch)
    with working_for(sample.ours.id, sample.planner.id):
        services.issue_package(card.package)
        services.record_completion(
            card,
            performed_by=Person.objects.get(user=sample.planner),
            completed_on=TODAY,
            sign_off_reference="SYNTHETIC-SOURCE",
            hours=Decimal("0.0"),
            cycles=0,
        )
    return sample, card


def add_grant(
    sample: Sample, card: WorkCard, *, valid_to: date | None = None, type_rating: str = ""
) -> MaintenanceAuthorisation:
    with working_for(sample.ours.id, sample.administrator.id):
        rating = type_rating or card.package.aircraft.type_rating
        return people_services.record_maintenance_authorisation(
            Person.objects.get(user=sample.planner),
            reference=f"SYNTHETIC-GRANT-{valid_to or rating}",
            scope=MaintenanceAuthorisation.SYNTHETIC_COMPLETION_SCOPE + rating,
            valid_from=TODAY - timedelta(days=2),
            valid_to=valid_to,
        )


def path_for(card: WorkCard) -> str:
    return reverse("attest_work_card", args=[card.package_id, card.pk])


def test_consent_archives_exact_version_once_and_exports_it(
    completed_card: tuple[Sample, WorkCard],
) -> None:
    sample, card = completed_card
    grant = add_grant(sample, card)
    client, path = signed_in(sample.planner), path_for(card)
    opened = client.get(path, secure=True)
    assert opened.status_code == 200
    assert opened.context["content"]["inspection_status"] == "Pending"
    token = opened.context["intent"]
    assert post(client, path, intent=token).status_code == 409
    assert post(client, path, consent="yes", intent=token + "x").status_code == 409
    assert post(client, path, consent="yes", intent=token).status_code == 302
    job = client.get(path, secure=True).context["job"]
    assert job.status == SigningState.PENDING
    assert post(client, path, command="check", job=job.pk).status_code == 302
    assert client.get(path, secure=True).context["job"].status == SigningState.SIGNED
    assert post(client, path, command="check", job=job.pk).status_code == 302
    assert client.get(path, secure=True).context["job"].status == SigningState.SIGNED
    assert post(client, path, command="archive", job=job.pk).status_code == 302
    assert post(client, path, command="archive", job=job.pk).status_code == 302
    assert post(client, path, consent="yes", intent=token).status_code == 302

    with working_for(sample.ours.id, sample.planner.id):
        record = WorkCardAttestation.objects.get(card=card)
        card.refresh_from_db()
        reviewed = Event.of(card).last()
        assert reviewed is not None
        assert len(Event.of(record)) == 1
        job.refresh_from_db()
        assert [json.loads(event.after_json or "{}")["status"] for event in Event.of(job)] == [
            SigningState.PENDING,
            SigningState.SIGNED,
            SigningState.ARCHIVED,
        ]
        assert job.document == record.evidence
        assert job.sha256 == record.sha256
        assert job.result["signer"] == str(sample.planner.pk)
        evidence = json.loads(record.evidence)
        assert evidence["reviewed_content"] == opened.context["content"]
        assert evidence["reviewed_content"]["card_version_hash"] == reviewed.hash
        assert hashlib.sha256(record.evidence.encode()).hexdigest() == record.sha256
        archive = build(sample.ours, by=sample.planner, aircraft=card.package.aircraft)
        assert verify(archive.content).problems == ()
        with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
            retained = json.loads(bundle.read("records/planning_workcardattestation.json"))
            assert retained[0]["evidence"] == record.evidence
            assert retained[0]["sha256"] == record.sha256
            [request] = json.loads(bundle.read("records/planning_workcardsigningjob.json"))
            assert request["archive_id"] == str(record.pk)
            assert request["document"] == record.evidence
            assert request["result"] == job.result
            people = json.loads(bundle.read("people.json"))
            assert str(grant.pk) in {grant["id"] for grant in people["maintenance_authorisations"]}
        assert not card.signed
        assert card.package.release_id is None
        with pytest.raises(people_services.RefusedError, match="Synthetic Authorisation"):
            people_services.check_certification_evidence(
                person=grant.person,
                on=TODAY,
                today=TODAY,
                authorisation=grant,
                scope_confirmed=True,
                legacy_evidence="",
            )

    with working_for(sample.other.id, sample.stranger.id):
        assert not WorkCardAttestation.objects.filter(pk=record.pk).exists()


def test_authority_identity_verification_and_changed_version(
    completed_card: tuple[Sample, WorkCard], settings: Any
) -> None:
    sample, card = completed_card
    client, path = signed_in(sample.planner), path_for(card)
    settings.SYNTHETIC_WORK_CARD_ATTESTATION = False
    assert get(client, path).status_code == 404
    settings.SYNTHETIC_WORK_CARD_ATTESTATION = True
    add_grant(sample, card, valid_to=TODAY - timedelta(days=1))
    add_grant(sample, card, type_rating="Different type")
    refusal = get(client, path)
    assert refusal.status_code == 409
    assert b"No Current Synthetic Authorisation" in refusal.content
    add_grant(sample, card)
    assert get(signed_in(sample.stranger), path).status_code == 404
    assert get(signed_in(sample.reader), path).status_code == 403
    token = client.get(path, secure=True).context["intent"]
    assert post(signed_in(sample.lucy), path, consent="yes", intent=token).status_code == 409
    session = client.session
    session[VERIFIED_AT_KEY] = (sign_in.current_time() - timedelta(minutes=6)).isoformat()
    session.save()
    prompt = post(client, path, consent="yes", intent=token)
    assert b"Verify your identity" in prompt.content
    assert get(client, "/work-packages/").status_code == 200  # Cancel.
    with working_for(sample.ours.id, sample.planner.id):
        assert not WorkCardAttestation.objects.exists()
        services.record_inspection(
            card,
            inspector=Person.objects.get(full_name="Chris Moore"),
            inspected_on=TODAY,
            qualification="Synthetic inspection authority",
            evidence="Synthetic result satisfactory",
        )
    client = signed_in(sample.planner)
    assert b"The Evidence Has Changed" in post(client, path, consent="yes", intent=token).content
    fresh = client.get(path, secure=True)
    assert fresh.context["content"]["inspection_status"] == "Recorded"
    assert post(client, path, consent="yes", intent=fresh.context["intent"]).status_code == 302


def test_failed_archive_write_rolls_back_and_retries(
    completed_card: tuple[Sample, WorkCard], monkeypatch: pytest.MonkeyPatch
) -> None:
    sample, card = completed_card
    add_grant(sample, card)
    client, path = signed_in(sample.planner), path_for(card)
    token = client.get(path, secure=True).context["intent"]
    assert post(client, path, consent="yes", intent=token).status_code == 302
    job = client.get(path, secure=True).context["job"]
    assert post(client, path, command="check", job=job.pk).status_code == 302
    manager = WorkCardAttestation.objects
    create = manager.create

    def fail_after_insert(**values: Any) -> None:
        create(**values)
        raise DatabaseError("Synthetic interruption after audit trigger")

    with monkeypatch.context() as patch:
        patch.setattr(manager, "create", fail_after_insert)
        assert post(client, path, command="archive", job=job.pk).status_code == 302
        response = client.get(path, secure=True)
        assert b"The archive write failed" in response.content
        assert response.context["job"].status == SigningState.SIGNED
    with working_for(sample.ours.id, sample.planner.id):
        assert not manager.exists()
        assert not Event.objects.filter(record_type="planning_workcardattestation").exists()
        services.record_inspection(
            card,
            inspector=Person.objects.get(full_name="Chris Moore"),
            inspected_on=TODAY,
            qualification="Synthetic inspection authority",
            evidence="Synthetic result satisfactory",
        )
    assert post(client, path, command="archive", job=job.pk).status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        archive = manager.get(card=card)
        assert len(Event.of(archive)) == 1
        assert json.loads(archive.evidence)["reviewed_content"]["inspection_status"] == "Pending"
        assert WorkCardSigningJob.objects.get(pk=job.pk).status == SigningState.ARCHIVED


@pytest.mark.parametrize(
    "case, expected",
    [
        ("delay", SigningState.PENDING),
        ("decline", SigningState.DECLINED),
        ("document", SigningState.REJECTED),
        ("signer", SigningState.REJECTED),
        ("proof", SigningState.REJECTED),
        ("cancel", SigningState.CANCELLED),
        ("stale", SigningState.STALE),
    ],
)
def test_pending_job_result_or_cancellation(
    completed_card: tuple[Sample, WorkCard],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    expected: SigningState,
) -> None:
    class Provider(signing_provider.SyntheticProvider):
        def check(self, request: signing_provider.Request) -> signing_provider.Result:
            if case == "delay":
                return signing_provider.Result("pending")
            if case == "decline":
                return signing_provider.Result("declined", reference=request.reference)
            if case == "signer":
                return super().check(replace(request, signer="someone-else"))
            if case == "document":
                return super().check(replace(request, sha256="0" * 64))
            if case == "proof":
                return replace(super().check(request), proof="invalid")
            return super().check(request)

    monkeypatch.setattr(signing_provider, "provider", Provider)
    sample, card = completed_card
    add_grant(sample, card)
    client, path = signed_in(sample.planner), path_for(card)
    opened = client.get(path, secure=True)
    assert post(client, path, consent="yes", intent=opened.context["intent"]).status_code == 302
    job = client.get(path, secure=True).context["job"]
    if case == "stale":
        with working_for(sample.ours.id, sample.planner.id):
            services.record_inspection(
                card,
                inspector=Person.objects.get(full_name="Chris Moore"),
                inspected_on=TODAY,
                qualification="Synthetic inspection authority",
                evidence="Synthetic result satisfactory",
            )
    if case == "cancel":
        assert post(client, path, command="cancel", job=job.pk).status_code == 302
    assert post(client, path, command="check", job=job.pk).status_code == 302
    assert client.get(path, secure=True).context["job"].status == expected
    with working_for(sample.ours.id, sample.planner.id):
        assert not WorkCardAttestation.objects.filter(card=card).exists()


def test_structured_steps_pin_revision_and_require_independent_inspection(
    settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample, card = _draft_card(
        settings, monkeypatch, steps="Check training fixture\n*Check independent return"
    )
    performer_grant = add_grant(sample, card)
    with working_for(sample.ours.id, sample.planner.id):
        services.issue_package(card.package)
        card.refresh_from_db()
        assert card.revision_id == card.structured_revision_id
    performer = signed_in(sample.planner)
    package_path = reverse("work_package", args=[card.package_id])
    completion_path = reverse("complete_work_card", args=[card.package_id, card.pk])
    inspection_path = reverse("inspect_work_card", args=[card.package_id, card.pk])
    step_paths = [
        reverse("sign_work_card_step", args=[card.package_id, card.pk, number]) for number in (1, 2)
    ]
    assert b"Sign Step 1" in get(performer, package_path).content
    assert b"Sign Step 2" not in get(performer, package_path).content
    assert get(signed_in(sample.stranger), step_paths[0]).status_code == 404
    result = {"evidence": "Fixture return completed", "consent": "on"}
    assert b"Sign Each Step Once" in post(performer, step_paths[1], **result).content
    assert post(performer, step_paths[0], **result).status_code == 302
    completion = {
        "revision": str(card.revision_id),
        "completed_on": TODAY.isoformat(),
        "performed_by": str(performer_grant.person_id),
        "sign_off_reference": "SYNTHETIC-COMPLETE",
        "hours": "0.0",
        "cycles": "0",
    }
    assert b"Every Structured Step Needs" in post(performer, completion_path, **completion).content
    assert post(performer, step_paths[1], **result).status_code == 302
    assert post(performer, completion_path, **completion).status_code == 302
    assert b"1 Outstanding" in get(performer, package_path).content
    inspection = {
        "inspector": str(performer_grant.person_id),
        "inspected_on": TODAY.isoformat(),
        "qualification": "Synthetic independent inspection training",
        "evidence": "Verified expected return",
    }
    assert b"Did Not Do or Supervise" in post(performer, inspection_path, **inspection).content
    with working_for(sample.ours.id, sample.administrator.id):
        inspector = Person.objects.get(user=sample.lucy)
        inspector.staff_group = StaffGroup.CERTIFYING
        inspector.save(update_fields=["staff_group"])
        inspector_grant = people_services.record_maintenance_authorisation(
            inspector,
            reference="SYNTHETIC-INSPECTION",
            scope=MaintenanceAuthorisation.SYNTHETIC_COMPLETION_SCOPE
            + "independent inspection: "
            + card.package.aircraft.type_rating,
            valid_from=TODAY,
        )
    inspection["inspector"] = str(inspector.pk)
    assert b"Sign In as the Named Person" in post(performer, inspection_path, **inspection).content
    assert post(signed_in(sample.lucy), inspection_path, **inspection).status_code == 302
    assert b"None Outstanding" in get(performer, package_path).content
    assert b"SYNTHETIC-INSPECTION" in get(performer, package_path).content
    preview = performer.get(path_for(card), secure=True).context["content"]
    assert len(preview["steps"]) == 2
    assert preview["steps"][1]["critical"]
    assert preview["inspection_authorisation_id"] == str(inspector_grant.pk)

    with working_for(sample.ours.id, sample.planner.id):
        card.refresh_from_db()
        assert card.performed_revision_id == card.structured_revision_id
        assert card.inspection_authorisation_id == inspector_grant.pk
        archive = build(sample.ours, by=sample.planner, aircraft=card.package.aircraft)
        assert verify(archive.content).problems == ()
        with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
            retained = json.loads(bundle.read("records/planning_workcardstepsignoff.json"))
            assert sorted(item["number"] for item in retained) == [1, 2]
            assert {item["authorisation_id"] for item in retained} == {str(performer_grant.pk)}
            people = json.loads(bundle.read("people.json"))
            assert {str(inspector_grant.pk), str(performer_grant.pk)} <= {
                grant["id"] for grant in people["maintenance_authorisations"]
            }


@pytest.mark.parametrize("after_issue", [False, True])
def test_superseded_structured_source_refuses_issue_or_step(
    settings: Any, monkeypatch: pytest.MonkeyPatch, after_issue: bool
) -> None:
    sample, card = _draft_card(settings, monkeypatch, steps="*Check training fixture")
    add_grant(sample, card)
    with working_for(sample.ours.id, sample.planner.id):
        if after_issue:
            services.issue_package(card.package)
        data_services.add_revision(card.data_set, revision="2", revision_date=TODAY)
        with pytest.raises(services.RefusedError, match="Superseded"):
            if after_issue:
                services.sign_step(card, sample.planner, 1, "Training fixture checked")
            else:
                services.issue_package(card.package)
