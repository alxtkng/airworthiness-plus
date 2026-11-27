"""Golden cases for deferred defects and repeat defects (REQ-222, REQ-223, REQ-226).

Worked by hand from design-system/SampleData.md, Defects, and the Defects
and Repeat Defects boards. Today in the sample is 18 November 2026.

ML.A.403(c): a deferred defect is rectified within the limits specified in
the maintenance data. The regulation gives no number of days; the 30 days
are the organisation's own default (REQ-214), counted from the day of the
decision. The repeat rule is the board's and is ours: 3 of the same defect
on one type in 12 months.
"""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules import defects
from airworthiness_rules.programme import Flag

TODAY = date(2026, 11, 18)


@pytest.mark.parametrize(
    ("registration", "decided_on", "limit", "days_left"),
    [
        # G-ABCD, Left Landing Light Inoperative: 3 November has 27 days left of its
        # 30, and 3 more reach 3 December. From 18 November: 12 and 3, 15 days.
        ("G-ABCD", date(2026, 11, 3), date(2026, 12, 3), 15),
        # G-BXYZ, Cabin Entry Step Loose: 28 October, 3 days to 31 October, 27 more
        # to 27 November. From 18 November: 9 days.
        ("G-BXYZ", date(2026, 10, 28), date(2026, 11, 27), 9),
        # G-EJKL, Right Headset Socket Crackle: 12 November, 18 days to 30 November,
        # 12 more to 12 December. From 18 November: 12 and 12, 24 days.
        ("G-EJKL", date(2026, 11, 12), date(2026, 12, 12), 24),
    ],
)
def test_the_limits_of_the_sample(
    registration: str, decided_on: date, limit: date, days_left: int
) -> None:
    """REQ-222. The Defects board: each limit is 30 days after the decision."""
    assert defects.deferral_limit(decided_on, 30, None) == limit, registration
    assert (limit - TODAY).days == days_left
    # All three are inside the lead time of 30 days, so each is Due Soon (REQ-223).
    assert defects.deferral_flag(TODAY, limit, 30) is Flag.DUE_SOON


def test_a_limit_in_the_maintenance_data_applies_when_it_is_earlier() -> None:
    """REQ-222, ML.A.403(c). 3 November and 30 days is 3 December; the data says 20 November."""
    decided = date(2026, 11, 3)
    assert defects.deferral_limit(decided, 30, date(2026, 11, 20)) == date(2026, 11, 20)
    # A later limit in the data does not lengthen the organisation's own.
    assert defects.deferral_limit(decided, 30, date(2026, 12, 20)) == date(2026, 12, 3)
    # The same day is the same day.
    assert defects.deferral_limit(decided, 30, date(2026, 12, 3)) == date(2026, 12, 3)


def test_the_minimum_equipment_list_gives_its_own_limit() -> None:
    """REQ-222, ML.A.403(b)(2). No default of the organisation's: the list's limit is the limit."""
    assert defects.deferral_limit(date(2026, 11, 3), None, date(2026, 11, 13)) == date(2026, 11, 13)
    with pytest.raises(ValueError, match="has a limit"):
        defects.deferral_limit(date(2026, 11, 3), None, None)


def test_what_cannot_be_a_limit_is_refused() -> None:
    """REQ-222. A default from 1 to 365 days; no limit before the decision."""
    decided = date(2026, 11, 3)
    for days in (0, -1, 366):
        with pytest.raises(ValueError, match="from 1 to 365"):
            defects.deferral_limit(decided, days, None)
    assert defects.deferral_limit(decided, 1, None) == date(2026, 11, 4)
    assert defects.deferral_limit(decided, 365, None) == date(2027, 11, 3)
    with pytest.raises(ValueError, match="not before"):
        defects.deferral_limit(decided, 30, date(2026, 11, 2))
    assert defects.deferral_limit(decided, 30, decided) == decided


@pytest.mark.parametrize(
    ("today", "flag"),
    [
        (date(2026, 10, 27), Flag.NONE),  # 31 days left
        (date(2026, 10, 28), Flag.DUE_SOON),  # 30 days left: the lead time itself
        (date(2026, 11, 26), Flag.DUE_SOON),  # 1 day left
        (date(2026, 11, 27), Flag.DUE),  # the last day
        (date(2026, 11, 28), Flag.OVERDUE),  # 1 day past
    ],
)
def test_the_flag_at_each_edge(today: date, flag: Flag) -> None:
    """REQ-223. G-BXYZ's limit of 27 November 2026 with a lead time of 30 days."""
    assert defects.deferral_flag(today, date(2026, 11, 27), 30) is flag


def test_a_lead_time_of_nothing_shows_only_the_last_day_and_after() -> None:
    """REQ-223. With a lead time of 0 days nothing is Due Soon."""
    limit = date(2026, 11, 27)
    assert defects.deferral_flag(date(2026, 11, 26), limit, 0) is Flag.NONE
    assert defects.deferral_flag(limit, limit, 0) is Flag.DUE


def test_the_12_months_that_end_on_18_november_2026() -> None:
    """REQ-226. From 19 November 2025 to 18 November 2026, both counted."""
    assert defects.counted_from(TODAY) == date(2025, 11, 19)
    assert not defects.counted(date(2025, 11, 18), TODAY)
    assert defects.counted(date(2025, 11, 19), TODAY)
    assert defects.counted(TODAY, TODAY)
    assert not defects.counted(date(2026, 11, 19), TODAY)
    # G-DGHI's trim cable wear of 9 December 2025 is counted (the Repeat Defects board).
    assert defects.counted(date(2025, 12, 9), TODAY)
    # A year that ends on 29 February starts on 1 March of the year before.
    assert defects.counted_from(date(2028, 2, 29)) == date(2027, 3, 1)


@pytest.mark.parametrize(
    ("count", "state"),
    [(0, "No Action"), (1, "No Action"), (2, "Watching"), (3, "Repeat"), (4, "Repeat")],
)
def test_what_a_count_is(count: int, state: str) -> None:
    """REQ-226. The Repeat Defects board: 3 is a Repeat, 2 is Watching, 1 is No Action."""
    assert defects.repeat_state(count) == state


DATES = st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 12, 31))


@given(decided=DATES, days=st.integers(1, 365), later=st.integers(0, 800))
def test_a_limit_is_never_after_either_of_its_two_limits(
    decided: date, days: int, later: int
) -> None:
    """REQ-222. Property: the limit is the earlier of the two, and never before the decision."""
    own = defects.deferral_limit(decided, days, None)
    assert (own - decided).days == days
    data = date.fromordinal(decided.toordinal() + later)
    limit = defects.deferral_limit(decided, days, data)
    assert decided <= limit <= own and limit <= data
    assert limit in (own, data)


@given(limit=DATES, today=DATES, lead=st.integers(0, 365))
def test_a_flag_never_improves_as_days_pass(limit: date, today: date, lead: int) -> None:
    """REQ-223. Property: a day later, the flag is the same or worse; past the limit it is red."""
    order = [Flag.NONE, Flag.DUE_SOON, Flag.DUE, Flag.OVERDUE]
    now = defects.deferral_flag(today, limit, lead)
    tomorrow = defects.deferral_flag(date.fromordinal(today.toordinal() + 1), limit, lead)
    assert order.index(tomorrow) >= order.index(now)
    assert (now is Flag.OVERDUE) == (today > limit)


@given(today=DATES, back=st.integers(-5, 800))
def test_what_is_counted_is_within_a_year_and_never_in_the_future(today: date, back: int) -> None:
    """REQ-226. Property: a counted defect was found at most 366 days ago and not after today."""
    found = date.fromordinal(today.toordinal() - back)
    if defects.counted(found, today):
        assert 0 <= back <= 365
    if 0 <= back <= 364:
        assert defects.counted(found, today)


@given(count=st.integers(0, 1000))
def test_more_of_a_defect_is_never_a_lesser_state(count: int) -> None:
    """REQ-226. Property: one more of the same defect never lowers the state."""
    order = ["No Action", "Watching", "Repeat"]
    assert order.index(defects.repeat_state(count + 1)) >= order.index(defects.repeat_state(count))
