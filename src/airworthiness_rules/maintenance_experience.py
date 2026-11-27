"""Duration evidence for the standard Part-66 routes in AMC 66.A.20(b)(2).

The caller supplies assessed activities and employment blocks relevant to the
licence and authorisation. Each day's input entries represent distinct work.
The duration alone does not determine whether the person can certify.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from airworthiness_rules.dates import add_months, add_years

STANDARD_DAYS = Decimal(100)
SUBSTITUTE_LIMIT = Decimal(20)
STANDARD_MONTHS = 6
ONE_DAY = Decimal(1)
ZERO = Decimal(0)


@dataclass(frozen=True)
class DaysOfExperience:
    on: date
    days: Decimal
    substitute: bool = False

    def __post_init__(self) -> None:
        if not self.days.is_finite() or not ZERO < self.days <= ONE_DAY:
            raise ValueError("Work credited to one date is a positive fraction of a day")


@dataclass(frozen=True)
class ExperienceDuration:
    days: Decimal
    substitute_days: Decimal
    full_months: int

    @property
    def meets_standard_duration(self) -> bool:
        return self.days >= STANDARD_DAYS or self.full_months >= STANDARD_MONTHS


def window_start(assessment_on: date) -> date:
    """First included date, for an assessment at the start of the given day."""
    return add_years(assessment_on, -2)


def _full_months(start: date, end: date, employment: Iterable[tuple[date, date]]) -> int:
    """Count full months of qualifying employment after clipping and merging overlaps."""
    blocks: list[tuple[date, date]] = []
    for first, stop in sorted(employment):
        if stop <= first:
            raise ValueError("An employment block ends after it starts")
        first, stop = max(first, start), min(stop, end)
        if first >= stop:
            continue
        if blocks and first <= blocks[-1][1]:
            beginning, previous_end = blocks[-1]
            blocks[-1] = (beginning, max(previous_end, stop))
        else:
            blocks.append((first, stop))
    total = 0
    for first, stop in blocks:
        candidate = (stop.year - first.year) * 12 + stop.month - first.month
        total += candidate - (add_months(first, candidate) > stop)
    return total


def duration(
    assessment_on: date,
    *,
    days: Iterable[DaysOfExperience] = (),
    employment: Iterable[tuple[date, date]] = (),
) -> ExperienceDuration:
    """Calculate ordinary duration routes for assessed, in-scope evidence.

    A date contributes at most one day. Direct maintenance gets first credit.
    Qualifying substitute activities can fill the remainder and contribute at
    most 20 days in total. Employment periods use an exclusive end date. Partial
    months in separate blocks are left for the organisation to assess.
    """
    start = window_start(assessment_on)
    direct_by_date: defaultdict[date, Decimal] = defaultdict(Decimal)
    substitute_by_date: defaultdict[date, Decimal] = defaultdict(Decimal)
    for entry in days:
        if start <= entry.on < assessment_on:
            totals = substitute_by_date if entry.substitute else direct_by_date
            totals[entry.on] += entry.days
    direct = sum((min(ONE_DAY, total) for total in direct_by_date.values()), ZERO)
    substitute = sum(
        (
            min(max(ZERO, ONE_DAY - direct_by_date[on]), total)
            for on, total in substitute_by_date.items()
        ),
        ZERO,
    )
    credited_substitute = min(SUBSTITUTE_LIMIT, substitute)
    return ExperienceDuration(
        direct + credited_substitute,
        credited_substitute,
        _full_months(start, assessment_on, employment),
    )
