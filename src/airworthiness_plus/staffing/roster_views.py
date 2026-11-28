"""Roster, handover and planning settings views."""

from collections.abc import Callable
from datetime import date, timedelta
from uuid import UUID

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.organisations.models import Approval, Organisation
from airworthiness_plus.planning.models import WorkCard
from airworthiness_plus.staffing import roster
from airworthiness_plus.staffing.roster_forms import (
    BankHolidayForm,
    HandoverForm,
    PublicationForm,
    SettingsForm,
    ShiftForm,
    ShiftPatternForm,
    StaffingMinimumForm,
    WithdrawShiftForm,
)
from airworthiness_plus.staffing.roster_models import (
    BankHoliday,
    Handover,
    PublishedRoster,
    Settings,
    Shift,
    ShiftPattern,
    StaffingMinimum,
)
from airworthiness_plus.staffing.roster_rules import week_of
from airworthiness_plus.staffing.services import RefusedError
from airworthiness_plus.staffing.views import _user


def chosen_week(request: HttpRequest) -> date:
    try:
        selected = date.fromisoformat(request.GET.get("week", ""))
        if date(1900, 1, 1) <= selected <= date(2100, 12, 31):
            return week_of(selected)
    except ValueError:
        pass
    return week_of(aircraft_services.today())


def _show_form(request: HttpRequest, form: Form, title: str) -> HttpResponse:
    return render(request, "contracts/form.html", {"form": form, "title": title, "button": title})


@never_cache
@requires(Action.VIEW_RECORDS)
def staff_roster(request: HttpRequest) -> HttpResponse:
    """Show the week, fatigue checks, Part-145 crew shares and handovers."""
    user = _user(request)
    week = chosen_week(request)
    settings = roster.settings_for(user.organisation)
    checked = roster.check_shifts(week, settings)
    publications = list(
        PublishedRoster.objects.filter(week=week)
        .select_related("published_by")
        .prefetch_related("entries__shift__person")
    )
    latest = next(
        (
            publication
            for publication in publications
            if not any(item.supersedes_id == publication.pk for item in publications)
        ),
        None,
    )
    published_shifts = {entry.shift_id for entry in latest.entries.all()} if latest else set()
    revised = latest is not None and published_shifts != {line.shift.pk for line in checked}

    with timezone.override(roster.LONDON):
        return render(
            request,
            "staffing/roster.html",
            {
                "week": week,
                "previous": week - timedelta(days=7),
                "next": week + timedelta(days=7),
                "checked": checked,
                "crews": roster.crews(checked),
                "publish_by": week - timedelta(days=settings.publish_days),
                "publications": publications,
                "unpublished_changes": revised,
                "handovers": roster.handovers_for(week),
                "user": user,
                "may_roster": user.may(Action.RECORD_STAFFING_PLAN),
                "may_acknowledge": user.may(Action.ACKNOWLEDGE_HANDOVER),
            },
        )


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def add_roster_shift(request: HttpRequest) -> HttpResponse:
    """Add a shift with roster times, work and fatigue evidence."""
    user = _user(request)
    settings = roster.settings_for(user.organisation)
    with timezone.override(roster.LONDON):
        form = ShiftForm(
            request.POST or None, initial={"break_minutes": settings.standard_break_minutes}
        )
        if request.method == "POST" and form.is_valid():
            try:
                shift = roster.add_shift(actor=user, **form.cleaned_data)
            except RefusedError as error:
                form.add_error(None, str(error))
            else:
                return redirect(
                    reverse(
                        "staff_roster",
                        query={"week": roster.local_day(shift.starts_at).isoformat()},
                    )
                )
        return _show_form(request, form, "Add Shift")


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def withdraw_roster_shift(request: HttpRequest, shift_id: UUID) -> HttpResponse:
    """Withdraw a shift and keep it in roster history."""
    shift = get_object_or_404(Shift, pk=shift_id)
    form = WithdrawShiftForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            roster.withdraw_shift(shift, actor=_user(request), **form.cleaned_data)
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect(
                reverse(
                    "staff_roster", query={"week": roster.local_day(shift.starts_at).isoformat()}
                )
            )
    return _show_form(request, form, "Withdraw Shift")


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def publish_roster(request: HttpRequest) -> HttpResponse:
    """Record publication or a change of the selected roster week."""
    form = PublicationForm(request.POST or None, initial={"week": chosen_week(request)})
    if request.method == "POST" and form.is_valid():
        try:
            publication = roster.publish(actor=_user(request), **form.cleaned_data)
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect(reverse("staff_roster", query={"week": publication.week.isoformat()}))
    return _show_form(request, form, "Publish Roster")


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def record_handover(request: HttpRequest) -> HttpResponse:
    """Record who handed over work and where it stood."""
    user = _user(request)
    with timezone.override(roster.LONDON):
        card_id = request.GET.get("card")
        card = None
        if card_id:
            try:
                card = get_object_or_404(WorkCard, pk=UUID(card_id))
            except ValueError:
                raise Http404 from None
        form = HandoverForm(
            request.POST or None,
            initial={"card": card, "package": card.package_id if card else None},
        )
        if request.method == "POST" and form.is_valid():
            try:
                handover = roster.record_handover(actor=user, **form.cleaned_data)
            except RefusedError as error:
                form.add_error(None, str(error))
            else:
                return _handover_return(request, handover)
        return _show_form(request, form, "Record Handover")


@never_cache
@requires(Action.ACKNOWLEDGE_HANDOVER)
@require_http_methods(["GET", "POST"])
def acknowledge_handover(request: HttpRequest, handover_id: UUID) -> HttpResponse:
    """Acknowledge a handover addressed to the signed-in person."""
    handover = get_object_or_404(Handover, pk=handover_id)
    form = Form(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            roster.acknowledge(handover, _user(request))
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _handover_return(request, handover)
    return _show_form(request, form, "Acknowledge Handover")


def _handover_return(request: HttpRequest, handover: Handover) -> HttpResponse:
    day = roster.local_day(handover.handed_at).isoformat()
    if request.GET.get("from") == "dispatch":
        return redirect(reverse("dispatch_board", query={"day": day}))
    return redirect(reverse("staff_roster", query={"week": day}))


@never_cache
@requires(Action.VIEW_RECORDS)
def planning_settings(request: HttpRequest) -> HttpResponse:
    """Show the organisation's planning, fatigue and roster settings."""
    user = _user(request)
    form = SettingsForm(initial=model_to_dict(roster.settings_for(user.organisation)))
    return render(
        request,
        "staffing/settings.html",
        {
            "form": form,
            "may_change": user.may(Action.CHANGE_ORGANISATION_RECORD),
            "holidays": BankHoliday.objects.all(),
            "patterns": ShiftPattern.objects.all(),
            "minimums": StaffingMinimum.objects.select_related("approval"),
        },
    )


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_http_methods(["GET", "POST"])
def change_planning_settings(request: HttpRequest) -> HttpResponse:
    """Set the organisation's planning, fatigue and roster limits."""
    user = _user(request)
    current = roster.settings_for(user.organisation)
    form = SettingsForm(request.POST or None, initial=model_to_dict(current))
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            Organisation.objects.select_for_update().only("id").get(pk=user.organisation_id)
            Settings.objects.update_or_create(
                organisation_id=user.organisation_id,
                defaults=form.cleaned_data,
            )
        return redirect("planning_settings")
    return _show_form(request, form, "Save Planning Settings")


@never_cache
@requires(Action.VIEW_RECORDS)
def load_and_capacity(request: HttpRequest) -> HttpResponse:
    """Compare weekly package work with maintenance roster capacity and show unplanned work."""
    from airworthiness_plus.releases.services import maintains
    from airworthiness_plus.staffing import capacity

    user = _user(request)
    week = chosen_week(request)
    settings = roster.settings_for(user.organisation)
    may_maintain = maintains(user.organisation)
    return render(
        request,
        "staffing/capacity.html",
        {
            "week": week,
            "weekly": capacity.weekly_loads(week, 6, settings) if may_maintain else (),
            "unplanned": capacity.work_not_planned(
                aircraft_services.today(), week + timedelta(days=42)
            )
            if may_maintain
            else (),
            "settings": settings,
            "may_build": may_maintain and user.may(Action.PLAN_WORK_PACKAGE),
        },
    )


def _setting_entry(
    request: HttpRequest, form: Form, title: str, write: Callable[..., object]
) -> HttpResponse:
    if request.method == "POST" and form.is_valid():
        organisation = _user(request).organisation
        with transaction.atomic():
            Organisation.objects.select_for_update().only("id").get(pk=organisation.pk)
            write(organisation=organisation, **form.cleaned_data)
        return redirect("planning_settings")
    return _show_form(request, form, title)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_http_methods(["GET", "POST"])
def record_bank_holiday(request: HttpRequest) -> HttpResponse:
    """Record a bank holiday for the weekly plan."""
    form = BankHolidayForm(request.POST or None)

    def save(*, organisation: Organisation, on: date, name: str) -> None:
        BankHoliday.objects.update_or_create(
            organisation=organisation, on=on, defaults={"name": name}
        )

    return _setting_entry(request, form, "Record Bank Holiday", save)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_http_methods(["GET", "POST"])
def record_shift_pattern(request: HttpRequest) -> HttpResponse:
    """Record an organisation shift pattern."""
    form = ShiftPatternForm(request.POST or None)

    def save(*, organisation: Organisation, name: str, **values: object) -> None:
        ShiftPattern.objects.update_or_create(organisation=organisation, name=name, defaults=values)

    return _setting_entry(request, form, "Record Shift Pattern", save)


@never_cache
@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_http_methods(["GET", "POST"])
def record_staffing_minimum(request: HttpRequest) -> HttpResponse:
    """Record the organisation's minimum and normal staffing by function."""
    form = StaffingMinimumForm(request.POST or None)

    def save(
        *, organisation: Organisation, approval: Approval, function: str, **values: object
    ) -> None:
        StaffingMinimum.objects.update_or_create(
            organisation=organisation,
            approval=approval,
            function=function,
            defaults=values,
        )

    return _setting_entry(request, form, "Record Staffing Minimum", save)
