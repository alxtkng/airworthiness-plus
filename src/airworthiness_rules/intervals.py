"""Next-due calculation for repeating tasks (REQ-041 to REQ-049, REQ-056, REQ-057).

A task may have a limit in hours, in cycles, in calendar time, or any
combination. Every limit is calculated exactly. Which comes first is a
planning projection only: the task is due when any limit is reached.

A tolerance never moves a due point. It is given only to an inspection of
the Minimum Inspection Programme (ML.A.302(d)(1)) and says how far past the
due point the inspection may still be done.

Hours are ``Decimal`` so that 6,425.0 less 6,412.6 is exactly 12.4 (REQ-028).

Source for the tolerance rules: UK Regulation (EU) No 1321/2014, ML.A.302,
ML.A.303, AMC1 ML.A.302(d), GM1 ML.A.302, GM1 ML.A.302(c)(3) and
GM1 ML.A.302(c)(4), read in the Civil Aviation Authority Regulatory Library
on 18 November 2026.
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


class TaskKind(Enum):
    """What a task is, which decides whether a tolerance may be applied (REQ-049)."""

    MINIMUM_INSPECTION_PROGRAMME = "Minimum Inspection Programme"
    PROGRAMME_TASK = "Programme Task"
    AIRWORTHINESS_DIRECTIVE = "Airworthiness Directive"
    AIRWORTHINESS_LIMITATION = "Airworthiness Limitation"
    LIFE_LIMIT = "Life Limit"


class ToleranceNotPermittedError(ValueError):
    """The tolerance asked for is not one the regulation gives."""


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
class Tolerance:
    """How far past its due point a task may still be done. At least one field is set.

    ``hours`` applies to the hours limit and ``months`` to the calendar limit.
    The regulation gives no tolerance in cycles.
    """

    hours: Decimal | None = None
    months: int | None = None

    def __post_init__(self) -> None:
        values = (self.hours, self.months)
        if all(value is None for value in values):
            raise ValueError("A tolerance needs at least one amount")
        if any(value is not None and value <= 0 for value in values):
            raise ValueError("Every amount of a tolerance must be greater than zero")


MOST_TOLERANCE_HOURS = Decimal("10")
MOST_TOLERANCE_MONTHS = 1
"""ML.A.302(d)(1): the largest tolerance the regulation gives."""

MINIMUM_INSPECTION_PROGRAMME_INTERVAL = Interval(hours=Decimal("100"), months=12)
"""ML.A.302(d)(1)(a): aeroplanes, touring motor gliders and balloons are
inspected every annual or 100-hour interval, whichever comes first."""

MINIMUM_INSPECTION_PROGRAMME_TOLERANCE = Tolerance(
    hours=MOST_TOLERANCE_HOURS, months=MOST_TOLERANCE_MONTHS
)
"""ML.A.302(d)(1)(a): a tolerance of 1 month or 10 hours may be applied."""

MINIMUM_INSPECTION_PROGRAMME_INTERVAL_SAILPLANE = Interval(months=12)
"""ML.A.302(d)(1)(b): sailplanes and powered sailplanes other than touring
motor gliders are inspected every annual interval."""

MINIMUM_INSPECTION_PROGRAMME_TOLERANCE_SAILPLANE = Tolerance(months=MOST_TOLERANCE_MONTHS)
"""ML.A.302(d)(1)(b): a tolerance of 1 month may be applied."""


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

    ``tolerance_limit`` is the due point plus the tolerance, and
    ``tolerance_remaining`` is what is left before it. Both are None when
    the limit has no tolerance.
    """

    unit: Unit
    due: Decimal | int | date
    remaining: Decimal | int
    tolerance_limit: Decimal | date | None = None
    tolerance_remaining: Decimal | int | None = None

    @property
    def overdue(self) -> bool:
        """Return whether the limit, and any tolerance on it, has been passed (REQ-056).

        Reaching the limit, or the end of the tolerance, exactly is not overdue.
        """
        if self.tolerance_remaining is not None:
            return self.tolerance_remaining < 0
        return self.remaining < 0

    @property
    def within_tolerance(self) -> bool:
        """Return whether the limit has been passed but its tolerance has not (REQ-056)."""
        return self.remaining < 0 and not self.overdue


def _check_tolerance(kind: TaskKind | None, tolerance: Tolerance) -> None:
    """Refuse any tolerance the regulation does not give (REQ-048, REQ-049)."""
    if kind is None:
        raise ToleranceNotPermittedError("A tolerance needs the kind of task to be stated")
    if kind is TaskKind.AIRWORTHINESS_DIRECTIVE:
        raise ToleranceNotPermittedError(
            "ML.A.303: an airworthiness directive is carried out within its own requirements"
        )
    if kind in (TaskKind.AIRWORTHINESS_LIMITATION, TaskKind.LIFE_LIMIT):
        raise ToleranceNotPermittedError(
            "GM1 ML.A.302(c)(4): the interval of mandatory continuing airworthiness "
            "information cannot be extended"
        )
    if kind is not TaskKind.MINIMUM_INSPECTION_PROGRAMME:
        raise ToleranceNotPermittedError(
            "ML.A.302(d)(1): a tolerance is given only for the Minimum Inspection Programme"
        )
    if (tolerance.hours is not None and tolerance.hours > MOST_TOLERANCE_HOURS) or (
        tolerance.months is not None and tolerance.months > MOST_TOLERANCE_MONTHS
    ):
        raise ToleranceNotPermittedError(
            "ML.A.302(d)(1): the tolerance is at most 1 month or 10 hours"
        )


def limits(
    interval: Interval,
    last_done: Reading,
    current: Reading,
    *,
    kind: TaskKind | None = None,
    tolerance: Tolerance | None = None,
) -> tuple[Limit, ...]:
    """Return every limit of the task, in the order hours, cycles, calendar (REQ-042).

    Each limit runs from when the task was last done, whether that was
    early, on time or inside a tolerance (REQ-048, ML.A.302(d)(1)).
    ``current.on`` is today.

    A tolerance is accepted only with ``kind`` stated as an inspection of the
    Minimum Inspection Programme, and never above 1 month or 10 hours
    (REQ-048, REQ-049). It adds a tolerance limit to the hours and calendar
    limits; the due point and what remains to it are unchanged.
    """
    if tolerance is not None:
        _check_tolerance(kind, tolerance)
    if current.hours < last_done.hours or current.cycles < last_done.cycles:
        raise ValueError("Current hours and cycles cannot be lower than when the task was done")
    if current.on < last_done.on:
        raise ValueError("Today cannot be before the day the task was done")

    found: list[Limit] = []
    if interval.hours is not None:
        due_hours = last_done.hours + interval.hours
        if tolerance is not None and tolerance.hours is not None:
            latest_hours = due_hours + tolerance.hours
            found.append(
                Limit(
                    Unit.HOURS,
                    due_hours,
                    due_hours - current.hours,
                    latest_hours,
                    latest_hours - current.hours,
                )
            )
        else:
            found.append(Limit(Unit.HOURS, due_hours, due_hours - current.hours))
    if interval.cycles is not None:
        due_cycles = last_done.cycles + interval.cycles
        found.append(Limit(Unit.CYCLES, due_cycles, due_cycles - current.cycles))
    due_date: date | None = None
    if interval.months is not None:
        due_date = add_months(last_done.on, interval.months)
    if interval.days is not None:
        due_date = add_days(last_done.on, interval.days)
    if due_date is not None:
        remaining_days = days_between(current.on, due_date)
        if tolerance is not None and tolerance.months is not None:
            latest_date = add_months(due_date, tolerance.months)
            found.append(
                Limit(
                    Unit.CALENDAR,
                    due_date,
                    remaining_days,
                    latest_date,
                    days_between(current.on, latest_date),
                )
            )
        else:
            found.append(Limit(Unit.CALENDAR, due_date, remaining_days))
    return tuple(found)


def is_due(found: tuple[Limit, ...]) -> bool:
    """Return whether the task is due: any limit reached or passed (REQ-043).

    This never uses a projection, and a tolerance never makes a task not due
    (REQ-056).
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


def tolerance_outlasts_certificate(limit: Limit, certificate_valid_to: date) -> bool:
    """Return whether the calendar tolerance ends after the review certificate (REQ-057).

    AMC1 ML.A.302(d) notes that using the 1-month tolerance for the annual
    inspection may result in an expired airworthiness review certificate.
    """
    return isinstance(limit.tolerance_limit, date) and limit.tolerance_limit > certificate_valid_to
