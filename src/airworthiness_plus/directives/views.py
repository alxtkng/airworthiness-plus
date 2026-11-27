"""Pages for airworthiness directives.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A directive, aircraft or decision of
another organisation is not found (REQ-003).
"""

import uuid

from django.db import DatabaseError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components import services as component_services
from airworthiness_plus.directives import services
from airworthiness_plus.directives.forms import (
    ComplianceForm,
    DecisionForm,
    DirectiveForm,
    SourceCheckForm,
    SourceForm,
    TerminationForm,
)
from airworthiness_plus.directives.models import Applicability, Decision, Directive, Source
from airworthiness_rules.intervals import Interval, Reading


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


def _interval(data: dict[str, object], prefix: str) -> Interval | None:
    values = {unit: data.get(f"{prefix}_{unit}") for unit in ("hours", "cycles", "months", "days")}
    if all(value is None for value in values.values()):
        return None
    return Interval(**values)  # type: ignore[arg-type]


@never_cache
@requires(Action.VIEW_RECORDS)
def directives_page(request: HttpRequest) -> HttpResponse:
    """Every directive recorded, with the one that superseded it if any."""
    return render(
        request,
        "directives/directives.html",
        {
            "sources": services.source_lines(
                _user(request).organisation, aircraft_services.today()
            ),
            "may_record": _user(request).may(Action.RECORD_AIRWORTHINESS_DIRECTIVE),
            "check_form": SourceCheckForm(),
            "directives": Directive.objects.all(),
            # ML.A.504(a): applicability is checked before a component is fitted again.
            "awaiting_refit": component_services.awaiting_refit(),
        },
    )


@never_cache
@requires(Action.RECORD_AIRWORTHINESS_DIRECTIVE)
@require_http_methods(["GET", "POST"])
def add_directive(request: HttpRequest) -> HttpResponse:
    """Record a directive (REQ-060)."""
    form = DirectiveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                services.record_directive(
                    organisation=_user(request).organisation, **form.cleaned_data
                )
        except DatabaseError:
            form.add_error("number", "This Directive and Revision Are Already Recorded")
        else:
            return redirect("directives")
    return render(
        request,
        "directives/form.html",
        {"form": form, "title": "Record an Airworthiness Directive", "button": "Record Directive"},
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def status_page(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """The directive status of one aircraft (REQ-067)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    lines = services.status(aircraft, aircraft_services.today())
    return render(request, "directives/status.html", {"aircraft": aircraft, "lines": lines})


@never_cache
@requires(Action.DECIDE_DIRECTIVE_APPLICABILITY)
@require_http_methods(["GET", "POST"])
def decide(request: HttpRequest, aircraft_id: uuid.UUID, directive_id: uuid.UUID) -> HttpResponse:
    """Decide whether one directive applies to one aircraft (REQ-061 to REQ-063)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    directive = get_object_or_404(Directive, pk=directive_id)
    form = DecisionForm(request.POST or None, aircraft_id=aircraft.id)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            first = _interval(data, "first")
            action = None
            if first is not None:
                if (
                    data["counter"] is None
                    or data["starts_dated"] is None
                    or data["starts_hours"] is None
                    or data["starts_cycles"] is None
                ):
                    raise services.RefusedError(
                        "An Action Names Its Counter and Where It Is Counted From"
                    )
                action = services.Action(
                    counter=data["counter"],
                    starts=Reading(
                        data["starts_dated"], data["starts_hours"], data["starts_cycles"]
                    ),
                    first=first,
                    repeat=_interval(data, "repeat"),
                )
            elif _interval(data, "repeat") is not None:
                raise services.RefusedError("A Repeating Action Has a First Limit")
            services.decide(
                directive=directive,
                aircraft=aircraft,
                decision=Decision(data["decision"]),
                basis=data["basis"],
                decided_by=_user(request),
                action=action,
            )
        except ValueError as error:
            form.add_error(None, str(error))
        else:
            return redirect("directive_status", aircraft_id=aircraft.id)
    return render(
        request,
        "directives/form.html",
        {
            "aircraft": aircraft,
            "form": form,
            "title": f"Applicability of {directive}, {directive.subject}",
            "button": "Record Decision",
        },
    )


@never_cache
@requires(Action.RECORD_DIRECTIVE_COMPLIANCE)
@require_http_methods(["GET", "POST"])
def comply(request: HttpRequest, applicability_id: uuid.UUID) -> HttpResponse:
    """Record compliance with a directive on one aircraft (REQ-064)."""
    applicability = get_object_or_404(Applicability, pk=applicability_id)
    form = ComplianceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.record_compliance(applicability, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("directive_status", aircraft_id=applicability.aircraft_id)
    return render(
        request,
        "directives/form.html",
        {
            "aircraft": applicability.aircraft,
            "form": form,
            "title": f"Compliance with {applicability.directive}",
            "button": "Record Compliance",
        },
    )


@never_cache
@requires(Action.DECIDE_DIRECTIVE_APPLICABILITY)
@require_http_methods(["GET", "POST"])
def terminate(request: HttpRequest, applicability_id: uuid.UUID) -> HttpResponse:
    """Record a terminating action. Earlier compliance stays in the record (REQ-066)."""
    applicability = get_object_or_404(Applicability, pk=applicability_id)
    form = TerminationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.terminate(applicability, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("directive_status", aircraft_id=applicability.aircraft_id)
    return render(
        request,
        "directives/form.html",
        {
            "aircraft": applicability.aircraft,
            "form": form,
            "title": f"Terminating Action for {applicability.directive}",
            "button": "Record Terminating Action",
        },
    )


@never_cache
@requires(Action.RECORD_AIRWORTHINESS_DIRECTIVE)
@require_http_methods(["GET", "POST"])
def add_directive_source(request: HttpRequest) -> HttpResponse:
    """Record a source the organisation checks for new directives (REQ-288)."""
    form = SourceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.add_source(_user(request).organisation, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("directives")
    return render(
        request,
        "directives/source.html",
        {"form": form, "title": "Record a Source", "button": "Record Source", "source": None},
    )


@never_cache
@requires(Action.RECORD_AIRWORTHINESS_DIRECTIVE)
@require_http_methods(["GET", "POST"])
def check_directive_source(request: HttpRequest, source_id: uuid.UUID) -> HttpResponse:
    """Record that a source was checked for new directives (REQ-288)."""
    source = get_object_or_404(Source, pk=source_id)
    form = SourceCheckForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.record_source_check(source, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("directives")
    return render(
        request,
        "directives/source.html",
        {"form": form, "title": "Record a Check", "button": "Record Check", "source": source},
    )
