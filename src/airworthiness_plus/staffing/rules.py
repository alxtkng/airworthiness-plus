"""Staffing adequacy for each approval and the Part-145 reporting threshold."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_rules.dates import add_months


@dataclass(frozen=True)
class Assessment:
    available: Decimal
    shortfall: Decimal
    display_percent: int
    reportable: bool


def assess(*, needed: Decimal, employed: Decimal, contracted: Decimal, approval: str) -> Assessment:
    """Compare usable hours with the work to be staffed in a calendar month."""
    available = employed + contracted
    shortfall = max(Decimal("0"), needed - available)
    percent = shortfall * 100 / needed if needed else Decimal("0")
    return Assessment(
        available=available,
        shortfall=shortfall,
        display_percent=int(percent.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        reportable=approval == ApprovalType.PART_145 and shortfall * 4 > needed,
    )


def required_review_by(reviewed_on: date, approval: str) -> date | None:
    """The three-calendar-month review period in AMC1 145.A.30(d)."""
    return add_months(reviewed_on, 3) if approval == ApprovalType.PART_145 else None
