"""The Problem Log and Organisation pages (REQ-172 to REQ-174)."""

import uuid
from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from airworthiness_plus.acceptance import services
from airworthiness_plus.acceptance.forms import ApprovalForm, NoteForm, ParallelRunForm, ProblemForm
from airworthiness_plus.acceptance.models import NoteKind, Problem
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.organisations.models import Organisation


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


def _log(request: HttpRequest, message: str = "") -> HttpResponse:
    return render(
        request,
        "acceptance/problem_log.html",
        {
            "lines": services.problem_log(),
            "problem_form": ProblemForm(),
            "note_form": NoteForm(),
            "message": message,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def problem_log(request: HttpRequest) -> HttpResponse:
    """Every problem raised, with the action, the solution, the dates and the people."""
    return _log(request)


@requires(Action.ADD_TO_PROBLEM_LOG)
@require_POST
def add_problem(request: HttpRequest) -> HttpResponse:
    """Add an entry to the problem log."""
    form = ProblemForm(request.POST)
    if not form.is_valid():
        return _log(request, "Describe the Problem")
    user = _user(request)
    services.add_problem(
        organisation=user.organisation, raised_by=user, problem=form.cleaned_data["problem"]
    )
    return redirect("problem_log")


@requires(Action.ADD_TO_PROBLEM_LOG)
@require_POST
def add_note(request: HttpRequest, problem_id: uuid.UUID) -> HttpResponse:
    """Add the action, the solution or a note to an entry."""
    problem = get_object_or_404(Problem, pk=problem_id)
    form = NoteForm(request.POST)
    if not form.is_valid():
        return _log(request, "Choose What to Add, and Say What Was Done or Found")
    services.add_note(
        problem,
        kind=NoteKind(form.cleaned_data["kind"]),
        text=form.cleaned_data["text"],
        noted_by=_user(request),
    )
    return redirect("problem_log")


def _organisation(request: HttpRequest) -> Organisation:
    return Organisation.objects.get(pk=_user(request).organisation_id)


def _organisation_page(request: HttpRequest, message: str = "") -> HttpResponse:
    organisation = _organisation(request)
    return render(
        request,
        "acceptance/organisation.html",
        {
            "organisation": organisation,
            "run": services.parallel_run(organisation),
            "approval_form": ApprovalForm(),
            "run_form": ParallelRunForm(),
            "message": message,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def organisation_page(request: HttpRequest) -> HttpResponse:
    """The organisation record, the written approval and the parallel run."""
    return _organisation_page(request)


@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_POST
def record_approval(request: HttpRequest) -> HttpResponse:
    """Record the written approval to keep records in the system."""
    form = ApprovalForm(request.POST)
    message = "Give the Approval Reference and Its Date"
    if form.is_valid():
        try:
            services.record_approval(_organisation(request), **form.cleaned_data)
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("organisation")
    return _organisation_page(request, message)


@requires(Action.CHANGE_ORGANISATION_RECORD)
@require_POST
def record_parallel_run(request: HttpRequest) -> HttpResponse:
    """Record the day the parallel run began."""
    form = ParallelRunForm(request.POST)
    message = "Give the Day the Parallel Run Started"
    if form.is_valid():
        try:
            services.record_parallel_run(_organisation(request), **form.cleaned_data)
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("organisation")
    return _organisation_page(request, message)
