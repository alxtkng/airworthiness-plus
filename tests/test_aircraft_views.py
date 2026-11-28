"""The forecast and configuration views of an aircraft's record (REQ-290 to REQ-293).

The Aircraft board, with the sample of design-system/SampleData.md. Today
in the sample is 18 November 2026. The forecast date is ours: a
projection for planning only.

By hand, for G-ABCD on 18 November 2026, at 0.8 hours a day:

- 50-Hour Check: 12.4 hours left, 15 days, 3 December 2026.
- Left landing light, deferred to 3 December 2026: 15 days.
- Battery date 28 February 2027: 102 days.
- Review certificate valid to 14 March 2027: 116 days.
- Vacuum pump: 318.0 hours left, 397 days, 20 December 2027.
- The first four are within the next 120 days.

For G-HKLM: 12 positions; 1 life-limited, the propeller; 6 needing
attention; 4 not recorded; none recorded as required equipment.
"""

import re
from datetime import date
from decimal import Decimal

import pytest

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.components import services as component_services
from airworthiness_plus.components.models import Basis
from airworthiness_plus.configuration import forecast
from airworthiness_plus.history.session import working_for
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.sample import build, phase1
from airworthiness_rules.intervals import Interval, Reading, TaskKind
from tests.support import TODAY, Sample, get, make_sample, page, signed_in
from tests.test_modifications import rows
from tests.test_sample_seed import row_of
from tests.test_sample_seed import rows as seeded_rows

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample(monkeypatch: pytest.MonkeyPatch) -> Sample:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    monkeypatch.setattr(sign_in, "today", lambda: TODAY)
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = build.add_fleet(sample)
    build.add_programmes(sample, fleet)
    build.add_other_work(sample, fleet)
    build.add_reviews(sample, fleet)
    phase1.add_defects(sample.ours, sample.planner, fleet)
    phase1.add_contracts(sample.ours, sample.lucy, fleet)
    phase1.add_components(sample.ours, sample.planner, fleet)
    phase1.add_modifications(sample.ours, sample.planner, fleet)
    phase1.add_set_up(sample.ours, sample.lucy, fleet)
    return fleet


def test_fleet_keeps_unprojectable_tasks_in_the_due_filter(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    aircraft = fleet["G-FMNO"]
    with working_for(sample.ours.id, sample.lucy.id):
        programme = aircraft.programme
        programme.hours_per_day = None
        programme.save(update_fields=["hours_per_day"])
        programme_services.add_task(
            programme,
            title="Calendar Inspection",
            kind=TaskKind.PROGRAMME_TASK,
            counter=aircraft.counters.get(kind=CounterKind.AIRFRAME),
            source="[Maintenance Manual Reference]",
            interval=Interval(days=120),
            starts=Reading(TODAY, Decimal("4950.2"), 0),
        )
    row = row_of(seeded_rows(signed_in(sample.reader), "/?show=due"), "G-FMNO")
    assert "No Planning Utilisation" in row[4]


def test_fleet_puts_the_fitted_component_limit_beside_the_programme(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    aircraft = fleet["G-FMNO"]
    with working_for(sample.ours.id, sample.planner.id):
        component = component_services.add_component(
            sample.ours,
            name="Emergency Locator Transmitter Battery",
            basis=Basis.DATE,
            limit_date=date(2026, 11, 23),
            date_label="Battery Date",
        )
        component_services.fit_component(
            component,
            aircraft,
            position="Emergency Locator Transmitter",
            fitted_on=TODAY,
            airframe_hours_fitted=Decimal("4950.2"),
            hours_at_fitting=Decimal("0"),
            airframe_cycles_fitted=0,
            cycles_at_fitting=0,
        )
    row = row_of(seeded_rows(signed_in(sample.reader), "/?show=due"), "G-FMNO")
    assert row[4:6] == ["Emergency Locator Transmitter Battery", "5 Days"]


def test_fleet_puts_the_annual_programme_review_beside_the_programme(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    aircraft = fleet["G-FMNO"]
    with working_for(sample.ours.id, sample.lucy.id):
        programme_services.record_review(aircraft.programme, date(2025, 11, 27))
    row = row_of(seeded_rows(signed_in(sample.reader), "/?show=due"), "G-FMNO")
    assert row[4:6] == ["Maintenance Programme Annual Review", "9 Days"]


# The forecast view

FORECAST = [
    ["50-Hour Check", "6,425.0 Hours", "12.4 Hours", "3 December 2026", "",
     "[Maintenance Manual Reference]", "Maintenance Programme"],
    ["Deferred Defect Limit, Left Landing Light Inoperative", "3 December 2026", "15 Days",
     "3 December 2026", "Due Soon", "ML.A.403(b)(1)", "Defects"],
    ["Emergency Locator Transmitter Battery", "28 February 2027", "102 Days", "28 February 2027",
     "", "Battery Date", "Aircraft Configuration"],
    ["Airworthiness Review Certificate Expires", "14 March 2027", "116 Days", "14 March 2027", "",
     "ML.A.901(a)", "Airworthiness Review"],
    ["Vacuum Pump", "500.0 Hours", "318.0 Hours", "20 December 2027", "",
     "500.0 Hours, Manufacturer Recommendation", "Aircraft Configuration"],
]  # fmt: skip


def test_the_forecast_of_the_sample_on_18_november_2026(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-290, REQ-291. Golden: the Maintenance Forecast of G-ABCD, the soonest
    first, and its next 120 days, worked by hand in the heading of this file."""
    abcd = fleet["G-ABCD"]
    body = page(signed_in(sample.reader), f"/aircraft/{abcd.id}/forecast/")
    assert "<h2>Next 120 Days</h2>" in body
    assert rows(body, 1) == FORECAST
    assert rows(body, 0) == [[row[3], row[0], row[2], row[4], row[6]] for row in FORECAST[:4]]
    # Each line links to the page that owns the figure.
    assert f'<a href="/aircraft/{abcd.id}/programme/">Maintenance Programme</a>' in body
    assert f'<a href="/aircraft/{abcd.id}/review/">Airworthiness Review</a>' in body
    assert "A Forecast Date Is a Projection From the Planning Utilisation" in body
    with working_for(sample.ours.id, sample.reader.id):
        lines = forecast.forecast_lines(Aircraft.objects.get(pk=abcd.pk), TODAY)
    assert [line.forecast for line in lines] == [
        date(2026, 12, 3),
        date(2026, 12, 3),
        date(2027, 2, 28),
        date(2027, 3, 14),
        date(2027, 12, 20),
    ]


def test_what_cannot_be_placed_or_calculated_is_said_and_not_left_out(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-290. G-DGHI has no planning utilisation, so its engine's review, 25.7
    hours away, has no forecast date: the page says so, last. G-CDEF's programme
    was reviewed on 11 November 2026, so its annual review is forecast for
    11 November 2027. An aircraft still being transferred in has no forecast."""
    reader = signed_in(sample.reader)

    def whole(aircraft: Aircraft) -> list[list[str]]:
        body = page(reader, f"/aircraft/{aircraft.id}/forecast/")
        return rows("<main>" + body.split("<h2>Maintenance Forecast</h2>", 1)[1])

    dghi = whole(fleet["G-DGHI"])
    assert dghi[-1][:4] == [
        "Engine, Lycoming O-360",
        "Review at 9,900.0",
        "25.7 Hours",
        "Not Forecast, No Planning Utilisation",
    ]
    assert dghi[0][:4] == [
        "Airworthiness Review Certificate Expires",
        "19 May 2027",
        "182 Days",
        "19 May 2027",
    ]
    cdef = whole(fleet["G-CDEF"])
    annual = next(row for row in cdef if row[0] == "Maintenance Programme Annual Review")
    assert annual[1:4] == ["11 November 2027", "358 Days", "11 November 2027"]
    # 220.0 hours at 0.6 a day is 366 days: 19 November 2027, for the task and the component.
    assert [row[3] for row in cdef if row[0] in ("Engine Overhaul", "Engine, Lycoming O-360")] == [
        "19 November 2027",
        "19 November 2027",
    ]
    hklm = page(reader, f"/aircraft/{fleet['G-HKLM'].id}/forecast/")
    assert "No Due Items Until Records Are Complete" in hklm
    assert "Nothing to Forecast" in hklm and "<table>" not in hklm.split("<main", 1)[1]


def test_forecast_keeps_the_calendar_limit_when_hours_cannot_be_projected(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    aircraft = fleet["G-DGHI"]
    with working_for(sample.ours.id, sample.planner.id):
        hose = component_services.add_component(
            sample.ours,
            name="Flexible Hose",
            basis=Basis.CERTIFIED,
            limit_hours=Decimal("2000.0"),
            limit_months=60,
        )
        component_services.fit_component(
            hose,
            aircraft,
            position="Fuel System",
            fitted_on=TODAY,
            airframe_hours_fitted=Decimal("9874.3"),
            hours_at_fitting=Decimal("0"),
            airframe_cycles_fitted=0,
            cycles_at_fitting=0,
            life_from=date(2021, 12, 1),
        )
    body = page(signed_in(sample.reader), f"/aircraft/{aircraft.id}/forecast/")
    assert row_of(rows(body, 0), "1 December 2026, Hours Not Forecast")[1:4] == [
        "Flexible Hose",
        "2,000.0 Hours; 13 Days",
        "Due Soon",
    ]


def test_forecast_keeps_a_cycle_limit_beyond_the_calendar(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    aircraft = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.lucy.id):
        programme = aircraft.programme
        programme.cycles_per_day = Decimal("0.1")
        programme.save(update_fields=["cycles_per_day"])
        bearing = component_services.add_component(
            sample.ours, name="Bearing", basis=Basis.CERTIFIED, limit_cycles=999_999
        )
        component_services.fit_component(
            bearing,
            aircraft,
            position="Bearing",
            fitted_on=TODAY,
            airframe_hours_fitted=Decimal("6412.6"),
            hours_at_fitting=Decimal("0"),
            airframe_cycles_fitted=0,
            cycles_at_fitting=0,
        )
    body = page(signed_in(sample.reader), f"/aircraft/{aircraft.id}/forecast/")
    assert row_of(rows(body, 1), "Bearing")[1:4] == [
        "999,999 Cycles",
        "999,999 Cycles",
        "Not Forecast, Beyond 31 December 9999",
    ]
    assert all(row[1] != "Bearing" for row in rows(body, 0))


def test_forecast_places_a_passed_calendar_limit_on_today(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    today = date(2026, 12, 7)
    with working_for(sample.ours.id, sample.reader.id):
        lines = forecast.forecast_lines(fleet["G-EJKL"], today)
    certificate = next(
        row for row in lines if row.item == "Airworthiness Review Certificate Expires"
    )
    assert certificate.due == "6 December 2026"
    assert certificate.forecast == today
    assert certificate.status == "Overdue"
    assert certificate in forecast.next_days(lines, today)


# The configuration view


def test_the_configuration_of_the_sample_on_18_november_2026(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-292. Golden: G-HKLM's positions under the filters of the Aircraft board,
    and G-CDEF's components, installation history, changes and weighing."""
    reader = signed_in(sample.reader)
    hklm = fleet["G-HKLM"]
    address = f"/aircraft/{hklm.id}/configuration/"
    body = page(reader, address)
    chosen = body.split('<p class="filter">', 1)[1].split("</p>", 1)[0]
    assert re.findall(r">([^<]+)</a>", chosen) == [
        "All 12",
        "Life-Limited 1",
        "Required 0",
        "Needs Attention 6",
        "Not Recorded 4",
    ]
    assert len(rows(body, 0)) == 12
    assert "No Baseline Signed" in body
    assert f'<a href="/aircraft/{hklm.id}/set-up-configuration/">Set Up Configuration</a>' in body
    limited = rows(page(reader, f"{address}?show=life-limited"), 0)
    assert [row[:3] + row[5:8] for row in limited] == [
        ["Propeller, Fixed Pitch", "Propeller", "61", "Recorded",
         "2,000.0 Hours or 72 Months, Manufacturer Recommendation",
         "Calendar Limit Not Worked Out Until the Day It Was New or Last Overhauled Is Recorded"],
    ]  # fmt: skip
    missing = rows(page(reader, f"{address}?show=not-recorded"), 0)
    assert sorted(row[0] for row in missing) == [
        "Emergency Locator Transmitter Battery",
        "Fire Extinguisher",
        "Right Magneto",
        "Vacuum Pump",
    ]
    attention = rows(page(reader, f"{address}?show=needs-attention"), 0)
    assert sorted(row[0] for row in attention) == sorted(
        [*(row[0] for row in missing), "Landing Light", "Propeller, Fixed Pitch"]
    )
    assert rows(page(reader, f"{address}?show=required"), 0) == []
    # Anything else asked for shows every position.
    assert len(rows(page(reader, f"{address}?show=anything"), 0)) == 12

    cdef = page(reader, f"/aircraft/{fleet['G-CDEF'].id}/configuration/")
    assert "No Positions Recorded" in cdef
    assert sorted(row[:2] for row in rows(cdef, 0)) == [
        ["Engine, Lycoming O-360", "Engine"],
        ["Propeller, Fixed Pitch, on Loan", "Propeller"],
    ]
    assert sorted(row[:4] for row in rows(cdef, 1)) == [
        ["Engine, Lycoming O-360", "Engine", "12 March 2019", "Fitted"],
        ["Propeller, Fixed Pitch", "Propeller", "2 November 2020", "2 November 2026"],
        ["Propeller, Fixed Pitch, on Loan", "Propeller", "4 November 2026", "Fitted"],
    ]
    assert rows(cdef, 2) == [
        ["Propeller Overhaul", "Maintenance, Same Part Number", "0.0 Kilograms", "In Progress",
         "In Progress"],
    ]  # fmt: skip
    for part in (
        "<dt>Last Weighed</dt><dd>3 September 2021</dd>",
        "<dt>Schedule</dt><dd>Issue 3</dd>",
        "<dt>Net Change</dt><dd>0.0 Kilograms</dd>",
        "<dt>Weight and Balance</dt><dd>Current</dd>",
    ):
        assert part in cdef


def test_the_record_of_an_aircraft_has_its_forecast_and_configuration_among_its_views(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-293. Every role sees the aircraft tabs and reads forecast and configuration."""
    abcd = fleet["G-ABCD"]
    for user in (sample.administrator, sample.lucy, sample.planner, sample.reviewer,
                 sample.reader):  # fmt: skip
        client = signed_in(user)
        for path, active in (("forecast", "Maintenance Forecast"),
                             ("configuration", "Configuration")):  # fmt: skip
            body = page(client, f"/aircraft/{abcd.id}/{path}/")
            assert "<h1>G-ABCD</h1>\n<p>Piper PA-28 Series (Lycoming)</p>" in body
            tabs = body.split('aria-label="Views of G-ABCD">', 1)[1].split("</nav>", 1)[0]
            assert re.findall(r">([^<]+)</a>", tabs) == [
                "Record",
                "Maintenance Programme",
                "Maintenance History",
                "Maintenance Forecast",
                "Airworthiness Directives",
                "Configuration",
                "Maintenance Data",
                "Airworthiness Review",
                "Damage Register",
                "Technical Log",
            ]
            assert re.findall(r'aria-current="page">([^<]+)</a>', tabs) == [active]
            assert "<form" not in body.split("<main", 1)[1]
    stranger = signed_in(sample.stranger)
    for path in ("forecast", "configuration"):
        assert get(stranger, f"/aircraft/{abcd.id}/{path}/").status_code == 404
