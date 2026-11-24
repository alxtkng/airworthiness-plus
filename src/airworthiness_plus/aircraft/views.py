"""Pages for the Fleet, Transfers and one aircraft.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). An aircraft of another organisation
is not found, because the database does not show it (REQ-003).
"""

import uuid
from dataclasses import dataclass
from datetime import date

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
    DetailsForm,
    OwnerForm,
    RecordsReceivedForm,
    UnserviceableForm,
    UtilisationForm,
)
from airworthiness_plus.aircraft.models import (
    Aircraft,
    Counter,
    CounterKind,
    Regime,
    Stage,
    Status,
)
from airworthiness_plus.customers import services as customer_services
from airworthiness_plus.interface import formatting
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Limit, Reading, Unit
from airworthiness_rules.programme import Flag, limit_flag
from airworthiness_rules.utilisation import EntryRefusedError


@dataclass(frozen=True)
class FleetRow:
    """One line of the Fleet: the aircraft, what is due next and its airframe total."""

    aircraft: Aircraft
    airframe: Reading | None
    next_due: str
    review_valid_to: date | None
    # Where the aircraft comes in the Fleet: what needs attention first.
    rank: tuple[int, int, int, str] = (0, 0, 0, "")


def _airframe(aircraft: Aircraft) -> Reading | None:
    counter = aircraft.counters.filter(kind=CounterKind.AIRFRAME).first()
    return services.current_reading(counter) if counter is not None else None


# The order of the Fleet (dogfooding D-5): how serious a mark is, worst first.
SEVERITY = {
    Flag.OVERDUE: 4,
    Flag.WITHIN_TOLERANCE: 3,
    Flag.DUE: 2,
    Flag.DUE_SOON: 1,
    Flag.NONE: 0,
}
CANNOT_BE_CALCULATED = 5
NOT_KNOWN = 1_000_000


def _next_due(
    aircraft: Aircraft, today: date, review_valid_to: date | None
) -> tuple[str, tuple[int, int, int, str]]:
    """Return what is due next on the aircraft, and where it comes in the Fleet.

    The first value is as the Fleet shows it (REQ-043, REQ-044, REQ-100).
    The second puts the Fleet in order: an Unserviceable aircraft, then
    whatever is marked with the worst mark first, then the soonest due by
    the projected days, then by Aircraft Registration. An aircraft with a
    task that cannot be calculated comes before every mark: nobody knows
    where it stands.

    An Unserviceable aircraft is to be rectified before anything else. The
    airworthiness review is set beside the tasks of the programme by its
    days remaining; the order across tasks is a projection from the
    planning utilisation, and when a task cannot be placed in it the Fleet
    says so.
    """
    from airworthiness_plus.programme import due

    registration = aircraft.registration
    if aircraft.status == Status.UNSERVICEABLE:
        return "Rectify Defect", (0, 0, 0, registration)
    thresholds = due.thresholds_of(aircraft.organisation)
    lines = due.due_lines(aircraft, today)
    first, complete = due.next_due(lines)
    candidates: list[tuple[int, str]] = []
    unranked = bool(lines) and not first
    severity = max(
        (CANNOT_BE_CALCULATED if line.needs_attention else SEVERITY[line.flag] for line in lines),
        default=0,
    )
    if first:
        urgent = any(line.needs_attention or line.reached for line in first)
        projected = [limit.projected for line in first for limit in line.first]
        known = [value for value in projected if value is not None]
        days = -1 if urgent or not known else min(known)
        text = "; ".join(line.summary for line in first)
        candidates.append((days, text if complete else f"{text}; Other Tasks Not Ranked"))
    if review_valid_to is not None:
        remaining = days_between(today, review_valid_to)
        review = f"Airworthiness Review, {formatting.amount(Unit.CALENDAR, remaining)}"
        candidates.append((min(remaining, -1) if remaining <= 0 else remaining, review))
        expiry = Limit(Unit.CALENDAR, review_valid_to, remaining)
        severity = max(severity, SEVERITY[limit_flag(expiry, thresholds)])
    else:
        # No certificate recorded: nobody knows where the aircraft stands, so it
        # comes with what cannot be calculated, as it comes first on the review schedule.
        severity = CANNOT_BE_CALCULATED
    if not candidates:
        text = "Not Ranked, No Planning Utilisation" if unranked else ""
        return text, (1, -severity, NOT_KNOWN, registration)
    soonest = min(days for days, _ in candidates)
    shown = "; ".join(text for days, text in candidates if days == soonest)
    if unranked:
        shown = f"{shown}; Tasks Not Ranked, No Planning Utilisation"
    return shown, (1, -severity, soonest, registration)


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def fleet(request: HttpRequest) -> HttpResponse:
    """The Fleet: aircraft under management (Decisions.md, Interface)."""
    today = services.today()
    from airworthiness_plus.reviews import services as review_services

    rows = []
    for aircraft in Aircraft.objects.filter(stage=Stage.FLEET).select_related("customer"):
        valid_to = review_services.current_valid_to(aircraft)
        next_due, rank = _next_due(aircraft, today, valid_to)
        rows.append(FleetRow(aircraft, _airframe(aircraft), next_due, valid_to, rank))
    # What needs attention first (dogfooding D-5). A column heading sorts it another way.
    rows.sort(key=lambda row: row.rank)
    return render(request, "aircraft/fleet.html", {"rows": rows})


@never_cache
@requires(Action.VIEW_RECORDS)
def transfers(request: HttpRequest) -> HttpResponse:
    """Transfers: aircraft whose records are not yet complete (REQ-027)."""
    aircraft = Aircraft.objects.filter(stage=Stage.TRANSFER_IN).select_related("customer")
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
    details = DetailsForm(
        initial={
            "serial_number": aircraft.serial_number,
            "manufacturer": aircraft.manufacturer,
            "designation": aircraft.designation,
        }
    )
    return render(
        request,
        "aircraft/aircraft.html",
        {
            "aircraft": aircraft,
            "counters": counters,
            "details_form": details,
            "owner_form": OwnerForm(initial={"customer": aircraft.customer_id}),
        },
    )


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_POST
def change_owner(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record another customer as the owner of an aircraft (REQ-208)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = OwnerForm(request.POST)
    if form.is_valid():
        services.change_owner(aircraft, form.cleaned_data["customer"])
    return redirect("aircraft", aircraft_id=aircraft.id)


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_POST
def record_details(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record the serial number, manufacturer and designation of an aircraft."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = DetailsForm(request.POST)
    if form.is_valid():
        services.record_details(aircraft, **form.cleaned_data)
    return redirect("aircraft", aircraft_id=aircraft.id)


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
                    manufacturer=data["manufacturer"],
                    designation=data["designation"],
                    owner=data["owner"],
                    customer=data["customer"],
                    regime=Regime(data["regime"]),
                    airframe=airframe,
                    records_expected=data["records_expected"],
                )
        except (EntryRefusedError, customer_services.RefusedError) as error:
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
