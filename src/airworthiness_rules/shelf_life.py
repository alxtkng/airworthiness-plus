"""Shelf-life status of stock from the manufacturer's recorded basis (REQ-358).

A shelf-life date means nothing on its own: the label or instructions say
whether the item may be used through that date or only until the start of
it. The basis is recorded with the date, so the last day of use is never
inferred from the date alone. With no basis the status is Unknown, and
Unknown stock is not available for use.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from airworthiness_rules.dates import days_between


class Basis(StrEnum):
    """How the recorded date bounds use, or that no shelf life applies."""

    THROUGH = "Usable Through the Date"
    BEFORE = "Expires at the Start of the Date"
    NOT_APPLICABLE = "Not Applicable"


class Status(StrEnum):
    CURRENT = "Current"
    DUE_SOON = "Due Soon"
    EXPIRED = "Expired"
    UNKNOWN = "Unknown"
    NOT_APPLICABLE = "Not Applicable"


@dataclass(frozen=True)
class ShelfLife:
    status: Status
    last_day: date | None = None
    days_left: int | None = None

    @property
    def usable(self) -> bool:
        """Return whether the shelf-life check passes on the day evaluated."""
        return self.status in (Status.CURRENT, Status.DUE_SOON, Status.NOT_APPLICABLE)


def last_day_of_use(basis: str, limit: date | None) -> date | None:
    """Return the last whole day of use, or None when there is none to compute."""
    if limit is None:
        return None
    if basis == Basis.THROUGH:
        return limit
    if basis == Basis.BEFORE:
        return limit - timedelta(days=1)
    return None


def evaluate(basis: str, limit: date | None, day: date, warning_days: int) -> ShelfLife:
    """Return the status on ``day`` with a warning ``warning_days`` before the last day.

    Due Soon starts when the days left to the last day of use are no more than
    ``warning_days``, and lasts through the last day itself. The next day is
    Expired.
    """
    if warning_days < 0:
        raise ValueError("The warning lead time cannot be negative")
    if basis == Basis.NOT_APPLICABLE:
        return ShelfLife(Status.NOT_APPLICABLE)
    last = last_day_of_use(basis, limit)
    if last is None:
        return ShelfLife(Status.UNKNOWN)
    left = days_between(day, last)
    if left < 0:
        return ShelfLife(Status.EXPIRED, last, left)
    if left <= warning_days:
        return ShelfLife(Status.DUE_SOON, last, left)
    return ShelfLife(Status.CURRENT, last, left)
