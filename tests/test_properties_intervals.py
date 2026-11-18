"""Property-based tests for interval arithmetic."""

from datetime import date, timedelta
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.dates import add_months
from airworthiness_rules.intervals import (
    MINIMUM_INSPECTION_PROGRAMME_INTERVAL,
    MINIMUM_INSPECTION_PROGRAMME_TOLERANCE,
    Interval,
    Reading,
    State,
    TaskKind,
    Unit,
    Utilisation,
    comes_first,
    is_due,
    limits,
    projected_days,
    task_state,
)

DATES = st.dates(min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))
TENTHS = st.integers(min_value=0, max_value=500_000).map(lambda n: Decimal(n) / 10)
POSITIVE_TENTHS = st.integers(min_value=1, max_value=50_000).map(lambda n: Decimal(n) / 10)
RATES = st.integers(min_value=1, max_value=200).map(lambda n: Decimal(n) / 10)


@given(TENTHS, POSITIVE_TENTHS, TENTHS, DATES)
def test_hours_remaining_is_interval_less_hours_flown(
    done_at: Decimal, interval: Decimal, flown: Decimal, day: date
) -> None:
    (limit,) = limits(
        Interval(hours=interval), Reading(day, done_at), Reading(day, done_at + flown)
    )
    assert limit.due == done_at + interval
    assert limit.remaining == interval - flown
    assert limit.overdue == (flown > interval)


@given(TENTHS, POSITIVE_TENTHS, TENTHS, TENTHS, DATES)
def test_flying_more_never_increases_what_remains(
    done_at: Decimal, interval: Decimal, flown: Decimal, more: Decimal, day: date
) -> None:
    task = Interval(hours=interval)
    done = Reading(day, done_at)
    (before,) = limits(task, done, Reading(day, done_at + flown))
    (after,) = limits(task, done, Reading(day, done_at + flown + more))
    assert after.remaining <= before.remaining


@given(DATES, st.integers(min_value=1, max_value=120), st.integers(min_value=0, max_value=5_000))
def test_calendar_remaining_falls_by_one_each_day(done: date, months: int, elapsed: int) -> None:
    task = Interval(months=months)
    today = done + timedelta(days=elapsed)
    (first,) = limits(task, Reading(done, Decimal(0)), Reading(today, Decimal(0)))
    (second,) = limits(
        task, Reading(done, Decimal(0)), Reading(today + timedelta(days=1), Decimal(0))
    )
    assert first.due == add_months(done, months)
    assert second.remaining == first.remaining - 1


@given(DATES, st.integers(min_value=1, max_value=600))
def test_adding_months_never_changes_the_day_except_to_shorten_it(start: date, months: int) -> None:
    result = add_months(start, months)
    assert (result.year * 12 + result.month) - (start.year * 12 + start.month) == months
    assert result.day <= start.day
    if result.day < start.day:
        assert (result + timedelta(days=1)).day == 1


@given(
    POSITIVE_TENTHS,
    TENTHS,
    st.integers(min_value=1, max_value=120),
    st.integers(min_value=0, max_value=4_000),
    RATES,
    DATES,
)
def test_what_comes_first_has_the_smallest_projection(
    interval: Decimal, flown: Decimal, months: int, elapsed: int, rate: Decimal, done: date
) -> None:
    found = limits(
        Interval(hours=interval, months=months),
        Reading(done, Decimal(1000)),
        Reading(done + timedelta(days=elapsed), Decimal(1000) + flown),
    )
    utilisation = Utilisation(hours_per_day=rate)
    first = comes_first(found, utilisation)
    assert first
    assert set(first) <= set(found)
    reached = tuple(limit for limit in found if limit.remaining <= 0)
    if reached:
        # A limit already reached needs no projection: all reached limits come first.
        assert first == reached
        return
    days = {limit.unit: projected_days(limit, utilisation) for limit in found}
    soonest = min(value for value in days.values() if value is not None)
    assert all(days[limit.unit] == soonest for limit in first)
    assert all(days[limit.unit] != soonest for limit in found if limit not in first)


@given(POSITIVE_TENTHS, TENTHS, RATES)
def test_projection_is_never_later_than_the_rate_implies(
    interval: Decimal, flown: Decimal, rate: Decimal
) -> None:
    day = date(2026, 11, 18)
    (limit,) = limits(Interval(hours=interval), Reading(day, Decimal(0)), Reading(day, flown))
    days = projected_days(limit, Utilisation(hours_per_day=rate))
    assert days is not None
    assert days * rate <= limit.remaining
    assert (days + 1) * rate > limit.remaining


@given(POSITIVE_TENTHS, TENTHS, st.integers(min_value=1, max_value=120), DATES)
def test_due_does_not_depend_on_planning_utilisation(
    interval: Decimal, flown: Decimal, months: int, done: date
) -> None:
    found = limits(
        Interval(hours=interval, months=months),
        Reading(done, Decimal(0)),
        Reading(done, flown),
    )
    assert is_due(found) == any(limit.remaining <= 0 for limit in found)
    assert {limit.unit for limit in found} == {Unit.HOURS, Unit.CALENDAR}


@given(TENTHS, TENTHS, st.integers(min_value=0, max_value=800), DATES)
def test_a_tolerance_changes_nothing_but_when_a_limit_is_overdue(
    done_at: Decimal, flown: Decimal, elapsed: int, done: date
) -> None:
    """REQ-048, REQ-056. For any inspection of the Minimum Inspection Programme:
    the due points and what remains are the same with and without the
    tolerance; the tolerance ends exactly 10.0 hours and 1 month later; the
    task is due at the same moment; and the tolerance only ever delays overdue."""
    last = Reading(done, done_at)
    current = Reading(done + timedelta(days=elapsed), done_at + flown)
    plain = limits(MINIMUM_INSPECTION_PROGRAMME_INTERVAL, last, current)
    toleranced = limits(
        MINIMUM_INSPECTION_PROGRAMME_INTERVAL,
        last,
        current,
        kind=TaskKind.MINIMUM_INSPECTION_PROGRAMME,
        tolerance=MINIMUM_INSPECTION_PROGRAMME_TOLERANCE,
    )
    assert is_due(plain) == is_due(toleranced)
    for without, with_tolerance in zip(plain, toleranced, strict=True):
        assert (without.unit, without.due, without.remaining) == (
            with_tolerance.unit,
            with_tolerance.due,
            with_tolerance.remaining,
        )
        assert with_tolerance.tolerance_remaining is not None
        extra = with_tolerance.tolerance_remaining - with_tolerance.remaining
        if with_tolerance.unit is Unit.HOURS:
            assert extra == Decimal("10")
        else:
            assert isinstance(with_tolerance.due, date)
            assert with_tolerance.tolerance_limit == add_months(with_tolerance.due, 1)
            assert 28 <= extra <= 31
        assert with_tolerance.overdue == (with_tolerance.tolerance_remaining < 0)
        assert with_tolerance.within_tolerance == (
            with_tolerance.remaining < 0 <= with_tolerance.tolerance_remaining
        )
        if with_tolerance.overdue:
            assert without.overdue
        assert not (with_tolerance.overdue and with_tolerance.within_tolerance)
    # The task is never shown better than its worst limit.
    whole = task_state(toleranced)
    assert (whole is State.OVERDUE) == any(limit.overdue for limit in toleranced)
    assert (whole is State.NOT_DUE) == (not is_due(toleranced))
    assert all(list(State).index(limit.state) <= list(State).index(whole) for limit in toleranced)


@given(TENTHS, TENTHS, st.integers(min_value=0, max_value=800), DATES)
def test_the_next_interval_depends_only_on_when_the_inspection_was_done(
    previous_hours: Decimal, flown: Decimal, elapsed: int, previous: date
) -> None:
    """REQ-048, ML.A.302(d)(1). However early or late the inspection was against
    the one before, the next is due 100.0 hours and 12 months after it."""
    done = Reading(previous + timedelta(days=elapsed), previous_hours + flown)
    hours, calendar = limits(
        MINIMUM_INSPECTION_PROGRAMME_INTERVAL,
        done,
        done,
        kind=TaskKind.MINIMUM_INSPECTION_PROGRAMME,
        tolerance=MINIMUM_INSPECTION_PROGRAMME_TOLERANCE,
    )
    assert hours.due == done.hours + Decimal("100")
    assert calendar.due == add_months(done.on, 12)
