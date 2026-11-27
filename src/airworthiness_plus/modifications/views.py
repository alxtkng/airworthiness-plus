"""Pages for Modifications and Repairs and for Weight and Balance (REQ-249 to REQ-259).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A record of another organisation is
not found, because the database does not show it (REQ-003).
"""

import uuid
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.modifications import services
from airworthiness_plus.modifications.forms import (
    BulletinForm,
    ChangeForm,
    DecisionForm,
    EmbodiedForm,
    ScheduleForm,
    WeighingForm,
)
from airworthiness_plus.modifications.models import Bulletin, Change


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def modifications_page(request: HttpRequest) -> HttpResponse:
    """Service bulletin decisions, and every change or repair (REQ-253)."""
    user = _user(request)
    return render(
        request,
        "modifications/modifications.html",
        {
            "bulletins": services.bulletin_lines(user.organisation, aircraft_services.today()),
            "changes": services.change_lines(),
            "may_record": user.may(Action.RECORD_AIRCRAFT_CONFIGURATION),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def weight_and_balance(request: HttpRequest) -> HttpResponse:
    """Each aircraft's last weighing, weight schedule and mass change since (REQ-256)."""
    user = _user(request)
    return render(
        request,
        "modifications/weight.html",
        {
            "lines": services.weight_lines(),
            "threshold": user.organisation.reweigh_threshold_kilograms,
            "may_record": user.may(Action.RECORD_AIRCRAFT_CONFIGURATION),
        },
    )


def _recorded(
    request: HttpRequest,
    form: Form,
    record: Callable[..., object],
    *,
    title: str,
    button: str,
    back: str,
    note: str = "",
) -> HttpResponse:
    """Show a form, and record what it holds for the aircraft chosen once it is valid."""
    if request.method == "POST" and form.is_valid():
        values = dict(form.cleaned_data)
        try:
            record(values.pop("aircraft"), **values)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect(back)
    return render(
        request,
        "modifications/form.html",
        {"form": form, "title": title, "button": button, "note": note},
    )


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_http_methods(["GET", "POST"])
def record_bulletin(request: HttpRequest) -> HttpResponse:
    """Record a service bulletin sent to the owner, with the decision if it is made (REQ-249)."""
    return _recorded(
        request,
        BulletinForm(request.POST or None),
        services.record_bulletin,
        title="Record a Service Bulletin",
        button="Record Service Bulletin",
        back="modifications",
    )


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_http_methods(["GET", "POST"])
def record_change(request: HttpRequest) -> HttpResponse:
    """Record a change or repair, embodied or in progress (REQ-251)."""
    return _recorded(
        request,
        ChangeForm(request.POST or None),
        services.record_change,
        title="Record a Change",
        button="Record Change or Repair",
        back="modifications",
        note="Modifications and Repairs Are Carried Out Using Data Approved by the Civil "
        "Aviation Authority or by a Design Organisation, or Contained in the Requirements "
        "of Point 21.A.90B or 21.A.431B, ML.A.304",
    )


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_http_methods(["GET", "POST"])
def record_weighing(request: HttpRequest) -> HttpResponse:
    """Record a weighing of an aircraft (REQ-254)."""
    return _recorded(
        request,
        WeighingForm(request.POST or None),
        services.record_weighing,
        title="Record a Weighing",
        button="Record Weighing",
        back="weight_and_balance",
    )


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_http_methods(["GET", "POST"])
def record_weight_schedule(request: HttpRequest) -> HttpResponse:
    """Record an issue of an aircraft's weight schedule (REQ-254)."""
    return _recorded(
        request,
        ScheduleForm(request.POST or None),
        services.record_schedule,
        title="Record a Weight Schedule Issue",
        button="Record Weight Schedule Issue",
        back="weight_and_balance",
    )


def _one(
    request: HttpRequest,
    record: Any,
    form: Form,
    change: Callable[..., object],
    *,
    title: str,
    button: str,
) -> HttpResponse:
    if request.method == "POST" and form.is_valid():
        try:
            change(record, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("modifications")
    return render(
        request,
        "modifications/form.html",
        {
            "form": form,
            "title": title,
            "button": button,
            "note": f"{record.aircraft.registration}, {record.title}",
        },
    )


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_http_methods(["GET", "POST"])
def decide_bulletin(request: HttpRequest, bulletin_id: uuid.UUID) -> HttpResponse:
    """Record what the owner decided of a service bulletin (REQ-250)."""
    bulletin = get_object_or_404(Bulletin.objects.select_related("aircraft"), pk=bulletin_id)
    return _one(
        request,
        bulletin,
        DecisionForm(request.POST or None),
        services.decide_bulletin,
        title="Record the Owner Decision",
        button="Record Owner Decision",
    )


@never_cache
@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_http_methods(["GET", "POST"])
def embody_change(request: HttpRequest, change_id: uuid.UUID) -> HttpResponse:
    """Record the day a change or repair in progress was embodied (REQ-252)."""
    change = get_object_or_404(Change.objects.select_related("aircraft"), pk=change_id)
    return _one(
        request,
        change,
        EmbodiedForm(request.POST or None),
        services.embody_change,
        title="Record a Change as Embodied",
        button="Record as Embodied",
    )
