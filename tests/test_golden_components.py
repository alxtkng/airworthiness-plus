"""Golden cases and properties for components and life limits (REQ-231 to REQ-236).

Worked by hand from design-system/SampleData.md, Components. Today in the
sample is 18 November 2026. ML.A.503 and ML.A.305(e) were read in the UK
text on 27 November 2026 (Decisions.md, Regulation Facts in Use). How the
hours of a component are counted is ours.

- G-CDEF engine: fitted at 5,951.5 airframe hours with 0.0; the airframe
  reads 7,731.5: 1,780.0 hours. Limit 2,000.0: 220.0 remain. At 0.6 hours
  a day, 366 days.
- G-ABCD vacuum pump: fitted at 6,230.6 with 0.0; airframe 6,412.6: 182.0
  hours. Limit 500.0: 318.0 remain. At 0.8 hours a day, 397 days.
- G-CDEF's own propeller: fitted at 6,319.5 with 16.5, removed at 7,715.0:
  1,412.0 hours. New or overhauled 2 November 2020, 72 months: 2 November
  2026, the day it was removed.
- G-DGHI engine, on condition: last reviewed at 9,800.0, every 100.0:
  review at 9,900.0. The airframe reads 9,874.3: 25.7 remain.
- G-ABCD battery date 28 February 2027: 102 days. G-BXYZ label inspection
  date 31 March 2027: 133 days.
- Six months from 18 November 2026 is 18 May 2027, 181 days.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules import components as rules
from airworthiness_rules.intervals import Interval, Unit, Utilisation
from airworthiness_rules.programme import Flag

TODAY = date(2026, 11, 18)
D = Decimal


def test_the_hours_of_a_component_are_those_when_fitted_and_what_the_airframe_has_flown() -> None:
    """REQ-231. The sample's four, by hand."""
    assert rules.hours_since(D("0.0"), D("5951.5"), D("7731.5")) == D("1780.0")
    assert rules.hours_since(D("0.0"), D("6230.6"), D("6412.6")) == D("182.0")
    assert rules.hours_since(D("16.5"), D("6319.5"), D("7715.0")) == D("1412.0")
    assert rules.hours_since(D("0.0"), D("7734.3"), D("9874.3")) == D("2140.0")
    assert rules.cycles_since(40, 1_000, 1_250) == 290
    # Fitted and not yet flown: what it had.
    assert rules.hours_since(D("16.5"), D("6319.5"), D("6319.5")) == D("16.5")
    with pytest.raises(ValueError, match="not fewer hours"):
        rules.hours_since(D("0.0"), D("6319.5"), D("6319.4"))
    with pytest.raises(ValueError, match="not fewer cycles"):
        rules.cycles_since(0, 10, 9)
    with pytest.raises(ValueError, match="below zero"):
        rules.hours_since(D("-0.1"), D("0"), D("0"))


def test_what_remains_of_a_life_in_hours() -> None:
    """REQ-232. G-CDEF's engine has 220.0 hours left, the vacuum pump 318.0."""
    (engine,) = rules.life_limits(Interval(hours=D("2000")), None, D("1780.0"), 0, TODAY)
    assert (engine.unit, engine.due, engine.remaining) == (Unit.HOURS, D("2000"), D("220.0"))
    (pump,) = rules.life_limits(Interval(hours=D("500")), None, D("182.0"), 0, TODAY)
    assert pump.remaining == D("318.0")
    # Reached exactly is not overdue; a tenth more is.
    (at,) = rules.life_limits(Interval(hours=D("500")), None, D("500.0"), 0, TODAY)
    assert (at.remaining, at.overdue) == (D("0.0"), False)
    (past,) = rules.life_limits(Interval(hours=D("500")), None, D("500.1"), 0, TODAY)
    assert (past.remaining, past.overdue) == (D("-0.1"), True)


def test_a_calendar_life_runs_from_new_or_overhaul() -> None:
    """REQ-232. The propeller: 2,000 hours or 72 months from 2 November 2020. On the
    day it was removed it had 588.0 hours and 0 days left; the day before, 1 day."""
    life = Interval(hours=D("2000"), months=72)
    hours, calendar = rules.life_limits(life, date(2020, 11, 2), D("1412.0"), 0, date(2026, 11, 2))
    assert (hours.due, hours.remaining) == (D("2000"), D("588.0"))
    assert (calendar.due, calendar.remaining) == (date(2026, 11, 2), 0)
    assert not calendar.overdue
    _, before = rules.life_limits(life, date(2020, 11, 2), D("1412.0"), 0, date(2026, 11, 1))
    assert before.remaining == 1
    _, after = rules.life_limits(life, date(2020, 11, 2), D("1412.0"), 0, date(2026, 11, 3))
    assert (after.remaining, after.overdue) == (-1, True)
    # 29 February 2024 and 12 months: the last day of February 2025.
    (leap,) = rules.life_limits(Interval(months=12), date(2024, 2, 29), D("0"), 0, TODAY)
    assert leap.due == date(2025, 2, 28)
    with pytest.raises(ValueError, match="needs the day it runs from"):
        rules.life_limits(life, None, D("0"), 0, TODAY)
    with pytest.raises(ValueError, match="in months"):
        rules.life_limits(Interval(days=30), TODAY, D("0"), 0, TODAY)


def test_a_date_on_the_component() -> None:
    """REQ-232. Battery date 28 February 2027 is 102 days from 18 November 2026; the
    label inspection date 31 March 2027 is 133."""
    battery = rules.dated_limit(date(2027, 2, 28), TODAY)
    assert (battery.unit, battery.due, battery.remaining) == (Unit.CALENDAR, date(2027, 2, 28), 102)
    assert rules.dated_limit(date(2027, 3, 31), TODAY).remaining == 133
    assert rules.dated_limit(TODAY, TODAY).overdue is False
    assert rules.dated_limit(date(2026, 11, 17), TODAY).overdue is True


def test_a_component_on_condition_is_reviewed_at_its_interval() -> None:
    """REQ-233. G-DGHI's engine: reviewed at 9,800.0, every 100.0, so at 9,900.0;
    at 9,874.3 airframe hours 25.7 remain."""
    review = rules.review_limit(D("9800.0"), D("100"), D("9874.3"))
    assert (review.unit, review.due, review.remaining) == (Unit.HOURS, D("9900.0"), D("25.7"))
    assert rules.review_limit(D("9800.0"), D("100"), D("9900.0")).remaining == D("0.0")
    assert rules.review_limit(D("9800.0"), D("100"), D("9900.1")).overdue
    with pytest.raises(ValueError, match="above zero"):
        rules.review_limit(D("9800.0"), D("0"), D("9874.3"))
    with pytest.raises(ValueError, match="last review"):
        rules.review_limit(D("9800.0"), D("100"), D("9799.9"))


def test_due_in_six_months_at_its_edges() -> None:
    """REQ-234. Six months from 18 November 2026 is 18 May 2027, 181 days. The battery
    (102 days) is within them. G-CDEF's engine, 220.0 hours at 0.6 a day, is 366 days
    and is not. A limit in hours with no planning utilisation cannot be placed
    outside them, so it is counted."""
    club = Utilisation(D("0.6"))
    assert rules.due_within_months((rules.dated_limit(date(2027, 2, 28), TODAY),), TODAY, None)
    assert rules.due_within_months((rules.dated_limit(date(2027, 5, 18), TODAY),), TODAY, None)
    assert not rules.due_within_months((rules.dated_limit(date(2027, 5, 19), TODAY),), TODAY, None)
    engine = rules.life_limits(Interval(hours=D("2000")), None, D("1780.0"), 0, TODAY)
    assert not rules.due_within_months(engine, TODAY, club)
    assert rules.due_within_months(engine, TODAY, None)
    # 108.6 hours at 0.6 a day is 181 days; 109.2 is 182.
    for hours, within in ((D("1891.4"), True), (D("1890.8"), False)):
        found = rules.life_limits(Interval(hours=D("2000")), None, hours, 0, TODAY)
        assert rules.due_within_months(found, TODAY, club) is within
    passed = rules.life_limits(Interval(hours=D("2000")), None, D("2000.1"), 0, TODAY)
    assert rules.due_within_months(passed, TODAY, club)
    assert not rules.due_within_months((), TODAY, None)


def test_a_component_due_back_is_marked_from_the_lead_time() -> None:
    """REQ-236. The propeller is due back on 25 November 2026: 7 days from 18 November,
    inside a lead time of 30 days. Due on the day and Overdue after it."""
    back = date(2026, 11, 25)
    assert rules.due_back_flag(TODAY, back, 30) is Flag.DUE_SOON
    assert rules.due_back_flag(TODAY, back, 7) is Flag.DUE_SOON
    assert rules.due_back_flag(TODAY, back, 6) is Flag.NONE
    assert rules.due_back_flag(back, back, 30) is Flag.DUE
    assert rules.due_back_flag(date(2026, 11, 26), back, 30) is Flag.OVERDUE


TENTHS = st.integers(min_value=0, max_value=5_000_000).map(lambda n: Decimal(n) / 10)
LIMITS = st.integers(min_value=1, max_value=999_999).map(lambda n: Decimal(n) / 10)
DATES = st.dates(min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))


@given(TENTHS, TENTHS, TENTHS, TENTHS)
def test_hours_flown_add_up(at: Decimal, airframe: Decimal, flown: Decimal, more: Decimal) -> None:
    """Flying on adds exactly what was flown, however the flying is split."""
    first = rules.hours_since(at, airframe, airframe + flown)
    assert first == at + flown
    assert rules.hours_since(at, airframe, airframe + flown + more) == first + more
    assert rules.hours_since(first, airframe + flown, airframe + flown + more) == first + more


@given(TENTHS, LIMITS, DATES)
def test_what_remains_and_what_is_used_make_the_limit(
    used: Decimal, limit: Decimal, day: date
) -> None:
    (found,) = rules.life_limits(Interval(hours=limit), None, used, 0, day)
    assert found.remaining + used == limit
    assert found.overdue == (used > limit)


@given(DATES, st.integers(min_value=1, max_value=600), st.integers(min_value=0, max_value=9_000))
def test_a_calendar_life_loses_a_day_each_day(start: date, months: int, elapsed: int) -> None:
    today = start + timedelta(days=elapsed)
    (first,) = rules.life_limits(Interval(months=months), start, D("0"), 0, today)
    (second,) = rules.life_limits(
        Interval(months=months), start, D("0"), 0, today + timedelta(days=1)
    )
    assert first.due == second.due
    assert second.remaining == first.remaining - 1


@given(TENTHS, LIMITS, TENTHS)
def test_a_review_is_due_one_interval_after_the_last(
    reviewed: Decimal, every: Decimal, flown: Decimal
) -> None:
    found = rules.review_limit(reviewed, every, reviewed + flown)
    assert found.due == reviewed + every
    assert found.remaining == every - flown


@given(DATES, st.integers(min_value=-400, max_value=400), st.integers(min_value=0, max_value=365))
def test_due_back_is_never_unmarked_once_the_day_is_reached(
    back: date, offset: int, lead: int
) -> None:
    today = back + timedelta(days=offset)
    flag = rules.due_back_flag(today, back, lead)
    if offset > 0:
        assert flag is Flag.OVERDUE
    elif offset == 0:
        assert flag is Flag.DUE
    else:
        assert flag is (Flag.DUE_SOON if -offset <= lead else Flag.NONE)
