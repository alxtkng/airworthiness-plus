"""Workshop custody, signed use and historical claim entry points."""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.planning.models import WorkPackage
from airworthiness_plus.tooling import custody, custody_forms
from airworthiness_plus.tooling.custody_models import ToolIssue
from airworthiness_plus.tooling.models import Tool
from airworthiness_plus.tooling.views import _user


def _tool(request: HttpRequest, tool_id: UUID) -> Tool:
    return get_object_or_404(Tool, pk=tool_id, organisation_id=_user(request).organisation_id)


def _issue(request: HttpRequest, issue_id: UUID) -> ToolIssue:
    return get_object_or_404(
        ToolIssue.objects.select_related(
            "tool",
            "work_approval__package",
            "work_approval__approval",
            "custodian",
            "return_record__returned_by",
            "return_record__delegation__person",
        ),
        pk=issue_id,
        organisation_id=_user(request).organisation_id,
    )


def _form(
    request: HttpRequest,
    form: Form,
    title: str,
    subject: object,
    submit: Callable[..., HttpResponse],
) -> HttpResponse:
    if request.method == "POST" and form.is_valid():
        try:
            return submit(**form.cleaned_data)
        except custody.RefusedError as error:
            form.add_error(None, str(error))
    return render(request, "tooling/form.html", {"form": form, "title": title, "tool": subject})


@never_cache
@requires(Action.PLAN_WORK_PACKAGE)
@require_http_methods(["GET", "POST"])
def assign_approval(request: HttpRequest, package_id: UUID) -> HttpResponse:
    """Pin the governing maintenance approval for an issued package."""
    user = _user(request)
    package = get_object_or_404(WorkPackage, pk=package_id, organisation_id=user.organisation_id)

    def save(**values: str) -> HttpResponse:
        custody.assign_approval(user, package, **values)
        return redirect("work_package", package_id=package.pk)

    return _form(
        request,
        custody_forms.AssignmentForm(request.POST or None),
        "Record Governing Approval",
        None,
        save,
    )


@never_cache
@requires(custody.WRITE)
@require_http_methods(["GET", "POST"])
def issue_tool(request: HttpRequest, tool_id: UUID) -> HttpResponse:
    """Record the single open physical issue of an eligible tool."""
    tool = _tool(request, tool_id)

    def save(**values: Any) -> HttpResponse:
        issue = custody.issue_tool(_user(request), tool, **values)
        return redirect("tool_issue", issue_id=issue.pk)

    return _form(
        request,
        custody_forms.IssueForm(request.POST or None),
        "Issue Tool",
        tool,
        save,
    )


@never_cache
@requires(Action.VIEW_RECORDS)
@require_http_methods(["GET", "HEAD"])
def issue_record(request: HttpRequest, issue_id: UUID) -> HttpResponse:
    """Show custody, use, inspections and return for one tool issue."""
    issue = _issue(request, issue_id)
    return render(
        request,
        "tooling/issue.html",
        {
            "issue": issue,
            "inspections": issue.inspections.select_related(
                "card", "revision", "delegation__person"
            ),
            "uses": issue.uses.select_related(
                "card", "revision", "delegation__person", "inspection"
            ),
            "may_record": _user(request).may(custody.WRITE),
        },
    )


@never_cache
@requires(custody.WRITE)
@require_http_methods(["GET", "POST"])
def record_inspection(request: HttpRequest, issue_id: UUID) -> HttpResponse:
    """Record the results of a task-specific pre-use inspection."""
    issue = _issue(request, issue_id)

    def save(**values: Any) -> HttpResponse:
        custody.record_inspection(_user(request), issue, **values)
        return redirect("tool_issue", issue_id=issue.pk)

    return _form(
        request,
        custody_forms.InspectionForm(request.POST or None, issue=issue),
        "Record Pre-Use Inspection",
        issue.tool,
        save,
    )


@never_cache
@requires(custody.WRITE)
@require_http_methods(["GET", "POST"])
def record_use(request: HttpRequest, issue_id: UUID) -> HttpResponse:
    """Record attributable actual use against a work card and revision."""
    issue = _issue(request, issue_id)

    def save(**values: Any) -> HttpResponse:
        custody.record_use(_user(request), issue, **values)
        return redirect("tool_issue", issue_id=issue.pk)

    return _form(
        request,
        custody_forms.UseForm(request.POST or None, issue=issue),
        "Record Actual Use",
        issue.tool,
        save,
    )


@never_cache
@requires(custody.WRITE)
@require_http_methods(["GET", "POST"])
def return_tool(request: HttpRequest, issue_id: UUID) -> HttpResponse:
    """Record return, destination and physical condition separately."""
    issue = _issue(request, issue_id)

    def save(**values: Any) -> HttpResponse:
        custody.return_tool(_user(request), issue, **values)
        return redirect("tool_issue", issue_id=issue.pk)

    return _form(
        request,
        custody_forms.ReturnForm(request.POST or None),
        "Record Tool Return",
        issue.tool,
        save,
    )


@never_cache
@requires(custody.WRITE)
@require_http_methods(["GET", "POST"])
def record_claim(request: HttpRequest, tool_id: UUID) -> HttpResponse:
    """Retain an attributable historical tool claim and evidence gaps."""
    tool = _tool(request, tool_id)

    def save(**values: Any) -> HttpResponse:
        custody.record_claim(_user(request), tool, **values)
        return redirect("tool_record", tool_id=tool.pk)

    return _form(
        request,
        custody_forms.ClaimForm(request.POST or None),
        "Record Historical Tool Claim",
        tool,
        save,
    )
