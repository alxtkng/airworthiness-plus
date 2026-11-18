"""How dates, hours and numbers are written (REQ-192, design-system/Writing.md)."""

from datetime import date, datetime
from decimal import Decimal

from airworthiness_rules.dates import UK
from airworthiness_rules.intervals import Unit

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def long_date(value: date) -> str:
    """Write a date as 18 November 2026."""
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def moment(value: datetime) -> str:
    """Write a time as 18 November 2026, 14:05, in United Kingdom time."""
    local = value.astimezone(UK)
    return f"{long_date(local.date())}, {local:%H:%M}"


def hours(value: Decimal) -> str:
    """Write hours as 6,412.6: a comma for thousands and one decimal place."""
    return f"{value:,.1f}"


def whole(value: int) -> str:
    """Write a whole number as 4,236."""
    return f"{value:,}"


def amount(unit: Unit, value: Decimal | int) -> str:
    """Write an amount with its unit: 12.4 Hours, 78 Days, 1 Day, 30 Cycles.

    A negative amount takes a true minus sign: \u22120.5 Hours.
    """
    sign = "\u2212" if value < 0 else ""
    if unit is Unit.HOURS:
        return f"{sign}{hours(abs(Decimal(value)))} Hours"
    count = abs(int(value))
    name = "Cycle" if unit is Unit.CYCLES else "Day"
    return f"{sign}{whole(count)} {name}{'' if count == 1 else 's'}"


def point(unit: Unit, value: Decimal | int | date) -> str:
    """Write a due point: 6,425.0 Hours, 4,236 Cycles or 30 July 2027."""
    if isinstance(value, date):
        return long_date(value)
    return amount(unit, value)
