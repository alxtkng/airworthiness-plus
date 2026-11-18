"""The parallel run (REQ-173). Each case is worked by hand.

The 6 months pass on the same day of the month, 6 months after the start,
or on the last day of that month if it is shorter. The month arithmetic is
``airworthiness_rules.dates.add_months``, verified independently in
``assurance/independent-verification/review-and-dates.md``.
"""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.acceptance import parallel_run_passed, parallel_run_passes_on


@pytest.mark.parametrize(
    ("started", "passes"),
    [
        # May, June, July, August, September, October: six months to 18 November.
        (date(2026, 5, 18), date(2026, 11, 18)),
        # Across the end of a year.
        (date(2026, 9, 1), date(2027, 3, 1)),
        # 31 August: February has no 31st, so the last day of February.
        (date(2026, 8, 31), date(2027, 2, 28)),
        # The same in a leap year.
        (date(2027, 8, 31), date(2028, 2, 29)),
        # 31 March: September has 30 days.
        (date(2026, 3, 31), date(2026, 9, 30)),
    ],
)
def test_the_day_six_months_pass(started: date, passes: date) -> None:
    assert parallel_run_passes_on(started) == passes


def test_the_run_has_passed_on_that_day_and_not_the_day_before() -> None:
    started = date(2026, 5, 18)
    assert not parallel_run_passed(started, date(2026, 11, 17))
    assert parallel_run_passed(started, date(2026, 11, 18))
    assert parallel_run_passed(started, date(2027, 1, 1))
    assert not parallel_run_passed(started, started)


@given(st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 1, 1)))
def test_the_run_lasts_between_181_and_184_days(started: date) -> None:
    """Six consecutive months hold between 181 and 184 days, less up to 3 at a month end."""
    days = (parallel_run_passes_on(started) - started).days
    assert 181 <= days <= 184
