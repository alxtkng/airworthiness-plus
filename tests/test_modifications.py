"""Modifications and Repairs, and Weight and Balance (REQ-249 to REQ-259).

The Modifications and Weighing boards, with the sample of
design-system/SampleData.md. Today in the sample is 18 November 2026.
ML.A.304 and ML.A.305(d) were read in the UK text on 27 November 2026.

By hand, for 18 November 2026 and a lead time of 30 days:

- Service bulletins: G-BXYZ's is awaiting the owner, sent 10 November,
  reminder 24 November, 6 days: Due Soon. G-ABCD's two were accepted on
  2 March 2026 and G-EJKL's declined on 6 June 2026.
- G-BXYZ: weighed 14 June 2019, Issue 6 of that day. The navigator of
  12 October 2026 is 1.2 Kilograms heavier and not yet in an issue of the
  schedule: Weight Schedule Update.
- G-FMNO: weighed 5 April 2018; the landing light of 14 April 2026 is 0.3
  lighter and in Issue 5 of 20 April 2026: Current.
- G-DGHI: weighed 9 March 2017; the wingtip repair of 18 July 2025 has no
  mass effect: 0.0, Current. The Weighing board's 3 Changes and 4.1
  Kilograms are not taken: the Modifications board has one change.
- G-ABCD: weighed 20 May 2022, after the transponder of 10 May: none since.
- No reweigh threshold is set, so nothing is marked for a reweigh.
"""

import io
import json
import re
import zipfile
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.dashboard import services as dashboard_services
from airworthiness_plus.exports.build import build as build_export
from airworthiness_plus.history.models import Event, RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.modifications import services
from airworthiness_plus.modifications.models import (
    Bulletin,
    Change,
    Classification,
    Data,
    OwnerDecision,
    Route,
    Weighing,
    WeightSchedule,
)
from airworthiness_plus.organisations import configuration
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.sample import build, phase1
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, make_sample, signed_in

pytestmark = pytest.mark.django_db
D = Decimal
MINUS = "\u2212"


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
    return build.add_fleet(sample)


@pytest.fixture
def recorded(sample: Sample, fleet: dict[str, Aircraft]) -> dict[str, Aircraft]:
    phase1.add_modifications(sample.ours, sample.planner, fleet)
    return fleet


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def rows(body: str, table: int = 0) -> list[list[str]]:
    """Return the cells of each row of one table of the page."""
    found = body.split("<main", 1)[1].split("<table>")[1 + table].split("</table>", 1)[0]
    out = []
    for row in re.findall(r"<tr>\s*(<td.*?)</tr>", found, flags=re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
        out.append([re.sub(r"<[^>]+>", "", cell).strip() for cell in cells])
    return out


def threshold(sample: Sample, value: str | None) -> None:
    with working_for(sample.ours.id, sample.administrator.id):
        configuration.set_reweigh_threshold(
            Organisation.objects.get(pk=sample.ours.pk),
            threshold=D(value) if value is not None else None,
        )


def change(sample: Sample, aircraft: Aircraft, **values: Any) -> Change:
    given: dict[str, Any] = {
        "title": "[Change]",
        "route": Route.STANDARD_CHANGE,
        "mass_effect": D("2.0"),
        "embodied_on": date(2026, 11, 1),
    }
    given.update(values)
    with working_for(sample.ours.id, sample.planner.id):
        return services.record_change(aircraft, **given)


def weight(sample: Sample, aircraft: Aircraft) -> services.WeightLine:
    with working_for(sample.ours.id, sample.reader.id):
        return services.weight_line(Aircraft.objects.get(pk=aircraft.pk))


# The sample

STANDARD = "Contained in the Requirements of Point 21.A.90B or 21.A.431B"
BULLETINS = [
    ["G-BXYZ", "Alternator Mounting Bracket Inspection", "Awaiting Owner",
     "Reminder 24 November 2026", "Due Soon", "[Service Bulletin Reference 3]", "Recommended",
     "Sent 10 November 2026", "10 November 2026"],
    ["G-ABCD", "Engine Valve Guide Inspection", "Every 100-Hour Check", "2 March 2026", "",
     "[Service Bulletin Reference 2]", "Recommended", "Accepted", "16 February 2026"],
    ["G-ABCD", "Seat Rail and Stop Inspection", "Every 50-Hour Check", "2 March 2026", "",
     "[Service Bulletin Reference 1]", "Recommended", "Accepted", "16 February 2026"],
    ["G-EJKL", "Seat Belt Replacement", "Declined", "6 June 2026", "",
     "[Service Bulletin Reference 4]", "Optional", "Belts On Condition, Annual Check",
     "20 May 2026"],
]  # fmt: skip
CHANGES = [
    ["G-BXYZ", "Panel-Mounted Navigator", "Standard Change, [Standard Change Reference 1]",
     "+1.2 Kilograms", "Weight Schedule Update", "To Assess", "12 October 2026", STANDARD],
    ["G-CDEF", "Propeller Overhaul", "Maintenance, Same Part Number", "0.0 Kilograms",
     "In Progress", "", "In Progress", ""],
    ["G-FMNO", "Light-Emitting Diode Landing Light", "Minor Change, [Minor Change Reference]",
     f"{MINUS}0.3 Kilograms", "Complete", "", "14 April 2026", "Approved by a Design Organisation"],
    ["G-DGHI", "Left Wingtip Repair, Hangar Damage", "Manufacturer&#x27;s Structural Repair Data",
     "0.0 Kilograms", "Complete", "", "18 July 2025", "Approved by a Design Organisation"],
    ["G-ABCD", "Mode S Transponder with Position Output",
     "Standard Change, [Standard Change Reference 2]", "+0.4 Kilograms", "Complete", "",
     "10 May 2022", STANDARD],
]  # fmt: skip
WEIGHT = [
    ["G-BXYZ", "14 June 2019", "Issue 6", "Panel-Mounted Navigator", "+1.2 Kilograms",
     "Weight Schedule Update", "To Assess"],
    ["G-ABCD", "20 May 2022", "Issue 4", "None", "0.0 Kilograms", "Current", ""],
    ["G-CDEF", "3 September 2021", "Issue 3", "None", "0.0 Kilograms", "Current", ""],
    ["G-DGHI", "9 March 2017", "Issue 9", "Left Wingtip Repair, Hangar Damage", "0.0 Kilograms",
     "Current", ""],
    ["G-EJKL", "22 July 2020", "Issue 2", "None", "0.0 Kilograms", "Current", ""],
    ["G-FMNO", "5 April 2018", "Issue 5", "Light-Emitting Diode Landing Light",
     f"{MINUS}0.3 Kilograms", "Current", ""],
]  # fmt: skip


def test_the_modifications_page_of_the_sample_on_18_november_2026(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-253. Golden: the Modifications board from the sample. What is outstanding
    comes first, and a role that may not record is shown no link to."""
    body = page(signed_in(sample.reader), "/modifications/")
    assert rows(body, 0) == BULLETINS
    assert rows(body, 1) == CHANGES
    assert dot("Due Soon") in body and dot("To Assess") in body
    assert "<a href" not in body.split("<h2>Service Bulletins</h2>")[0].split("<main", 1)[1]
    assert '<a href="/weight-and-balance/">Weight Schedule Update</a>' in body


def test_the_weight_and_balance_page_of_the_sample_on_18_november_2026(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-255, REQ-256. Golden: the Weighing board, with G-DGHI as the
    Modifications board has it. No threshold is set, the page says so, and nothing
    is marked for a reweigh. How a net change was worked out is on the page."""
    body = page(signed_in(sample.reader), "/weight-and-balance/")
    assert [row[:7] for row in rows(body)] == WEIGHT
    assert "No Reweigh Threshold Set. Nothing Is Marked for a Reweigh Until One Is Set" in body
    assert "Reweigh</td>" not in body
    bxyz = rows(body)[0]
    assert bxyz[7:10] == ["[Weighing Report G-BXYZ]", "14 June 2019", "No Reweigh Threshold Set"]
    for part in ("Last Weighed", "Panel-Mounted Navigator, 12 October 2026", "+1.2 Kilograms",
                 "ML.A.305(d)"):  # fmt: skip
        assert part in bxyz[10]


def test_a_reweigh_is_marked_only_over_a_threshold_the_organisation_has_set(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-256, REQ-257. G-BXYZ is 1.2 Kilograms heavier. With no threshold: a
    schedule to update, no reweigh. At 1.2 it is not over; at 1.1 it is. A loss
    counts by its size: G-FMNO, 0.3 lighter, is over 0.2."""
    bxyz, fmno = recorded["G-BXYZ"], recorded["G-FMNO"]
    assert weight(sample, bxyz).state == "Weight Schedule Update"
    threshold(sample, "1.2")
    assert weight(sample, bxyz).state == "Weight Schedule Update"
    threshold(sample, "1.1")
    line = weight(sample, bxyz)
    assert (line.state, line.status, line.threshold_text) == ("Reweigh", "To Assess",
                                                              "1.1 Kilograms")  # fmt: skip
    assert weight(sample, fmno).state == "Current"
    threshold(sample, "0.2")
    assert weight(sample, fmno).state == "Reweigh"
    body = page(signed_in(sample.reader), "/weight-and-balance/")
    assert [row[0] for row in rows(body) if row[5] == "Reweigh"] == ["G-BXYZ", "G-FMNO"]
    assert "Reweigh Threshold 0.2 Kilograms, the Organisation's Own" in body
    threshold(sample, None)
    assert weight(sample, bxyz).state == "Weight Schedule Update"
    assert weight(sample, fmno).state == "Current"


def test_an_issue_of_the_schedule_takes_in_a_change_and_a_weighing_starts_the_count_again(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-254 to REQ-256. Issue 7 of G-BXYZ's schedule, dated 13 October 2026, takes
    in the navigator of the day before: its records are Complete and the aircraft
    is Current, with the 1.2 Kilograms still counted since the weighing. A weighing
    on 18 November starts the count again: none since."""
    bxyz = recorded["G-BXYZ"]
    client = signed_in(sample.planner)
    form = {"aircraft": str(bxyz.id), "issue": "7", "issued_on": "2026-10-13"}
    assert post(client, "/weight-and-balance/schedules/record/", **form).status_code == 302
    twice = post(client, "/weight-and-balance/schedules/record/", **form)
    assert "This Issue Is Already Recorded" in twice.content.decode()
    line = weight(sample, bxyz)
    assert (line.state, line.net_text, line.schedule.issue) == (  # type: ignore[union-attr]
        "Current",
        "+1.2 Kilograms",
        7,
    )
    assert rows(page(client, "/modifications/"), 1)[1][:5] == [
        "G-BXYZ",
        "Panel-Mounted Navigator",
        "Standard Change, [Standard Change Reference 1]",
        "+1.2 Kilograms",
        "Complete",
    ]
    weighed = {"aircraft": str(bxyz.id), "weighed_on": "2026-11-18", "reference": "[Report 2]"}
    assert post(client, "/weight-and-balance/weighings/record/", **weighed).status_code == 302
    again = post(client, "/weight-and-balance/weighings/record/", **weighed)
    assert "A Weighing on This Day Is Already Recorded" in again.content.decode()
    line = weight(sample, bxyz)
    assert (line.changes_text, line.net_text, line.state) == ("None", "0.0 Kilograms", "Current")
    with working_for(sample.ours.id, sample.reader.id):
        assert Weighing.objects.filter(aircraft=bxyz).count() == 2
        assert WeightSchedule.objects.filter(aircraft=bxyz).count() == 2


def test_several_changes_are_summed_from_the_day_after_the_weighing(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-255. G-ABCD was weighed on 20 May 2022. A change on that day is not
    counted. Three after it, 2.0 and 1.5 heavier and 0.7 lighter, are 2.8 heavier;
    one in progress is not counted until it is embodied."""
    abcd = recorded["G-ABCD"]
    change(sample, abcd, title="[On the Day]", embodied_on=date(2022, 5, 20))
    assert weight(sample, abcd).net == D("0.0")
    change(sample, abcd, title="[First]", embodied_on=date(2022, 5, 21))
    change(sample, abcd, title="[Second]", mass_effect=D("1.5"), embodied_on=date(2024, 1, 2))
    change(sample, abcd, title="[Third]", mass_effect=D("-0.7"), embodied_on=TODAY)
    waiting = change(sample, abcd, title="[Fourth]", mass_effect=D("10.0"), embodied_on=None)
    line = weight(sample, abcd)
    assert (line.net, line.net_text, line.changes_text) == (D("2.8"), "+2.8 Kilograms", "3 Changes")
    assert line.state == "Weight Schedule Update"
    with working_for(sample.ours.id, sample.planner.id):
        services.embody_change(waiting, embodied_on=TODAY)
    assert weight(sample, abcd).net == D("12.8")


def test_an_aircraft_with_no_weighing_recorded_says_so(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-256. Nothing is counted without a weighing to count from, and the page
    says Not Recorded; it does not show the aircraft as Current."""
    change(sample, fleet["G-ABCD"])
    line = weight(sample, fleet["G-ABCD"])
    assert (line.state, line.net_text, line.changes_text) == ("No Weighing Recorded", "", "")
    body = page(signed_in(sample.reader), "/weight-and-balance/")
    assert rows(body)[0][:7] == ["G-ABCD", "Not Recorded", "Not Recorded", "", "",
                                 "No Weighing Recorded", ""]  # fmt: skip
    # G-HKLM is still being transferred in, and is not of the Fleet.
    assert [row[0] for row in rows(body)] == sorted(set(fleet) - {"G-HKLM"})


# Service bulletins


def test_the_owner_decision_is_recorded_once_and_never_altered(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-250. G-BXYZ's syndicate accepts on 20 November. The decision is then
    fixed: a second is refused, and the database refuses any change, to the
    bulletin as well as to the decision."""
    with working_for(sample.ours.id, sample.reader.id):
        awaited = Bulletin.objects.get(decision=OwnerDecision.AWAITING)
    client = signed_in(sample.planner)
    address = f"/modifications/service-bulletins/{awaited.id}/decide/"
    assert "G-BXYZ, Alternator Mounting Bracket Inspection" in page(client, address)
    for values, reason in (
        ({"decided_on": "2026-11-19"}, "Not Recorded After Today"),
        ({"decided_on": "2026-11-09"}, "Not Before the Bulletin Was Sent"),
        ({"detail": " "}, "This field is required"),
    ):
        form = {"decision": "Accepted", "detail": "Every 100-Hour Check",
                "decided_on": "2026-11-18", **values}  # fmt: skip
        assert reason in post(client, address, **form).content.decode()
    form = {"decision": "Accepted", "detail": "Every 100-Hour Check", "decided_on": "2026-11-18"}
    assert post(client, address, **form).status_code == 302
    assert "Already Recorded" in post(client, address, **form).content.decode()
    assert rows(page(client, "/modifications/"))[2][:5] == [
        "G-BXYZ",
        "Alternator Mounting Bracket Inspection",
        "Every 100-Hour Check",
        "18 November 2026",
        "",
    ]
    with working_for(sample.ours.id, sample.planner.id):
        for altered in (
            {"detail": "[Altered]"},
            {"decision": OwnerDecision.DECLINED},
            {"decided_on": date(2026, 11, 17)},
            {"title": "[Altered]"},
        ):
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                Bulletin.objects.filter(pk=awaited.pk).update(**altered)
        with pytest.raises(RecordsAreNeverDeletedError):
            awaited.delete()
        assert Event.of(awaited).count() == 2


def test_what_was_recorded_of_a_bulletin_awaiting_its_decision_is_not_altered(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-250. While the owner has still to decide, nothing of the bulletin changes
    but the decision; and a decision is whole or absent."""
    with working_for(sample.ours.id, sample.planner.id):
        awaited = Bulletin.objects.get(decision=OwnerDecision.AWAITING)
        for altered in (
            {"title": "[Altered]"},
            {"reference": "[Altered]"},
            {"classification": Classification.OPTIONAL},
            {"sent_on": date(2026, 11, 1)},
            {"reminder_on": date(2026, 12, 24)},
            {"aircraft": recorded["G-ABCD"]},
        ):
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                Bulletin.objects.filter(pk=awaited.pk).update(**altered)
        for partial in (
            {"decision": OwnerDecision.ACCEPTED},
            {"decision": OwnerDecision.ACCEPTED, "detail": "X"},
            {"decision": OwnerDecision.ACCEPTED, "detail": "X", "decided_on": date(2026, 11, 9)},
            {"detail": "X"},
            {"decision": "[Unknown]", "detail": "X", "decided_on": TODAY},
        ):
            with pytest.raises(IntegrityError, match="whole_or_awaited"), transaction.atomic():
                Bulletin.objects.filter(pk=awaited.pk).update(**partial)


REFUSED_BULLETINS: tuple[tuple[dict[str, Any], str], ...] = (
    ({"title": " "}, "Has a Title and a Reference"),
    ({"reference": " "}, "Has a Title and a Reference"),
    ({"classification": "[Unknown]"}, "Recommended or Optional"),
    ({"sent_on": date(2026, 11, 19)}, "Not Sent After Today"),
    ({"reminder_on": date(2026, 10, 31)}, "Reminder Is Not Before"),
    ({"decision": OwnerDecision.ACCEPTED, "detail": "X"}, "Has the Day It Was Recorded"),
    ({"decision": OwnerDecision.ACCEPTED, "decided_on": TODAY}, "Says What Was Decided"),
    ({"detail": "X", "decided_on": TODAY}, "Accepted or Declined"),
    (
        {"decision": OwnerDecision.DECLINED, "detail": "X", "decided_on": date(2026, 10, 31)},
        "Not Before the Bulletin Was Sent",
    ),
)


@pytest.mark.parametrize(("altered", "reason"), REFUSED_BULLETINS)
def test_what_cannot_be_true_of_a_bulletin_is_refused(
    sample: Sample, fleet: dict[str, Aircraft], altered: dict[str, Any], reason: str
) -> None:
    """REQ-249, REQ-250. Nothing is left behind by a bulletin that is refused."""
    given: dict[str, Any] = {
        "title": "[Bulletin]",
        "reference": "[Reference]",
        "classification": Classification.RECOMMENDED,
        "sent_on": date(2026, 11, 1),
    }
    with (
        working_for(sample.ours.id, sample.planner.id),
        pytest.raises(services.RefusedError, match=reason),
    ):
        services.record_bulletin(fleet["G-ABCD"], **{**given, **altered})
    with working_for(sample.ours.id, sample.reader.id):
        assert Bulletin.objects.count() == 0


# Changes and repairs


def test_the_data_of_a_change_fits_its_route(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-251. ML.A.304: a standard change or repair uses the requirements of point
    21.A.90B or 21.A.431B; any other modification or repair says whether its data
    is approved by the Civil Aviation Authority or by a design organisation.
    Maintenance with the same part number names none. The database holds the same."""
    abcd = fleet["G-ABCD"]
    assert change(sample, abcd, title="[1]").data == Data.STANDARD
    assert change(sample, abcd, title="[2]", route=Route.STANDARD_REPAIR).data == Data.STANDARD
    minor = change(sample, abcd, title="[3]", route=Route.MINOR_CHANGE, data_kind=Data.AUTHORITY)
    assert minor.data == "Approved by the Civil Aviation Authority"
    assert change(sample, abcd, title="[4]", route=Route.SAME_PART).data == ""
    for values, reason in (
        ({"route": Route.MINOR_CHANGE}, "Say Whether the Data Is Approved"),
        ({"route": Route.OTHER, "data_kind": Data.STANDARD}, "Say Whether the Data Is Approved"),
        ({"route": Route.STRUCTURAL_REPAIR_DATA}, "Say Whether the Data Is Approved"),
        ({"data_kind": Data.AUTHORITY}, "Uses the Requirements of Point 21.A.90B"),
        ({"route": Route.SAME_PART, "data_kind": Data.AUTHORITY}, "Names No Data"),
        ({"route": "[Unknown]"}, "Choose the Approval Route"),
        ({"title": " "}, "Has a Title"),
        ({"mass_effect": D("1000.0")}, "at Most 999.9 Kilograms"),
        ({"mass_effect": D("-1000.0")}, "at Most 999.9 Kilograms"),
        ({"embodied_on": date(2026, 11, 19)}, "Not Embodied After Today"),
    ):
        with pytest.raises(services.RefusedError, match=reason):
            change(sample, abcd, **{"title": "[Refused]", **values})
    good: dict[str, Any] = {
        "organisation": sample.ours,
        "aircraft": abcd,
        "title": "[Change]",
        "route": Route.MINOR_CHANGE,
        "data": Data.AUTHORITY,
        "mass_effect": D("0.0"),
    }
    with working_for(sample.ours.id, sample.planner.id):
        for altered, constraint in (
            ({"data": Data.STANDARD}, "change_data_fits_its_route"),
            ({"data": ""}, "change_data_fits_its_route"),
            ({"route": Route.STANDARD_CHANGE}, "change_data_fits_its_route"),
            ({"route": Route.SAME_PART}, "change_data_fits_its_route"),
            ({"route": "[Unknown]"}, "change_has_a_title_a_route|change_data_fits_its_route"),
            ({"title": ""}, "change_has_a_title_a_route"),
            ({"mass_effect": D("1000.0")}, "numeric field overflow|change_has_a_title_a_route"),
        ):
            with pytest.raises(Exception, match=constraint), transaction.atomic():
                Change.objects.create(**{**good, **altered})
        Change.objects.create(**{**good, "mass_effect": D("-999.9")})
        assert Change.objects.count() == 5


def test_a_change_in_progress_is_embodied_once_and_then_never_changes(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-252. G-CDEF's propeller overhaul is in progress. It is recorded as
    embodied once; nothing else of it was ever alterable, and nothing is after."""
    with working_for(sample.ours.id, sample.planner.id):
        overhaul = Change.objects.get(embodied_on__isnull=True)
        for altered in (
            {"title": "[Altered]"},
            {"mass_effect": D("5.0")},
            {"route": Route.STANDARD_CHANGE, "data": Data.STANDARD},
            {"reference": "[Altered]"},
            {"aircraft": recorded["G-ABCD"]},
        ):
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                Change.objects.filter(pk=overhaul.pk).update(**altered)
    client = signed_in(sample.planner)
    address = f"/modifications/{overhaul.id}/embodied/"
    assert "Not Embodied After Today" in (
        post(client, address, embodied_on="2026-11-19").content.decode()
    )
    assert post(client, address, embodied_on="2026-11-18").status_code == 302
    assert "Already Embodied" in post(client, address, embodied_on="2026-11-18").content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        for day_altered in (date(2026, 11, 17), None):
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                Change.objects.filter(pk=overhaul.pk).update(embodied_on=day_altered)
        with pytest.raises(RecordsAreNeverDeletedError):
            overhaul.delete()
        assert Change.objects.get(pk=overhaul.pk).embodied_on == TODAY


def test_a_form_sent_twice_is_recorded_once(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-259. A bulletin, and a change embodied on the same day or still in
    progress, are recorded once for an aircraft."""
    client = signed_in(sample.planner)
    abcd = str(fleet["G-ABCD"].id)
    bulletin = {"aircraft": abcd, "title": "[Bulletin]", "reference": "[Reference]",
                "classification": "Recommended", "sent_on": "2026-11-01"}  # fmt: skip
    address = "/modifications/service-bulletins/record/"
    assert post(client, address, **bulletin).status_code == 302
    assert "Already Recorded for the Aircraft" in post(client, address, **bulletin).content.decode()
    made = {"aircraft": abcd, "title": "[Change]", "route": "Standard Change", "mass_effect": "1.5"}
    for values in (made, {**made, "embodied_on": "2026-11-01"}):
        assert post(client, "/modifications/record/", **values).status_code == 302
        refused = post(client, "/modifications/record/", **values)
        assert "Already Recorded for the Aircraft" in refused.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert (Bulletin.objects.count(), Change.objects.count()) == (1, 2)
        assert Bulletin.objects.get().awaiting


# Weighings and the schedule


def test_a_weighing_and_an_issue_of_the_schedule_follow_the_last_and_are_never_changed(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-254. G-BXYZ was weighed on 14 June 2019 and has Issue 6 of that day."""
    bxyz = recorded["G-BXYZ"]
    with working_for(sample.ours.id, sample.planner.id):
        for values, reason in (
            ({"weighed_on": date(2026, 11, 19)}, "Not Weighed After Today"),
            ({"weighed_on": date(2019, 6, 13)}, "Not Before the Last One"),
            ({"weighed_on": date(2019, 6, 14)}, "Already Recorded"),
            ({"reference": " "}, "Names Its Report"),
        ):
            with pytest.raises(services.RefusedError, match=reason):
                given: dict[str, Any] = {"weighed_on": TODAY, "reference": "X", **values}
                services.record_weighing(bxyz, **given)
        for issue, issued_on, reason in (
            (6, TODAY, "Already Recorded"),
            (5, TODAY, "Follows the Last"),
            (7, date(2019, 6, 13), "Follows the Last"),
            (7, date(2026, 11, 19), "Not Issued After Today"),
            (0, TODAY, "From 1 to 9,999"),
            (10_000, TODAY, "From 1 to 9,999"),
        ):
            with pytest.raises(services.RefusedError, match=reason):
                services.record_schedule(bxyz, issue=issue, issued_on=issued_on)
        weighing = Weighing.objects.get(aircraft=bxyz)
        schedule = WeightSchedule.objects.get(aircraft=bxyz)
        for constraint, make in (
            ("weighing_one_for_an_aircraft_on_a_day", lambda: Weighing.objects.create(
                organisation=sample.ours, aircraft=bxyz, weighed_on=date(2019, 6, 14),
                reference="X")),
            ("weighing_has_a_report", lambda: Weighing.objects.create(
                organisation=sample.ours, aircraft=bxyz, weighed_on=TODAY, reference="")),
            ("weight_schedule_one_of_each_issue", lambda: WeightSchedule.objects.create(
                organisation=sample.ours, aircraft=bxyz, issue=6, issued_on=TODAY)),
            ("weight_schedule_issue_from_1_to_9999", lambda: WeightSchedule.objects.create(
                organisation=sample.ours, aircraft=bxyz, issue=0, issued_on=TODAY)),
            ("weight_schedule_issue_from_1_to_9999", lambda: WeightSchedule.objects.create(
                organisation=sample.ours, aircraft=bxyz, issue=10_000, issued_on=TODAY)),
        ):  # fmt: skip
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                make()
        # Neither is changed once recorded: the application has no right to.
        for held, table in ((weighing, Weighing), (schedule, WeightSchedule)):
            with pytest.raises(RecordsAreNeverDeletedError):
                held.save()
            with pytest.raises(Exception, match="permission denied"), transaction.atomic():
                table.objects.filter(pk=held.pk).update(organisation=sample.ours)


# The reweigh threshold


def test_the_reweigh_threshold_is_the_organisations_own_with_no_default(sample: Sample) -> None:
    """REQ-257. None until the Administrator sets one, from 0.1 to 999.9 Kilograms,
    held by the form, the service and the database. It can be taken off again."""
    assert sample.ours.reweigh_threshold_kilograms is None
    admin = signed_in(sample.administrator)
    assert "No Reweigh Threshold Set" in page(admin, "/settings/")
    for value in ("0", "0.05", "1000", "-1"):
        refused = post(admin, "/settings/reweigh-threshold/", threshold=value)
        assert refused.status_code == 200 and 'class="field-error"' in refused.content.decode()
    assert post(admin, "/settings/reweigh-threshold/", threshold="2.5").status_code == 302
    assert "Reweigh Threshold 2.5 Kilograms" in page(signed_in(sample.reader), "/settings/")
    with working_for(sample.ours.id, sample.administrator.id):
        ours = Organisation.objects.get(pk=sample.ours.pk)
        assert ours.reweigh_threshold_kilograms == D("2.5")
        for beyond in (D("0"), D("-0.1"), D("1000.0")):
            with pytest.raises(configuration.RefusedError, match=r"Above 0 and at Most 999\.9"):
                configuration.set_reweigh_threshold(ours, threshold=beyond)
        for beyond in (D("0"), D("-0.1")):
            with (
                pytest.raises(IntegrityError, match="reweigh_threshold_above_zero"),
                transaction.atomic(),
            ):
                Organisation.objects.filter(pk=ours.pk).update(reweigh_threshold_kilograms=beyond)
        configuration.set_reweigh_threshold(ours, threshold=D("999.9"))
    assert post(admin, "/settings/reweigh-threshold/", threshold="").status_code == 302
    assert "No Reweigh Threshold Set" in page(admin, "/settings/")
    # Only a role that may change the organisation record sets it.
    for user in (sample.lucy, sample.planner, sample.reader):
        client = signed_in(user)
        assert post(client, "/settings/reweigh-threshold/", threshold="1").status_code == 403
        assert "Save Reweigh Threshold" not in page(client, "/settings/")


# The Dashboard, roles, other organisations and the export


def test_the_dashboard_shows_what_waits_in_modifications_and_weight(
    sample: Sample, recorded: dict[str, Aircraft], day: Day
) -> None:
    """REQ-258. Golden: G-BXYZ's bulletin awaiting the syndicate, reminder
    24 November, 6 days; and its weight schedule to update. With a threshold of
    1.0 Kilograms the second row says Reweigh."""

    def shown() -> list[list[str]]:
        with working_for(sample.ours.id, sample.reader.id):
            panel = dashboard_services.continuing_airworthiness(
                Organisation.objects.get(pk=sample.ours.pk), day.today
            )
        return [
            [row.subject, row.item, row.due, row.remaining, row.status, row.detail]
            for row in panel.rows
            if row.page == "Aircraft Configuration"
        ]

    bulletin = [
        "G-BXYZ",
        "Service Bulletin Awaiting Owner Decision, Alternator Mounting Bracket Inspection",
        "24 November 2026",
        "6 Days",
        "Due Soon",
        "[Service Bulletin Reference 3], Recommended, Sent 10 November 2026",
    ]
    schedule = [
        "G-BXYZ",
        "Weight Schedule to Update",
        "Not Set",
        "",
        "To Assess",
        "Panel-Mounted Navigator, +1.2 Kilograms; Threshold No Reweigh Threshold Set",
    ]
    assert shown() == [bulletin, schedule]
    threshold(sample, "1.0")
    assert shown()[1][1::4] == [
        "Reweigh, Net Mass Change Over the Threshold",
        "Panel-Mounted Navigator, +1.2 Kilograms; Threshold 1.0 Kilograms",
    ]
    day.today = date(2026, 11, 25)
    assert shown()[0][2:5] == ["24 November 2026", "1 Day Overdue", "Overdue"]
    body = page(signed_in(sample.reader), "/dashboard/")
    assert '<a href="/modifications/">Aircraft Configuration</a>' in body
    assert '<a href="/weight-and-balance/">Aircraft Configuration</a>' in body


CHANGE = {"title": "[Change]", "route": "Standard Change", "mass_effect": "1.5"}
BULLETIN = {"title": "[Bulletin]", "reference": "[Reference]", "classification": "Optional",
            "sent_on": "2026-11-01"}  # fmt: skip


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_who_may_record_modifications_and_weighings(
    sample: Sample, recorded: dict[str, Aircraft], role: str
) -> None:
    """REQ-006, REQ-259. The Continuing Airworthiness Manager and Planning and Records
    record, under Record Aircraft Configuration; every role reads."""
    client = signed_in(getattr(sample, role))
    may = role in ("lucy", "planner")
    ejkl = str(recorded["G-EJKL"].id)
    with working_for(sample.ours.id, sample.reader.id):
        awaited = Bulletin.objects.get(decision=OwnerDecision.AWAITING)
        waiting = Change.objects.get(embodied_on__isnull=True)
    for path in ("/modifications/", "/weight-and-balance/"):
        body = page(client, path).split("<main", 1)[1]
        assert ("Record a " in body) == may, path
    posts = [
        ("/modifications/record/", {"aircraft": ejkl, **CHANGE}),
        ("/modifications/service-bulletins/record/", {"aircraft": ejkl, **BULLETIN}),
        (f"/modifications/{waiting.id}/embodied/", {"embodied_on": "2026-11-18"}),
        (
            f"/modifications/service-bulletins/{awaited.id}/decide/",
            {"decision": "Declined", "detail": "X", "decided_on": "2026-11-18"},
        ),
        (
            "/weight-and-balance/weighings/record/",
            {"aircraft": ejkl, "weighed_on": "2026-11-18", "reference": "X"},
        ),
        (
            "/weight-and-balance/schedules/record/",
            {"aircraft": ejkl, "issue": "3", "issued_on": "2026-11-18"},
        ),
    ]
    for path, values in posts:
        assert get(client, path).status_code == (200 if may else 403), path
        assert post(client, path, **values).status_code == (302 if may else 403), path
    with working_for(sample.ours.id, sample.reader.id):
        assert Change.objects.count() == (6 if may else 5)
        assert Bulletin.objects.filter(decision=OwnerDecision.AWAITING).count() == 1
        assert Weighing.objects.count() == (7 if may else 6)
    if not may:
        with as_owner():
            refused = AccessEntry.objects.filter(kind="Action Refused")
            assert list(refused.values_list("detail", flat=True)) == (
                ["Record Aircraft Configuration"] * 12
            )


def test_another_organisations_modifications_are_not_found_or_shown(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-003, REQ-002."""
    stranger = signed_in(sample.stranger)
    with working_for(sample.ours.id, sample.reader.id):
        awaited = Bulletin.objects.get(decision=OwnerDecision.AWAITING)
        waiting = Change.objects.get(embodied_on__isnull=True)
    for path in (
        f"/modifications/{waiting.id}/embodied/",
        f"/modifications/service-bulletins/{awaited.id}/decide/",
    ):
        assert get(stranger, path).status_code == 404
        assert post(stranger, path, embodied_on="2026-11-18").status_code == 404
    for path in ("/modifications/", "/weight-and-balance/", "/dashboard/"):
        body = page(stranger, path)
        assert "G-BXYZ" not in body and "Navigator" not in body and "Alternator" not in body
    ours = str(recorded["G-ABCD"].id)
    for path, values in (
        ("/modifications/record/", CHANGE),
        ("/modifications/service-bulletins/record/", BULLETIN),
        ("/weight-and-balance/weighings/record/", {"weighed_on": "2026-11-18", "reference": "X"}),
        ("/weight-and-balance/schedules/record/", {"issue": "9", "issued_on": "2026-11-18"}),
    ):
        refused = post(stranger, path, aircraft=ours, **values)
        assert "Select a valid choice" in refused.content.decode(), path
    with working_for(sample.other.id, sample.stranger.id):
        makes = (
            lambda: Change.objects.create(
                organisation=sample.other, aircraft=recorded["G-ABCD"], title="X",
                route=Route.SAME_PART, mass_effect=D("0")),
            lambda: Bulletin.objects.create(
                organisation=sample.other, aircraft=recorded["G-ABCD"], title="X", reference="X",
                classification=Classification.OPTIONAL, sent_on=TODAY),
            lambda: Weighing.objects.create(
                organisation=sample.other, aircraft=recorded["G-ABCD"], weighed_on=TODAY,
                reference="X"),
            lambda: WeightSchedule.objects.create(
                organisation=sample.other, aircraft=recorded["G-ABCD"], issue=1, issued_on=TODAY),
        )  # fmt: skip
        for make in makes:
            with (
                pytest.raises(Exception, match="refers only to records of its own organisation"),
                transaction.atomic(),
            ):
                make()


def test_the_export_of_an_aircraft_holds_its_changes_bulletins_and_weighings(
    sample: Sample, recorded: dict[str, Aircraft]
) -> None:
    """REQ-134. G-BXYZ: its navigator, its bulletin, its weighing and Issue 6.
    G-HKLM, still being transferred in, has none."""
    with working_for(sample.ours.id, sample.lucy.id):
        bxyz = build_export(sample.ours, by=sample.lucy, aircraft=recorded["G-BXYZ"])
        hklm = build_export(sample.ours, by=sample.lucy, aircraft=recorded["G-HKLM"])

    def read(export: object, name: str) -> list[dict[str, object]]:
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:  # type: ignore[attr-defined]
            found: list[dict[str, object]] = json.loads(archive.read(f"records/{name}.json"))
            return found

    assert [one["title"] for one in read(bxyz, "modifications_change")] == [
        "Panel-Mounted Navigator"
    ]
    assert [one["mass_effect"] for one in read(bxyz, "modifications_change")] in ([1.2], ["1.2"])
    assert [one["title"] for one in read(bxyz, "modifications_bulletin")] == [
        "Alternator Mounting Bracket Inspection"
    ]
    assert [one["weighed_on"] for one in read(bxyz, "modifications_weighing")] == ["2019-06-14"]
    assert [one["issue"] for one in read(bxyz, "modifications_weightschedule")] == [6]
    for table in ("change", "bulletin", "weighing", "weightschedule"):
        assert read(hklm, f"modifications_{table}") == []


def test_the_views_of_aircraft_configuration(sample: Sample, recorded: dict[str, Aircraft]) -> None:
    """REQ-259. The Tabs board: four views, in its order."""
    client = signed_in(sample.reader)
    for path in ("/modifications/", "/weight-and-balance/"):
        body = page(client, path)
        tabs = body.split('<nav class="tabs" aria-label="Views">', 1)[1].split("</nav>", 1)[0]
        assert re.findall(r">([^<]+)</a>", tabs) == [
            "Components and Life Limits",
            "Airworthiness Directives",
            "Modifications and Repairs",
            "Weight and Balance",
        ]
        assert 'aria-current="page">Aircraft Configuration</a>' in body
