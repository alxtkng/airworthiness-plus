"""Golden cases for hours and cycles entries (REQ-024, REQ-025, REQ-028).

G-ABCD in design-system/SampleData.md: 6,375.0 airframe hours on
2 October 2026, when the 50-Hour Check was done, and 6,412.6 on
18 November 2026, today in the sample world. Cycles are not in the sample
data; 4,180 and 4,236 are used here.
"""

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.intervals import Reading
from airworthiness_rules.utilisation import (
    EntryRefusedError,
    Verdict,
    check_entry,
    current_total,
)

D = Decimal
TODAY = date(2026, 11, 18)
OCTOBER = Reading(date(2026, 10, 2), D("6375.0"), 4180)
NOVEMBER = Reading(date(2026, 11, 18), D("6412.6"), 4236)


def check(new: Reading, earlier: Reading | None = OCTOBER, later: Reading | None = None) -> Verdict:
    others = [entry for entry in (earlier, later) if entry is not None]
    return check_entry(new, others=others, today=TODAY)


def test_g_abcd_todays_entry_is_accepted() -> None:
    """REQ-024. 37.6 hours and 56 cycles gained over 47 days, counted as 48:
    the bounds are 480.0 hours and 4,800 cycles before confirmation."""
    assert check(NOVEMBER) is Verdict.ACCEPTED
    assert current_total([OCTOBER, NOVEMBER]) == NOVEMBER


def test_the_first_entry_for_a_counter_is_accepted() -> None:
    """REQ-024. There is nothing to compare it with; it is checked on import (hazard H-008)."""
    assert check(OCTOBER, earlier=None) is Verdict.ACCEPTED


@pytest.mark.parametrize(("hours", "cycles"), [(D("6374.9"), 4180), (D("6375.0"), 4179)])
def test_a_total_below_the_previous_entry_is_refused(hours: Decimal, cycles: int) -> None:
    """REQ-025. Below 6,375.0 hours or 4,180 cycles."""
    with pytest.raises(EntryRefusedError, match="Lower than the previous entry"):
        check(Reading(TODAY, hours, cycles))


def test_g_abcd_a_slip_of_ten_hours_downwards_is_refused() -> None:
    """REQ-025, hazard H-011. 6,412.6 already entered today; 6,402.6 typed after it."""
    with pytest.raises(EntryRefusedError, match="Lower than the previous entry"):
        check(Reading(TODAY, D("6402.6"), 4236), earlier=NOVEMBER)


def test_an_unchanged_total_is_accepted() -> None:
    """REQ-025. Not lower: an aircraft that has not flown."""
    assert check(Reading(TODAY, D("6375.0"), 4180)) is Verdict.ACCEPTED


def test_a_decimal_slip_is_refused() -> None:
    """REQ-025, hazard H-011. 6,412.6 typed as 64,126.0 on 18 November 2026:
    57,751.0 hours gained in 48 days, against 1,152.0 hours in 48 days."""
    with pytest.raises(EntryRefusedError, match="More hours than there are"):
        check(Reading(TODAY, D("64126.0"), 4236))


@pytest.mark.parametrize(
    ("on", "hours", "expected"),
    [
        # The same day as the previous entry counts as 1 day.
        (date(2026, 10, 2), D("6385.0"), Verdict.ACCEPTED),  # 10.0 gained
        (date(2026, 10, 2), D("6385.1"), Verdict.NEEDS_CONFIRMATION),  # 10.1 gained
        (date(2026, 10, 2), D("6399.0"), Verdict.NEEDS_CONFIRMATION),  # 24.0 gained
        # The next day counts as 2 days: 20.0 before confirmation, 48.0 at most.
        (date(2026, 10, 3), D("6395.0"), Verdict.ACCEPTED),
        (date(2026, 10, 3), D("6395.1"), Verdict.NEEDS_CONFIRMATION),
        (date(2026, 10, 3), D("6423.0"), Verdict.NEEDS_CONFIRMATION),
    ],
)
def test_an_unusual_gain_in_hours_needs_confirmation(
    on: date, hours: Decimal, expected: Verdict
) -> None:
    """REQ-025. More than 10.0 hours for each day needs confirmation."""
    assert check(Reading(on, hours, 4180)) is expected


@pytest.mark.parametrize(
    ("on", "hours"),
    [(date(2026, 10, 2), D("6399.1")), (date(2026, 10, 3), D("6423.1"))],
)
def test_more_than_24_hours_a_day_is_refused(on: date, hours: Decimal) -> None:
    """REQ-025. 24.1 gained in 1 day; 48.1 gained in 2."""
    with pytest.raises(EntryRefusedError, match="More hours than there are"):
        check(Reading(on, hours, 4180))


def test_an_unusual_gain_in_cycles_needs_confirmation() -> None:
    """REQ-025. More than 100 cycles for each day: 100 in 1 day passes, 101 does not."""
    same_day = date(2026, 10, 2)
    assert check(Reading(same_day, D("6380.0"), 4280)) is Verdict.ACCEPTED
    assert check(Reading(same_day, D("6380.0"), 4281)) is Verdict.NEEDS_CONFIRMATION


def test_a_late_entry_must_fit_between_the_entries_around_it() -> None:
    """REQ-025. A flight on 10 November 2026 entered after today's total."""
    late = date(2026, 11, 10)
    assert check(Reading(late, D("6400.0"), 4220), later=NOVEMBER) is Verdict.ACCEPTED
    assert check(Reading(late, D("6412.6"), 4236), later=NOVEMBER) is Verdict.ACCEPTED
    with pytest.raises(EntryRefusedError, match="Higher than a later entry"):
        check(Reading(late, D("6412.7"), 4220), later=NOVEMBER)
    with pytest.raises(EntryRefusedError, match="Higher than a later entry"):
        check(Reading(late, D("6400.0"), 4237), later=NOVEMBER)


def test_a_run_of_same_day_entries_cannot_add_up_past_the_limits() -> None:
    """REQ-025. Found by the independent recompute. Each step is 10.0 hours
    from the one before, which alone would pass; measured from 6,375.0 the
    third is 20.0 in 1 day, which needs confirmation, and 6,400.0 would be
    25.0 in 1 day, which is refused."""
    same_day = date(2026, 10, 2)
    second = Reading(same_day, D("6385.0"), 4180)
    third = Reading(same_day, D("6395.0"), 4180)
    assert check_entry(second, others=[OCTOBER], today=TODAY) is Verdict.ACCEPTED
    assert check_entry(third, others=[OCTOBER, second], today=TODAY) is Verdict.NEEDS_CONFIRMATION
    with pytest.raises(EntryRefusedError, match="More hours than there are"):
        check_entry(
            Reading(same_day, D("6400.0"), 4180), others=[OCTOBER, second, third], today=TODAY
        )


def test_steps_on_following_days_cannot_add_up_past_the_limits() -> None:
    """REQ-025. Found by the independent recompute. 48.0 hours to 3 October
    passes with confirmation; another 48.0 to 4 October makes 96.0 in 3 days
    counted, against 72.0."""
    third_of_october = Reading(date(2026, 10, 3), D("6423.0"), 4180)
    with pytest.raises(EntryRefusedError, match="More hours than there are"):
        check_entry(
            Reading(date(2026, 10, 4), D("6471.0"), 4180),
            others=[OCTOBER, third_of_october],
            today=TODAY,
        )


def test_a_late_entry_is_measured_against_the_entries_after_it_too() -> None:
    """REQ-025. Found by the independent recompute. 6,375.0 entered late for
    17 November leaves 37.6 hours to the entry of 18 November: 2 days counted,
    20.0 before confirmation, 48.0 at most. 6,392.6 leaves exactly 20.0;
    6,364.5, measured against 18 November alone, would leave 48.1."""
    late = date(2026, 11, 17)
    assert (
        check_entry(Reading(late, D("6375.0"), 4180), others=[OCTOBER, NOVEMBER], today=TODAY)
        is Verdict.NEEDS_CONFIRMATION
    )
    assert (
        check_entry(Reading(late, D("6392.6"), 4230), others=[OCTOBER, NOVEMBER], today=TODAY)
        is Verdict.ACCEPTED
    )
    with pytest.raises(EntryRefusedError, match="More hours than there are"):
        check_entry(Reading(late, D("6364.5"), 4180), others=[NOVEMBER], today=TODAY)


def test_two_entries_on_one_date_are_both_respected() -> None:
    """REQ-025. Found by the independent recompute. With 6,411.0 and 6,412.6
    both entered for 18 November, a total below either is refused."""
    morning = Reading(TODAY, D("6411.0"), 4234)
    with pytest.raises(EntryRefusedError, match="Lower than the previous entry"):
        check_entry(
            Reading(TODAY, D("6411.5"), 4235), others=[OCTOBER, morning, NOVEMBER], today=TODAY
        )


def test_an_entry_cannot_be_dated_after_today() -> None:
    """REQ-025."""
    with pytest.raises(EntryRefusedError, match="after today"):
        check(Reading(date(2026, 11, 19), D("6413.0"), 4237))


@pytest.mark.parametrize("hours", [D("6412.65"), D("6412.649"), D("-0.1")])
def test_hours_are_to_one_decimal_place_and_not_below_zero(hours: Decimal) -> None:
    """REQ-028."""
    with pytest.raises(EntryRefusedError, match=r"one decimal place|below zero"):
        check(Reading(TODAY, hours, 4236), earlier=None)


def test_hours_written_with_trailing_zeros_are_accepted() -> None:
    """REQ-028. 6,412.60 is 6,412.6."""
    assert check(Reading(TODAY, D("6412.60"), 4236)) is Verdict.ACCEPTED
    assert check(Reading(TODAY, D("6413"), 4236)) is Verdict.ACCEPTED


def test_the_current_total_is_the_latest_date_then_the_higher() -> None:
    """REQ-024."""
    morning = Reading(TODAY, D("6411.0"), 4234)
    assert current_total([NOVEMBER, OCTOBER, morning]) == NOVEMBER
    assert current_total([morning, OCTOBER]) == morning
    assert current_total([]) is None


TENTHS = st.integers(min_value=0, max_value=500_000).map(lambda n: Decimal(n) / 10)
DATES = st.dates(min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))


@given(TENTHS, st.integers(0, 100_000), TENTHS, st.integers(0, 5_000), st.integers(0, 2_000), DATES)
def test_an_accepted_entry_is_never_lower_and_never_impossible(
    hours: Decimal, cycles: int, gained: Decimal, gained_cycles: int, days: int, start: date
) -> None:
    """REQ-025. For any pair of entries: if the check does not refuse, the new
    total is not below the old one and not more than 24 hours a day above it;
    and confirmation is asked for exactly when a daily threshold is passed."""
    earlier = Reading(start, hours, cycles)
    on = date.fromordinal(start.toordinal() + days)
    new = Reading(on, hours + gained, cycles + gained_cycles)
    counted = days + 1
    try:
        verdict = check_entry(new, others=[earlier], today=on)
    except EntryRefusedError:
        assert gained > 24 * counted
        return
    assert gained <= 24 * counted
    unusual = gained > 10 * counted or gained_cycles > 100 * counted
    assert verdict is (Verdict.NEEDS_CONFIRMATION if unusual else Verdict.ACCEPTED)


@given(TENTHS, TENTHS, DATES)
def test_a_lower_total_is_always_refused(hours: Decimal, less: Decimal, on: date) -> None:
    """REQ-025."""
    if less == 0:
        return
    earlier = Reading(on, hours + less, 0)
    with pytest.raises(EntryRefusedError):
        check_entry(Reading(on, hours, 0), others=[earlier], today=on)
