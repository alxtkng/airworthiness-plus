"""The Settings page (REQ-211 to REQ-214).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). Everyone may read what is set; the
Administrator changes it, and every change is in the history of the
organisation record.
"""

import uuid
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.interface import formatting
from airworthiness_plus.organisations import approvals, configuration
from airworthiness_plus.organisations.forms import (
    ApprovalHeldForm,
    DeferralLimitsForm,
    DetailsForm,
    EndApprovalForm,
    LeadTimesForm,
)
from airworthiness_plus.organisations.models import Approval, ApprovalType, Organisation
from airworthiness_plus.programme import due
from airworthiness_rules.intervals import Unit


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


def _organisation(request: HttpRequest) -> Organisation:
    return Organisation.objects.get(pk=_user(request).organisation_id)


def _page(request: HttpRequest, status: int = 200, **forms: Any) -> HttpResponse:
    """Show Settings. A form that was refused is shown again with what was sent."""
    organisation = _organisation(request)
    lead = due.thresholds_of(organisation)
    certificate = due.certificate_thresholds(organisation)
    lead_times = (
        (
            "Airworthiness Review Certificate Expiry",
            formatting.amount(Unit.CALENDAR, certificate.days),
        ),
        ("Hour-Based Checks and Life Limits", formatting.amount(Unit.HOURS, lead.hours)),
        ("Cycle-Based Checks and Life Limits", formatting.amount(Unit.CYCLES, lead.cycles)),
        ("Calendar Checks and Programme Reviews", formatting.amount(Unit.CALENDAR, lead.days)),
    )
    context = {
        "organisation": organisation,
        "approvals": [
            # An approval that is held can be ended, but for the one set up with.
            (one, one.held and one.approval != organisation.approval_type)
            for one in approvals.every(organisation)
        ],
        "deferral_lines": configuration.deferral_lines(organisation),
        "lead_times": lead_times,
        "may_change": _user(request).may(Action.CHANGE_ORGANISATION_RECORD),
        "details_form": DetailsForm(
            initial={"name": organisation.name, "address": organisation.address}
        ),
        "approval_form": ApprovalHeldForm(initial={"approval": ApprovalType.PART_145}),
        "end_form": EndApprovalForm(),
        "lead_form": LeadTimesForm(
            initial={
                "due_soon_days": organisation.due_soon_days,
                "due_soon_hours": organisation.due_soon_hours,
                "due_soon_cycles": organisation.due_soon_cycles,
                "review_alert": organisation.review_alert_days is not None,
                "review_alert_days": organisation.review_alert_days,
            }
        ),
        "deferral_form": DeferralLimitsForm(
            initial={
                "deferral_days_non_required": organisation.deferral_days_non_required,
                "deferral_days_with_agreement": organisation.deferral_days_with_agreement,
                "deferral_days_certifying_staff": organisation.deferral_days_certifying_staff,
            }
        ),
        "message": "",
        **forms,
    }
    return render(request, "organisations/settings.html", context, status=status)


@never_cache
@requires(Action.VIEW_RECORDS)
def settings_page(request: HttpRequest) -> HttpResponse:
    """Organisation details, approvals held, deferral limits and alert lead times."""
    return _page(request)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_POST
def change_details(request: HttpRequest) -> HttpResponse:
    """Change the name and address of the organisation (REQ-211)."""
    form = DetailsForm(request.POST)
    if form.is_valid():
        try:
            configuration.change_details(_organisation(request), **form.cleaned_data)
        except configuration.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("settings")
    return _page(request, details_form=form)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_POST
def record_approval_held(request: HttpRequest) -> HttpResponse:
    """Record an approval the organisation holds, with its reference (REQ-200)."""
    form = ApprovalHeldForm(request.POST)
    if form.is_valid():
        try:
            approvals.record(
                _organisation(request),
                approval=ApprovalType(form.cleaned_data["approval"]),
                reference=form.cleaned_data["reference"],
            )
        except approvals.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("settings")
    return _page(request, approval_form=form)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_POST
def end_approval_held(request: HttpRequest, approval_id: uuid.UUID) -> HttpResponse:
    """Record that an approval is no longer held. The record stays (REQ-200)."""
    approval = get_object_or_404(Approval, pk=approval_id)
    form = EndApprovalForm(request.POST)
    message = "Give the Day the Approval Was No Longer Held From"
    if form.is_valid():
        try:
            approvals.end(approval, on=form.cleaned_data["on"])
        except approvals.RefusedError as error:
            message = str(error)
        else:
            return redirect("settings")
    return _page(request, message=message)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_POST
def set_lead_times(request: HttpRequest) -> HttpResponse:
    """Set how close a limit must be to show as Due Soon (REQ-212, REQ-213)."""
    form = LeadTimesForm(request.POST)
    if form.is_valid():
        data = dict(form.cleaned_data)
        data.pop("review_alert")
        try:
            configuration.set_lead_times(_organisation(request), **data)
        except configuration.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("settings")
    return _page(request, lead_form=form)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_POST
def set_deferral_limits(request: HttpRequest) -> HttpResponse:
    """Set the organisation's default limits for a deferred defect (REQ-214)."""
    form = DeferralLimitsForm(request.POST)
    if form.is_valid():
        try:
            configuration.set_deferral_limits(_organisation(request), **form.cleaned_data)
        except configuration.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("settings")
    return _page(request, deferral_form=form)
