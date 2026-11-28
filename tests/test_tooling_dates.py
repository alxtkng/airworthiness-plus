"""The REQ-362 label anniversary uses the shared whole-UK-date arithmetic."""

from calendar import monthrange
from datetime import UTC, date, datetime

from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules.dates import add_months, uk_today


@given(
    anchor=st.dates(min_value=date(1900, 1, 1), max_value=date(2200, 12, 31)),
    months=st.integers(min_value=1, max_value=1200),
)
def test_tool_due_month_keeps_anniversary_day_when_available(anchor: date, months: int) -> None:
    due = add_months(anchor, months)
    assert (due.year - anchor.year) * 12 + due.month - anchor.month == months
    assert due.day == min(anchor.day, monthrange(due.year, due.month)[1])


def test_tool_due_business_date_rolls_over_at_uk_midnight() -> None:
    assert uk_today(datetime(2026, 9, 12, 22, 59, 59, tzinfo=UTC)) == date(2026, 9, 12)
    assert uk_today(datetime(2026, 9, 12, 23, tzinfo=UTC)) == date(2026, 9, 13)
