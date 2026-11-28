"""Stores reservation, issue and quarantine forms."""

from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.permissions import ActionRefusedError, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics import allocations, stock_appointments, substitutions
from airworthiness_plus.logistics.forms import (
    AllocationForm,
    QuarantineAllocationForm,
    ReserveAllocationForm,
    ReturnAllocationForm,
    StockAppointmentForm,
    StockAppointmentWithdrawalForm,
    StockSubstitutionForm,
)
from airworthiness_plus.logistics.models import (
    AllocationKind,
    StockAllocation,
    StockAppointment,
    StockPosting,
)
from airworthiness_plus.logistics.services import RefusedError, maintenance_approvals
from airworthiness_plus.logistics.stores_views import _access, _back, _form_page

FORMS = {
    AllocationKind.RESERVE: (ReserveAllocationForm, "Reserve Stock"),
    AllocationKind.RELEASE: (AllocationForm, "Release Reservation"),
    AllocationKind.ISSUE: (AllocationForm, "Issue Reserved Stock"),
    AllocationKind.RETURN: (ReturnAllocationForm, "Return Stock to Quarantine"),
    AllocationKind.QUARANTINE: (QuarantineAllocationForm, "Quarantine Stock"),
}


@never_cache
@requires(Action.MOVE_STOCK)
@require_http_methods(["GET", "POST"])
def change_custody(
    request: HttpRequest,
    kind: AllocationKind,
    posting_id: UUID | None = None,
    allocation_id: UUID | None = None,
) -> HttpResponse:
    """Record an authorised custody action on posted stock."""
    user, today = _access(request, Action.MOVE_STOCK), aircraft_services.today()
    action = allocations.appointment_action(kind)
    preceding = None
    postings = StockPosting.objects.filter(organisation=user.organisation).select_related(
        "disposition__receipt"
    )
    if allocation_id is not None:
        previous_kind = (
            AllocationKind.ISSUE if kind == AllocationKind.RETURN else AllocationKind.RESERVE
        )
        preceding = get_object_or_404(
            StockAllocation.objects.filter(organisation=user.organisation).select_related(
                "card__package", "source"
            ),
            pk=allocation_id,
            kind=previous_kind,
        )
        posting = postings.get(pk=preceding.posting_id)
    else:
        posting = get_object_or_404(postings, pk=posting_id)
    form_class, heading = FORMS[kind]
    data = request.POST if request.method == "POST" else None
    form = (
        ReserveAllocationForm(data, substitutes=substitutions.available(posting, today))
        if kind == AllocationKind.RESERVE
        else form_class(data)
    )
    if stock_appointments.current(user, action, today) is None:
        raise ActionRefusedError(Action.MOVE_STOCK)
    if request.method == "POST" and form.is_valid():
        try:
            allocations.record(user, posting, kind, preceding=preceding, **form.cleaned_data)
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(posting.disposition)
    return _custody_form(request, form, heading, posting, custody=preceding)


@never_cache
@requires(Action.RECORD_RELEASE_CERTIFICATE)
@require_http_methods(["GET", "POST"])
def approve_substitution(request: HttpRequest, posting_id: UUID) -> HttpResponse:
    """Record scoped approval of an alternate for a work card and lot."""
    user, today = _access(request, Action.RECORD_RELEASE_CERTIFICATE), aircraft_services.today()
    posting = get_object_or_404(
        StockPosting.objects.filter(organisation=user.organisation).select_related(
            "disposition__receipt"
        ),
        pk=posting_id,
    )
    form = StockSubstitutionForm(
        request.POST if request.method == "POST" else None,
        authorisations=substitutions.authorisations(user, today),
    )
    if request.method == "POST" and form.is_valid():
        try:
            substitutions.approve(user, posting, **form.cleaned_data)
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(posting.disposition)
    return _custody_form(
        request,
        form,
        "Approve an Alternate",
        posting,
        alternate_identity=posting.part_number or posting.specification,
    )


def _custody_form(
    request: HttpRequest,
    form: AllocationForm | StockSubstitutionForm,
    heading: str,
    posting: StockPosting,
    *,
    custody: StockAllocation | None = None,
    alternate_identity: str = "",
) -> HttpResponse:
    return render(
        request,
        "logistics/stores_form.html",
        {
            "form": form,
            "heading": heading,
            "button": heading,
            "back": reverse("stores_disposition", args=[posting.disposition_id]),
            "custody": custody,
            "alternate_identity": alternate_identity,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def custody_appointments(request: HttpRequest) -> HttpResponse:
    user = _access(request, Action.VIEW_RECORDS)
    return render(
        request,
        "logistics/custody_appointments.html",
        {
            "appointments": StockAppointment.objects.filter(organisation=user.organisation)
            .select_related("person", "approval", "withdrawal")
            .order_by("person__full_name", "action"),
            "today": aircraft_services.today(),
            "may_grant": user.may(Action.MANAGE_STORE_LOCATIONS),
        },
    )


@never_cache
@requires(Action.MANAGE_STORE_LOCATIONS)
@require_http_methods(["GET", "POST"])
def add_custody_appointment(request: HttpRequest) -> HttpResponse:
    """Record a dated appointment for one Stores custody action."""
    user = _access(request, Action.MANAGE_STORE_LOCATIONS)
    form = StockAppointmentForm(
        request.POST if request.method == "POST" else None,
        approvals=maintenance_approvals(user.organisation, aircraft_services.today()),
    )
    if request.method == "POST" and form.is_valid():
        try:
            stock_appointments.appoint(user, **form.cleaned_data)
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("custody_appointments")
    return _form_page(request, form, "Record a Stores Appointment", reverse("custody_appointments"))


@never_cache
@requires(Action.MANAGE_STORE_LOCATIONS)
@require_http_methods(["GET", "POST"])
def withdraw_custody_appointment(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    """Record the withdrawal of an existing custody appointment."""
    user = _access(request, Action.MANAGE_STORE_LOCATIONS)
    appointment = get_object_or_404(
        StockAppointment, pk=appointment_id, organisation=user.organisation
    )
    form = StockAppointmentWithdrawalForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            stock_appointments.withdraw(user, appointment, form.cleaned_data["evidence"])
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("custody_appointments")
    return _form_page(request, form, "Withdraw Stores Appointment", reverse("custody_appointments"))
