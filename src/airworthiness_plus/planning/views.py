"""The work package board, cards and evidence forms."""

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.planning import forms, services
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.releases.services import maintains


def _user(request: HttpRequest, *, write: bool = True) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101
    if write and not maintains(user.organisation):
        raise Http404
    return user


def _package(package_id: UUID) -> WorkPackage:
    return get_object_or_404(
        WorkPackage.objects.select_related("aircraft", "order", "defect"), pk=package_id
    )


def _card(package_id: UUID, card_id: UUID) -> WorkCard:
    return get_object_or_404(WorkCard, pk=card_id, package_id=package_id)


def _form(
    request: HttpRequest,
    form: Form,
    title: str,
    submit: Callable[..., object],
    package: WorkPackage | None = None,
) -> HttpResponse:
    if request.method == "POST" and form.is_valid():
        try:
            result = submit(**form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            target = package or result
            if isinstance(target, WorkPackage):
                return redirect("work_package", package_id=target.id)
    return render(request, "contracts/form.html", {"form": form, "title": title, "button": title})


@never_cache
@requires(Action.VIEW_RECORDS)
def work_packages(request: HttpRequest) -> HttpResponse:
    user = _user(request, write=False)
    packages = WorkPackage.objects.select_related("aircraft", "order").prefetch_related("cards")
    return render(
        request,
        "planning/work_packages.html",
        {
            "packages": packages,
            "may_plan": maintains(user.organisation) and user.may(Action.PLAN_WORK_PACKAGE),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def work_package(request: HttpRequest, package_id: UUID) -> HttpResponse:
    user = _user(request, write=False)
    package = _package(package_id)
    may_maintain = maintains(user.organisation)
    cards = list(
        package.cards.select_related(
            "data_set",
            "revision",
            "performed_by",
            "supervised_by",
            "inspector",
            "work__certificate",
        )
    )
    open_cards = [card for card in cards if card.completed_on is None]
    awaiting_inspection = [card for card in cards if card.completed_on and not card.signed]
    return render(
        request,
        "planning/work_package.html",
        {
            "package": package,
            "cards": cards,
            "signed": sum(card.signed for card in cards),
            "completed": len(cards) - len(open_cards),
            "open_cards": open_cards,
            "open_hours": sum((card.planned_hours for card in open_cards), Decimal("0.0")),
            "awaiting_inspection": awaiting_inspection,
            "missing_inspections": sum(
                card.critical and card.inspected_on is None for card in cards
            ),
            "planned": sum((card.planned_hours for card in cards), Decimal("0.0")),
            "inspection": sum((card.inspection_hours for card in cards), Decimal("0.0")),
            "may_plan": may_maintain and user.may(Action.PLAN_WORK_PACKAGE),
            "may_record": may_maintain and user.may(Action.RECORD_WORK_CARD),
            "may_release": may_maintain and user.may(Action.RECORD_RELEASE_CERTIFICATE),
        },
    )


@never_cache
@requires(Action.PLAN_WORK_PACKAGE)
@require_http_methods(["GET", "POST"])
def build_work_package(request: HttpRequest) -> HttpResponse:
    """Build a draft work package."""
    _user(request)
    return _form(
        request,
        forms.BuildPackageForm(request.POST or None),
        "Build a Work Package",
        services.build_package,
    )


@never_cache
@requires(Action.PLAN_WORK_PACKAGE)
@require_http_methods(["GET", "POST"])
def link_package_order(request: HttpRequest, package_id: UUID) -> HttpResponse:
    """Link an open work order to the draft package."""
    _user(request)
    package = _package(package_id)
    return _form(
        request,
        forms.LinkOrderForm(request.POST or None, package=package),
        "Link Work Order",
        lambda **values: services.link_order(package, **values),
        package,
    )


@never_cache
@requires(Action.PLAN_WORK_PACKAGE)
@require_http_methods(["GET", "POST"])
def add_work_card(request: HttpRequest, package_id: UUID) -> HttpResponse:
    """Plan a task and identify its maintenance data."""
    _user(request)
    package = _package(package_id)
    return _form(
        request,
        forms.WorkCardForm(request.POST or None, package=package),
        "Add Work Card",
        lambda **values: services.add_card(package, **values),
        package,
    )


@never_cache
@requires(Action.PLAN_WORK_PACKAGE)
@require_http_methods(["GET", "POST"])
def issue_work_package(request: HttpRequest, package_id: UUID) -> HttpResponse:
    """Issue the package with checked maintenance data."""
    _user(request)
    package = _package(package_id)
    return _form(
        request,
        Form(request.POST if request.method == "POST" else None),
        "Issue Work Package",
        lambda: services.issue_package(package),
        package,
    )


@never_cache
@requires(Action.RECORD_WORK_CARD)
@require_http_methods(["GET", "POST"])
def complete_work_card(request: HttpRequest, package_id: UUID, card_id: UUID) -> HttpResponse:
    """Record signed evidence of the work performed."""
    _user(request)
    card = _card(package_id, card_id)
    return _form(
        request,
        forms.WorkCompletionForm(request.POST or None, card=card),
        "Record Signed Work",
        lambda **values: services.record_completion(card, **values),
        card.package,
    )


@never_cache
@requires(Action.RECORD_WORK_CARD)
@require_http_methods(["GET", "POST"])
def inspect_work_card(request: HttpRequest, package_id: UUID, card_id: UUID) -> HttpResponse:
    """Record satisfactory independent inspection of a critical task."""
    _user(request)
    card = _card(package_id, card_id)
    return _form(
        request,
        forms.InspectionForm(request.POST or None),
        "Record Independent Inspection",
        lambda **values: services.record_inspection(card, **values),
        card.package,
    )


@never_cache
@requires(Action.RECORD_RELEASE_CERTIFICATE)
@require_http_methods(["GET", "POST"])
def release_work_package(request: HttpRequest, package_id: UUID) -> HttpResponse:
    """Record the package release after the release checklist is satisfied."""
    _user(request)
    package = _package(package_id)
    return _form(
        request,
        forms.PackageReleaseForm(request.POST or None),
        "Record Package Release",
        lambda **values: services.release_package(package, **values),
        package,
    )
