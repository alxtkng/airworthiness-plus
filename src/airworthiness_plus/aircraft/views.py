"""Pages for the Fleet, Transfers and one aircraft.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). An aircraft of another organisation
is not found, because the database does not show it (REQ-003).
"""

import uuid
from dataclasses import dataclass

from django.db import DatabaseError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services
from airworthiness_plus.aircraft.forms import (
    AddAircraftForm,
    CounterForm,
    RecordsReceivedForm,
    UnserviceableForm,
    UtilisationForm,
)
from airworthiness_plus.aircraft.models import Aircraft, Counter, CounterKind, Regime, Stage
from airworthiness_rules.intervals import Reading
from airworthiness_rules.utilisation import EntryRefusedError


@dataclass(frozen=True)
class FleetRow:
    """One line of the Fleet: the aircraft and its current airframe total."""

    aircraft: Aircraft
    airframe: Reading | None


def _airframe(aircraft: Aircraft) -> Reading | None:
    counter = aircraft.counters.filter(kind=CounterKind.AIRFRAME).first()
    return services.current_reading(counter) if counter is not None else None


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def fleet(request: HttpRequest) -> HttpResponse:
    """The Fleet: aircraft under management (Decisions.md, Interface)."""
    rows = [FleetRow(a, _airframe(a)) for a in Aircraft.objects.filter(stage=Stage.FLEET)]
    return render(request, "aircraft/fleet.html", {"rows": rows})


@never_cache
@requires(Action.VIEW_RECORDS)
def transfers(request: HttpRequest) -> HttpResponse:
    """Transfers: aircraft whose records are not yet complete (REQ-027)."""
    aircraft = Aircraft.objects.filter(stage=Stage.TRANSFER_IN)
    return render(request, "aircraft/transfers.html", {"aircraft": aircraft})


@never_cache
@requires(Action.VIEW_RECORDS)
def aircraft_page(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """One aircraft: its record, its counters and every entry of hours and cycles."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    counters = [
        (counter, services.current_reading(counter), list(counter.entries.all()))
        for counter in aircraft.counters.all()
    ]
    return render(request, "aircraft/aircraft.html", {"aircraft": aircraft, "counters": counters})


@never_cache
@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_http_methods(["GET", "POST"])
def add_aircraft(request: HttpRequest) -> HttpResponse:
    """Add an aircraft."""
    form = AddAircraftForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        airframe = (
            Reading(data["dated"], data["hours"], data["cycles"])
            if data["hours"] is not None
            else None
        )
        try:
            with transaction.atomic():
                aircraft = services.add_aircraft(
                    organisation=_user(request).organisation,
                    registration=data["registration"],
                    type_rating=data["type_rating"],
                    serial_number=data["serial_number"],
                    owner=data["owner"],
                    regime=Regime(data["regime"]),
                    airframe=airframe,
                    records_expected=data["records_expected"],
                )
        except EntryRefusedError as error:
            form.add_error(None, str(error))
        except DatabaseError:
            form.add_error("registration", "This Aircraft Registration Is Already Recorded")
        else:
            return redirect("aircraft", aircraft_id=aircraft.id)
    return render(request, "aircraft/add_aircraft.html", {"form": form})


@never_cache
@requires(Action.ENTER_UTILISATION)
@require_http_methods(["GET", "POST"])
def enter_utilisation(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Enter hours and cycles. The page names the aircraft throughout (REQ-026)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = UtilisationForm(request.POST or None, aircraft_id=aircraft.id)
    needs_confirmation = False
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with transaction.atomic():
                services.enter_utilisation(
                    data["counter"],
                    Reading(data["dated"], data["hours"], data["cycles"]),
                    confirmed=data["confirmed"],
                    supersedes=data["supersedes"],
                )
        except services.ConfirmationNeededError:
            needs_confirmation = True
        except EntryRefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("aircraft", aircraft_id=aircraft.id)
    return render(
        request,
        "aircraft/utilisation.html",
        {"aircraft": aircraft, "form": form, "needs_confirmation": needs_confirmation},
    )


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_http_methods(["GET", "POST"])
def make_unserviceable(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record the aircraft as Unserviceable, with a reason and a date (REQ-023)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = UnserviceableForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        services.make_unserviceable(
            aircraft, form.cleaned_data["reason"], form.cleaned_data["since"]
        )
        return redirect("aircraft", aircraft_id=aircraft.id)
    return render(request, "aircraft/unserviceable.html", {"aircraft": aircraft, "form": form})


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_POST
def make_serviceable(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record the aircraft as Serviceable (REQ-023)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    services.make_serviceable(aircraft)
    return redirect("aircraft", aircraft_id=aircraft.id)


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_http_methods(["GET", "POST"])
def add_counter(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Add an engine or a propeller as a counter (REQ-020)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = CounterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        exists = Counter.objects.filter(
            aircraft=aircraft, kind=data["kind"], position=data["position"]
        ).exists()
        if exists:
            form.add_error("position", "This Position Is Already Recorded")
        else:
            services.add_counter(
                aircraft, CounterKind(data["kind"]), data["position"], data["serial_number"]
            )
            return redirect("aircraft", aircraft_id=aircraft.id)
    return render(request, "aircraft/counter.html", {"aircraft": aircraft, "form": form})


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_POST
def records_received(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Update the count of records received, and move a complete transfer to the Fleet."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id, stage=Stage.TRANSFER_IN)
    form = RecordsReceivedForm(request.POST)
    expected = aircraft.records_expected or 0
    if form.is_valid() and form.cleaned_data["received"] <= expected:
        services.record_received(aircraft, form.cleaned_data["received"])
        if request.POST.get("complete") == "Yes":
            try:
                services.complete_transfer(aircraft)
            except services.TransferNotCompleteError:
                return redirect("transfers")
            return redirect("aircraft", aircraft_id=aircraft.id)
    return redirect("transfers")
