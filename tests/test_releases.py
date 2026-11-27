"""Certificates of release to service (REQ-260 to REQ-268).

The Release to Service board, with the sample of
design-system/SampleData.md. Today in the sample is 18 November 2026.
ML.A.801 and ML.A.803 were read in the UK text on 27 November 2026
(Decisions.md, Regulation Facts in Use).

By hand, for 18 November 2026:

- G-ABCD's right main tyre was replaced by the pilot-owner on 22 October
  2026, 27 days ago. Its release is not in the records: 30 days, by
  21 November 2026 (ML.A.305(a)). The organisation was told on 23 October.
- G-CDEF's 100-hour check and spinner replacement were completed on
  4 November 2026, 14 days ago, released by Chris Moore and entered in the
  records on 5 November.
- So 3 were issued in the last 30 days and 1 is not yet in the records.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.utils import DatabaseError
from django.test.utils import CaptureQueriesContext

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.defects import services as defect_services
from airworthiness_plus.defects.models import Decision
from airworthiness_plus.history.models import Event, RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations import configuration
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.releases import services
from airworthiness_plus.releases.models import IssuedBy, Release
from airworthiness_plus.sample import build, phase1
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, get, make_sample, page, post, signed_in
from tests.test_defects import Day, tables

pytestmark = pytest.mark.django_db


@pytest.fixture
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    chosen = Day()
    monkeypatch.setattr(aircraft_services, "today", lambda: chosen.today)
    return chosen


@pytest.fixture
def sample(day: Day) -> Sample:
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = build.add_fleet(sample)
    build.add_other_work(sample, fleet)
    return fleet


@pytest.fixture
def releases(sample: Sample, fleet: dict[str, Aircraft]) -> list[Release]:
    return phase1.add_releases(sample.ours, sample.planner, fleet)


def person(sample: Sample, name: str) -> Person:
    with working_for(sample.ours.id, sample.reader.id):
        return Person.objects.get(full_name=name)


def tyre(sample: Sample) -> WorkDone:
    with working_for(sample.ours.id, sample.reader.id):
        return WorkDone.objects.get(description="Right Main Tyre Replaced")


def work_on(sample: Sample, aircraft: Aircraft, **values: Any) -> WorkDone:
    """Record other work on an aircraft, on 10 November 2026 unless told otherwise."""
    given: dict[str, Any] = {
        "description": "[Work]",
        "dated": date(2026, 11, 10),
        "hours": Decimal("100.0"),
        "cycles": 0,
    }
    given.update(values)
    with working_for(sample.ours.id, sample.planner.id):
        return programme_services.record_work(aircraft, **given)


def record(sample: Sample, work: WorkDone, **values: Any) -> Release:
    given: dict[str, Any] = {
        "reference": "[Reference]",
        "kind": IssuedBy.INDEPENDENT,
        "issuer_name": "[Independent Name]",
        "issued_on": work.dated,
    }
    given.update(values)
    with working_for(sample.ours.id, sample.planner.id):
        return services.record_certificate(work, **given)


PILOT = {
    "reference": "[Logbook Entry]",
    "kind": "Pilot-Owner",
    "issuer_name": "[Owner Name G-ABCD]",
    "licence": "[Number]",
    "issued_on": "2026-10-22",
}

# The sample

LISTED = [
    ["G-ABCD", "Right Main Tyre Replaced, Pilot-Owner Maintenance", "Pilot-Owner",
     "22 October 2026", "Due 21 November 2026", "Due Soon", "", "", "", "", "23 October 2026"],
    ["G-CDEF", "100-Hour Check", "Chris Moore, Certifying Staff", "4 November 2026",
     "5 November 2026", "", "None", "UK.CAO.[Number], Part-66 B1.2",
     "[Release Reference WP-2026-043]", "4 November 2026", ""],
    ["G-CDEF", "Propeller Spinner Replaced", "Chris Moore, Certifying Staff", "4 November 2026",
     "5 November 2026", "", "None", "UK.CAO.[Number], Part-66 B1.2",
     "[Release Reference WP-2026-043]", "4 November 2026", ""],
]  # fmt: skip


def test_the_release_to_service_page_of_the_sample_on_18_november_2026(
    sample: Sample, releases: list[Release]
) -> None:
    """REQ-264. Golden, from the Release to Service board: what is not yet in the
    records first, then what was completed in the last 30 days, with the counts."""
    body = page(signed_in(sample.reader), "/release-to-service/")
    listed, who = tables(body)
    assert [row[:11] for row in listed] == LISTED
    assert (
        "<p>2 Issued, Last 30 Days, 1 Not Yet in Records, 0 Incomplete Maintenance, "
        "0 Pilot-Owner Notice Overdue</p>" in body
    )
    assert "<p>In Records Within 30 Days of Completion, ML.A.305(a)</p>" in body
    assert body.count(dot("Due Soon")) == 1
    # How the 30 days were worked out is on the page (REQ-139).
    assert "How the Release by 21 November 2026 Was Calculated" in listed[0][11]
    assert [row[0] for row in who] == [
        "Organisation Certifying Staff",
        "Independent Certifying Staff",
        "Pilot-Owner",
    ]
    assert [row[3] for row in who] == [
        "ML.A.801(b)(1), ML.A.801(e)(3)",
        "ML.A.801(b)(2), ML.A.801(e)(3)",
        "ML.A.801(b)(3), ML.A.803, Appendices I and II to Part-ML",
    ]
    assert "<li>Continuing Airworthiness</li>" in body
    assert (
        '<li><a href="/release-to-service/" aria-current="location">Release to Service</a></li>'
        in body
    )


def test_what_is_listed_and_counted_as_days_pass(
    sample: Sample, releases: list[Release], day: Day
) -> None:
    """REQ-264. The tyre's release is Due on 21 November and Overdue on 22 November,
    and stays listed until it is in the records. G-CDEF's work of 4 November is
    listed up to 4 December, 30 days on, and not on 5 December."""
    reader = signed_in(sample.reader)

    def listed() -> tuple[list[list[str]], str]:
        body = page(reader, "/release-to-service/")
        counts = re.search(r"<p>(\d+ Issued[^<]*)</p>", body)
        assert counts is not None
        return tables(body)[0], counts.group(1)

    day.today = date(2026, 11, 21)
    assert listed()[0][0][4:6] == ["Due 21 November 2026", "Due"]
    day.today = date(2026, 11, 22)
    rows, counts = listed()
    assert rows[0][4:6] == ["Due 21 November 2026", "Overdue"]
    # The tyre was completed 31 days ago: no longer among those issued in 30 days.
    assert counts.startswith("2 Issued, Last 30 Days, 1 Not Yet in Records")
    day.today = date(2026, 12, 4)
    assert [row[0] for row in listed()[0]] == ["G-ABCD", "G-CDEF", "G-CDEF"]
    day.today = date(2026, 12, 5)
    rows, counts = listed()
    assert [row[0] for row in rows] == ["G-ABCD"]
    assert counts.startswith("0 Issued, Last 30 Days, 1 Not Yet in Records")


# Recording a certificate


def test_a_pilot_owners_certificate_is_recorded_and_enters_the_records(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-260, REQ-263, ML.A.803(d). Recording the certificate for the tyre enters
    the release in the records that day, and the page no longer shows it as due."""
    work = tyre(sample)
    planner = signed_in(sample.planner)
    path = f"/release-to-service/{work.id}/record/"
    assert "<dd>Right Main Tyre Replaced, Pilot-Owner Maintenance</dd>" in page(planner, path)
    response = post(planner, path, **PILOT)
    assert response.status_code == 302, response.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        release = Release.objects.get()
        work.refresh_from_db()
        entries = list(Event.of(release))
    assert (work.release_reference, work.release_recorded_on) == ("[Logbook Entry]", TODAY)
    assert (release.issued_by_text, release.identity_text, release.point) == (
        "[Owner Name G-ABCD], Pilot-Owner",
        "Licence [Number]",
        "ML.A.801(b)(3), ML.A.803",
    )
    assert (release.registration, release.maintenance, release.completed_on) == (
        "G-ABCD",
        "Right Main Tyre Replaced",
        date(2026, 10, 22),
    )
    assert [(entry.action, entry.actor_name) for entry in entries] == [
        ("Created", "[Planning and Records Name]")
    ]
    (rows, _) = tables(page(planner, "/release-to-service/"))
    assert rows[0][2:7] == [
        "[Owner Name G-ABCD], Pilot-Owner",
        "22 October 2026",
        "18 November 2026",
        "",
        "None",
    ]
    again = post(planner, path, **PILOT)
    assert "The Certificate for This Work Is Already Recorded" in again.content.decode()


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ({"reference": " "}, "This field is required"),
        ({"kind": "[Anyone]"}, "Select a valid choice"),
        ({"issued_on": "2026-11-19"}, "Not Issued After Today"),
        ({"issued_on": "2026-10-21"}, "Not Issued Before the Work Was Completed"),
        ({"issued_on": "2026-11-10", "recorded_on": "2026-11-09"}, "On or After the Day It Was"),
        ({"recorded_on": "2026-11-19"}, "and Not After Today"),
        ({"kind": "Independent Certifying Staff"}, "Released by the Pilot-Owner"),
        ({"kind": "Organisation Certifying Staff"}, "Released by the Pilot-Owner"),
        ({"issuer_name": " "}, "Names Who Issued It, ML.A.801(e)(3)"),
        ({"licence": ""}, "Gives the Pilot Licence Number, ML.A.803(d)"),
        ({"incomplete": "on"}, "With Its Limitations Stated, ML.A.801(f)"),
    ],
)
def test_what_cannot_be_true_of_a_certificate_is_refused(
    sample: Sample, fleet: dict[str, Aircraft], values: dict[str, str], reason: str
) -> None:
    """REQ-260, REQ-263. Said on the page, with nothing recorded and no release entered."""
    work = tyre(sample)
    response = post(
        signed_in(sample.lucy), f"/release-to-service/{work.id}/record/", **{**PILOT, **values}
    )
    assert response.status_code == 200
    assert reason in response.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert Release.objects.count() == 0
        assert WorkDone.objects.get(pk=work.pk).release_reference == ""


def test_who_issues_a_certificate_for_the_organisation(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-262, ML.A.801(b)(1). Certifying staff of the organisation, named from the
    staff, who had not left by the day of issue; nobody else is chosen from the staff."""
    work = work_on(sample, fleet["G-EJKL"])
    sam, ellie = person(sample, "Sam Patel"), person(sample, "Ellie Ward")
    lucy = signed_in(sample.lucy)
    path = f"/release-to-service/{work.id}/record/"
    form = {"reference": "[Reference]", "issued_on": "2026-11-10"}
    staff = {**form, "kind": "Organisation Certifying Staff"}
    for values, reason in (
        (staff, "Certifying Staff Who Issue a Certificate Are Named"),
        ({**staff, "issued_by": str(ellie.id)}, "Select a valid choice"),
        ({**staff, "issued_by": str(sam.id), "licence": "[Typed]"}, "Come From Their Record"),
        (
            {**form, "kind": "Independent Certifying Staff", "issuer_name": "[Name]",
             "issued_by": str(sam.id)},
            "Only Certifying Staff of the Organisation Are Chosen",
        ),
        ({**form, "kind": "Pilot-Owner", "issuer_name": "[Name]", "licence": "[Number]"},
         "Released by the Pilot-Owner"),
    ):  # fmt: skip
        refused = post(lucy, path, **values)
        assert refused.status_code == 200 and reason in refused.content.decode(), values
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(services.RefusedError, match="Is Not Certifying Staff"):
            services.record_certificate(
                work,
                reference="[Reference]",
                kind=IssuedBy.ORGANISATION,
                issued_by=ellie,
                issued_on=work.dated,
            )
    # Sam Patel left on 9 November: a certificate of 10 November is not his.
    with working_for(sample.ours.id, sample.administrator.id):
        people_services.change_person(
            sam,
            full_name=sam.full_name,
            role=sam.role,
            staff_group=StaffGroup.CERTIFYING,
            reports_to=sam.reports_to,
            employment=Employment(sam.employment),
            licence=sam.licence,
            joined_on=None,
            left_on=date(2026, 11, 9),
            by=sample.administrator,
        )
    left = post(lucy, path, **staff, issued_by=str(sam.id))
    assert "Had Left by the Day of Issue" in left.content.decode()
    chris = person(sample, "Chris Moore")
    assert (
        post(
            lucy, path, **staff, issued_by=str(chris.id), legacy_evidence="[Signed Certificate]"
        ).status_code
        == 302
    )
    assert "Unverified Historical Evidence, [Signed Certificate]" in page(
        signed_in(sample.reader), "/release-to-service/"
    )
    # An independent certificate may have no licence number: ML.A.801(e)(3), if applicable.
    other = work_on(sample, fleet["G-EJKL"], description="[Other Work]")
    assert record(sample, other).identity_text == ""


def test_an_organisation_that_does_not_maintain_has_no_certifying_staff_release(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-262, ML.A.801(b)(1). A Part-CAO whose approval has no maintenance privilege
    is refused a certificate by its own certifying staff; an independent one is recorded."""
    work = work_on(sample, fleet["G-EJKL"])
    chris = person(sample, "Chris Moore")
    with as_owner():
        Organisation.objects.filter(pk=sample.ours.pk).update(
            privileges=["Continuing Airworthiness Management", "Airworthiness Review"]
        )
    with working_for(sample.ours.id, sample.reader.id):
        assert not services.maintains(Organisation.objects.get(pk=sample.ours.pk))
    refused = post(
        signed_in(sample.lucy),
        f"/release-to-service/{work.id}/record/",
        reference="[Reference]",
        kind="Organisation Certifying Staff",
        issued_by=str(chris.id),
        issued_on="2026-11-10",
    )
    assert "Part-CAO with the Maintenance Privilege, ML.A.801(b)(1)" in refused.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        work.refresh_from_db()
    assert record(sample, work).kind == "Independent Certifying Staff"


def test_incomplete_maintenance_is_released_with_its_limitations(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-263, ML.A.801(f). Counted on the page, and shown with its limitations."""
    work = work_on(sample, fleet["G-EJKL"])
    record(sample, work, incomplete=True, limitations="Placarded, Daylight Only")
    body = page(signed_in(sample.reader), "/release-to-service/")
    assert "1 Incomplete Maintenance" in body
    (rows, _) = tables(body)
    assert [row[6] for row in rows if row[0] == "G-EJKL"] == ["Placarded, Daylight Only"]


def test_no_certificate_while_a_grounding_defect_is_open(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-263, ML.A.801(g). G-EJKL has a defect that is Not Deferrable, found on
    9 November. A certificate of 10 November is refused while it is open, and
    recorded once the defect was closed by that day. One of 8 November is not stopped."""
    ejkl = fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.planner.id):
        defect = defect_services.record_defect(
            ejkl,
            title="[Cracked Bracket]",
            found_on=date(2026, 11, 9),
            chapter=53,
            system="Fuselage",
            decision=Decision.NOT_DEFERRABLE,
            decided_on=date(2026, 11, 9),
        )
    work = work_on(sample, ejkl)
    with pytest.raises(services.RefusedError, match=r"ML.A.801\(g\): \[Cracked Bracket\]"):
        record(sample, work)
    earlier = work_on(sample, ejkl, description="[Earlier Work]", dated=date(2026, 11, 8))
    assert record(sample, earlier).completed_on == date(2026, 11, 8)
    with working_for(sample.ours.id, sample.planner.id):
        defect_services.close_defect(
            defect, rectification="[Replaced]", closed_on=date(2026, 11, 11)
        )
    with pytest.raises(services.RefusedError, match=r"ML.A.801\(g\)"):
        record(sample, work)
    assert record(sample, work, issued_on=date(2026, 11, 11)).issued_on == date(2026, 11, 11)


def test_a_certificate_keeps_what_it_said_and_is_never_changed(
    sample: Sample, releases: list[Release], fleet: dict[str, Aircraft]
) -> None:
    """REQ-261. Chris Moore is renamed, his licence changes and the organisation's
    approval reference would differ: the certificate says what it said. The database
    wrote those values, whatever was sent, and gives no right to change the record."""
    chris = person(sample, "Chris Moore")
    with working_for(sample.ours.id, sample.administrator.id):
        people_services.change_person(
            chris,
            full_name="[Another Name]",
            role=chris.role,
            staff_group=StaffGroup.CERTIFYING,
            reports_to=chris.reports_to,
            employment=Employment(chris.employment),
            licence="Part-66 B2",
            joined_on=None,
            left_on=None,
            by=sample.administrator,
        )
        configuration.change_details(
            Organisation.objects.get(pk=sample.ours.pk), name="[New Name]", address="[New Address]"
        )
    (rows, _) = tables(page(signed_in(sample.reader), "/release-to-service/"))
    assert rows[1][2] == "Chris Moore, Certifying Staff"
    assert rows[1][7] == "UK.CAO.[Number], Part-66 B1.2"
    work = work_on(sample, fleet["G-EJKL"])
    with working_for(sample.ours.id, sample.planner.id):
        made = Release.objects.create(
            organisation=sample.ours,
            work=work,
            reference="[Reference]",
            kind=IssuedBy.ORGANISATION,
            issued_by=chris,
            issuer_name="[Somebody Else]",
            licence="[Any Licence]",
            approval_reference="UK.145.[Other]",
            issued_on=work.dated,
            registration="G-FAKE",
            maintenance="[Other Work]",
            completed_on=date(2020, 1, 1),
            legacy_evidence="[Original Signed Release]",
        )
        made.refresh_from_db()
        assert (made.issuer_name, made.licence, made.approval_reference) == (
            "[Another Name]",
            "Part-66 B2",
            "UK.CAO.[Number]",
        )
        assert (made.registration, made.maintenance, made.completed_on) == (
            "G-EJKL",
            "[Work]",
            date(2026, 11, 10),
        )
        with pytest.raises(RecordsAreNeverDeletedError):
            made.save()
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            Release.objects.filter(pk=made.pk).update(limitations="[Altered]")


def test_the_database_holds_the_rules_of_a_certificate(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-260, REQ-263. Whatever the application sends: a reference, a known issuer
    who is named, a pilot-owner's licence number, limitations for incomplete
    maintenance, never issued before the work was completed, and one for each work."""
    work = work_on(sample, fleet["G-EJKL"])
    chris = person(sample, "Chris Moore")
    good: dict[str, Any] = {
        "organisation": sample.ours,
        "work": work,
        "reference": "[Reference]",
        "kind": IssuedBy.INDEPENDENT,
        "issuer_name": "[Name]",
        "issued_on": work.dated,
    }
    cases: tuple[tuple[dict[str, Any], str], ...] = (
        ({"reference": ""}, "release_has_a_reference_and_a_known_issuer"),
        ({"kind": "[Anyone]"}, "release_"),
        ({"issuer_name": ""}, "release_names_who_issued_it"),
        ({"issued_by": chris}, "release_names_who_issued_it"),
        ({"kind": IssuedBy.ORGANISATION}, "release_names_who_issued_it"),
        ({"kind": IssuedBy.PILOT_OWNER}, "release_by_a_pilot_owner_has_the_licence_number"),
        ({"incomplete": True}, "release_of_incomplete_maintenance_states_its_limitations"),
        ({"issued_on": date(2026, 11, 9)}, "not issued before the work was completed"),
    )
    with working_for(sample.ours.id, sample.planner.id):
        for change, constraint in cases:
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Release.objects.create(**{**good, **change})
        Release.objects.create(**good)
        with pytest.raises(IntegrityError, match="work_id"), transaction.atomic():
            Release.objects.create(**good)


def test_a_certificate_sent_twice_is_recorded_once(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-260. The work's row is taken before anything is looked for, so a second
    submit waits for the first and is refused. A work already recorded with another
    release reference is refused too."""
    work = work_on(sample, fleet["G-EJKL"])
    with working_for(sample.ours.id, sample.planner.id), CaptureQueriesContext(connection) as sent:
        record(sample, work)
    statements = [query["sql"] for query in sent.captured_queries]
    lock = next(
        index
        for index, statement in enumerate(statements)
        if "FOR UPDATE" in statement and "programme_workdone" in statement
    )
    look = next(i for i, statement in enumerate(statements) if "releases_release" in statement)
    assert lock < look
    with pytest.raises(services.RefusedError, match="Already Recorded"):
        record(sample, work)
    other = work_on(
        sample,
        fleet["G-EJKL"],
        description="[Other Work]",
        release_reference="[Earlier Reference]",
        release_recorded_on=date(2026, 11, 12),
    )
    with pytest.raises(services.RefusedError, match="Another Release Reference"):
        record(sample, other)
    kept = record(sample, other, reference="[Earlier Reference]")
    with working_for(sample.ours.id, sample.reader.id):
        other.refresh_from_db()
    # The day it went into the records stays as it was recorded (REQ-051).
    assert (kept.reference, other.release_recorded_on) == (
        "[Earlier Reference]",
        date(2026, 11, 12),
    )


def test_a_later_date_cannot_override_when_a_release_already_entered_the_records(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    work = work_on(
        sample,
        fleet["G-EJKL"],
        release_reference="[Earlier Reference]",
        release_recorded_on=date(2026, 11, 11),
    )
    with pytest.raises(services.RefusedError, match="Already Entered in the Records"):
        record(
            sample,
            work,
            reference="[Earlier Reference]",
            issued_on=date(2026, 11, 13),
            recorded_on=date(2026, 11, 14),
        )
    with pytest.raises(services.RefusedError, match="On or After the Day It Was Issued"):
        record(sample, work, reference="[Earlier Reference]", issued_on=date(2026, 11, 13))
    with working_for(sample.ours.id, sample.reader.id):
        assert not Release.objects.filter(work=work).exists()
        work.refresh_from_db()
        assert work.release_recorded_on == date(2026, 11, 11)


# Who may


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_who_may_record_a_certificate(
    sample: Sample, fleet: dict[str, Aircraft], role: str
) -> None:
    """REQ-006, REQ-266. The Continuing Airworthiness Manager and Planning and Records.
    Every role reads the page. The link is shown only to a role that may use it."""
    work = tyre(sample)
    client = signed_in(getattr(sample, role))
    may = role in ("lucy", "planner")
    path = f"/release-to-service/{work.id}/record/"
    listed = page(client, "/release-to-service/").split("<main", 1)[1]
    assert (f'href="{path}"' in listed) == may
    assert get(client, path).status_code == (200 if may else 403)
    assert post(client, path, **PILOT).status_code == (302 if may else 403)
    with working_for(sample.ours.id, sample.reader.id):
        assert Release.objects.count() == (1 if may else 0)
    with as_owner():
        refused = AccessEntry.objects.filter(kind="Action Refused")
        assert sorted(refused.values_list("detail", flat=True)) == (
            [] if may else ["Record Certificate of Release to Service"] * 2
        )


def test_another_organisations_releases_are_not_found_or_shown(
    sample: Sample, releases: list[Release], fleet: dict[str, Aircraft]
) -> None:
    """REQ-002, REQ-003."""
    stranger = signed_in(sample.stranger)
    work = tyre(sample)
    assert get(stranger, f"/release-to-service/{work.id}/record/").status_code == 404
    assert post(stranger, f"/release-to-service/{work.id}/record/", **PILOT).status_code == 404
    body = page(stranger, "/release-to-service/")
    assert "G-CDEF" not in body and "Chris Moore" not in body and "Tyre" not in body
    assert "<p>0 Issued, Last 30 Days, 0 Not Yet in Records" in body
    with (
        working_for(sample.other.id, sample.stranger.id),
        pytest.raises(Exception, match="refers only to records of its own organisation"),
        transaction.atomic(),
    ):
        Release.objects.create(
            organisation=sample.other,
            work=work,
            reference="[Reference]",
            kind=IssuedBy.INDEPENDENT,
            issuer_name="[Name]",
            issued_on=TODAY,
        )


def test_the_dashboard_links_a_release_not_yet_in_the_records_to_this_page(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-265. The Home board: Certificate of Release to Service Not Yet in Records,
    held on Release to Service. Once the certificate is recorded the row is gone."""
    reader = signed_in(sample.reader)
    row = '<td><a href="/release-to-service/">Release to Service</a></td>'
    assert row in page(reader, "/dashboard/")
    assert (
        post(
            signed_in(sample.planner), f"/release-to-service/{tyre(sample).id}/record/", **PILOT
        ).status_code
        == 302
    )
    assert row not in page(reader, "/dashboard/")


def test_new_staff_release_needs_in_force_authorisation_and_confirmation(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    certifier = person(sample, "Sam Patel")
    work = work_on(sample, fleet["G-EJKL"], dated=TODAY)
    with working_for(sample.ours.id, sample.administrator.id):
        old = people_services.record_maintenance_authorisation(
            certifier,
            scope="Part-ML aircraft",
            valid_from=date(2026, 1, 1),
            reference="TEST-OLD",
            valid_to=date(2026, 11, 17),
        )
        current = people_services.record_maintenance_authorisation(
            certifier,
            scope="Part-ML aircraft",
            valid_from=date(2026, 1, 1),
            reference="TEST-NEW",
            valid_to=TODAY,
        )
    details = dict(kind=IssuedBy.ORGANISATION, issuer_name="", issued_by=certifier)
    with pytest.raises(services.RefusedError, match="Record the Maintenance Authorisation"):
        record(sample, work, **details)
    with pytest.raises(services.RefusedError, match="Signed Legacy Evidence Must Predate Today"):
        record(sample, work, **details, legacy_evidence="Today's signed release")
    with pytest.raises(services.RefusedError, match="No Recorded Maintenance Authorisation Covers"):
        record(sample, work, **details, maintenance_authorisation=old, scope_confirmed=True)
    verified = record(
        sample, work, **details, maintenance_authorisation=current, scope_confirmed=True
    )
    assert verified.maintenance_authorisation_id == current.pk and verified.scope_confirmed
    later_work = work_on(sample, fleet["G-EJKL"], dated=TODAY, description="A second inspection")
    with working_for(sample.ours.id, sample.administrator.id):
        people_services.withdraw_maintenance_authorisation(
            current, withdrawn_from=TODAY, reason="Grant entered in error"
        )
    with pytest.raises(services.RefusedError, match="No Recorded Maintenance Authorisation Covers"):
        record(
            sample, later_work, **details, maintenance_authorisation=current, scope_confirmed=True
        )
    review = signed_in(sample.reader)
    evidence = page(review, f"/release-to-service/certificates/{verified.pk}/")
    assert "TEST-NEW, Scope Confirmed" in evidence
    assert "Later Withdrawal Effective 18 November 2026" in evidence
    programme = page(review, f"/aircraft/{work.aircraft_id}/programme/")
    assert f"/release-to-service/certificates/{verified.pk}/" in programme
