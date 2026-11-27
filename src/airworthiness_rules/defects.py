"""Deferred defects and repeat defects (REQ-220 to REQ-229).

UK Regulation (EU) No 1321/2014, ML.A.403, read in the Civil Aviation
Authority Regulatory Library on 27 November 2026:

- (a) a defect that seriously endangers flight safety is rectified before
  further flight;
- (b)(1) to (4) say who may defer any other defect;
- (c) a deferred defect is rectified as soon as practicable from first
  identification, within the maintenance-data limits.

The organisation sets a default for (b)(1), (b)(3) and (b)(4), starting
on the date first identified for new deferrals. An earlier maintenance-data
limit takes precedence. Under (b)(2) the minimum equipment list gives
the limit. The Repeat Defects board uses three occurrences of the same
defect on one type in 12 months (design-system/Decisions.md).
"""

from datetime import date

from airworthiness_rules.dates import add_days, add_months, days_between
from airworthiness_rules.programme import Flag

MOST_DAYS = 365
"""Ours: the most days a default limit may be, as the settings hold (REQ-214)."""

REPEAT_AT = 3
"""Ours, from the Repeat Defects board: 3 of the same defect on one type is a repeat."""

WATCH_AT = 2
"""Ours, from the Repeat Defects board: 2 of the same defect is watched."""

REPEAT_MONTHS = 12
"""Ours, from the Repeat Defects board: the months looked back over."""

FIRST_CHAPTER, LAST_CHAPTER = 1, 99
"""The chapter of the system a defect is in is a number of two digits at most."""


def deferral_limit(identified_on: date, default_days: int | None, data_limit: date | None) -> date:
    """Return the last day by which a deferred defect is rectified (REQ-222).

    ``default_days`` is the organisation's default for the decision, counted
    from the day the defect was first identified; none where the minimum equipment list
    gives the limit. ``data_limit`` is a limit specified in the maintenance
    data or the list, and applies when it is the earlier (ML.A.403(c)).
    """
    if default_days is None and data_limit is None:
        raise ValueError("A deferred defect has a limit")
    if default_days is not None and not 1 <= default_days <= MOST_DAYS:
        raise ValueError("A default limit is from 1 to 365 days")
    if data_limit is not None and data_limit < identified_on:
        raise ValueError("A limit is not before the day the defect was first identified")
    found = [] if default_days is None else [add_days(identified_on, default_days)]
    if data_limit is not None:
        found.append(data_limit)
    return min(found)


def deferral_flag(today: date, limit: date, lead_days: int) -> Flag:
    """Return the flag for a deferred defect (REQ-223).

    Overdue once the limit has passed, Due on its last day, and Due Soon
    from the organisation's lead time in days.
    """
    remaining = days_between(today, limit)
    if remaining < 0:
        return Flag.OVERDUE
    if remaining == 0:
        return Flag.DUE
    return Flag.DUE_SOON if remaining <= lead_days else Flag.NONE


def counted_from(today: date) -> date:
    """Return the first day of the 12 months that end today (REQ-226).

    The day after the same day 12 months before: on 18 November 2026 a
    defect found on 19 November 2025 is counted and one found on
    18 November 2025 is not.
    """
    return add_days(add_months(today, -REPEAT_MONTHS), 1)


def counted(found_on: date, today: date) -> bool:
    """Return whether a defect found on ``found_on`` is within the 12 months to today."""
    return counted_from(today) <= found_on <= today


def repeat_state(count: int) -> str:
    """Return what a count of the same defect on one type in 12 months is (REQ-226)."""
    if count < 0:
        raise ValueError("A count is not below zero")
    if count >= REPEAT_AT:
        return "Repeat"
    return "Watching" if count >= WATCH_AT else "No Action"
