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


def add_days(start: date, days: int) -> date:
    """Return the date ``days`` days after ``start``."""
    return start + timedelta(days=days)


def add_years(start: date, years: int) -> date:
    """Return the same day and month ``years`` years later (REQ-047).

    29 February lands on 28 February when the target year is not a leap year.
    """
    try:
        return start.replace(year=start.year + years)
    except ValueError:
        return start.replace(year=start.year + years, day=28)
