"""Golden cases and properties for the mass change since a weighing (REQ-255, REQ-256).

Worked by hand from design-system/SampleData.md, Modifications and Repairs
and Weight and Balance. ML.A.305(d) was read in the UK text on 27 November
2026. The reweigh threshold is the organisation's own: no rule read gives
one.

- G-BXYZ, weighed 14 June 2019: the navigator of 12 October 2026, +1.2
  Kilograms. Net +1.2.
- G-FMNO, weighed 5 April 2018: the landing light of 14 April 2026, 0.3
  lighter. Net 0.3 lighter. Issue 5 of its schedule is dated 20 April 2026,
  so the light is in the schedule.
- G-ABCD, weighed 20 May 2022: the transponder of 10 May 2022 was on the
  aircraft when it was weighed. Net 0.0.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_rules import mass as rules

D = Decimal


def test_a_change_counts_from_the_day_after_the_weighing() -> None:
    """REQ-255. Embodied on the day of the weighing, or before, it was weighed with
    the aircraft; the day after, it is a change since."""
    weighed = date(2022, 5, 20)
    assert not rules.counted_since(date(2022, 5, 10), weighed)
    assert not rules.counted_since(weighed, weighed)
    assert rules.counted_since(date(2022, 5, 21), weighed)
    assert rules.counted_since(date(2026, 10, 12), date(2019, 6, 14))


def test_the_net_change_is_the_sum_with_each_sign() -> None:
    """REQ-255. The sample's, and a case of several: 1.2 and 0.4 heavier and 0.3
    lighter is 1.3 heavier, exactly."""
    assert rules.net_change([D("1.2")]) == D("1.2")
    assert rules.net_change([D("-0.3")]) == D("-0.3")
    assert rules.net_change([]) == D("0.0")
    assert rules.net_change([D("1.2"), D("0.4"), D("-0.3")]) == D("1.3")
    assert rules.net_change([D("0.1"), D("0.2")]) == D("0.3")
    assert rules.net_change([D("999.9"), D("-999.9")]) == D("0.0")
    with pytest.raises(ValueError, match=r"at most 999\.9"):
        rules.net_change([D("1000.0")])


def test_a_change_is_in_the_schedule_once_an_issue_is_dated_on_or_after_it() -> None:
    """REQ-256. G-FMNO's light of 14 April 2026 is in Issue 5 of 20 April 2026.
    G-BXYZ's navigator of 12 October 2026 is not in Issue 6 of 14 June 2019."""
    assert rules.in_schedule(date(2026, 4, 14), date(2026, 4, 20))
    assert rules.in_schedule(date(2026, 4, 14), date(2026, 4, 14))
    assert not rules.in_schedule(date(2026, 4, 14), date(2026, 4, 13))
    assert not rules.in_schedule(date(2026, 10, 12), date(2019, 6, 14))
    assert not rules.in_schedule(date(2026, 10, 12), None)


def test_over_the_threshold_at_its_edges() -> None:
    """REQ-256. Ours: over is more than, by size, whichever way the mass has gone.
    With no threshold set nothing is over it."""
    assert not rules.over_threshold(D("1.2"), None)
    assert not rules.over_threshold(D("999.9"), None)
    assert not rules.over_threshold(D("1.2"), D("1.2"))
    assert rules.over_threshold(D("1.2"), D("1.1"))
    assert rules.over_threshold(D("-1.2"), D("1.1"))
    assert not rules.over_threshold(D("-1.2"), D("1.2"))
    assert not rules.over_threshold(D("0.0"), D("0.1"))
    with pytest.raises(ValueError, match="above zero"):
        rules.over_threshold(D("1.2"), D("0"))


EFFECTS = st.integers(min_value=-9_999, max_value=9_999).map(lambda n: Decimal(n) / 10)
THRESHOLDS = st.integers(min_value=1, max_value=9_999).map(lambda n: Decimal(n) / 10)
DATES = st.dates(min_value=date(1950, 1, 1), max_value=date(2100, 12, 31))


@given(st.lists(EFFECTS, max_size=30), st.lists(EFFECTS, max_size=30))
def test_the_net_change_does_not_depend_on_order_or_grouping(
    first: list[Decimal], second: list[Decimal]
) -> None:
    both = rules.net_change(first + second)
    assert both == rules.net_change(second + first)
    assert both == rules.net_change(first) + rules.net_change(second)
    assert both == sum(first + second, D("0.0"))


@given(st.lists(EFFECTS, max_size=30))
def test_undoing_every_change_leaves_nothing(effects: list[Decimal]) -> None:
    assert rules.net_change(effects + [-effect for effect in effects]) == 0


@given(EFFECTS, THRESHOLDS)
def test_the_threshold_looks_only_at_size(net: Decimal, threshold: Decimal) -> None:
    assert rules.over_threshold(net, threshold) == rules.over_threshold(-net, threshold)
    assert rules.over_threshold(net, threshold) == (abs(net) > threshold)
    assert not rules.over_threshold(net, None)


@given(DATES, st.integers(min_value=-500, max_value=500))
def test_a_change_is_either_weighed_with_the_aircraft_or_since(weighed: date, offset: int) -> None:
    embodied = weighed + timedelta(days=offset)
    assert rules.counted_since(embodied, weighed) == (offset > 0)
    assert rules.in_schedule(embodied, weighed) == (offset <= 0)
