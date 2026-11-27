"""Property tests for the arithmetic of Phase 3, Planning.

The golden cases in `test_golden_staffing.py` and `test_golden_roster.py` fix
the sample's figures. These check that the rules hold for any input
(`prompts/canvas-build.md`, Part 4, step 5): the Staffing Plan shortfall and
its Part-145 threshold (REQ-324 to REQ-326), the roster's elapsed time and
weekly split (REQ-328, REQ-332), the employed share and the load warning
(REQ-330, REQ-331).
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from hypothesis import assume, given
from hypothesis import strategies as st

from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_plus.staffing import roster_rules, rules

LONDON = ZoneInfo("Europe/London")

hours = st.decimals(min_value=0, max_value=5000, places=1, allow_nan=False, allow_infinity=False)
positive_hours = st.decimals(
    min_value=Decimal("0.1"), max_value=5000, places=1, allow_nan=False, allow_infinity=False
)
approvals = st.sampled_from(list(ApprovalType.values))
days = st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31))
# Hypothesis takes naive bounds and adds the time zone itself.
instants = st.datetimes(
    min_value=datetime(2020, 1, 1),  # noqa: DTZ001
    max_value=datetime(2035, 12, 31),  # noqa: DTZ001
    timezones=st.just(UTC),
)


@given(needed=hours, employed=hours, contracted=hours, approval=approvals)
def test_the_shortfall_is_what_the_hours_available_leave_uncovered(
    needed: Decimal, employed: Decimal, contracted: Decimal, approval: str
) -> None:
    """REQ-324. Never below nothing, and never more than the hours needed."""
    found = rules.assess(needed=needed, employed=employed, contracted=contracted, approval=approval)
    assert found.available == employed + contracted
    assert found.shortfall == max(Decimal("0"), needed - employed - contracted)
    assert 0 <= found.shortfall <= needed
    assert 0 <= found.display_percent <= 100


@given(needed=hours, employed=hours, contracted=hours, more=positive_hours, approval=approvals)
def test_more_cover_never_makes_the_shortfall_worse(
    needed: Decimal, employed: Decimal, contracted: Decimal, more: Decimal, approval: str
) -> None:
    """REQ-324. Contracted cover only ever reduces the shortfall."""
    before = rules.assess(
        needed=needed, employed=employed, contracted=contracted, approval=approval
    )
    after = rules.assess(
        needed=needed, employed=employed, contracted=contracted + more, approval=approval
    )
    assert after.shortfall <= before.shortfall
    assert after.reportable <= before.reportable


@given(needed=positive_hours, employed=hours, contracted=hours, approval=approvals)
def test_only_a_part_145_shortfall_over_25_percent_is_reportable(
    needed: Decimal, employed: Decimal, contracted: Decimal, approval: str
) -> None:
    """REQ-325, AMC1 145.A.30(d). Exactly 25 percent is not over it."""
    found = rules.assess(needed=needed, employed=employed, contracted=contracted, approval=approval)
    over = found.shortfall / needed > Decimal("0.25")
    assert found.reportable == (approval == ApprovalType.PART_145 and over)


@given(needed=st.integers(min_value=1, max_value=5000), approval=approvals)
def test_the_threshold_at_its_edge(needed: int, approval: str) -> None:
    """REQ-325. A quarter of the hours short is not reported; a tenth of an hour more is."""
    need = Decimal(needed) * 4
    at_edge = rules.assess(needed=need, employed=need - needed, contracted=Decimal("0"),
                           approval=approval)  # fmt: skip
    past_edge = rules.assess(
        needed=need, employed=need - needed - Decimal("0.1"), contracted=Decimal("0"),
        approval=approval,
    )  # fmt: skip
    assert not at_edge.reportable
    assert past_edge.reportable == (approval == ApprovalType.PART_145)


@given(reviewed=days, approval=approvals)
def test_a_part_145_plan_is_reviewed_within_three_calendar_months(
    reviewed: date, approval: str
) -> None:
    """REQ-326, AMC1 145.A.30(d). Other approvals have no fixed period."""
    due = rules.required_review_by(reviewed, approval)
    if approval != ApprovalType.PART_145:
        assert due is None
        return
    assert due is not None
    assert 89 <= (due - reviewed).days <= 92
    months = (due.year - reviewed.year) * 12 + due.month - reviewed.month
    assert months == 3
    assert due.day <= reviewed.day


@given(day=days)
def test_a_week_starts_on_the_monday_on_or_before_the_day(day: date) -> None:
    """REQ-330."""
    monday = roster_rules.week_of(day)
    assert monday.weekday() == 0
    assert 0 <= (day - monday).days <= 6


@given(
    starts=instants,
    length=st.integers(min_value=1, max_value=24 * 60),
    break_minutes=st.integers(min_value=0, max_value=120),
    split=st.integers(min_value=0, max_value=24 * 60),
)
def test_a_shift_split_at_any_moment_adds_up_to_its_working_minutes(
    starts: datetime, length: int, break_minutes: int, split: int
) -> None:
    """REQ-332. A shift across a week boundary is counted once, in two parts."""
    assume(break_minutes < length)
    ends = starts + timedelta(minutes=length)
    boundary = starts + timedelta(minutes=min(split, length))
    early = datetime(2000, 1, 1, tzinfo=UTC)
    late = datetime(2100, 1, 1, tzinfo=UTC)
    first = roster_rules.minutes_in_window(starts, ends, break_minutes, early, boundary)
    second = roster_rules.minutes_in_window(starts, ends, break_minutes, boundary, late)
    whole = roster_rules.active_minutes(starts, ends, break_minutes)
    assert whole == length - break_minutes
    assert first >= 0 and second >= 0
    assert first + second == whole


@given(day=st.dates(min_value=date(2020, 1, 1), max_value=date(2035, 12, 31)))
def test_elapsed_time_is_kept_across_a_clock_change(day: date) -> None:
    """REQ-328. 22:00 to 06:00 UK time is 8 hours, or 7 or 9 on the nights the clocks change."""
    starts = datetime(day.year, day.month, day.day, 22, 0, tzinfo=LONDON)
    following = day + timedelta(days=1)
    ends = datetime(following.year, following.month, following.day, 6, 0, tzinfo=LONDON)
    shift = (starts.utcoffset() or timedelta()) - (ends.utcoffset() or timedelta())
    expected = 8 * 60 + int(shift.total_seconds() // 60)
    assert roster_rules.gap_minutes(starts, ends) == expected
    assert expected in (7 * 60, 8 * 60, 9 * 60)


@given(employed=st.integers(min_value=0, max_value=200), contracted=st.integers(0, 200))
def test_the_employed_share_is_a_whole_percent_and_flags_a_contracted_majority(
    employed: int, contracted: int
) -> None:
    """REQ-330, AMC1 145.A.30(d). Half and half is not flagged."""
    share, flagged = roster_rules.employed_share(employed, contracted)
    if employed + contracted == 0:
        assert (share, flagged) == (None, False)
        return
    assert share is not None
    assert 0 <= share <= 100
    assert flagged == (employed < contracted)
    other, _ = roster_rules.employed_share(contracted, employed)
    assert other is not None
    assert share + other in (100, 101)


@given(
    package=hours,
    other=hours,
    more=positive_hours,
    available=positive_hours,
    margin=st.integers(min_value=1, max_value=200),
)
def test_more_planned_work_never_lowers_the_load(
    package: Decimal, other: Decimal, more: Decimal, available: Decimal, margin: int
) -> None:
    """REQ-330, REQ-331. The warning is at the margin, inclusive, and stays on as work is added."""
    percent, warned = roster_rules.workload(package, other, available, margin)
    heavier, heavier_warned = roster_rules.workload(package + more, other, available, margin)
    assert percent is not None and heavier is not None
    assert heavier >= percent
    assert warned == ((package + other) * 100 / available >= margin)
    assert heavier_warned >= warned


@given(package=hours, other=hours, margin=st.integers(min_value=1, max_value=200))
def test_with_no_hours_available_any_work_is_a_warning(
    package: Decimal, other: Decimal, margin: int
) -> None:
    """REQ-330. No percentage can be given; work with nobody to do it is flagged."""
    assert roster_rules.workload(package, other, Decimal("0"), margin) == (
        None,
        package + other > 0,
    )


@given(margin=st.integers(min_value=1, max_value=200), available=st.integers(1, 500))
def test_the_load_warning_is_at_its_margin_and_not_before(margin: int, available: int) -> None:
    """REQ-331, decision 6. The 85% default is inclusive: at the margin the warning shows."""
    capacity = Decimal(available)
    at_margin = capacity * margin / 100
    assert roster_rules.workload(at_margin, Decimal("0"), capacity, margin)[1]
    below = at_margin - Decimal("0.01")
    assert not roster_rules.workload(below, Decimal("0"), capacity, margin)[1]
