"""The Tools and Equipment register, labels and write workflows."""

from datetime import date
from uuid import UUID

from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.services import maintenance_approvals
from airworthiness_plus.organisations.models import Approval
from airworthiness_plus.tooling import services, status
from airworthiness_plus.tooling.forms import (
    ControlForm,
    DelegationForm,
    EventForm,
    RegistrationForm,
    WithdrawalForm,
)
from airworthiness_plus.tooling.models import (
    Tool,
    ToolControlEvent,
    ToolControlRevision,
    ToolDelegation,
)


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by requires
    return user


def _read_access(user: User, available: list[Approval]) -> None:
    if not available and not Tool.objects.filter(organisation_id=user.organisation_id).exists():
        raise ActionRefusedError(Action.VIEW_RECORDS)


def _approval_context(
    request: HttpRequest, user: User, today: date
) -> tuple[list[Approval], Approval | None, str]:
    available = sorted(maintenance_approvals(user.organisation, today), key=lambda a: a.approval)
    requested = request.GET.get("approval")
    selected = next((approval for approval in available if approval.approval == requested), None)
    if requested is None and available:
        selected = available[0]
    reference = (selected.reference_on(today) or "") if selected else ""
    return available, selected, reference


def _tools(user: User) -> QuerySet[Tool]:
    revisions = ToolControlRevision.objects.select_related(
        "delegation__person", "delegation__approval"
    )
    events = ToolControlEvent.objects.select_related("delegation__person", "control")
    return (
        Tool.objects.filter(organisation_id=user.organisation_id)
        .prefetch_related(Prefetch("control_revisions", queryset=revisions))
        .prefetch_related(Prefetch("control_events", queryset=events))
        .prefetch_related(
            "calibration_orders__movements",
            "calibration_orders__certificates__decisions__reinstatement",
            "calibration_orders__impact_case__trigger__certificate",
        )
    )


@never_cache
@requires(Action.VIEW_RECORDS)
@require_http_methods(["GET", "HEAD"])
def tool_register(request: HttpRequest) -> HttpResponse:
    """Show the shared physical register and approval-specific tool labels."""
    user = _user(request)
    today = aircraft_services.today()
    available, selected, reference = _approval_context(request, user, today)
    _read_access(user, available)
    lines = [
        status.label(tool, selected, reference, today, user.organisation.due_soon_days)
        for tool in _tools(user)
    ]
    return render(
        request,
        "tooling/register.html",
        {
            "available": available,
            "selected": selected,
            "reference": reference,
            "lines": lines,
            "attention": [line for line in lines if line.needs_attention],
            "may_register": bool(available) and user.may(Action.RECORD_TOOL),
            "may_delegate": user.may(Action.MANAGE_TOOL_DELEGATIONS),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
@require_http_methods(["GET", "HEAD"])
def tool_record(request: HttpRequest, tool_id: UUID) -> HttpResponse:
    """Show the label, control revisions and dated condition evidence for a tool."""
    user = _user(request)
    tool = get_object_or_404(_tools(user), pk=tool_id)
    today = aircraft_services.today()
    available, selected, reference = _approval_context(request, user, today)
    _read_access(user, available)
    visible_label = status.label(tool, selected, reference, today, user.organisation.due_soon_days)
    return render(
        request,
        "tooling/record.html",
        {
            "tool": tool,
            "label": visible_label,
            "available": available,
            "selected": selected,
            "reference": reference,
            "may_control": bool(selected) and user.may(Action.RECORD_TOOL_CONTROL),
            "may_record": bool(selected) and user.may(Action.RECORD_TOOL_EVENT),
            "may_calibrate": bool(selected) and user.may(Action.RECORD_TOOL_CALIBRATION),
        },
    )


def _initial(request: HttpRequest, user: User) -> dict[str, str]:
    _, selected, _ = _approval_context(request, user, aircraft_services.today())
    return {"approval": selected.approval} if selected else {}


def _detail_url(tool: Tool, approval: str) -> HttpResponse:
    response = redirect("tool_record", tool_id=tool.pk)
    response["Location"] += f"?approval={approval}"
    return response


@never_cache
@requires(Action.RECORD_TOOL)
@require_http_methods(["GET", "POST"])
def add_tool(request: HttpRequest) -> HttpResponse:
    """Register one physical tool."""
    user = _user(request)
    form = RegistrationForm(
        request.POST if request.method == "POST" else None, initial=_initial(request, user)
    )
    if request.method == "POST" and form.is_valid():
        try:
            tool = services.register_tool(user, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _detail_url(tool, form.cleaned_data["approval"])
    return render(request, "tooling/form.html", {"form": form, "title": "Register a Tool"})


@never_cache
@requires(Action.RECORD_TOOL_CONTROL)
@require_http_methods(["GET", "POST"])
def add_tool_control(request: HttpRequest, tool_id: UUID) -> HttpResponse:
    """Approve a dated calibration, servicing or before-use control basis."""
    user = _user(request)
    tool = get_object_or_404(Tool, pk=tool_id, organisation_id=user.organisation_id)
    form = ControlForm(
        request.POST if request.method == "POST" else None, initial=_initial(request, user)
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.record_control(user, tool, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _detail_url(tool, form.cleaned_data["approval"])
    return render(
        request, "tooling/form.html", {"form": form, "tool": tool, "title": "Record Control Basis"}
    )


@never_cache
@requires(Action.RECORD_TOOL_EVENT)
@require_http_methods(["GET", "POST"])
def add_tool_event(request: HttpRequest, tool_id: UUID) -> HttpResponse:
    """Record completion, inspection, interim check, withdrawal, repair or return to use."""
    user = _user(request)
    tool = get_object_or_404(Tool, pk=tool_id, organisation_id=user.organisation_id)
    initial = _initial(request, user)
    initial["occurred_on"] = aircraft_services.today().isoformat()
    today = aircraft_services.today()
    active = [
        revision.pk
        for approval in maintenance_approvals(user.organisation, today)
        if (reference := approval.reference_on(today))
        for revision in status.active_controls(tool, approval, reference, today).values()
    ]
    controls = ToolControlRevision.objects.filter(pk__in=active).select_related(
        "delegation__approval"
    )
    forms_data = request.POST if request.method == "POST" else None
    form = EventForm(forms_data, initial=initial, controls=controls)
    if request.method == "POST" and form.is_valid():
        try:
            services.record_event(user, tool, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _detail_url(tool, form.cleaned_data["approval"])
    return render(
        request, "tooling/form.html", {"form": form, "tool": tool, "title": "Record Tool Event"}
    )


@never_cache
@requires(Action.MANAGE_TOOL_DELEGATIONS)
@require_http_methods(["GET", "HEAD"])
def tool_delegations(request: HttpRequest) -> HttpResponse:
    """Show the organisation's recorded exposition delegations."""
    user = _user(request)
    delegations = ToolDelegation.objects.filter(
        organisation_id=user.organisation_id
    ).select_related("person", "approval", "withdrawal")
    return render(request, "tooling/delegations.html", {"delegations": delegations})


@never_cache
@requires(Action.MANAGE_TOOL_DELEGATIONS)
@require_http_methods(["GET", "POST"])
def add_tool_delegation(request: HttpRequest) -> HttpResponse:
    """Transcribe an existing signed tooling delegation."""
    user = _user(request)
    form = DelegationForm(
        request.POST if request.method == "POST" else None, initial=_initial(request, user)
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.record_delegation(user, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("tool_delegations")
    return render(request, "tooling/form.html", {"form": form, "title": "Record Tool Delegation"})


@never_cache
@requires(Action.MANAGE_TOOL_DELEGATIONS)
@require_http_methods(["GET", "POST"])
def withdraw_tool_delegation(request: HttpRequest, delegation_id: UUID) -> HttpResponse:
    """Record the withdrawal of a tooling delegation."""
    user = _user(request)
    delegation = get_object_or_404(
        ToolDelegation, pk=delegation_id, organisation_id=user.organisation_id
    )
    form = WithdrawalForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            services.withdraw_delegation(user, delegation, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("tool_delegations")
    return render(
        request,
        "tooling/form.html",
        {"form": form, "title": "Withdraw Tool Delegation", "delegation": delegation},
    )
