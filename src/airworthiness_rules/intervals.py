"""Next-due calculation for repeating tasks (REQ-041 to REQ-047).

A task may have a limit in hours, in cycles, in calendar time, or any
combination. Every limit is calculated exactly. Which comes first is a
planning projection only: the task is due when any limit is reached.

Hours are ``Decimal`` so that 6,425.0 less 6,412.6 is exactly 12.4 (REQ-028).
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal
from enum import Enum

from airworthiness_rules.dates import add_days, add_months, days_between


class Unit(Enum):
    """The unit a limit is expressed in."""

    HOURS = "Hours"
    CYCLES = "Cycles"
    CALENDAR = "Calendar"


@dataclass(frozen=True)
class Interval:
    """How often a task repeats. At least one field is set."""

    hours: Decimal | None = None
    cycles: int | None = None
    months: int | None = None
    days: int | None = None

    def __post_init__(self) -> None:
        if self.months is not None and self.days is not None:
            raise ValueError("A calendar interval is in months or in days, not both")
        values = (self.hours, self.cycles, self.months, self.days)
        if all(value is None for value in values):
            raise ValueError("An interval needs at least one limit")
        if any(value is not None and value <= 0 for value in values):
            raise ValueError("Every limit of an interval must be greater than zero")


@dataclass(frozen=True)
class Reading:
    """Airframe hours and cycles on a date."""

    on: date
    hours: Decimal
    cycles: int = 0


@dataclass(frozen=True)
class Utilisation:
    """Planning figures used only to rank limits in different units."""

    hours_per_day: Decimal | None = None
    cycles_per_day: Decimal | None = None


@dataclass(frozen=True)
class Limit:
    """One limit of a task: when it falls due and how much remains.

    ``due`` and ``remaining`` are hours (``Decimal``) for HOURS, a whole
    number for CYCLES, and for CALENDAR a date and a number of days.
    ``remaining`` is negative when the limit has been passed.
    """

    unit: Unit
    due: Decimal | int | date
    remaining: Decimal | int

    @property
    def overdue(self) -> bool:
        """Return whether the limit has been passed. Reaching it exactly is not overdue."""
        return self.remaining < 0


def limits(interval: Interval, last_done: Reading, current: Reading) -> tuple[Limit, ...]:
    """Return every limit of the task, in the order hours, cycles, calendar (REQ-042).

    Each limit runs from when the task was last done. ``current.on`` is today.
    """
    if current.hours < last_done.hours or current.cycles < last_done.cycles:
        raise ValueError("Current hours and cycles cannot be lower than when the task was done")
    if current.on < last_done.on:
        raise ValueError("Today cannot be before the day the task was done")

    found: list[Limit] = []
    if interval.hours is not None:
        due_hours = last_done.hours + interval.hours
        found.append(Limit(Unit.HOURS, due_hours, due_hours - current.hours))
    if interval.cycles is not None:
        due_cycles = last_done.cycles + interval.cycles
        found.append(Limit(Unit.CYCLES, due_cycles, due_cycles - current.cycles))
    if interval.months is not None:
        due_date = add_months(last_done.on, interval.months)
        found.append(Limit(Unit.CALENDAR, due_date, days_between(current.on, due_date)))
    if interval.days is not None:
        due_date = add_days(last_done.on, interval.days)
        found.append(Limit(Unit.CALENDAR, due_date, days_between(current.on, due_date)))
    return tuple(found)


def is_due(found: tuple[Limit, ...]) -> bool:
    """Return whether the task is due: any limit reached or passed (REQ-043).

    This never uses a projection.
    """
    return any(limit.remaining <= 0 for limit in found)


def projected_days(limit: Limit, utilisation: Utilisation | None) -> int | None:
    """Return the whole days until the limit is reached, or None if it cannot be projected.

    Hours and cycles are divided by the planning rate and rounded down, so
    the projection is never later than the rate implies (REQ-044).
    """
    if limit.unit is Unit.CALENDAR:
        return int(limit.remaining)
    rate = None
    if utilisation is not None:
        rate = utilisation.hours_per_day if limit.unit is Unit.HOURS else utilisation.cycles_per_day
    if rate is None or rate <= 0:
        return None
    return int((Decimal(limit.remaining) / rate).to_integral_value(rounding=ROUND_FLOOR))


def comes_first(found: tuple[Limit, ...], utilisation: Utilisation | None) -> tuple[Limit, ...]:
    """Return the limit or limits expected to be reached first (REQ-043, REQ-044).

    One limit: it is returned. A limit already reached or passed needs no
    projection: the reached limits are returned whatever the planning
    figures say. Otherwise each limit is projected to a number of days and
    the smallest wins; limits on the same day are all returned. If any limit
    cannot be projected, none is ranked and all are returned.
    """
    if not found:
        raise ValueError("A task has at least one limit")
    if len(found) == 1:
        return found
    reached = tuple(limit for limit in found if limit.remaining <= 0)
    if reached:
        return reached
    projections = [projected_days(limit, utilisation) for limit in found]
    known = [days for days in projections if days is not None]
    if len(known) != len(found):
        return found
    soonest = min(known)
    return tuple(limit for limit, days in zip(found, known, strict=True) if days == soonest)
