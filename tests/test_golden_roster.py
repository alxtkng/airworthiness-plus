"""Worked cases from the Staff Roster and Load and Capacity boards."""

from datetime import UTC, datetime
from decimal import Decimal


def test_november_shift_and_rest() -> None:
    from airworthiness_plus.staffing.roster_rules import active_minutes, gap_minutes

    starts = datetime(2026, 11, 19, 8, tzinfo=UTC)
    ends = datetime(2026, 11, 19, 19, tzinfo=UTC)
    next_start = datetime(2026, 11, 20, 8, tzinfo=UTC)
    assert active_minutes(starts, ends, 30) == 630
    assert gap_minutes(ends, next_start) == 780


def test_hour_across_british_summer_time_measures_elapsed_time() -> None:
    from zoneinfo import ZoneInfo

    from airworthiness_plus.staffing.roster_rules import active_minutes

    london = ZoneInfo("Europe/London")
    starts = datetime(2026, 10, 25, 0, tzinfo=london)
    ends = datetime(2026, 10, 25, 8, tzinfo=london)
    assert active_minutes(starts, ends, 30) == 510


def test_wednesday_employed_share() -> None:
    from airworthiness_plus.staffing.roster_rules import employed_share

    assert employed_share(2, 2) == (50, False)
    assert employed_share(2, 1) == (67, False)
    assert employed_share(1, 2) == (33, True)
    assert employed_share(0, 0) == (None, False)


def test_november_workload_and_efficiency_margin() -> None:
    from airworthiness_plus.staffing.roster_rules import workload

    assert workload(Decimal("20"), Decimal("50"), Decimal("122.5"), 85) == (57, False)
    assert workload(Decimal("35"), Decimal("50"), Decimal("100"), 85) == (85, True)
    assert workload(Decimal("20"), Decimal("50"), Decimal("0"), 85) == (None, True)
