"""The Users page and the change of password (REQ-005 to REQ-010)."""

import uuid
from datetime import timedelta
from typing import cast

from django.contrib.auth import HASH_SESSION_KEY, update_session_auth_hash
from django.contrib.auth.hashers import check_password
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts import sessions, sign_in, users
from airworthiness_plus.accounts.middleware import VERIFIED_AT_KEY, recently_verified
from airworthiness_plus.accounts.models import AccessEntry, AccessKind, User
from airworthiness_plus.accounts.permissions import address_of, requires, signed_in
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.accounts.user_forms import (
    AddUserForm,
    ChangePasswordForm,
    RolesForm,
)


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


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


# Ours: how many entries of the access log one page shows.
ACCESS_LOG_PAGE = 100


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
def access_log(request: HttpRequest) -> HttpResponse:
    """The access log of the organisation, newest first (REQ-009).

    Every sign-in, failed sign-in, sign-out, refused action, export and
    change to how someone signs in. The database shows an organisation its
    own entries and no others.
    """
    entries = AccessEntry.objects.select_related("user").order_by("-id")
    before = request.GET.get("before", "")
    # ASCII digits only, and no more than an identifier can hold.
    if before.isascii() and before.isdigit() and len(before) <= 18:
        entries = entries.filter(id__lt=int(before))
    shown = list(entries[: ACCESS_LOG_PAGE + 1])
    more = len(shown) > ACCESS_LOG_PAGE
    shown = shown[:ACCESS_LOG_PAGE]
    return render(
        request,
        "accounts/access_log.html",
        {"entries": shown, "older": shown[-1].id if more else None},
    )


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def add_user(request: HttpRequest) -> HttpResponse:
    """Add a user. The system makes their first password and shows it once."""
    form = AddUserForm(request.POST)
    if not form.is_valid():
        return _users(request, "Give a Full Name and a User Name That Is an Email Address")
    asked = code_page(request, "Add a User", "Adding a User", full=True)
    if asked is not None:
        return asked
    password = users.new_first_password()
    try:
        person = users.add_user(
            organisation=_user(request).organisation, password=password, **form.cleaned_data
        )
    except users.RefusedError as error:
        return _users(request, str(error))
    return _users(request, given=(person, password))


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def set_roles(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Set the roles a user holds."""
    person = get_object_or_404(User, pk=user_id)
    form = RolesForm(request.POST, prefix=str(person.pk))
    if not form.is_valid():
        return _users(request, "A Role Is One of the Five Roles")
    asked = code_page(request, f"Save Roles of {person.full_name}", "a Change of Roles", full=True)
    if asked is not None:
        return asked
    try:
        users.set_roles(person, form.cleaned_data["roles"])
    except users.RefusedError as error:
        return _users(request, str(error))
    return redirect("users")


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def set_active(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Make a user inactive, or active again."""
    person = get_object_or_404(User, pk=user_id)
    active = request.POST.get("active") == "yes"
    asked = code_page(
        request,
        f"Make {person.full_name} {'Active' if active else 'Inactive'}",
        "Making a User Active or Inactive",
        full=True,
    )
    if asked is not None:
        return asked
    try:
        users.set_active(person, active=active, by=_user(request))
    except users.RefusedError as error:
        return _users(request, str(error))
    return redirect("users")


def code_page(
    request: HttpRequest,
    what: str,
    at: str,
    back: tuple[str, str] = ("users", "Back to Users"),
    *,
    full: bool = False,
) -> HttpResponse | None:
    """Use recent verification or ask for a passkey or the authenticator fallback."""
    if recently_verified(request.session):
        return None
    code = request.POST.get("code", "")
    if code:
        user = User.objects.select_for_update().get(pk=_user(request).pk)
        address = address_of(request)
        current_session = (
            user.is_active and request.session.get(HASH_SESSION_KEY) == user.get_session_auth_hash()
        )
        password = request.POST.get("verification_password", "")
        if current_session and full and sign_in._refuse_if_locked(user.username, address):
            current_session = False
        if current_session and full and not check_password(password, user.password):
            sign_in.log_account_event(
                AccessKind.SIGN_IN_FAILED, user, detail=f"Wrong Password at {at}", address=address
            )
        elif current_session and sign_in.confirm_code(user, code, address, at=at):
            if full:
                request.session.cycle_key()
                request.session[VERIFIED_AT_KEY] = sign_in.current_time().isoformat()
            return None
    if full:
        refused = "Password or Authenticator Code Is Not Right"
    else:
        refused = "The Code From Your Authenticator Application Is Not Right"
    message = refused if code else ""
    return render(
        request,
        "accounts/confirm_code.html",
        {
            "what": what,
            "action": request.path,
            "message": message,
            "full_verification": full,
            "passkey_available": bool(_user(request).passkeys),
            "carried": [
                (name, value)
                for name in request.POST
                if name not in ("csrfmiddlewaretoken", "code", "verification_password")
                for value in request.POST.getlist(name)
            ],
            "back": back[0],
            "back_label": back[1],
        },
    )


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def reset_password(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Give a user a new first password, made by the system and shown once."""
    person = get_object_or_404(User, pk=user_id)
    asked = code_page(
        request, f"Give {person.full_name} a New First Password", "a New First Password", full=True
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
    asked = code_page(
        request,
        f"Reset Second Factor of {person.full_name}",
        "a Reset of a Second Factor",
        full=True,
    )
    if asked is not None:
        return asked
    users.reset_second_factor(person, by=_user(request), address=address_of(request))
    return redirect("users")


@never_cache
@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def end_sessions(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """End every session of a user, for example when a device is lost."""
    person = get_object_or_404(User, pk=user_id)
    asked = code_page(request, f"End Sessions of {person.full_name}", "Ending a User's Sessions")
    if asked is not None:
        return asked
    users.end_sessions(person, by=_user(request), address=address_of(request))
    if person.pk == _user(request).pk:
        update_session_auth_hash(request, person)
    return redirect("users")


# Where the page that asks for a code goes back to, for the user's own sessions.
OWN = ("change_password", "Back to Change Password")


@never_cache
@signed_in
@require_POST
def end_other_sessions(request: HttpRequest) -> HttpResponse:
    """End every other session of the signed-in user. This one continues."""
    user = _user(request)
    asked = code_page(request, "Sign Out Everywhere Else", "Ending Other Sessions", OWN)
    if asked is not None:
        return asked
    users.end_sessions(user, by=user, address=address_of(request))
    update_session_auth_hash(request, user)
    return redirect("change_password")


@never_cache
@signed_in
@require_POST
def end_session(request: HttpRequest, session_id: uuid.UUID) -> HttpResponse:
    """End one other session of the signed-in user."""
    user = _user(request)
    found = sessions.other_session(user, session_id, request.session.session_key)
    if found is None:
        raise Http404
    asked = code_page(request, "End a Session", "Ending a Session", OWN)
    if asked is not None:
        return asked
    sessions.end_session(user, found, address_of(request))
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
    fresh = recently_verified(request.session)
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
                return redirect("dashboard")
    return render(
        request,
        "accounts/change_password.html",
        {
            "form": ChangePasswordForm(),
            "message": message,
            "must": user.password_must_change,
            "code_needed": not fresh,
            "passkey_available": bool(user.passkeys),
            "sessions": sessions.live_sessions(user, request.session.session_key),
        },
    )
