"""Supplier records for the organisation's maintenance approvals."""

from datetime import date
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics import services
from airworthiness_plus.logistics.forms import (
    EvaluationForm,
    NewSupplierForm,
    SubcontractorAssessmentForm,
)
from airworthiness_plus.logistics.models import Supplier
from airworthiness_plus.organisations.models import Approval


def _maintenance_access(
    request: HttpRequest, action: Action, today: date
) -> tuple[User, list[Approval]]:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by requires
    held = services.maintenance_approvals(user.organisation, today)
    if not held:
        raise ActionRefusedError(action)
    return user, held


@never_cache
@requires(Action.VIEW_RECORDS)
def suppliers(request: HttpRequest) -> HttpResponse:
    """Show the organisation's supplier register (REQ-340)."""
    today = aircraft_services.today()
    user, held = _maintenance_access(request, Action.VIEW_RECORDS, today)
    return render(
        request,
        "logistics/suppliers.html",
        {
            "lines": services.register(user.organisation, held, today),
            "may_evaluate": user.may(Action.RECORD_SUPPLIER_EVALUATION),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def supplier(request: HttpRequest, supplier_id: UUID) -> HttpResponse:
    """Show every evaluation recorded for this supplier (REQ-342)."""
    user, _ = _maintenance_access(request, Action.VIEW_RECORDS, aircraft_services.today())
    record = get_object_or_404(Supplier, pk=supplier_id)
    return render(
        request,
        "logistics/supplier.html",
        {
            "supplier": record,
            "evaluations": record.evaluations.select_related("approval"),
            "subcontracting": record.subcontractor_assessments.select_related("approval"),
            "may_assess": user.may(Action.RECORD_SUBCONTRACTOR_ASSESSMENT),
            "may_evaluate": user.may(Action.RECORD_SUPPLIER_EVALUATION),
        },
    )


@never_cache
@requires(Action.RECORD_SUPPLIER_EVALUATION)
@require_http_methods(["GET", "POST"])
def add_supplier(request: HttpRequest) -> HttpResponse:
    """Record a supplier and its initial evaluation (REQ-341)."""
    return _evaluate(request)


@never_cache
@requires(Action.RECORD_SUPPLIER_EVALUATION)
@require_http_methods(["GET", "POST"])
def evaluate_supplier(request: HttpRequest, supplier_id: UUID) -> HttpResponse:
    """Record a further evaluation of an existing supplier (REQ-342)."""
    return _evaluate(request, supplier_id)


def _evaluate(request: HttpRequest, supplier_id: UUID | None = None) -> HttpResponse:
    user, _ = _maintenance_access(
        request, Action.RECORD_SUPPLIER_EVALUATION, aircraft_services.today()
    )
    record = get_object_or_404(Supplier, pk=supplier_id) if supplier_id else None
    form_class = EvaluationForm if record else NewSupplierForm
    form = form_class(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            evaluation = services.record_evaluation(
                user.organisation, supplier=record, **form.cleaned_data
            )
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("supplier", supplier_id=evaluation.supplier_id)
    return render(request, "logistics/evaluate.html", {"form": form, "supplier": record})


@never_cache
@requires(Action.RECORD_SUBCONTRACTOR_ASSESSMENT)
@require_http_methods(["GET", "POST"])
def assess_subcontractor(request: HttpRequest, supplier_id: UUID) -> HttpResponse:
    """Record the maintenance subcontractor controls for a supplier (REQ-348)."""
    _maintenance_access(request, Action.RECORD_SUBCONTRACTOR_ASSESSMENT, aircraft_services.today())
    supplier_record = get_object_or_404(Supplier, pk=supplier_id)
    form = SubcontractorAssessmentForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            services.assess_subcontractor(supplier_record, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("supplier", supplier_id=supplier_id)
    return render(
        request,
        "logistics/evaluate.html",
        {"form": form, "supplier": supplier_record, "assessing_subcontractor": True},
    )
