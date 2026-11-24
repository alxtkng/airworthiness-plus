"""What an organisation sets for itself (REQ-211 to REQ-214). Views check the role first.

Decisions.md, Canvas Build, decision 4. None of these numbers is the
regulation's. The lead times say how close a limit must be to show as Due
Soon. The deferral limits are the organisation's own defaults for a
deferred defect: ML.A.403(b) says who may defer, and ML.A.403(c) that the
defect is rectified within the limits specified in the maintenance data,
which apply when they are shorter.
"""

from dataclasses import dataclass
from decimal import Decimal

from airworthiness_plus.organisations.models import Organisation

# Ours, not the regulation's: the most a lead time or a default limit may be
# (REQ-212 to REQ-214). Held here, by the form and by the database, so that no
# caller can store more (independent recompute of 24 November 2026).
MOST_DAYS = 365
MOST_HOURS = Decimal("999.9")
MOST_CYCLES = 9999


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


def change_details(organisation: Organisation, *, name: str, address: str) -> None:
    """Change the name and address of the organisation (REQ-211)."""
    name = name.strip()
    if not name:
        raise RefusedError("An Organisation Has a Name")
    organisation.name = name
    organisation.address = address.strip()
    organisation.save(update_fields=["name", "address"])


def set_lead_times(
    organisation: Organisation,
    *,
    due_soon_days: int,
    due_soon_hours: Decimal,
    due_soon_cycles: int,
    review_alert_days: int | None,
) -> None:
    """Set how close a limit must be to show as Due Soon (REQ-212, REQ-213).

    ``review_alert_days`` is the earlier alert for airworthiness review
    certificates, or nothing when the organisation has not turned one on.
    """
    if due_soon_days < 0 or due_soon_hours < 0 or due_soon_cycles < 0:
        raise RefusedError("A Lead Time Is Not Below Zero")
    if due_soon_days > MOST_DAYS or due_soon_hours > MOST_HOURS or due_soon_cycles > MOST_CYCLES:
        raise RefusedError("A Lead Time Is at Most 365 Days, 999.9 Hours or 9,999 Cycles")
    if review_alert_days is not None and review_alert_days <= due_soon_days:
        raise RefusedError("The Earlier Alert Is More Days Than the Calendar Lead Time")
    if review_alert_days is not None and review_alert_days > MOST_DAYS:
        raise RefusedError("The Earlier Alert Is at Most 365 Days")
    organisation.due_soon_days = due_soon_days
    organisation.due_soon_hours = due_soon_hours
    organisation.due_soon_cycles = due_soon_cycles
    organisation.review_alert_days = review_alert_days
    organisation.save(
        update_fields=["due_soon_days", "due_soon_hours", "due_soon_cycles", "review_alert_days"]
    )


def set_deferral_limits(
    organisation: Organisation,
    *,
    deferral_days_non_required: int,
    deferral_days_with_agreement: int,
    deferral_days_certifying_staff: int,
) -> None:
    """Set the organisation's default limits for a deferred defect, in days (REQ-214)."""
    limits = (
        deferral_days_non_required,
        deferral_days_with_agreement,
        deferral_days_certifying_staff,
    )
    if min(limits) < 1:
        raise RefusedError("A Default Limit Is at Least 1 Day")
    if max(limits) > MOST_DAYS:
        raise RefusedError("A Default Limit Is at Most 365 Days")
    organisation.deferral_days_non_required = deferral_days_non_required
    organisation.deferral_days_with_agreement = deferral_days_with_agreement
    organisation.deferral_days_certifying_staff = deferral_days_certifying_staff
    organisation.save(
        update_fields=[
            "deferral_days_non_required",
            "deferral_days_with_agreement",
            "deferral_days_certifying_staff",
        ]
    )


@dataclass(frozen=True)
class DeferralLine:
    """One line of the Deferral Limits table: who decides, for what, the limit and the point."""

    decision_by: str
    applies_to: str
    limit: str
    point: str


def deferral_lines(organisation: Organisation) -> tuple[DeferralLine, ...]:
    """Return the four decisions of ML.A.403(b) with the organisation's default for each.

    The minimum equipment list gives its own limit, so none is set for it.
    """

    def days(value: int) -> str:
        return f"{value} Day" if value == 1 else f"{value} Days"

    return (
        DeferralLine(
            "Pilot-in-Command",
            "Defects on Non-Required Equipment",
            days(organisation.deferral_days_non_required),
            "ML.A.403(b)(1)",
        ),
        DeferralLine(
            "Pilot-in-Command, Minimum Equipment List",
            "Required Equipment Listed in the Minimum Equipment List",
            "Limit Given in the Minimum Equipment List",
            "ML.A.403(b)(2)",
        ),
        DeferralLine(
            "Pilot-in-Command, With Agreement",
            "Other Defects, Part-NCO, Owner or Organisation Agrees",
            days(organisation.deferral_days_with_agreement),
            "ML.A.403(b)(3)",
        ),
        DeferralLine(
            "Certifying Staff",
            "Other Defects",
            days(organisation.deferral_days_certifying_staff),
            "ML.A.403(b)(4)",
        ),
    )
