"""Pages for the maintenance programme of one aircraft.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). An aircraft, task or record of
another organisation is not found (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.programme import due, services
from airworthiness_plus.programme.forms import (
    ProgrammeForm,
    ReleaseForm,
    ReviewForm,
    TaskForm,
    WorkForm,
)
from airworthiness_plus.programme.models import Basis, Programme, Task, WorkDone
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
        },
    )


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
    services.retire_task(task)
    return redirect("programme", aircraft_id=task.programme.aircraft_id)


@requires(Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW)
@require_POST
def record_review(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record the annual review of the programme (REQ-053)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    programme = get_object_or_404(Programme, aircraft=aircraft)
    form = ReviewForm(request.POST)
    if form.is_valid():
        try:
            services.record_review(programme, form.cleaned_data["reviewed_on"])
        except services.RefusedError:
            pass
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
                release_reference=data["release_reference"],
                release_recorded_on=data["release_recorded_on"],
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
    """Record that the certificate of release to service is in the records (REQ-051)."""
    work = get_object_or_404(WorkDone, pk=work_id)
    form = ReleaseForm(request.POST)
    if form.is_valid():
        services.record_release(work, form.cleaned_data["release_reference"])
    return redirect("programme", aircraft_id=work.aircraft_id)
