"""Template filters for the writing rules (REQ-192).

A value that is missing is written as nothing. A template passes an empty
string, not None, for a value that is not there.
"""

from datetime import date
from decimal import Decimal

from django import template

from airworthiness_plus.interface import formatting
from airworthiness_rules.intervals import Unit

register = template.Library()


@register.filter
def long_date(value: object) -> str:
    """Write a date as 18 November 2026, or nothing if there is none."""
    return formatting.long_date(value) if isinstance(value, date) else ""


@register.filter
def hours(value: object) -> str:
    """Write hours as 6,412.6, or nothing if there are none."""
    return formatting.hours(value) if isinstance(value, Decimal) else ""


@register.filter
def days(value: object) -> str:
    """Write a number of days as 18 Days, or nothing if there is none."""
    return formatting.amount(Unit.CALENDAR, value) if isinstance(value, int) else ""


@register.filter
def whole(value: object) -> str:
    """Write a whole number as 4,236, or nothing if there is none."""
    return formatting.whole(value) if isinstance(value, int) else ""
