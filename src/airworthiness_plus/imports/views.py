"""The Import pages: loading a file and its verification report (REQ-170, REQ-171)."""

import uuid
from typing import cast

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.imports import services
from airworthiness_plus.imports.forms import LoadForm
from airworthiness_plus.imports.layouts import COLUMNS, OPTIONAL
from airworthiness_plus.imports.models import Load, LoadKind


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


def _imports(request: HttpRequest, message: str = "") -> HttpResponse:
    layouts = [
        (kind.label, ", ".join(COLUMNS[kind]), ", ".join(sorted(OPTIONAL[kind])))
        for kind in LoadKind
    ]
    return render(
        request,
        "imports/imports.html",
        {
            "reports": services.reports(),
            "form": LoadForm(),
            "layouts": layouts,
            "message": message,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def imports_page(request: HttpRequest) -> HttpResponse:
    """Every file loaded, with the proportion of its values checked against the source."""
    return _imports(request)


@requires(Action.IMPORT_RECORDS)
@require_POST
def load(request: HttpRequest) -> HttpResponse:
    """Load a file. It is loaded whole, or not at all with the reasons shown."""
    form = LoadForm(request.POST, request.FILES)
    if not form.is_valid():
        return _imports(request, "Choose What the File Holds, Name Its Source and Give the File")
    upload = form.cleaned_data["file"]
    if not (upload.name or "").lower().endswith(".csv"):
        return _imports(request, "The File Is a CSV File, with a Name Ending in .csv")
    if upload.size > services.MAXIMUM_BYTES:
        return _imports(request, "The File Is Larger Than 1 Megabyte")
    user = _user(request)
    try:
        record = services.load(
            organisation=user.organisation,
            by=user,
            kind=LoadKind(form.cleaned_data["kind"]),
            source=form.cleaned_data["source"],
            file_name=upload.name or "",
            content=upload.read(),
        )
    except services.RefusedError as error:
        return _imports(request, str(error))
    return redirect("import_report", load_id=record.id)


@never_cache
@requires(Action.VIEW_RECORDS)
def report_page(request: HttpRequest, load_id: uuid.UUID) -> HttpResponse:
    """The verification report: every imported value beside its source value."""
    record = get_object_or_404(Load, pk=load_id)
    return render(request, "imports/report.html", {"report": services.report(record)})


@requires(Action.CHECK_IMPORTED_RECORDS)
@require_POST
def check(request: HttpRequest, load_id: uuid.UUID) -> HttpResponse:
    """Record the values checked against the source. Each is ticked or given by hand."""
    record = get_object_or_404(Load, pk=load_id)
    agreed = [key.removeprefix("agrees_") for key in request.POST if key.startswith("agrees_")]
    differing = {
        key.removeprefix("source_"): request.POST.get(key, "")
        for key in request.POST
        if key.startswith("source_") and request.POST.get(key, "").strip()
    }
    try:
        services.record_checks(record, by=_user(request), agreed=agreed, differing=differing)
    except services.RefusedError as error:
        return render(
            request,
            "imports/report.html",
            {"report": services.report(record), "message": str(error)},
        )
    return redirect("import_report", load_id=record.id)
