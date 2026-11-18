"""The Users page and the change of password (REQ-005 to REQ-010)."""

import uuid
from typing import cast

from django.contrib.auth import update_session_auth_hash
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts import users
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import address_of, requires, signed_in
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.accounts.user_forms import (
    AddUserForm,
    ChangePasswordForm,
    ResetPasswordForm,
    RolesForm,
)


def _user(request: HttpRequest) -> User:
    return cast(User, request.user)


def _users(request: HttpRequest, message: str = "", status: int = 200) -> HttpResponse:
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
            "reset_form": ResetPasswordForm(),
            "message": message,
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
    """Add a user."""
    form = AddUserForm(request.POST)
    if not form.is_valid():
        return _users(
            request, "Give a Full Name, a User Name That Is an Email Address and a Password"
        )
    try:
        users.add_user(organisation=_user(request).organisation, **form.cleaned_data)
    except users.RefusedError as error:
        return _users(request, str(error))
    return redirect("users")


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


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def reset_password(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Give a user a new first password."""
    person = get_object_or_404(User, pk=user_id)
    form = ResetPasswordForm(request.POST)
    if not form.is_valid():
        return _users(request, "Give the New First Password")
    try:
        users.reset_password(
            person,
            password=form.cleaned_data["password"],
            by=_user(request),
            address=address_of(request),
        )
    except users.RefusedError as error:
        return _users(request, str(error))
    if person.pk == _user(request).pk:
        update_session_auth_hash(request, person)
    return redirect("users")


@requires(Action.MANAGE_USERS_AND_ROLES)
@require_POST
def reset_second_factor(request: HttpRequest, user_id: uuid.UUID) -> HttpResponse:
    """Clear a user's second factor so that they set one up again."""
    person = get_object_or_404(User, pk=user_id)
    users.reset_second_factor(person, by=_user(request), address=address_of(request))
    return redirect("users")


@never_cache
@signed_in
@require_http_methods(["GET", "POST"])
def change_password(request: HttpRequest) -> HttpResponse:
    """Change the signed-in user's own password."""
    user = _user(request)
    message = ""
    if request.method == "POST":
        form = ChangePasswordForm(request.POST)
        message = "Give the Current Password and the New Password Twice"
        if form.is_valid():
            try:
                users.change_password(user, address=address_of(request), **form.cleaned_data)
            except users.RefusedError as error:
                message = str(error)
            else:
                # Other sessions of this user end; this one continues.
                update_session_auth_hash(request, user)
                return redirect("home")
    return render(
        request,
        "accounts/change_password.html",
        {"form": ChangePasswordForm(), "message": message, "must": user.password_must_change},
    )
