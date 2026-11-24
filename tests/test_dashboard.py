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
- G-HKLM is a Transfer In with 14 of 18 records received.
- [Review Name]'s recency lapses on 2 December 2026: 14 days.
- The Grob manual's amendment check is due by 20 November 2026 (2 days) and
  CAP 747's by 30 November 2026 (12 days). The Piper PA-38 manual is not
  held. The supplementary type certificate instructions have no check recorded.
"""

import re
from datetime import date

import pytest
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.dashboard import services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations import configuration
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.sample import build
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, make_sample, signed_in

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

CONTINUING_AIRWORTHINESS = [
    ["G-DGHI", "Unserviceable, Stabilator Trim Cable", "Grounded Since 14 November 2026", "",
     "Unserviceable", "Aircraft"],
    ["G-DGHI", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
    ["G-EJKL", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
    ["G-ABCD", "Certificate of Release to Service Not Yet in Records", "21 November 2026",
     "3 Days", "Due Soon", "Maintenance Programme"],
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
    ["Piper PA-38 Series Maintenance Manual", "Maintenance Data Not Held", "Not Set", "", "",
     "Maintenance Data"],
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
    assert len(rows) == 19
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
    assert rows == [*CONTINUING_AIRWORTHINESS[:5], check, *CONTINUING_AIRWORTHINESS[5:]]


def test_what_is_overdue_is_red_and_comes_first(sample: Sample, day: Day) -> None:
    """REQ-193, REQ-216. On 22 November 2026 both 21 November deadlines are 1 day past.

    The Grob manual's check, due by 20 November, is 2 days past. G-EJKL's
    certificate has 14 days left and [Review Name] 10.
    """
    day.today = date(2026, 11, 22)
    body = page(signed_in(sample.reader), "/dashboard/")
    found = panels(body)
    first = shown(found["Continuing Airworthiness"])[:6]
    assert first == [
        ["G-ABCD", "Certificate of Release to Service Not Yet in Records", "21 November 2026",
         "1 Day Overdue", "Overdue", "Maintenance Programme"],
        ["G-CDEF", "Copy of Review Certificate to the Civil Aviation Authority",
         "21 November 2026", "1 Day Overdue", "Overdue", "Airworthiness Review"],
        ["G-DGHI", "Unserviceable, Stabilator Trim Cable", "Grounded Since 14 November 2026", "",
         "Unserviceable", "Aircraft"],
        ["G-DGHI", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
        ["G-EJKL", "No Maintenance Programme Set Up", "Not Set", "", "", "Maintenance Programme"],
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
