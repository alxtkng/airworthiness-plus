"""Maintenance Programmes across the fleet (REQ-283).

The Maintenance Programmes board's list, with the sample of
design-system/SampleData.md. Today in the sample is 18 November 2026.

By hand:

- G-ABCD and G-CDEF are on the design approval holder's instructions; G-BXYZ
  and G-FMNO on the Minimum Inspection Programme. G-DGHI and G-EJKL have no
  programme set up.
- Only G-CDEF's programme has an annual review recorded, on 11 November
  2026. ML.A.302(c)(9): at least annually, so by 11 November 2027. From
  18 November 2026 that is 365 days less 7: 358 days.
"""

from datetime import date

import pytest

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.sample import build
from tests.support import Sample, dot, make_sample, page, signed_in
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
    build.add_programmes(sample, fleet)
    return fleet


INSTRUCTIONS = "Design Approval Holder\N{RIGHT SINGLE QUOTATION MARK}s Instructions"
LISTED = [
    # From 27 November 2026 the list also has how many departures are in force, after
    # the tasks, and a review in progress, last (REQ-284, REQ-286): none of either here.
    ["G-ABCD", INSTRUCTIONS, "[Programme Reference]", "1", "0", "Not Recorded", "", "", "", ""],
    ["G-BXYZ", "Minimum Inspection Programme", "[Programme Reference]", "1", "0",
     "Not Recorded", "", "", "", ""],
    ["G-CDEF", INSTRUCTIONS, "[Programme Reference]", "1", "0", "11 November 2026",
     "11 November 2027", "358 Days", "", ""],
    ["G-DGHI", "No Maintenance Programme Set Up", "", "", "", "", "", "", "", ""],
    ["G-EJKL", "No Maintenance Programme Set Up", "", "", "", "", "", "", "", ""],
    ["G-FMNO", "Minimum Inspection Programme", "[Programme Reference]", "1", "0",
     "Not Recorded", "", "", "", ""],
]  # fmt: skip


def test_the_programmes_of_the_sample_on_18_november_2026(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-283. Golden: every aircraft of the Fleet with its programme and when its
    annual review is due. The Transfer In, G-HKLM, is not in the Fleet and not listed."""
    body = page(signed_in(sample.reader), "/programmes/")
    (rows,) = tables(body)
    assert [[cell.replace("&#x27;", "\N{RIGHT SINGLE QUOTATION MARK}") for cell in row]
            for row in rows] == LISTED  # fmt: skip
    assert (
        "<p>Minimum Inspection Programme: Annual or 100 Hours, Whichever First, "
        "Tolerance 1 Month or 10 Hours, ML.A.302(d)(1)</p>" in body
    )
    assert "<p>Reviewed at Least Annually, ML.A.302(c)(9)</p>" in body
    assert f'<a href="/aircraft/{fleet["G-CDEF"].id}/programme/">G-CDEF</a>' in body
    assert "<li>Continuing Airworthiness</li>" in body
    assert (
        '<li><a href="/programmes/" aria-current="location">Maintenance Programmes</a></li>' in body
    )


def test_the_annual_review_is_marked_as_it_falls_due(
    sample: Sample, fleet: dict[str, Aircraft], day: Day
) -> None:
    """REQ-283, ML.A.302(c)(9). G-CDEF's review is due by 11 November 2027: Due Soon
    from 12 October, 30 days before; Due on the day; Overdue the day after."""
    reader = signed_in(sample.reader)

    def cdef() -> list[str]:
        (rows,) = tables(page(reader, "/programmes/"))
        return next(row[6:9] for row in rows if row[0] == "G-CDEF")

    day.today = date(2027, 10, 11)
    assert cdef() == ["11 November 2027", "31 Days", ""]
    day.today = date(2027, 10, 12)
    assert cdef() == ["11 November 2027", "30 Days", "Due Soon"]
    day.today = date(2027, 11, 11)
    assert cdef() == ["11 November 2027", "0 Days", "Due"]
    day.today = date(2027, 11, 12)
    assert cdef() == ["11 November 2027", "1 Day Overdue", "Overdue"]
    assert dot("Overdue") in page(reader, "/programmes/")


def test_another_organisation_sees_none_of_our_programmes(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-003."""
    body = page(signed_in(sample.stranger), "/programmes/")
    assert "G-CDEF" not in body and "[Programme Reference]" not in body
    assert "<p>No Aircraft in the Fleet</p>" in body
