"""How dates, hours and numbers are written (REQ-192, design-system/Writing.md)."""

from datetime import date
from decimal import Decimal

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


def hours(value: Decimal) -> str:
    """Write hours as 6,412.6: a comma for thousands and one decimal place."""
    return f"{value:,.1f}"


def whole(value: int) -> str:
    """Write a whole number as 4,236."""
    return f"{value:,}"
