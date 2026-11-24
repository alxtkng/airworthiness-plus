"""The approvals an organisation holds (REQ-200). Views check the role first.

Decisions.md, Canvas Build, decision 1: Part-CAO, Part-CAMO and Part-145.
The approvals held decide which sections the sidebar shows (REQ-201).
"""

from datetime import date

from django.db import transaction

from airworthiness_plus.organisations.models import Approval, ApprovalType, Organisation
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


@transaction.atomic
def record(organisation: Organisation, *, approval: ApprovalType, reference: str) -> Approval:
    """Record an approval as held, with its reference.

    One that ended is recorded as held again on its own record, so that an
    approval has one record and one history.
    """
    reference = reference.strip()
    if not reference:
        raise RefusedError("An Approval Has Its Reference")
    existing = Approval.objects.filter(organisation=organisation, approval=approval).first()
    if existing is None:
        return Approval.objects.create(
            organisation=organisation, approval=approval, reference=reference
        )
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
