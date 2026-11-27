"""Pages for contracts and work orders (REQ-240 to REQ-249).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A record of another organisation is
not found, because the database does not show it (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.contracts import services
from airworthiness_plus.contracts.forms import (
    AuthorityToldForm,
    CloseWorkOrderForm,
    ContractForm,
    EndContractForm,
    WorkOrderForm,
)
from airworthiness_plus.contracts.models import Contract, WorkOrder
from airworthiness_plus.interface.forms import Form


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def contracts_page(request: HttpRequest) -> HttpResponse:
    """Every contract and every work order (REQ-246)."""
    user = _user(request)
    return render(
        request,
        "contracts/contracts.html",
        {
            "lines": services.contract_lines(),
            "orders": services.work_orders(),
            "may_draw_up": user.may(Action.DRAW_UP_OR_END_CONTRACT),
            "may_order": user.may(Action.RECORD_WORK_ORDER),
        },
    )


@never_cache
@requires(Action.DRAW_UP_OR_END_CONTRACT)
@require_http_methods(["GET", "POST"])
def draw_up_contract(request: HttpRequest) -> HttpResponse:
    """Record a contract signed with the owner of an aircraft (REQ-240)."""
    form = ContractForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        values = dict(form.cleaned_data)
        aircraft = values.pop("aircraft")
        try:
            contract = services.draw_up_contract(aircraft, **values)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("contract", contract_id=contract.id)
    return render(
        request,
        "contracts/form.html",
        {"form": form, "title": "Draw Up a Contract", "button": "Record Contract"},
    )


def _contract_page(
    request: HttpRequest, contract: Contract, form: Form | None = None
) -> HttpResponse:
    line = services.ContractLine(contract)
    return render(
        request,
        "contracts/contract.html",
        {
            "contract": contract,
            "line": line,
            "end_form": EndContractForm(),
            "told_form": AuthorityToldForm(),
            "refused": form,
            "may_change": _user(request).may(Action.DRAW_UP_OR_END_CONTRACT),
            "orders": contract.work_orders.all(),
        },
    )


def _contract(contract_id: uuid.UUID) -> Contract:
    return get_object_or_404(Contract.objects.select_related("aircraft"), pk=contract_id)


@never_cache
@requires(Action.VIEW_RECORDS)
def contract_page(request: HttpRequest, contract_id: uuid.UUID) -> HttpResponse:
    """One contract: what it says, where it stands and the work orders under it."""
    return _contract_page(request, _contract(contract_id))


@never_cache
@requires(Action.DRAW_UP_OR_END_CONTRACT)
@require_POST
def end_contract(request: HttpRequest, contract_id: uuid.UUID) -> HttpResponse:
    """Record that a contract has ended, and why (REQ-242)."""
    contract = _contract(contract_id)
    form = EndContractForm(request.POST)
    if form.is_valid():
        try:
            services.end_contract(contract, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("contract", contract_id=contract.id)
    contract.refresh_from_db()
    return _contract_page(request, contract, form)


@never_cache
@requires(Action.DRAW_UP_OR_END_CONTRACT)
@require_POST
def contract_authority_told(request: HttpRequest, contract_id: uuid.UUID) -> HttpResponse:
    """Record the day the Civil Aviation Authority was told a contract ended (REQ-243)."""
    contract = _contract(contract_id)
    form = AuthorityToldForm(request.POST)
    if form.is_valid():
        try:
            services.record_authority_told(contract, form.cleaned_data["told_on"])
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("contract", contract_id=contract.id)
    contract.refresh_from_db()
    return _contract_page(request, contract, form)


@never_cache
@requires(Action.RECORD_WORK_ORDER)
@require_http_methods(["GET", "POST"])
def add_work_order(request: HttpRequest) -> HttpResponse:
    """Record a written request for maintenance (REQ-244)."""
    form = WorkOrderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        values = dict(form.cleaned_data)
        aircraft = values.pop("aircraft")
        try:
            services.add_work_order(aircraft, **values)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("contracts")
    return render(
        request,
        "contracts/form.html",
        {"form": form, "title": "Record a Work Order", "button": "Record Work Order"},
    )


@never_cache
@requires(Action.RECORD_WORK_ORDER)
@require_http_methods(["GET", "POST"])
def close_work_order(request: HttpRequest, order_id: uuid.UUID) -> HttpResponse:
    """Record that a work order is completed or withdrawn (REQ-245)."""
    order = get_object_or_404(WorkOrder.objects.select_related("aircraft"), pk=order_id)
    form = CloseWorkOrderForm(request.POST or None, aircraft=order.aircraft)
    if request.method == "POST" and form.is_valid():
        try:
            services.close_work_order(order, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("contracts")
    return render(
        request,
        "contracts/form.html",
        {
            "form": form,
            "title": f"Close the Work Order, {order.aircraft.registration}, {order.work}",
            "button": "Close Work Order",
        },
    )
