"""Defects, open and deferred, and repeat defects (REQ-220 to REQ-229).

The Defects and Repeat Defects boards, with the sample of
design-system/SampleData.md, Defects. Today in the sample is 18 November
2026. ML.A.403 was confirmed in the UK text on 24 November 2026
(Decisions.md, Regulation Facts in Use).

By hand, for 18 November 2026 and a lead time of 30 days:

- G-DGHI, Stabilator Trim Cable Frayed at Pulley: Not Deferrable, grounded
  since 14 November 2026.
- G-BXYZ, Cabin Entry Step Loose: deferred 28 October, 30 days, limit
  27 November 2026, 9 days.
- G-ABCD, Left Landing Light Inoperative: deferred 3 November, limit
  3 December 2026, 15 days.
- G-EJKL, Right Headset Socket Crackle: deferred 12 November, limit
  12 December 2026, 24 days.
- Closed in the last 30 days: G-CDEF's spinner on 4 November (14 days ago)
  and G-ABCD's tyre on 22 October (27 days ago).
- In the 12 months from 19 November 2025: Piper PA-28, chapter 33, 3
  (G-ABCD February and November, G-DGHI June); chapter 27, 2 (G-DGHI
  December 2025 and November 2026); chapter 32, 1; Cessna 152, chapter 23,
  1; Cessna 172, chapter 53, 1; Robin DR 400, chapter 61, 1.
"""

import io
import json
import re
import zipfile
from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.utils import DatabaseError
from django.test.utils import CaptureQueriesContext

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.dashboard import services as dashboard_services
from airworthiness_plus.defects import services
from airworthiness_plus.defects.models import Basis, Decision, Defect, RepeatAction
from airworthiness_plus.exports.build import build as build_export
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event, RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations import configuration
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.sample import build, phase1
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, get, make_sample, page, post, signed_in

pytestmark = pytest.mark.django_db


class Day:
    """Today, as the tests set it."""

    def __init__(self) -> None:
        self.today = TODAY


@pytest.fixture
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    chosen = Day()
    monkeypatch.setattr(aircraft_services, "today", lambda: chosen.today)
    monkeypatch.setattr(sign_in, "today", lambda: chosen.today)
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
def defects(sample: Sample, fleet: dict[str, Aircraft]) -> dict[str, Defect]:
    added = phase1.add_defects(sample.ours, sample.planner, fleet)
    phase1.add_repeat_actions(sample.ours, sample.lucy)
    return {defect.title: defect for defect in added}


def tables(body: str) -> list[list[list[str]]]:
    """Return the cells of each row of each table of the page."""
    found = []
    for table in body.split("<main", 1)[1].split("<table>")[1:]:
        rows = []
        for row in re.findall(r"<tr>\s*(<td.*?)</tr>", table.split("</table>", 1)[0], flags=re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
            rows.append([re.sub(r"<[^>]+>", "", cell).strip() for cell in cells])
        found.append(rows)
    return found


def person(sample: Sample, name: str) -> Person:
    with working_for(sample.ours.id, sample.reader.id):
        return Person.objects.get(full_name=name)


def record(sample: Sample, aircraft: Aircraft, **values: object) -> Defect:
    """Record a defect as Planning and Records, deferred by the pilot unless told otherwise."""
    given: dict[str, Any] = {
        "title": "[Defect]",
        "found_on": TODAY,
        "chapter": 33,
        "system": "Lights",
        "decision": Decision.DEFERRED,
        "basis": Basis.PILOT_NON_REQUIRED,
        "decided_on": TODAY,
    }
    given.update(values)
    with working_for(sample.ours.id, sample.planner.id):
        return services.record_defect(aircraft, **given)


FORM = {
    "title": "Left Landing Light Inoperative",
    "note": "Placarded, Daylight Only",
    "found_on": "2026-11-03",
    "chapter": "33",
    "system": "Lights",
    "decision": "Deferred",
    "basis": "Pilot-in-Command",
    "decided_on": "2026-11-03",
}


# The sample

OPEN = [
    ["G-DGHI", "Stabilator Trim Cable Frayed at Pulley", "Not Deferrable", "Grounded",
     "Since 14 November 2026", "Unserviceable", "Trim Check", "Chris Moore, Part-66 B1.2",
     "14 November 2026", "14 November 2026", "Chapter 27, Flight Controls", "ML.A.403(a)"],
    ["G-BXYZ", "Cabin Entry Step Loose", "Deferred", "27 November 2026", "9 Days", "Due Soon",
     "No Effect on Flight, Step Out of Use", "Sam Patel, Part-66 B1.2", "28 October 2026",
     "28 October 2026", "Chapter 53, Fuselage", "ML.A.403(b)(4)"],
    ["G-ABCD", "Left Landing Light Inoperative", "Deferred", "3 December 2026", "15 Days",
     "Due Soon", "Placarded, Daylight Only", "Pilot-in-Command", "3 November 2026",
     "3 November 2026", "Chapter 33, Lights", "ML.A.403(b)(1)"],
    ["G-EJKL", "Right Headset Socket Crackle", "Deferred", "12 December 2026", "24 Days",
     "Due Soon", "Left Socket Serviceable", "Pilot-in-Command", "12 November 2026",
     "12 November 2026", "Chapter 23, Communications", "ML.A.403(b)(1)"],
]  # fmt: skip

CLOSED = [
    ["G-CDEF", "Propeller Spinner Crack", "Spinner Replaced", "4 November 2026", "",
     "2 November 2026"],
    ["G-ABCD", "Right Main Tyre Worn to Limit", "Tyre Replaced", "22 October 2026",
     "Right Main Tyre Replaced, Pilot-Owner Maintenance", "22 October 2026"],
]  # fmt: skip


def test_the_defects_page_of_the_sample_on_18_november_2026(
    sample: Sample, defects: dict[str, Defect]
) -> None:
    """REQ-220, REQ-223, REQ-224. Golden, from the Defects board: what stops an
    aircraft first, then the nearest limit; then what was closed in the last 30 days."""
    body = page(signed_in(sample.reader), "/defects/")
    opened, closed = tables(body)
    assert [row[:12] for row in opened] == OPEN
    assert closed == CLOSED
    assert dot("Unserviceable") in body and body.count(dot("Due Soon")) == 3
    # How the limit was worked out is on the page, with its source (REQ-139).
    working = opened[1][12]
    for said in ("28 October 2026", "30 Days", "ML.A.403(b)(4); ML.A.403(c)"):
        assert said in working
    assert "<li>Continuing Airworthiness</li>" in body
    assert '<a href="/defects/" aria-current="page">Open and Deferred</a>' in body
    assert '<a href="/defects/repeat/">Repeat Defects</a>' in body


REPEATS = [
    ["Piper PA-28 Series (Lycoming)", "Chapter 33, Lights", "3", "Repeat",
     "Add Lamp Holder Check to 50-Hour Check", "", "G-ABCD, G-DGHI"],
    ["Piper PA-28 Series (Lycoming)", "Chapter 27, Flight Controls", "2", "Watching",
     "Pulley Alignment, WP-2026-046", "", "G-DGHI"],
    ["Cessna/Reims-Cessna 152/F152 Series (Lycoming)", "Chapter 23, Communications", "1",
     "No Action", "", "", "G-EJKL"],
    ["Cessna/Reims-Cessna 172/F172 Series (Lycoming)", "Chapter 53, Fuselage", "1",
     "No Action", "", "", "G-BXYZ"],
    ["Piper PA-28 Series (Lycoming)", "Chapter 32, Landing Gear", "1", "No Action", "", "",
     "G-ABCD"],
    ["Robin DR 400 series (Lycoming)", "Chapter 61, Propeller", "1", "No Action", "", "",
     "G-CDEF"],
]  # fmt: skip


def test_the_repeat_defects_of_the_sample_on_18_november_2026(
    sample: Sample, defects: dict[str, Defect]
) -> None:
    """REQ-226, REQ-227. Golden, from the Repeat Defects board: 3 of the same defect
    on one type in 12 months is a Repeat, 2 is Watching, 1 is No Action."""
    body = page(signed_in(sample.reader), "/defects/repeat/")
    (rows,) = tables(body)
    assert [row[:7] for row in rows] == REPEATS
    assert "<p>Repeat: 3 of the Same Defect on One Type in 12 Months</p>" in body
    assert "G-ABCD, Landing Light Inoperative, 10 February 2026" in rows[0][7]
    assert "G-DGHI, Stabilator Trim Cable Wear, 9 December 2025" in rows[1][7]
    assert '<a href="/defects/repeat/" aria-current="page">Repeat Defects</a>' in body


def test_a_defect_leaves_the_count_12_months_after_it_was_found(
    sample: Sample, defects: dict[str, Defect], day: Day
) -> None:
    """REQ-226. G-DGHI's trim cable wear of 9 December 2025 is counted up to
    8 December 2026, the last day of its 12 months, and not on 9 December 2026:
    2 becomes 1, and Watching becomes No Action."""

    def count() -> tuple[int, str]:
        with working_for(sample.ours.id, sample.reader.id):
            (line,) = [line for line in services.repeat_lines(day.today) if line.chapter == 27]
        return line.count, line.state

    day.today = date(2026, 12, 8)
    assert count() == (2, "Watching")
    day.today = date(2026, 12, 9)
    assert count() == (1, "No Action")


def test_a_repeat_with_no_action_recorded_is_to_assess(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-226, REQ-227. Three landing light defects on the Piper PA-28: a Repeat,
    marked To Assess until an action is recorded. The action is added, never changed."""
    for registration, found in (("G-ABCD", 3), ("G-ABCD", 10), ("G-DGHI", 12)):
        record(
            sample, fleet[registration], title=f"[Defect {found}]", found_on=date(2026, 11, found)
        )
    lucy = signed_in(sample.lucy)
    (rows,) = tables(page(lucy, "/defects/repeat/"))
    assert rows[0][2:6] == ["3", "Repeat", "", "To Assess"]
    values = {"type_rating": "Piper PA-28 Series (Lycoming)", "chapter": "33"}
    assert post(lucy, "/defects/repeat/action/", **values, action="[Action]").status_code == 302
    (rows,) = tables(page(lucy, "/defects/repeat/"))
    assert rows[0][2:6] == ["3", "Repeat", "[Action]", ""]
    assert rows[0][8] == "18 November 2026"
    # The same action sent again is refused; a different one takes its place.
    again = post(lucy, "/defects/repeat/action/", **values, action=" [Action] ")
    assert again.status_code == 200
    assert "This Action Is Already Recorded" in again.content.decode()
    assert post(lucy, "/defects/repeat/action/", **values, action="[Later]").status_code == 302
    (rows,) = tables(page(lucy, "/defects/repeat/"))
    assert rows[0][4] == "[Later]"
    # No defect is recorded for the type rating and chapter: refused.
    for other in (
        {"type_rating": "Piper PA-28 Series (Lycoming)", "chapter": "34"},
        {"type_rating": "piper pa-28 series (lycoming)", "chapter": "33"},
    ):
        refused = post(lucy, "/defects/repeat/action/", **other, action="[Action]")
        assert "No Defect Is Recorded for This Type Rating and Chapter" in refused.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        first, second = RepeatAction.objects.order_by("action")
        assert (first.action, second.action) == ("[Action]", "[Later]")
        assert (first.supersedes, second.supersedes) == (None, first)
        with pytest.raises(RecordsAreNeverDeletedError):
            first.save()
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            RepeatAction.objects.filter(pk=first.pk).update(action="[Altered]")


# Recording a defect


def test_a_deferred_defect_is_recorded_with_its_limit(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-220, REQ-222. By Planning and Records, on the page: 3 November and the
    organisation's 30 days is 3 December 2026, and the page says how."""
    planner = signed_in(sample.planner)
    response = post(planner, "/defects/record/", aircraft=str(fleet["G-ABCD"].id), **FORM)
    assert response.status_code == 302, response.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        defect = Defect.objects.get()
        entries = list(Event.of(defect))
    assert response["Location"] == f"/defects/{defect.id}/"
    assert (defect.limit_on, defect.default_days, defect.data_limit_on) == (
        date(2026, 12, 3),
        30,
        None,
    )
    assert (defect.decided_by, defect.decided_by_name, defect.basis) == (
        None,
        "",
        "Pilot-in-Command",
    )
    assert [(entry.action, entry.actor_name) for entry in entries] == [
        ("Created", "[Planning and Records Name]")
    ]
    body = page(planner, f"/defects/{defect.id}/")
    assert "<h1>Left Landing Light Inoperative</h1>" in body
    assert "<dt>Limit</dt><dd>3 December 2026</dd>" in body
    assert "<dt>Remaining</dt><dd>15 Days</dd>" in body
    assert f"<dt>Status</dt><dd>{dot('Due Soon')}</dd>" in body
    assert "<dt>Point</dt><dd>ML.A.403(b)(1)</dd>" in body
    assert "<summary>How the Limit Was Calculated</summary>" in body
    assert "<dt>Default Limit of the Organisation</dt><dd>30 Days</dd>" in body
    # The aircraft stays Serviceable, and its own page lists the defect.
    record_page = page(planner, f"/aircraft/{fleet['G-ABCD'].id}/")
    assert "<dt>Status</dt><dd>Serviceable</dd>" in record_page
    assert f'<a href="/defects/{defect.id}/">Left Landing Light Inoperative</a>' in record_page


def test_the_limit_uses_the_default_for_who_deferred_it(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-214, REQ-222. Each point of ML.A.403(b) has its own default: 10, 20 and 40
    days here. The minimum equipment list gives its own limit and takes no default."""
    with working_for(sample.ours.id, sample.administrator.id):
        configuration.set_deferral_limits(
            Organisation.objects.get(pk=sample.ours.pk),
            deferral_days_non_required=10,
            deferral_days_with_agreement=20,
            deferral_days_certifying_staff=40,
        )
    sam = person(sample, "Sam Patel")
    abcd = fleet["G-ABCD"]
    decided = date(2026, 11, 3)
    cases = (
        (Basis.PILOT_NON_REQUIRED, None, None, date(2026, 11, 13), 10),
        (Basis.PILOT_WITH_AGREEMENT, None, None, date(2026, 11, 23), 20),
        (Basis.CERTIFYING_STAFF, sam, None, date(2026, 12, 13), 40),
        (Basis.PILOT_LIST, None, date(2026, 11, 6), date(2026, 11, 6), None),
        # ML.A.403(c): the limit in the maintenance data applies when it is the earlier.
        (Basis.CERTIFYING_STAFF, sam, date(2026, 11, 20), date(2026, 11, 20), 40),
        (Basis.CERTIFYING_STAFF, sam, date(2026, 12, 25), date(2026, 12, 13), 40),
    )
    for number, (basis, by, data_limit, limit, days) in enumerate(cases):
        defect = record(
            sample,
            abcd,
            title=f"[Defect {number}]",
            found_on=decided,
            decided_on=decided,
            basis=basis,
            decided_by=by,
            data_limit_on=data_limit,
            legacy_evidence="[Signed Defect Entry]" if by else "",
        )
        assert (defect.limit_on, defect.default_days) == (limit, days), basis


def test_a_limit_already_given_does_not_move_when_the_setting_changes(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-222. The limit is kept as it was given: 3 December 2026, whatever the
    organisation's default becomes afterwards."""
    defect = record(
        sample, fleet["G-ABCD"], found_on=date(2026, 11, 3), decided_on=date(2026, 11, 3)
    )
    with working_for(sample.ours.id, sample.administrator.id):
        configuration.set_deferral_limits(
            Organisation.objects.get(pk=sample.ours.pk),
            deferral_days_non_required=5,
            deferral_days_with_agreement=5,
            deferral_days_certifying_staff=5,
        )
    with working_for(sample.ours.id, sample.reader.id):
        (line,) = services.open_lines(Organisation.objects.get(pk=sample.ours.pk), TODAY)
    assert (line.defect.pk, line.defect.limit_on, line.defect.default_days, line.days_left) == (
        defect.pk,
        date(2026, 12, 3),
        30,
        15,
    )


def test_a_defect_that_is_not_deferrable_grounds_the_aircraft(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-221, ML.A.403(a). G-ABCD is made Unserviceable with the defect as the
    reason, and is not made Serviceable while the defect is open."""
    abcd = fleet["G-ABCD"]
    chris = person(sample, "Chris Moore")
    lucy = signed_in(sample.lucy)
    values = {**FORM, "decision": "Not Deferrable", "basis": "", "title": "[Cracked Bracket]"}
    response = post(
        lucy, "/defects/record/", aircraft=str(abcd.id), decided_by=str(chris.id), **values
    )
    assert response.status_code == 302, response.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        defect = Defect.objects.get()
        grounded = Aircraft.objects.get(pk=abcd.pk)
    assert (grounded.status, grounded.unserviceable_reason, grounded.unserviceable_since) == (
        "Unserviceable",
        "[Cracked Bracket]",
        date(2026, 11, 3),
    )
    assert (defect.limit_on, defect.basis, defect.decided_by_text) == (
        None,
        "",
        "Chris Moore, Part-66 B1.2",
    )
    refused = post(lucy, f"/aircraft/{abcd.id}/serviceable/")
    assert refused.status_code == 200
    assert (
        '<p role="alert">Open Defect That Is Not Deferrable, ML.A.403(a): [Cracked Bracket]</p>'
        in refused.content.decode()
    )
    # The database refuses it as well, whatever the application does.
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(IntegrityError, match="is not made Serviceable"), transaction.atomic():
            Aircraft.objects.filter(pk=abcd.pk).update(
                status="Serviceable", unserviceable_reason="", unserviceable_since=None
            )
        assert Aircraft.objects.get(pk=abcd.pk).status == "Unserviceable"
    # Closed, the defect no longer stops it. Closing does not itself change the status.
    closed = post(
        lucy,
        f"/defects/{defect.id}/close/",
        rectification="[Bracket Replaced]",
        closed_on="2026-11-17",
    )
    assert closed.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        assert Aircraft.objects.get(pk=abcd.pk).status == "Unserviceable"
    assert post(lucy, f"/aircraft/{abcd.id}/serviceable/").status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        assert Aircraft.objects.get(pk=abcd.pk).status == "Serviceable"


def test_an_aircraft_already_unserviceable_keeps_its_reason(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-221. G-DGHI is Unserviceable since 14 November: a second defect that is
    Not Deferrable changes nothing of its status, and either stops it being made Serviceable."""
    dghi = fleet["G-DGHI"]
    first = record(sample, dghi, title="[First]", decision=Decision.NOT_DEFERRABLE, basis="")
    record(sample, dghi, title="[Second]", decision=Decision.NOT_DEFERRABLE, basis="")
    with working_for(sample.ours.id, sample.lucy.id):
        aircraft = Aircraft.objects.get(pk=dghi.pk)
        assert (aircraft.unserviceable_reason, aircraft.unserviceable_since) == (
            "Stabilator Trim Cable",
            date(2026, 11, 14),
        )
        services.close_defect(first, rectification="[Done]", closed_on=TODAY)
        with pytest.raises(aircraft_services.NotServiceableError, match=r"\[Second\]"):
            aircraft_services.make_serviceable(aircraft)


def test_the_database_refuses_a_grounding_defect_on_a_serviceable_aircraft(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-221. Whatever the application does: a defect that is Not Deferrable and
    open is recorded only against an aircraft that is Unserviceable."""
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.planner.id):
        with pytest.raises(IntegrityError, match="that is Unserviceable"), transaction.atomic():
            Defect.objects.create(
                organisation=sample.ours,
                aircraft=abcd,
                title="[Defect]",
                found_on=TODAY,
                chapter=33,
                system="Lights",
                decision=Decision.NOT_DEFERRABLE,
                decided_on=TODAY,
            )
        assert Defect.objects.count() == 0


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ({"title": "  "}, "This field is required"),
        ({"system": " "}, "This field is required"),
        ({"chapter": "0"}, "greater than or equal to 1"),
        ({"chapter": "100"}, "less than or equal to 99"),
        (
            {"found_on": "2026-11-19", "decided_on": "2026-11-19"},
            "Not Found or Decided After Today",
        ),
        ({"decided_on": "2026-11-19"}, "Not Found or Decided After Today"),
        ({"decided_on": "2026-11-02"}, "Not Before the Defect Was Found"),
        ({"basis": ""}, "Says Who Deferred It, ML.A.403(b)"),
        ({"basis": "Certifying Staff"}, "Certifying Staff Who Defer a Defect Are Named"),
        ({"basis": "Pilot-in-Command, Minimum Equipment List"}, "Minimum Equipment List Gives"),
        ({"data_limit_on": "2026-11-02"}, "Not Before the Day of the Decision"),
        (
            {"basis": "Pilot-in-Command, Minimum Equipment List", "data_limit_on": "2028-01-01"},
            "365 Days After the Decision",
        ),
        ({"decision": "Not Deferrable"}, "Not Deferrable Has No Limit"),
        ({"decision": "Deferred Later"}, "Select a valid choice"),
        ({"rectification": "[Done]"}, "Has the Day It Was Closed"),
        ({"closed_on": "2026-11-10"}, "Says How It Was Rectified"),
        ({"rectification": "[Done]", "closed_on": "2026-11-19"}, "Not Closed After Today"),
        ({"rectification": "[Done]", "closed_on": "2026-11-02"}, "Not Closed Before It Was Found"),
    ],
)
def test_what_cannot_be_true_of_a_defect_is_refused(
    sample: Sample, fleet: dict[str, Aircraft], values: dict[str, str], reason: str
) -> None:
    """REQ-220 to REQ-222. Said on the page, with nothing recorded and no status changed."""
    lucy = signed_in(sample.lucy)
    response = post(
        lucy, "/defects/record/", aircraft=str(fleet["G-ABCD"].id), **{**FORM, **values}
    )
    assert response.status_code == 200
    assert reason in response.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert Defect.objects.count() == 0
        assert Aircraft.objects.get(pk=fleet["G-ABCD"].pk).status == "Serviceable"


def test_who_may_be_named_as_deferring_a_defect(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-222, ML.A.403(b)(4). Certifying staff of the organisation who had not left
    by the day; a pilot-in-command is not chosen from the staff."""
    lucy = signed_in(sample.lucy)
    abcd = str(fleet["G-ABCD"].id)
    sam, ellie = person(sample, "Sam Patel"), person(sample, "Ellie Ward")
    staff = {**FORM, "basis": "Certifying Staff"}
    not_staff = post(lucy, "/defects/record/", aircraft=abcd, decided_by=str(ellie.id), **staff)
    assert "Select a valid choice" in not_staff.content.decode()
    pilot = post(lucy, "/defects/record/", aircraft=abcd, decided_by=str(sam.id), **FORM)
    assert "A Pilot-in-Command Is Not Chosen From the Staff" in pilot.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(services.RefusedError, match="Is Not Certifying Staff"):
            services.record_defect(
                fleet["G-ABCD"],
                title="[Defect]",
                found_on=TODAY,
                chapter=33,
                system="Lights",
                decision=Decision.DEFERRED,
                basis=Basis.CERTIFYING_STAFF,
                decided_on=TODAY,
                decided_by=ellie,
            )
    # Sam Patel left on 10 November: a decision of 12 November is not his, one of 3 November is.
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
            left_on=date(2026, 11, 10),
            by=sample.administrator,
        )
    with working_for(sample.ours.id, sample.lucy.id):
        sam.refresh_from_db()
        given: dict[str, Any] = {
            "title": "[Defect]",
            "chapter": 33,
            "system": "Lights",
            "decision": Decision.DEFERRED,
            "basis": Basis.CERTIFYING_STAFF,
            "decided_by": sam,
            "legacy_evidence": "[Signed Defect Entry]",
        }
        with pytest.raises(services.RefusedError, match="Had Left by the Day"):
            services.record_defect(
                fleet["G-ABCD"], found_on=date(2026, 11, 12), decided_on=date(2026, 11, 12), **given
            )
        kept = services.record_defect(
            fleet["G-ABCD"], found_on=date(2026, 11, 3), decided_on=date(2026, 11, 3), **given
        )
        assert kept.decided_by_text == "Sam Patel, Part-66 B1.2"
    with working_for(sample.ours.id, sample.reader.id):
        assert Defect.objects.count() == 1


def test_the_decision_keeps_who_made_it_as_they_then_were(
    sample: Sample, defects: dict[str, Defect]
) -> None:
    """REQ-225. Sam Patel deferred G-BXYZ's step on 28 October. He is renamed and
    his licence changes: the defect still says Sam Patel, Part-66 B1.2. The
    database wrote both, and refuses any change to them or to the decision."""
    sam = person(sample, "Sam Patel")
    with working_for(sample.ours.id, sample.administrator.id):
        people_services.change_person(
            sam,
            full_name="[Another Name]",
            role=sam.role,
            staff_group=StaffGroup.CERTIFYING,
            reports_to=sam.reports_to,
            employment=Employment(sam.employment),
            licence="Part-66 B2",
            joined_on=None,
            left_on=None,
            by=sample.administrator,
        )
    step = defects["Cabin Entry Step Loose"]
    body = page(signed_in(sample.reader), f"/defects/{step.id}/")
    assert "<dt>Decided By</dt><dd>Sam Patel, Part-66 B1.2</dd>" in body
    with working_for(sample.ours.id, sample.planner.id):
        # What the application sends for them is not what is kept.
        chris = Person.objects.get(full_name="Chris Moore")
        grant = people_services.record_maintenance_authorisation(
            chris, reference="TEST-DEFECT", scope=step.aircraft.type_rating, valid_from=TODAY
        )
        made = Defect.objects.create(
            organisation=sample.ours,
            aircraft=step.aircraft,
            title="[Defect]",
            found_on=TODAY,
            chapter=33,
            system="Lights",
            decision=Decision.DEFERRED,
            basis=Basis.CERTIFYING_STAFF,
            decided_on=TODAY,
            decided_by=chris,
            maintenance_authorisation=grant,
            scope_confirmed=True,
            decided_by_name="[Somebody Else]",
            decided_by_licence="[Any Licence]",
            default_days=30,
            limit_on=date(2026, 12, 18),
        )
        made.refresh_from_db()
        assert (made.decided_by_name, made.decided_by_licence) == ("Chris Moore", "Part-66 B1.2")
        for change in (
            {"decided_by_name": "[Altered]"},
            {"decided_by_licence": "[Altered]"},
            {"decided_by": chris},
            {"limit_on": date(2026, 12, 30)},
            {"default_days": 60},
            {"decided_on": date(2026, 10, 29)},
            {"title": "[Altered]"},
            {"note": "[Altered]"},
            {"chapter": 34},
            {"system": "[Altered]"},
            {"found_on": date(2026, 10, 27)},
            {"data_limit_on": date(2026, 11, 20)},
            {"aircraft": Aircraft.objects.get(registration="G-ABCD")},
        ):
            with (
                pytest.raises(IntegrityError, match="decision is never altered"),
                transaction.atomic(),
            ):
                Defect.objects.filter(pk=step.pk).update(**change)
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('airworthiness.organisation', %s, true)", [str(sample.ours.id)]
        )
        with pytest.raises(IntegrityError, match="decision is never altered"), transaction.atomic():
            cursor.execute(
                "UPDATE defects_defect SET limit_on = '2027-01-01' WHERE id = %s", [step.id]
            )
        cursor.execute("SELECT set_config('airworthiness.organisation', '', true)")


def test_the_database_holds_the_bounds_of_a_defect(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-220, REQ-222. Whatever the application sends: a chapter from 1 to 99, a
    default from 1 to 365 days, a limit at most 365 days after the decision and
    never before it, and a basis and a limit for every deferred defect."""
    abcd = fleet["G-ABCD"]
    good: dict[str, object] = {
        "organisation": sample.ours,
        "aircraft": abcd,
        "title": "[Defect]",
        "found_on": TODAY,
        "chapter": 33,
        "system": "Lights",
        "decision": Decision.DEFERRED,
        "basis": Basis.PILOT_NON_REQUIRED,
        "decided_on": TODAY,
        "default_days": 30,
        "limit_on": date(2026, 12, 18),
    }
    cases: tuple[tuple[dict[str, object], str], ...] = (
        ({"chapter": 0}, "defect_has_a_title"),
        ({"chapter": 100}, "defect_has_a_title"),
        ({"title": ""}, "defect_has_a_title"),
        ({"system": ""}, "defect_has_a_title"),
        ({"decided_on": date(2026, 11, 17)}, "defect_has_a_title"),
        ({"default_days": 0}, "defect_default_limit_from_1_to_365_days"),
        ({"default_days": 366}, "defect_default_limit_from_1_to_365_days"),
        ({"limit_on": date(2026, 11, 17)}, "defect_deferred_has_a_basis_and_a_limit"),
        ({"limit_on": None}, "defect_deferred_has_a_basis_and_a_limit"),
        ({"basis": ""}, "defect_deferred_has_a_basis_and_a_limit"),
        ({"basis": "[Anyone]"}, "defect_certifying_staff_are_named_and_a_pilot_is_not"),
        ({"decision": "[Unknown]"}, "defect_deferred_has_a_basis_and_a_limit"),
        ({"limit_on": date(2027, 11, 19)}, "at most 365 days after the decision"),
        ({"default_days": None}, "defect_limit_comes_from_the_list_or_the_default"),
        (
            {"basis": Basis.PILOT_LIST, "default_days": None},
            "defect_limit_comes_from_the_list_or_the_default",
        ),
        ({"basis": Basis.CERTIFYING_STAFF}, "defect_certifying_staff_are_named"),
        ({"closed_on": TODAY}, "defect_closed_has_a_rectification_and_a_day"),
        ({"rectification": "[Done]"}, "defect_closed_has_a_rectification_and_a_day"),
        (
            {"rectification": "[Done]", "closed_on": date(2026, 11, 17)},
            "defect_closed_has_a_rectification_and_a_day",
        ),
    )
    with working_for(sample.ours.id, sample.planner.id):
        for change, constraint in cases:
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Defect.objects.create(**{**good, **change})
        # The last day the database allows: 365 days after the decision.
        Defect.objects.create(**{**good, "limit_on": date(2027, 11, 18), "default_days": 365})
        assert Defect.objects.count() == 1


# Closing a defect


def test_a_defect_is_closed_once_and_then_never_changes(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-224. Closed with its rectification and the work done; a second submit is
    refused; nothing of a closed defect is altered, by the application or the owner."""
    abcd = fleet["G-ABCD"]
    defect = record(
        sample,
        abcd,
        title="[Tyre Worn]",
        found_on=date(2026, 10, 22),
        decided_on=date(2026, 10, 22),
    )
    with working_for(sample.ours.id, sample.reader.id):
        work = abcd.work_done.get()
    planner = signed_in(sample.planner)
    values = {
        "rectification": " Tyre Replaced ",
        "closed_on": "2026-10-22",
        "work_done": str(work.id),
    }
    assert post(planner, f"/defects/{defect.id}/close/", **values).status_code == 302
    again = post(planner, f"/defects/{defect.id}/close/", **values)
    assert again.status_code == 200
    assert "This Defect Is Already Closed" in again.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        closed = Defect.objects.get(pk=defect.pk)
        assert (closed.rectification, closed.closed_on, closed.work_done) == (
            "Tyre Replaced",
            date(2026, 10, 22),
            work,
        )
        entries = list(Event.of(closed))
        assert [(entry.action, entry.changed) for entry in entries] == [
            ("Created", []),
            ("Changed", ["closed_on", "rectification", "work_done_id"]),
        ]
        assert chain.problems(entries) == []
        for change in ({"rectification": "[Altered]"}, {"closed_on": TODAY}, {"work_done": None}):
            with (
                pytest.raises(IntegrityError, match="closed defect is never altered"),
                transaction.atomic(),
            ):
                Defect.objects.filter(pk=defect.pk).update(**change)
    body = page(planner, f"/defects/{defect.id}/")
    assert "<dt>Rectification</dt><dd>Tyre Replaced</dd>" in body
    assert "<dt>Work Done</dt><dd>Right Main Tyre Replaced, Pilot-Owner Maintenance</dd>" in body
    assert "<form" not in body.split("<main", 1)[1]


def test_what_cannot_be_true_of_a_closure_is_refused(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-224. Not after today, not before the defect was found, with a rectification,
    and with work done on the same aircraft."""
    defect = record(
        sample, fleet["G-EJKL"], found_on=date(2026, 11, 12), decided_on=date(2026, 11, 12)
    )
    with working_for(sample.ours.id, sample.reader.id):
        work = fleet["G-ABCD"].work_done.get()
    lucy = signed_in(sample.lucy)
    for values, reason in (
        ({"rectification": "[Done]", "closed_on": "2026-11-19"}, "Not Closed After Today"),
        ({"rectification": "[Done]", "closed_on": "2026-11-11"}, "Not Closed Before It Was Found"),
        ({"rectification": " ", "closed_on": "2026-11-18"}, "This field is required"),
        (
            {"rectification": "[Done]", "closed_on": "2026-11-18", "work_done": str(work.id)},
            "Select a valid choice",
        ),
    ):
        refused = post(lucy, f"/defects/{defect.id}/close/", **values)
        assert refused.status_code == 200, values
        assert reason in refused.content.decode(), values
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(services.RefusedError, match="Belongs to Another Aircraft"):
            services.close_defect(defect, rectification="[Done]", closed_on=TODAY, work_done=work)
        assert Defect.objects.get(pk=defect.pk).open


def test_closed_defects_are_shown_for_30_days(
    sample: Sample, defects: dict[str, Defect], day: Day
) -> None:
    """REQ-224. The tyre was closed on 22 October: shown up to 21 November, 30 days
    later, and not on 22 November."""
    reader = signed_in(sample.reader)
    day.today = date(2026, 11, 21)
    assert "Right Main Tyre Worn to Limit" in page(reader, "/defects/")
    day.today = date(2026, 11, 22)
    assert "Right Main Tyre Worn to Limit" not in page(reader, "/defects/")
    assert "Propeller Spinner Crack" in page(reader, "/defects/")


# Two submits at once


def test_rectified_defect_sent_twice_is_recorded_once(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    client = signed_in(sample.lucy)
    aircraft = fleet["G-ABCD"]
    values = dict(
        FORM, aircraft=str(aircraft.id), closed_on="2026-11-04", rectification="Lamp Replaced"
    )
    assert post(client, "/defects/record/", **values).status_code == 302
    repeated = post(client, "/defects/record/", **values)
    assert repeated.status_code == 200
    assert "This Rectified Defect Is Already Recorded" in repeated.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        assert Defect.objects.filter(aircraft=aircraft, title=FORM["title"]).count() == 1
    values["note"] = "Second Occurrence After Replacement"
    assert post(client, "/defects/record/", **values).status_code == 302


def test_a_defect_sent_twice_is_recorded_once(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-220. The aircraft's row is taken before anything is looked for, so a
    second submit waits for the first and is refused with the reason."""
    lucy = signed_in(sample.lucy)
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.lucy.id), CaptureQueriesContext(connection) as sent:
        record(
            sample,
            abcd,
            title=FORM["title"],
            found_on=date(2026, 11, 3),
            decided_on=date(2026, 11, 3),
        )
    statements = [query["sql"] for query in sent.captured_queries]
    lock = next(
        index
        for index, statement in enumerate(statements)
        if "FOR UPDATE" in statement and "aircraft_aircraft" in statement
    )
    look = next(
        index for index, statement in enumerate(statements) if "defects_defect" in statement
    )
    assert lock < look
    again = post(lucy, "/defects/record/", aircraft=str(abcd.id), **FORM)
    assert again.status_code == 200
    assert "This Defect Is Already Recorded and Open" in again.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert Defect.objects.count() == 1


# Who may


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_who_may_record_and_close_a_defect(
    sample: Sample, fleet: dict[str, Aircraft], role: str
) -> None:
    """REQ-006, REQ-229. The Continuing Airworthiness Manager and Planning and Records
    record and close; only the manager records the action on a repeat. Every role
    reads. A link or form is shown only to a role that may use it."""
    defect = record(sample, fleet["G-ABCD"])
    user = getattr(sample, role)
    client = signed_in(user)
    may = role in ("lucy", "planner")
    listed = page(client, "/defects/").split("<main", 1)[1]
    one = page(client, f"/defects/{defect.id}/").split("<main", 1)[1]
    repeat = page(client, "/defects/repeat/").split("<main", 1)[1]
    assert ('href="/defects/record/"' in listed) == may
    assert ("<form" in one) == may
    assert ("<form" in repeat) == (role == "lucy")
    assert get(client, "/defects/record/").status_code == (200 if may else 403)
    recorded = post(client, "/defects/record/", aircraft=str(fleet["G-EJKL"].id), **FORM)
    assert recorded.status_code == (302 if may else 403)
    action = post(
        client,
        "/defects/repeat/action/",
        type_rating="Piper PA-28 Series (Lycoming)",
        chapter="33",
        action="[Action]",
    )
    assert action.status_code == (302 if role == "lucy" else 403)
    closed = post(
        client, f"/defects/{defect.id}/close/", rectification="[Done]", closed_on="2026-11-18"
    )
    assert closed.status_code == (302 if may else 403)
    with working_for(sample.ours.id, sample.reader.id):
        assert Defect.objects.get(pk=defect.pk).open == (not may)
        assert RepeatAction.objects.count() == (1 if role == "lucy" else 0)
    if not may:
        with as_owner():
            refused = AccessEntry.objects.filter(kind="Action Refused")
            assert sorted(refused.values_list("detail", flat=True)) == [
                "Record Defect",
                "Record Defect",
                "Record Defect",
                "Record Repeat Defect Action",
            ]


def test_another_organisations_defects_are_not_found_or_shown(
    sample: Sample, defects: dict[str, Defect], fleet: dict[str, Aircraft]
) -> None:
    """REQ-003, REQ-002."""
    stranger = signed_in(sample.stranger)
    step = defects["Cabin Entry Step Loose"]
    assert get(stranger, f"/defects/{step.id}/").status_code == 404
    assert (
        post(
            stranger, f"/defects/{step.id}/close/", rectification="X", closed_on="2026-11-18"
        ).status_code
        == 404
    )
    for path in ("/defects/", "/defects/repeat/"):
        body = page(stranger, path)
        assert "G-BXYZ" not in body and "Cabin Entry Step" not in body and "Piper" not in body
    refused = post(stranger, "/defects/record/", aircraft=str(fleet["G-ABCD"].id), **FORM)
    assert refused.status_code == 200
    assert "Select a valid choice" in refused.content.decode()
    sam = person(sample, "Sam Patel")
    with working_for(sample.other.id, sample.stranger.id):
        theirs = aircraft_services.add_aircraft(
            organisation=sample.other, registration="G-OTHR", type_rating="[Type]", owner="X"
        )
        for values in ({"aircraft": fleet["G-ABCD"]}, {"aircraft": theirs, "decided_by": sam}):
            with (
                pytest.raises(Exception, match="refers only to records of its own organisation"),
                transaction.atomic(),
            ):
                Defect.objects.create(
                    organisation=sample.other,
                    title="[Defect]",
                    found_on=date(2026, 11, 17),
                    chapter=33,
                    system="Lights",
                    decision=Decision.DEFERRED,
                    basis=Basis.CERTIFYING_STAFF
                    if "decided_by" in values
                    else Basis.PILOT_NON_REQUIRED,
                    decided_on=date(2026, 11, 17),
                    legacy_evidence="Original Signed Record" if "decided_by" in values else "",
                    default_days=30,
                    limit_on=date(2026, 12, 17),
                    **values,
                )


# The Dashboard and the export

DASHBOARD = [
    ["G-BXYZ", "Deferred Defect Limit, Cabin Entry Step Loose", "27 November 2026", "9 Days",
     "Due Soon", "Deferred by Sam Patel, Part-66 B1.2, 28 October 2026, ML.A.403(b)(4)",
     "Defects"],
    ["G-ABCD", "Deferred Defect Limit, Left Landing Light Inoperative", "3 December 2026",
     "15 Days", "Due Soon", "Deferred by Pilot-in-Command, 3 November 2026, ML.A.403(b)(1)",
     "Defects"],
    ["G-EJKL", "Deferred Defect Limit, Right Headset Socket Crackle", "12 December 2026",
     "24 Days", "Due Soon", "Deferred by Pilot-in-Command, 12 November 2026, ML.A.403(b)(1)",
     "Defects"],
]  # fmt: skip


def test_the_dashboard_shows_each_deferred_defect_from_its_lead_time(
    sample: Sample, defects: dict[str, Defect], day: Day
) -> None:
    """REQ-228. Golden, from the Home board: the three deferred defects of the
    sample, each inside the lead time of 30 days. A limit passed is Overdue and red."""

    def rows() -> list[list[str]]:
        with working_for(sample.ours.id, sample.reader.id):
            panel = dashboard_services.continuing_airworthiness(
                Organisation.objects.get(pk=sample.ours.pk), day.today
            )
        return [
            [row.subject, row.item, row.due, row.remaining, row.status, row.detail, row.page]
            for row in panel.rows
            if row.page == "Defects" and row.item.startswith("Deferred Defect Limit")
        ]

    assert rows() == DASHBOARD
    # With a lead time of 10 days only G-BXYZ's 9 days are shown.
    with working_for(sample.ours.id, sample.administrator.id):
        configuration.set_lead_times(
            Organisation.objects.get(pk=sample.ours.pk),
            due_soon_days=10,
            due_soon_hours=sample.ours.due_soon_hours,
            due_soon_cycles=sample.ours.due_soon_cycles,
            review_alert_days=None,
        )
    assert [row[0] for row in rows()] == ["G-BXYZ"]
    day.today = date(2026, 11, 27)
    assert next(row[3:5] for row in rows()) == ["0 Days", "Due"]
    day.today = date(2026, 11, 29)
    first = rows()[0]
    assert first[:5] == [
        "G-BXYZ",
        "Deferred Defect Limit, Cabin Entry Step Loose",
        "27 November 2026",
        "2 Days Overdue",
        "Overdue",
    ]
    body = page(signed_in(sample.reader), "/dashboard/")
    assert dot("Overdue") in body
    step = defects["Cabin Entry Step Loose"]
    assert f'<a href="/defects/{step.id}/">Defects</a>' in body


def test_the_export_of_an_aircraft_holds_its_defects_and_the_actions_for_its_type(
    sample: Sample, defects: dict[str, Defect], fleet: dict[str, Aircraft]
) -> None:
    """REQ-134. G-DGHI's three defects and the two actions recorded for the Piper
    PA-28; G-EJKL's one defect and no action."""
    with working_for(sample.ours.id, sample.lucy.id):
        dghi = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-DGHI"])
        ejkl = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-EJKL"])

    def read(export: object, name: str) -> list[dict[str, object]]:
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:  # type: ignore[attr-defined]
            found: list[dict[str, object]] = json.loads(archive.read(f"records/{name}.json"))
            return found

    assert sorted(str(one["title"]) for one in read(dghi, "defects_defect")) == [
        "Landing Light Inoperative",
        "Stabilator Trim Cable Frayed at Pulley",
        "Stabilator Trim Cable Wear",
    ]
    assert sorted(str(one["action"]) for one in read(dghi, "defects_repeataction")) == [
        "Add Lamp Holder Check to 50-Hour Check",
        "Pulley Alignment, WP-2026-046",
    ]
    assert [one["title"] for one in read(ejkl, "defects_defect")] == [
        "Right Headset Socket Crackle"
    ]
    assert read(ejkl, "defects_repeataction") == []


def test_certifying_staff_cannot_defer_outside_their_authorisation_dates(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    certifier = person(sample, "Sam Patel")
    with working_for(sample.ours.id, sample.administrator.id):
        authorisation = people_services.record_maintenance_authorisation(
            certifier,
            reference="TEST-OLD",
            scope="Part-ML aircraft",
            valid_from=date(2026, 1, 1),
            valid_to=date(2026, 11, 17),
        )
    with pytest.raises(services.RefusedError, match="No Recorded Maintenance Authorisation Covers"):
        record(
            sample,
            fleet["G-BXYZ"],
            basis=Basis.CERTIFYING_STAFF,
            decided_by=certifier,
            maintenance_authorisation=authorisation,
            scope_confirmed=True,
        )
