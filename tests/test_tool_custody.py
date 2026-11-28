"""Acceptance of separate custody, use, return and release evidence."""

from datetime import date
from decimal import Decimal
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from django.test import Client

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts import services as orders
from airworthiness_plus.contracts.models import OrderedBy
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning import services as planning
from airworthiness_plus.planning.models import WorkCard
from airworthiness_plus.releases.models import Release
from airworthiness_plus.tooling.release_evidence import Verification
from tests.support import TODAY, Sample, add_sample_fleet, get, post, signed_in
from tests.test_tooling import basis, event, register

pytestmark = pytest.mark.django_db


@pytest.fixture
def job(sample: Sample, monkeypatch: pytest.MonkeyPatch) -> tuple[WorkCard, Person]:
    return make_job(sample, monkeypatch, add_sample_fleet(sample)["G-EJKL"])


def make_job(
    sample: Sample, monkeypatch: pytest.MonkeyPatch, aircraft: Aircraft
) -> tuple[WorkCard, Person]:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    with working_for(sample.ours.pk, sample.planner.pk):
        order = orders.add_work_order(
            aircraft, work="Check the fixture", ordered_by=OrderedBy.MANAGER, agreed_on=TODAY
        )
        package = planning.build_package(
            aircraft,
            reference="WP-TEST-CUSTODY",
            title=order.work,
            location="Hangar",
            starts_on=TODAY,
            ends_on=TODAY,
        )
        planning.link_order(package, order)
        manual = data.record_data(
            organisation=sample.ours,
            title="Fictitious tooling instruction",
            author="Fictitious design organisation",
            kind=Kind.INSTRUCTIONS,
            revision="2",
            revision_date=TODAY,
            check_due=TODAY,
        )
        card = planning.add_card(
            package,
            title=order.work,
            data_set=manual,
            instruction="Fictitious task 01",
            planned_hours=Decimal("1.0"),
        )
        planning.issue_package(package, approval="Part-CAO")
        card.refresh_from_db()
        return card, Person.objects.get(user=sample.lucy)


def submit(who: Client, path: str, **values: str) -> str:
    response = post(who, path, **values)
    assert response.status_code == 302, response.content[:3000]
    return urlsplit(response["Location"]).path


def grant(admin: Client, person: Person, action: str) -> None:
    submit(
        admin,
        "/tools/delegations/add/",
        request_id=str(uuid4()),
        approval="Part-CAO",
        person=str(person.pk),
        action=action,
        site="Hangar",
        starts_on="2026-11-18",
        ends_on="2026-12-31",
        procedure="Fictitious CAE revision 1, C.3",
        authority="Fictitious signed tooling scope",
    )


def test_issue_actual_use_and_adverse_return_are_separate(
    sample: Sample, job: tuple[WorkCard, Person]
) -> None:
    exercise_custody(sample, *job)


def exercise_custody(sample: Sample, card: WorkCard, user: Person) -> None:
    admin, writer = signed_in(sample.administrator), signed_in(sample.lucy)
    for action in ("Register", "Control", "Issue", "Use", "Return"):
        grant(admin, user, action)
    tool = register(writer, "TEST-ADAPTER", "Fictitious adapter")
    fields = {
        "package": str(card.package_id),
        "custodian": str(user.pk),
        "location": "Hangar bench",
        "evidence": "Fictitious handover reference",
    }
    assert (
        b"Control basis" in post(writer, tool + "issue/", request_id=str(uuid4()), **fields).content
    )
    basis(writer, tool, "Before each use")
    token = str(uuid4())
    issue = submit(writer, tool + "issue/", request_id=token, **fields)
    assert issue == submit(writer, tool + "issue/", request_id=token, **fields)
    result = post(writer, tool + "issue/", request_id=str(uuid4()), **fields)
    assert result.status_code == 200 and b"open issue" in result.content

    use_fields = {
        "card": str(card.pk),
        "revision": str(card.revision_id),
        "evidence": "Fictitious signed work evidence",
        "configuration": "Fixture orientation",
    }
    result = post(writer, issue + "use/", request_id=str(uuid4()), **use_fields)
    assert result.status_code == 200 and b"pre-use inspection" in result.content
    submit(
        writer,
        issue + "inspect/",
        request_id=str(uuid4()),
        card=str(card.pk),
        revision=str(card.revision_id),
        passed="on",
        evidence="Fictitious lot and condition checked",
    )
    from airworthiness_plus.tooling.custody_models import ToolPreUseInspection

    with working_for(sample.ours.pk, sample.lucy.pk):
        inspection = ToolPreUseInspection.objects.get()
    submit(
        writer, issue + "use/", request_id=str(uuid4()), inspection=str(inspection.pk), **use_fields
    )
    result = post(
        writer, issue + "use/", request_id=str(uuid4()), inspection=str(inspection.pk), **use_fields
    )
    assert result.status_code == 200 and b"already been used" in result.content
    submit(
        writer,
        issue + "return/",
        request_id=str(uuid4()),
        returned_by=str(user.pk),
        location="Quarantine shelf",
        condition="Unserviceable",
        evidence="Fictitious damaged adaptor",
    )
    result = post(writer, tool + "issue/", request_id=str(uuid4()), **fields)
    assert result.status_code == 200 and b"unserviceable" in result.content
    assert b"Quarantine shelf" in get(writer, issue).content
    assert b"Unserviceable" in get(writer, tool).content
    assert get(signed_in(sample.stranger), issue).status_code == 404
    package = get(writer, f"/work-packages/{card.package_id}/").content
    assert b"Fictitious signed work evidence" in package
    submit(
        writer,
        tool + "claim/",
        request_id=str(uuid4()),
        occurred_on="2026-09-12",
        card=str(card.pk),
        attributed_to="Named fictitious mechanic",
        subject="Fictitious test aircraft",
        claim="A previous use was reported",
        source="Fictitious worksheet",
        gaps="Historical custody unconfirmed",
    )


def test_prospective_package_release_requires_separate_signed_verification(
    sample: Sample, job: tuple[WorkCard, Person]
) -> None:
    card, _ = job
    exercise_release(sample, card)


def exercise_release(sample: Sample, card: WorkCard) -> None:
    with working_for(sample.ours.pk, sample.planner.pk):
        certifier = Person.objects.get(full_name="Sam Patel")
        authority = people_services.record_maintenance_authorisation(
            certifier,
            scope="Fictitious aircraft release",
            valid_from=TODAY,
            reference="WP-TEST-CUSTODY",
        )
        planning.record_completion(
            card,
            performed_by=certifier,
            completed_on=TODAY,
            sign_off_reference="Fictitious signed card",
            hours=Decimal("9874.3"),
            cycles=0,
        )
        with pytest.raises(planning.RefusedError, match=r"[Gg]eneral verification"):
            planning.release_package(
                card.package,
                reference="TEST-CUSTODY-RELEASE",
                issued_by=certifier,
                issued_on=TODAY,
                maintenance_authorisation=authority,
                scope_confirmed=True,
                verification="A general note alone",
            )
        assert not Release.objects.filter(reference="TEST-CUSTODY-RELEASE").exists()
        planning.release_package(
            card.package,
            reference="TEST-CUSTODY-RELEASE",
            issued_by=certifier,
            issued_on=TODAY,
            maintenance_authorisation=authority,
            scope_confirmed=True,
            verification="Signed fixture clearance",
            general_verification=Verification(
                "",
                TODAY,
                True,
                "None removed",
                "Signed fixture clearance",
                "Fixture register reconciled",
            ),
        )
        release = Release.objects.get(reference="TEST-CUSTODY-RELEASE")
        assert release.general_verification.rule == "CAO.A.060(i)"
        assert release.approval_reference == release.general_verification.approval_reference
        assert release.general_verification.accountability == "Fixture register reconciled"


def test_expired_tool_cannot_be_used_but_can_be_returned(
    sample: Sample, job: tuple[WorkCard, Person], monkeypatch: pytest.MonkeyPatch
) -> None:
    card, user = job
    with working_for(sample.ours.pk, sample.planner.pk):
        data.record_check(
            card.data_set,
            checked_by=sample.planner,
            checked_on=TODAY,
            result="Confirmed current from the fictitious amendment source",
            next_due=date(2026, 12, 30),
        )
    admin, writer = signed_in(sample.administrator), signed_in(sample.lucy)
    for action in ("Register", "Control", "Evidence", "Issue", "Use", "Return"):
        grant(admin, user, action)
    tool = register(writer, "TEST-SERVICE-TOOL", "Fictitious serviced tool")
    basis(writer, tool, "Servicing", "1")
    assert event(writer, tool, "Servicing completed", TODAY.isoformat()) == 302
    issue = submit(
        writer,
        tool + "issue/",
        request_id=str(uuid4()),
        package=str(card.package_id),
        custodian=str(user.pk),
        location="Fixture bench",
        evidence="Fictitious handover",
    )
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2026, 12, 19))
    refused = post(
        writer,
        issue + "use/",
        request_id=str(uuid4()),
        card=str(card.pk),
        revision=str(card.revision_id),
        configuration="Test orientation",
        evidence="Test setting",
    )
    assert refused.status_code == 200 and b"outstanding and overdue controls" in refused.content
    submit(
        writer,
        issue + "return/",
        request_id=str(uuid4()),
        returned_by=str(user.pk),
        location="Stores bench",
        condition="Satisfactory",
        evidence="Fictitious return after the due date",
    )
    assert b"Fictitious return after the due date" in get(writer, issue).content
