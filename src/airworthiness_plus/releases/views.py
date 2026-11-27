"""Pages for certificates of release to service (REQ-260 to REQ-268).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). Work of another organisation is not
found, because the database does not show it (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.planning.pending import releases_waiting
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.releases import services
from airworthiness_plus.releases.forms import CertificateForm, HistoricalReleaseEvidenceForm
from airworthiness_plus.releases.models import HistoricalReleaseEvidence, Release


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def release_to_service(request: HttpRequest) -> HttpResponse:
    """Certificates of release to service, and whether each is in the records (REQ-264)."""
    today = aircraft_services.today()
    lines = services.release_lines(today)
    waiting = releases_waiting(today)
    summary = services.summary(lines)
    return render(
        request,
        "releases/releases.html",
        {
            "lines": lines,
            "summary": summary,
            "waiting_packages": waiting,
            "not_in_records": summary.not_in_records + len(waiting),
            "historical_evidence": HistoricalReleaseEvidence.objects.select_related(
                "work__aircraft", "grounding_defect"
            ),
            "who": services.WHO_MAY_RELEASE,
            "may_record": _user(request).may(Action.RECORD_RELEASE_CERTIFICATE),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def release_certificate(request: HttpRequest, release_id: uuid.UUID) -> HttpResponse:
    """Show the retained release and any certification evidence (REQ-302)."""
    certificate = get_object_or_404(
        Release.objects.select_related(
            "work", "maintenance_authorisation__withdrawal", "work_package"
        ),
        pk=release_id,
    )
    package = getattr(certificate, "work_package", None)
    cards = package.cards.all() if package is not None else ()
    return render(
        request,
        "releases/certificate.html",
        {"certificate": certificate, "package": package, "cards": cards},
    )


@never_cache
@requires(Action.RECORD_RELEASE_CERTIFICATE)
@require_http_methods(["GET", "POST"])
def record_release_certificate(request: HttpRequest, work_id: uuid.UUID) -> HttpResponse:
    """Record the certificate of release to service for work done (REQ-260)."""
    work = get_object_or_404(WorkDone.objects.select_related("aircraft"), pk=work_id)
    form = CertificateForm(request.POST or None, initial={"reference": work.release_reference})
    if request.method == "POST" and form.is_valid():
        try:
            services.record_certificate(work, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("release_to_service")
    return render(
        request,
        "releases/record.html",
        {"form": form, "work": work, "who": services.WHO_MAY_RELEASE},
    )


@never_cache
@requires(Action.RECORD_RELEASE_CERTIFICATE)
@require_http_methods(["GET", "POST"])
def record_historical_release_evidence(request: HttpRequest, work_id: uuid.UUID) -> HttpResponse:
    """Retain a signed historical source dated during a grounding period."""
    work = get_object_or_404(WorkDone.objects.select_related("aircraft"), pk=work_id)
    form = HistoricalReleaseEvidenceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.retain_historical_evidence(work, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("release_to_service")
    return render(request, "releases/historical_evidence.html", {"form": form, "work": work})
