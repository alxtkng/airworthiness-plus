"""The Staffing Plan and its record forms."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Approval
from airworthiness_plus.staffing import forms, rules, services
from airworthiness_plus.staffing.models import Absence, Demand, Report, Review


@dataclass(frozen=True)
class Line:
    demand: Demand
    result: rules.Assessment
    reported: bool

    @property
    def status(self) -> str:
        if self.result.reportable:
            return "Reported" if self.reported else "Report Needed"
        return "Shortfall" if self.result.shortfall else "Within Plan"


@dataclass(frozen=True)
class ReviewLine:
    approval: Approval
    latest: Review | None

    @property
    def next_due(self) -> date | None:
        if self.latest is None:
            return None
        return rules.required_review_by(self.latest.reviewed_on, self.approval.approval)


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101
    return user


def _form(
    request: HttpRequest, form: Form, title: str, submit: Callable[..., object]
) -> HttpResponse:
    if request.method == "POST" and form.is_valid():
        try:
            submit(actor=_user(request), **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("staffing_plan")
    return render(request, "contracts/form.html", {"form": form, "title": title, "button": title})


@never_cache
@requires(Action.VIEW_RECORDS)
def staffing_plan(request: HttpRequest) -> HttpResponse:
    """Show monthly staffing adequacy, reviews, reports and absences."""
    user = _user(request)
    lines = [
        Line(
            demand,
            rules.assess(
                needed=demand.needed,
                employed=demand.employed,
                contracted=demand.contracted,
                approval=demand.approval.approval,
            ),
            any(
                (entry.needed, entry.employed, entry.contracted)
                == (demand.needed, demand.employed, demand.contracted)
                for entry in demand.reports.all()
            ),
        )
        for demand in Demand.objects.select_related("approval").prefetch_related("reports")
    ]
    reviews: dict[UUID, Review] = {}
    for review in Review.objects.all():
        reviews.setdefault(review.approval_id, review)
    from airworthiness_plus.aircraft import services as aircraft_services
    from airworthiness_plus.staffing import roster
    from airworthiness_plus.staffing.roster_rules import week_of

    week = week_of(aircraft_services.today())
    checked = roster.check_shifts(week, roster.settings_for(user.organisation))
    return render(
        request,
        "staffing/plan.html",
        {
            "lines": lines,
            "reviews": [
                ReviewLine(approval, reviews.get(approval.id))
                for approval in approvals.held(user.organisation)
            ],
            "reports": Report.objects.select_related("demand__approval", "reported_by"),
            "absences": Absence.objects.select_related("person"),
            "may_staff": user.may(Action.RECORD_STAFFING_PLAN),
            "crews": roster.crews(checked),
        },
    )


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def record_staffing_hours(request: HttpRequest) -> HttpResponse:
    """Set the hours needed and available for a function and month."""
    return _form(
        request,
        forms.DemandForm(request.POST or None),
        "Record Staffing Hours",
        services.record_demand,
    )


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def review_staffing_plan(request: HttpRequest) -> HttpResponse:
    """Record a review of the plan under its approval."""
    return _form(
        request, forms.ReviewForm(request.POST or None), "Review the Plan", services.review_plan
    )


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def record_staffing_shortfall(request: HttpRequest, demand_id: UUID) -> HttpResponse:
    """Record a reported Part-145 shortfall and retain its figures."""
    demand = get_object_or_404(Demand, pk=demand_id)
    form = forms.ReportForm(
        request.POST or None,
        initial={"reported_to": "Compliance Monitoring Manager, Accountable Manager"},
    )
    return _form(
        request,
        form,
        "Record a Shortfall Report",
        lambda **values: services.record_report(demand, **values),
    )


@never_cache
@requires(Action.RECORD_STAFFING_PLAN)
@require_http_methods(["GET", "POST"])
def record_staff_absence(request: HttpRequest) -> HttpResponse:
    """Record an absence for a person and a range of days."""
    return _form(
        request,
        forms.AbsenceForm(request.POST or None),
        "Record an Absence",
        services.record_absence,
    )
