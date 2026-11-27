"""Hand-worked cases from the Plan and Plan Settings boards."""

from datetime import date
from decimal import Decimal

import pytest

from airworthiness_plus.organisations.models import ApprovalType

D = Decimal


def test_december_certifying_staff_before_and_after_cover() -> None:
    """98 / 290 rounds to 34%, and 10 / 290 rounds to 3%."""
    from airworthiness_plus.staffing.rules import assess

    first = assess(
        needed=D("290"), employed=D("192"), contracted=D("0"), approval=ApprovalType.PART_145
    )
    second = assess(
        needed=D("290"), employed=D("192"), contracted=D("88"), approval=ApprovalType.PART_145
    )
    assert (first.shortfall, first.display_percent, first.reportable) == (D("98"), 34, True)
    assert (second.shortfall, second.display_percent, second.reportable) == (D("10"), 3, False)


@pytest.mark.parametrize("approval", [ApprovalType.PART_CAO, ApprovalType.PART_CAMO])
def test_each_approval_shows_the_shortfall_without_part_145_thresholds(
    approval: ApprovalType,
) -> None:
    """CAO.A.035(d) and CAMO.A.305(d) require adequate staff."""
    from airworthiness_plus.staffing.rules import assess, required_review_by

    result = assess(needed=D("40"), employed=D("0"), contracted=D("0"), approval=approval)
    assert result.shortfall == D("40")
    assert not result.reportable
    assert required_review_by(date(2026, 9, 2), approval) is None


def test_part_145_exact_threshold_and_three_calendar_months() -> None:
    from airworthiness_plus.staffing.rules import assess, required_review_by

    assert not assess(
        needed=D("100"),
        employed=D("75"),
        contracted=D("0"),
        approval=ApprovalType.PART_145,
    ).reportable
    assert assess(
        needed=D("100"),
        employed=D("74.9"),
        contracted=D("0"),
        approval=ApprovalType.PART_145,
    ).reportable
    assert required_review_by(date(2026, 9, 2), ApprovalType.PART_145) == date(2026, 12, 2)
    assert required_review_by(date(2026, 11, 30), ApprovalType.PART_145) == date(2027, 2, 28)
