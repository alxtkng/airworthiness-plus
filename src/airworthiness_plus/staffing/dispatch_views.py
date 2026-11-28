"""Day board and normal dispatch record forms."""

from datetime import date, timedelta
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.staffing import dispatch, roster
from airworthiness_plus.staffing.dispatch_forms import (
    AssignmentForm,
    BreakForm,
    MoveAssignmentForm,
    TurnaroundForm,
)
from airworthiness_plus.staffing.dispatch_models import DispatchAssignment
from airworthiness_plus.staffing.roster_rules import week_of
from airworthiness_plus.staffing.roster_views import _show_form
from airworthiness_plus.staffing.services import RefusedError
from airworthiness_plus.staffing.views import _user


def _selected_day(request: HttpRequest) -> date:
    try:
        day = date.fromisoformat(request.GET.get("day", ""))
        if date(1900, 1, 1) <= day <= date(2100, 12, 31):
            return day
    except ValueError:
        pass
    return aircraft_services.today()


@never_cache
@requires(Action.VIEW_RECORDS)
@require_safe
def dispatch_board(request: HttpRequest) -> HttpResponse:
    user = _user(request)
    day = _selected_day(request)
    with timezone.override(roster.LONDON):
        handovers = [
            (handover, dispatch.remaining(handover.card) if handover.card is not None else "")
            for handover in roster.handovers_for(week_of(day))
            if roster.local_day(handover.handed_at) == day or handover.acknowledged_at is None
        ]
        return render(
            request,
            "staffing/dispatch.html",
            {
                "board": dispatch.day_board(day, user.organisation),
                "day": day,
                "week": week_of(day),
                "previous": day - timedelta(days=1),
                "next": day + timedelta(days=1),
                "may_plan": user.may(Action.RECORD_STAFFING_PLAN),
                "may_acknowledge": user.may(Action.ACKNOWLEDGE_HANDOVER),
                "user": user,
                "handovers": handovers,
            },
        )


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def dispatch_assignment(request: HttpRequest, assignment_id: UUID | None = None) -> HttpResponse:
    previous = None
    if assignment_id is not None:
        previous = get_object_or_404(
            DispatchAssignment.objects.select_related("card__package"), pk=assignment_id
        )
    with timezone.override(roster.LONDON):
        form: MoveAssignmentForm
        if previous is None:
            form = AssignmentForm(
                request.POST or None,
                initial={"starts_at": roster.midnight(_selected_day(request))},
            )
        else:
            form = MoveAssignmentForm(
                request.POST or None,
                initial={
                    "shift": previous.shift_id,
                    "starts_at": previous.starts_at,
                    "ends_at": previous.ends_at,
                },
            )
        if request.method == "POST" and form.is_valid():
            values = form.cleaned_data
            if previous is not None:
                values["card"] = previous.card
            try:
                item = dispatch.assign(actor=_user(request), previous=previous, **values)
            except RefusedError as error:
                form.add_error(None, str(error))
            else:
                return redirect(
                    reverse(
                        "dispatch_board",
                        query={"day": roster.local_day(item.starts_at).isoformat()},
                    )
                )
        title = f"Move Assignment for {previous.card}" if previous is not None else "Assign Work"
        return _show_form(request, form, title)


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def dispatch_window(request: HttpRequest, turnaround: bool = False) -> HttpResponse:
    with timezone.override(roster.LONDON):
        form_class = TurnaroundForm if turnaround else BreakForm
        form = form_class(
            request.POST or None, initial={"starts_at": roster.midnight(_selected_day(request))}
        )
        if request.method == "POST" and form.is_valid():
            try:
                item = dispatch.add_window(actor=_user(request), **form.cleaned_data)
            except RefusedError as error:
                form.add_error(None, str(error))
            else:
                return redirect(
                    reverse(
                        "dispatch_board",
                        query={"day": roster.local_day(item.starts_at).isoformat()},
                    )
                )
        return _show_form(request, form, "Record Turnaround" if turnaround else "Record Break")
