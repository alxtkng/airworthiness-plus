"""Pages for the maintenance programme of one aircraft.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). An aircraft, task or record of
another organisation is not found (REQ-003).
"""

import uuid
from collections.abc import Callable
from datetime import date

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.programme import due, services
from airworthiness_plus.programme.forms import (
    AnnualReviewForm,
    CompleteReviewForm,
    DepartureDateForm,
    DepartureForm,
    ProgrammeForm,
    ReviewForm,
    TaskForm,
    WorkForm,
)
from airworthiness_plus.programme.models import (
    AnnualReview,
    Basis,
    Departure,
    Programme,
    Task,
    WorkDone,
)
from airworthiness_plus.reviews import services as review_services
from airworthiness_rules.intervals import Interval, Reading, TaskKind


def _interval(data: dict[str, object], prefix: str) -> Interval | None:
    """Build an interval from form fields, or None if none of them is filled."""
    values = {unit: data.get(f"{prefix}_{unit}") for unit in ("hours", "cycles", "months", "days")}
    if all(value is None for value in values.values()):
        return None
    return Interval(**values)  # type: ignore[arg-type]


@never_cache
@requires(Action.VIEW_RECORDS)
def programme_page(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """The programme of one aircraft: what is due, with the working, and the work done."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    programme = Programme.objects.filter(aircraft=aircraft).first()
    today = aircraft_services.today()
    lines = due.due_lines(aircraft, today, review_services.current_valid_to(aircraft))
    review = (
        due.review_line(programme, today, due.thresholds_of(aircraft.organisation))
        if programme
        else None
    )
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return render(
        request,
        "programme/programme.html",
        {
            "aircraft": aircraft,
            "programme": programme,
            "lines": lines,
            "review": review,
            "work": due.work_lines(aircraft, today),
            "today": today,
            "may_record_work": user.may(Action.RECORD_ACCOMPLISHMENT),
            "may_change": user.may(Action.CHANGE_MAINTENANCE_PROGRAMME),
            **_review_parts(request, programme),
        },
    )


def _review_parts(request: HttpRequest, programme: Programme | None) -> dict[str, object]:
    """Return the departures and the annual review of a programme, for its page."""
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    if programme is None:
        return {}
    review = services.open_annual_review(programme)
    initial: dict[str, object] = {}
    if review is not None:
        for name, _, _, note, done in review.points:
            initial[f"{name}_note"] = note
            initial[f"{name}_done"] = done
    return {
        "departures": Departure.objects.filter(programme=programme).order_by(
            "withdrawn_on", "recorded_on", "task"
        ),
        "annual_review": review,
        "annual_form": AnnualReviewForm(initial=initial),
        "completed_reviews": AnnualReview.objects.filter(
            programme=programme, completed_on__isnull=False
        ).order_by("-completed_on"),
        "may_review": user.may(Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW),
    }


@never_cache
@requires(Action.CHANGE_MAINTENANCE_PROGRAMME)
@require_http_methods(["GET", "POST"])
def set_up_programme(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record or change the programme of an aircraft (REQ-040)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    existing = Programme.objects.filter(aircraft=aircraft).first()
    initial = (
        {
            "basis": existing.basis,
            "inspection_category": existing.inspection_category,
            "reference": existing.reference,
            "hours_per_day": existing.hours_per_day,
            "cycles_per_day": existing.cycles_per_day,
        }
        if existing
        else None
    )
    form = ProgrammeForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.set_up_programme(
                aircraft,
                basis=Basis(data["basis"]),
                reference=data["reference"],
                inspection_category=data["inspection_category"],
                hours_per_day=data["hours_per_day"] or None,
                cycles_per_day=data["cycles_per_day"] or None,
            )
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("programme", aircraft_id=aircraft.id)
    return render(
        request,
        "programme/form.html",
        {
            "aircraft": aircraft,
            "form": form,
            "title": "Maintenance Programme",
            "button": "Save Programme",
        },
    )


@never_cache
@requires(Action.CHANGE_MAINTENANCE_PROGRAMME)
@require_http_methods(["GET", "POST"])
def add_task(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Add a task to the programme (REQ-041)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    programme = get_object_or_404(Programme, aircraft=aircraft)
    form = TaskForm(request.POST or None, aircraft_id=aircraft.id)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        starts = (
            Reading(data["starts_dated"], data["starts_hours"], data["starts_cycles"])
            if data["starts_dated"] is not None
            and data["starts_hours"] is not None
            and data["starts_cycles"] is not None
            else None
        )
        try:
            interval = _interval(data, "interval")
            if interval is None:
                raise services.RefusedError("A Task Has an Interval")
            services.add_task(
                programme,
                title=data["title"],
                kind=TaskKind(data["kind"]),
                counter=data["counter"],
                source=data["source"],
                interval=interval,
                first=_interval(data, "first"),
                starts=starts,
            )
        except ValueError as error:
            form.add_error(None, str(error))
        else:
            return redirect("programme", aircraft_id=aircraft.id)
    return render(
        request,
        "programme/form.html",
        {"aircraft": aircraft, "form": form, "title": "Add a Task", "button": "Add Task"},
    )


@requires(Action.CHANGE_MAINTENANCE_PROGRAMME)
@require_POST
def retire_task(request: HttpRequest, task_id: uuid.UUID) -> HttpResponse:
    """Take a task out of the programme. It stays in the record."""
    task = get_object_or_404(Task, pk=task_id)
    try:
        services.retire_task(task)
    except services.RefusedError as error:
        return HttpResponse(str(error), status=409, content_type="text/plain; charset=utf-8")
    return redirect("programme", aircraft_id=task.programme.aircraft_id)


@requires(Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW)
@require_POST
def record_review(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record the annual review of the programme (REQ-053)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    programme = get_object_or_404(Programme, aircraft=aircraft)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return _refused(request, aircraft, "Give the Day the Programme Was Reviewed")
    try:
        services.record_review(programme, form.cleaned_data["reviewed_on"])
    except services.RefusedError as error:
        return _refused(request, aircraft, str(error))
    return redirect("programme", aircraft_id=aircraft.id)


@never_cache
@requires(Action.RECORD_ACCOMPLISHMENT)
@require_http_methods(["GET", "POST"])
def record_work(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record work done on the aircraft (REQ-050 to REQ-052)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = WorkForm(request.POST or None, aircraft_id=aircraft.id)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            services.record_work(
                aircraft,
                task=data["task"],
                description=data["description"],
                dated=data["dated"],
                hours=data["hours"],
                cycles=data["cycles"],
                performed_by=data["performed_by"],
                by_pilot_owner=data["by_pilot_owner"],
                pilot_owner_told_on=data["pilot_owner_told_on"],
            )
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("programme", aircraft_id=aircraft.id)
    return render(
        request,
        "programme/form.html",
        {"aircraft": aircraft, "form": form, "title": "Record Work Done", "button": "Record Work"},
    )


@requires(Action.RECORD_ACCOMPLISHMENT)
@require_POST
def record_release(request: HttpRequest, work_id: uuid.UUID) -> HttpResponse:
    """Open the certificate of release to service form (REQ-051)."""
    work = get_object_or_404(WorkDone, pk=work_id)
    return redirect("record_release_certificate", work_id=work.id)


@never_cache
@requires(Action.VIEW_RECORDS)
def programmes_page(request: HttpRequest) -> HttpResponse:
    """The maintenance programme of every aircraft of the Fleet (REQ-283)."""
    lines = due.programme_lines(aircraft_services.today())
    return render(request, "programme/programmes.html", {"lines": lines})


def _refused(request: HttpRequest, aircraft: Aircraft, reason: str) -> HttpResponse:
    """Say why something of a programme was refused, with the way back to the programme."""
    return render(
        request,
        "programme/refused.html",
        {"aircraft": aircraft, "reason": reason},
        status=409,
    )


@never_cache
@requires(Action.CHANGE_MAINTENANCE_PROGRAMME)
@require_http_methods(["GET", "POST"])
def add_departure(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record a departure from the manufacturer's instructions (REQ-284)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    programme = get_object_or_404(Programme, aircraft=aircraft)
    form = DepartureForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.add_departure(programme, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("programme", aircraft_id=aircraft.id)
    return render(request, "programme/departure.html", {"aircraft": aircraft, "form": form})


def _departure_dated(
    request: HttpRequest, departure_id: uuid.UUID, record: Callable[[Departure, date], object]
) -> HttpResponse:
    departure = get_object_or_404(
        Departure.objects.select_related("programme__aircraft"), pk=departure_id
    )
    aircraft = departure.programme.aircraft
    form = DepartureDateForm(request.POST)
    if not form.is_valid():
        return _refused(request, aircraft, "Give the Date")
    try:
        record(departure, form.cleaned_data["on"])
    except services.RefusedError as error:
        return _refused(request, aircraft, str(error))
    return redirect("programme", aircraft_id=aircraft.id)


@requires(Action.CHANGE_MAINTENANCE_PROGRAMME)
@require_POST
def departure_copy_sent(request: HttpRequest, departure_id: uuid.UUID) -> HttpResponse:
    """Record the day a copy of a departure went to the owner (REQ-285)."""
    return _departure_dated(request, departure_id, services.departure_copy_sent)


@requires(Action.CHANGE_MAINTENANCE_PROGRAMME)
@require_POST
def withdraw_departure(request: HttpRequest, departure_id: uuid.UUID) -> HttpResponse:
    """Record that a departure no longer stands (REQ-285)."""
    return _departure_dated(request, departure_id, services.withdraw_departure)


@requires(Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW)
@require_POST
def start_annual_review(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Open the annual review of the programme (REQ-286)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    programme = get_object_or_404(Programme, aircraft=aircraft)
    try:
        services.start_annual_review(programme)
    except services.RefusedError as error:
        return _refused(request, aircraft, str(error))
    return redirect("programme", aircraft_id=aircraft.id)


def _open_review(aircraft_id: uuid.UUID) -> tuple[Aircraft, AnnualReview | None]:
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    programme = get_object_or_404(Programme, aircraft=aircraft)
    return aircraft, services.open_annual_review(programme)


@requires(Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW)
@require_POST
def note_annual_review(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record what was found on each point of the annual review (REQ-286)."""
    aircraft, review = _open_review(aircraft_id)
    form = AnnualReviewForm(request.POST)
    if review is None:
        return _refused(request, aircraft, "No Annual Review Is in Progress")
    if not form.is_valid():
        return _refused(request, aircraft, "A Note Is at Most 300 Characters")
    try:
        services.note_annual_review(review, **form.cleaned_data)
    except services.RefusedError as error:
        return _refused(request, aircraft, str(error))
    return redirect("programme", aircraft_id=aircraft.id)


@requires(Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW)
@require_POST
def complete_annual_review(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Complete the annual review and record the programme as reviewed (REQ-287)."""
    aircraft, review = _open_review(aircraft_id)
    form = CompleteReviewForm(request.POST)
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    if review is None:
        return _refused(request, aircraft, "No Annual Review Is in Progress")
    if not form.is_valid():
        return _refused(request, aircraft, "Give the Day the Review Was Completed")
    try:
        services.complete_annual_review(review, by=user, **form.cleaned_data)
    except services.RefusedError as error:
        return _refused(request, aircraft, str(error))
    return redirect("programme", aircraft_id=aircraft.id)
