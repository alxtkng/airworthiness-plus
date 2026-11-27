"""Pages for the review schedule, the certificates of an aircraft, and review staff.

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). Records of another organisation are
not found (REQ-003).
"""

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.db import DatabaseError, transaction
from django.db.models import Count, F, Max, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError, address_of, requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.organisations import approvals
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person, StaffGroup
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews.forms import (
    CertificateForm,
    ClosureForm,
    CopySentForm,
    DetailsForm,
    ExtensionForm,
    InvolvementForm,
    ItemForm,
    RestorationForm,
    ReviewAuthorisationForm,
    ReviewStaffForm,
    ReviewStartForm,
    VoidForm,
)
from airworthiness_plus.reviews.models import (
    Certificate,
    Extension,
    Result,
    Review,
    ReviewItem,
    ReviewStaff,
)


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


def _refusal(request: HttpRequest) -> str:
    """Return why the organisation is not offered airworthiness review, or nothing."""
    return approvals.review_refusal(_user(request).organisation)


def with_the_privilege(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Let an action of airworthiness review run only for an organisation it is open to.

    CAO.A.095(c): a Part-CAO whose approval includes airworthiness review.
    Any other organisation is refused with the reason, whatever the roles
    of the user, and the refusal is entered in the access log (REQ-009;
    independent review of 24 November 2026, finding 10). Placed under
    ``requires``, so the role matrix is checked first.
    """

    @wraps(view)
    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        reason = _refusal(request)
        if reason:
            sign_in.log_action_refused(
                _user(request), approvals.REVIEW_REFUSED, address_of(request)
            )
            return render(request, "reviews/not_open.html", {"refusal": reason}, status=403)
        return view(request, *args, **kwargs)

    return wrapped


@never_cache
@requires(Action.VIEW_RECORDS)
def schedule_page(request: HttpRequest) -> HttpResponse:
    """The review schedule: every aircraft by days remaining to expiry (REQ-116)."""
    today = aircraft_services.today()
    lines = services.schedule(_user(request).organisation, today)
    return render(request, "reviews/schedule.html", {"lines": lines, "refusal": _refusal(request)})


def _aircraft_page(
    request: HttpRequest, aircraft: Aircraft, form: CertificateForm, message: str = ""
) -> HttpResponse:
    today = aircraft_services.today()
    line = services.schedule_line(aircraft, today)
    user = _user(request)
    start_staff = (
        ReviewStaff.objects.filter(user=user, left_on__isnull=True).first()
        if user.may(Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
        else None
    )
    return render(
        request,
        "reviews/aircraft.html",
        {
            "aircraft": aircraft,
            "line": line,
            "working": services.working(line, today),
            "certificates": [
                (certificate, list(certificate.extensions.all()))
                for certificate in services.certificates(aircraft)
            ],
            "reviews": Review.objects.filter(aircraft=aircraft).select_related("staff__user"),
            "certificate_form": form,
            "start_scope": start_staff.authorisation_scope if start_staff else "",
            "start_form": ReviewStartForm(),
            "extension_form": ExtensionForm(),
            "copy_form": CopySentForm(),
            "message": message,
            "refusal": _refusal(request),
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
@with_the_privilege
def record_certificate(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Record a certificate issued elsewhere, or by the organisation before these records."""
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
@with_the_privilege
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
@with_the_privilege
def certificate_copy_sent(request: HttpRequest, certificate_id: uuid.UUID) -> HttpResponse:
    """Record the copy of a certificate sent to the authority (REQ-111)."""
    certificate = get_object_or_404(Certificate, pk=certificate_id)
    return _copy_sent(request, certificate, certificate.aircraft)


@requires(Action.RECORD_COPY_SENT_TO_THE_AUTHORITY)
@require_POST
@with_the_privilege
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
            "lines": [
                (
                    line,
                    InvolvementForm(auto_id=f"involvement-{line.staff.id}-%s"),
                    RestorationForm(auto_id=f"restoration-{line.staff.id}-%s"),
                )
                for line in lines
            ],
            "maintenance_authorisations": MaintenanceAuthorisation.objects.select_related("person"),
            "may_change_person": _user(request).may(Action.ADD_OR_CHANGE_PERSON),
            "may_manage_review_staff": _user(request).may(Action.MANAGE_USERS_AND_ROLES),
            "certifying_people": Person.objects.filter(
                staff_group=StaffGroup.CERTIFYING, left_on__isnull=True
            ),
            "form": form,
            "message": message,
            "refusal": _refusal(request),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def staff_page(request: HttpRequest) -> HttpResponse:
    """Airworthiness review staff and whether each has recent experience (REQ-113)."""
    return _staff_page(request, ReviewStaffForm())


@never_cache
@requires(Action.VIEW_RECORDS)
def recency_page(request: HttpRequest) -> HttpResponse:
    """Show airworthiness review and maintenance experience separately (REQ-296)."""
    today = aircraft_services.today()
    review_staff = ReviewStaff.objects.filter(left_on__isnull=True).select_related(
        "user", "organisation"
    )
    certifying_people = (
        Person.objects.filter(
            Q(staff_group=StaffGroup.CERTIFYING) | Q(maintenance_authorisations__isnull=False),
            left_on__isnull=True,
        )
        .distinct()
        .prefetch_related("maintenance_authorisations")
    )
    within_employment = Q(performed_by__joined_on__isnull=True) | Q(
        dated__gte=F("performed_by__joined_on")
    )
    dates = {
        row["performed_by_id"]: (row["last_work"], row["outside_employment"])
        for row in WorkDone.objects.filter(performed_by__in=certifying_people, dated__lte=today)
        .order_by()
        .values("performed_by_id")
        .annotate(
            last_work=Max("dated", filter=within_employment),
            outside_employment=Count("pk", filter=~within_employment),
        )
    }
    authorisations = (
        MaintenanceAuthorisation.objects.filter(person__in=certifying_people)
        .select_related("person", "withdrawal")
        .prefetch_related("experience_evidence__withdrawal")
    )
    assessments = []
    for authorisation in authorisations:
        evidence = list(authorisation.experience_evidence.all())
        result = people_services.assessed_experience(evidence, today) if evidence else None
        assessments.append((authorisation, authorisation.term_on(today), result))
    return render(
        request,
        "reviews/recency.html",
        {
            "review_lines": [services.staff_line(staff, today) for staff in review_staff],
            "assessments": assessments,
            "certifying_staff": [
                (person, *dates.get(person.pk, (None, 0))) for person in certifying_people
            ],
        },
    )


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
@with_the_privilege
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
@with_the_privilege
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
@with_the_privilege
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


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_http_methods(["GET", "POST"])
@with_the_privilege
def record_review_authorisation(request: HttpRequest, staff_id: uuid.UUID) -> HttpResponse:
    """Record the terms of a review authorisation (REQ-300)."""
    staff = get_object_or_404(ReviewStaff.objects.select_related("user"), pk=staff_id)
    form = ReviewAuthorisationForm(
        request.POST or None,
        initial={
            "authorisation_scope": staff.authorisation_scope,
            "authorisation_valid_to": staff.authorisation_valid_to,
            "version": services.review_authorisation_version(staff),
        },
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.record_review_authorisation(staff, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("review_staff")
    return render(request, "reviews/review_authorisation.html", {"staff": staff, "form": form})


# The review itself


def _own_review(request: HttpRequest, review: Review, action: Action) -> None:
    """Refuse anyone but the member of review staff carrying out this review.

    ML.A.903(e)(1) and (g): the review is carried out and its certificate
    issued by the authorised review staff, and is not passed to another.
    The refusal is entered in the access log.
    """
    if review.staff.user_id != _user(request).id:
        raise ActionRefusedError(action)


def _review_page(request: HttpRequest, review: Review, message: str = "") -> HttpResponse:
    today = aircraft_services.today()
    return render(
        request,
        "reviews/review.html",
        {
            "review": review,
            "aircraft": review.aircraft,
            "items": [
                (
                    item,
                    ItemForm(auto_id=f"review-{item.id}-%s", may_not_apply=item.may_not_apply),
                    ClosureForm(auto_id=f"closure-{item.id}-%s"),
                )
                for item in review.items.all()
            ],
            "outstanding": services.outstanding(review, today) if not review.certificate else [],
            "details_form": DetailsForm(
                initial={
                    "assisted_by": review.assisted_by,
                    "airframe_hours": review.airframe_hours,
                    "programme_discrepancy": review.programme_discrepancy,
                }
            ),
            "message": message,
            "refusal": _refusal(request),
        },
    )


@requires(Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
@require_POST
@with_the_privilege
def start_review(request: HttpRequest, aircraft_id: uuid.UUID) -> HttpResponse:
    """Start a review of an aircraft, as the signed-in member of review staff."""
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    staff = ReviewStaff.objects.filter(user=_user(request), left_on__isnull=True).first()
    if staff is None:
        raise ActionRefusedError(Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
    form = ReviewStartForm(request.POST)
    if form.is_valid():
        try:
            review = services.start_review(aircraft, staff=staff, **form.cleaned_data)
        except services.RefusedError as error:
            return _aircraft_page(request, aircraft, CertificateForm(), str(error))
        return redirect("review", review_id=review.id)
    return _aircraft_page(request, aircraft, CertificateForm(), "Confirm the Review Scope")


@never_cache
@requires(Action.VIEW_RECORDS)
def review_page(request: HttpRequest, review_id: uuid.UUID) -> HttpResponse:
    """One review: every point of ML.A.903, its result, evidence and findings (REQ-107, REQ-108)."""
    return _review_page(request, get_object_or_404(Review, pk=review_id))


@requires(Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
@require_POST
@with_the_privilege
def record_item(request: HttpRequest, item_id: uuid.UUID) -> HttpResponse:
    """Record the result of one point."""
    item = get_object_or_404(ReviewItem, pk=item_id)
    _own_review(request, item.review, Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
    form = ItemForm(request.POST)
    message = "Give a Result and the Evidence Sampled"
    if form.is_valid():
        data = form.cleaned_data
        try:
            services.record_item(
                item,
                result=Result(data["result"]),
                evidence=data["evidence"],
                finding=data["finding"],
            )
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("review", review_id=item.review_id)
    return _review_page(request, item.review, message)


@requires(Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
@require_POST
@with_the_privilege
def close_finding(request: HttpRequest, item_id: uuid.UUID) -> HttpResponse:
    """Record how a finding was closed."""
    item = get_object_or_404(ReviewItem, pk=item_id)
    _own_review(request, item.review, Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
    form = ClosureForm(request.POST)
    message = "Say How the Finding Was Closed"
    if form.is_valid():
        try:
            services.close_finding(item, closure=form.cleaned_data["closure"])
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("review", review_id=item.review_id)
    return _review_page(request, item.review, message)


@requires(Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
@require_POST
@with_the_privilege
def review_details(request: HttpRequest, review_id: uuid.UUID) -> HttpResponse:
    """Record who assisted at the survey, the airframe hours and the state of the programme."""
    review = get_object_or_404(Review, pk=review_id)
    _own_review(request, review, Action.CARRY_OUT_AIRWORTHINESS_REVIEW)
    form = DetailsForm(request.POST)
    message = ""
    if form.is_valid():
        try:
            services.record_details(review, **form.cleaned_data)
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("review", review_id=review.id)
    return _review_page(request, review, message)


@requires(Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE)
@require_POST
@with_the_privilege
def issue(request: HttpRequest, review_id: uuid.UUID) -> HttpResponse:
    """Issue the certificate for a completed review (REQ-109, REQ-110).

    Whether the person may issue is decided here, on the server, at the
    moment of issue (threat TH-009). A lapse found now is recorded even
    though the issue is refused.
    """
    review = get_object_or_404(Review, pk=review_id)
    _own_review(request, review, Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE)
    services.note_lapse(review.staff, aircraft_services.today())
    try:
        certificate = services.issue_from_review(review)
    except services.RefusedError as error:
        return _review_page(request, review, str(error))
    return redirect("certificate", certificate_id=certificate.id)


@never_cache
@requires(Action.VIEW_RECORDS)
def certificate_page(request: HttpRequest, certificate_id: uuid.UUID) -> HttpResponse:
    """One certificate, with the entries of CAA Form 15c (REQ-110)."""
    certificate = get_object_or_404(Certificate, pk=certificate_id)
    # What the certificate kept when it was recorded, never the organisation
    # or the person as they stand today (finding 1 of 24 November 2026).
    issued_by = ", ".join(
        part
        for part in (
            certificate.organisation_name,
            certificate.organisation_address,
            certificate.organisation_approval_reference,
        )
        if part
    )
    return render(
        request,
        "reviews/certificate.html",
        {
            "certificate": certificate,
            "issued_by": issued_by,
            "aircraft": certificate.aircraft,
            "extensions": list(certificate.extensions.all()),
            "review": Review.objects.filter(certificate=certificate).first(),
            "void_form": VoidForm(),
            "refusal": _refusal(request),
        },
    )


@requires(Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE)
@require_POST
@with_the_privilege
def void(request: HttpRequest, certificate_id: uuid.UUID) -> HttpResponse:
    """Void a certificate. It stays in the record and its serial is not used again."""
    certificate = get_object_or_404(Certificate, pk=certificate_id)
    form = VoidForm(request.POST)
    if form.is_valid():
        try:
            services.void_certificate(certificate, form.cleaned_data["reason"])
        except services.RefusedError:
            pass
    return redirect("certificate", certificate_id=certificate.id)
