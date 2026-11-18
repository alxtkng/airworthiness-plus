"""What is flagged, and when: Due Soon, deadlines, the programme review (REQ-051 to REQ-055).

The thresholds for Due Soon are ours, not the regulation's
(design-system/Decisions.md, Interface). The periods are the regulation's:
UK Regulation (EU) No 1321/2014, ML.A.302(c)(9) and Appendices I and II to
Part-ML, read in the Civil Aviation Authority Regulatory Library on
18 November 2026.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from airworthiness_rules.dates import add_days, add_months, days_between
from airworthiness_rules.intervals import Limit, State, Unit

PROGRAMME_REVIEW_MONTHS = 12
"""ML.A.302(c)(9): the programme is reviewed at least annually."""

PILOT_OWNER_NOTIFICATION_DAYS = 30
"""Appendices I and II to Part-ML: the pilot-owner informs the contracted
organisation no later than 30 days after completing a task."""


class Flag(Enum):
    """What is shown beside an item, from nothing to the worst."""

    NONE = ""
    DUE_SOON = "Due Soon"
    DUE = "Due"
    WITHIN_TOLERANCE = "Within Tolerance"
    OVERDUE = "Overdue"


@dataclass(frozen=True)
class Thresholds:
    """How close a limit must be to count as Due Soon (REQ-055).

    The defaults are 30 days, 10.0 hours and 10 cycles. An organisation may
    set its own.
    """

    days: int = 30
    hours: Decimal = Decimal("10.0")
    cycles: int = 10

    def __post_init__(self) -> None:
        if self.days < 0 or self.hours < 0 or self.cycles < 0:
            raise ValueError("A threshold cannot be below zero")

    def of(self, unit: Unit) -> Decimal | int:
        """Return the threshold for limits in ``unit``."""
        if unit is Unit.HOURS:
            return self.hours
        if unit is Unit.CYCLES:
            return self.cycles
        return self.days


def limit_flag(limit: Limit, thresholds: Thresholds) -> Flag:
    """Return the flag for one limit (REQ-055, REQ-056).

    Overdue, Within Tolerance and Due come from the state of the limit. A
    limit not yet reached is Due Soon when what remains is at or inside
    the threshold for its unit.
    """
    state = limit.state
    if state is State.OVERDUE:
        return Flag.OVERDUE
    if state is State.WITHIN_TOLERANCE:
        return Flag.WITHIN_TOLERANCE
    if state is State.DUE:
        return Flag.DUE
    return Flag.DUE_SOON if limit.remaining <= thresholds.of(limit.unit) else Flag.NONE


def task_flag(found: tuple[Limit, ...], thresholds: Thresholds) -> Flag:
    """Return the flag for a task: the worst among its limits (REQ-056)."""
    if not found:
        raise ValueError("A task has at least one limit")
    order = list(Flag)
    return max((limit_flag(limit, thresholds) for limit in found), key=order.index)


def deadline_flag(today: date, deadline: date) -> Flag:
    """Return the flag for a regulatory deadline of 30 days or fewer (REQ-055).

    Such a deadline is Due Soon from the day it starts, Due on its last
    day, and Overdue after it.
    """
    remaining = days_between(today, deadline)
    if remaining < 0:
        return Flag.OVERDUE
    return Flag.DUE if remaining == 0 else Flag.DUE_SOON


def programme_review_due(last_reviewed: date) -> date:
    """Return the day by which the programme is next reviewed (REQ-053).

    ML.A.302(c)(9): at least annually. Twelve months after the last review.
    """
    return add_months(last_reviewed, PROGRAMME_REVIEW_MONTHS)


def pilot_owner_notification_deadline(completed: date) -> date:
    """Return the last day for a pilot-owner to tell the organisation of a task (REQ-052)."""
    return add_days(completed, PILOT_OWNER_NOTIFICATION_DAYS)


def pilot_owner_told_late(completed: date, told: date) -> bool:
    """Return whether the organisation was told more than 30 days after the task (REQ-052)."""
    return days_between(completed, told) > PILOT_OWNER_NOTIFICATION_DAYS
