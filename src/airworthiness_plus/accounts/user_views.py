"""The Users page and the change of password (REQ-005 to REQ-010)."""

import uuid
from datetime import datetime, timedelta
from typing import cast

from django.contrib.auth import update_session_auth_hash
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts import sign_in, users
from airworthiness_plus.accounts.middleware import SIGNED_IN_AT_KEY
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import address_of, requires, signed_in
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.accounts.user_forms import (
    AddUserForm,
    ChangePasswordForm,
    RolesForm,
)


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


# Ours: a session this new has just given a password and a code.
JUST_SIGNED_IN_MINUTES = 5


def _just_signed_in(request: HttpRequest) -> bool:
    try:
        started = datetime.fromisoformat(str(request.session.get(SIGNED_IN_AT_KEY)))
    except ValueError:
        return False
    return sign_in.current_time() - started <= timedelta(minutes=JUST_SIGNED_IN_MINUTES)


def _users(
    request: HttpRequest,
    message: str = "",
    status: int = 200,
    given: tuple[User, str] | None = None,
) -> HttpResponse:
    people = [
        (person, RolesForm(initial={"roles": person.roles}, prefix=str(person.pk)))
        for person in User.objects.order_by("full_name")
    ]
    return render(
        request,
        "accounts/users.html",
        {
            "people": people,
            "add_form": AddUserForm(),
            "message": message,
            # A first password is shown once, on the page that follows its making.
            "given": given,
            "given_until": (
                sign_in.today() + timedelta(days=sign_in.FIRST_PASSWORD_DAYS) if given else None
            ),
        },
        status=status,
    )


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
def users_page(request: HttpRequest) -> HttpResponse:
    """Every user of the organisation, with their roles and whether they can sign in."""
    return _users(request)


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def add_user(request: HttpRequest) -> HttpResponse:
    """Add a user. The system makes their first password and shows it once."""
    form = AddUserForm(request.POST)
    if not form.is_valid():
        return _users(request, "Give a Full Name and a User Name That Is an Email Address")
    password = users.new_first_password()
    try:
        person = users.add_user(
            organisation=_user(request).organisation, password=password, **form.cleaned_data
        )
    except users.RefusedError as error:
        return _users(request, str(error))
    return _users(request, given=(person, password))


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def set_roles(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Set the roles a user holds."""
    person = get_object_or_404(User, pk=user_id)
    form = RolesForm(request.POST, prefix=str(person.pk))
    if not form.is_valid():
        return _users(request, "A Role Is One of the Five Roles")
    try:
        users.set_roles(person, form.cleaned_data["roles"])
    except users.RefusedError as error:
        return _users(request, str(error))
    return redirect("users")


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def set_active(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Make a user inactive, or active again."""
    person = get_object_or_404(User, pk=user_id)
    try:
        users.set_active(person, active=request.POST.get("active") == "yes", by=_user(request))
    except users.RefusedError as error:
        return _users(request, str(error))
    return redirect("users")


def _code_page(request: HttpRequest, what: str, at: str) -> HttpResponse | None:
    """Ask the Administrator for a code before a change to how a user signs in.

    Nothing is asked within 5 minutes of sign-in. After that the change is
    made only with a code from the Administrator's own authenticator
    application (OWASP ASVS 5.0, 7.5.1; threat TH-002). Returns the page that
    asks, or nothing when the change may go ahead.
    """
    if _just_signed_in(request):
        return None
    code = request.POST.get("code", "")
    if code and sign_in.confirm_code(_user(request), code, address_of(request), at=at):
        return None
    message = "The Code From Your Authenticator Application Is Not Right" if code else ""
    return render(
        request,
        "accounts/confirm_code.html",
        {"what": what, "action": request.path, "message": message},
    )


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def reset_password(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Give a user a new first password, made by the system and shown once."""
    person = get_object_or_404(User, pk=user_id)
    asked = _code_page(
        request, f"Give {person.full_name} a New First Password", "a New First Password"
    )
    if asked is not None:
        return asked
    password = users.new_first_password(person)
    users.reset_password(person, password=password, by=_user(request), address=address_of(request))
    if person.pk == _user(request).pk:
        update_session_auth_hash(request, person)
    return _users(request, given=(person, password))


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def reset_second_factor(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Clear a user's second factor so that they set one up again."""
    person = get_object_or_404(User, pk=user_id)
    asked = _code_page(
        request, f"Reset Second Factor of {person.full_name}", "a Reset of a Second Factor"
    )
    if asked is not None:
        return asked
    users.reset_second_factor(person, by=_user(request), address=address_of(request))
    return redirect("users")


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def end_sessions(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """End every session of a user, for example when a device is lost."""
    person = get_object_or_404(User, pk=user_id)
    users.end_sessions(person, by=_user(request), address=address_of(request))
    if person.pk == _user(request).pk:
        update_session_auth_hash(request, person)
    return redirect("users")


@signed_in
@require_POST
def end_other_sessions(request: HttpRequest) -> HttpResponse:
    """End every other session of the signed-in user. This one continues."""
    user = _user(request)
    users.end_sessions(user, by=user, address=address_of(request))
    update_session_auth_hash(request, user)
    return redirect("change_password")


@never_cache
@signed_in
@require_http_methods(["GET", "POST"])
def change_password(request: HttpRequest) -> HttpResponse:
    """Change the signed-in user's own password.

    A code is asked for as well as the current password, unless the user
    signed in within the last 5 minutes (OWASP ASVS 5.0, 7.5.1).
    """
    user = _user(request)
    fresh = _just_signed_in(request)
    message = ""
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        message = "Give the Current Password and the New Password Twice"
        if form.is_valid():
            try:
                users.change_password(
                    user, just_signed_in=fresh, address=address_of(request), **form.cleaned_data
                )
            except users.RefusedError as error:
                message = str(error)
            else:
                # Other sessions of this user end; this one continues.
                update_session_auth_hash(request, user)
                return redirect("home")
    return render(
        request,
        "accounts/change_password.html",
        {
            "form": ChangePasswordForm(),
            "message": message,
            "must": user.password_must_change,
            "code_needed": not fresh,
        },
    )
