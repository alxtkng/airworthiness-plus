"""Fictitious board examples for the marked Part-CAO sample site."""

from datetime import date
from uuid import NAMESPACE_URL, UUID, uuid5

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics.services import maintenance_approvals
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.tooling.models import (
    ControlKind,
    EventKind,
    Tool,
    ToolAction,
    ToolControlEvent,
    ToolControlRevision,
    ToolDelegation,
)

DAY = date(2026, 11, 18)
SITE = "Hangar"
LOAN_NOTES = (
    "Access can be arranged through the lender. Verify the applicable task and revision, "
    "actual kit and sensor IDs, equipment maker's instructions and evidence for the actual loan."
)
WRENCH_NOTES = (
    "Canvas source claims: C05 despatch 1 September and G-ABCD use 12 September 2026 "
    "conflict. The old control anniversary would be 12 September. Verify the actual label "
    "and custody. Confirm whether 0143 covered the applicable recheck setting and method. "
    "The G-FMNO no-effect claim needs signed task and verification evidence. Verify the "
    "September certificate's serial, scope, limits, traceability and acceptance before use."
)


def submission(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"airworthiness-plus/sample/tools/{key}")


def add(organisation: Organisation, administrator: User) -> int:
    """Add missing fictitious examples without modifying existing records."""
    with working_for(organisation.pk, administrator.pk), transaction.atomic():
        organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
        if organisation.approval_reference != "UK.CAO.[Number]":
            return 0
        term = next(
            (
                approval
                for approval in maintenance_approvals(organisation, DAY)
                if approval.approval == ApprovalType.PART_CAO
            ),
            None,
        )
        reference = term.reference_on(DAY) if term else None
        person = (
            Person.objects.select_related("user")
            .filter(user__username="lucy.grant@your-organisation.example", user__is_active=True)
            .first()
        )
        if not reference or person is None or person.user is None:
            return 0
        records = {
            "0201": ("Grease Gun", "Tool Board 1", "", "", ""),
            "0210": ("Hydraulic Aircraft Jack", "Segregated, Bay 2", "3 tonnes", "", ""),
            "0301": ("Jack Point Adapter", "Tool Board 2", "", "", ""),
            "0142": ("Torque Wrench", "Tool Board", "20 to 100 Nm", "", WRENCH_NOTES),
            "LOAN-01": (
                "Propeller Dynamic Balancing Kit",
                "Occasional access",
                "",
                "[Propeller Organisation]",
                LOAN_NOTES,
            ),
        }
        missing = {
            asset: entry
            for asset, entry in records.items()
            if not Tool.objects.filter(asset_id__iexact=asset).exists()
        }
        if not missing:
            return 0
        grants = {
            action: ToolDelegation.objects.get_or_create(
                organisation=organisation,
                submission=submission(action),
                defaults={
                    "person": person,
                    "approval": term,
                    "approval_reference": reference,
                    "action": action,
                    "site": SITE,
                    "starts_on": DAY,
                    "ends_on": date(2099, 12, 31),
                    "procedure": "Fictitious sample exposition, C.3, demonstration revision",
                    "authority": "Fictitious example of a signed site delegation",
                },
            )[0]
            for action in ToolAction
        }
        with working_for(organisation.pk, person.user.pk):
            for asset, (description, location, measurement_range, lender, notes) in missing.items():
                tool = Tool.objects.create(
                    organisation=organisation,
                    submission=submission(asset),
                    asset_id=asset,
                    description=description,
                    site=SITE,
                    location=location,
                    lender=lender,
                    owner="" if lender else "Organisation",
                    measurement_range=measurement_range,
                    is_assembly=bool(lender),
                    notes=notes,
                    registered_on=DAY,
                    delegation=grants[ToolAction.REGISTER],
                )
                if asset in {"0201", "0210", "0301"}:
                    _board_evidence(tool, grants)
        return len(missing)


def _board_evidence(tool: Tool, grants: dict[ToolAction, ToolDelegation]) -> None:
    before_use = tool.asset_id == "0301"
    control = ToolControlRevision.objects.create(
        organisation=tool.organisation,
        tool=tool,
        delegation=grants[ToolAction.CONTROL],
        submission=submission(f"{tool.asset_id}/basis"),
        effective_on=DAY,
        kind=ControlKind.BEFORE_USE if before_use else ControlKind.SERVICING,
        interval_months={"0201": 6, "0210": 12}.get(tool.asset_id),
        instruction="Tool and Equipment Register board, fictitious example",
        instruction_revision="18 November 2026 board",
        method="Inspection under the applicable task instructions"
        if before_use
        else "Service under the tool manufacturer's instructions",
        limits="Refer to applicable instructions for inspection or service criteria",
        decision_basis="Sample board control basis",
        scope="Piper PA-28 Series (Lycoming)"
        if before_use
        else "Tool in the displayed configuration",
    )
    if before_use:
        return
    grease_gun = tool.asset_id == "0201"
    ToolControlEvent.objects.create(
        organisation=tool.organisation,
        tool=tool,
        submission=submission(f"{tool.asset_id}/event"),
        delegation=grants[ToolAction.EVIDENCE if grease_gun else ToolAction.CONDITION],
        control=control if grease_gun else None,
        signed_on=DAY,
        kind=EventKind.SERVICED if grease_gun else EventKind.UNSERVICEABLE,
        occurred_on=date(2026, 8, 3) if grease_gun else date(2026, 11, 10),
        evidence="Service entry on the fictitious Tool and Equipment Register board"
        if grease_gun
        else "Seal leaking. The board shows a seal-kit ETA of 25 November. "
        "Confirm repair and the service completion before signing return to use.",
    )
