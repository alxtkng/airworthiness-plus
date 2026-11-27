"""The sample organisation, seeded by the command, compared with SampleData.md (Step 9).

Every figure below was worked by hand from design-system/SampleData.md
before it was compared with what the pages show; the working is in
assurance/dogfooding.md. Today in the sample world is 18 November 2026.
"""

import re
import secrets
from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.reviews.models import Certificate
from tests.conftest import as_owner
from tests.support import TODAY, signed_in

pytestmark = pytest.mark.django_db
PASSWORD = secrets.token_urlsafe(18)


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    monkeypatch.setattr("getpass.getpass", lambda prompt: PASSWORD)


@pytest.fixture
def seeded() -> dict[str, Aircraft]:
    with as_owner():
        call_command("seed_sample_organisation")
        return {aircraft.registration: aircraft for aircraft in Aircraft.objects.all()}


@pytest.fixture
def reader(seeded: dict[str, Aircraft]) -> Client:
    with as_owner():
        user = User.objects.get(full_name="[Read Only Name]")
    return signed_in(user)


def rows(client: Client, path: str) -> list[list[str]]:
    """Return every table row of a page as the words in its cells."""
    response: HttpResponse = client.get(path, secure=True)  # type: ignore[assignment]
    assert response.status_code == 200, path
    found = []
    for row in re.findall(r"<tr>(.*?)</tr>", response.content.decode(), flags=re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
        words = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cell)).strip() for cell in cells]
        if words:
            found.append(words)
    return found


def row_of(table: list[list[str]], first: str, second: str | None = None) -> list[str]:
    matches = [r for r in table if r[0] == first and (second is None or r[1] == second)]
    assert len(matches) == 1, (first, second, len(matches))
    return matches[0]


# The command


def test_the_command_sets_up_the_sample_once(seeded: dict[str, Aircraft]) -> None:
    """Step 9. One organisation, its people and its fleet; a second run is refused."""
    with as_owner():
        organisation = Organisation.objects.get()
        assert (organisation.name, organisation.approval_reference) == (
            "[Your Organisation]",
            "UK.CAO.[Number]",
        )
        people = {user.full_name: user for user in User.objects.all()}
        assert sorted(people) == [
            "Lucy Grant",
            "[Accountable Manager]",
            "[Planning and Records Name]",
            "[Read Only Name]",
            "[Review Name]",
        ]
        # Only the Administrator can sign in, with the password typed at the prompt.
        assert people["[Accountable Manager]"].check_password(PASSWORD)
        assert not any(
            user.has_usable_password()
            for name, user in people.items()
            if name != "[Accountable Manager]"
        )
        assert chain.problems(Event.objects.all()) == []
        with pytest.raises(CommandError, match="already set up"):
            call_command("seed_sample_organisation")
    assert sorted(seeded) == [
        "G-ABCD",
        "G-BXYZ",
        "G-CDEF",
        "G-DGHI",
        "G-EJKL",
        "G-FMNO",
        "G-HKLM",
    ]


def test_a_weak_password_sets_nothing_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Threat TH-001. The whole set-up is one transaction."""
    monkeypatch.setattr("getpass.getpass", lambda prompt: "short")
    with as_owner():
        with pytest.raises(CommandError, match="too short"):
            call_command("seed_sample_organisation")
        assert Organisation.objects.count() == 0
        assert User.objects.count() == 0


# SampleData.md, Fleet


def test_the_fleet_is_the_fleet_of_the_sample(reader: Client) -> None:
    """SampleData.md, Fleet: every cell of every row. One difference is known and recorded:
    the sample writes 220 Hours for G-CDEF and the system writes hours to one decimal place.
    Next Due and Remaining are two columns, as the Fleet board has them (REQ-280)."""
    table = {row[0]: row[1:8] for row in rows(reader, "/")}
    assert table == {
        "G-DGHI": [
            "Piper PA-28 Series (Lycoming)",
            "Flying Club",
            "Unserviceable, Stabilator Trim Cable",
            "Rectify Defect",
            "Grounded",
            "19 May 2027",
            "9,874.3",
        ],
        "G-EJKL": [
            "Cessna/Reims-Cessna 152/F152 Series (Lycoming)",
            "Pilot-Owner",
            "Serviceable",
            "Airworthiness Review",
            "18 Days",
            "6 December 2026",
            "11,206.8",
        ],
        "G-ABCD": [
            "Piper PA-28 Series (Lycoming)",
            "Pilot-Owner",
            "Serviceable",
            "50-Hour Check",
            "12.4 Hours",
            "14 March 2027",
            "6,412.6",
        ],
        "G-BXYZ": [
            "Cessna/Reims-Cessna 172/F172 Series (Lycoming)",
            "Syndicate of 6",
            "Serviceable",
            "100-Hour or Annual Check",
            "41.0 Hours",
            "2 August 2027",
            "3,318.0",
        ],
        "G-FMNO": [
            "Grob G115/120 Series (Lycoming)",
            "Pilot-Owner",
            "Serviceable",
            "Annual Check",
            "78 Days",
            "27 April 2027",
            "4,950.2",
        ],
        "G-CDEF": [
            "Robin DR 400 series (Lycoming)",
            "Syndicate of 4",
            "Serviceable",
            "Engine Overhaul",
            "220.0 Hours",
            "2 December 2027",
            "7,731.5",
        ],
    }
    transfer = row_of(rows(reader, "/transfers/"), "G-HKLM")
    assert transfer[1:4] == [
        "Piper PA-38 Series (Lycoming)",
        # SampleData.md was corrected on 24 November 2026 from the Customers board: the
        # owner of G-HKLM is a pilot-owner, and [Owner Name G-HKLM] is the customer's name.
        "Pilot-Owner",
        "Records 14 of 18 Received",
    ]


# SampleData.md, Maintenance Programme Inputs


def test_the_due_items_are_those_worked_by_hand(
    seeded: dict[str, Aircraft], reader: Client
) -> None:
    """SampleData.md, Maintenance Programme Inputs. Limit, due, remaining, tolerance, first."""
    abcd = rows(reader, f"/aircraft/{seeded['G-ABCD'].id}/programme/")
    assert row_of(abcd, "50-Hour Check")[1:4] == ["Hours", "6,425.0 Hours", "12.4 Hours"]
    # The tyre: replaced 22 October 2026, release to be in the records by 21 November.
    tyre = row_of(abcd, "22 October 2026")
    assert tyre[1:3] == ["Right Main Tyre Replaced", "6,390.0"]
    assert tyre[3].startswith("To Be Recorded by 21 November 2026, Due Soon")
    # Work done before these records began is not shown as entered late.
    inspected = row_of(abcd, "20 July 2026")
    assert inspected[3] == "[Release Reference 4], Recorded 20 July 2026"

    bxyz = rows(reader, f"/aircraft/{seeded['G-BXYZ'].id}/programme/")
    assert row_of(bxyz, "100-Hour or Annual Check", "Hours")[2:] == [
        "3,359.0 Hours",
        "41.0 Hours",
        "3,369.0 Hours",
        "",
        "Projected First",
    ]
    assert row_of(bxyz, "100-Hour or Annual Check", "Calendar")[2:] == [
        "30 July 2027",
        "254 Days",
        "30 August 2027, After the Review Certificate Ends 2 August 2027",
        "",
        "",
    ]
    fmno = rows(reader, f"/aircraft/{seeded['G-FMNO'].id}/programme/")
    assert row_of(fmno, "Annual Check", "Hours")[2:] == [
        "5,012.0 Hours",
        "61.8 Hours",
        "5,022.0 Hours",
        "",
        "",
    ]
    assert row_of(fmno, "Annual Check", "Calendar")[2:] == [
        "4 February 2027",
        "78 Days",
        "4 March 2027",
        "",
        "Projected First",
    ]
    cdef = rows(reader, f"/aircraft/{seeded['G-CDEF'].id}/programme/")
    assert row_of(cdef, "Engine Overhaul")[1:4] == ["Hours", "2,000.0 Hours", "220.0 Hours"]


def test_the_fleet_opens_with_what_needs_attention_first(reader: Client) -> None:
    """Dogfooding D-5, decided 19 November 2026. The Unserviceable aircraft, then
    whatever is marked, then the soonest due.

    By hand. G-DGHI is Unserviceable. G-EJKL's review is 18 days away, which is
    Due Soon, and nothing else is marked. Then by days to what is next due:
    G-ABCD 12.4 hours at 0.8 a day is 15 days; G-FMNO 78 days; G-BXYZ 41.0
    hours at 0.5 a day is 82 days; G-CDEF 220.0 hours at 0.6 a day is 366
    days, rounded down.
    """
    order = [row[0] for row in rows(reader, "/")]
    assert order == ["G-DGHI", "G-EJKL", "G-ABCD", "G-FMNO", "G-BXYZ", "G-CDEF"]


def test_the_fleet_is_filtered_as_the_fleet_board_filters_it(reader: Client) -> None:
    """REQ-281. Golden, from the Fleet board: All 6, Due in 30 Days 3, Unserviceable 1.

    By hand, for 18 November 2026. G-DGHI is Unserviceable. G-EJKL's review is
    18 days away. G-ABCD's 12.4 hours at 0.8 a day are 15 days. The others are
    78, 82 and 366 days away: outside the 30.
    """
    response: HttpResponse = reader.get("/", secure=True)  # type: ignore[assignment]
    body = response.content.decode()
    filters = body.split('<p class="filter">', 1)[1].split("</p>", 1)[0]
    assert re.findall(r'<a href="([^"]*)"( aria-current="true")?>([^<]+)</a>', filters) == [
        ("/", ' aria-current="true"', "All 6"),
        ("/?show=due", "", "Due in 30 Days 3"),
        ("/?show=unserviceable", "", "Unserviceable 1"),
    ]
    assert [row[0] for row in rows(reader, "/?show=due")] == ["G-DGHI", "G-EJKL", "G-ABCD"]
    assert [row[0] for row in rows(reader, "/?show=unserviceable")] == ["G-DGHI"]
    # The view asked for is the one marked, and anything else shows every aircraft.
    due: HttpResponse = reader.get("/?show=due", secure=True)  # type: ignore[assignment]
    assert '<a href="/?show=due" aria-current="true">Due in 30 Days 3</a>' in due.content.decode()
    assert len(rows(reader, "/?show=anything")) == 6
    # The search is always shown above the Fleet, however few aircraft (REQ-282).
    assert '<table data-search="always">' in body
    # What remains is a column of its own (REQ-280).
    remaining = {row[0]: row[5] for row in rows(reader, "/")}
    assert remaining == {
        "G-DGHI": "Grounded",
        "G-EJKL": "18 Days",
        "G-ABCD": "12.4 Hours",
        "G-BXYZ": "41.0 Hours",
        "G-FMNO": "78 Days",
        "G-CDEF": "220.0 Hours",
    }
    # A reader may not add an aircraft, and is not shown the link (REQ-006).
    assert "Add an Aircraft" not in body.split("<main", 1)[1]


def test_what_is_due_in_30_days_at_its_edges(
    seeded: dict[str, Aircraft], reader: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-281. G-EJKL's certificate is valid to 6 December 2026: 30 days away on
    6 November it is among those due in 30 days, and 31 days away on 5 November it
    is not. An aircraft with something that cannot be calculated is always among
    them, and so is an Unserviceable one, whatever the days."""
    from airworthiness_plus.aircraft import services as aircraft_services
    from airworthiness_plus.aircraft.views import CANNOT_BE_CALCULATED, NOT_KNOWN, FleetRow

    def soon(rank: tuple[int, int, int, str]) -> bool:
        return FleetRow(seeded["G-ABCD"], None, "", "", None, rank).soon

    assert soon((1, -CANNOT_BE_CALCULATED, NOT_KNOWN, "G-ABCD"))
    assert soon((0, 0, 0, "G-ABCD"))
    assert soon((1, 0, 30, "G-ABCD")) and not soon((1, 0, 31, "G-ABCD"))
    assert not soon((1, -1, NOT_KNOWN, "G-ABCD"))

    def due_on(day: date) -> list[str]:
        monkeypatch.setattr(aircraft_services, "today", lambda: day)
        return sorted(row[0] for row in rows(reader, "/?show=due"))

    assert "G-EJKL" in due_on(date(2026, 11, 6))
    assert "G-EJKL" not in due_on(date(2026, 11, 5))


# SampleData.md, review certificates and review staff


def test_the_review_dates_are_those_worked_by_hand(reader: Client) -> None:
    """Day counts from 18 November 2026, each counted by hand in assurance/dogfooding.md."""
    schedule = {row[0]: row[2:] for row in rows(reader, "/reviews/")}
    assert schedule == {
        "G-EJKL": ["6 December 2026", "18 Days", "Due Soon", "Inside the 90-Day Window", ""],
        "G-ABCD": ["14 March 2027", "116 Days", "", "", ""],
        "G-FMNO": ["27 April 2027", "160 Days", "", "", ""],
        "G-DGHI": ["19 May 2027", "182 Days", "", "", ""],
        "G-BXYZ": ["2 August 2027", "257 Days", "", "", ""],
        "G-CDEF": [
            "2 December 2027",
            "379 Days",
            "",
            "",
            "To Be Sent by 21 November 2026, Due Soon",
        ],
    }
    assert list(schedule) == ["G-EJKL", "G-ABCD", "G-FMNO", "G-DGHI", "G-BXYZ", "G-CDEF"]
    staff = {row[0]: row[1:8] for row in rows(reader, "/review-staff/")}
    assert staff["Lucy Grant"][2:7] == [
        "11 November 2026",
        "0, Recorded 18 November 2026",
        "A Review in the Last 12 Months",
        "After 11 November 2027",
        "Current",
    ]
    assert staff["[Review Name]"][2:7] == [
        "2 December 2025",
        "4, Recorded 18 November 2026",
        "A Review in the Last 12 Months",
        "After 2 December 2026, Due Soon",
        "Current",
    ]


# Directive status and maintenance data


def test_lucy_grant_has_her_5_reviews_in_12_months(seeded: dict[str, Aircraft]) -> None:
    """SampleData.md, recency figures; Issue 71, D-3. Four from before these
    records, with the references they were issued with, and G-CDEF's issued here."""
    with as_owner():
        hers = list(
            Certificate.objects.filter(
                issued_by__user__full_name="Lucy Grant", issued_on__gt=date(2025, 11, 18)
            ).select_related("aircraft")
        )
    assert sorted(one.aircraft.registration for one in hers) == [
        "G-ABCD",
        "G-BXYZ",
        "G-CDEF",
        "G-DGHI",
        "G-FMNO",
    ]
    assert {one.reference for one in hers if not one.from_before_records} == {
        "UK.CAO.[Number]-ARC-0001"
    }
    assert all(one.serial_number is None for one in hers if one.from_before_records)


def test_the_directive_status_is_that_worked_by_hand(
    seeded: dict[str, Aircraft], reader: Client
) -> None:
    """First within 50 hours of 6,300.0, done at 6,350.0, then every 100: due at 6,450.0,
    37.4 hours from 6,412.6. Once within 3 months of 1 October 2026: 1 January 2027, 44 days."""
    status = {
        row[0]: row[1:8] for row in rows(reader, f"/aircraft/{seeded['G-ABCD'].id}/directives/")
    }
    assert status["[Directive Number 1]"][1] == "Applicable"
    assert status["[Directive Number 1]"][5] == "6,450.0 Hours, 37.4 Hours"
    assert status["[Directive Number 2]"][1:3] == [
        "Not Applicable",
        "Propeller Model Not Fitted, Logbook Checked",
    ]
    assert status["[Directive Number 3]"][1] == "Applicability to Assess"
    assert status["[Directive Number 3]"][6] == "To Assess"
    assert status["[Directive Number 4]"][5] == "1 January 2027, 44 Days"
    # Every directive is still to be assessed against every other aircraft.
    other = rows(reader, f"/aircraft/{seeded['G-EJKL'].id}/directives/")
    assert [row[2] for row in other] == ["Applicability to Assess"] * 4


def test_the_maintenance_data_is_that_of_the_sample(
    seeded: dict[str, Aircraft], reader: Client
) -> None:
    """SampleData.md, Documentation, Maintenance data."""
    data = {row[0]: row for row in rows(reader, "/maintenance-data/")}
    grob = data["Grob G 115 Maintenance Manual"]
    assert (grob[9], grob[10], grob[11]) == (
        "2 November 2026, [Planning and Records Name]",
        "20 November 2026",
        "Due Soon",
    )
    cap = data["CAP 747 Mandatory Requirements for Airworthiness"]
    assert cap[9].startswith("16 November 2026")
    assert data["Piper PA-38 Series Maintenance Manual"][6] == "Not Held"
    owner = data["[Supplementary Type Certificate Instructions]"]
    assert owner[8] == "Provided by Syndicate of 6, Written Confirmation, 2 June 2026"
    needed = rows(reader, f"/aircraft/{seeded['G-HKLM'].id}/maintenance-data/")
    assert [(row[0], row[6]) for row in needed] == [
        ("Piper PA-38 Series Maintenance Manual", "Not Held")
    ]
