"""Stores pages: the posting backlog, locations, the location ledger, counts and adjustments."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics import (
    services,
    station_stock,
    stock_appointments,
    stores,
    substitutions,
)
from airworthiness_plus.logistics.forms import (
    PostStockForm,
    StockAdjustmentForm,
    StockCountForm,
    StockMovementForm,
    StockResolutionForm,
    StoreLocationForm,
)
from airworthiness_plus.logistics.models import (
    Destination,
    ReceivingDisposition,
    StockCount,
    StockDuty,
    StockEntry,
    StockPosting,
    StoreLocation,
)
from airworthiness_plus.people.models import Person


def _access(request: HttpRequest, action: Action) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by requires
    if not services.maintenance_approvals(user.organisation, aircraft_services.today()):
        raise ActionRefusedError(action)
    return user


def _actor(user: User) -> Person:
    person = getattr(user, "person", None)
    if not isinstance(person, Person):
        raise services.RefusedError("This Sign-In Has No Person Record")
    return person


def _lead(user: User) -> int:
    return int(user.organisation.due_soon_days)


def _state(decision: ReceivingDisposition, lot: StockPosting | None) -> str:
    if decision.outcome == Destination.RETURN:
        return "Returned to Supplier"
    if decision.outcome == Destination.QUARANTINE:
        return "Quarantine Hold" if lot is not None else "Quarantine Hold, Details to Verify"
    return "Posted to Stock" if lot is not None else "Awaiting Stock Posting"


def _line(decision: ReceivingDisposition, today: date, lead: int) -> dict[str, Any]:
    lot = getattr(decision, "stock_posting", None)
    resolution = stores.latest_resolution(decision) if lot is None else lot.resolution
    blockers = [] if lot is not None else stores.posting_blockers(decision, resolution)
    lines = stores.positions([lot], today, lead) if lot is not None else []
    return {
        "decision": decision,
        "receipt": decision.receipt,
        "entry": getattr(decision, "stock_entry", None),
        "lot": lot,
        "resolution": resolution,
        "state": _state(decision, lot),
        "blockers": blockers,
        "positions": lines,
        "on_hand": stores.display(sum((one.on_hand for one in lines), Decimal(0))),
        "available": stores.display(sum((one.available for one in lines), Decimal(0))),
        "reserved": stores.display(sum((one.reserved for one in lines), Decimal(0))),
        "shelf": stores.lot_shelf(lot, today, lead) if lot is not None else "",
        "unit": lot.unit if lot is not None else (resolution.unit if resolution else ""),
    }


def _decisions(user: User) -> Any:
    return (
        ReceivingDisposition.objects.filter(organisation=user.organisation)
        .select_related("receipt", "stock_entry", "stock_posting__resolution")
        .prefetch_related("stock_posting__movements", "stock_resolutions__location")
        .order_by("-disposition_on", "receipt__item", "id")
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def stores_stock(request: HttpRequest) -> HttpResponse:
    """The Stores register: posted custody, the posting backlog, holds and returns."""
    user = _access(request, Action.VIEW_RECORDS)
    today, lead = aircraft_services.today(), _lead(user)
    lines = [_line(decision, today, lead) for decision in _decisions(user)]
    identity = request.GET.get("identity", "").strip()
    if identity:
        lines = [
            line
            for line in lines
            if (record := line["lot"] or line["resolution"]) is not None
            and station_stock.matches(record, line["receipt"].classification, identity)
        ]
    lots = [line["lot"] for line in lines if line["lot"] is not None]
    positions = stores.positions(lots, today, lead)
    configured = StoreLocation.objects.filter(organisation=user.organisation, active=True)
    summary = station_stock.summarise(positions, configured)
    return render(
        request,
        "logistics/stock.html",
        {
            "entries": [line for line in lines if line["decision"].outcome == Destination.STORES],
            "holds": [line for line in lines if line["decision"].outcome == Destination.QUARANTINE],
            "returns": [line for line in lines if line["decision"].outcome == Destination.RETURN],
            "positions": positions,
            "identity": identity,
            "summary": summary,
            "display": stores.display,
        },
    )


def _detail(request: HttpRequest, user: User, decision: ReceivingDisposition) -> HttpResponse:
    today, lead = aircraft_services.today(), _lead(user)
    line = _line(decision, today, lead)
    lot = line["lot"]
    return render(
        request,
        "logistics/stock_entry.html",
        {
            **line,
            "disposition": decision,
            "resolutions": list(decision.stock_resolutions.select_related("location")),
            "movements": list(lot.movements.select_related("from_location", "to_location"))
            if lot
            else [],
            "counts": list(lot.counts.select_related("location", "adjustment")) if lot else [],
            "allocations": lot.allocations.select_related(
                "source",
                "destination",
                "card__package",
                "appointment__person",
                "following",
                "substitution__authorisation__person",
            )
            if lot
            else [],
            "approved_alternates": substitutions.available(lot, today) if lot else [],
            "may_approve_substitution": bool(
                lot
                and user.may(Action.RECORD_RELEASE_CERTIFICATE)
                and substitutions.authorisations(user, today).exists()
            ),
            "may_reserve": stock_appointments.current(user, StockDuty.RESERVE, today) is not None,
            "may_issue": stock_appointments.current(user, StockDuty.ISSUE, today) is not None,
            "may_return": stock_appointments.current(user, StockDuty.RETURN, today) is not None,
            "may_quarantine": stock_appointments.current(user, StockDuty.QUARANTINE, today)
            is not None,
            "may_post": user.may(Action.POST_STOCK)
            and lot is None
            and stock_appointments.current(user, StockDuty.POST, today) is not None,
            "may_move": user.may(Action.MOVE_STOCK)
            and lot is not None
            and stock_appointments.current(user, StockDuty.MOVE, today) is not None,
            "may_count": user.may(Action.COUNT_STOCK)
            and lot is not None
            and stock_appointments.current(user, StockDuty.COUNT, today) is not None,
            "may_adjust": user.may(Action.ADJUST_STOCK)
            and stock_appointments.current(user, StockDuty.ADJUST, today) is not None,
            "ready": lot is None and not line["blockers"],
            "post_form": PostStockForm(initial={"posted_on": today}),
            "display": stores.display,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def stock_entry(request: HttpRequest, stock_id: UUID) -> HttpResponse:
    """One acceptance's Stores entry, posting state, blockers and ledger (REQ-357, REQ-358)."""
    user = _access(request, Action.VIEW_RECORDS)
    entry = get_object_or_404(
        StockEntry.objects.filter(organisation=user.organisation), pk=stock_id
    )
    return _detail(request, user, _decisions(user).get(pk=entry.disposition_id))


@never_cache
@requires(Action.VIEW_RECORDS)
def stores_disposition(request: HttpRequest, disposition_id: UUID) -> HttpResponse:
    """A quarantine hold or a supplier return as Stores shows it."""
    user = _access(request, Action.VIEW_RECORDS)
    decision = get_object_or_404(_decisions(user), pk=disposition_id)
    if decision.outcome == Destination.STORES:
        return redirect("stock_entry", stock_id=decision.stock_entry.pk)
    return _detail(request, user, decision)


def _back(decision: ReceivingDisposition) -> HttpResponse:
    entry = getattr(decision, "stock_entry", None)
    if entry is not None:
        return redirect("stock_entry", stock_id=entry.pk)
    return redirect("stores_disposition", disposition_id=decision.pk)


def _form_page(request: HttpRequest, form: Any, heading: str, back: str) -> HttpResponse:
    return render(
        request,
        "logistics/stores_form.html",
        {"form": form, "heading": heading, "button": heading, "back": back},
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def store_locations(request: HttpRequest) -> HttpResponse:
    """The organisation's Stores and quarantine locations and the classes each may hold."""
    user = _access(request, Action.VIEW_RECORDS)
    return render(
        request,
        "logistics/locations.html",
        {
            "locations": StoreLocation.objects.filter(organisation=user.organisation),
            "may_add": user.may(Action.MANAGE_STORE_LOCATIONS),
        },
    )


@never_cache
@requires(Action.MANAGE_STORE_LOCATIONS)
@require_http_methods(["GET", "POST"])
def add_store_location(request: HttpRequest) -> HttpResponse:
    """Add a Stores or quarantine location with its classes and storage rules."""
    user = _access(request, Action.MANAGE_STORE_LOCATIONS)
    form = StoreLocationForm(request.POST if request.method == "POST" else None)
    if form.is_bound and form.is_valid():
        try:
            stores.add_location(user.organisation, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("store_locations")
    return _form_page(request, form, "Add a Stores Location", "/stores/locations/")


@never_cache
@requires(Action.POST_STOCK)
@require_http_methods(["GET", "POST"])
def resolve_stock(request: HttpRequest, disposition_id: UUID) -> HttpResponse:
    """Record the dated structured reading of unit, identity, location and shelf life."""
    user = _access(request, Action.POST_STOCK)
    decision = get_object_or_404(_decisions(user), pk=disposition_id)
    if decision.outcome == Destination.RETURN:
        raise Http404
    form = StockResolutionForm(
        request.POST if request.method == "POST" else None,
        organisation=user.organisation,
        initial={"evidence_on": aircraft_services.today()},
    )
    if form.is_bound and form.is_valid():
        try:
            stores.resolve(decision, actor=_actor(user), **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(decision)
    return _form_page(
        request,
        form,
        f"Resolve {decision.receipt.delivery_reference} for Stock",
        _back(decision)["Location"],
    )


@never_cache
@requires(Action.POST_STOCK)
@require_POST
def post_stock(request: HttpRequest, disposition_id: UUID) -> HttpResponse:
    """Post the disposition once. A repeated submission returns the original posting."""
    user = _access(request, Action.POST_STOCK)
    decision = get_object_or_404(_decisions(user), pk=disposition_id)
    form = PostStockForm(request.POST)
    if form.is_valid():
        try:
            stores.post(decision, actor=_actor(user), **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(decision)
    return _form_page(
        request, form, f"Post {decision.receipt.delivery_reference}", _back(decision)["Location"]
    )


def _lot(user: User, lot_id: UUID) -> StockPosting:
    return get_object_or_404(
        StockPosting.objects.filter(organisation=user.organisation).select_related(
            "disposition__receipt", "disposition__stock_entry"
        ),
        pk=lot_id,
    )


@never_cache
@requires(Action.MOVE_STOCK)
@require_http_methods(["GET", "POST"])
def move_stock(request: HttpRequest, lot_id: UUID) -> HttpResponse:
    """Move part or all of a position between compatible locations, conserving quantity."""
    user = _access(request, Action.MOVE_STOCK)
    lot = _lot(user, lot_id)
    form = StockMovementForm(
        request.POST if request.method == "POST" else None,
        organisation=user.organisation,
        initial={"moved_on": aircraft_services.today()},
    )
    if form.is_bound and form.is_valid():
        try:
            stores.move(lot, actor=_actor(user), **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(lot.disposition)
    return _form_page(request, form, "Move Stock", _back(lot.disposition)["Location"])


@never_cache
@requires(Action.COUNT_STOCK)
@require_http_methods(["GET", "POST"])
def count_stock(request: HttpRequest, lot_id: UUID) -> HttpResponse:
    """Record a physical count against the ledger. No balance changes."""
    user = _access(request, Action.COUNT_STOCK)
    lot = _lot(user, lot_id)
    form = StockCountForm(
        request.POST if request.method == "POST" else None,
        organisation=user.organisation,
        initial={"counted_on": aircraft_services.today()},
    )
    if form.is_bound and form.is_valid():
        try:
            stores.count(lot, counter=_actor(user), **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(lot.disposition)
    return _form_page(request, form, "Record a Stock Count", _back(lot.disposition)["Location"])


@never_cache
@requires(Action.ADJUST_STOCK)
@require_http_methods(["GET", "POST"])
def adjust_stock(request: HttpRequest, count_id: UUID) -> HttpResponse:
    """Apply a count's variance once, with the adjuster's authority and evidence."""
    user = _access(request, Action.ADJUST_STOCK)
    tally = get_object_or_404(
        StockCount.objects.filter(organisation=user.organisation).select_related(
            "lot__disposition__stock_entry", "location"
        ),
        pk=count_id,
    )
    form = StockAdjustmentForm(
        request.POST if request.method == "POST" else None,
        initial={"moved_on": aircraft_services.today()},
    )
    if form.is_bound and form.is_valid():
        try:
            stores.adjust(tally, actor=_actor(user), **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return _back(tally.lot.disposition)
    return _form_page(
        request,
        form,
        f"Adjust by {stores.display(tally.variance)} From the Count",
        _back(tally.lot.disposition)["Location"],
    )
