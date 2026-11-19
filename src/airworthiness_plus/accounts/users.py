"""Add users, set their roles, and set and change passwords (REQ-005 to REQ-010).

A user is never deleted. One who leaves is made inactive, and the history
keeps their name. An organisation always has an active Administrator, or
nobody could manage its users.
"""

from collections.abc import Sequence

from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessKind, User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.organisations.models import Organisation


class RefusedError(Exception):
    """What was asked cannot be done. The message says why."""


def _validated(password: str, user: User | None = None) -> None:
    try:
        validate_password(password, user)
    except ValidationError as error:
        raise RefusedError(" ".join(error.messages)) from error


def _roles(roles: Sequence[str]) -> list[str]:
    if not set(roles) <= set(Role.values):
        raise RefusedError("A Role Is One of the Five Roles")
    return [role for role in Role.values if role in roles]


def _another_administrator(user: User) -> bool:
    others = User.objects.filter(is_active=True, roles__contains=[Role.ADMINISTRATOR])
    found: bool = others.exclude(pk=user.pk).exists()
    return found


def add_user(
    *,
    organisation: Organisation,
    username: str,
    full_name: str,
    roles: Sequence[str],
    password: str,
) -> User:
    """Add a user, with a first password that must be changed at first sign-in.

    The first password reaches the person by a route that is not the
    system. A user name is used once across every organisation; the
    message does not say whether a name is taken elsewhere.
    """
    username, full_name = username.strip(), full_name.strip()
    if not username or not full_name:
        raise RefusedError("A User Has a User Name and a Full Name")
    chosen = _roles(roles)
    _validated(password, User(username=username, full_name=full_name))
    try:
        with transaction.atomic():
            return User.objects.create_user(
                organisation=organisation,
                username=username,
                full_name=full_name,
                roles=chosen,
                password=password,
                password_must_change=True,
            )
    except IntegrityError as error:
        raise RefusedError("This User Name Cannot Be Used") from error


def set_roles(user: User, roles: Sequence[str]) -> None:
    """Set the roles a user holds. The change is in the history (REQ-007)."""
    chosen = _roles(roles)
    losing = Role.ADMINISTRATOR in user.roles and Role.ADMINISTRATOR not in chosen
    if losing and user.is_active and not _another_administrator(user):
        raise RefusedError("An Organisation Always Has an Active Administrator")
    user.roles = chosen
    user.save(update_fields=["roles"])


def set_active(user: User, *, active: bool, by: User) -> None:
    """Make a user inactive, or active again. An inactive user's sessions end (REQ-010)."""
    if not active and user.pk == by.pk:
        raise RefusedError("A User Does Not Make Themselves Inactive")
    if not active and Role.ADMINISTRATOR in user.roles and not _another_administrator(user):
        raise RefusedError("An Organisation Always Has an Active Administrator")
    user.is_active = active
    user.save(update_fields=["is_active"])


def reset_password(user: User, *, password: str, by: User, address: str | None = None) -> None:
    """Give a user a new first password, to be changed at their next sign-in.

    Their sessions end, because the password has changed.
    """
    _validated(password, user)
    user.set_password(password)
    user.password_must_change = True
    user.save(update_fields=["password", "password_must_change"])
    sign_in.log_account_event(
        AccessKind.PASSWORD_RESET, user, detail=f"By {by.full_name}"[:200], address=address
    )


def reset_second_factor(user: User, *, by: User, address: str | None = None) -> None:
    """Clear a user's second factor, so that they set one up again at their next sign-in."""
    user.second_factor_secret = ""
    user.second_factor_confirmed = False
    user.save(update_fields=["second_factor_secret", "second_factor_confirmed"])
    sign_in.log_account_event(
        AccessKind.SECOND_FACTOR_RESET, user, detail=f"By {by.full_name}"[:200], address=address
    )


def end_sessions(user: User, *, by: User, address: str | None = None) -> None:
    """End every session of a user. They sign in again, with both factors."""
    user.session_generation += 1
    user.save(update_fields=["session_generation"])
    sign_in.log_account_event(
        AccessKind.SESSIONS_ENDED, user, detail=f"By {by.full_name}"[:200], address=address
    )


def change_password(
    user: User, *, current: str, new: str, again: str, address: str | None = None
) -> None:
    """Change the signed-in user's own password. The current one is asked for again."""
    if not check_password(current, user.password):
        raise RefusedError("The Current Password Is Not Right")
    if new != again:
        raise RefusedError("The Two New Passwords Differ")
    if new == current:
        raise RefusedError("The New Password Is the Same as the Current One")
    _validated(new, user)
    user.set_password(new)
    user.password_must_change = False
    user.save(update_fields=["password", "password_must_change"])
    sign_in.log_account_event(AccessKind.PASSWORD_CHANGED, user, address=address)
