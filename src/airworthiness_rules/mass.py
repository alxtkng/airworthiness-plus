"""Mass change since the last weighing (REQ-255, REQ-256).

UK Regulation (EU) No 1321/2014, ML.A.305(d), read in the Civil Aviation
Authority Regulatory Library on 27 November 2026: the continuing
airworthiness records contain the current status of modifications and
repairs and the current mass and balance report.

No rule read gives a mass change at which an aircraft is weighed again.
Ours, not the regulation's (design-system/Decisions.md, Canvas Build,
Phase 1): the threshold is a setting the organisation keeps, with no
default. Until it is set nothing is marked for a reweigh.

Kilograms are ``Decimal``, so that 1.2 less 0.3 is exactly 0.9.
"""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

MOST_MASS = Decimal("999.9")
"""Ours: the most the mass effect of one change, or the threshold, may be, in Kilograms."""


def counted_since(embodied_on: date, weighed_on: date) -> bool:
    """Return whether a change embodied on ``embodied_on`` is one since the weighing.

    A change embodied after the day of the weighing. One embodied on the
    day itself, or before, was on the aircraft when it was weighed.
    """
    return embodied_on > weighed_on


def net_change(effects: Iterable[Decimal]) -> Decimal:
    """Return the net mass change: the sum of the mass effects, each with its sign."""
    total = Decimal("0.0")
    for effect in effects:
        if abs(effect) > MOST_MASS:
            raise ValueError("A mass effect is at most 999.9 Kilograms either way")
        total += effect
    return total


def in_schedule(embodied_on: date, schedule_issued_on: date | None) -> bool:
    """Return whether a change is in the weight schedule.

    It is once an issue of the schedule is dated on or after the day the
    change was embodied.
    """
    return schedule_issued_on is not None and schedule_issued_on >= embodied_on


def over_threshold(net: Decimal, threshold: Decimal | None) -> bool:
    """Return whether the net change is over the organisation's reweigh threshold.

    By its size, whichever way the mass has gone. Exactly at the threshold
    is not over it. With no threshold set nothing is over it.
    """
    if threshold is None:
        return False
    if threshold <= 0:
        raise ValueError("A threshold is above zero")
    return abs(net) > threshold
