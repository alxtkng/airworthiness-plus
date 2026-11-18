"""Golden cases for next-due, from design-system/SampleData.md.

Inputs are in "Maintenance Programme Inputs"; results are in the Fleet
table. Today in the sample world is 18 November 2026.
"""

from datetime import date
from decimal import Decimal

import pytest

from airworthiness_rules.dates import add_months
from airworthiness_rules.intervals import (
    Interval,
    Limit,
    Reading,
    Unit,
    Utilisation,
    comes_first,
    is_due,
    limits,
    projected_days,
)

TODAY = date(2026, 11, 18)
D = Decimal


def test_g_abcd_50_hour_check_is_12_4_hours_away() -> None:
    """REQ-045. Done at 6,375.0; due at 6,425.0; now 6,412.6; 12.4 remain."""
    found = limits(
        Interval(hours=D("50")),
        Reading(date(2026, 10, 2), D("6375.0")),
        Reading(TODAY, D("6412.6")),
    )
    assert found == (Limit(Unit.HOURS, D("6425.0"), D("12.4")),)
    assert comes_first(found, None) == found
    assert not is_due(found)


def test_g_bxyz_100_hour_or_annual_check_is_41_0_hours_away() -> None:
    """REQ-043, REQ-044. Done 30 July 2026 at 3,259.0. Hours: due 3,359.0, now
    3,318.0, 41.0 remain. Calendar: due 30 July 2027, 254 days (12 in November,
    31, 31, 28, 31, 30, 31, 30, then 30 in July). At 0.5 hours a day 41.0 hours
    is 82 days, so hours come first."""
    found = limits(
        Interval(hours=D("100"), months=12),
        Reading(date(2026, 7, 30), D("3259.0")),
        Reading(TODAY, D("3318.0")),
    )
    hours, calendar = found
    assert hours == Limit(Unit.HOURS, D("3359.0"), D("41.0"))
    assert calendar == Limit(Unit.CALENDAR, date(2027, 7, 30), 254)
    assert projected_days(hours, Utilisation(hours_per_day=D("0.5"))) == 82
    assert comes_first(found, Utilisation(hours_per_day=D("0.5"))) == (hours,)


def test_g_fmno_annual_check_is_78_days_away() -> None:
    """REQ-043, REQ-046. Done 4 February 2026 at 4,912.0. Calendar: due
    4 February 2027; 12 days left in November, 31, 31, then 4: 78 days.
    Hours: due 5,012.0, now 4,950.2, 61.8 remain; at 0.2 hours a day that is
    309 days, so the calendar limit comes first."""
    found = limits(
        Interval(hours=D("100"), months=12),
        Reading(date(2026, 2, 4), D("4912.0")),
        Reading(TODAY, D("4950.2")),
    )
    hours, calendar = found
    assert hours == Limit(Unit.HOURS, D("5012.0"), D("61.8"))
    assert calendar == Limit(Unit.CALENDAR, date(2027, 2, 4), 78)
    assert projected_days(hours, Utilisation(hours_per_day=D("0.2"))) == 309
    assert comes_first(found, Utilisation(hours_per_day=D("0.2"))) == (calendar,)


def test_limits_on_the_same_day_are_shown_together() -> None:
    """REQ-044. 41.0 hours at 0.5 hours a day is 82 days; a calendar limit
    82 days away (8 February 2027: 12 + 31 + 31 + 8) ties with it."""
    found = limits(
        Interval(hours=D("100"), days=100),
        Reading(date(2026, 10, 31), D("3259.0")),
        Reading(TODAY, D("3318.0")),
    )
    assert found[1] == Limit(Unit.CALENDAR, date(2027, 2, 8), 82)
    assert comes_first(found, Utilisation(hours_per_day=D("0.5"))) == found


def test_three_units_rank_by_projected_day() -> None:
    """REQ-043. Hours 20.0 at 1 a day: 20 days. Cycles 30 at 2 a day: 15 days.
    Calendar: 40 days. Cycles come first."""
    found = limits(
        Interval(hours=D("100"), cycles=300, days=60),
        Reading(date(2026, 10, 29), D("1000.0"), 5000),
        Reading(TODAY, D("1080.0"), 5270),
    )
    rate = Utilisation(hours_per_day=D("1"), cycles_per_day=D("2"))
    assert [limit.remaining for limit in found] == [D("20.0"), 30, 40]
    assert comes_first(found, rate) == (found[1],)


def test_without_planning_utilisation_no_limit_is_ranked() -> None:
    """REQ-044. Nothing is guessed: every limit is returned."""
    found = limits(
        Interval(hours=D("100"), months=12),
        Reading(date(2026, 7, 30), D("3259.0")),
        Reading(TODAY, D("3318.0")),
    )
    assert comes_first(found, None) == found
    assert comes_first(found, Utilisation(hours_per_day=D("0"))) == found


def test_projection_rounds_down_so_it_is_never_late() -> None:
    """REQ-044. 12.4 hours at 0.8 hours a day is 15.5 days: shown as 15."""
    limit = Limit(Unit.HOURS, D("6425.0"), D("12.4"))
    assert projected_days(limit, Utilisation(hours_per_day=D("0.8"))) == 15


def test_due_exactly_and_overdue() -> None:
    """REQ-043, REQ-055. Reaching a limit is due but not overdue; passing it is overdue."""
    interval = Interval(hours=D("50"), months=6)
    done = Reading(date(2026, 5, 18), D("100.0"))
    exact = limits(interval, done, Reading(TODAY, D("150.0")))
    assert [limit.remaining for limit in exact] == [D("0.0"), 0]
    assert is_due(exact)
    assert not any(limit.overdue for limit in exact)
    late = limits(interval, done, Reading(date(2026, 11, 19), D("150.1")))
    assert [limit.remaining for limit in late] == [D("-0.1"), -1]
    assert all(limit.overdue for limit in late)


def test_one_limit_past_makes_the_task_due_whatever_the_projection_says() -> None:
    """REQ-044. The projection never decides that a task is not yet due."""
    found = limits(
        Interval(hours=D("50"), months=12),
        Reading(date(2026, 1, 1), D("100.0")),
        Reading(TODAY, D("150.5")),
    )
    assert is_due(found)


def test_a_reached_limit_comes_first_without_any_planning_figure() -> None:
    """REQ-044. Found by the independent recompute: a limit already reached is
    never hidden behind "not ranked". 150.5 hours flown against 50 passes the
    hours limit; the calendar limit is still 44 days away (1 January 2027)."""
    found = limits(
        Interval(hours=D("50"), months=12),
        Reading(date(2026, 1, 1), D("100.0")),
        Reading(TODAY, D("150.5")),
    )
    assert [limit.remaining for limit in found] == [D("-0.5"), 44]
    assert comes_first(found, None) == (found[0],)
    assert comes_first(found, Utilisation(hours_per_day=D("0.5"))) == (found[0],)


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2028, 1, 31), 1, date(2028, 2, 29)),
        (date(2026, 8, 31), 6, date(2027, 2, 28)),
        (date(2026, 11, 30), 3, date(2027, 2, 28)),
        (date(2026, 12, 15), 1, date(2027, 1, 15)),
        (date(2028, 2, 29), 12, date(2029, 2, 28)),
        (date(2026, 2, 4), 12, date(2027, 2, 4)),
    ],
)
def test_month_intervals_at_month_ends(start: date, months: int, expected: date) -> None:
    """REQ-047. Same day of the month, or the last day of a shorter month."""
    assert add_months(start, months) == expected


def test_readings_that_go_backwards_are_refused() -> None:
    """REQ-025."""
    interval = Interval(hours=D("50"))
    with pytest.raises(ValueError, match="lower"):
        limits(interval, Reading(TODAY, D("100.0")), Reading(TODAY, D("99.9")))
    with pytest.raises(ValueError, match="before"):
        limits(interval, Reading(TODAY, D("100.0")), Reading(date(2026, 11, 17), D("100.0")))


def test_an_interval_needs_a_positive_limit() -> None:
    """REQ-041."""
    with pytest.raises(ValueError, match="at least one"):
        Interval()
    with pytest.raises(ValueError, match="greater than zero"):
        Interval(hours=D("0"))
    with pytest.raises(ValueError, match="not both"):
        Interval(months=12, days=365)
