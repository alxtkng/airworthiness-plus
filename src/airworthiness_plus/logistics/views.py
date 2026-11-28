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
from airworthiness_plus.logistics import receiving, services
from airworthiness_plus.logistics.forms import (
    EvaluationForm,
    NewSupplierForm,
    ReceiptForm,
    ReceivingCheckForm,
    ReceivingDispositionForm,
    SubcontractorAssessmentForm,
)
from airworthiness_plus.logistics.models import (
    CheckKind,
    Receipt,
    ReceivingDisposition,
    Supplier,
)
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


@never_cache
@requires(Action.VIEW_RECORDS)
def goods_in(request: HttpRequest) -> HttpResponse:
    """Show the shared receiving register under the organisation's maintenance approvals."""
    user, _ = _maintenance_access(request, Action.VIEW_RECORDS, aircraft_services.today())
    return render(
        request,
        "logistics/goods_in.html",
        {
            "receipts": Receipt.objects.filter(organisation=user.organisation).select_related(
                "disposition"
            ),
            "may_record": user.may(Action.RECORD_GOODS_IN),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def receipt(request: HttpRequest, receipt_id: UUID) -> HttpResponse:
    """Show the current state and retain the history of recorded observations."""
    user, _ = _maintenance_access(request, Action.VIEW_RECORDS, aircraft_services.today())
    record = get_object_or_404(
        Receipt.objects.select_related("disposition__approval", "disposition__stock_entry"),
        pk=receipt_id,
    )
    history = list(record.checks.all())
    current = receiving.current_checks(history)
    return render(
        request,
        "logistics/receipt.html",
        {
            "receipt": record,
            "disposition": getattr(record, "disposition", None),
            "check_rows": [(kind.label, current.get(kind)) for kind in CheckKind],
            "checks_done": len(current),
            "history": history,
            "may_record": user.may(Action.RECORD_GOODS_IN),
        },
    )


@never_cache
@requires(Action.RECORD_GOODS_IN)
@require_http_methods(["GET", "POST"])
def receive(request: HttpRequest) -> HttpResponse:
    """Record one line of goods received (REQ-353)."""
    user, _ = _maintenance_access(request, Action.RECORD_GOODS_IN, aircraft_services.today())
    form = ReceiptForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            record = receiving.receive(user.organisation, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("goods_receipt", receipt_id=record.pk)
    return render(
        request,
        "logistics/receiving_form.html",
        {"form": form, "heading": "Receive an Item", "button": "Record Receipt"},
    )


@never_cache
@requires(Action.RECORD_GOODS_IN)
@require_http_methods(["GET", "POST"])
def record_receiving_check(request: HttpRequest, receipt_id: UUID) -> HttpResponse:
    """Append an inspection check observation (REQ-354)."""
    return _record_inspection(request, receipt_id, check=True)


@never_cache
@requires(Action.RECORD_GOODS_IN)
@require_http_methods(["GET", "POST"])
def record_receiving_disposition(request: HttpRequest, receipt_id: UUID) -> HttpResponse:
    """Record the inspection decision and its disposition (REQ-355)."""
    return _record_inspection(request, receipt_id, check=False)


def _record_inspection(request: HttpRequest, receipt_id: UUID, *, check: bool) -> HttpResponse:
    _maintenance_access(request, Action.RECORD_GOODS_IN, aircraft_services.today())
    record = get_object_or_404(Receipt, pk=receipt_id)
    if request.method == "GET" and ReceivingDisposition.objects.filter(receipt=record).exists():
        return redirect("goods_receipt", receipt_id=record.pk)
    form_class = ReceivingCheckForm if check else ReceivingDispositionForm
    form = form_class(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            action = receiving.record_check if check else receiving.dispose
            action(record, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("goods_receipt", receipt_id=record.pk)
    heading = "Record a Check" if check else "Record the Disposition"
    return render(
        request,
        "logistics/receiving_form.html",
        {"form": form, "heading": heading, "button": heading, "receipt": record},
    )
