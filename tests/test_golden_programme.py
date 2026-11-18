"""Golden cases for flags, deadlines and the programme review (REQ-051 to REQ-055, REQ-058).

Inputs are from design-system/SampleData.md. Today in the sample world is
18 November 2026.
"""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.intervals import (
    MINIMUM_INSPECTION_PROGRAMME_INTERVAL,
    MINIMUM_INSPECTION_PROGRAMME_TOLERANCE,
    Interval,
    Limit,
    Reading,
    TaskKind,
    Unit,
    limits,
)
from airworthiness_rules.programme import (
    Flag,
    Thresholds,
    deadline_flag,
    limit_flag,
    pilot_owner_notification_deadline,
    pilot_owner_told_late,
    programme_review_due,
    task_flag,
)
from airworthiness_rules.records import release_record_deadline

D = Decimal
TODAY = date(2026, 11, 18)
DEFAULT = Thresholds()


def test_the_default_thresholds_are_30_days_10_hours_and_10_cycles() -> None:
    """REQ-055."""
    assert (DEFAULT.days, DEFAULT.hours, DEFAULT.cycles) == (30, D("10.0"), 10)
    with pytest.raises(ValueError, match="below zero"):
        Thresholds(days=-1)


def test_g_abcd_50_hour_check_is_not_yet_due_soon() -> None:
    """REQ-055. 12.4 hours remain; the threshold is 10.0."""
    (hours,) = limits(
        Interval(hours=D("50")),
        Reading(date(2026, 10, 2), D("6375.0")),
        Reading(TODAY, D("6412.6")),
    )
    assert limit_flag(hours, DEFAULT) is Flag.NONE


@pytest.mark.parametrize(
    ("hours_now", "expected"),
    [
        (D("6414.9"), Flag.NONE),  # 10.1 remain
        (D("6415.0"), Flag.DUE_SOON),  # 10.0 remain
        (D("6424.9"), Flag.DUE_SOON),  # 0.1 remain
        (D("6425.0"), Flag.DUE),  # reached exactly
        (D("6425.1"), Flag.OVERDUE),  # no tolerance on this task
    ],
)
def test_g_abcd_50_hour_check_as_the_hours_run_down(hours_now: Decimal, expected: Flag) -> None:
    """REQ-055. Due at 6,425.0. Due Soon at or inside 10.0 hours; Overdue only when passed."""
    found = limits(
        Interval(hours=D("50")), Reading(date(2026, 10, 2), D("6375.0")), Reading(TODAY, hours_now)
    )
    assert task_flag(found, DEFAULT) is expected


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2027, 1, 4), Flag.NONE),  # 31 days before 4 February 2027
        (date(2027, 1, 5), Flag.DUE_SOON),  # 30 days
        (date(2027, 2, 3), Flag.DUE_SOON),  # 1 day
        (date(2027, 2, 4), Flag.DUE),
        (date(2027, 2, 5), Flag.WITHIN_TOLERANCE),  # the tolerance ends 4 March 2027
        (date(2027, 3, 4), Flag.WITHIN_TOLERANCE),
        (date(2027, 3, 5), Flag.OVERDUE),
    ],
)
def test_g_fmno_annual_check_as_the_days_run_down(today: date, expected: Flag) -> None:
    """REQ-055, REQ-056. Calendar limit 4 February 2027; hours limit 5,012.0,
    with 52.0 hours still to go at 4,960.0, so the calendar limit gives the flag."""
    found = limits(
        MINIMUM_INSPECTION_PROGRAMME_INTERVAL,
        Reading(date(2026, 2, 4), D("4912.0")),
        Reading(today, D("4960.0")),
        kind=TaskKind.MINIMUM_INSPECTION_PROGRAMME,
        tolerance=MINIMUM_INSPECTION_PROGRAMME_TOLERANCE,
    )
    assert task_flag(found, DEFAULT) is expected


def test_cycles_are_due_soon_at_10() -> None:
    """REQ-055."""
    assert limit_flag(Limit(Unit.CYCLES, 500, 11), DEFAULT) is Flag.NONE
    assert limit_flag(Limit(Unit.CYCLES, 500, 10), DEFAULT) is Flag.DUE_SOON


def test_an_organisation_may_set_its_own_thresholds() -> None:
    """REQ-055. 12.4 hours remaining is Due Soon for an organisation that warns at 15.0."""
    earlier = Thresholds(days=60, hours=D("15.0"), cycles=25)
    assert limit_flag(Limit(Unit.HOURS, D("6425.0"), D("12.4")), earlier) is Flag.DUE_SOON
    assert limit_flag(Limit(Unit.CALENDAR, date(2027, 2, 4), 60), earlier) is Flag.DUE_SOON
    assert limit_flag(Limit(Unit.CALENDAR, date(2027, 2, 4), 61), earlier) is Flag.NONE


def test_the_task_takes_the_worst_flag_of_its_limits() -> None:
    """REQ-056. Hours Due Soon and calendar Overdue: the task is Overdue."""
    found = (
        Limit(Unit.HOURS, D("5012.0"), D("3.0")),
        Limit(Unit.CALENDAR, date(2026, 11, 1), -17),
    )
    assert task_flag(found, DEFAULT) is Flag.OVERDUE


def test_g_abcd_release_to_service_deadline_is_due_soon_from_its_first_day() -> None:
    """REQ-051, REQ-055, ML.A.305(a). Tyre replaced 22 October 2026: in the records
    by 21 November 2026. Due Soon throughout, Due on the last day, Overdue after."""
    deadline = release_record_deadline(date(2026, 10, 22))
    assert deadline == date(2026, 11, 21)
    assert deadline_flag(date(2026, 10, 22), deadline) is Flag.DUE_SOON
    assert deadline_flag(TODAY, deadline) is Flag.DUE_SOON
    assert deadline_flag(date(2026, 11, 21), deadline) is Flag.DUE
    assert deadline_flag(date(2026, 11, 22), deadline) is Flag.OVERDUE


def test_the_programme_is_reviewed_within_12_months() -> None:
    """REQ-053, ML.A.302(c)(9). Reviewed with the G-CDEF airworthiness review on
    11 November 2026: next by 11 November 2027. From 29 February 2028: 28 February 2029."""
    assert programme_review_due(date(2026, 11, 11)) == date(2027, 11, 11)
    assert programme_review_due(date(2028, 2, 29)) == date(2029, 2, 28)


def test_a_pilot_owner_tells_the_organisation_within_30_days() -> None:
    """REQ-052, Appendices I and II to Part-ML. G-ABCD tyre replaced 22 October
    2026: told by 21 November 2026. Told on 21 November is in time; 22 November is late."""
    assert pilot_owner_notification_deadline(date(2026, 10, 22)) == date(2026, 11, 21)
    assert not pilot_owner_told_late(date(2026, 10, 22), date(2026, 11, 21))
    assert pilot_owner_told_late(date(2026, 10, 22), date(2026, 11, 22))
    assert not pilot_owner_told_late(date(2026, 10, 22), date(2026, 10, 22))


def test_g_cdef_engine_overhaul_never_yet_done_runs_from_the_last_overhaul() -> None:
    """REQ-058. The engine counts hours since its overhaul, 0.0 on 12 March 2019.
    Overhaul every 2,000 hours: due at 2,000.0; at 1,780.0 hours, 220.0 remain."""
    (hours,) = limits(
        Interval(hours=D("2000")),
        Reading(date(2019, 3, 12), D("0.0")),
        Reading(TODAY, D("1780.0")),
    )
    assert hours == Limit(Unit.HOURS, D("2000.0"), D("220.0"))
    assert limit_flag(hours, DEFAULT) is Flag.NONE


def test_a_first_threshold_may_differ_from_the_repeat() -> None:
    """REQ-058. First at 500 hours since new, then every 100: with the airframe
    at 420.0 hours since new, 80.0 remain; once done at 498.0, next at 598.0."""
    since_new = Reading(date(2024, 6, 1), D("0.0"))
    (first,) = limits(Interval(hours=D("500")), since_new, Reading(TODAY, D("420.0")))
    assert first == Limit(Unit.HOURS, D("500.0"), D("80.0"))
    done = Reading(date(2027, 1, 15), D("498.0"))
    (repeat,) = limits(Interval(hours=D("100")), done, done)
    assert repeat.due == D("598.0")


TENTHS = st.integers(min_value=-2_000, max_value=5_000).map(lambda n: Decimal(n) / 10)


@given(TENTHS)
def test_an_hours_flag_follows_what_remains(remaining: Decimal) -> None:
    """REQ-055. For a limit with no tolerance: Overdue below zero, Due at zero,
    Due Soon up to 10.0, nothing beyond."""
    flag = limit_flag(Limit(Unit.HOURS, D("1000.0"), remaining), DEFAULT)
    if remaining < 0:
        assert flag is Flag.OVERDUE
    elif remaining == 0:
        assert flag is Flag.DUE
    elif remaining <= D("10.0"):
        assert flag is Flag.DUE_SOON
    else:
        assert flag is Flag.NONE


@given(st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 1, 1)), st.integers(-60, 60))
def test_a_deadline_is_never_shown_as_nothing(deadline: date, before: int) -> None:
    """REQ-055. A regulatory deadline is flagged every day until it is met."""
    today = date.fromordinal(deadline.toordinal() - before)
    flag = deadline_flag(today, deadline)
    assert flag is (Flag.OVERDUE if before < 0 else Flag.DUE if before == 0 else Flag.DUE_SOON)
