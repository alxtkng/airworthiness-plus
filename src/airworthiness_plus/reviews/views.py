"""Pages for the review schedule, the certificates of an aircraft, and review staff.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). Records of another organisation are
not found (REQ-003).
"""

import uuid

from django.db import DatabaseError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews.forms import (
    CertificateForm,
    CopySentForm,
    ExtensionForm,
    InvolvementForm,
    RestorationForm,
    ReviewStaffForm,
)
from airworthiness_plus.reviews.models import Certificate, Extension, ReviewStaff


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def schedule_page(request: HttpRequest) -> HttpResponse:
    """The review schedule: every aircraft by days remaining to expiry (REQ-116)."""
    today = aircraft_services.today()
    lines = services.schedule(_user(request).organisation, today)
    return render(request, "reviews/schedule.html", {"lines": lines})


def _aircraft_page(
    request: HttpRequest, aircraft: Aircraft, form: CertificateForm, message: str = ""
) -> HttpResponse:
    today = aircraft_services.today()
    return render(
        request,
        "reviews/aircraft.html",
        {
            "aircraft": aircraft,
            "line": services.schedule_line(aircraft, today),
            "certificates": [
                (certificate, list(certificate.extensions.select_related("extended_by")))
                for certificate in services.certificates(aircraft)
            ],
            "certificate_form": form,
            "extension_form": ExtensionForm(),
            "copy_form": CopySentForm(),
            "message": message,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def aircraft_review_page(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """The review certificates of one aircraft, with their extensions (REQ-100)."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    return _aircraft_page(request, aircraft, CertificateForm())


@requires(Action.ADD_OR_CHANGE_AIRCRAFT)
@require_POST
def record_certificate(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record a certificate issued elsewhere, as when an aircraft is taken on."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    form = CertificateForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                services.record_certificate(aircraft, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        except DatabaseError:
            form.add_error("reference", "This Certificate Reference Is Already Recorded")
        else:
            return redirect("aircraft_review", aircraft_id=aircraft.id)
    return _aircraft_page(request, aircraft, form)


@requires(Action.EXTEND_AIRWORTHINESS_REVIEW_CERTIFICATE)
@require_POST
def extend(request: HttpRequest, certificate_id: uuid.UUID) -> HttpResponse:
    """Extend a certificate, each condition of ML.A.901(c) confirmed (REQ-104 to REQ-106)."""
    certificate = get_object_or_404(Certificate, pk=certificate_id)
    form = ExtensionForm(request.POST)
    message = ""
    if form.is_valid():
        try:
            services.extend_certificate(
                certificate, extended_by=_user(request), **form.cleaned_data
            )
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("aircraft_review", aircraft_id=certificate.aircraft_id)
    return _aircraft_page(request, certificate.aircraft, CertificateForm(), message)


def _copy_sent(
    request: HttpRequest, item: Certificate | Extension, aircraft: Aircraft
) -> HttpResponse:
    form = CopySentForm(request.POST)
    message = ""
    if form.is_valid():
        try:
            services.record_copy_sent(item, form.cleaned_data["on"])
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("aircraft_review", aircraft_id=aircraft.id)
    return _aircraft_page(request, aircraft, CertificateForm(), message)


@requires(Action.RECORD_COPY_SENT_TO_THE_AUTHORITY)
@require_POST
def certificate_copy_sent(request: HttpRequest, certificate_id: uuid.UUID) -> HttpResponse:
    """Record the copy of a certificate sent to the authority (REQ-111)."""
    certificate = get_object_or_404(Certificate, pk=certificate_id)
    return _copy_sent(request, certificate, certificate.aircraft)


@requires(Action.RECORD_COPY_SENT_TO_THE_AUTHORITY)
@require_POST
def extension_copy_sent(request: HttpRequest, extension_id: uuid.UUID) -> HttpResponse:
    """Record the copy of an extended certificate sent to the authority (REQ-111)."""
    extension = get_object_or_404(Extension, pk=extension_id)
    return _copy_sent(request, extension, extension.certificate.aircraft)


def _staff_page(request: HttpRequest, form: ReviewStaffForm, message: str = "") -> HttpResponse:
    today = aircraft_services.today()
    lines = [
        services.staff_line(staff, today) for staff in ReviewStaff.objects.select_related("user")
    ]
    return render(
        request,
        "reviews/staff.html",
        {
            "lines": lines,
            "form": form,
            "involvement_form": InvolvementForm(),
            "restoration_form": RestorationForm(),
            "message": message,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def staff_page(request: HttpRequest) -> HttpResponse:
    """Airworthiness review staff and whether each has recent experience (REQ-113)."""
    return _staff_page(request, ReviewStaffForm())


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def add_staff(request: HttpRequest) -> HttpResponse:
    """Record a person as airworthiness review staff."""
    form = ReviewStaffForm(request.POST)
    if form.is_valid():
        try:
            services.add_review_staff(**form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("review_staff")
    return _staff_page(request, form)


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def update_involvement(request: HttpRequest, staff_id: uuid.UUID) -> HttpResponse:
    """Change the recorded months of involvement. A lapse already reached is recorded first."""
    staff = get_object_or_404(ReviewStaff, pk=staff_id)
    form = InvolvementForm(request.POST)
    message = ""
    if form.is_valid():
        try:
            services.update_involvement(staff, **form.cleaned_data)
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("review_staff")
    return _staff_page(request, ReviewStaffForm(), message)


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def record_restoration(request: HttpRequest, staff_id: uuid.UUID) -> HttpResponse:
    """Record a review under supervision that restores a lapsed authorisation (REQ-114)."""
    staff = get_object_or_404(ReviewStaff, pk=staff_id)
    form = RestorationForm(request.POST)
    message = ""
    if form.is_valid():
        try:
            services.record_restoration(staff, **form.cleaned_data)
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("review_staff")
    return _staff_page(request, ReviewStaffForm(), message)
