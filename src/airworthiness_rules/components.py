"""Components and their life limits (REQ-230 to REQ-239).

UK Regulation (EU) No 1321/2014, ML.A.503 and ML.A.305(e), read in the
Civil Aviation Authority Regulatory Library on 27 November 2026:

- a service-life-limited component is one with a certified life limit,
  after which it is retired, or a service life limit, after which it
  undergoes maintenance to restore its serviceability;
- an installed component does not exceed its approved service life limit;
- the life is expressed in calendar time, flight hours, landings or
  cycles;
- the records of a component hold where it has been fitted, with its
  installation and removal, and its accumulated time.

Ours, not the regulation's (design-system/Decisions.md, Canvas Build,
Phase 1): the time of a component is what it had when it was fitted and
what the airframe has flown since; a calendar life runs from the day the
component was new or last overhauled; a limit has no tolerance.

Hours are ``Decimal``, so that 2,000.0 less 1,780.0 is exactly 220.0.
"""

from datetime import date
from decimal import Decimal

from airworthiness_rules.dates import add_months, days_between
from airworthiness_rules.intervals import (
    Interval,
    Limit,
    Reading,
    TaskKind,
    Unit,
    Utilisation,
    limits,
    projected_days,
)
from airworthiness_rules.programme import Flag

MOST_HOURS = Decimal("999999.9")
"""Ours: the most hours a component or an airframe is recorded with."""

MOST_CYCLES = 9_999_999
"""Ours: the most cycles a component or an airframe is recorded with."""

MOST_LIMIT_HOURS = Decimal("99999.9")
MOST_LIMIT_CYCLES = 999_999
MOST_LIMIT_MONTHS = 1_200
MOST_REVIEW_HOURS = Decimal("9999.9")
"""Ours: the most a limit may be."""

DUE_WITHIN_MONTHS = 6
"""Ours, from the Components board: Due in 6 Months."""


def hours_since(
    at_fitting: Decimal, airframe_at_fitting: Decimal, airframe_now: Decimal
) -> Decimal:
    """Return the hours of a component since new or overhaul (REQ-231).

    What it had when it was fitted, and what the airframe has flown since.
    """
    if at_fitting < 0 or airframe_at_fitting < 0:
        raise ValueError("Hours are not below zero")
    if airframe_now < airframe_at_fitting:
        raise ValueError("The airframe has not fewer hours than when the component was fitted")
    return at_fitting + (airframe_now - airframe_at_fitting)


def cycles_since(at_fitting: int, airframe_at_fitting: int, airframe_now: int) -> int:
    """Return the cycles of a component since new or overhaul (REQ-231)."""
    if at_fitting < 0 or airframe_at_fitting < 0:
        raise ValueError("Cycles are not below zero")
    if airframe_now < airframe_at_fitting:
        raise ValueError("The airframe has not fewer cycles than when the component was fitted")
    return at_fitting + (airframe_now - airframe_at_fitting)


def life_limits(
    limit: Interval, life_from: date | None, hours: Decimal, cycles: int, today: date
) -> tuple[Limit, ...]:
    """Return every limit of a component's life, in the order hours, cycles, calendar (REQ-232).

    ``hours`` and ``cycles`` are the component's since new or overhaul. A
    limit in hours or cycles is due at the limit itself. A calendar life
    runs from ``life_from``, the day the component was new or last
    overhauled; without that day it cannot be worked out, and this refuses.
    No tolerance: GM1 ML.A.302(c)(4).
    """
    if limit.days is not None:
        raise ValueError("A calendar life is in months")
    if limit.months is not None and life_from is None:
        raise ValueError("A calendar life needs the day it runs from")
    start = life_from if life_from is not None else today
    return limits(
        limit,
        Reading(start, Decimal(0), 0),
        Reading(today, hours, cycles),
        kind=TaskKind.LIFE_LIMIT,
    )


def dated_limit(limit_on: date, today: date) -> Limit:
    """Return the limit of a date printed on a component, such as a battery date (REQ-232)."""
    return Limit(Unit.CALENDAR, limit_on, days_between(today, limit_on))


def review_limit(reviewed_at: Decimal, every: Decimal, airframe_now: Decimal) -> Limit:
    """Return when a component kept on condition is next reviewed (REQ-233).

    In airframe hours: the hours at the last review and the review interval.
    """
    if every <= 0:
        raise ValueError("A review interval is above zero")
    if airframe_now < reviewed_at:
        raise ValueError("The airframe has not fewer hours than at the last review")
    due = reviewed_at + every
    return Limit(Unit.HOURS, due, due - airframe_now)


def due_within_months(
    found: tuple[Limit, ...], today: date, utilisation: Utilisation | None
) -> bool:
    """Return whether a component is among those Due in 6 Months (REQ-234).

    A limit reached or passed; a calendar limit on or before the same day
    6 months on; a limit in hours or cycles projected to on or before it.
    A limit that cannot be projected is counted: nobody can place it
    outside the 6 months.
    """
    window = days_between(today, add_months(today, DUE_WITHIN_MONTHS))
    for limit in found:
        days = projected_days(limit, utilisation)
        if limit.remaining <= 0 or days is None or days <= window:
            return True
    return False


def due_back_flag(today: date, due_back: date, lead_days: int) -> Flag:
    """Return the flag for a component due back from maintenance (REQ-236).

    Overdue once the day has passed, Due on the day, and Due Soon from the
    organisation's lead time in days.
    """
    remaining = days_between(today, due_back)
    if remaining < 0:
        return Flag.OVERDUE
    if remaining == 0:
        return Flag.DUE
    return Flag.DUE_SOON if remaining <= lead_days else Flag.NONE
