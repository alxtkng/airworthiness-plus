"""The Dashboard: one page of everything due across the organisation (REQ-215 to REQ-217).

The Home board of the canvas. A panel for each section that is built, each
row with what it is, when it is due, what remains and the page that holds
it. The rows below are worked by hand from design-system/SampleData.md for
18 November 2026, with the lead times of Decisions.md, Canvas Build,
decision 4: 30 days, 10.0 hours, 10 cycles.

By hand:

- G-DGHI is Unserviceable, Stabilator Trim Cable, grounded since 14 November 2026.
- G-ABCD's right main tyre was replaced on 22 October 2026 with no release
  yet in the records: 30 days, by 21 November 2026 (ML.A.305(a)), 3 days.
- G-CDEF's certificate was issued on 11 November 2026: the copy goes to the
  Civil Aviation Authority within 10 days, by 21 November 2026
  (ML.A.903(f)), 3 days.
- G-EJKL's certificate is valid to 6 December 2026: 18 days.
- G-ABCD's 50-hour check has 12.4 hours remaining: more than 10.0, so it is
  not yet Due Soon and is not on the Dashboard. The Home board shows it
  because the Settings board had 15 hours, which decision 4 does not take.
- Four directives are recorded. G-ABCD has decisions on three of them; no
  other aircraft has any.
- G-DGHI and G-EJKL have no maintenance programme set up: SampleData.md gives
  programme inputs for G-ABCD, G-BXYZ, G-FMNO and G-CDEF only.
- Of those four programmes only G-CDEF's has an annual review recorded, on
  11 November 2026. The other three have none: each is shown, not left clear.
- G-HKLM is a Transfer In with 14 of 18 records received.
- [Review Name]'s recency lapses on 2 December 2026: 14 days.
- The Grob manual's amendment check is due by 20 November 2026 (2 days) and
  CAP 747's by 30 November 2026 (12 days). The Piper PA-38 manual is not
  held. The supplementary type certificate instructions have no check recorded.
- Maintenance data is recorded for three type ratings: the Grob, the Piper
  PA-38 and the Cessna 172. No data is recorded for the Cessna 152 (G-EJKL),
  the Piper PA-28 (G-ABCD and G-DGHI) or the Robin DR 400 (G-CDEF).
"""

import re
from datetime import date
from decimal import Decimal

import pytest
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.acceptance import services as acceptance_services
from airworthiness_plus.acceptance.models import NoteKind
from airworthiness_plus.accounts import sign_in
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind, Regime
from airworthiness_plus.dashboard import services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.imports import services as import_services
from airworthiness_plus.imports.layouts import AIRCRAFT
from airworthiness_plus.imports.models import LoadedValue, LoadKind
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import DataSet
from airworthiness_plus.maintenance_data.models import Kind as DataKind
from airworthiness_plus.organisations import configuration
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Programme
from airworthiness_plus.sample import build
from airworthiness_rules.intervals import Interval, Reading, TaskKind
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, make_sample, signed_in
from tests.test_imports import csv_of

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
    """The whole sample: people, fleet, programmes, reviews, directives and data."""
    sample = make_sample()
    fleet = build.add_fleet(sample)
    build.add_programmes(sample, fleet)
    build.add_other_work(sample, fleet)
    build.add_reviews(sample, fleet)
    build.add_directives(sample, fleet)
    build.add_maintenance_data(sample)
    return sample


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def panels(body: str) -> dict[str, list[list[str]]]:
    """Return each panel of the page: its heading, and the cells of each of its rows."""
    found: dict[str, list[list[str]]] = {}
    for part in body.split("<main", 1)[1].split("<h2>")[1:]:
        heading, rest = part.split("</h2>", 1)
        rows = []
        if "<table>" in rest:
            table = rest.split("<table>", 1)[1].split("</table>", 1)[0]
            for row in re.findall(r"<tr>\s*(<td.*?)</tr>", table, flags=re.S):
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
                rows.append([re.sub(r"<[^>]+>", "", cell).strip() for cell in cells])
        found[heading] = rows
    return found


ASSESS_4 = "Applicability of 4 Airworthiness Directives to Assess"
NO_REVIEW = "Maintenance Programme Annual Review Not Recorded"
NO_DATA = "No Maintenance Data Recorded for This Type Rating"

CONTINUING_AIRWORTHINESS = [
    ["G-DGHI", "Unserviceable, Stabilator Trim Cable", "Grounded Since 14 November 2026", "",
     "Unserviceable", "Aircraft"],
    ["G-ABCD", NO_REVIEW, "Not Set", "", "", "Maintenance Programme"],
    ["G-BXYZ", NO_REVIEW, "Not Set", "", "", "Maintenance Programme"],
    ["G-DGHI", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
    ["G-EJKL", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
    ["G-FMNO", NO_REVIEW, "Not Set", "", "", "Maintenance Programme"],
    ["G-ABCD", "Certificate of Release to Service Not Yet in Records", "21 November 2026",
     "3 Days", "Due Soon", "Release to Service"],
    ["G-CDEF", "Copy of Review Certificate to the Civil Aviation Authority", "21 November 2026",
     "3 Days", "Due Soon", "Airworthiness Review"],
    ["G-EJKL", "Airworthiness Review Certificate Expires", "6 December 2026", "18 Days",
     "Due Soon", "Airworthiness Review"],
    ["G-ABCD", "Applicability of 1 Airworthiness Directive to Assess", "Not Set", "",
     "To Assess", "Airworthiness Directives"],
    ["G-BXYZ", ASSESS_4, "Not Set", "", "To Assess", "Airworthiness Directives"],
    ["G-CDEF", ASSESS_4, "Not Set", "", "To Assess", "Airworthiness Directives"],
    ["G-DGHI", ASSESS_4, "Not Set", "", "To Assess", "Airworthiness Directives"],
    ["G-EJKL", ASSESS_4, "Not Set", "", "To Assess", "Airworthiness Directives"],
    ["G-FMNO", ASSESS_4, "Not Set", "", "To Assess", "Airworthiness Directives"],
    ["G-HKLM", ASSESS_4, "Not Set", "", "To Assess", "Airworthiness Directives"],
    ["G-HKLM", "Transfer In, Records 14 of 18 Received", "Not Set", "", "", "Transfers"],
]  # fmt: skip

PEOPLE = [
    ["[Review Name]", "Airworthiness Review Staff Recency Lapses", "2 December 2026", "14 Days",
     "Due Soon", "Authorisations"],
]  # fmt: skip

DOCUMENTATION = [
    ["Grob G 115 Maintenance Manual", "Maintenance Data Amendment to Check", "20 November 2026",
     "2 Days", "Due Soon", "Maintenance Data"],
    ["CAP 747 Mandatory Requirements for Airworthiness", "Maintenance Data Amendment to Check",
     "30 November 2026", "12 Days", "Due Soon", "Maintenance Data"],
    ["Cessna/Reims-Cessna 152/F152 Series (Lycoming)", NO_DATA, "Not Set", "", "",
     "Maintenance Data"],
    ["Piper PA-28 Series (Lycoming)", NO_DATA, "Not Set", "", "", "Maintenance Data"],
    ["Piper PA-38 Series Maintenance Manual", "Maintenance Data Not Held", "Not Set", "", "",
     "Maintenance Data"],
    ["Robin DR 400 series (Lycoming)", NO_DATA, "Not Set", "", "", "Maintenance Data"],
    ["[Supplementary Type Certificate Instructions]", "No Amendment Check Recorded", "Not Set",
     "", "", "Maintenance Data"],
]  # fmt: skip


def shown(rows: list[list[str]]) -> list[list[str]]:
    """Leave out the detail, which the script moves under the row."""
    return [[*row[:5], row[6]] for row in rows]


def test_the_dashboard_of_the_sample_on_18_november_2026(sample: Sample) -> None:
    """REQ-215 to REQ-217. Golden: every row, in order, worked by hand above."""
    body = page(signed_in(sample.reader), "/dashboard/")
    found = panels(body)
    assert list(found) == ["Continuing Airworthiness", "People", "Documentation", "Organisation"]
    assert shown(found["Continuing Airworthiness"]) == CONTINUING_AIRWORTHINESS
    assert shown(found["People"]) == PEOPLE
    assert shown(found["Documentation"]) == DOCUMENTATION
    assert found["Organisation"] == []
    assert "<p>Nothing Due</p>" in body.split("<h2>Organisation</h2>", 1)[1]
    # The detail says where each figure comes from.
    details = {(row[0], row[1]): row[5] for row in found["Continuing Airworthiness"]}
    assert details["G-ABCD", "Certificate of Release to Service Not Yet in Records"] == (
        "Right Main Tyre Replaced, 22 October 2026, Within 30 Days, ML.A.305(a)"
    )
    assert details["G-CDEF", "Copy of Review Certificate to the Civil Aviation Authority"] == (
        "Issued 11 November 2026, Within 10 Days, ML.A.903(f)"
    )
    assert details["G-ABCD", NO_REVIEW] == "At Least Annually, ML.A.302(c)(9)"
    # A type rating with no data names the aircraft it leaves without any.
    documents = {(row[0], row[1]): row[5] for row in found["Documentation"]}
    assert documents["Piper PA-28 Series (Lycoming)", NO_DATA] == "G-ABCD, G-DGHI"
    assert documents["Robin DR 400 series (Lycoming)", NO_DATA] == "G-CDEF"
    # Amber for what is due soon or waiting, red for what stops the aircraft (REQ-193).
    assert dot("Unserviceable") in body
    assert dot("Due Soon") in body
    assert dot("To Assess") in body
    assert "status-ok" not in body


def test_the_dashboard_stands_at_the_head_of_the_sidebar_and_links_to_each_page(
    sample: Sample,
) -> None:
    """REQ-202, REQ-215. Outside the groups; each row links to the page that holds it."""
    body = page(signed_in(sample.reader), "/dashboard/")
    sidebar = body.split('<nav aria-label="Sections">', 1)[1].split("</nav>", 1)[0]
    first = re.findall(r'<a href="([^"]+)"(?: aria-current="page")?>([^<]+)</a>', sidebar)[0]
    assert first == ("/dashboard/", "Dashboard")
    assert sidebar.index("Dashboard") < sidebar.index("<h2>")
    crumb = body.split('aria-label="Location"', 1)[1].split("</nav>", 1)[0]
    assert crumb.count("<li>") == 1
    assert '<h1 class="visually-hidden">Dashboard</h1>' in body
    with working_for(sample.ours.id, sample.reader.id):
        rows = [row for panel in services.dashboard(sample.ours, TODAY) for row in panel.rows]
    assert len(rows) == 25
    client = signed_in(sample.reader)
    for row in rows:
        assert f'<a href="{row.url}">{row.page}</a>' in body
        assert get(client, row.url).status_code == 200, row.url
    assert {row.url for row in rows if row.page == "Transfers"} == {"/transfers/"}


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_every_role_reads_the_dashboard_and_it_writes_nothing(sample: Sample, role: str) -> None:
    """REQ-006, REQ-215. View Records is enough; reading it changes no record."""
    with as_owner():
        before = Event.objects.count()
    assert get(signed_in(getattr(sample, role)), "/dashboard/").status_code == 200
    with as_owner():
        assert Event.objects.count() == before


def test_another_organisation_sees_nothing_of_ours(sample: Sample) -> None:
    """REQ-003."""
    body = page(signed_in(sample.stranger), "/dashboard/")
    assert "G-" not in body
    assert "[Review Name]" not in body
    assert "Grob" not in body
    found = panels(body)
    assert all(rows == [] for rows in found.values())
    assert body.count("<p>Nothing Due</p>") == 4


def test_an_item_is_shown_from_its_lead_time(sample: Sample) -> None:
    """REQ-212, REQ-216. G-ABCD's 50-hour check has 12.4 hours remaining.

    It is due at 6,425.0 hours. With the lead time at 15.0 hours it is Due
    Soon and is shown. At 0.8 hours a day 12.4 hours is 15 days, so it comes
    after what is due in 3 days and before the certificate due in 18.
    """
    with working_for(sample.ours.id, sample.administrator.id):
        configuration.set_lead_times(
            Organisation.objects.get(),
            due_soon_days=30,
            due_soon_hours=15,  # type: ignore[arg-type]
            due_soon_cycles=10,
            review_alert_days=None,
        )
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    rows = shown(found["Continuing Airworthiness"])
    check = ["G-ABCD", "50-Hour Check", "6,425.0 Hours", "12.4 Hours", "Due Soon",
             "Maintenance Programme"]  # fmt: skip
    assert rows == [*CONTINUING_AIRWORTHINESS[:8], check, *CONTINUING_AIRWORTHINESS[8:]]


def test_what_is_overdue_is_red_and_comes_first(sample: Sample, day: Day) -> None:
    """REQ-193, REQ-216. On 22 November 2026 both 21 November deadlines are 1 day past.

    The Grob manual's check, due by 20 November, is 2 days past. G-EJKL's
    certificate has 14 days left and [Review Name] 10.
    """
    day.today = date(2026, 11, 22)
    body = page(signed_in(sample.reader), "/dashboard/")
    found = panels(body)
    first = shown(found["Continuing Airworthiness"])[:9]
    assert first == [
        ["G-ABCD", "Certificate of Release to Service Not Yet in Records", "21 November 2026",
         "1 Day Overdue", "Overdue", "Release to Service"],
        ["G-CDEF", "Copy of Review Certificate to the Civil Aviation Authority",
         "21 November 2026", "1 Day Overdue", "Overdue", "Airworthiness Review"],
        ["G-DGHI", "Unserviceable, Stabilator Trim Cable", "Grounded Since 14 November 2026", "",
         "Unserviceable", "Aircraft"],
        ["G-ABCD", NO_REVIEW, "Not Set", "", "", "Maintenance Programme"],
        ["G-BXYZ", NO_REVIEW, "Not Set", "", "", "Maintenance Programme"],
        ["G-DGHI", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
        ["G-EJKL", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
        ["G-FMNO", NO_REVIEW, "Not Set", "", "", "Maintenance Programme"],
        ["G-EJKL", "Airworthiness Review Certificate Expires", "6 December 2026", "14 Days",
         "Due Soon", "Airworthiness Review"],
    ]  # fmt: skip
    assert shown(found["Documentation"])[0] == [
        "Grob G 115 Maintenance Manual", "Maintenance Data Amendment to Check",
        "20 November 2026", "2 Days Overdue", "Overdue", "Maintenance Data",
    ]  # fmt: skip
    assert shown(found["People"])[0][2:5] == ["2 December 2026", "10 Days", "Due Soon"]
    assert dot("Overdue") in body


def test_a_day_that_is_due_today_is_due_and_not_overdue(sample: Sample, day: Day) -> None:
    """REQ-216. Readings Kept as Built: a calendar limit with 0 days remaining is Due."""
    day.today = date(2026, 11, 21)
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    rows = {(row[0], row[1]): row[2:5] for row in shown(found["Continuing Airworthiness"])}
    assert rows["G-ABCD", "Certificate of Release to Service Not Yet in Records"] == [
        "21 November 2026",
        "0 Days",
        "Due",
    ]


def test_an_aircraft_with_no_review_certificate_recorded_is_shown(sample: Sample) -> None:
    """REQ-216. Nobody knows where it stands, so it is never left off."""
    with working_for(sample.ours.id, sample.lucy.id):
        aircraft_services.add_aircraft(
            organisation=sample.ours,
            registration="G-NEWA",
            type_rating="[Type Rating]",
            owner="[New Owner Name]",
        )
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    rows = shown(found["Continuing Airworthiness"])
    assert ["G-NEWA", "No Airworthiness Review Certificate Recorded", "Not Set", "", "",
            "Airworthiness Review"] in rows  # fmt: skip


# Rows the independent review of 24 November 2026 found with no test, and the three
# it found missing (finding 7). Each is worked by hand from SampleData.md.


def continuing(sample: Sample) -> dict[tuple[str, str], list[str]]:
    """Return the rows of Continuing Airworthiness by what each is about and what it is."""
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    return {(row[0], row[1]): row[2:] for row in found["Continuing Airworthiness"]}


def test_a_programme_never_reviewed_is_shown_until_a_review_is_recorded(sample: Sample) -> None:
    """REQ-053, REQ-216, finding 7. G-ABCD's programme has no annual review recorded; its
    own page says Not Recorded. The Dashboard shows it until one is. Recorded on
    18 November 2026 the next is due 18 November 2027, a year away, and is not shown."""
    rows = continuing(sample)
    assert rows["G-ABCD", NO_REVIEW] == [
        "Not Set",
        "",
        "",
        "At Least Annually, ML.A.302(c)(9)",
        "Maintenance Programme",
    ]
    assert ("G-CDEF", NO_REVIEW) not in rows
    with working_for(sample.ours.id, sample.reader.id):
        abcd = Aircraft.objects.get(registration="G-ABCD")
    programme = page(signed_in(sample.reader), f"/aircraft/{abcd.id}/programme/")
    assert "<dt>Last Reviewed</dt><dd>Not Recorded</dd>" in programme
    with working_for(sample.ours.id, sample.lucy.id):
        programme_services.record_review(Programme.objects.get(aircraft=abcd), TODAY)
    rows = continuing(sample)
    assert ("G-ABCD", NO_REVIEW) not in rows
    assert ("G-ABCD", "Maintenance Programme Annual Review") not in rows
    assert ("G-BXYZ", NO_REVIEW) in rows


def test_the_annual_review_of_a_programme_is_shown_from_its_lead_time(
    sample: Sample, day: Day
) -> None:
    """REQ-053, REQ-216, ML.A.302(c)(9). G-CDEF's programme was reviewed on 11 November
    2026: the next is due 11 November 2027. By hand: 12 October 2027 is 30 days
    before (19 to the end of October, 11 in November), 11 October is 31, and
    12 November 2027 is 1 day after."""
    item = ("G-CDEF", "Maintenance Programme Annual Review")
    day.today = date(2027, 10, 11)
    assert item not in continuing(sample)
    day.today = date(2027, 10, 12)
    assert continuing(sample)[item] == [
        "11 November 2027",
        "30 Days",
        "Due Soon",
        "At Least Annually, ML.A.302(c)(9)",
        "Maintenance Programme",
    ]
    day.today = date(2027, 11, 12)
    assert continuing(sample)[item][:3] == ["11 November 2027", "1 Day Overdue", "Overdue"]


def test_a_non_part_21_aircraft_says_its_tasks_are_not_calculated(sample: Sample) -> None:
    """REQ-022, REQ-216, finding 7. Nothing is calculated for a Non-Part 21 aircraft, so
    none of its tasks can show as due. The Dashboard says so, as the aircraft's own
    pages do. It is not told to set up a programme whose tasks would not be
    calculated, and its review certificate is shown as any other's is."""
    with working_for(sample.ours.id, sample.lucy.id):
        other = aircraft_services.add_aircraft(
            organisation=sample.ours,
            registration="G-NONP",
            type_rating="[Type Rating]",
            owner="[New Owner Name]",
            regime=Regime.NON_PART_21,
        )
    wording = "Calculations Not Yet Supported for Non-Part 21 Aircraft"
    rows = continuing(sample)
    assert rows["G-NONP", wording] == [
        "Not Set",
        "",
        "",
        "Tasks Are Not Calculated",
        "Maintenance Programme",
    ]
    assert ("G-NONP", "No Maintenance Programme Set Up") not in rows
    assert ("G-NONP", "No Airworthiness Review Certificate Recorded") in rows
    assert not [key for key in rows if key[1] == wording and key[0] != "G-NONP"]
    reader = signed_in(sample.reader)
    for path in (f"/aircraft/{other.id}/", f"/aircraft/{other.id}/programme/"):
        assert f"<p>{wording}</p>" in page(reader, path)


def test_a_task_that_cannot_be_calculated_is_shown_first_and_never_as_not_due(
    sample: Sample,
) -> None:
    """REQ-043, REQ-216, hazard H-018. A task of G-ABCD on an engine with no hours
    recorded cannot be calculated: nobody knows where it stands, so it is shown,
    with what is missing, before everything but what is red."""
    with working_for(sample.ours.id, sample.lucy.id):
        abcd = Aircraft.objects.get(registration="G-ABCD")
        engine = aircraft_services.add_counter(abcd, CounterKind.ENGINE, "Engine 1")
        programme_services.add_task(
            Programme.objects.get(aircraft=abcd),
            title="[Engine Task]",
            kind=TaskKind.PROGRAMME_TASK,
            counter=engine,
            source="[Maintenance Manual Reference]",
            interval=Interval(hours=Decimal("100")),
            starts=Reading(date(2026, 1, 1), Decimal("0.0"), 0),
        )
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    rows = found["Continuing Airworthiness"]
    task = next(row for row in rows if row[1] == "[Engine Task]")
    assert task == [
        "G-ABCD",
        "[Engine Task]",
        "Cannot Be Calculated",
        "",
        "",
        "No Hours Recorded for Engine 1",
        "Maintenance Programme",
    ]
    # After the Unserviceable aircraft, which is red, and before anything that has a day.
    assert rows.index(task) < [row[1] for row in rows].index(
        "Certificate of Release to Service Not Yet in Records"
    )
    assert rows[0][4] == "Unserviceable"


def test_a_limit_passed_within_its_tolerance_is_past_the_limit_and_not_overdue(
    sample: Sample, day: Day
) -> None:
    """REQ-056, REQ-216. G-FMNO's annual check is due 4 February 2027, and its tolerance
    of 1 month ends 4 March 2027. On 20 February 2027 it is 16 days past the limit,
    Within Tolerance, amber. On 5 March 2027 it is 29 days overdue, red."""
    item = ("G-FMNO", "Annual Check")
    day.today = date(2027, 2, 20)
    assert continuing(sample)[item][:3] == [
        "4 February 2027",
        "16 Days Past the Limit",
        "Within Tolerance",
    ]
    day.today = date(2027, 3, 5)
    assert continuing(sample)[item][:3] == ["4 February 2027", "29 Days Overdue", "Overdue"]


def test_review_staff_whose_recency_has_lapsed_are_shown_as_lapsed(
    sample: Sample, day: Day
) -> None:
    """REQ-113, REQ-217, AMC1 CAO.A.045(c) and (d). [Review Name]'s recency lapses after
    2 December 2026. On that day it has 0 days left; on 3 December it has lapsed,
    and stays shown, red, until a restoration is recorded."""
    day.today = date(2026, 12, 2)
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    assert shown(found["People"])[0] == [
        "[Review Name]",
        "Airworthiness Review Staff Recency Lapses",
        "2 December 2026",
        "0 Days",
        "Due",
        "Authorisations",
    ]
    day.today = date(2026, 12, 3)
    body = page(signed_in(sample.reader), "/dashboard/")
    lapsed = panels(body)["People"][0]
    assert lapsed == [
        "[Review Name]",
        "Airworthiness Review Staff Recency Lapsed",
        "2 December 2026",
        "",
        "Overdue",
        "Restored by 1 Review Under Supervision, AMC1 CAO.A.045(d)",
        "Authorisations",
    ]
    assert dot("Overdue") in body


def test_maintenance_data_held_and_current_is_left_out(sample: Sample) -> None:
    """REQ-083, REQ-217. The Grob manual's amendment check is due by 20 November 2026 and
    is shown. Checked on 18 November with the next due by 1 March 2027, it is held
    and current, 103 days from its next check, and is left out."""
    title = "Grob G 115 Maintenance Manual"
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    assert title in [row[0] for row in found["Documentation"]]
    with working_for(sample.ours.id, sample.planner.id):
        data_services.record_check(
            DataSet.objects.get(title=title),
            checked_by=sample.planner,
            checked_on=TODAY,
            result="No Amendment",
            next_due=date(2027, 3, 1),
        )
    found = panels(page(signed_in(sample.reader), "/dashboard/"))
    assert title not in [row[0] for row in found["Documentation"]]
    assert "Held and Current" not in [row[1] for row in found["Documentation"]]
    assert len(found["Documentation"]) == len(DOCUMENTATION) - 1


def test_data_recorded_for_a_type_rating_takes_its_row_away(sample: Sample) -> None:
    """REQ-089, REQ-217, finding 7. Once data is recorded for the Robin DR 400, G-CDEF's
    type rating is no longer shown as having none; the data itself is shown if it
    is not held and current."""
    with working_for(sample.ours.id, sample.planner.id):
        data_services.record_data(
            organisation=sample.ours,
            title="[Robin Maintenance Manual]",
            author="[Type Certificate Holder]",
            kind=DataKind.INSTRUCTIONS,
            applies_to=["Robin DR 400 series (Lycoming)"],
            held=False,
        )
    rows = panels(page(signed_in(sample.reader), "/dashboard/"))["Documentation"]
    assert "Robin DR 400 series (Lycoming)" not in [row[0] for row in rows]
    assert ["[Robin Maintenance Manual]", "Maintenance Data Not Held"] in [row[:2] for row in rows]


def test_a_problem_is_shown_until_it_is_solved(sample: Sample) -> None:
    """REQ-172, REQ-217. An entry of the problem log is shown while it is Open or has
    an action taken, and is left out once its solution is recorded."""
    with working_for(sample.ours.id, sample.planner.id):
        problem = acceptance_services.add_problem(
            organisation=sample.ours, raised_by=sample.planner, problem="[Problem Found]"
        )

    def organisation_rows() -> list[list[str]]:
        return panels(page(signed_in(sample.reader), "/dashboard/"))["Organisation"]

    assert [row[1] for row in organisation_rows()] == ["Problem Log Entry, Open"]
    assert organisation_rows()[0][5:] == ["[Problem Found]", "Records"]
    with working_for(sample.ours.id, sample.planner.id):
        acceptance_services.add_note(
            problem, kind=NoteKind.ACTION, text="[Action Taken]", noted_by=sample.planner
        )
    assert [row[1] for row in organisation_rows()] == ["Problem Log Entry, Action Taken"]
    with working_for(sample.ours.id, sample.planner.id):
        acceptance_services.add_note(
            problem, kind=NoteKind.SOLUTION, text="[Solution Found]", noted_by=sample.planner
        )
    assert organisation_rows() == []


def test_an_import_is_shown_until_every_value_of_it_is_checked(sample: Sample) -> None:
    """REQ-171, REQ-217, CAP 562 C-90. A file of one aircraft is loaded by Lucy Grant:
    It is shown until each value of it is checked, the hours and cycles by
    a second person, and then left out."""
    row = ("G-NEWB", "[Type Rating]", "", "", "", "[New Owner Name]", "2026-11-18", "100.0", "0")
    with working_for(sample.ours.id, sample.lucy.id):
        loaded = import_services.load(
            organisation=sample.ours,
            by=sample.lucy,
            kind=LoadKind.AIRCRAFT,
            source="[Logbooks]",
            file_name="file.csv",
            content=csv_of(AIRCRAFT, row),
        )
        values = list(LoadedValue.objects.filter(load=loaded))

    def organisation_rows() -> list[list[str]]:
        return panels(page(signed_in(sample.reader), "/dashboard/"))["Organisation"]

    assert [row[:2] for row in organisation_rows()] == [
        ["Aircraft and Totals", "Imported Records to Check"]
    ]
    second = {"Airframe Hours", "Airframe Cycles"}
    with working_for(sample.ours.id, sample.lucy.id):
        import_services.record_checks(
            loaded,
            by=sample.lucy,
            agreed=[str(value.id) for value in values if value.field not in second],
            differing={},
        )
    # Some checked and not all: still shown.
    assert [row[1] for row in organisation_rows()] == ["Imported Records to Check"]
    with working_for(sample.ours.id, sample.planner.id):
        import_services.record_checks(
            loaded,
            by=sample.planner,
            agreed=[str(value.id) for value in values if value.field in second],
            differing={},
        )
    assert organisation_rows() == []
