"""Pages for maintenance data.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). Data of another organisation is not
found (REQ-003).
"""

import uuid
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.maintenance_data import services
from airworthiness_plus.maintenance_data.forms import (
    CheckForm,
    CustomerStatusForm,
    DataSetForm,
    EndHoldingForm,
    RevisionForm,
)
from airworthiness_plus.maintenance_data.models import DataSet, Evidence, Kind


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def data_page(request: HttpRequest) -> HttpResponse:
    """Every set of maintenance data, those needing attention first (REQ-083, REQ-084)."""
    lines = services.data_lines(_user(request).organisation, aircraft_services.today())
    return render(request, "maintenance_data/data.html", {"lines": lines})


@never_cache
@requires(Action.VIEW_RECORDS)
def data_set_page(request: HttpRequest, data_set_id: uuid.UUID) -> HttpResponse:
    """One set of data: every revision and every amendment check."""
    return _data_set_page(request, get_object_or_404(DataSet, pk=data_set_id))


def _data_set_page(
    request: HttpRequest, data_set: DataSet, submitted: Form | None = None
) -> HttpResponse:
    return render(
        request,
        "maintenance_data/data_set.html",
        {
            "data_set": data_set,
            "revisions": data_set.revisions.all(),
            "checks": data_set.checks.select_related("checked_by"),
            "revision_form": submitted if isinstance(submitted, RevisionForm) else RevisionForm(),
            "check_form": submitted if isinstance(submitted, CheckForm) else CheckForm(),
            "customer_form": submitted
            if isinstance(submitted, CustomerStatusForm)
            else CustomerStatusForm(),
            "end_form": submitted if isinstance(submitted, EndHoldingForm) else EndHoldingForm(),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def aircraft_data_page(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Whether the data for an aircraft's type rating is held and current (REQ-089)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    data = services.data_for(aircraft, aircraft_services.today())
    return render(request, "maintenance_data/aircraft.html", {"aircraft": aircraft, "data": data})


@never_cache
@requires(Action.RECORD_MAINTENANCE_DATA)
@require_http_methods(["GET", "POST"])
def add_data(request: HttpRequest) -> HttpResponse:
    """Record a set of maintenance data (REQ-080)."""
    form = DataSetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        data["kind"] = Kind(data["kind"])
        data["evidence"] = Evidence(data["evidence"]) if data["evidence"] else None
        try:
            data_set = services.record_data(organisation=_user(request).organisation, **data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("data_set", data_set_id=data_set.id)
    return render(request, "maintenance_data/add.html", {"form": form})


def _act(
    request: HttpRequest,
    data_set_id: uuid.UUID,
    form_class: type[Form],
    act: Callable[[DataSet, dict[str, Any]], object],
) -> HttpResponse:
    """Run one change to a set of data from a small form on its page."""
    data_set = get_object_or_404(DataSet, pk=data_set_id)
    form = form_class(request.POST)
    if form.is_valid():
        try:
            act(data_set, form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("data_set", data_set_id=data_set.id)
    return _data_set_page(request, data_set, form)


@requires(Action.RECORD_MAINTENANCE_DATA)
@require_POST
def add_revision(request: HttpRequest, data_set_id: uuid.UUID) -> HttpResponse:
    """Record a new revision, superseding the current one (REQ-085)."""
    return _act(
        request,
        data_set_id,
        RevisionForm,
        lambda data_set, data: services.add_revision(data_set, **data),
    )


@requires(Action.RECORD_AMENDMENT_CHECK)
@require_POST
def record_check(request: HttpRequest, data_set_id: uuid.UUID) -> HttpResponse:
    """Record a check of the amendment status (REQ-082)."""
    user = _user(request)
    return _act(
        request,
        data_set_id,
        CheckForm,
        lambda data_set, data: services.record_check(data_set, checked_by=user, **data),
    )


@requires(Action.RECORD_MAINTENANCE_DATA)
@require_POST
def customer_status(request: HttpRequest, data_set_id: uuid.UUID) -> HttpResponse:
    """Record how the customer showed the amendment status of their data (REQ-086)."""
    return _act(
        request,
        data_set_id,
        CustomerStatusForm,
        lambda data_set, data: services.confirm_customer_status(
            data_set, evidence=Evidence(data["evidence"]), dated=data["dated"]
        ),
    )


@requires(Action.RECORD_MAINTENANCE_DATA)
@require_POST
def end_holding(request: HttpRequest, data_set_id: uuid.UUID) -> HttpResponse:
    """Mark data as No Longer Held (REQ-087)."""
    return _act(
        request,
        data_set_id,
        EndHoldingForm,
        lambda data_set, data: services.end_holding(data_set, data["on"]),
    )
