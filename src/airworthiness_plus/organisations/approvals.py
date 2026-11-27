"""The approvals an organisation holds (REQ-200). Views check the role first.

Decisions.md, Canvas Build, decision 1: Part-CAO, Part-CAMO and Part-145.
The approvals held decide which sections the sidebar shows (REQ-201).
"""

from datetime import date

from django.db import IntegrityError, transaction

from airworthiness_plus.organisations.models import (
    Approval,
    ApprovalType,
    Organisation,
    Privilege,
)
from airworthiness_rules.dates import uk_today, utc_now

# The order approvals are listed in: as the regulation's annexes are not, but
# as Decisions.md names them.
ORDER = {value: position for position, value in enumerate(ApprovalType.values)}


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


def every(organisation: Organisation) -> list[Approval]:
    """Return every approval recorded for ``organisation``, held or ended."""
    found = Approval.objects.filter(organisation=organisation)
    return sorted(found, key=lambda one: (one.approval != organisation.approval_type, one.approval))


def held(organisation: Organisation) -> list[Approval]:
    """Return the approvals ``organisation`` holds now, the one it was set up with first."""
    return [one for one in every(organisation) if one.held]


def types_held(organisation: Organisation) -> set[str]:
    """Return which approvals ``organisation`` holds now."""
    return {one.approval for one in held(organisation)}


def may_act_on(
    organisation: Organisation, day: date, approval_type: ApprovalType, cao_privilege: Privilege
) -> bool:
    """Check whether a recorded approval and privilege cover an action on the given day."""
    return any(
        approval.held_on(day)
        and (
            approval.approval == approval_type
            or (
                approval.approval == ApprovalType.PART_CAO
                and cao_privilege in organisation.privileges
            )
        )
        for approval in every(organisation)
    )


# Why an organisation is not offered airworthiness review. CAO.A.095(c) gives
# the privilege to a Part-CAO whose approval includes it.
REVIEW_NOT_OPEN = (
    "Airworthiness Review Is for an Organisation Holding Part-CAO "
    "with the Airworthiness Review Privilege, CAO.A.095(c)"
)
# What the access log says of an action refused for that reason (REQ-009).
REVIEW_REFUSED = "Airworthiness Review Without the Privilege, CAO.A.095(c)"


def review_refusal(organisation: Organisation) -> str:
    """Return why ``organisation`` is not offered airworthiness review, or nothing.

    Airworthiness review staff, reviews and review certificates are for an
    organisation that holds Part-CAO now and whose approval includes the
    airworthiness review privilege (CAO.A.095(c)). The privileges recorded
    are those of a Part-CAO and are set by Airworthiness Limited when the
    organisation is set up. The privileges of a Part-CAMO are not yet
    recorded, so a Part-CAMO is refused until they are (independent review
    of 24 November 2026, finding 10).
    """
    if (
        ApprovalType.PART_CAO in types_held(organisation)
        and Privilege.AIRWORTHINESS_REVIEW in organisation.privileges
    ):
        return ""
    return REVIEW_NOT_OPEN


def _recorded(organisation: Organisation, approval: ApprovalType) -> Approval | None:
    """Return the record of ``approval`` for ``organisation``, held or ended, if there is one."""
    found: Approval | None = Approval.objects.filter(
        organisation=organisation, approval=approval
    ).first()
    return found


@transaction.atomic
def record(organisation: Organisation, *, approval: ApprovalType, reference: str) -> Approval:
    """Record an approval as held, with its reference.

    One that ended is recorded as held again on its own record, so that an
    approval has one record and one history.
    """
    reference = reference.strip()
    if not reference:
        raise RefusedError("An Approval Has Its Reference")
    # One at a time for an organisation: a second submit of the same form waits
    # for the first, then finds the approval recorded and is refused with the
    # reason (independent review of 24 November 2026, finding 14).
    Organisation.objects.select_for_update().get(pk=organisation.pk)
    existing = _recorded(organisation, approval)
    if existing is None:
        try:
            with transaction.atomic():
                return Approval.objects.create(
                    organisation=organisation, approval=approval, reference=reference
                )
        except IntegrityError as error:
            # Recorded by other work all the same. The database holds one record
            # for each approval: refused, never a fault.
            raise RefusedError(f"{approval} Is Already Recorded") from error
    if existing.held:
        raise RefusedError(f"{approval} Is Already Recorded")
    existing.reference = reference
    existing.no_longer_held_on = None
    existing.save(update_fields=["reference", "no_longer_held_on"])
    return existing


def end(approval: Approval, *, on: date) -> None:
    """Record an approval as no longer held from ``on``. The record stays (REQ-131)."""
    if not approval.held:
        raise RefusedError("Already Recorded as No Longer Held")
    if on > uk_today(utc_now()):
        raise RefusedError("No Longer Held From Is Not After Today")
    organisation = Organisation.objects.get(pk=approval.organisation_id)
    if approval.approval == organisation.approval_type:
        raise RefusedError(
            "The Approval the Organisation Was Set Up With Is Changed by Airworthiness Limited"
        )
    approval.no_longer_held_on = on
    approval.save(update_fields=["no_longer_held_on"])
