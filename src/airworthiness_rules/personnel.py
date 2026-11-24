"""How long the record of a person who has left is kept (REQ-206).

Read in the UK text in the Civil Aviation Authority Regulatory Library on
24 November 2026:

- CAO.A.045(e): a Part-CAO retains the record of its airworthiness review
  staff "for a period of at least 2 years after the date at which the
  person concerned no longer works for the CAO".
- CAMO.A.220, Personnel Records: "retained until 3 years after the person
  has left the organisation".
- 145.A.55, Personnel Records: "retained for 3 years after the person has
  left the organisation".
- CAO.A.035(e) has a Part-CAO assess and record the qualification of all
  personnel and gives no period, so none is given here for the other
  staff of an organisation that holds Part-CAO alone.

Ours, not the regulation's: the Part-CAMO and Part-145 periods are applied
to every person of an organisation that holds the approval, whatever the
person did; where more than one period applies the longer is shown; and a
period that is a minimum is never cut a day short, so a person who left
on 29 February is kept until 1 March of a year that has no 29 February.

The system itself never deletes a record. The day is shown so that the
organisation knows the least it must keep.
"""

from collections.abc import Set
from dataclasses import dataclass
from datetime import date

from airworthiness_rules.dates import BeyondCalendarError

PART_CAO = "Part-CAO"
PART_CAMO = "Part-CAMO"
PART_145 = "Part-145"

REVIEW_STAFF_YEARS = 2  # CAO.A.045(e)
PERSONNEL_YEARS = 3  # CAMO.A.220 and 145.A.55, Personnel Records


@dataclass(frozen=True)
class Retention:
    """The day a former person's record is kept until, the years and the source."""

    until: date
    years: int
    source: str


def _years_after(left: date, years: int) -> date:
    """Return the same day ``years`` years on, or 1 March where there is no 29 February."""
    if left.year + years > date.max.year:
        raise BeyondCalendarError(f"{years} years after {left} is not a date")
    try:
        return left.replace(year=left.year + years)
    except ValueError:
        return date(left.year + years, 3, 1)


def record_kept_until(left: date, *, approvals: Set[str], review_staff: bool) -> Retention | None:
    """Return the day the record of a person who left on ``left`` is kept until.

    ``approvals`` are those the organisation holds. With no period given
    for the person by any of them, nothing is returned.
    """
    sources = [
        name
        for approval, name in ((PART_CAMO, "CAMO.A.220"), (PART_145, "145.A.55"))
        if approval in approvals
    ]
    if sources:
        return Retention(
            _years_after(left, PERSONNEL_YEARS),
            PERSONNEL_YEARS,
            f"{' and '.join(sources)}, Personnel Records",
        )
    if review_staff and PART_CAO in approvals:
        return Retention(_years_after(left, REVIEW_STAFF_YEARS), REVIEW_STAFF_YEARS, "CAO.A.045(e)")
    return None
