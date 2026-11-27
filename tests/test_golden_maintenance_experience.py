"""Standard duration routes from UK CAA AMC 66.A.20(b)(2).

Evidence for activity type, scope, licence and approvals is assessed separately.
"""

from datetime import date, timedelta
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.maintenance_experience import DaysOfExperience, duration, window_start

ON = date(2026, 11, 18)
D = Decimal
FULL_DAYS = [DaysOfExperience(date(2026, 1, 1) + timedelta(days=i), D("1")) for i in range(100)]


def test_golden_standard_days_and_partial_days() -> None:
    assert duration(ON, days=FULL_DAYS).days == D("100")
    short = FULL_DAYS[:99]
    first = DaysOfExperience(date(2026, 5, 1), D("0.5"))
    second = DaysOfExperience(date(2026, 5, 2), D("0.5"))
    assert duration(ON, days=[*short, first]).days == D("99.5")
    assert duration(ON, days=[*short, first, second]).days == D("100")


def test_golden_window_first_day_and_start_of_assessment_day() -> None:
    assert window_start(ON) == date(2024, 11, 18)
    short = FULL_DAYS[:99]
    assert duration(ON, days=[*short, DaysOfExperience(date(2024, 11, 18), D("1"))]).days == 100
    assert duration(ON, days=[*short, DaysOfExperience(date(2024, 11, 17), D("1"))]).days == 99
    assert duration(ON, days=[*short, DaysOfExperience(ON, D("1"))]).days == 99


def test_golden_same_date_cap_and_substitute_credit() -> None:
    short = [*FULL_DAYS[:98], DaysOfExperience(date(2026, 6, 1), D("0.5"))]
    date_with_two_entries = date(2026, 7, 1)
    entry = DaysOfExperience(date_with_two_entries, D("0.75"))
    assert duration(ON, days=[*short, entry, entry]).days == D("99.5")
    alternate = [
        DaysOfExperience(date(2026, 6, 1) + timedelta(days=i), D("1"), substitute=True)
        for i in range(21)
    ]
    assert duration(ON, days=[*FULL_DAYS[:80], *alternate]).days == 100
    result = duration(ON, days=[*FULL_DAYS[:79], *alternate])
    assert result.days == 99 and result.substitute_days == 20


def test_golden_six_month_route_counts_full_calendar_months() -> None:
    continuous = [(date(2026, 1, 1), date(2026, 7, 1))]
    assert duration(ON, employment=continuous).full_months == 6
    blocks = [(date(2026, 1, 1), date(2026, 4, 1)), (date(2026, 7, 1), date(2026, 10, 1))]
    assert duration(ON, employment=blocks).full_months == 6
    overlap = [(date(2026, 1, 1), date(2026, 4, 1)), (date(2026, 3, 1), date(2026, 6, 1))]
    assert duration(ON, employment=overlap).full_months == 5


@given(st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=30))
def test_days_cannot_exceed_one_per_date(hundredths: list[int]) -> None:
    on = date(2026, 1, 1)
    days = [DaysOfExperience(on, D(portion) / 100) for portion in hundredths]
    assert duration(ON, days=days).days == min(D("1"), D(sum(hundredths)) / 100)
