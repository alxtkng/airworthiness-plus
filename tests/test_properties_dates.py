"""Property-based tests: rules that must hold for every date, not only chosen ones."""

from datetime import date, timedelta

from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.dates import add_days, add_years, days_between
from airworthiness_rules.records import release_record_deadline
from airworthiness_rules.review import (
    ExtensionNotPermittedError,
    copy_to_authority_deadline,
    extension_window_opens,
    review_keeps_pattern,
    review_window_opens,
    valid_to_after_extension,
    valid_to_after_review,
)

DATES = st.dates(min_value=date(1950, 1, 1), max_value=date(2150, 12, 31))
SPANS = st.integers(min_value=-40_000, max_value=40_000)


@given(DATES, SPANS)
def test_adding_days_then_counting_gives_the_same_number(start: date, days: int) -> None:
    assert days_between(start, add_days(start, days)) == days


@given(DATES, DATES)
def test_day_count_reverses_sign_when_dates_are_swapped(a: date, b: date) -> None:
    assert days_between(a, b) == -days_between(b, a)


@given(DATES, DATES, DATES)
def test_day_counts_add_up(a: date, b: date, c: date) -> None:
    assert days_between(a, b) + days_between(b, c) == days_between(a, c)


@given(DATES, st.integers(min_value=1, max_value=50))
def test_anniversary_keeps_day_and_month_except_from_29_february(start: date, years: int) -> None:
    result = add_years(start, years)
    assert result.year == start.year + years
    assert result.month == start.month
    if (start.month, start.day) == (2, 29):
        assert result.day in (28, 29)
    else:
        assert result.day == start.day


@given(DATES, st.integers(min_value=0, max_value=90))
def test_any_review_inside_the_window_gives_the_same_expiry(valid_to: date, early: int) -> None:
    """ML.A.903(d): the pattern does not depend on which day in the window is used."""
    reviewed = valid_to - timedelta(days=early)
    assert review_keeps_pattern(reviewed, valid_to)
    assert valid_to_after_review(reviewed, valid_to) == add_years(valid_to, 1)


@given(DATES, st.integers(min_value=91, max_value=3_000))
def test_a_review_before_the_window_never_keeps_the_pattern(valid_to: date, early: int) -> None:
    reviewed = valid_to - timedelta(days=early)
    assert not review_keeps_pattern(reviewed, valid_to)
    assert valid_to_after_review(reviewed, valid_to) == add_years(reviewed, 1)


@given(DATES, DATES)
def test_a_new_certificate_never_expires_before_the_review(reviewed: date, valid_to: date) -> None:
    assert valid_to_after_review(reviewed, valid_to) > reviewed


@given(DATES)
def test_deadlines_are_exact_day_counts(start: date) -> None:
    assert days_between(start, copy_to_authority_deadline(start)) == 10
    assert days_between(start, release_record_deadline(start)) == 30


@given(DATES, DATES)
def test_the_review_window_shown_is_the_window_the_rule_uses(
    reviewed: date, valid_to: date
) -> None:
    """REQ-139. The day shown as the start of the window is where the rule begins."""
    inside = review_window_opens(valid_to) <= reviewed <= valid_to
    assert review_keeps_pattern(reviewed, valid_to) == inside


@given(DATES, DATES)
def test_the_extension_window_shown_is_the_window_the_rule_uses(
    extended: date, valid_to: date
) -> None:
    """REQ-139. An extension is accepted exactly from the day shown to the day of expiry."""
    inside = extension_window_opens(valid_to) <= extended <= valid_to
    try:
        valid_to_after_extension(extended, valid_to, 0)
    except ExtensionNotPermittedError:
        accepted = False
    else:
        accepted = True
    assert accepted == inside
