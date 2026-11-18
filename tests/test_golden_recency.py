"""Golden cases for the recency of airworthiness review staff (REQ-113).

AMC1 CAO.A.045(c), read in the UK text on 18 November 2026. The people are
those of design-system/SampleData.md. Today in the sample world is
18 November 2026.

SampleData.md says the other review staff member's recency lapses on
2 December 2026, with 4 months of continuing airworthiness work, but not
the date of their last review. The case below takes it to have been
2 December 2025, to be confirmed by Alex King.
"""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.dates import add_months
from airworthiness_rules.review import (
    recency_by_review_lasts_to,
    recency_lapses,
    review_staff_recent,
)

TODAY = date(2026, 11, 18)


def test_lucy_grant_is_recent_by_her_last_review() -> None:
    """REQ-113. Last review 11 November 2026, G-CDEF: counts to 11 November 2027."""
    last = date(2026, 11, 11)
    assert recency_by_review_lasts_to(last) == date(2027, 11, 11)
    assert review_staff_recent(TODAY, last_review=last, months_involved_in_two_years=0)
    assert review_staff_recent(date(2027, 11, 11), last_review=last, months_involved_in_two_years=0)
    assert not review_staff_recent(
        date(2027, 11, 12), last_review=last, months_involved_in_two_years=0
    )


def test_the_other_review_staff_member_lapses_on_2_december_2026() -> None:
    """REQ-113. 4 months of continuing airworthiness work is short of 6, so
    recency rests on the last review. Taken as 2 December 2025: it counts to
    2 December 2026, and from 3 December recency is lost unless the G-EJKL
    review is carried out."""
    last = date(2025, 12, 2)
    assert recency_lapses(last_review=last, months_involved_in_two_years=4) == date(2026, 12, 2)
    assert review_staff_recent(TODAY, last_review=last, months_involved_in_two_years=4)
    assert review_staff_recent(date(2026, 12, 2), last_review=last, months_involved_in_two_years=4)
    assert not review_staff_recent(
        date(2026, 12, 3), last_review=last, months_involved_in_two_years=4
    )
    # The G-EJKL review, done on 1 December 2026, keeps them current to 1 December 2027.
    assert recency_lapses(last_review=date(2026, 12, 1), months_involved_in_two_years=4) == date(
        2027, 12, 1
    )


@pytest.mark.parametrize(("months", "recent"), [(5, False), (6, True), (24, True)])
def test_six_months_of_involvement_is_enough_without_a_review(months: int, recent: bool) -> None:
    """REQ-113, AMC1 CAO.A.045(c)(1)."""
    assert (
        review_staff_recent(TODAY, last_review=None, months_involved_in_two_years=months) is recent
    )
    old = date(2024, 1, 1)
    assert (
        review_staff_recent(TODAY, last_review=old, months_involved_in_two_years=months) is recent
    )


def test_no_lapse_date_is_given_when_recency_does_not_rest_on_a_review() -> None:
    """REQ-113. Nothing is invented: with 6 months of involvement, or with no review."""
    assert recency_lapses(last_review=date(2026, 11, 11), months_involved_in_two_years=6) is None
    assert recency_lapses(last_review=None, months_involved_in_two_years=0) is None
    with pytest.raises(ValueError, match="below zero"):
        review_staff_recent(TODAY, last_review=None, months_involved_in_two_years=-1)


def test_a_review_on_29_february_counts_to_28_february() -> None:
    """REQ-113, REQ-047."""
    assert recency_by_review_lasts_to(date(2028, 2, 29)) == date(2029, 2, 28)


@given(
    st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 1, 1)),
    st.integers(min_value=0, max_value=800),
    st.integers(min_value=0, max_value=5),
)
def test_recency_by_review_ends_12_months_after_it(last: date, later: int, months: int) -> None:
    """REQ-113. With less than 6 months of involvement, staff are recent exactly
    up to and including the day 12 months after their last review."""
    today = date.fromordinal(last.toordinal() + later)
    recent = review_staff_recent(today, last_review=last, months_involved_in_two_years=months)
    assert recent == (today <= add_months(last, 12))
