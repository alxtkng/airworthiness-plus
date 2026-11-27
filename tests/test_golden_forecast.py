"""Golden cases and properties for the forecast date (REQ-291).

Ours, not the regulation's: the day a limit is expected to be reached is
today and the whole days to it. Worked by hand for 18 November 2026, the
day of design-system/SampleData.md.
"""

from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules import forecast as rules

TODAY = date(2026, 11, 18)


def test_the_forecast_date_is_today_and_the_days_to_the_limit() -> None:
    """REQ-291. Golden: 15 days from 18 November 2026 is 3 December 2026; 82 days,
    8 February 2027; 366 days, 19 November 2027. A limit reached or passed is
    forecast for today. What cannot be placed has no forecast."""
    assert rules.forecast_date(TODAY, 15) == date(2026, 12, 3)
    assert rules.forecast_date(TODAY, 82) == date(2027, 2, 8)
    assert rules.forecast_date(TODAY, 366) == date(2027, 11, 19)
    assert rules.forecast_date(TODAY, 397) == date(2027, 12, 20)
    assert rules.forecast_date(TODAY, 0) == TODAY
    assert rules.forecast_date(TODAY, -3) == TODAY
    assert rules.forecast_date(TODAY, None) is None
    # The window of the Aircraft board, Next 120 Days: 18 March 2027 is the last day in it.
    assert rules.within_window(TODAY, date(2027, 3, 18))
    assert not rules.within_window(TODAY, date(2027, 3, 19))
    assert rules.within_window(TODAY, TODAY)
    assert not rules.within_window(TODAY, None)
    with pytest.raises(ValueError, match="below zero"):
        rules.within_window(TODAY, TODAY, -1)


DATES = st.dates(min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))


@given(DATES, st.integers(min_value=-2_000, max_value=20_000))
def test_a_forecast_is_never_before_today_and_never_later_than_the_days_given(
    today: date, days: int
) -> None:
    found = rules.forecast_date(today, days)
    assert found is not None
    assert found >= today
    assert found == today + timedelta(days=max(days, 0))
    assert rules.within_window(today, found) == (days <= rules.WINDOW_DAYS)
