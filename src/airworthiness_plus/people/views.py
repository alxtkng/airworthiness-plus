"""Pages for the people of an organisation (REQ-203 to REQ-206).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A person of another organisation is
not found, because the database does not show them (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.accounts.user_views import code_page
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.people import services
from airworthiness_plus.people.forms import (
    ExperienceEvidenceForm,
    ExperienceWithdrawalForm,
    MaintenanceAuthorisationForm,
    PersonForm,
    RecurrentTrainingForm,
)
from airworthiness_plus.people.models import (
    ExperienceEvidence,
    MaintenanceAuthorisation,
    Person,
    StaffGroup,
)
from airworthiness_rules.maintenance_experience import window_start


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def staff_page(request: HttpRequest) -> HttpResponse:
    """Everyone of the organisation, and those who have left (REQ-205)."""
    staff = services.staff(_user(request).organisation)
    training = services.current_recurrent_training(_user(request).organisation)
    return render(
        request,
        "people/staff.html",
        {
            "staff": staff,
            "staff_rows": [(person, training.get(person.pk, ())) for person in staff.current],
            **_shown_to(request),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def organisation_chart(request: HttpRequest) -> HttpResponse:
    """Show current reporting lines and management personnel (REQ-295)."""
    roots, managers, unresolved = services.organisation_chart(_user(request).organisation)
    return render(
        request,
        "people/chart.html",
        {"roots": roots, "managers": managers, "unresolved": unresolved},
    )


def _shown_to(request: HttpRequest) -> dict[str, bool]:
    """Return what the roles of the user let the Staff pages show them.

    A user name is half of what a sign-in needs, and five wrong passwords
    lock it for 15 minutes: it is shown only to a role that manages users.
    A link or a form for an action the roles do not permit is not shown;
    the check on the server stays the control (REQ-006; independent review
    of 24 November 2026, finding 8).
    """
    user = _user(request)
    return {
        "may_manage_users": user.may(Action.MANAGE_USERS_AND_ROLES),
        "may_change": user.may(Action.ADD_OR_CHANGE_PERSON),
    }


def _initial(person: Person) -> dict[str, object]:
    return {
        "full_name": person.full_name,
        "role": person.role,
        "staff_group": person.staff_group,
        "reports_to": person.reports_to_id,
        "employment": person.employment,
        "licence": person.licence,
        "joined_on": person.joined_on,
        "left_on": person.left_on,
    }


def _person_page(request: HttpRequest, person: Person, form: PersonForm) -> HttpResponse:
    return render(
        request,
        "people/person.html",
        {
            "person": person,
            "reports": person.reports.filter(left_on__isnull=True),
            "training_records": person.recurrent_training.all(),
            "certifying_staff": person.staff_group == StaffGroup.CERTIFYING,
            "form": form,
            **_shown_to(request),
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
def person_page(request: HttpRequest, person_id: uuid.UUID) -> HttpResponse:
    """One person: what is recorded of them, and who reports to them."""
    person = get_object_or_404(Person.objects.select_related("reports_to", "user"), pk=person_id)
    return _person_page(request, person, PersonForm(initial=_initial(person), person=person))


@never_cache
@requires(Action.ADD_OR_CHANGE_PERSON)
@require_http_methods(["GET", "POST"])
def add_person(request: HttpRequest) -> HttpResponse:
    """Add a person who has no sign-in (REQ-203)."""
    form = PersonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            person = services.add_person(
                organisation=_user(request).organisation, **form.cleaned_data
            )
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("person", person_id=person.id)
    return render(request, "people/add_person.html", {"form": form})


@never_cache
@requires(Action.ADD_OR_CHANGE_PERSON)
@require_POST
def change_person(request: HttpRequest, person_id: uuid.UUID) -> HttpResponse:
    """Change what is recorded of a person, or record that they have left."""
    person = get_object_or_404(Person.objects.select_related("reports_to", "user"), pk=person_id)
    form = PersonForm(request.POST, person=person)
    if form.is_valid():
        if person.user_id is not None and form.cleaned_data["full_name"] != person.full_name:
            # The name of a person with a sign-in is the name of the sign-in, which
            # later entries of the history record as who acted. So it is changed as
            # a change on the Users page is: within 5 minutes of signing in, or with
            # a code (OWASP ASVS 5.0, 7.5.1; finding 2 of 24 November 2026).
            asked = code_page(
                request,
                f"Change the Name of {person.full_name}",
                "a Change of Name",
                ("staff", "Back to Staff"),
            )
            if asked is not None:
                return asked
        try:
            services.change_person(person, by=_user(request), **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("person", person_id=person.id)
    person.refresh_from_db()
    return _person_page(request, person, form)


@never_cache
@requires(Action.ADD_OR_CHANGE_PERSON)
@require_http_methods(["GET", "POST"])
def add_maintenance_authorisation(request: HttpRequest, person_id: uuid.UUID) -> HttpResponse:
    """Record an existing maintenance authorisation for a person (REQ-297)."""
    person = get_object_or_404(Person, pk=person_id, staff_group=StaffGroup.CERTIFYING)
    form = MaintenanceAuthorisationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.record_maintenance_authorisation(person, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("review_staff")
    return render(
        request, "people/maintenance_authorisation.html", {"person": person, "form": form}
    )


@never_cache
@requires(Action.ADD_OR_CHANGE_PERSON)
@require_http_methods(["GET", "POST"])
def add_recurrent_training(request: HttpRequest, person_id: uuid.UUID) -> HttpResponse:
    """Record a person's training evidence and stated renewal date (REQ-299)."""
    person = get_object_or_404(Person, pk=person_id)
    form = RecurrentTrainingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            services.record_recurrent_training(person, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("person", person_id=person.id)
    return render(request, "people/recurrent_training.html", {"person": person, "form": form})


def _experience_page(
    request: HttpRequest,
    authorisation: MaintenanceAuthorisation,
    form: ExperienceEvidenceForm,
    *,
    withdrawal_message: str = "",
) -> HttpResponse:
    evidence = list(authorisation.experience_evidence.select_related("withdrawal"))
    today = aircraft_services.today()
    return render(
        request,
        "people/experience_evidence.html",
        {
            "authorisation": authorisation,
            "evidence": evidence,
            "withdrawal_message": withdrawal_message,
            "result": services.assessed_experience(evidence, today),
            "start": window_start(today),
            "assessment_on": today,
            "form": form if _user(request).may(Action.ADD_OR_CHANGE_PERSON) else None,
        },
    )


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def experience_evidence(request: HttpRequest, authorisation_id: uuid.UUID) -> HttpResponse:
    """Read assessed experience for one authorisation (REQ-301)."""
    authorisation = get_object_or_404(
        MaintenanceAuthorisation.objects.select_related("person"), pk=authorisation_id
    )
    return _experience_page(request, authorisation, ExperienceEvidenceForm())


@never_cache
@requires(Action.ADD_OR_CHANGE_PERSON)
@require_POST
def record_experience_evidence(request: HttpRequest, authorisation_id: uuid.UUID) -> HttpResponse:
    """Record an assessment of maintenance experience evidence (REQ-301)."""
    authorisation = get_object_or_404(
        MaintenanceAuthorisation.objects.select_related("person"), pk=authorisation_id
    )
    form = ExperienceEvidenceForm(request.POST)
    if form.is_valid():
        try:
            services.record_experience_evidence(authorisation, **form.cleaned_data)
        except services.RefusedError as error:
            form.add_error(None, str(error))
        else:
            return redirect("maintenance_experience", authorisation_id=authorisation.id)
    return _experience_page(request, authorisation, form)


@never_cache
@requires(Action.ADD_OR_CHANGE_PERSON)
@require_POST
def withdraw_experience_evidence(
    request: HttpRequest, authorisation_id: uuid.UUID, evidence_id: uuid.UUID
) -> HttpResponse:
    """Withdraw experience evidence with a reason (REQ-301)."""
    evidence = get_object_or_404(
        ExperienceEvidence.objects.select_related("authorisation", "authorisation__person"),
        pk=evidence_id,
        authorisation_id=authorisation_id,
    )
    form = ExperienceWithdrawalForm(request.POST)
    message = ""
    if form.is_valid():
        try:
            services.withdraw_experience_evidence(evidence, **form.cleaned_data)
        except services.RefusedError as error:
            message = str(error)
        else:
            return redirect("maintenance_experience", authorisation_id=authorisation_id)
    else:
        message = str(form.errors["reason"][0])
    return _experience_page(
        request, evidence.authorisation, ExperienceEvidenceForm(), withdrawal_message=message
    )
