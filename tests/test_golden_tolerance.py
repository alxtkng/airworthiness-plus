"""Golden cases for the Minimum Inspection Programme tolerance.

Rule: UK Regulation (EU) No 1321/2014, ML.A.302(d)(1), read on 18 November
2026. Aeroplanes are inspected every annual or 100-hour interval, whichever
comes first; a tolerance of 1 month or 10 hours may be applied; the next
interval is calculated from when the inspection takes place.

Inputs are in design-system/SampleData.md, "Maintenance Programme Inputs".
SampleData.md does not yet say which aircraft are on the Minimum Inspection
Programme; these cases take G-BXYZ and G-FMNO to be. Today in the sample
world is 18 November 2026.
"""

from datetime import date
from decimal import Decimal

import pytest

from airworthiness_rules.intervals import (
    MINIMUM_INSPECTION_PROGRAMME_INTERVAL,
    MINIMUM_INSPECTION_PROGRAMME_INTERVAL_SAILPLANE,
    MINIMUM_INSPECTION_PROGRAMME_TOLERANCE,
    MINIMUM_INSPECTION_PROGRAMME_TOLERANCE_SAILPLANE,
    Interval,
    Limit,
    Reading,
    TaskKind,
    Tolerance,
    ToleranceNotPermittedError,
    Unit,
    comes_first,
    is_due,
    limits,
    tolerance_outlasts_certificate,
)

TODAY = date(2026, 11, 18)
D = Decimal
INSPECTION = TaskKind.MINIMUM_INSPECTION_PROGRAMME
INTERVAL = MINIMUM_INSPECTION_PROGRAMME_INTERVAL
TOLERANCE = MINIMUM_INSPECTION_PROGRAMME_TOLERANCE

G_BXYZ_DONE = Reading(date(2026, 7, 30), D("3259.0"))
G_FMNO_DONE = Reading(date(2026, 2, 4), D("4912.0"))


def inspection(done: Reading, current: Reading) -> tuple[Limit, ...]:
    return limits(INTERVAL, done, current, kind=INSPECTION, tolerance=TOLERANCE)


def test_the_programme_is_100_hours_or_12_months_with_10_hours_or_1_month() -> None:
    """REQ-048, ML.A.302(d)(1)(a) and (b)."""
    assert INTERVAL == Interval(hours=D("100"), months=12)
    assert TOLERANCE == Tolerance(hours=D("10"), months=1)
    assert MINIMUM_INSPECTION_PROGRAMME_INTERVAL_SAILPLANE == Interval(months=12)
    assert MINIMUM_INSPECTION_PROGRAMME_TOLERANCE_SAILPLANE == Tolerance(months=1)


def test_g_bxyz_tolerance_limits() -> None:
    """REQ-048. Done 30 July 2026 at 3,259.0. Hours: due 3,359.0, so the
    tolerance ends at 3,369.0; now 3,318.0, so 41.0 to the due point and 51.0
    to the end of the tolerance. Calendar: due 30 July 2027 (254 days), so the
    tolerance ends 30 August 2027, 31 days later: 285 days."""
    hours, calendar = inspection(G_BXYZ_DONE, Reading(TODAY, D("3318.0")))
    assert hours == Limit(Unit.HOURS, D("3359.0"), D("41.0"), D("3369.0"), D("51.0"))
    assert calendar == Limit(Unit.CALENDAR, date(2027, 7, 30), 254, date(2027, 8, 30), 285)
    assert not is_due((hours, calendar))
    assert not hours.within_tolerance
    assert not hours.overdue


def test_g_fmno_tolerance_limits() -> None:
    """REQ-048. Done 4 February 2026 at 4,912.0. Hours: due 5,012.0, tolerance
    ends 5,022.0; now 4,950.2, so 61.8 and 71.8. Calendar: due 4 February 2027
    (78 days), tolerance ends 4 March 2027, 28 days later: 106 days."""
    hours, calendar = inspection(G_FMNO_DONE, Reading(TODAY, D("4950.2")))
    assert hours == Limit(Unit.HOURS, D("5012.0"), D("61.8"), D("5022.0"), D("71.8"))
    assert calendar == Limit(Unit.CALENDAR, date(2027, 2, 4), 78, date(2027, 3, 4), 106)


def test_a_tolerance_never_moves_the_due_point() -> None:
    """REQ-056. With and without the tolerance, due and remaining are the same."""
    current = Reading(TODAY, D("3318.0"))
    plain = limits(INTERVAL, G_BXYZ_DONE, current)
    toleranced = inspection(G_BXYZ_DONE, current)
    assert [(found.due, found.remaining) for found in plain] == [
        (found.due, found.remaining) for found in toleranced
    ]


@pytest.mark.parametrize(
    ("hours_now", "remaining", "tolerance_remaining", "within", "overdue"),
    [
        (D("3359.0"), D("0.0"), D("10.0"), False, False),  # reached exactly: due
        (D("3359.1"), D("-0.1"), D("9.9"), True, False),
        (D("3365.0"), D("-6.0"), D("4.0"), True, False),
        (D("3369.0"), D("-10.0"), D("0.0"), True, False),  # end of the tolerance exactly
        (D("3369.1"), D("-10.1"), D("-0.1"), False, True),
    ],
)
def test_g_bxyz_hours_inside_and_past_the_tolerance(
    hours_now: Decimal,
    remaining: Decimal,
    tolerance_remaining: Decimal,
    within: bool,
    overdue: bool,
) -> None:
    """REQ-056. On 1 June 2027 the calendar limit of 30 July 2027 is 59 days
    away (29 left in June, 30 in July). Past 3,359.0 the inspection is due;
    it is overdue only past 3,369.0."""
    found = inspection(G_BXYZ_DONE, Reading(date(2027, 6, 1), hours_now))
    hours, calendar = found
    assert (hours.remaining, hours.tolerance_remaining) == (remaining, tolerance_remaining)
    assert hours.within_tolerance is within
    assert hours.overdue is overdue
    assert is_due(found)
    assert calendar.remaining == 59
    assert comes_first(found, None) == (hours,)


@pytest.mark.parametrize(
    ("today", "remaining", "tolerance_remaining", "within", "overdue"),
    [
        (date(2027, 2, 4), 0, 28, False, False),  # the due date itself
        (date(2027, 2, 5), -1, 27, True, False),
        (date(2027, 2, 20), -16, 12, True, False),  # 8 left in February, 4 in March
        (date(2027, 3, 4), -28, 0, True, False),  # last day of the tolerance
        (date(2027, 3, 5), -29, -1, False, True),
    ],
)
def test_g_fmno_calendar_inside_and_past_the_tolerance(
    today: date, remaining: int, tolerance_remaining: int, within: bool, overdue: bool
) -> None:
    """REQ-056. Due 4 February 2027; the tolerance ends 4 March 2027."""
    found = inspection(G_FMNO_DONE, Reading(today, D("4960.0")))
    calendar = found[1]
    assert (calendar.remaining, calendar.tolerance_remaining) == (remaining, tolerance_remaining)
    assert calendar.within_tolerance is within
    assert calendar.overdue is overdue
    assert is_due(found)


def test_the_next_interval_runs_from_when_the_inspection_was_done() -> None:
    """REQ-048, ML.A.302(d)(1). G-FMNO inspected inside the tolerance on
    20 February 2027 at 4,960.0: next due 20 February 2028 or 5,060.0, not
    4 February 2028 or 5,112.0. Inspected early on 10 January 2027 at 4,955.0:
    next due 10 January 2028 or 5,055.0."""
    late = Reading(date(2027, 2, 20), D("4960.0"))
    hours, calendar = inspection(late, late)
    assert (hours.due, hours.tolerance_limit) == (D("5060.0"), D("5070.0"))
    assert (calendar.due, calendar.tolerance_limit) == (date(2028, 2, 20), date(2028, 3, 20))

    early = Reading(date(2027, 1, 10), D("4955.0"))
    hours, calendar = inspection(early, early)
    assert (hours.due, calendar.due) == (D("5055.0"), date(2028, 1, 10))


def test_an_inspection_done_inside_the_tolerance_shows_that_it_was() -> None:
    """REQ-056. The state at the reading when the inspection was done says
    whether the tolerance was used: G-FMNO on 20 February 2027 was 16 days
    past the calendar limit, with 52.0 hours still to the hours limit."""
    hours, calendar = inspection(G_FMNO_DONE, Reading(date(2027, 2, 20), D("4960.0")))
    assert calendar.within_tolerance
    assert not hours.within_tolerance
    assert hours.remaining == D("52.0")


@pytest.mark.parametrize(
    ("done", "due", "tolerance_ends"),
    [
        (date(2026, 1, 31), date(2027, 1, 31), date(2027, 2, 28)),
        (date(2027, 1, 31), date(2028, 1, 31), date(2028, 2, 29)),  # leap year
        (date(2026, 2, 28), date(2027, 2, 28), date(2027, 3, 28)),
        (date(2026, 12, 31), date(2027, 12, 31), date(2028, 1, 31)),
        (date(2028, 2, 29), date(2029, 2, 28), date(2029, 3, 28)),
    ],
)
def test_the_1_month_tolerance_at_month_ends(done: date, due: date, tolerance_ends: date) -> None:
    """REQ-048, REQ-047. One month after the due date: the same day of the
    next month, or its last day when it is shorter."""
    start = Reading(done, D("0.0"))
    calendar = inspection(start, start)[1]
    assert (calendar.due, calendar.tolerance_limit) == (due, tolerance_ends)


def test_a_sailplane_has_one_calendar_limit_with_1_month() -> None:
    """REQ-048, ML.A.302(d)(1)(b). Done 15 May 2026: due 15 May 2027, 178 days
    from 18 November 2026 (12, 31, 31, 28, 31, 30, 15); the tolerance ends
    15 June 2027, 31 days later: 209 days."""
    found = limits(
        MINIMUM_INSPECTION_PROGRAMME_INTERVAL_SAILPLANE,
        Reading(date(2026, 5, 15), D("812.0")),
        Reading(TODAY, D("840.0")),
        kind=INSPECTION,
        tolerance=MINIMUM_INSPECTION_PROGRAMME_TOLERANCE_SAILPLANE,
    )
    assert found == (Limit(Unit.CALENDAR, date(2027, 5, 15), 178, date(2027, 6, 15), 209),)


@pytest.mark.parametrize(
    "kind",
    [
        TaskKind.AIRWORTHINESS_DIRECTIVE,
        TaskKind.AIRWORTHINESS_LIMITATION,
        TaskKind.LIFE_LIMIT,
        TaskKind.PROGRAMME_TASK,
        None,
    ],
)
def test_a_tolerance_is_refused_for_anything_but_the_minimum_inspection_programme(
    kind: TaskKind | None,
) -> None:
    """REQ-049. ML.A.303: a directive is carried out within its own
    requirements. GM1 ML.A.302(c)(4): intervals of mandatory continuing
    airworthiness information cannot be extended. ML.A.302(d)(1) gives a
    tolerance to the Minimum Inspection Programme only. With no kind stated,
    nothing is assumed."""
    current = Reading(TODAY, D("3318.0"))
    with pytest.raises(ToleranceNotPermittedError):
        limits(INTERVAL, G_BXYZ_DONE, current, kind=kind, tolerance=TOLERANCE)


@pytest.mark.parametrize(
    "tolerance",
    [Tolerance(hours=D("10.1")), Tolerance(months=2), Tolerance(hours=D("5"), months=2)],
)
def test_a_tolerance_above_1_month_or_10_hours_is_refused(tolerance: Tolerance) -> None:
    """REQ-049, ML.A.302(d)(1)."""
    current = Reading(TODAY, D("3318.0"))
    with pytest.raises(ToleranceNotPermittedError, match="at most"):
        limits(INTERVAL, G_BXYZ_DONE, current, kind=INSPECTION, tolerance=tolerance)


def test_a_tolerance_needs_a_positive_amount() -> None:
    """REQ-048."""
    with pytest.raises(ValueError, match="at least one"):
        Tolerance()
    with pytest.raises(ValueError, match="greater than zero"):
        Tolerance(hours=D("0"))


def test_every_kind_is_calculated_without_a_tolerance() -> None:
    """REQ-049, REQ-065. A directive or a limitation is due at its limit and
    overdue the moment it is passed."""
    for kind in TaskKind:
        (hours,) = limits(
            Interval(hours=D("50")),
            Reading(TODAY, D("100.0")),
            Reading(TODAY, D("150.1")),
            kind=kind,
        )
        assert hours.tolerance_limit is None
        assert hours.overdue
        assert not hours.within_tolerance


def test_g_bxyz_tolerance_ends_after_the_review_certificate() -> None:
    """REQ-057, AMC1 ML.A.302(d). G-BXYZ: the calendar tolerance ends
    30 August 2027; the review certificate is valid to 2 August 2027, so
    using the tolerance in full would pass the end of the certificate."""
    hours, calendar = inspection(G_BXYZ_DONE, Reading(TODAY, D("3318.0")))
    assert tolerance_outlasts_certificate(calendar, date(2027, 8, 2))
    assert not tolerance_outlasts_certificate(calendar, date(2027, 8, 30))
    assert not tolerance_outlasts_certificate(hours, date(2027, 8, 2))


def test_g_fmno_tolerance_ends_before_the_review_certificate() -> None:
    """REQ-057. G-FMNO: the calendar tolerance ends 4 March 2027; the review
    certificate is valid to 27 April 2027."""
    calendar = inspection(G_FMNO_DONE, Reading(TODAY, D("4950.2")))[1]
    assert not tolerance_outlasts_certificate(calendar, date(2027, 4, 27))
