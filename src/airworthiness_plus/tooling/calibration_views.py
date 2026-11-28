"""Service provider, custody, certificate and reinstatement routes."""

from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.logistics.services import maintenance_approvals
from airworthiness_plus.tooling import calibration, status
from airworthiness_plus.tooling.calibration_forms import (
    CertificateForm,
    DecisionForm,
    MovementForm,
    OrderForm,
    ProviderForm,
    ReinstateForm,
    ResultForm,
)
from airworthiness_plus.tooling.calibration_models import (
    CalibrationCertificate,
    CalibrationOrder,
    MovementKind,
    Phase,
    Statement,
    ToolServiceProviderAuthorisation,
)
from airworthiness_plus.tooling.calibration_status import (
    decision_on,
    latest_certificate,
    movement,
    order_open,
    reinstatement_on,
)
from airworthiness_plus.tooling.models import Tool
from airworthiness_plus.tooling.views import _read_access, _user

CALIBRATION = Action.RECORD_TOOL_CALIBRATION
PROVIDER = Action.RECORD_TOOL_PROVIDER
READ = Action.VIEW_RECORDS


def _order(request: HttpRequest, order_id: UUID) -> CalibrationOrder:
    return get_object_or_404(
        CalibrationOrder, pk=order_id, organisation=_user(request).organisation
    )


def _certificate(
    request: HttpRequest, order_id: UUID, certificate_id: UUID
) -> CalibrationCertificate:
    return get_object_or_404(
        CalibrationCertificate,
        pk=certificate_id,
        order_id=order_id,
        organisation=_user(request).organisation,
    )


def _form(
    request: HttpRequest,
    cls: type[Form],
    title: str,
    save: Callable[..., HttpResponse],
    subject: object = None,
    initial: dict[str, Any] | None = None,
) -> HttpResponse:
    form = cls(request.POST if request.method == "POST" else None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            return save(_user(request), **form.cleaned_data)
        except calibration.RefusedError as error:
            form.add_error(None, str(error))
    return render(request, "tooling/form.html", {"form": form, "title": title, "tool": subject})


def _order_redirect(order: CalibrationOrder) -> HttpResponse:
    return redirect("calibration_order", order_id=order.pk)


def _certificate_redirect(certificate: CalibrationCertificate) -> HttpResponse:
    return redirect(
        "calibration_certificate", order_id=certificate.order_id, certificate_id=certificate.pk
    )


@never_cache
@requires(READ)
@require_http_methods(["GET", "HEAD"])
def providers(request: HttpRequest) -> HttpResponse:
    """Read provider scope and calibration custody."""
    user = _user(request)
    today = aircraft_services.today()
    held = maintenance_approvals(user.organisation, today)
    _read_access(user, held)
    scopes = ToolServiceProviderAuthorisation.objects.filter(
        organisation=user.organisation
    ).select_related(
        "supplier",
        "delegation__approval",
        "delegation__person",
    )
    orders = (
        CalibrationOrder.objects.filter(organisation=user.organisation)
        .select_related(
            "tool",
            "provider__supplier",
        )
        .prefetch_related("movements")
    )
    return render(
        request,
        "tooling/providers.html",
        {
            "scopes": scopes,
            "orders": [
                (
                    order,
                    movement(order, MovementKind.DESPATCHED, today),
                    movement(order, MovementKind.RETURNED, today),
                )
                for order in orders
            ],
            "may_provider": bool(held) and user.may(PROVIDER),
        },
    )


@never_cache
@requires(READ)
@require_http_methods(["GET", "HEAD"])
def provider(request: HttpRequest, provider_id: UUID) -> HttpResponse:
    """Read the dated evidence for one provider scope."""
    scope = get_object_or_404(
        ToolServiceProviderAuthorisation,
        pk=provider_id,
        organisation=_user(request).organisation,
    )
    return render(request, "tooling/provider.html", {"scope": scope})


@never_cache
@requires(PROVIDER)
@require_http_methods(["GET", "POST"])
def authorise_provider(request: HttpRequest) -> HttpResponse:
    """Record a dated provider scope or suspension."""

    def save(user: User, **fields: Any) -> HttpResponse:
        scope = calibration.authorise_provider(user, **fields)
        return redirect("tool_provider", provider_id=scope.pk)

    return _form(
        request,
        ProviderForm,
        "Record Provider Scope",
        save,
        initial={"status": "Authorised", "service": "Calibration"},
    )


@never_cache
@requires(CALIBRATION)
@require_http_methods(["GET", "POST"])
def place_order(request: HttpRequest, tool_id: UUID) -> HttpResponse:
    """Place a calibration order for this tool."""
    tool = get_object_or_404(Tool, pk=tool_id, organisation=_user(request).organisation)
    return _form(
        request,
        OrderForm,
        "Place Calibration Order",
        lambda user, **fields: _order_redirect(calibration.place_order(user, tool, **fields)),
        tool,
    )


@never_cache
@requires(READ)
@require_http_methods(["GET", "HEAD"])
def order(request: HttpRequest, order_id: UUID) -> HttpResponse:
    """Read the order, its custody, certificates, hold and case."""
    record = _order(request, order_id)
    today = aircraft_services.today()
    grant = record.delegation
    selected = status.label(record.tool, grant.approval, grant.approval_reference, today, 0)
    current = latest_certificate(record, today)
    completion = next(
        (line.due_on for line in selected.controls if line.revision.kind == "Calibration"),
        None,
    )
    returned = movement(record, MovementKind.RETURNED, today)
    sent = movement(record, MovementKind.DESPATCHED, today)
    release = reinstatement_on(record, today)
    decision = decision_on(current, today) if current else None
    return render(
        request,
        "tooling/order.html",
        {
            "order": record,
            "sent": sent,
            "returned": returned,
            "calibration_due": completion,
            "may_record": _user(request).may(CALIBRATION),
            "open_order": order_open(record, today),
            "ready": release,
            "latest": current,
            "may_reinstate": returned
            and decision
            and decision.outcome == "Accepted"
            and not release,
        },
    )


@never_cache
@requires(CALIBRATION)
@require_http_methods(["GET", "POST"])
def record_movement(request: HttpRequest, order_id: UUID) -> HttpResponse:
    """Record despatch or physical return against the order."""
    record = _order(request, order_id)

    def save(user: User, **fields: Any) -> HttpResponse:
        calibration.record_movement(user, record, **fields)
        return _order_redirect(record)

    return _form(request, MovementForm, "Record Calibration Custody", save, record)


@never_cache
@requires(CALIBRATION)
@require_http_methods(["GET", "POST"])
def record_certificate(request: HttpRequest, order_id: UUID) -> HttpResponse:
    """Record a certificate version and its evidence."""
    record = _order(request, order_id)
    return _form(
        request,
        CertificateForm,
        "Record Calibration Certificate",
        lambda user, **fields: _certificate_redirect(
            calibration.record_certificate(user, record, **fields)
        ),
        record,
    )


@never_cache
@requires(READ)
@require_http_methods(["GET", "HEAD"])
def certificate(request: HttpRequest, order_id: UUID, certificate_id: UUID) -> HttpResponse:
    """Read one retained certificate version, results and decisions."""
    record = _certificate(request, order_id, certificate_id)
    current = latest_certificate(record.order, aircraft_services.today()) == record
    may = _user(request).may(CALIBRATION)
    found_points = {
        point.reference_value
        for point in record.results.all()
        if point.phase == Phase.FOUND
        and point.error is not None
        and point.statement != Statement.INCONCLUSIVE
    }
    return render(
        request,
        "tooling/calibration_certificate.html",
        {
            "certificate": record,
            "order": record.order,
            "current": current,
            "found_gap": not {Decimal(point) for point in record.order.points} <= found_points,
            "may_decide": may and current,
            "may_result": may and current and not record.decisions.exists(),
        },
    )


@never_cache
@requires(CALIBRATION)
@require_http_methods(["GET", "POST"])
def record_result(request: HttpRequest, order_id: UUID, certificate_id: UUID) -> HttpResponse:
    """Record one result and create any required hold and affected-work case."""
    record = _certificate(request, order_id, certificate_id)

    def save(user: User, **fields: Any) -> HttpResponse:
        calibration.record_result(user, record, **fields)
        return _certificate_redirect(record)

    return _form(request, ResultForm, "Record Calibration Result", save, record)


@never_cache
@requires(CALIBRATION)
@require_http_methods(["GET", "POST"])
def decide_certificate(request: HttpRequest, order_id: UUID, certificate_id: UUID) -> HttpResponse:
    """Record an acceptance, rejection or hold decision."""
    record = _certificate(request, order_id, certificate_id)

    def save(user: User, **fields: Any) -> HttpResponse:
        calibration.decide_certificate(user, record, **fields)
        return _certificate_redirect(record)

    return _form(request, DecisionForm, "Decide Certificate Acceptance", save, record)


@never_cache
@requires(CALIBRATION)
@require_http_methods(["GET", "POST"])
def reinstate(request: HttpRequest, order_id: UUID) -> HttpResponse:
    """Sign prospective reinstatement after return and acceptance."""
    record = _order(request, order_id)

    def save(user: User, **fields: Any) -> HttpResponse:
        calibration.reinstate(user, record, **fields)
        return _order_redirect(record)

    return _form(request, ReinstateForm, "Authorise Return to Use", save, record)
