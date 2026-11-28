"""Issue and use tooling against dated maintenance approval and scoped evidence."""

from datetime import date
from uuid import UUID

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.contracts.models import Outcome, WorkOrder
from airworthiness_plus.logistics.services import maintenance_approvals
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import DataSet, Revision
from airworthiness_plus.organisations.models import Approval, Organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.tooling import services, status
from airworthiness_plus.tooling.custody_models import (
    HistoricalToolClaim,
    ReturnCondition,
    ToolIssue,
    ToolPreUseInspection,
    ToolReturn,
    ToolUse,
    WorkPackageApproval,
)
from airworthiness_plus.tooling.models import (
    ControlKind,
    Tool,
    ToolAction,
    ToolControlRevision,
    ToolDelegation,
)

RefusedError = services.RefusedError
WRITE = Action.RECORD_TOOL_CUSTODY


def select_approval(organisation: Organisation, kind: str, on: date) -> tuple[Approval, str]:
    held = maintenance_approvals(organisation, on)
    matches = [approval for approval in held if approval.approval == kind] if kind else held
    if len(matches) != 1 or not (reference := matches[0].reference_on(on)):
        raise RefusedError("Select the governing maintenance approval held on the activity date")
    return matches[0], reference


def pin_approval(package: WorkPackage, kind: str, on: date, evidence: str) -> WorkPackageApproval:
    """Called with the package locked in the surrounding transaction."""
    approval, reference = select_approval(package.organisation, kind, on)
    if not evidence.strip():
        raise RefusedError("Give the signed evidence for the package approval assignment")
    if previous := WorkPackageApproval.objects.filter(package=package).first():
        if (previous.approval_id, previous.reference) == (approval.pk, reference):
            return previous
        raise RefusedError("The governing approval is already recorded for this package")
    return WorkPackageApproval.objects.create(
        organisation_id=package.organisation_id,
        package=package,
        approval=approval,
        reference=reference,
        assigned_on=on,
        evidence=evidence.strip(),
    )


def _open_package(package_id: UUID, organisation: Organisation) -> WorkPackage:
    package = WorkPackage.objects.select_for_update().get(pk=package_id, organisation=organisation)
    if not package.issued_on or package.released_on or not package.order_id:
        raise RefusedError("Choose an issued and open work package")
    order = WorkOrder.objects.select_for_update().get(pk=package.order_id)
    if order.outcome == Outcome.WITHDRAWN:
        raise RefusedError("The package's work order has been withdrawn")
    return package


def _eligibility(tool: Tool, assignment: WorkPackageApproval, today: date) -> list[dict[str, str]]:
    label = status.label(tool, assignment.approval, assignment.reference, today, 0)
    if label.restricted:
        raise RefusedError("This tool is held, unserviceable or withdrawn")
    if not label.controls:
        raise RefusedError("Control basis to verify")
    if label.control_status in {"Overdue", "Completion evidence needed"}:
        raise RefusedError("Complete outstanding and overdue controls before using this tool")
    return [
        {
            "basis": str(line.revision.pk),
            "completion": str(line.completion.pk) if line.completion else "",
            "completion_evidence": line.completion.evidence if line.completion else "",
            "instruction": line.revision.instruction,
            "instruction_revision": line.revision.instruction_revision,
            "method": line.revision.method,
            "limits": line.revision.limits,
            "scope": line.revision.scope,
            "state": line.status,
            "due_on": line.due_on.isoformat() if line.due_on else "",
        }
        for line in label.controls
    ]


def _person(organisation: Organisation, person: Person, today: date) -> None:
    if (
        person.organisation_id != organisation.pk
        or (person.joined_on and person.joined_on > today)
        or (person.left_on and person.left_on <= today)
    ):
        raise RefusedError("Choose a person with this organisation on the activity date")


@transaction.atomic
def assign_approval(user: User, package: WorkPackage, *, approval: str, evidence: str) -> None:
    organisation, today = services._lock(user, Action.PLAN_WORK_PACKAGE)
    package = _open_package(package.pk, organisation)
    pin_approval(package, approval, today, evidence)


@transaction.atomic
def issue_tool(
    user: User,
    tool: Tool,
    *,
    request_id: UUID,
    package: WorkPackage,
    custodian: Person,
    location: str,
    evidence: str,
) -> ToolIssue:
    organisation, today = services._lock(user, WRITE)
    tool = Tool.objects.get(pk=tool.pk, organisation=organisation)
    package = _open_package(package.pk, organisation)
    assignment = (
        WorkPackageApproval.objects.filter(package=package).select_related("approval").first()
    )
    if assignment is None:
        raise RefusedError("Record the governing maintenance approval on the work package")
    grant = services._authorise(
        organisation, user, assignment.approval.approval, ToolAction.ISSUE, tool.site, today
    )
    if grant.approval_reference != assignment.reference:
        raise RefusedError("The work package refers to an earlier approval reference")
    fields: dict[str, object] = dict(
        organisation=organisation,
        tool=tool,
        work_approval=assignment,
        delegation=grant,
        custodian=custodian,
        location=location.strip(),
        evidence=evidence.strip(),
    )
    if saved := services._retry(ToolIssue, request_id, fields):
        return saved
    _person(organisation, custodian, today)
    if not location.strip() or not evidence.strip():
        raise RefusedError("Record the custody location and evidence of handover")
    if tool.issues.filter(return_record__isnull=True).exists():
        raise RefusedError("The tool already has an open issue")
    return ToolIssue.objects.create(
        submission=request_id,
        occurred_on=today,
        controls=_eligibility(tool, assignment, today),
        **fields,
    )


def _get_issue(issue: ToolIssue, organisation: Organisation) -> ToolIssue:
    return ToolIssue.objects.select_related("tool", "work_approval__approval").get(
        pk=issue.pk, organisation=organisation
    )


def _use_grant(
    organisation: Organisation, user: User, issue: ToolIssue, today: date
) -> ToolDelegation:
    grant = services._authorise(
        organisation,
        user,
        issue.work_approval.approval.approval,
        ToolAction.USE,
        issue.tool.site,
        today,
    )
    if grant.approval_reference != issue.work_approval.reference:
        raise RefusedError("The work package refers to an earlier approval reference")
    return grant


def _use_scope(
    organisation: Organisation, issue: ToolIssue, card: WorkCard, revision: Revision, today: date
) -> tuple[WorkCard, ToolControlRevision | None, list[dict[str, str]]]:
    package = _open_package(issue.work_approval.package_id, organisation)
    if hasattr(issue, "return_record"):
        raise RefusedError("The tool has already been returned")
    scoped_card = WorkCard.objects.filter(pk=card.pk, package=package).first()
    if scoped_card is None:
        raise RefusedError("Choose a work card on this issue's package")
    card = scoped_card
    if card.completed_on:
        raise RefusedError("Record later evidence as a historical claim after card sign-off")
    data_set = DataSet.objects.select_for_update().get(pk=card.data_set_id)
    from airworthiness_plus.planning import services as planning

    try:
        planning._check_data(
            package,
            data_set,
            revision,
            today,
            checked_until=data_set.check_due,
        )
    except planning.RefusedError as error:
        raise RefusedError(str(error)) from error
    if data_services.current_revision(data_set) != revision:
        raise RefusedError("Choose the current maintenance-data revision for this work card")
    assignment = issue.work_approval
    controls = _eligibility(issue.tool, assignment, today)
    before = status.active_controls(issue.tool, assignment.approval, assignment.reference, today)
    return card, before.get(ControlKind.BEFORE_USE), controls


@transaction.atomic
def record_inspection(
    user: User,
    issue: ToolIssue,
    *,
    request_id: UUID,
    card: WorkCard,
    revision: Revision,
    passed: bool,
    evidence: str,
) -> ToolPreUseInspection:
    organisation, today = services._lock(user, WRITE)
    issue = _get_issue(issue, organisation)
    grant = _use_grant(organisation, user, issue, today)
    fields: dict[str, object] = dict(
        organisation=organisation,
        issue=issue,
        delegation=grant,
        card=card,
        revision=revision,
        passed=passed,
        evidence=evidence.strip(),
    )
    if saved := services._retry(ToolPreUseInspection, request_id, fields):
        return saved
    _, before, _ = _use_scope(organisation, issue, card, revision, today)
    if not before or not evidence.strip():
        raise RefusedError("A before-use control and recorded findings are required")
    return ToolPreUseInspection.objects.create(
        submission=request_id, occurred_on=today, control=before, **fields
    )


@transaction.atomic
def record_use(
    user: User,
    issue: ToolIssue,
    *,
    request_id: UUID,
    card: WorkCard,
    revision: Revision,
    inspection: ToolPreUseInspection | None,
    configuration: str,
    setting: str,
    evidence: str,
) -> ToolUse:
    organisation, today = services._lock(user, WRITE)
    issue = _get_issue(issue, organisation)
    grant = _use_grant(organisation, user, issue, today)
    fields: dict[str, object] = dict(
        organisation=organisation,
        issue=issue,
        delegation=grant,
        card=card,
        revision=revision,
        inspection=inspection,
        configuration=configuration.strip(),
        setting=setting.strip(),
        evidence=evidence.strip(),
    )
    if saved := services._retry(ToolUse, request_id, fields):
        return saved
    card, before, controls = _use_scope(organisation, issue, card, revision, today)
    if not evidence.strip() or not configuration.strip():
        raise RefusedError("Give signed use evidence and the actual task configuration")
    if inspection and ToolUse.objects.filter(inspection=inspection).exists():
        raise RefusedError("That inspection has already been used")
    if before and (
        inspection is None
        or inspection.issue_id != issue.pk
        or inspection.card_id != card.pk
        or inspection.revision_id != revision.pk
        or inspection.control_id != before.pk
        or inspection.delegation.person_id != grant.person_id
        or inspection.occurred_on != today
        or not inspection.passed
        or issue.inspections.filter(
            card=card, revision=revision, control=before, entered_at__gt=inspection.entered_at
        ).exists()
    ):
        raise RefusedError("Record a satisfactory pre-use inspection for this use")
    if not before and inspection:
        raise RefusedError("Choose inspection evidence for the applicable control")
    return ToolUse.objects.create(
        submission=request_id,
        occurred_on=today,
        controls=controls,
        aircraft_registration=card.package.aircraft.registration,
        **fields,
    )


@transaction.atomic
def return_tool(
    user: User,
    issue: ToolIssue,
    *,
    request_id: UUID,
    returned_by: Person,
    location: str,
    condition: str,
    evidence: str,
) -> ToolReturn:
    organisation, today = services._lock(user, WRITE)
    issue = _get_issue(issue, organisation)
    # One physical register. A current custodian can receive an old issue under a
    # current maintenance approval after the original reference has ended.
    held = maintenance_approvals(organisation, today)
    preferred = issue.work_approval.approval.approval
    candidates = sorted(held, key=lambda approval: approval.approval != preferred)
    for approval in candidates:
        try:
            grant = services._authorise(
                organisation, user, approval.approval, ToolAction.RETURN, issue.tool.site, today
            )
        except RefusedError:
            continue
        break
    else:
        raise RefusedError("Your person record needs a current tooling return delegation")
    fields: dict[str, object] = dict(
        organisation=organisation,
        issue=issue,
        delegation=grant,
        returned_by=returned_by,
        location=location.strip(),
        kind=condition,
        evidence=evidence.strip(),
    )
    if saved := services._retry(ToolReturn, request_id, fields):
        return saved
    if hasattr(issue, "return_record"):
        raise RefusedError("This issue already has a recorded return")
    _person(organisation, returned_by, today)
    if not location.strip() or not evidence.strip() or condition not in ReturnCondition.values:
        raise RefusedError("Record the condition, return location and handover evidence")
    return ToolReturn.objects.create(submission=request_id, occurred_on=today, **fields)


@transaction.atomic
def record_claim(
    user: User,
    tool: Tool,
    *,
    request_id: UUID,
    occurred_on: date,
    card: WorkCard | None,
    work: WorkDone | None,
    claim: str,
    attributed_to: str,
    subject: str,
    source: str,
    gaps: str,
) -> HistoricalToolClaim:
    organisation, today = services._lock(user, WRITE)
    tool = Tool.objects.get(pk=tool.pk, organisation=organisation)
    if occurred_on > today or not all(
        item.strip() for item in (claim, attributed_to, subject, source, gaps)
    ):
        raise RefusedError("Record the dated claim, attribution, subject, source and evidence gaps")
    if (card and card.organisation_id != organisation.pk) or (
        work and work.organisation_id != organisation.pk
    ):
        raise RefusedError("Choose work of this organisation")
    if card and work and card.work_id != work.pk:
        raise RefusedError("The selected work must be linked to the card")
    fields: dict[str, object] = dict(
        organisation=organisation,
        tool=tool,
        card=card,
        work=work,
        occurred_on=occurred_on,
        claim=claim.strip(),
        attributed_to=attributed_to.strip(),
        subject=subject.strip(),
        source=source.strip(),
        gaps=gaps.strip(),
    )
    return services._retry(
        HistoricalToolClaim, request_id, fields
    ) or HistoricalToolClaim.objects.create(submission=request_id, **fields)
