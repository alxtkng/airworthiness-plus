"""The Records Export page and the two exports (REQ-134, REQ-135)."""

import uuid
from datetime import timedelta
from typing import cast

from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessEntry, AccessKind, User
from airworthiness_plus.accounts.permissions import address_of, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.exports.build import Export, build


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


def _send(request: HttpRequest, export: Export) -> HttpResponse:
    """Log the export, with the SHA-256 of its manifest, and send the file (threat TH-080)."""
    sign_in.log_records_exported(
        _user(request), f"{export.subject}, SHA-256 {export.manifest_sha256}", address_of(request)
    )
    response = HttpResponse(export.content, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{export.name}"'
    response["Cache-Control"] = "no-store"
    return response


# Ours: the export of an organisation reads every record and its history, so
# it is limited for each organisation (OWASP ASVS 5.0, 15.2.2).
ORGANISATION_EXPORTS_AN_HOUR = 6


def _page(request: HttpRequest, message: str = "", status: int = 200) -> HttpResponse:
    made = AccessEntry.objects.filter(kind=AccessKind.RECORDS_EXPORTED).select_related("user")
    return render(
        request,
        "exports/exports.html",
        {
            "aircraft": Aircraft.objects.order_by("registration"),
            "organisation": _user(request).organisation,
            "made": made.order_by("-id"),
            "message": message,
        },
        status=status,
    )


@never_cache
@requires(Action.EXPORT_RECORDS)
def exports_page(request: HttpRequest) -> HttpResponse:
    """What can be exported, and every export made, with the SHA-256 of its manifest."""
    return _page(request)


@requires(Action.EXPORT_RECORDS)
@require_POST
def export_aircraft(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Export the complete record of one aircraft."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    return _send(request, build(aircraft.organisation, by=_user(request), aircraft=aircraft))


@requires(Action.EXPORT_RECORDS)
@require_POST
def export_organisation(request: HttpRequest) -> HttpResponse:
    """Export the complete record of the organisation."""
    user = _user(request)
    organisation = user.organisation
    # One at a time for each organisation, so that requests sent together are
    # counted one after another and cannot all pass the limit. The lock is held
    # until this request's entry in the access log is committed.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            [f"export of organisation {organisation.pk}"],
        )
    recent = AccessEntry.objects.filter(
        kind=AccessKind.RECORDS_EXPORTED,
        detail__startswith=f"{organisation.name}, SHA-256 ",
        at__gte=sign_in.current_time() - timedelta(hours=1),
    ).count()
    if recent >= ORGANISATION_EXPORTS_AN_HOUR:
        return _page(
            request,
            f"No More Than {ORGANISATION_EXPORTS_AN_HOUR} Exports of the Organisation in an Hour",
            status=429,
        )
    return _send(request, build(organisation, by=user))
