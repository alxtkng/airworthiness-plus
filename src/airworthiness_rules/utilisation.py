"""Checks on a new hours and cycles entry (REQ-024, REQ-025, REQ-028).

Hazard H-011: hours or cycles entered wrongly and accepted. An entry is a
total on a date. It must fit between the entries around it, and an
increase too large to be believed is refused or sent back for
confirmation. The thresholds are ours, not the regulation's
(design-system/Decisions.md, Interface).
"""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from enum import Enum

from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Reading

HOURS_IN_A_DAY = Decimal("24")
"""No counter can gain more than 24 hours in a day."""

UNUSUAL_HOURS_A_DAY = Decimal("10")
UNUSUAL_CYCLES_A_DAY = 100
"""More than this for each day needs the person entering it to confirm."""


class Verdict(Enum):
    """What to do with an entry that is not refused."""

    ACCEPTED = "Accepted"
    NEEDS_CONFIRMATION = "Needs Confirmation"


class EntryRefusedError(ValueError):
    """The entry cannot be right and is not accepted."""


def _days_counted(first: date, second: date) -> int:
    """Return the days between two entries, plus one.

    An entry may be made at the start of its day and the next at the end
    of its day, so two entries a day apart can be two days of flying apart.
    """
    return days_between(first, second) + 1


def check_entry(new: Reading, *, others: Iterable[Reading], today: date) -> Verdict:
    """Check ``new`` against every other current entry of the same counter.

    ``others`` are the current entries: a superseded entry is never passed
    in, nor is the entry that ``new`` corrects.

    Refused: a date after today; hours not to one decimal place; a total
    below any entry dated on or before it, or above any entry dated after
    it; a gain of more than 24 hours for each day counted, from any earlier
    entry to this one or from this one to any later entry.

    Needs confirmation: a gain of more than 10.0 hours or 100 cycles for
    each day counted, measured the same way.

    Every pair is measured, not only neighbours, so that a run of entries
    each within the limit cannot add up to a gain that is not. This was
    found by the independent recompute.
    """
    if new.on > today:
        raise EntryRefusedError("An entry cannot be dated after today")
    if new.hours < 0 or new.cycles < 0:
        raise EntryRefusedError("Hours and cycles cannot be below zero")
    if new.hours != new.hours.quantize(Decimal("0.1")):
        raise EntryRefusedError("Hours are entered to one decimal place")

    current = list(others)
    earlier = [entry for entry in current if entry.on <= new.on]
    later = [entry for entry in current if entry.on > new.on]
    if any(new.hours > entry.hours or new.cycles > entry.cycles for entry in later):
        raise EntryRefusedError("Higher than a later entry")
    if any(new.hours < entry.hours or new.cycles < entry.cycles for entry in earlier):
        raise EntryRefusedError("Lower than the previous entry")

    spans = [(entry, new) for entry in earlier] + [(new, entry) for entry in later]
    unusual = False
    for first, second in spans:
        days = _days_counted(first.on, second.on)
        gained_hours = second.hours - first.hours
        gained_cycles = second.cycles - first.cycles
        if gained_hours > HOURS_IN_A_DAY * days:
            raise EntryRefusedError("More hours than there are in the days between entries")
        if gained_hours > UNUSUAL_HOURS_A_DAY * days or gained_cycles > UNUSUAL_CYCLES_A_DAY * days:
            unusual = True
    return Verdict.NEEDS_CONFIRMATION if unusual else Verdict.ACCEPTED


def current_total(entries: Iterable[Reading]) -> Reading | None:
    """Return the current total: the entry with the latest date (REQ-024).

    ``entries`` are the current entries, without superseded ones. Of two
    entries on the same date the higher is the later.
    """
    latest: Reading | None = None
    for entry in entries:
        if latest is None or (entry.on, entry.hours, entry.cycles) > (
            latest.on,
            latest.hours,
            latest.cycles,
        ):
            latest = entry
    return latest
