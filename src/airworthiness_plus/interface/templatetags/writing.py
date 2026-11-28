"""Template filters for the writing rules (REQ-192).

A value that is missing is written as nothing. A template passes an empty
string, not None, for a value that is not there.
"""

from datetime import date, datetime
from decimal import Decimal

from django import template
from django.utils.html import format_html

from airworthiness_plus.interface import formatting
from airworthiness_rules.intervals import Unit

register = template.Library()


@register.filter
def long_date(value: object) -> str:
    """Write a date as 18 November 2026, or nothing if there is none."""
    return formatting.long_date(value) if isinstance(value, date) else ""


@register.filter
def status(value: object) -> str:
    """Write a status as its word, with a dot beside it where one is called for (REQ-193)."""
    word = str(value) if value is not None else ""
    mark = formatting.STATUS_MARKS.get(word)
    if mark is None:
        return word
    return format_html('<span class="status status-{}">{}</span>', mark, word)


@register.filter
def moment(value: object) -> str:
    """Write a time in United Kingdom time, or nothing if there is none."""
    return formatting.moment(value) if isinstance(value, datetime) else ""


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


@register.filter
def stock_quantity(value: object) -> str:
    """An exact Stores quantity, with no trailing zeros and never in exponent form."""
    if value is None or value == "":
        return ""
    text = f"{Decimal(str(value)):f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
