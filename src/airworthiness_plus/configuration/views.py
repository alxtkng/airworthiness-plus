"""Pages for Transfers and Set Up Configuration (REQ-267 to REQ-279).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A record of another organisation is
not found, because the database does not show it (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Stage
from airworthiness_plus.components import services as component_services
from airworthiness_plus.components.models import Installation
from airworthiness_plus.configuration import forecast, services
from airworthiness_plus.configuration.forms import ItemForm, PositionForm, RecordPositionForm
from airworthiness_plus.configuration.models import Baseline, Position, TransferItem
from airworthiness_plus.modifications import services as modification_services
from airworthiness_rules.forecast import WINDOW_DAYS


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


def _refused(request: HttpRequest, reason: str, back: str, *args: object) -> HttpResponse:
    """Say why something was refused, with the way back."""
    return render(
        request,
        "configuration/refused.html",
        {"reason": reason, "back": back, "arguments": args},
        status=409,
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def transfers_page(request: HttpRequest) -> HttpResponse:
    """Transfers in, each with its checklist, and transfer out by export (REQ-267, REQ-276)."""
    user = _user(request)
    today = aircraft_services.today()
    coming = [
        (aircraft, services.transfer_line(aircraft, today))
        for aircraft in Aircraft.objects.filter(stage=Stage.TRANSFER_IN).select_related("customer")
    ]
    return render(
        request,
        "configuration/transfers.html",
        {
            "coming": coming,
            "may_change": user.may(Action.ADD_OR_CHANGE_AIRCRAFT),
            "may_export": user.may(Action.EXPORT_RECORDS),
            "item_form": ItemForm(),
        },
    )


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_POST
def start_transfer(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Start the checklist of a transfer in (REQ-267)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    try:
        services.start_transfer(aircraft)
    except services.RefusedError as error:
        return _refused(request, str(error), "transfers")
    return redirect("transfers")


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_POST
def set_transfer_item(request: HttpRequest, item_id: uuid.UUID) -> HttpResponse:
    """Record where an item of a transfer in stands (REQ-268)."""
    item = get_object_or_404(TransferItem, pk=item_id)
    form = ItemForm(request.POST)
    if not form.is_valid():
        return _refused(request, "Choose Where the Item Stands", "transfers")
    try:
        services.set_item(item, **form.cleaned_data)
    except services.RefusedError as error:
        return _refused(request, str(error), "transfers")
    return redirect("transfers")


@never_cache
@requires(Action.VIEW_RECORDS)
def set_up_configuration(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """The six steps that set up the configuration of an aircraft (REQ-272)."""
    aircraft = get_object_or_404(Aircraft.objects.select_related("customer"), pk=aircraft_id)
    user = _user(request)
    today = aircraft_services.today()
    found = services.set_up(aircraft, today)
    major = [
        (
            position,
            component_services.component_line(position.component, today)
            if position.component is not None
            else None,
        )
        for position in found.major
    ]
    return render(
        request,
        "configuration/set_up.html",
        {
            "aircraft": aircraft,
            "set_up": found,
            "major": major,
            "airframe": component_services.airframe(aircraft),
            "today": today,
            "baselines": Baseline.objects.filter(aircraft=aircraft).order_by("-signed_on"),
            "may_record": user.may(Action.RECORD_AIRCRAFT_CONFIGURATION),
            "may_sign": user.may(Action.SIGN_CONFIGURATION_BASELINE),
            "position_form": PositionForm(),
            "record_form": RecordPositionForm(aircraft=aircraft),
        },
    )


@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_POST
def add_position(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Add a position to the configuration of an aircraft (REQ-270)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = PositionForm(request.POST)
    if not form.is_valid():
        return _refused(
            request,
            "A Position Has a Product, a Chapter From 1 to 99 and a Name",
            "set_up_configuration",
            aircraft.id,
        )
    try:
        services.add_position(aircraft, **form.cleaned_data)
    except services.RefusedError as error:
        return _refused(request, str(error), "set_up_configuration", aircraft.id)
    return redirect("set_up_configuration", aircraft_id=aircraft.id)


@requires(Action.RECORD_AIRCRAFT_CONFIGURATION)
@require_POST
def record_position(request: HttpRequest, position_id: uuid.UUID) -> HttpResponse:
    """Record what is fitted at a position, and where that was read (REQ-271)."""
    position = get_object_or_404(Position.objects.select_related("aircraft"), pk=position_id)
    aircraft = position.aircraft
    form = RecordPositionForm(request.POST, aircraft=aircraft)
    if not form.is_valid():
        return _refused(
            request,
            "Say Where What Is Fitted Was Read, and Choose a Change and a Component "
            "of This Aircraft",
            "set_up_configuration",
            aircraft.id,
        )
    try:
        services.record_position(position, **form.cleaned_data)
    except services.RefusedError as error:
        return _refused(request, str(error), "set_up_configuration", aircraft.id)
    return redirect("set_up_configuration", aircraft_id=aircraft.id)


@requires(Action.SIGN_CONFIGURATION_BASELINE)
@require_POST
def sign_baseline(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Sign the configuration baseline of an aircraft (REQ-273)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    try:
        baseline = services.sign_baseline(aircraft, by=_user(request))
    except services.RefusedError as error:
        return _refused(request, str(error), "set_up_configuration", aircraft.id)
    return redirect("baseline", baseline_id=baseline.id)


@never_cache
@requires(Action.VIEW_RECORDS)
def baseline_page(request: HttpRequest, baseline_id: uuid.UUID) -> HttpResponse:
    """A signed configuration baseline, as it was signed (REQ-274)."""
    baseline = get_object_or_404(Baseline, pk=baseline_id)
    return render(
        request,
        "configuration/baseline.html",
        {
            "baseline": baseline,
            "positions": services.signed_positions(baseline),
            "changes": services.signed_changes(baseline),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def aircraft_forecast(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """The forecast of one aircraft: everything that falls due, the soonest first (REQ-290)."""
    aircraft = get_object_or_404(Aircraft.objects.select_related("customer"), pk=aircraft_id)
    today = aircraft_services.today()
    lines = forecast.forecast_lines(aircraft, today) if aircraft.calculations_supported else []
    return render(
        request,
        "configuration/forecast.html",
        {
            "aircraft": aircraft,
            "lines": lines,
            "soon": forecast.next_days(lines, today),
            "window": WINDOW_DAYS,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def aircraft_configuration(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """The configuration of one aircraft: its positions, components and changes (REQ-292)."""
    aircraft = get_object_or_404(Aircraft.objects.select_related("customer"), pk=aircraft_id)
    today = aircraft_services.today()
    positions = forecast.position_lines(aircraft, today)
    chosen = request.GET.get("show", "")
    if chosen not in dict(forecast.FILTERS):
        chosen = ""
    filters = [
        (key, label, sum(1 for line in positions if line.shown_for(key)), key == chosen)
        for key, label in forecast.FILTERS
    ]
    return render(
        request,
        "configuration/aircraft.html",
        {
            "aircraft": aircraft,
            "positions": [line for line in positions if line.shown_for(chosen)],
            "any_position": bool(positions),
            "filters": filters,
            "baseline": services.last_baseline(aircraft),
            "components": component_services.component_lines(today, aircraft),
            "fittings": Installation.objects.filter(aircraft=aircraft)
            .select_related("component")
            .order_by("-fitted_on", "component__name"),
            "changes": modification_services.change_lines(aircraft),
            "weight": modification_services.weight_line(aircraft),
        },
    )
