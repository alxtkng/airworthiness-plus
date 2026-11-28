"""Aircraft-specific structural findings and transcription of flight reports."""

from uuid import UUID

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from airworthiness_plus.accounts.middleware import recent_verification
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.accounts.user_views import code_page
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.defects.aircraft_records_forms import (
    DamageForm,
    DrawingForm,
    FlightForm,
    FlightReportForm,
    LogFilter,
    ReportReleaseForm,
)
from airworthiness_plus.defects.models import (
    AircraftDrawing,
    DamageEntry,
    FlightEvent,
    FlightReport,
    FlightReportRelease,
)
from airworthiness_plus.defects.views import _user
from airworthiness_plus.interface.forms import Form


def _form_page(
    request: HttpRequest,
    aircraft: Aircraft,
    form: Form,
    title: str,
    back: str,
    *,
    subject: object | None = None,
) -> HttpResponse:
    return render(
        request,
        "defects/aircraft_record_form.html",
        {"aircraft": aircraft, "form": form, "heading": title, "back": back, "subject": subject},
    )


def _locked(aircraft_id: UUID) -> Aircraft:
    return get_object_or_404(Aircraft.objects.select_for_update(), pk=aircraft_id)


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def damage_register(request: HttpRequest, aircraft_id: UUID) -> HttpResponse:
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    return render(
        request,
        "defects/damage_register.html",
        {
            "aircraft": aircraft,
            "entries": DamageEntry.objects.filter(
                aircraft=aircraft, superseded_by__isnull=True
            ).select_related("drawing", "repair", "follow_up"),
            "drawings": AircraftDrawing.objects.filter(aircraft=aircraft).select_related(
                "superseded_by"
            ),
            "may_record": _user(request).may(Action.RECORD_DEFECT),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def drawing_page(request: HttpRequest, aircraft_id: UUID, drawing_id: UUID) -> HttpResponse:
    drawing = get_object_or_404(
        AircraftDrawing.objects.select_related("aircraft", "supersedes", "superseded_by"),
        pk=drawing_id,
        aircraft_id=aircraft_id,
    )
    return render(
        request,
        "defects/drawing.html",
        {
            "aircraft": drawing.aircraft,
            "drawing": drawing,
            "markers": drawing.markers.select_related("superseded_by"),
            "may_record": _user(request).may(Action.RECORD_DEFECT),
        },
    )


@never_cache
@requires(Action.RECORD_DEFECT)
@require_http_methods(["GET", "POST"])
@transaction.atomic
def record_drawing(
    request: HttpRequest, aircraft_id: UUID, drawing_id: UUID | None = None
) -> HttpResponse:
    """Record the first or a subsequent revision of a drawing."""
    aircraft = (
        _locked(aircraft_id)
        if request.method == "POST"
        else get_object_or_404(Aircraft, pk=aircraft_id)
    )
    previous = None
    form = DrawingForm(request.POST if request.method == "POST" else None)
    if drawing_id is not None:
        previous = get_object_or_404(AircraftDrawing, pk=drawing_id, aircraft=aircraft)
        form.initial.update(
            reference=previous.reference, view=previous.view, outline=previous.outline
        )
        for field in ("reference", "view"):
            form.fields[field].disabled = True
    if form.is_valid():
        values = form.cleaned_data
        history = AircraftDrawing.objects.filter(
            aircraft=aircraft, reference=values["reference"], view=values["view"]
        )
        if previous is None and history.exists():
            form.add_error(None, "Open the current drawing revision to record its successor.")
        elif previous and history.filter(supersedes=previous).exists():
            form.add_error(None, "The drawing already has a newer revision.")
        elif history.filter(revision=values["revision"]).exists():
            form.add_error("revision", "This revision is already recorded.")
        else:
            drawing = AircraftDrawing.objects.create(
                organisation=aircraft.organisation, aircraft=aircraft, supersedes=previous, **values
            )
            return redirect("damage_drawing", aircraft_id=aircraft.id, drawing_id=drawing.id)
    return _form_page(request, aircraft, form, "Record a Drawing Revision", "damage_register")


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def damage_page(request: HttpRequest, aircraft_id: UUID, damage_id: UUID) -> HttpResponse:
    entry = get_object_or_404(
        DamageEntry.objects.select_related(
            "aircraft", "drawing", "defect", "repair", "follow_up", "supersedes", "superseded_by"
        ),
        pk=damage_id,
        aircraft_id=aircraft_id,
    )
    return render(
        request,
        "defects/damage_entry.html",
        {
            "aircraft": entry.aircraft,
            "entry": entry,
            "may_record": _user(request).may(Action.RECORD_DEFECT),
        },
    )


@never_cache
@requires(Action.RECORD_DEFECT)
@require_http_methods(["GET", "POST"])
@transaction.atomic
def record_damage(
    request: HttpRequest, aircraft_id: UUID, damage_id: UUID | None = None
) -> HttpResponse:
    """Record a finding or preserve a superseding version with a revised marker."""
    aircraft = (
        _locked(aircraft_id)
        if request.method == "POST"
        else get_object_or_404(Aircraft, pk=aircraft_id)
    )
    previous = None
    if damage_id is not None:
        previous = get_object_or_404(
            DamageEntry.objects.select_related("aircraft", "drawing"),
            pk=damage_id,
            aircraft=aircraft,
        )
    if request.method == "POST":
        form = DamageForm(request.POST, aircraft=aircraft)
    else:
        form = DamageForm.for_revision(previous) if previous else DamageForm(aircraft=aircraft)
    if form.is_valid():
        if previous and DamageEntry.objects.filter(supersedes=previous).exists():
            form.add_error(None, "The finding already has a newer version.")
        else:
            entry, _ = DamageEntry.objects.get_or_create(
                organisation=aircraft.organisation,
                aircraft=aircraft,
                supersedes=previous,
                **form.cleaned_data,
            )
            return redirect("damage_entry", aircraft_id=aircraft.id, damage_id=entry.id)
    return _form_page(request, aircraft, form, "Record a Structural Finding", "damage_register")


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def technical_log(request: HttpRequest, aircraft_id: UUID) -> HttpResponse:
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    flights = FlightEvent.objects.filter(aircraft=aircraft)
    reports = FlightReport.objects.filter(flight__aircraft=aircraft).select_related("flight")
    form = LogFilter(request.GET or None, label_suffix="")
    if form.is_bound and form.is_valid():
        if chapter := form.cleaned_data["chapter"]:
            number, _, section = chapter.partition("-")
            reports = reports.filter(chapter=int(number))
            if section:
                reports = reports.filter(section=section)
        if part := form.cleaned_data["part"]:
            reports = reports.filter(part_number__iexact=part, component__isnull=False)
    elif form.is_bound:
        reports = reports.none()
    return render(
        request,
        "defects/technical_log.html",
        {
            "aircraft": aircraft,
            "flights": flights,
            "reports": reports,
            "filter": form,
            "may_record": _user(request).may(Action.RECORD_DEFECT),
        },
    )


@never_cache
@requires(Action.RECORD_DEFECT)
@require_http_methods(["GET", "POST"])
@transaction.atomic
def record_flight(request: HttpRequest, aircraft_id: UUID) -> HttpResponse:
    """Add a flight event from the source flight record."""
    aircraft = (
        _locked(aircraft_id)
        if request.method == "POST"
        else get_object_or_404(Aircraft, pk=aircraft_id)
    )
    form = FlightForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        values = form.cleaned_data
        flight, created = FlightEvent.objects.get_or_create(
            organisation=aircraft.organisation,
            aircraft=aircraft,
            reference=values["reference"],
            flown_on=values["flown_on"],
            defaults={"departure": values["departure"], "arrival": values["arrival"]},
        )
        if created or (flight.departure, flight.arrival) == (
            values["departure"],
            values["arrival"],
        ):
            return redirect("technical_log_flight", aircraft_id=aircraft.id, flight_id=flight.id)
        form.add_error("reference", "This flight reference and date already identify a flight.")
    return _form_page(request, aircraft, form, "Record a Flight", "technical_log")


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def flight_page(request: HttpRequest, aircraft_id: UUID, flight_id: UUID) -> HttpResponse:
    flight = get_object_or_404(
        FlightEvent.objects.select_related("aircraft"), pk=flight_id, aircraft_id=aircraft_id
    )
    return render(
        request,
        "defects/technical_log_flight.html",
        {
            "aircraft": flight.aircraft,
            "flight": flight,
            "may_record": _user(request).may(Action.RECORD_DEFECT),
        },
    )


@never_cache
@requires(Action.RECORD_DEFECT)
@require_http_methods(["GET", "POST"])
@transaction.atomic
def transcribe_report(request: HttpRequest, aircraft_id: UUID, flight_id: UUID) -> HttpResponse:
    """Transcribe a flight report after recent verification."""
    flight = get_object_or_404(
        FlightEvent.objects.select_related("aircraft"), pk=flight_id, aircraft_id=aircraft_id
    )
    form = FlightReportForm(request.POST if request.method == "POST" else None, flight=flight)
    if form.is_valid():
        prompt = code_page(
            request,
            "Verify to Transcribe the Report",
            "Technical Log Transcription",
            back=("dashboard", "Cancel"),
            full=True,
        )
        if prompt is not None:
            return prompt
        verified_at = recent_verification(request.session)
        if verified_at is None:
            form.add_error(None, "Verification expired. Submit the report to verify again.")
        else:
            _locked(aircraft_id)
            user = _user(request)
            values = dict(form.cleaned_data)
            values.pop("confirmed")
            component = values.get("component")
            existing = FlightReport.objects.filter(
                flight=flight, kind=values["kind"], source_reference=values["source_reference"]
            ).first()
            if existing is None:
                existing = FlightReport.objects.create(
                    organisation=flight.organisation,
                    flight=flight,
                    recorded_by=user,
                    recorder_name=user.full_name,
                    verification_at=verified_at,
                    part_number=component.part_number if component else "",
                    **values,
                )
            elif not all(getattr(existing, field) == value for field, value in values.items()):
                form.add_error("source_reference", "This source already identifies a report.")
                existing = None
            if existing is not None:
                return redirect(
                    "technical_log_report", aircraft_id=aircraft_id, report_id=existing.id
                )
    return _form_page(
        request,
        flight.aircraft,
        form,
        "Transcribe a Flight Report",
        "technical_log",
        subject=flight,
    )


def _report(aircraft_id: UUID, report_id: UUID) -> FlightReport:
    return get_object_or_404(
        FlightReport.objects.select_related(
            "flight__aircraft", "defect", "component", "certification__release"
        ),
        pk=report_id,
        flight__aircraft_id=aircraft_id,
    )


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def report_page(request: HttpRequest, aircraft_id: UUID, report_id: UUID) -> HttpResponse:
    report = _report(aircraft_id, report_id)
    return render(
        request,
        "defects/technical_log_report.html",
        {
            "aircraft": report.flight.aircraft,
            "report": report,
            "may_record_release": _user(request).may(Action.RECORD_RELEASE_CERTIFICATE)
            and report.defect is not None
            and report.defect.work_done_id is not None,
        },
    )


@never_cache
@requires(Action.RECORD_RELEASE_CERTIFICATE)
@require_http_methods(["GET", "POST"])
@transaction.atomic
def link_report_release(request: HttpRequest, aircraft_id: UUID, report_id: UUID) -> HttpResponse:
    """Link the existing certificate for the recorded rectification."""
    if request.method == "POST":
        _locked(aircraft_id)
    report = _report(aircraft_id, report_id)
    form = ReportReleaseForm(request.POST if request.method == "POST" else None, report=report)
    if form.is_valid():
        link, _ = FlightReportRelease.objects.get_or_create(
            organisation=report.organisation,
            report=report,
            defaults={"release": form.cleaned_data["release"]},
        )
        if link.release == form.cleaned_data["release"]:
            return redirect("technical_log_report", aircraft_id=aircraft_id, report_id=report.id)
        form.add_error("release", "The report already links to a certificate.")
    return _form_page(
        request,
        report.flight.aircraft,
        form,
        "Link the Release",
        "technical_log",
        subject=report.source_reference,
    )
