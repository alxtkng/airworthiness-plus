"""Record append-only tooling decisions under an applicable exposition delegation."""

from datetime import date
from uuid import UUID

from django.db import IntegrityError, models, transaction
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.services import maintenance_approvals
from airworthiness_plus.organisations.models import Approval, Organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.tooling import status
from airworthiness_plus.tooling.models import (
    ControlKind,
    EventKind,
    Tool,
    ToolAction,
    ToolControlEvent,
    ToolControlRevision,
    ToolDelegation,
    ToolDelegationWithdrawal,
)
from airworthiness_rules.dates import BeyondCalendarError, add_months


class RefusedError(ValueError):
    """Evidence or authority cannot support the requested action."""


def _lock(user: User, action: Action) -> tuple[Organisation, date]:
    if not user.is_active or not user.may(action):
        raise ActionRefusedError(action)
    # Match approval changes' organisation lock. Serialize delegation withdrawals,
    # same-tool condition transitions and retries before re-reading the evidence.
    organisation = Organisation.objects.select_for_update(no_key=True).get(pk=user.organisation_id)
    return organisation, aircraft_services.today()


def _approval(organisation: Organisation, kind: str, today: date) -> tuple[Approval, str]:
    for approval in maintenance_approvals(organisation, today):
        if approval.approval == kind and (reference := approval.reference_on(today)):
            return approval, reference
    raise RefusedError("Choose a maintenance approval held today")


def _authorise(
    organisation: Organisation,
    user: User,
    approval_kind: str,
    action: ToolAction,
    site: str,
    today: date,
) -> ToolDelegation:
    approval, reference = _approval(organisation, approval_kind, today)
    grant = (
        ToolDelegation.objects.filter(
            organisation=organisation,
            approval=approval,
            approval_reference=reference,
            person__user=user,
            action=action,
            site__iexact=site,
            starts_on__lte=today,
            ends_on__gte=today,
            withdrawal__isnull=True,
        )
        .filter(Q(person__joined_on__isnull=True) | Q(person__joined_on__lte=today))
        .filter(Q(person__left_on__isnull=True) | Q(person__left_on__gt=today))
        .select_related("person", "approval")
        .order_by("-starts_on", "-entered_at", "-id")
        .first()
    )
    if grant is None:
        raise RefusedError(
            "Your person record needs a current tooling delegation "
            "for this action, approval and site"
        )
    return grant


def _retry[RecordType: models.Model](
    model: type[RecordType], request_id: UUID, expected: dict[str, object]
) -> RecordType | None:
    record = model._default_manager.filter(submission=request_id).first()
    if record is not None and any(
        getattr(record, field) != value for field, value in expected.items()
    ):
        raise RefusedError(
            "This submission has already been used. Reopen the form to record new evidence"
        )
    return record


@transaction.atomic
def record_delegation(
    user: User,
    *,
    request_id: UUID,
    approval: str,
    person: Person,
    action: str,
    site: str,
    starts_on: date,
    ends_on: date,
    procedure: str,
    authority: str,
) -> ToolDelegation:
    organisation, today = _lock(user, Action.MANAGE_TOOL_DELEGATIONS)
    term, reference = _approval(organisation, approval, today)
    if person.organisation_id != organisation.pk:
        raise RefusedError("Choose a person of this organisation")
    if ends_on < starts_on or ends_on < today:
        raise RefusedError(
            "The delegation must have a valid period with an end date today or later"
        )
    fields = dict(
        organisation=organisation,
        approval=term,
        approval_reference=reference,
        person=person,
        action=action,
        site=site,
        starts_on=starts_on,
        ends_on=ends_on,
        procedure=procedure,
        authority=authority,
    )
    return _retry(ToolDelegation, request_id, fields) or ToolDelegation.objects.create(
        submission=request_id, **fields
    )


@transaction.atomic
def withdraw_delegation(
    user: User, delegation: ToolDelegation, *, evidence: str
) -> ToolDelegationWithdrawal:
    organisation, today = _lock(user, Action.MANAGE_TOOL_DELEGATIONS)
    delegation = ToolDelegation.objects.get(pk=delegation.pk, organisation=organisation)
    existing = ToolDelegationWithdrawal.objects.filter(delegation=delegation).first()
    if existing:
        if existing.evidence != evidence:
            raise RefusedError("This delegation has already been withdrawn")
        return existing
    return ToolDelegationWithdrawal.objects.create(
        organisation=organisation, delegation=delegation, withdrawn_on=today, evidence=evidence
    )


@transaction.atomic
def register_tool(
    user: User,
    *,
    request_id: UUID,
    approval: str,
    asset_id: str,
    description: str,
    manufacturer: str,
    model: str,
    part_number: str,
    serial: str,
    component_ids: str,
    is_assembly: bool,
    measurement_range: str,
    owner: str,
    lender: str,
    site: str,
    location: str,
    notes: str,
) -> Tool:
    organisation, today = _lock(user, Action.RECORD_TOOL)
    grant = _authorise(organisation, user, approval, ToolAction.REGISTER, site, today)
    if not (owner or lender):
        raise RefusedError("Record the owner or lender for this tool")
    fields = dict(
        organisation=organisation,
        delegation=grant,
        asset_id=asset_id,
        description=description,
        manufacturer=manufacturer,
        model=model,
        part_number=part_number,
        serial=serial,
        component_ids=component_ids,
        is_assembly=is_assembly,
        measurement_range=measurement_range,
        owner=owner,
        lender=lender,
        site=site,
        location=location,
        notes=notes,
    )
    if existing := _retry(Tool, request_id, fields):
        return existing
    try:
        with transaction.atomic():
            return Tool.objects.create(submission=request_id, registered_on=today, **fields)
    except IntegrityError as error:
        if Tool.objects.filter(organisation=organisation, asset_id__iexact=asset_id).exists():
            raise RefusedError("This asset ID is already recorded. Open its tool record") from error
        raise


@transaction.atomic
def record_control(
    user: User,
    tool: Tool,
    *,
    request_id: UUID,
    approval: str,
    kind: str,
    interval_months: int | None,
    instruction: str,
    instruction_revision: str,
    method: str,
    limits: str,
    decision_basis: str,
    scope: str,
    standard: str,
    loan_task: str,
    loan_evidence: str,
    loan_identity: str,
) -> ToolControlRevision:
    organisation, today = _lock(user, Action.RECORD_TOOL_CONTROL)
    tool = Tool.objects.get(pk=tool.pk, organisation=organisation)
    grant = _authorise(organisation, user, approval, ToolAction.CONTROL, tool.site, today)
    fields = dict(
        organisation=organisation,
        tool=tool,
        delegation=grant,
        kind=kind,
        interval_months=interval_months,
        instruction=instruction,
        instruction_revision=instruction_revision,
        method=method,
        limits=limits,
        decision_basis=decision_basis,
        scope=scope,
        standard=standard,
        loan_task=loan_task,
        loan_evidence=loan_evidence,
        loan_identity=loan_identity,
    )
    if existing := _retry(ToolControlRevision, request_id, fields):
        return existing
    condition = status.condition_on(tool, today)
    if condition and condition.kind == EventKind.WITHDRAWN:
        raise RefusedError("The asset has been withdrawn")
    if tool.lender:
        identity = " / ".join(value for value in (tool.serial, tool.component_ids) if value)
        if (
            not all((tool.serial, loan_task, loan_evidence))
            or (tool.is_assembly and not tool.component_ids)
            or loan_identity != identity
        ):
            raise RefusedError(
                "Verify the task revision, serials, toolmaker instructions "
                "and evidence for the actual loan. "
                "The loan identity must match the serial and any component IDs on the register"
            )
    if kind == ControlKind.CALIBRATION and not standard:
        raise RefusedError("Record the recognised standard used for calibration")
    if (kind == ControlKind.BEFORE_USE and interval_months is not None) or (
        kind != ControlKind.BEFORE_USE and not interval_months
    ):
        raise RefusedError("Record a calendar interval for servicing or calibration")
    return ToolControlRevision.objects.create(submission=request_id, effective_on=today, **fields)


CONTROL_FOR_EVENT = {
    EventKind.CALIBRATED: ControlKind.CALIBRATION,
    EventKind.SERVICED: ControlKind.SERVICING,
    EventKind.INSPECTED: ControlKind.BEFORE_USE,
    EventKind.INTERIM_PASS: ControlKind.CALIBRATION,
    EventKind.INTERIM_FAIL: ControlKind.CALIBRATION,
}


def _event_action(kind: EventKind) -> ToolAction:
    if kind == EventKind.REINSTATED:
        return ToolAction.REINSTATE
    if kind in CONTROL_FOR_EVENT:
        return ToolAction.EVIDENCE
    return ToolAction.CONDITION


def _check_condition(
    tool: Tool, grant: ToolDelegation, kind: EventKind, occurred_on: date, today: date
) -> None:
    condition = status.condition_on(tool, today)
    if condition and condition.kind == EventKind.WITHDRAWN:
        raise RefusedError("The asset has been withdrawn")
    if kind in (*status.CONDITION_EVENTS, EventKind.REPAIRED):
        if condition and occurred_on < condition.occurred_on:
            raise RefusedError("Enter physical condition events in chronological order")
    if kind not in (EventKind.REPAIRED, EventKind.REINSTATED):
        return
    if not condition or condition.kind not in status.RESTRICTIONS:
        raise RefusedError("Record the restriction before repair or return to use")
    if kind == EventKind.REPAIRED:
        return
    if occurred_on != today:
        raise RefusedError("Return to use takes effect on the day the decision is signed")
    repair = tool.control_events.filter(
        kind=EventKind.REPAIRED,
        occurred_on__gte=condition.occurred_on,
        entered_at__gt=condition.entered_at,
    ).exists()
    if not repair:
        raise RefusedError(
            "Record completed repair or rectification before returning the tool to use"
        )
    label = status.label(tool, grant.approval, grant.approval_reference, today, 0)
    if label.control_status in {status.UNKNOWN, "Completion evidence needed", "Overdue"}:
        raise RefusedError(
            "Verify the control basis and complete any outstanding or overdue controls"
        )


@transaction.atomic
def record_event(
    user: User,
    tool: Tool,
    *,
    request_id: UUID,
    approval: str,
    kind: str,
    occurred_on: date,
    evidence: str,
    reference_instrument: str,
    result: str,
    limit: str,
    control: ToolControlRevision | None,
) -> ToolControlEvent:
    organisation, today = _lock(user, Action.RECORD_TOOL_EVENT)
    tool = Tool.objects.get(pk=tool.pk, organisation=organisation)
    event_kind = EventKind(kind)
    grant = _authorise(organisation, user, approval, _event_action(event_kind), tool.site, today)
    fields = dict(
        organisation=organisation,
        tool=tool,
        delegation=grant,
        kind=event_kind,
        occurred_on=occurred_on,
        evidence=evidence,
        reference_instrument=reference_instrument,
        result=result,
        limit=limit,
        control=control,
    )
    if existing := _retry(ToolControlEvent, request_id, fields):
        return existing
    if occurred_on > today:
        raise RefusedError("Evidence cannot be dated in the future")
    _check_condition(tool, grant, event_kind, occurred_on, today)
    if control_kind := CONTROL_FOR_EVENT.get(event_kind):
        controls = status.active_controls(tool, grant.approval, grant.approval_reference, today)
        if control is None or controls.get(control_kind) != control:
            raise RefusedError("Select the current control basis for this event and approval")
        if event_kind in (EventKind.INTERIM_PASS, EventKind.INTERIM_FAIL) and not all(
            (reference_instrument, result, limit)
        ):
            raise RefusedError(
                "Record the reference instrument, result and limit for the interim check"
            )
        if control.interval_months and event_kind in status.COMPLETIONS.values():
            try:
                add_months(occurred_on, control.interval_months)
            except BeyondCalendarError as error:
                raise RefusedError(
                    "The completion and interval put the due date outside the calendar"
                ) from error
    elif control is not None:
        raise RefusedError("Leave the control basis blank for a physical condition entry")
    return ToolControlEvent.objects.create(submission=request_id, signed_on=today, **fields)
