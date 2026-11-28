"""Stores reservation, issue and quarantine forms."""

from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.permissions import ActionRefusedError, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.logistics import allocations, stores, substitutions
from airworthiness_plus.logistics.forms import (
    AllocationForm,
    QuarantineAllocationForm,
    ReserveAllocationForm,
    ReturnAllocationForm,
    StockSubstitutionForm,
)
from airworthiness_plus.logistics.models import AllocationKind, StockAllocation, StockPosting
from airworthiness_plus.logistics.services import RefusedError
from airworthiness_plus.logistics.stores_views import _access, _back, _render_form

FORMS = {
    AllocationKind.RESERVE: (ReserveAllocationForm, "Reserve Stock"),
    AllocationKind.RELEASE: (AllocationForm, "Release Reservation"),
    AllocationKind.ISSUE: (AllocationForm, "Issue Reserved Stock"),
    AllocationKind.RETURN: (ReturnAllocationForm, "Return Stock to Quarantine"),
    AllocationKind.QUARANTINE: (QuarantineAllocationForm, "Quarantine Stock"),
}


@never_cache
@requires(Action.RECORD_STORES)
@require_http_methods(["GET", "POST"])
def change_custody(
    request: HttpRequest,
    kind: AllocationKind,
    posting_id: UUID | None = None,
    allocation_id: UUID | None = None,
) -> HttpResponse:
    user, today = _access(request, Action.RECORD_STORES)
    action = allocations.appointment_action(kind)
    preceding = None
    postings = StockPosting.objects.filter(organisation=user.organisation).select_related(
        "evidence", "disposition__receipt"
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
    if not stores.may_act(user, Action.RECORD_STORES, action, today):
        raise ActionRefusedError(Action.RECORD_STORES)
    if request.method == "POST" and form.is_valid():
        try:
            allocations.record(user, posting, kind, preceding=preceding, **form.cleaned_data)
        except RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(posting.disposition)
    return _render_form(
        request, form, heading, receipt=posting.disposition.receipt, custody=preceding
    )


@never_cache
@requires(Action.RECORD_RELEASE_CERTIFICATE)
@require_http_methods(["GET", "POST"])
def approve_substitution(request: HttpRequest, posting_id: UUID) -> HttpResponse:
    user, today = _access(request, Action.RECORD_RELEASE_CERTIFICATE)
    posting = get_object_or_404(
        StockPosting.objects.filter(organisation=user.organisation).select_related(
            "evidence", "disposition__receipt"
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
    return _render_form(
        request,
        form,
        "Approve an Alternate",
        receipt=posting.disposition.receipt,
        alternate_identity=posting.evidence.part_number or posting.evidence.specification,
    )
