"""Golden cases and properties for how long a former person's record is kept (REQ-206).

Read in the UK text in the Civil Aviation Authority Regulatory Library on
24 November 2026:

- CAO.A.045(e): the record of airworthiness review staff is retained "for
  a period of at least 2 years after the date at which the person
  concerned no longer works for the CAO".
- CAMO.A.220, Personnel Records: "retained until 3 years after the person
  has left the organisation".
- 145.A.55, Personnel Records: "retained for 3 years after the person has
  left the organisation".
- CAO.A.035(e) has a Part-CAO record the qualification of all personnel,
  and gives no period.

The person is the former airworthiness review staff member of
design-system/SampleData.md, People: left 30 June 2025. The Staff board
shows the record kept until 30 June 2027, 2 years after leaving.
"""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.personnel import Retention, record_kept_until

CAO, CAMO, P145 = "Part-CAO", "Part-CAMO", "Part-145"
LEFT = date(2025, 6, 30)


def test_a_former_review_staff_member_of_a_part_cao_is_kept_2_years() -> None:
    """REQ-206, CAO.A.045(e). Left 30 June 2025: 30 June 2027, as the Staff board shows."""
    kept = record_kept_until(LEFT, approvals={CAO}, review_staff=True)
    assert kept == Retention(date(2027, 6, 30), 2, "CAO.A.045(e)")


def test_part_cao_gives_no_period_for_other_staff() -> None:
    """REQ-206. CAO.A.035(e) gives none, so none is shown as the regulation's."""
    assert record_kept_until(LEFT, approvals={CAO}, review_staff=False) is None


@pytest.mark.parametrize(
    ("approvals", "source"),
    [
        ({CAMO}, "CAMO.A.220, Personnel Records"),
        ({P145}, "145.A.55, Personnel Records"),
        ({CAMO, P145}, "CAMO.A.220 and 145.A.55, Personnel Records"),
        ({CAO, P145}, "145.A.55, Personnel Records"),
        ({CAO, CAMO, P145}, "CAMO.A.220 and 145.A.55, Personnel Records"),
    ],
)
@pytest.mark.parametrize("review_staff", [True, False])
def test_a_part_camo_or_part_145_keeps_every_record_3_years(
    approvals: set[str], source: str, review_staff: bool
) -> None:
    """REQ-206. Left 30 June 2025: 30 June 2028. The longer period is the one shown."""
    kept = record_kept_until(LEFT, approvals=approvals, review_staff=review_staff)
    assert kept == Retention(date(2028, 6, 30), 3, source)


def test_no_approval_held_gives_no_period() -> None:
    """REQ-206."""
    assert record_kept_until(LEFT, approvals=set(), review_staff=True) is None


def test_a_person_who_left_on_29_february_is_kept_to_1_march() -> None:
    """REQ-206. Ours: a period that is a minimum is never cut a day short.

    29 February 2024 and 2 years has no such day in 2026; 28 February 2026
    would be a day less than 2 years, so the record is kept until 1 March.
    The same holds 3 years on: 2027 has no 29 February either. A person who
    left on 28 February, in a leap year or not, is kept until 28 February.
    """
    left = date(2024, 2, 29)
    assert record_kept_until(left, approvals={CAO}, review_staff=True) == Retention(
        date(2026, 3, 1), 2, "CAO.A.045(e)"
    )
    assert record_kept_until(left, approvals={P145}, review_staff=False) == Retention(
        date(2027, 3, 1), 3, "145.A.55, Personnel Records"
    )
    assert record_kept_until(date(2028, 2, 28), approvals={CAO}, review_staff=True) == Retention(
        date(2030, 2, 28), 2, "CAO.A.045(e)"
    )


DATES = st.dates(min_value=date(1950, 1, 1), max_value=date(2150, 12, 31))
APPROVALS = st.sets(st.sampled_from([CAO, CAMO, P145]))


@given(DATES, APPROVALS, st.booleans())
def test_the_record_is_kept_the_whole_period_and_no_other_day(
    left: date, approvals: set[str], review_staff: bool
) -> None:
    """The day is the same day of the same month, the stated number of years on."""
    kept = record_kept_until(left, approvals=approvals, review_staff=review_staff)
    if kept is None:
        assert not approvals & {CAMO, P145}
        assert not (review_staff and CAO in approvals)
        return
    assert kept.years == (3 if approvals & {CAMO, P145} else 2)
    assert kept.until.year == left.year + kept.years
    if (left.month, left.day) == (2, 29):
        assert (kept.until.month, kept.until.day) == (3, 1)
    else:
        assert (kept.until.month, kept.until.day) == (left.month, left.day)
    # Never fewer days than that many years of 365 days.
    assert (kept.until - left).days >= 365 * kept.years


@given(DATES, DATES, APPROVALS, st.booleans())
def test_leaving_later_never_ends_the_keeping_sooner(
    first: date, second: date, approvals: set[str], review_staff: bool
) -> None:
    earlier, later = sorted((first, second))
    one = record_kept_until(earlier, approvals=approvals, review_staff=review_staff)
    two = record_kept_until(later, approvals=approvals, review_staff=review_staff)
    assert (one is None) == (two is None)
    if one is not None and two is not None:
        assert one.until <= two.until


@given(DATES, APPROVALS)
def test_another_approval_never_shortens_the_period(left: date, approvals: set[str]) -> None:
    """Holding more never gives a former person's record less time."""
    for more in (CAO, CAMO, P145):
        for review_staff in (True, False):
            one = record_kept_until(left, approvals=approvals, review_staff=review_staff)
            two = record_kept_until(left, approvals=approvals | {more}, review_staff=review_staff)
            if one is not None:
                assert two is not None
                assert two.until >= one.until
