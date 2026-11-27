"""The maintenance programme through the pages (REQ-040 to REQ-059, REQ-139).

The golden cases of design-system/SampleData.md, worked by the rules
package and shown on the Fleet and the programme page. Today in the sample
world is 18 November 2026.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import due, services
from airworthiness_plus.programme.models import (
    Basis,
    InspectionCategory,
    Programme,
    Task,
    WorkDone,
)
from airworthiness_rules.intervals import Interval, Reading, TaskKind
from airworthiness_rules.programme import Flag
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    call,
    dot,
    page,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db
D = Decimal
MINUS = "\N{MINUS SIGN}"  # Writing.md: a true minus sign for negative values


class Day:
    """Today, which a test may move on."""

    def __init__(self) -> None:
        self.today = TODAY

    def __call__(self) -> date:
        return self.today


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    moving = Day()
    monkeypatch.setattr(aircraft_services, "today", moving)
    return moving


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    return add_sample_fleet(sample)


@pytest.fixture
def tasks(sample: Sample, fleet: dict[str, Aircraft]) -> dict[str, Task]:
    return add_sample_programmes(sample, fleet)


def row_for(body: str, registration: str) -> str:
    """Return the Fleet row for one aircraft."""
    start = body.index(f">{registration}</a>")
    return body[start : body.index("</tr>", start)]


# The golden cases on the Fleet


def test_the_fleet_shows_what_is_due_next(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-043, REQ-045, REQ-046, REQ-058. SampleData.md, Fleet, Next Due: G-ABCD
    50-Hour Check, 12.4 Hours; G-BXYZ 100-Hour or Annual Check, 41.0 Hours; G-FMNO
    Annual Check, 78 Days; G-CDEF Engine Overhaul, 220.0 Hours."""
    body = page(signed_in(sample.reader), "/")
    assert "<td>50-Hour Check</td><td>12.4 Hours</td>" in row_for(body, "G-ABCD")
    assert "<td>100-Hour or Annual Check</td><td>41.0 Hours</td>" in row_for(body, "G-BXYZ")
    assert "<td>Annual Check</td><td>78 Days</td>" in row_for(body, "G-FMNO")
    assert "<td>Engine Overhaul</td><td>220.0 Hours</td>" in row_for(body, "G-CDEF")
    assert "<td></td>" in row_for(body, "G-EJKL")  # no programme recorded yet


def test_g_bxyz_programme_page_shows_every_limit_and_its_working(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-042 to REQ-048, REQ-054, REQ-139. Both limits, the tolerance ends, which
    is projected first, and for each figure the rule, the inputs and the source."""
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-BXYZ'].id}/programme/")
    for text in (
        "<td>3,359.0 Hours</td>",
        '<td class="number">41.0 Hours</td>',
        "<td>3,369.0 Hours</td>",
        "<td>30 July 2027</td>",
        '<td class="number">254 Days</td>',
        "<td>30 August 2027</td>",
        "<dd>Minimum Inspection Programme, Aeroplane, Touring Motor Glider or Balloon</dd>",
        "<dd>0.5 Hours a Day</dd>",
        "<dt>Last Done</dt><dd>30 July 2026 at 3,259.0 Hours</dd>",
        "<dt>Interval</dt><dd>100.0 Hours or 12 Months, Whichever Comes First</dd>",
        "<dt>Current, Airframe</dt><dd>3,318.0 Hours, Entered For 18 November 2026</dd>",
        "<dt>Tolerance</dt><dd>10.0 Hours, to 3,369.0 Hours</dd>",
        "<dt>Tolerance</dt><dd>1 Month, to 30 August 2027</dd>",
        "41.0 Hours at 0.5 Hours a Day Is 82 Days, Rounded Down",
        "<dt>Today</dt><dd>18 November 2026</dd>",
        "<dt>Source</dt><dd>ML.A.302(d), AMC1 ML.A.302(d); ML.A.302; Tolerance, "
        "ML.A.302(d)(1)</dd>",
        "Remaining Is Due Hours Less Current Hours",
    ):
        assert text in body, text
    assert body.count("Projected First") == 1
    hours_row = body[body.index("<td>3,359.0 Hours</td>") :]
    assert "Projected First" in hours_row[: hours_row.index("</tr>")]


def test_g_fmno_calendar_limit_is_projected_first(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-043, REQ-044. 61.8 hours at 0.2 a day is 309 days; the calendar limit is 78."""
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-FMNO'].id}/programme/")
    for text in (
        "<td>5,012.0 Hours</td>",
        '<td class="number">61.8 Hours</td>',
        '<td class="number">78 Days</td>',
    ):
        assert text in body
    assert "61.8 Hours at 0.2 Hours a Day Is 309 Days, Rounded Down" in body
    calendar_row = body[body.index("<td>4 February 2027</td>") :]
    assert "Projected First" in calendar_row[: calendar_row.index("</tr>")]


def test_g_fmno_shows_when_the_tolerance_was_used_and_when_twice_running(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task], day: Day
) -> None:
    """REQ-056; GM1 ML.A.302(c)(3). Nothing is refused; what happened is said.

    By hand. Due 4 February 2027 or 5,012.0. Inspected 20 February 2027 at
    4,960.0, 16 days past the calendar limit: the tolerance was used. Next
    due 20 February 2028 or 5,060.0. On 5 March 2028 at 5,000.0 it is 14
    days past again, Within Tolerance: said before the inspection is done.
    Inspected that day: used at two in a row. Next due 5 March 2029.
    Inspected 1 March 2029 at 5,040.0, on time: nothing more is said.
    """
    fmno = fleet["G-FMNO"]
    path = f"/aircraft/{fmno.id}/programme/"
    reader = signed_in(sample.reader)
    assert "Tolerance Used" not in page(reader, path)

    def inspect(on: date, hours: str) -> None:
        day.today = on
        with working_for(sample.ours.id, sample.lucy.id):
            aircraft = Aircraft.objects.get(pk=fmno.pk)
            aircraft_services.enter_utilisation(
                aircraft.counters.get(kind="Airframe"), Reading(on, D(hours), 0), confirmed=True
            )
            services.record_work(
                aircraft,
                task=tasks["G-FMNO"],
                description="Annual Check",
                dated=on,
                hours=D(hours),
                cycles=0,
            )

    inspect(date(2027, 2, 20), "4960.0")
    body = page(reader, path)
    assert '<td colspan="7">Tolerance Used at the Last Inspection, 20 February 2027</td>' in body
    assert "One-Time Extension" not in body

    day.today = date(2028, 3, 5)
    body = page(reader, path)
    assert dot("Within Tolerance") in body
    assert (
        "Within Tolerance Again: the Tolerance Was Used at the Last Inspection, 20 February "
        "2027. GM1 ML.A.302(c)(3) Calls the Tolerance a One-Time Extension"
    ) in body

    inspect(date(2028, 3, 5), "5000.0")
    body = page(reader, path)
    assert (
        "Tolerance Used at the Last Two Inspections, the Latest on 5 March 2028. "
        "GM1 ML.A.302(c)(3) Calls the Tolerance a One-Time Extension"
    ) in body

    inspect(date(2029, 3, 1), "5040.0")
    assert "Tolerance Used" not in page(reader, path)


def test_g_abcd_task_has_no_tolerance_and_one_limit(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-049. Not a Minimum Inspection Programme inspection: no tolerance is shown."""
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-ABCD'].id}/programme/")
    assert "<td>6,425.0 Hours</td>" in body
    assert '<td class="number">12.4 Hours</td>' in body
    assert "Only Limit" in body
    assert "<dt>Tolerance</dt>" not in body
    with working_for(sample.ours.id, sample.lucy.id):
        (line,) = due.due_lines(Aircraft.objects.get(pk=fleet["G-ABCD"].pk), TODAY)
    assert line.limits[0].limit.tolerance_limit is None
    assert line.flag is Flag.NONE


def test_g_cdef_engine_overhaul_runs_against_the_engine_from_its_overhaul(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-058, REQ-059. Never yet done here: counted from 0.0 on 12 March 2019,
    against the engine's hours, not the airframe's 7,731.5."""
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-CDEF'].id}/programme/")
    for text in (
        "<td>2,000.0 Hours</td>",
        '<td class="number">220.0 Hours</td>',
        "<dt>Counted From, Never Yet Done</dt><dd>12 March 2019 at 0.0 Hours</dd>",
        "<dt>First Threshold</dt><dd>2,000.0 Hours</dd>",
        "<dt>Current, Engine 1</dt><dd>1,780.0 Hours, Entered For 18 November 2026</dd>",
        "<dt>Last Reviewed</dt><dd>11 November 2026</dd>",
        "<dt>Next Review By</dt><dd>11 November 2027</dd>",
    ):
        assert text in body, text


# Due Soon, and thresholds of the organisation


def test_due_soon_follows_the_organisations_thresholds(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-055. 12.4 hours is outside the default 10.0 and inside 15.0."""
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.lucy.id):
        (line,) = due.due_lines(Aircraft.objects.get(pk=abcd.pk), TODAY)
        assert line.flag is Flag.NONE
    with working_for(sample.ours.id, sample.administrator.id):
        Organisation.objects.filter(pk=sample.ours.pk).update(due_soon_hours=D("15.0"))
    with working_for(sample.ours.id, sample.lucy.id):
        (line,) = due.due_lines(Aircraft.objects.get(pk=abcd.pk), TODAY)
        assert line.flag is Flag.DUE_SOON
    body = page(signed_in(sample.reader), f"/aircraft/{abcd.id}/programme/")
    assert f"<td>{dot('Due Soon')}</td>" in body


def test_flags_as_g_fmno_runs_into_and_past_its_tolerance(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task], day: Day
) -> None:
    """REQ-055, REQ-056. Due 4 February 2027; the tolerance ends 4 March 2027."""
    client = signed_in(sample.reader)
    path = f"/aircraft/{fleet['G-FMNO'].id}/programme/"
    for today, flag in (
        (date(2027, 1, 5), "Due Soon"),
        (date(2027, 2, 4), "Due"),
        (date(2027, 2, 20), "Within Tolerance"),
        (date(2027, 3, 5), "Overdue"),
    ):
        day.today = today
        client = signed_in(sample.reader)
        assert f"<td>{dot(flag)}</td>" in page(client, path), today
    day.today = date(2027, 2, 20)
    body = page(signed_in(sample.reader), "/")
    assert f"<td>Annual Check</td><td>{MINUS}16 Days</td>" in row_for(body, "G-FMNO")


# Ranking


def test_with_no_planning_utilisation_nothing_is_ranked(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-044. Every limit is shown; none is called first; the Fleet says so."""
    bxyz = fleet["G-BXYZ"]
    with working_for(sample.ours.id, sample.lucy.id):
        Programme.objects.filter(aircraft=bxyz).update(hours_per_day=None)
    client = signed_in(sample.reader)
    body = page(client, f"/aircraft/{bxyz.id}/programme/")
    assert "Projected First" not in body
    assert body.count("<td>Not Ranked</td>") == 2
    assert "No Planning Utilisation Recorded, So Limits Are Not Ranked" in body
    row = row_for(page(client, "/"), "G-BXYZ")
    assert "<td>100-Hour or Annual Check</td><td>41.0 Hours or 254 Days</td>" in row


def test_a_reached_limit_comes_first_whatever_the_planning_figures(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-044. G-ABCD flown to 6,425.5: the 50-Hour Check is 0.5 hours past and Overdue."""
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.planner.id):
        counter = abcd.counters.get(kind=CounterKind.AIRFRAME)
        aircraft_services.enter_utilisation(counter, Reading(TODAY, D("6425.5"), 0), confirmed=True)
    client = signed_in(sample.reader)
    assert f"<td>50-Hour Check</td><td>{MINUS}0.5 Hours</td>" in row_for(
        page(client, "/"), "G-ABCD"
    )
    body = page(client, f"/aircraft/{abcd.id}/programme/")
    assert f"<td>{dot('Overdue')}</td>" in body


def test_a_task_that_cannot_be_calculated_is_shown_first_never_as_not_due(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-058. Found by the independent recompute. A task never yet done with no
    starting point recorded: nobody knows where it stands, and the pages say so."""
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.lucy.id):
        programme = Programme.objects.get(aircraft=abcd)
        services.add_task(
            programme,
            title="Fire Extinguisher Weight Check",
            kind=TaskKind.PROGRAMME_TASK,
            counter=abcd.counters.get(kind=CounterKind.AIRFRAME),
            source="[Manufacturer's Instructions]",
            interval=Interval(months=12),
        )
    client = signed_in(sample.reader)
    body = page(client, f"/aircraft/{abcd.id}/programme/")
    assert "Cannot Be Calculated, No Starting Point Recorded" in body
    # A row of its own, marked so that sorting by Status puts it first.
    assert "<td>Cannot Be Calculated, No Starting Point Recorded</td>" in body
    assert "<td data-attention></td>" in body
    row = row_for(page(client, "/"), "G-ABCD")
    assert "Fire Extinguisher Weight Check" in row
    assert "No Starting Point Recorded</td>" in row


def test_nothing_is_calculated_for_a_transfer_in(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-027. G-HKLM: a programme may be recorded, but no due item is shown."""
    hklm = fleet["G-HKLM"]
    with working_for(sample.ours.id, sample.lucy.id):
        programme = services.set_up_programme(
            hklm, basis=Basis.INSTRUCTIONS, reference="[Programme Reference]"
        )
        services.add_task(
            programme,
            title="50-Hour Check",
            kind=TaskKind.PROGRAMME_TASK,
            counter=hklm.counters.get(kind=CounterKind.AIRFRAME),
            source="[Maintenance Manual Reference]",
            interval=Interval(hours=D("50")),
            starts=Reading(TODAY, D("0.0"), 0),
        )
        assert due.due_lines(Aircraft.objects.get(pk=hklm.pk), TODAY) == []
    body = page(signed_in(sample.reader), f"/aircraft/{hklm.id}/programme/")
    assert "No Due Items Until Records Are Complete" in body
    assert "50-Hour Check" not in body


# The Minimum Inspection Programme


def test_a_minimum_inspection_programme_inspection_keeps_to_the_regulation(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-040, REQ-048, ML.A.302(d)(1). Not less often than 100 hours or annually,
    and only in a programme on that basis."""
    with working_for(sample.ours.id, sample.lucy.id):
        mip = Programme.objects.get(aircraft=fleet["G-BXYZ"])
        counter = fleet["G-BXYZ"].counters.get(kind=CounterKind.AIRFRAME)
        common = {
            "title": "Inspection",
            "kind": TaskKind.MINIMUM_INSPECTION_PROGRAMME,
            "counter": counter,
            "source": "ML.A.302(d)",
        }
        for interval, message in (
            (Interval(hours=D("150"), months=12), "100 Hours"),
            (Interval(hours=D("100"), months=24), "Annual"),
            (Interval(months=12), "100 Hours"),
            (Interval(hours=D("100")), "Annual"),
        ):
            with pytest.raises(services.RefusedError, match=message):
                services.add_task(mip, interval=interval, **common)  # type: ignore[arg-type]
        # More often than the regulation asks is allowed.
        services.add_task(mip, interval=Interval(hours=D("50"), months=6), **common)  # type: ignore[arg-type]

        other = Programme.objects.get(aircraft=fleet["G-ABCD"])
        with pytest.raises(services.RefusedError, match="on That Basis"):
            services.add_task(
                other,
                title="Inspection",
                kind=TaskKind.MINIMUM_INSPECTION_PROGRAMME,
                counter=fleet["G-ABCD"].counters.get(kind=CounterKind.AIRFRAME),
                source="ML.A.302(d)",
                interval=Interval(hours=D("100"), months=12),
            )
        with pytest.raises(services.RefusedError, match="Another Aircraft"):
            services.add_task(
                other,
                title="50-Hour Check",
                kind=TaskKind.PROGRAMME_TASK,
                counter=counter,
                source="[Maintenance Manual Reference]",
                interval=Interval(hours=D("50")),
            )
        with pytest.raises(services.RefusedError, match="Says Which Aircraft"):
            services.set_up_programme(
                fleet["G-EJKL"],
                basis=Basis.MINIMUM_INSPECTION_PROGRAMME,
                reference="[Programme Reference]",
            )


def test_a_programme_does_not_change_under_its_minimum_inspection_programme_inspections(
    sample: Sample, fleet: dict[str, Aircraft], day: Day
) -> None:
    """REQ-040, REQ-048, ML.A.302(d)(1); review of 20 November 2026, finding 4.

    What is refused when an inspection is added is refused when the
    programme is changed under it. A sailplane's annual inspection has no
    100-hour interval, so the programme cannot become an aeroplane's; and an
    inspection of the Minimum Inspection Programme cannot stay live in a
    programme on the design approval holder's instructions, where it would
    keep a tolerance the regulation does not give."""
    ejkl = fleet["G-EJKL"]
    sailplane = {
        "basis": Basis.MINIMUM_INSPECTION_PROGRAMME,
        "inspection_category": InspectionCategory.SAILPLANE,
        "reference": "[Programme Reference]",
    }
    with working_for(sample.ours.id, sample.lucy.id):
        programme = services.set_up_programme(ejkl, **sailplane)  # type: ignore[arg-type]
        inspection = services.add_task(
            programme,
            title="Annual Inspection",
            kind=TaskKind.MINIMUM_INSPECTION_PROGRAMME,
            counter=ejkl.counters.get(kind=CounterKind.AIRFRAME),
            source="ML.A.302(d)",
            interval=Interval(months=12),
            starts=Reading(date(2025, 11, 3), D("0"), 0),
        )
        with pytest.raises(services.RefusedError, match="at Least Every 100 Hours"):
            services.set_up_programme(
                ejkl,
                basis=Basis.MINIMUM_INSPECTION_PROGRAMME,
                inspection_category=InspectionCategory.AEROPLANE,
                reference="[Programme Reference]",
            )
        with pytest.raises(services.RefusedError, match="Retire Its Inspections"):
            services.set_up_programme(
                ejkl, basis=Basis.INSTRUCTIONS, reference="[Programme Reference]"
            )
        programme.refresh_from_db()
        assert programme.basis == Basis.MINIMUM_INSPECTION_PROGRAMME
        assert programme.inspection_category == InspectionCategory.SAILPLANE
        # What does not touch the inspections still changes.
        services.set_up_programme(ejkl, **{**sailplane, "reference": "[Programme Reference 2]"})  # type: ignore[arg-type]

    client = signed_in(sample.lucy)
    refused = post(
        client,
        f"/aircraft/{ejkl.id}/programme/set-up/",
        basis=Basis.INSTRUCTIONS,
        reference="[Programme Reference]",
    )
    assert refused.status_code == 200
    assert "Retire Its Inspections" in refused.content.decode()

    # Once the inspection is retired the basis can change.
    with working_for(sample.ours.id, sample.lucy.id):
        services.retire_task(inspection)
        services.set_up_programme(ejkl, basis=Basis.INSTRUCTIONS, reference="[Programme Reference]")


def test_a_tolerance_is_given_only_in_a_minimum_inspection_programme(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task], day: Day
) -> None:
    """REQ-048, ML.A.302(d)(1); review of 20 November 2026, finding 4.

    The second line of defence. G-FMNO's inspection was last done on 4
    February 2026, so it is due on 4 February 2027. On 20 February 2027 it
    is 16 days past: Within Tolerance in its own programme. Were the basis
    of the programme changed behind the service, the same inspection has no
    tolerance and is Overdue."""
    fmno = fleet["G-FMNO"]
    day.today = date(2027, 2, 20)
    path = f"/aircraft/{fmno.id}/programme/"
    reader = signed_in(sample.reader)
    assert dot("Within Tolerance") in page(reader, path)
    with working_for(sample.ours.id, sample.lucy.id):
        Programme.objects.filter(aircraft=fmno).update(
            basis=Basis.INSTRUCTIONS, inspection_category=""
        )
    body = page(reader, path)
    assert dot("Overdue") in body
    assert "Within Tolerance" not in body
    assert "Tolerance 1 Month" not in body


# Work done


def test_each_time_a_task_is_done_is_kept_and_the_next_runs_from_the_last(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-050. G-ABCD 50-Hour Check done again on 18 November 2026 at 6,412.6:
    next due 6,462.6. The check of 2 October stays in the record."""
    client = signed_in(sample.planner)
    abcd = fleet["G-ABCD"]
    recorded = post(
        client,
        f"/aircraft/{abcd.id}/work/add/",
        task=str(tasks["G-ABCD"].id),
        description="50-Hour Check",
        dated="2026-11-18",
        hours="6412.6",
        cycles="0",
        release_reference="[Release Reference 2]",
    )
    assert recorded.status_code == 302
    body = page(client, f"/aircraft/{abcd.id}/programme/")
    assert "<td>6,462.6 Hours</td>" in body
    assert '<td class="number">50.0 Hours</td>' in body
    assert "<td>2 October 2026</td>" in body
    assert "<td>18 November 2026</td>" in body
    with working_for(sample.ours.id, sample.planner.id):
        assert WorkDone.objects.filter(task=tasks["G-ABCD"]).count() == 2
        for dated, hours, message in (
            (date(2026, 11, 19), "6412.6", "After Today"),
            (TODAY, "6500.0", "Above the Hours"),
            (date(2026, 11, 1), "6400.0", "Before the Last Time"),
        ):
            with pytest.raises(services.RefusedError, match=message):
                services.record_work(
                    Aircraft.objects.get(pk=abcd.pk),
                    task=tasks["G-ABCD"],
                    description="50-Hour Check",
                    dated=dated,
                    hours=D(hours),
                    cycles=0,
                )


def test_g_abcd_release_to_service_deadline_is_shown_and_flagged(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task], day: Day
) -> None:
    """REQ-051, REQ-052, REQ-055. Right main tyre replaced by the pilot-owner on
    22 October 2026: the release is to be in the records by 21 November 2026."""
    client = signed_in(sample.planner)
    abcd = fleet["G-ABCD"]
    path = f"/aircraft/{abcd.id}/programme/"
    recorded = post(
        client,
        f"/aircraft/{abcd.id}/work/add/",
        description="Right Main Tyre Replaced",
        dated="2026-10-22",
        hours="6390.0",
        cycles="0",
        by_pilot_owner="on",
    )
    assert recorded.status_code == 302
    body = page(client, path)
    assert "To Be Recorded by 21 November 2026, Due Soon" in body
    # REQ-139. By hand: 9 days left in October and 21 in November is 30 days.
    for title, source in (
        ("How the Release by 21 November 2026 Was Calculated", "ML.A.305(a)"),
        ("How Told by 21 November 2026 Was Calculated", "Appendices I and II to Part-ML"),
    ):
        assert f"<summary>{title}</summary>" in body, title
        working = body.split(f"<summary>{title}</summary>", 1)[1].split("</details>", 1)[0]
        assert "<dt>Completed</dt><dd>22 October 2026</dd>" in working
        assert "<dt>Days Allowed</dt><dd>30</dd>" in working
        assert f"<dt>Source</dt><dd>{source}</dd>" in working

    day.today = date(2026, 11, 21)
    assert "To Be Recorded by 21 November 2026, Due\n" in page(signed_in(sample.planner), path)
    day.today = date(2026, 11, 25)
    client = signed_in(sample.planner)
    assert "To Be Recorded by 21 November 2026, Overdue" in page(client, path)

    with working_for(sample.ours.id, sample.planner.id):
        work = WorkDone.objects.get(description="Right Main Tyre Replaced")
        work.pilot_owner_told_on = date(2026, 11, 25)
        work.save(update_fields=["pilot_owner_told_on"])
    legacy = post(client, f"/work/{work.id}/release/", release_reference="[Release Reference 3]")
    assert legacy.status_code == 302
    endpoint = f"/release-to-service/{work.id}/record/"
    assert legacy["Location"] == endpoint
    with working_for(sample.ours.id, sample.planner.id):
        work.refresh_from_db()
        assert not work.release_reference
    released = post(
        client,
        endpoint,
        reference="[Release Reference 3]",
        kind="Pilot-Owner",
        issuer_name="[Pilot Owner]",
        licence="[Pilot Licence]",
        issued_on="2026-10-22",
    )
    assert released.status_code == 302
    body = page(client, path)
    assert "[Release Reference 3], Recorded 25 November 2026, After the 30 Days" in body
    assert "Pilot-Owner Maintenance, Organisation Told 25 November 2026, After the 30 Days" in body
    assert "To Be Recorded by" not in body


def test_a_retired_task_leaves_the_programme_and_stays_in_the_record(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-131."""
    client = signed_in(sample.lucy)
    abcd = fleet["G-ABCD"]
    assert post(client, f"/tasks/{tasks['G-ABCD'].id}/retire/").status_code == 302
    assert "<td>6,425.0 Hours</td>" not in page(client, f"/aircraft/{abcd.id}/programme/")
    with working_for(sample.ours.id, sample.lucy.id):
        assert Task.objects.get(pk=tasks["G-ABCD"].pk).retired
        assert WorkDone.objects.filter(task=tasks["G-ABCD"]).count() == 1


def test_a_programme_and_a_task_are_recorded_through_the_pages(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-040, REQ-041, REQ-058. G-EJKL: the programme, then a task first due at
    a threshold since a stated starting point."""
    client = signed_in(sample.lucy)
    ejkl = fleet["G-EJKL"]
    saved = post(
        client,
        f"/aircraft/{ejkl.id}/programme/set-up/",
        basis="Design Approval Holder's Instructions",
        reference="[Programme Reference]",
        hours_per_day="0.4",
    )
    assert saved.status_code == 302
    with working_for(sample.ours.id, sample.lucy.id):
        counter = ejkl.counters.get(kind=CounterKind.AIRFRAME)
    added = post(
        client,
        f"/aircraft/{ejkl.id}/programme/tasks/add/",
        title="Seat Rail Inspection",
        kind="Programme Task",
        counter=str(counter.id),
        source="[Maintenance Manual Reference]",
        interval_hours="100",
        first_hours="11300",
        starts_dated="1979-05-01",
        starts_hours="0.0",
        starts_cycles="0",
    )
    assert added.status_code == 302
    body = page(client, f"/aircraft/{ejkl.id}/programme/")
    assert "<td>11,300.0 Hours</td>" in body
    assert '<td class="number">93.2 Hours</td>' in body  # 11,300.0 less 11,206.8
    assert "<dt>First Threshold</dt><dd>11,300.0 Hours</dd>" in body

    no_interval = post(
        client,
        f"/aircraft/{ejkl.id}/programme/tasks/add/",
        title="No Interval",
        kind="Programme Task",
        counter=str(counter.id),
        source="[Source]",
    )
    assert no_interval.status_code == 200
    assert "A Task Has an Interval" in no_interval.content.decode()


def test_the_programme_review_is_recorded_by_those_the_matrix_allows(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-053, ML.A.302(c)(9). Airworthiness Review Staff may record it; Planning
    and Records may not."""
    cdef = fleet["G-CDEF"]
    path = f"/aircraft/{cdef.id}/programme/review/"
    assert post(signed_in(sample.planner), path, reviewed_on="2026-11-18").status_code == 403
    assert post(signed_in(sample.reviewer), path, reviewed_on="2026-11-18").status_code == 302
    body = page(signed_in(sample.reader), f"/aircraft/{cdef.id}/programme/")
    assert "<dt>Next Review By</dt><dd>18 November 2027</dd>" in body
    # A review dated after today is not recorded.
    post(signed_in(sample.reviewer), path, reviewed_on="2026-12-25")
    with working_for(sample.ours.id, sample.lucy.id):
        assert Programme.objects.get(aircraft=cdef).last_reviewed == TODAY


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)

AIRCRAFT_PAGES = (
    ("GET", "/programme/", Action.VIEW_RECORDS),
    ("GET", "/programme/set-up/", Action.CHANGE_MAINTENANCE_PROGRAMME),
    ("POST", "/programme/set-up/", Action.CHANGE_MAINTENANCE_PROGRAMME),
    ("GET", "/programme/tasks/add/", Action.CHANGE_MAINTENANCE_PROGRAMME),
    ("POST", "/programme/tasks/add/", Action.CHANGE_MAINTENANCE_PROGRAMME),
    ("POST", "/programme/review/", Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW),
    ("GET", "/work/add/", Action.RECORD_ACCOMPLISHMENT),
    ("POST", "/work/add/", Action.RECORD_ACCOMPLISHMENT),
)


def test_future_and_older_programme_reviews_are_refused_with_reasons(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    aircraft = fleet["G-CDEF"]
    path = f"/aircraft/{aircraft.id}/programme/review/"
    manager = signed_in(sample.lucy)
    assert post(manager, path, reviewed_on="2026-11-18").status_code == 302
    for day, reason in (("2026-11-19", "After Today"), ("2026-11-01", "Before the Last Review")):
        refused = post(manager, path, reviewed_on=day)
        assert refused.status_code == 409
        assert reason in refused.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert Programme.objects.get(aircraft=aircraft).last_reviewed == TODAY


def addresses(aircraft: Aircraft, task: Task, work: WorkDone) -> list[tuple[str, str, Action]]:
    pages = [(m, f"/aircraft/{aircraft.id}{tail}", a) for m, tail, a in AIRCRAFT_PAGES]
    pages.append(("POST", f"/tasks/{task.id}/retire/", Action.CHANGE_MAINTENANCE_PROGRAMME))
    pages.append(("POST", f"/work/{work.id}/release/", Action.RECORD_ACCOMPLISHMENT))
    return pages


def one_work(sample: Sample, task: Task) -> WorkDone:
    with working_for(sample.ours.id, sample.lucy.id):
        return WorkDone.objects.filter(task=task).get()


def test_another_organisations_programme_is_not_found_on_any_page(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. Read and write."""
    stranger = signed_in(sample.stranger)
    work = one_work(sample, tasks["G-BXYZ"])
    for method, path, _ in addresses(fleet["G-BXYZ"], tasks["G-BXYZ"], work):
        assert call(stranger, method, path).status_code == 404, f"{method} {path}"
    with as_owner():
        assert not Task.objects.get(pk=tasks["G-BXYZ"].pk).retired
        assert WorkDone.objects.get(pk=work.pk).release_reference == "[Release Reference]"


@pytest.mark.parametrize(
    "role",
    ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"],
)
def test_every_programme_page_follows_the_role_matrix(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task], role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refused with 403 and logged
    for a role the matrix does not allow; answered for one it does."""
    user = sample.by_role()[role]
    client = signed_in(user)
    work = one_work(sample, tasks["G-FMNO"])
    refusals = 0
    for method, path, action in addresses(fleet["G-FMNO"], tasks["G-FMNO"], work):
        if action is Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW:
            status = post(client, path, reviewed_on="2026-11-18").status_code
        else:
            status = call(client, method, path).status_code
        if permitted(user.roles, action):
            assert status in (200, 302), f"{role} {method} {path}"
        else:
            assert status == 403, f"{role} {method} {path}"
            refusals += 1
    with working_for(sample.ours.id, user.id):
        logged = AccessEntry.objects.filter(user=user, kind="Action Refused").count()
    assert logged == refusals
    expected = {
        "Administrator": 9,
        "Airworthiness Review Staff": 8,
        "Planning and Records": 6,
        "Read Only": 9,
    }
    assert refusals == expected[role]


def test_programme_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, fleet: dict[str, Aircraft], tasks: dict[str, Task]
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    work = one_work(sample, tasks["G-ABCD"])
    pages = addresses(fleet["G-ABCD"], tasks["G-ABCD"], work)
    anonymous = Client()
    for method, path, _ in pages:
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.lucy, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in pages:
        if method == "POST":
            assert post(forged, path).status_code == 403, path


def test_record_work_keeps_the_person_who_performed_it(
    sample: Sample,
    fleet: dict[str, Aircraft],
) -> None:
    from airworthiness_plus.people import services as people_services
    from airworthiness_plus.people.models import StaffGroup

    with working_for(sample.ours.id, sample.lucy.id):
        mechanic = people_services.add_person(
            organisation=sample.ours, full_name="Sample Mechanic", staff_group=StaffGroup.CERTIFYING
        )
    aircraft = fleet["G-ABCD"]
    response = post(
        signed_in(sample.planner),
        f"/aircraft/{aircraft.id}/work/add/",
        description="Attribution Check",
        dated="2026-11-18",
        hours="6412.6",
        cycles="0",
        performed_by=str(mechanic.id),
    )
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        work = WorkDone.objects.get(description="Attribution Check")
        assert work.performed_by == mechanic
        assert work.performed_by_name == "Sample Mechanic"
    recency = page(signed_in(sample.reader), "/review-staff/recency/")
    assert "Last Attributed Work" in recency
    assert "Last Recorded Work 18 November 2026" in recency
