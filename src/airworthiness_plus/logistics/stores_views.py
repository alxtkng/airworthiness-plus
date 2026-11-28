"""Stores register, posting, locations, movements, counts and appointments (REQ-358)."""

from datetime import date
from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics import services, stores, substitutions
from airworthiness_plus.logistics.forms import (
    PostingEvidenceForm,
    StockAdjustmentForm,
    StockCountForm,
    StockMovementForm,
    StockPostingForm,
    StoresAppointmentForm,
    StoresLocationForm,
    StoresWithdrawalForm,
)
from airworthiness_plus.logistics.models import (
    Destination,
    PostingKind,
    ReceivingDisposition,
    StockCount,
    StockEntry,
    StockPosting,
    StoresAction,
    StoresAppointment,
    StoresLocation,
)


def _access(request: HttpRequest, action: Action) -> tuple[User, date]:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by requires
    today = aircraft_services.today()
    if not services.maintenance_approvals(user.organisation, today):
        raise ActionRefusedError(action)
    return user, today


def _decisions(user: User) -> QuerySet[ReceivingDisposition]:
    return ReceivingDisposition.objects.filter(organisation=user.organisation).select_related(
        "receipt", "stock_entry", "posting__evidence"
    )


def _state(decision: ReceivingDisposition, today: date) -> dict[str, Any]:
    """Return what the register shows for one disposition, from the ledger."""
    evidence = stores.latest_evidence(decision)
    posting = getattr(decision, "posting", None)
    lines = stores.positions(decision.organisation, today, posting=posting) if posting else []
    total = stores.totals(lines)
    unit = posting.evidence.unit if posting else (evidence.unit if evidence else "")
    figures = total.get(unit, stores.Totals(unit))
    reasons = [] if posting else stores.blockers(decision, evidence, today)
    if decision.outcome == Destination.RETURN:
        status = stores.RETURNED
    elif posting is None:
        status = (
            stores.AWAITING if decision.outcome == Destination.STORES else stores.HOLD_TO_VERIFY
        )
    else:
        status = stores.POSTED if posting.kind == PostingKind.STOCK else stores.HELD
    return {
        "disposition": decision,
        "receipt": decision.receipt,
        "evidence": evidence,
        "posting": posting,
        "positions": lines,
        "status": status,
        "unit": unit,
        "on_hand": stores.quantity_text(figures.on_hand, unit),
        "reserved": stores.quantity_text(figures.reserved, unit),
        "available": stores.quantity_text(figures.available, unit),
        "blockers": reasons,
    }


def _controls(user: User, today: date) -> dict[str, bool]:
    return {
        "may_post": stores.may_act(user, Action.RECORD_STORES, StoresAction.POST, today),
        "may_move": stores.may_act(user, Action.RECORD_STORES, StoresAction.MOVE, today),
        "may_count": stores.may_act(user, Action.RECORD_STORES, StoresAction.COUNT, today),
        "may_adjust": stores.may_act(user, Action.ADJUST_STOCK, StoresAction.ADJUST, today),
        "may_locate": stores.may_act(user, Action.RECORD_STORES, StoresAction.LOCATIONS, today),
        "may_reserve": stores.may_act(user, Action.RECORD_STORES, StoresAction.RESERVE, today),
        "may_issue": stores.may_act(user, Action.RECORD_STORES, StoresAction.ISSUE, today),
        "may_return": stores.may_act(user, Action.RECORD_STORES, StoresAction.RETURN, today),
        "may_quarantine": stores.may_act(
            user, Action.RECORD_STORES, StoresAction.QUARANTINE, today
        ),
    }


@never_cache
@requires(Action.VIEW_RECORDS)
def stores_stock(request: HttpRequest) -> HttpResponse:
    """Show custody by location, the posting backlog, holds and return history."""
    user, today = _access(request, Action.VIEW_RECORDS)
    lines = stores.positions(user.organisation, today)
    identity = request.GET.get("identity", "").strip()[:160]
    if identity:
        lines = [
            line
            for line in lines
            if identity.casefold()
            == (line.posting.evidence.part_number or line.posting.evidence.specification)
            .strip()
            .casefold()
        ]
    stationed = (
        StoresLocation.objects.filter(organisation=user.organisation)
        .exclude(station="")
        .exclude(withdrawal__withdrawn_on__lte=today)
    )
    places = stores.by_location(lines, stationed)
    decisions = list(_decisions(user))
    awaiting = [
        _state(one, today)
        for one in decisions
        if one.outcome == Destination.STORES and not hasattr(one, "posting")
    ]
    holds = [_state(one, today) for one in decisions if one.outcome == Destination.QUARANTINE]
    returns = [one for one in decisions if one.outcome == Destination.RETURN]
    return render(
        request,
        "logistics/stock.html",
        {
            "positions": [line for line in lines if not line.held],
            "awaiting": awaiting,
            "holds": holds,
            "returns": returns,
            "by_location": places,
            "by_station": stores.by_station(places),
            "identity": identity,
            "overall": list(stores.totals(lines).values()) or [stores.Totals("")],
            "warning_days": stores.SHELF_LIFE_WARNING_DAYS,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def stock_entry(request: HttpRequest, stock_id: UUID) -> HttpResponse:
    """Show one accepted disposition's Stores state through its permanent link."""
    user, today = _access(request, Action.VIEW_RECORDS)
    entry = get_object_or_404(
        StockEntry.objects.filter(organisation=user.organisation).select_related(
            "disposition__receipt"
        ),
        pk=stock_id,
    )
    return _detail(request, user, today, entry.disposition)


@never_cache
@requires(Action.VIEW_RECORDS)
def quarantine_hold(request: HttpRequest, disposition_id: UUID) -> HttpResponse:
    """Show one quarantined disposition as blocked custody."""
    user, today = _access(request, Action.VIEW_RECORDS)
    decision = get_object_or_404(
        _decisions(user).filter(outcome=Destination.QUARANTINE), pk=disposition_id
    )
    return _detail(request, user, today, decision)


def _detail(
    request: HttpRequest, user: User, today: date, decision: ReceivingDisposition
) -> HttpResponse:
    state = _state(decision, today)
    posting = state["posting"]
    return render(
        request,
        "logistics/stock_entry.html",
        {
            **state,
            **_controls(user, today),
            "history": decision.posting_evidence.select_related("location", "appointment__person"),
            "movements": posting.movements.select_related(
                "source", "destination", "appointment__person"
            )
            if posting
            else [],
            "counts": posting.counts.select_related("location", "adjustment", "appointment__person")
            if posting
            else [],
            "quantity": stores.quantity_text,
            "may_approve_substitution": (
                user.may(Action.RECORD_RELEASE_CERTIFICATE)
                and substitutions.authorisations(user, today).exists()
            ),
            "approved_alternates": substitutions.available(posting, today) if posting else [],
            "allocations": posting.allocations.select_related(
                "source",
                "destination",
                "card__package",
                "appointment__person",
                "following",
                "substitution__authorisation__person",
            )
            if posting
            else [],
        },
    )


def _back(decision: ReceivingDisposition) -> HttpResponse:
    entry = getattr(decision, "stock_entry", None)
    if entry is not None:
        return redirect("stock_entry", stock_id=entry.pk)
    return redirect("quarantine_hold", disposition_id=decision.pk)


def _decision(user: User, disposition_id: UUID) -> ReceivingDisposition:
    return get_object_or_404(
        _decisions(user).exclude(outcome=Destination.RETURN), pk=disposition_id
    )


def _render_form(request: HttpRequest, form: Any, heading: str, **context: Any) -> HttpResponse:
    return render(
        request,
        "logistics/stores_form.html",
        {"form": form, "heading": heading, **context},
    )


@never_cache
@requires(Action.RECORD_STORES)
@require_http_methods(["GET", "POST"])
def record_posting_evidence(request: HttpRequest, disposition_id: UUID) -> HttpResponse:
    """Record the dated evidence that resolves unit, identity, shelf life and location."""
    user, today = _access(request, Action.RECORD_STORES)
    decision = _decision(user, disposition_id)
    previous = stores.latest_evidence(decision)
    initial: dict[str, Any] = {"assessed_on": today.isoformat()}
    if previous is not None:
        for name in (
            "unit",
            "quantity",
            "manufacturer",
            "part_number",
            "serial",
            "batch",
            "specification",
            "shelf_life_basis",
            "shelf_life_to",
            "location",
            "tag",
        ):
            initial[name] = getattr(previous, name)
    form = PostingEvidenceForm(
        request.POST if request.method == "POST" else None,
        initial=initial,
        locations=StoresLocation.objects.filter(organisation=user.organisation).exclude(
            withdrawal__withdrawn_on__lte=today
        ),
    )
    if request.method == "POST" and form.is_valid():
        try:
            stores.record_posting_evidence(user, decision, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(decision)
    return _render_form(
        request,
        form,
        "Record Posting Evidence",
        receipt=decision.receipt,
        blockers=stores.blockers(decision, previous, today),
    )


@never_cache
@requires(Action.RECORD_STORES)
@require_http_methods(["GET", "POST"])
def post_disposition(request: HttpRequest, disposition_id: UUID) -> HttpResponse:
    """Post the disposition once, with its opening movement."""
    user, today = _access(request, Action.RECORD_STORES)
    decision = _decision(user, disposition_id)
    if request.method == "GET" and hasattr(decision, "posting"):
        return _back(decision)
    form = StockPostingForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            stores.post(user, decision, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(decision)
    heading = (
        "Post the Quarantine Hold"
        if decision.outcome == Destination.QUARANTINE
        else "Post to Stock"
    )
    state = _state(decision, today)
    return _render_form(
        request,
        form,
        heading,
        receipt=decision.receipt,
        blockers=state["blockers"],
        summary=state["evidence"],
    )


def _posting(user: User, posting_id: UUID) -> StockPosting:
    return get_object_or_404(
        StockPosting.objects.filter(organisation=user.organisation).select_related(
            "evidence", "disposition__receipt", "disposition__stock_entry"
        ),
        pk=posting_id,
    )


def _held_locations(posting: StockPosting, today: date) -> QuerySet[StoresLocation]:
    held = [
        line.location.pk for line in stores.positions(posting.organisation, today, posting=posting)
    ]
    return StoresLocation.objects.filter(pk__in=held)


@never_cache
@requires(Action.RECORD_STORES)
@require_http_methods(["GET", "POST"])
def move_stock(request: HttpRequest, posting_id: UUID) -> HttpResponse:
    """Move a quantity between two locations that accept the item."""
    user, today = _access(request, Action.RECORD_STORES)
    posting = _posting(user, posting_id)
    form = StockMovementForm(
        request.POST if request.method == "POST" else None,
        initial={"moved_on": today.isoformat()},
        sources=_held_locations(posting, today),
        destinations=StoresLocation.objects.filter(organisation=user.organisation).exclude(
            withdrawal__withdrawn_on__lte=today
        ),
    )
    if request.method == "POST" and form.is_valid():
        try:
            stores.move(user, posting, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(posting.disposition)
    return _render_form(request, form, "Move Stock", receipt=posting.disposition.receipt)


@never_cache
@requires(Action.RECORD_STORES)
@require_http_methods(["GET", "POST"])
def count_stock(request: HttpRequest, posting_id: UUID) -> HttpResponse:
    """Record a physical count. The ledger is unchanged until an authorised adjustment."""
    user, _ = _access(request, Action.RECORD_STORES)
    posting = _posting(user, posting_id)
    form = StockCountForm(
        request.POST if request.method == "POST" else None,
        locations=StoresLocation.objects.filter(organisation=user.organisation),
    )
    if request.method == "POST" and form.is_valid():
        try:
            stores.count(user, posting, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(posting.disposition)
    return _render_form(request, form, "Count Stock", receipt=posting.disposition.receipt)


@never_cache
@requires(Action.ADJUST_STOCK)
@require_http_methods(["GET", "POST"])
def adjust_stock(request: HttpRequest, count_id: UUID) -> HttpResponse:
    """Apply one count's variance under a separate adjustment appointment."""
    user, _ = _access(request, Action.ADJUST_STOCK)
    taken = get_object_or_404(
        StockCount.objects.filter(organisation=user.organisation).select_related(
            "posting__evidence",
            "posting__disposition__receipt",
            "posting__disposition__stock_entry",
            "location",
        ),
        pk=count_id,
    )
    if request.method == "GET" and hasattr(taken, "adjustment"):
        return _back(taken.posting.disposition)
    form = StockAdjustmentForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            stores.adjust(user, taken, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(taken.posting.disposition)
    unit = taken.posting.evidence.unit
    return _render_form(
        request,
        form,
        "Adjust Stock After a Count",
        receipt=taken.posting.disposition.receipt,
        count=taken,
        variance=("+" if taken.variance > 0 else "")
        + stores.quantity_text(taken.variance, "")
        + (" L" if unit == "Litre" else ""),
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def stores_locations(request: HttpRequest) -> HttpResponse:
    """Show the Stores locations and their rules (REQ-358)."""
    user, today = _access(request, Action.VIEW_RECORDS)
    places = StoresLocation.objects.filter(organisation=user.organisation).select_related(
        "withdrawal"
    )
    return render(
        request,
        "logistics/stores_locations.html",
        {
            "locations": places,
            "today": today,
            "may_locate": stores.may_act(user, Action.RECORD_STORES, StoresAction.LOCATIONS, today),
        },
    )


@never_cache
@requires(Action.RECORD_STORES)
@require_http_methods(["GET", "POST"])
def add_stores_location(request: HttpRequest) -> HttpResponse:
    """Record a Stores location with the classes and conditions it accepts (REQ-358)."""
    user, _ = _access(request, Action.RECORD_STORES)
    form = StoresLocationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            stores.record_location(user, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("stores_locations")
    return _render_form(request, form, "Add a Stores Location")


@never_cache
@requires(Action.RECORD_STORES)
@require_http_methods(["GET", "POST"])
def withdraw_stores_location(request: HttpRequest, location_id: UUID) -> HttpResponse:
    """Withdraw an empty Stores location from use (REQ-358)."""
    user, _ = _access(request, Action.RECORD_STORES)
    place = get_object_or_404(
        StoresLocation.objects.filter(organisation=user.organisation), pk=location_id
    )
    form = StoresWithdrawalForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            stores.withdraw_location(user, place, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("stores_locations")
    return _render_form(request, form, f"Withdraw {place}")


@never_cache
@requires(Action.VIEW_RECORDS)
def stores_appointments(request: HttpRequest) -> HttpResponse:
    """Show the Stores appointments and their status (REQ-358)."""
    user, today = _access(request, Action.VIEW_RECORDS)
    return render(
        request,
        "logistics/stores_appointments.html",
        {
            "appointments": StoresAppointment.objects.filter(
                organisation=user.organisation
            ).select_related("person", "approval", "withdrawal"),
            "today": today,
            "may_manage": user.may(Action.MANAGE_STORES_APPOINTMENTS),
        },
    )


@never_cache
@requires(Action.MANAGE_STORES_APPOINTMENTS)
@require_http_methods(["GET", "POST"])
def add_stores_appointment(request: HttpRequest) -> HttpResponse:
    """Record a person's dated Stores appointment under the exposition (REQ-358)."""
    user, today = _access(request, Action.MANAGE_STORES_APPOINTMENTS)
    form = StoresAppointmentForm(
        request.POST if request.method == "POST" else None,
        initial={"starts_on": today.isoformat()},
    )
    if request.method == "POST" and form.is_valid():
        try:
            stores.record_appointment(user, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("stores_appointments")
    return _render_form(request, form, "Record a Stores Appointment")


@never_cache
@requires(Action.MANAGE_STORES_APPOINTMENTS)
@require_http_methods(["GET", "POST"])
def withdraw_stores_appointment(request: HttpRequest, appointment_id: UUID) -> HttpResponse:
    """Withdraw a Stores appointment from a dated day (REQ-358)."""
    user, _ = _access(request, Action.MANAGE_STORES_APPOINTMENTS)
    appointment = get_object_or_404(
        StoresAppointment.objects.filter(organisation=user.organisation).select_related("person"),
        pk=appointment_id,
    )
    form = StoresWithdrawalForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            stores.withdraw_appointment(user, appointment, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("stores_appointments")
    return _render_form(request, form, f"Withdraw {appointment}")
