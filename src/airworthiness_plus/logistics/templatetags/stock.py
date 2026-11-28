"""Show stock quantities exactly, without exponents or trailing zeros (REQ-358)."""

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def amount(value: Decimal | None) -> str:
    """Return 24 for 24.000, 0.5 for 0.500 and 20 for 2E+1."""
    if value is None:
        return ""
    return f"{value.normalize():f}"
