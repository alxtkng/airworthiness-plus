"""Pages for the people of an organisation (REQ-203 to REQ-206).

Every view names the action it takes, and the role matrix is checked on
the server before it runs (REQ-006). A person of another organisation is
not found, because the database does not show them (REQ-003).
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.accounts.user_views import code_page
from airworthiness_plus.people import services
from airworthiness_plus.people.forms import PersonForm
from airworthiness_plus.people.models import Person


def _user(request: HttpRequest) -> User:
    user = request.user
    assert isinstance(user, User)  # noqa: S101  guaranteed by ``requires``
    return user


@never_cache
@requires(Action.VIEW_RECORDS)
def staff_page(request: HttpRequest) -> HttpResponse:
    """Everyone of the organisation, and those who have left (REQ-205)."""
    staff = services.staff(_user(request).organisation)
    return render(request, "people/staff.html", {"staff": staff, **_shown_to(request)})


@never_cache
@requires(Action.VIEW_RECORDS)
def organisation_chart(request: HttpRequest) -> HttpResponse:
    """Show current reporting lines and management personnel (REQ-295)."""
    roots, managers = services.organisation_chart(_user(request).organisation)
    return render(request, "people/chart.html", {"roots": roots, "managers": managers})


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
