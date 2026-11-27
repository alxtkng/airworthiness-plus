"""Departures, the annual review point by point, and the sources of directives.

REQ-284 to REQ-289: what the Maintenance Programmes and Airworthiness
Directives boards show beyond what was built. ML.A.302 and AMC1
ML.A.302(c)(9) were read in the UK text on 27 November 2026 (Decisions.md,
Regulation Facts in Use). Today in the sample is 18 November 2026.

By hand, for 18 November 2026 and a lead time of 30 days:

- G-DGHI's programme has 2 departures in force, each with its copy sent to
  the owner on 4 March 2026. It was last reviewed on 4 March 2026, so the
  next review is due by 4 March 2027, 106 days.
- G-FMNO's annual review was opened on 9 November 2026 and is 4 of 6
  complete: the revisions and the pilot-owners are open.
- Three sources of directives were checked on 16 November and are next
  checked on 30 November 2026, 12 days: Due Soon. CAP 747 is checked at
  each amendment, and has no day.
"""

import io
import json
import zipfile
from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.dashboard import services as dashboard_services
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.directives.models import Source
from airworthiness_plus.exports.build import build as build_export
from airworthiness_plus.history.models import Event, RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import services
from airworthiness_plus.programme.models import AnnualReview, Departure, Programme
from airworthiness_plus.sample import build, phase1
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, get, make_sample, page, post, signed_in
from tests.test_modifications import rows

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
    build.add_programmes(sample, fleet)
    phase1.add_programme_records(sample.ours, sample.lucy, fleet)
    phase1.add_sources(sample.ours, sample.planner)
    return fleet


def programme(sample: Sample, aircraft: Aircraft) -> Programme:
    with working_for(sample.ours.id, sample.reader.id):
        return Programme.objects.get(aircraft=aircraft)


DEPARTURE = {
    "task": "[Task]",
    "manufacturer": "[500 Hours]",
    "programme_says": "[On Condition]",
    "compensating_measures": "[Measures]",
    "justification": "[Justification]",
    "recorded_on": "2026-11-18",
}

# Departures


def test_the_departures_of_the_sample_on_18_november_2026(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-284. Golden: the board's two departures of G-DGHI's programme, and the
    count of them beside each programme on the list."""
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-DGHI'].id}/programme/")
    assert rows(body) == [
        ["Engine Overhaul, Lycoming O-360", "2,000 Hours or 12 Years",
         "On Condition, Reviewed Every 100 Hours",
         "Oil Analysis Every 50 Hours, Compression and Borescope Every 100 Hours",
         "Sent 4 March 2026", "Club Use, About 300 Hours a Year", "4 March 2026", "In Force"],
        ["Vacuum Pump Replacement", "500 Hours", "On Condition", "Standby Vacuum Source Fitted",
         "Sent 4 March 2026", "Pump Checked Every 50 Hours", "4 March 2026", "In Force"],
    ]  # fmt: skip
    listed = rows(page(signed_in(sample.reader), "/programmes/"))
    assert [(row[0], row[4]) for row in listed] == [
        ("G-ABCD", "0"),
        ("G-BXYZ", "0"),
        ("G-CDEF", "0"),
        ("G-DGHI", "2"),
        ("G-EJKL", ""),
        ("G-FMNO", "0"),
    ]
    dghi = next(row for row in listed if row[0] == "G-DGHI")
    # Last reviewed 4 March 2026: due 4 March 2027, 106 days from 18 November 2026.
    assert dghi[5:9] == ["4 March 2026", "4 March 2027", "106 Days", ""]
    fmno = next(row for row in listed if row[0] == "G-FMNO")
    assert fmno[9] == "Open, 4 of 6 Complete"


def test_a_departure_says_what_it_departs_from_and_why(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-284. ML.A.302(c)(8): the justification for any deviation is kept. Each part
    is required, by the form, the service and the database; a departure for the
    same task that is in force is recorded once."""
    client = signed_in(sample.lucy)
    address = f"/aircraft/{fleet['G-ABCD'].id}/programme/departures/add/"
    for missing in ("task", "manufacturer", "programme_says", "compensating_measures",
                    "justification"):  # fmt: skip
        refused = post(client, address, **{**DEPARTURE, missing: " "})
        assert "This field is required" in refused.content.decode(), missing
    for values, reason in (
        ({"recorded_on": "2026-11-19"}, "Not Recorded After Today"),
        ({"owner_copy_sent_on": "2026-11-17"}, "Sent on or After the Day Recorded"),
        ({"owner_copy_sent_on": "2026-11-19"}, "Sent on or After the Day Recorded"),
    ):
        assert reason in post(client, address, **{**DEPARTURE, **values}).content.decode()
    assert post(client, address, **DEPARTURE).status_code == 302
    assert "Already Recorded" in post(client, address, **DEPARTURE).content.decode()
    abcd = programme(sample, fleet["G-ABCD"])
    with working_for(sample.ours.id, sample.lucy.id):
        held = Departure.objects.get(programme=abcd)
        good: dict[str, Any] = {
            "organisation": sample.ours,
            "programme": abcd,
            "task": "[Another]",
            "manufacturer": "X",
            "programme_says": "X",
            "compensating_measures": "X",
            "justification": "X",
            "recorded_on": TODAY,
        }
        for altered, constraint in (
            ({"task": ""}, "departure_says_what_it_departs_from_and_why"),
            ({"manufacturer": ""}, "departure_says_what_it_departs_from_and_why"),
            ({"programme_says": ""}, "departure_says_what_it_departs_from_and_why"),
            ({"compensating_measures": ""}, "departure_says_what_it_departs_from_and_why"),
            ({"justification": ""}, "departure_says_what_it_departs_from_and_why"),
            ({"owner_copy_sent_on": date(2026, 11, 17)}, "departure_dates_follow"),
            ({"withdrawn_on": date(2026, 11, 17)}, "departure_dates_follow"),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Departure.objects.create(**{**good, **altered})
        assert Departure.objects.filter(programme=abcd).count() == 1
        with pytest.raises(RecordsAreNeverDeletedError):
            held.delete()


def test_a_departure_is_never_altered_and_its_dates_are_recorded_once(
    sample: Sample, fleet: dict[str, Aircraft], day: Day
) -> None:
    """REQ-285. The owner copy and the withdrawal are each recorded once. Nothing
    else of a departure changes, whoever asks. A withdrawn departure stays in the
    record and leaves the count."""
    client = signed_in(sample.lucy)
    aircraft = fleet["G-ABCD"]
    post(client, f"/aircraft/{aircraft.id}/programme/departures/add/", **DEPARTURE)
    with working_for(sample.ours.id, sample.lucy.id):
        held = Departure.objects.get(task="[Task]")
        for altered in (
            {"task": "[Altered]"},
            {"manufacturer": "[Altered]"},
            {"programme_says": "[Altered]"},
            {"compensating_measures": "[Altered]"},
            {"justification": "[Altered]"},
            {"recorded_on": date(2026, 11, 1)},
            {"programme": programme(sample, fleet["G-BXYZ"])},
        ):
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                Departure.objects.filter(pk=held.pk).update(**altered)
    day.today = date(2026, 11, 20)
    copy = f"/programmes/departures/{held.id}/owner-copy/"
    assert "Not After Today" in post(client, copy, on="2026-11-21").content.decode()
    assert "Not Before the Departure Was Recorded" in (
        post(client, copy, on="2026-11-17").content.decode()
    )
    assert post(client, copy, on="2026-11-19").status_code == 302
    again = post(client, copy, on="2026-11-20")
    assert again.status_code == 409 and "Already Recorded as Sent" in again.content.decode()
    withdraw = f"/programmes/departures/{held.id}/withdraw/"
    assert post(client, withdraw, on="2026-11-20").status_code == 302
    assert "This Departure Is Withdrawn" in post(client, withdraw, on="2026-11-20").content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        for dated in ({"owner_copy_sent_on": TODAY}, {"withdrawn_on": None}):
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                Departure.objects.filter(pk=held.pk).update(**dated)
        kept = Departure.objects.get(pk=held.pk)
        assert (kept.owner_copy_sent_on, kept.withdrawn_on) == (date(2026, 11, 19), day.today)
        assert Event.of(kept).count() == 3
    listed = rows(page(client, "/programmes/"))
    assert next(row[4] for row in listed if row[0] == "G-ABCD") == "0"
    # The same task may depart again once the first is withdrawn.
    again_form = {**DEPARTURE, "recorded_on": "2026-11-20"}
    assert post(
        client, f"/aircraft/{aircraft.id}/programme/departures/add/", **again_form
    ).status_code == (302)


# The annual review

POINTS = [
    ["Maintenance Results This Year", "2 Defects, No Repeats", "Complete",
     "AMC1 ML.A.302(c)(9)(a)(1)"],
    ["Last Airworthiness Review", "27 April 2026, Programme Adequate", "Complete",
     "AMC1 ML.A.302(c)(9)(a)(2)"],
    ["Minimum Inspection Programme and Manufacturer&#x27;s Revisions",
     "Maintenance Manual Revision [Revision] to Check", "Open", "AMC1 ML.A.302(c)(9)(a)(3)"],
    ["Configuration, Type and Operation", "No Change, Private Flying", "Complete",
     "AMC1 ML.A.302(c)(9)(a)(4)"],
    ["Pilot-Owners", "Awaiting Owner Confirmation", "Open", "AMC1 ML.A.302(c)(9)(a)(5)"],
    ["Directives, Airworthiness Limitations and Data Sheet", "Checked 16 November 2026",
     "Complete", "AMC1 ML.A.302(c)(9)(a)(6)"],
]  # fmt: skip


def test_the_annual_review_of_the_sample_is_four_of_six_complete(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-286. Golden: the board's Annual Review, G-FMNO, with the six points of
    AMC1 ML.A.302(c)(9)(a) each under its reference."""
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-FMNO'].id}/programme/")
    assert "<p>Opened 9 November 2026, 4 of 6 Complete</p>" in body
    points = body.split("<h2>Annual Review</h2>", 1)[1]
    assert rows("<main>" + points) == POINTS
    # A role that may not record the review is shown no form for it.
    assert "Complete the Review" not in body and "Save the Review" not in body
    assert "Complete the Review" in page(
        signed_in(sample.reviewer), f"/aircraft/{fleet['G-FMNO'].id}/programme/"
    )


def test_the_annual_review_is_not_completed_with_a_point_still_open(
    sample: Sample, fleet: dict[str, Aircraft], day: Day
) -> None:
    """REQ-287. Ours: Complete the Review is refused while a point is open, and says
    which. Once every point is complete the review is completed once, the programme
    is recorded as reviewed that day, and the next is due 12 months on."""
    aircraft = fleet["G-FMNO"]
    client = signed_in(sample.lucy)
    complete = f"/aircraft/{aircraft.id}/programme/annual-review/complete/"
    refused = post(client, complete, completed_on="2026-11-18")
    assert refused.status_code == 409
    assert (
        "Not Complete: Minimum Inspection Programme and Manufacturer&#x27;s Revisions; "
        "Pilot-Owners" in refused.content.decode()
    )
    assert programme(sample, aircraft).last_reviewed is None
    note = f"/aircraft/{aircraft.id}/programme/annual-review/"
    # A point that is complete says what was found.
    blank = post(client, note, pilot_owners_note="", pilot_owners_done="on")
    assert "Pilot-Owners: A Point That Is Complete Says What Was Found" in blank.content.decode()
    form = {}
    for name, (found, _) in phase1.FMNO_REVIEW.items():
        form[f"{name}_note"] = found
        form[f"{name}_done"] = "on"
    form["revisions_note"] = "Revision [Revision] Checked, No Change"
    assert post(client, note, **form).status_code == 302
    assert "6 of 6 Complete" in page(client, f"/aircraft/{aircraft.id}/programme/")
    assert "Not Completed Before It Was Opened" in (
        post(client, complete, completed_on="2026-11-08").content.decode()
    )
    assert "After Today" in post(client, complete, completed_on="2026-11-19").content.decode()
    assert post(client, complete, completed_on="2026-11-18").status_code == 302
    again = post(client, complete, completed_on="2026-11-18")
    assert again.status_code == 409 and "No Annual Review Is in Progress" in again.content.decode()
    assert programme(sample, aircraft).last_reviewed == TODAY
    body = page(client, f"/aircraft/{aircraft.id}/programme/")
    assert "Annual Review Completed 18 November 2026 by Lucy Grant" in body
    assert "No Annual Review in Progress" in body
    listed = rows(page(client, "/programmes/"))
    fmno = next(row for row in listed if row[0] == "G-FMNO")
    # 18 November 2026 and 12 months: 18 November 2027, 365 days.
    assert fmno[5:10] == ["18 November 2026", "18 November 2027", "365 Days", "", ""]


def test_a_completed_annual_review_keeps_what_it_said_and_who_completed_it(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-287. The database writes the name of whoever completed the review, as it
    then stood, and refuses any change afterwards: to the name, to a point or to
    the day. A later change of the person's name does not change it."""
    fmno = programme(sample, fleet["G-FMNO"])
    with working_for(sample.ours.id, sample.lucy.id):
        review = AnnualReview.objects.get(programme=fmno)
        # Not completed with a point open, whatever the application sends.
        with (
            pytest.raises(IntegrityError, match="completed_with_every_point_complete"),
            transaction.atomic(),
        ):
            AnnualReview.objects.filter(pk=review.pk).update(
                completed_on=TODAY, completed_by=sample.lucy
            )
        for altered, constraint in (
            ({"results_note": ""}, "point_complete_says_what_was_found"),
            ({"opened_on": date(2026, 11, 1)}, "keeps its programme and the day it was opened"),
            ({"programme": programme(sample, fleet["G-ABCD"])}, "keeps its programme"),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                AnnualReview.objects.filter(pk=review.pk).update(**altered)
        services.note_annual_review(review, revisions_done=True, pilot_owners_done=True)
        with (
            pytest.raises(IntegrityError, match="completed_with_every_point_complete"),
            transaction.atomic(),
        ):
            AnnualReview.objects.filter(pk=review.pk).update(completed_on=TODAY)
        AnnualReview.objects.filter(pk=review.pk).update(
            completed_on=TODAY, completed_by=sample.lucy, completed_by_name="[Somebody Else]"
        )
        review.refresh_from_db()
        assert review.completed_by_name == "Lucy Grant"
        fixed: tuple[dict[str, Any], ...] = (
            {"completed_by_name": "[Altered]"},
            {"completed_on": date(2026, 11, 17)},
            {"results_note": "[Altered]"},
            {"pilot_owners_done": False},
            {"completed_by": sample.reviewer},
        )
        for change in fixed:
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                AnnualReview.objects.filter(pk=review.pk).update(**change)
        with pytest.raises(services.RefusedError, match="Never Altered"):
            services.note_annual_review(review, results_note="[Altered]")
        # A review cannot be made already completed.
        with pytest.raises(IntegrityError, match="opened before it is completed"):
            with transaction.atomic():
                AnnualReview.objects.create(
                    organisation=sample.ours,
                    programme=programme(sample, fleet["G-ABCD"]),
                    opened_on=TODAY,
                    completed_on=TODAY,
                    completed_by=sample.lucy,
                )
    with working_for(sample.ours.id, sample.administrator.id):
        User.objects.filter(pk=sample.lucy.pk).update(full_name="[Renamed]")
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-FMNO'].id}/programme/")
    assert "Annual Review Completed 18 November 2026 by Lucy Grant" in body


def test_one_annual_review_is_in_progress_at_a_time(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-286. A second is refused, by the service and by the database, so Start the
    Annual Review sent twice opens one."""
    aircraft = fleet["G-ABCD"]
    client = signed_in(sample.reviewer)
    start = f"/aircraft/{aircraft.id}/programme/annual-review/start/"
    assert post(client, start).status_code == 302
    twice = post(client, start)
    assert twice.status_code == 409 and "Already in Progress" in twice.content.decode()
    abcd = programme(sample, aircraft)
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(IntegrityError, match="one_in_progress"), transaction.atomic():
            AnnualReview.objects.create(organisation=sample.ours, programme=abcd, opened_on=TODAY)
        assert AnnualReview.objects.filter(programme=abcd).count() == 1
        assert AnnualReview.objects.get(programme=abcd).progress == "0 of 6 Complete"


# The sources of directives

SOURCES = [
    ["Civil Aviation Authority", "United Kingdom Directives, All Aircraft", "16 November 2026",
     "30 November 2026", "Due Soon", ""],
    ["European Union Aviation Safety Agency", "Robin and Grob Airframes", "16 November 2026",
     "30 November 2026", "Due Soon", "State of Design"],
    ["Federal Aviation Administration",
     "Piper and Cessna Airframes, Lycoming Engines, Sensenich and McCauley Propellers",
     "16 November 2026", "30 November 2026", "Due Soon", "State of Design, Biweekly [Reference]"],
    ["CAP 747 Mandatory Requirements for Airworthiness", "Generic Requirements and Concessions",
     "16 November 2026", "Each Amendment", "", "Issue [Issue]"],
]  # fmt: skip


def test_the_sources_of_directives_of_the_sample_on_18_november_2026(
    sample: Sample, fleet: dict[str, Aircraft], day: Day
) -> None:
    """REQ-288, REQ-289. Golden: the Directives board's Sources. The three with a day
    are due in 12 days, inside the lead time of 30. On the day a check is Due, and
    the day after it is Overdue."""
    body = page(signed_in(sample.reader), "/directives/")
    assert rows(body) == SOURCES
    assert dot("Due Soon") in body

    def flags() -> list[tuple[str, int | None]]:
        with working_for(sample.ours.id, sample.reader.id):
            lines = directive_services.source_lines(
                Organisation.objects.get(pk=sample.ours.pk), day.today
            )
        return [(line.status, line.days) for line in lines]

    assert flags() == [("Due Soon", 12)] * 3 + [("", None)]
    day.today = date(2026, 10, 30)
    assert flags()[0] == ("", 31)
    day.today = date(2026, 10, 31)
    assert flags()[0] == ("Due Soon", 30)
    day.today = date(2026, 11, 30)
    assert flags()[0] == ("Due", 0)
    day.today = date(2026, 12, 1)
    assert flags()[0] == ("Overdue", -1)


def test_a_check_of_a_source_is_recorded_with_its_next_check(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-288. A source is recorded once; one never checked says so and is to
    assess. A check has its next check as a day or in words, is not before the
    last, and sent twice is recorded once. The history keeps every check."""
    client = signed_in(sample.planner)
    form = {"name": "[State of Design Authority]", "covers": "[Airframes]"}
    assert post(client, "/directives/sources/add/", **form).status_code == 302
    assert "Already Recorded" in post(client, "/directives/sources/add/", **form).content.decode()
    first = rows(page(client, "/directives/"))[0]
    assert first[:5] == ["[State of Design Authority]", "[Airframes]", "Not Checked",
                         "Not Checked", "To Assess"]  # fmt: skip
    with working_for(sample.ours.id, sample.reader.id):
        source = Source.objects.get(name="[State of Design Authority]")
        authority = Source.objects.get(name="Civil Aviation Authority")
    check = f"/directives/sources/{source.id}/check/"
    for values, reason in (
        ({"checked_on": "2026-11-19", "next_check_on": "2026-12-01"}, "Not After Today"),
        ({"checked_on": "2026-11-18"}, "or Say When It Is, and Not Both"),
        (
            {"checked_on": "2026-11-18", "next_check_on": "2026-12-01", "next_check_note": "X"},
            "or Say When It Is, and Not Both",
        ),
        ({"checked_on": "2026-11-18", "next_check_on": "2026-11-17"}, "Not Before This One"),
    ):
        assert reason in post(client, check, **values).content.decode(), reason
    good = {"checked_on": "2026-11-18", "next_check_on": "2026-12-02"}
    assert post(client, check, **good).status_code == 302
    assert "This Check Is Already Recorded" in post(client, check, **good).content.decode()
    earlier = {"checked_on": "2026-11-17", "next_check_on": "2026-12-02"}
    assert "Not Before the Last One" in post(client, check, **earlier).content.decode()
    # The Civil Aviation Authority, checked again today and next in words.
    words = {"checked_on": "2026-11-18", "next_check_note": "Each Amendment"}
    assert post(client, f"/directives/sources/{authority.id}/check/", **words).status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        authority.refresh_from_db()
        assert (authority.last_checked_on, authority.next_check_on, authority.next_check_note) == (
            TODAY,
            None,
            "Each Amendment",
        )
        checks = [
            json.loads(event.after_json or "{}")["last_checked_on"] for event in Event.of(authority)
        ]
        assert checks == [None, "2026-11-16", "2026-11-18"]
        for altered, constraint in (
            ({"next_check_on": date(2026, 11, 17)}, "check_has_its_next_check"),
            ({"next_check_on": date(2026, 12, 1)}, "check_has_its_next_check"),
            ({"next_check_note": ""}, "check_has_its_next_check"),
            ({"last_checked_on": None}, "check_has_its_next_check"),
            ({"name": ""}, "has_a_name_and_what_it_covers"),
            ({"covers": ""}, "has_a_name_and_what_it_covers"),
            ({"name": "CAP 747 Mandatory Requirements for Airworthiness"}, "recorded_once"),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Source.objects.filter(pk=authority.pk).update(**altered)


# The Dashboard, roles, other organisations and the export


def test_the_dashboard_shows_the_review_in_progress_and_the_sources_to_check(
    sample: Sample, fleet: dict[str, Aircraft], day: Day
) -> None:
    """REQ-289, REQ-286. Golden: G-FMNO's annual review, 4 of 6 complete, and the
    three sources due on 30 November 2026, in 12 days. CAP 747 has no day and is
    not shown. A source never checked comes first."""

    def shown() -> list[list[str]]:
        with working_for(sample.ours.id, sample.reader.id):
            panel = dashboard_services.continuing_airworthiness(
                Organisation.objects.get(pk=sample.ours.pk), day.today
            )
        return [
            [row.subject, row.item, row.due, row.remaining, row.status, row.detail]
            for row in panel.rows
        ]

    found = shown()
    assert [
        "G-FMNO",
        "Maintenance Programme Annual Review in Progress, 4 of 6 Complete",
        "Not Set",
        "",
        "To Assess",
        "Opened 9 November 2026, AMC1 ML.A.302(c)(9)",
    ] in found
    sources = [row for row in found if row[1].startswith("Source of Directives")]
    assert sources == [
        ["Civil Aviation Authority", "Source of Directives to Check", "30 November 2026",
         "12 Days", "Due Soon",
         "United Kingdom Directives, All Aircraft, Last Checked 16 November 2026"],
        ["European Union Aviation Safety Agency", "Source of Directives to Check",
         "30 November 2026", "12 Days", "Due Soon",
         "Robin and Grob Airframes, Last Checked 16 November 2026"],
        ["Federal Aviation Administration", "Source of Directives to Check", "30 November 2026",
         "12 Days", "Due Soon",
         "Piper and Cessna Airframes, Lycoming Engines, Sensenich and McCauley Propellers, "
         "Last Checked 16 November 2026"],
    ]  # fmt: skip
    with working_for(sample.ours.id, sample.planner.id):
        directive_services.add_source(sample.ours, name="[New Source]", covers="[Engines]")
    unchecked = next(row for row in shown() if row[0] == "[New Source]")
    assert unchecked[1:5] == ["Source of Directives Not Checked", "Not Set", "", "To Assess"]
    day.today = date(2026, 12, 2)
    late = next(row for row in shown() if row[0] == "Civil Aviation Authority")
    assert late[2:5] == ["30 November 2026", "2 Days Overdue", "Overdue"]


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_who_may_record_departures_reviews_and_sources(
    sample: Sample, fleet: dict[str, Aircraft], role: str
) -> None:
    """REQ-006. A departure changes the programme: the Continuing Airworthiness
    Manager. The annual review: the manager and Airworthiness Review Staff. A source
    and its checks: the manager and Planning and Records. Every role reads."""
    client = signed_in(getattr(sample, role))
    abcd, dghi = fleet["G-ABCD"], fleet["G-DGHI"]
    with working_for(sample.ours.id, sample.reader.id):
        departure = Departure.objects.filter(programme__aircraft=dghi).first()
        source = Source.objects.get(name="Civil Aviation Authority")
    assert departure is not None
    changes, reviews, records = (
        role == "lucy",
        role in ("lucy", "reviewer"),
        role
        in (
            "lucy",
            "planner",
        ),
    )
    body = page(client, f"/aircraft/{dghi.id}/programme/").split("<main", 1)[1]
    assert ("Record a Departure" in body) == changes
    assert ("Withdraw Departure" in body) == changes
    assert ("Start the Annual Review" in body) == reviews
    assert ("Record a Source" in page(client, "/directives/")) == records

    def answer(path: str, **values: str) -> int:
        return post(client, path, **values).status_code

    assert answer(f"/aircraft/{abcd.id}/programme/departures/add/", **DEPARTURE) == (
        302 if changes else 403
    )
    assert answer(f"/programmes/departures/{departure.id}/withdraw/", on="2026-11-18") == (
        302 if changes else 403
    )
    assert answer(f"/programmes/departures/{departure.id}/owner-copy/", on="2026-11-18") == (
        409 if changes else 403
    )
    assert answer(f"/aircraft/{abcd.id}/programme/annual-review/start/") == (
        302 if reviews else 403
    )
    assert answer(f"/aircraft/{abcd.id}/programme/annual-review/", results_note="X") == (
        302 if reviews else 403
    )
    assert answer(
        f"/aircraft/{abcd.id}/programme/annual-review/complete/", completed_on="2026-11-18"
    ) == (409 if reviews else 403)
    assert answer("/directives/sources/add/", name="[New]", covers="[All]") == (
        302 if records else 403
    )
    assert answer(
        f"/directives/sources/{source.id}/check/",
        checked_on="2026-11-18",
        next_check_on="2026-12-02",
    ) == (302 if records else 403)
    if role in ("administrator", "reader"):
        with as_owner():
            refused = AccessEntry.objects.filter(kind="Action Refused")
            assert sorted(refused.values_list("detail", flat=True)) == sorted(
                ["Change Maintenance Programme"] * 3
                + ["Record Maintenance Programme Review"] * 3
                + ["Record Airworthiness Directive"] * 2
            )


def test_another_organisations_departures_reviews_and_sources_are_not_found(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-003, REQ-002."""
    stranger = signed_in(sample.stranger)
    dghi, fmno = fleet["G-DGHI"], fleet["G-FMNO"]
    with working_for(sample.ours.id, sample.reader.id):
        departure = Departure.objects.filter(programme__aircraft=dghi).first()
        source = Source.objects.get(name="Civil Aviation Authority")
        review = AnnualReview.objects.get()
    assert departure is not None
    for path, values in (
        (f"/aircraft/{dghi.id}/programme/departures/add/", DEPARTURE),
        (f"/programmes/departures/{departure.id}/withdraw/", {"on": "2026-11-18"}),
        (f"/programmes/departures/{departure.id}/owner-copy/", {"on": "2026-11-18"}),
        (f"/aircraft/{fmno.id}/programme/annual-review/start/", {}),
        (f"/aircraft/{fmno.id}/programme/annual-review/", {"results_note": "X"}),
        (f"/aircraft/{fmno.id}/programme/annual-review/complete/", {"completed_on": "2026-11-18"}),
        (f"/directives/sources/{source.id}/check/", {"checked_on": "2026-11-18",
                                                     "next_check_note": "X"}),
    ):  # fmt: skip
        assert post(stranger, path, **values).status_code == 404, path
    assert get(stranger, f"/directives/sources/{source.id}/check/").status_code == 404
    for path in ("/directives/", "/programmes/", "/dashboard/"):
        body = page(stranger, path)
        assert "Federal Aviation Administration" not in body and "G-DGHI" not in body
    with working_for(sample.other.id, sample.stranger.id):
        makes = (
            lambda: Departure.objects.create(
                organisation=sample.other, programme_id=departure.programme_id, task="X",
                manufacturer="X", programme_says="X", compensating_measures="X",
                justification="X", recorded_on=TODAY),
            lambda: AnnualReview.objects.create(
                organisation=sample.other, programme_id=review.programme_id, opened_on=TODAY),
        )  # fmt: skip
        for make in makes:
            with (
                pytest.raises(Exception, match="refers only to records of its own organisation"),
                transaction.atomic(),
            ):
                make()
        # A source of the same name is another organisation's own.
        directive_services.add_source(
            sample.other, name="Civil Aviation Authority", covers="[Theirs]"
        )
        assert Source.objects.count() == 1


def test_the_export_holds_the_departures_the_review_and_the_sources(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-134. G-DGHI's export holds its two departures and every source; G-FMNO's
    holds its annual review and no departure."""
    with working_for(sample.ours.id, sample.lucy.id):
        dghi = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-DGHI"])
        fmno = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-FMNO"])

    def read(export: object, name: str) -> list[dict[str, object]]:
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:  # type: ignore[attr-defined]
            found: list[dict[str, object]] = json.loads(archive.read(f"records/{name}.json"))
            return found

    assert sorted(str(one["task"]) for one in read(dghi, "programme_departure")) == [
        "Engine Overhaul, Lycoming O-360",
        "Vacuum Pump Replacement",
    ]
    assert read(dghi, "programme_annualreview") == []
    assert len(read(dghi, "directives_source")) == 4
    assert read(fmno, "programme_departure") == []
    (review,) = read(fmno, "programme_annualreview")
    assert (review["opened_on"], review["results_note"], review["pilot_owners_done"]) == (
        "2026-11-09",
        "2 Defects, No Repeats",
        False,
    )
