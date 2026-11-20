"""Date arithmetic used by every rule.

Regulatory periods are counted in whole UK local dates (REQ-137). A date
here is always a ``datetime.date`` with no time and no time zone; the only
place a clock time enters is ``uk_today``.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")


def uk_today(now: datetime) -> date:
    """Return the UK local date at the instant ``now`` (REQ-137).

    ``now`` must carry a time zone, so that an instant near midnight during
    British Summer Time is never read as the wrong day.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must carry a time zone")
    return now.astimezone(UK).date()


def utc_now() -> datetime:
    """Return the current instant in Coordinated Universal Time."""
    return datetime.now(UTC)


def days_between(start: date, end: date) -> int:
    """Return the exact number of days from ``start`` to ``end`` (REQ-046).

    From 18 November 2026 to 6 December 2026 is 18. Negative when ``end`` is
    before ``start``.
    """
    return (end - start).days


class BeyondCalendarError(ValueError):
    """The date asked for is before 1 January 1 or after 31 December 9999."""


def add_days(start: date, days: int) -> date:
    """Return the date ``days`` days after ``start``."""
    try:
        return start + timedelta(days=days)
    except OverflowError as error:
        raise BeyondCalendarError(f"{days} days after {start} is not a date") from error


def add_years(start: date, years: int) -> date:
    """Return the same day and month ``years`` years later (REQ-047).

    29 February lands on 28 February when the target year is not a leap year.
    """
    if not date.min.year <= start.year + years <= date.max.year:
        raise BeyondCalendarError(f"{years} years after {start} is not a date")
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        return start.replace(year=start.year + years, day=28)


def add_months(start: date, months: int) -> date:
    """Return the same day of the month ``months`` months later (REQ-047).

    Lands on the last day of the month when that month is shorter:
    31 January plus 1 month is 28 or 29 February.
    """
    index = start.year * 12 + (start.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    if not date.min.year <= year <= date.max.year:
        raise BeyondCalendarError(f"{months} months after {start} is not a date")
    if (year, month) == (date.max.year, 12):
        return date(year, 12, min(start.day, 31))
    first_of_next = date(year + (month == 12), month % 12 + 1, 1)
    last_day = (first_of_next - timedelta(days=1)).day
    return date(year, month, min(start.day, last_day))
