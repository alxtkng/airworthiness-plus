"""Golden cases: fixed worked examples from design-system/SampleData.md.

Each expected value was worked by hand and is cited to its rule. Today in
the sample world is 18 November 2026.
"""

from datetime import UTC, date, datetime

import pytest

from airworthiness_rules.dates import add_years, days_between, uk_today
from airworthiness_rules.records import release_record_deadline
from airworthiness_rules.review import (
    ExtensionNotPermittedError,
    copy_to_authority_deadline,
    days_to_expiry,
    extension_window_opens,
    review_keeps_pattern,
    review_window_opens,
    valid_to_after_extension,
    valid_to_after_review,
)

TODAY = date(2026, 11, 18)


def test_g_ejkl_review_certificate_is_18_days_away() -> None:
    """REQ-100, REQ-046. 18 to 30 November is 12 days, plus 6 in December: 18."""
    assert days_to_expiry(TODAY, date(2026, 12, 6)) == 18


def test_g_cdef_early_review_keeps_the_pattern() -> None:
    """REQ-102, ML.A.903(d). Reviewed 11 November 2026, 21 days before the
    previous expiry of 2 December 2026, so valid to 2 December 2027."""
    assert days_between(date(2026, 11, 11), date(2026, 12, 2)) == 21
    assert valid_to_after_review(date(2026, 11, 11), date(2026, 12, 2)) == date(2027, 12, 2)


def test_g_cdef_copy_to_the_authority_is_due_21_november() -> None:
    """REQ-111, ML.A.903(f). Issued 11 November 2026 plus 10 days: 21 November 2026."""
    assert copy_to_authority_deadline(date(2026, 11, 11)) == date(2026, 11, 21)


def test_g_abcd_release_to_service_must_be_recorded_by_21_november() -> None:
    """REQ-051, ML.A.305(a). Tyre replaced 22 October 2026. 9 days remain in
    October, plus 21 in November: 30 days, 21 November 2026."""
    assert release_record_deadline(date(2026, 10, 22)) == date(2026, 11, 21)


@pytest.mark.parametrize(
    ("reviewed", "keeps"),
    [
        (date(2026, 9, 2), False),  # 91 days before 2 December 2026
        (date(2026, 9, 3), True),  # 90 days before
        (date(2026, 12, 2), True),  # on the expiry date
        (date(2026, 12, 3), False),  # the day after expiry
    ],
)
def test_early_review_window_boundaries(reviewed: date, keeps: bool) -> None:
    """REQ-102, ML.A.903(d). 2 December back to 2 September is 30 + 31 + 30 = 91
    days, so 3 September is exactly 90."""
    assert review_keeps_pattern(reviewed, date(2026, 12, 2)) is keeps


def test_review_outside_the_window_runs_1_year_from_the_review() -> None:
    """REQ-101, ML.A.901(a). REQ-103 (anniversary or the day before) is To Be Checked."""
    assert valid_to_after_review(date(2026, 9, 2), date(2026, 12, 2)) == date(2027, 9, 2)
    assert valid_to_after_review(date(2026, 11, 18), None) == date(2027, 11, 18)


def test_extension_keeps_the_pattern_within_30_days() -> None:
    """REQ-106, ML.A.901(d). 6 November to 6 December 2026 is 30 days."""
    assert valid_to_after_extension(date(2026, 11, 6), date(2026, 12, 6), 0) == date(2027, 12, 6)
    assert valid_to_after_extension(date(2026, 12, 6), date(2026, 12, 6), 1) == date(2027, 12, 6)


def test_g_ejkl_windows_open_on_7_september_and_6_november() -> None:
    """REQ-102, REQ-106, REQ-139. The certificate ends 6 December 2026.

    By hand, 90 days back: 6 days of December reach 30 November, 30 more
    reach 31 October, 31 more reach 30 September, and the remaining 23 reach
    7 September 2026 (6 + 30 + 31 + 23 = 90). 30 days back: 6 days of
    December reach 30 November, and 24 more reach 6 November 2026.
    """
    valid_to = date(2026, 12, 6)
    assert review_window_opens(valid_to) == date(2026, 9, 7)
    assert extension_window_opens(valid_to) == date(2026, 11, 6)
    # The first day of each window is in it, and the day before is not.
    assert review_keeps_pattern(date(2026, 9, 7), valid_to)
    assert not review_keeps_pattern(date(2026, 9, 6), valid_to)
    assert valid_to_after_extension(date(2026, 11, 6), valid_to, 0) == date(2027, 12, 6)
    with pytest.raises(ExtensionNotPermittedError):
        valid_to_after_extension(date(2026, 11, 5), valid_to, 0)


def test_extension_refused_31_days_early_after_expiry_and_a_third_time() -> None:
    """REQ-104, REQ-106, ML.A.901(c) and (d)."""
    with pytest.raises(ExtensionNotPermittedError):
        valid_to_after_extension(date(2026, 11, 5), date(2026, 12, 6), 0)
    with pytest.raises(ExtensionNotPermittedError):
        valid_to_after_extension(date(2026, 12, 7), date(2026, 12, 6), 0)
    with pytest.raises(ExtensionNotPermittedError):
        valid_to_after_extension(date(2026, 11, 20), date(2026, 12, 6), 2)


def test_leap_day_anniversary_falls_on_28_february() -> None:
    """REQ-047. 29 February 2028 plus 1 year is 28 February 2029; plus 4 is 29 February 2032."""
    assert add_years(date(2028, 2, 29), 1) == date(2029, 2, 28)
    assert add_years(date(2028, 2, 29), 4) == date(2032, 2, 29)
    assert valid_to_after_review(date(2028, 2, 1), date(2028, 2, 29)) == date(2029, 2, 28)


def test_day_counts_across_month_ends_leap_years_and_clock_changes() -> None:
    """REQ-046. Counts are of dates, so clock changes cannot alter them."""
    assert days_between(date(2026, 1, 31), date(2026, 3, 1)) == 29
    assert days_between(date(2028, 1, 31), date(2028, 3, 1)) == 30  # leap year
    assert days_between(date(2026, 3, 28), date(2026, 3, 30)) == 2  # clocks forward 29 March
    assert days_between(date(2026, 10, 24), date(2026, 10, 26)) == 2  # clocks back 25 October
    assert days_between(date(2026, 12, 31), date(2027, 1, 1)) == 1


def test_uk_today_follows_british_summer_time() -> None:
    """REQ-137. 23:30 UTC is 00:30 the next day in the UK during British Summer Time."""
    assert uk_today(datetime(2026, 6, 30, 23, 30, tzinfo=UTC)) == date(2026, 7, 1)
    assert uk_today(datetime(2026, 12, 31, 23, 30, tzinfo=UTC)) == date(2026, 12, 31)
    # Clocks go back at 01:00 UTC on 25 October 2026.
    assert uk_today(datetime(2026, 10, 24, 23, 30, tzinfo=UTC)) == date(2026, 10, 25)
    assert uk_today(datetime(2026, 10, 25, 23, 30, tzinfo=UTC)) == date(2026, 10, 25)


def test_uk_today_refuses_a_time_without_a_zone() -> None:
    """REQ-137."""
    with pytest.raises(ValueError, match="time zone"):
        uk_today(datetime(2026, 11, 18, 12, 0))  # noqa: DTZ001
