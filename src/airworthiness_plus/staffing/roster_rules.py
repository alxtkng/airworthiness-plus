"""Elapsed time, employed share and weekly workload."""

from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal


def week_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def gap_minutes(before: datetime, after: datetime) -> int:
    """Use elapsed time, including overnight clock changes."""
    return int((after.astimezone(UTC) - before.astimezone(UTC)).total_seconds() // 60)


def active_minutes(starts: datetime, ends: datetime, break_minutes: int) -> int:
    return gap_minutes(starts, ends) - break_minutes


def _whole_percent(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def employed_share(employed: int, contracted: int) -> tuple[int | None, bool]:
    total = employed + contracted
    if total == 0:
        return None, False
    return _whole_percent(Decimal(employed * 100) / total), employed < contracted


def workload(
    package_hours: Decimal, other_hours: Decimal, available: Decimal, margin_percent: int
) -> tuple[int | None, bool]:
    needed = package_hours + other_hours
    if available <= 0:
        return None, needed > 0
    percent = needed * 100 / available
    return _whole_percent(percent), percent >= margin_percent
