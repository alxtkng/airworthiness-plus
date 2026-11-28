"""Pages for defects (REQ-220 to REQ-229).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A defect of another organisation is
not found, because the database does not show it (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.defects import services
from airworthiness_plus.defects.forms import CloseForm, DefectForm, RepeatActionForm
from airworthiness_plus.defects.models import Defect, FlightReport
from airworthiness_plus.organisations import configuration


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def defects_page(request: HttpRequest) -> HttpResponse:
    """Open and deferred defects, and those closed in the last 30 days (REQ-223, REQ-224)."""
    user = _user(request)
    today = aircraft_services.today()
    return render(
        request,
        "defects/defects.html",
        {
            "lines": services.open_lines(user.organisation, today),
            "closed": services.closed_lately(today),
            "may_record": user.may(Action.RECORD_DEFECT),
        },
    )


@never_cache
@requires(Action.RECORD_DEFECT)
@require_http_methods(["GET", "POST"])
def record_defect(request: HttpRequest) -> HttpResponse:
    """Record a defect and what was decided of it (REQ-220 to REQ-222)."""
    initial = {}
    try:
        chosen = uuid.UUID(request.GET.get("aircraft", ""))
    except ValueError:
        chosen = None
    if chosen is not None:
        initial["aircraft"] = Aircraft.objects.filter(pk=chosen).first()
    form = DefectForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        values = dict(form.cleaned_data)
        aircraft = values.pop("aircraft")
        try:
            defect = services.record_defect(aircraft, **values)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("defect", defect_id=defect.id)
    return render(
        request,
        "defects/record.html",
        {"form": form, "limits": configuration.deferral_lines(_user(request).organisation)},
    )


def _defect_page(request: HttpRequest, defect: Defect, form: CloseForm) -> HttpResponse:
    return render(
        request,
        "defects/defect.html",
        {
            "defect": defect,
            "flight_reports": FlightReport.objects.filter(defect=defect),
            "line": services.defect_line(defect, aircraft_services.today()),
            "form": form,
            "may_record": _user(request).may(Action.RECORD_DEFECT),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def defect_page(request: HttpRequest, defect_id: uuid.UUID) -> HttpResponse:
    """One defect: what was found, what was decided, its limit and its rectification."""
    defect = get_object_or_404(Defect.objects.select_related("aircraft"), pk=defect_id)
    return _defect_page(request, defect, CloseForm(aircraft=defect.aircraft))


@never_cache
@requires(Action.RECORD_DEFECT)
@require_POST
def close_defect(request: HttpRequest, defect_id: uuid.UUID) -> HttpResponse:
    """Record that a defect is rectified (REQ-224)."""
    defect = get_object_or_404(Defect.objects.select_related("aircraft"), pk=defect_id)
    form = CloseForm(request.POST, aircraft=defect.aircraft)
    if form.is_valid():
        try:
            services.close_defect(defect, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("defect", defect_id=defect.id)
    defect.refresh_from_db()
    return _defect_page(request, defect, form)


def _repeat_page(request: HttpRequest, form: RepeatActionForm) -> HttpResponse:
    return render(
        request,
        "defects/repeat.html",
        {
            "lines": services.repeat_lines(aircraft_services.today()),
            "form": form,
            "may_record": _user(request).may(Action.RECORD_REPEAT_DEFECT_ACTION),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def repeat_defects(request: HttpRequest) -> HttpResponse:
    """The same defect on one type in 12 months, and the action taken (REQ-226, REQ-227)."""
    return _repeat_page(request, RepeatActionForm())


@never_cache
@requires(Action.RECORD_REPEAT_DEFECT_ACTION)
@require_POST
def record_repeat_action(request: HttpRequest) -> HttpResponse:
    """Record what was done about a repeat defect (REQ-227)."""
    form = RepeatActionForm(request.POST)
    if form.is_valid():
        try:
            services.record_repeat_action(_user(request).organisation, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("repeat_defects")
    return _repeat_page(request, form)
