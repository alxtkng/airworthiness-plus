"""Add users, set their roles, and set and change passwords (REQ-005 to REQ-010).

A user is never deleted. One who leaves is made inactive, and the history
keeps their name. An organisation always has an active Administrator, or
nobody could manage its users.
"""

import secrets
from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessKind, User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.organisations.models import Organisation

if TYPE_CHECKING:
    from airworthiness_plus.people.models import Person


class RefusedError(Exception):
    """What was asked cannot be done. The message says why."""


class CodeRefusedError(RefusedError):
    """The code was wrong. The attempt has been entered in the access log and must be kept."""


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


def new_first_password(user: User | None = None) -> str:
    """Make a first password: random, and one the password rules accept."""
    while True:
        password = secrets.token_urlsafe(12)
        try:
            validate_password(password, user)
        except ValidationError:
            continue
        return password


def add_user(
    *,
    organisation: Organisation,
    username: str,
    full_name: str,
    roles: Sequence[str],
    password: str,
    person: "Person | None" = None,
) -> User:
    """Add a user, with a first password that must be changed at first sign-in.

    The first password reaches the person by a route that is not the
    system. A user name is used once across every organisation; the
    message does not say whether a name is taken elsewhere.

    The sign-in is given a new person record, unless ``person`` is chosen:
    a person of the organisation already recorded, who has no sign-in. The
    sign-in then takes that person's name. Nobody is found by name
    (REQ-204; independent review of 24 November 2026, finding 4).
    """
    from airworthiness_plus.people.services import RefusedError as PersonRefusedError

    if person is not None:
        full_name = person.full_name
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
                first_password_set_on=sign_in.today(),
                person=person,
            )
    except PersonRefusedError as error:
        raise RefusedError(str(error)) from error
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


def set_active(user: User, *, active: bool, by: User | None) -> None:
    """Make a user inactive, or active again. An inactive user's sessions end (REQ-010).

    ``by`` is the user doing it, or nobody when it is the owner's work. A
    user whose person is recorded as having left is not made active: the
    day they left is taken off the person's record first (REQ-205;
    independent review of 24 November 2026, finding 5).
    """
    from airworthiness_plus.people.models import Person

    if not active and by is not None and user.pk == by.pk:
        raise RefusedError("A User Does Not Make Themselves Inactive")
    if active and Person.objects.filter(user=user, left_on__isnull=False).exists():
        raise RefusedError("A Person Recorded as Having Left Is Not Made Active")
    if not active and Role.ADMINISTRATOR in user.roles and not _another_administrator(user):
        raise RefusedError("An Organisation Always Has an Active Administrator")
    user.is_active = active
    if not active:
        # The sessions end, not wait: a session made before cannot resume
        # when the user is made active again.
        user.session_generation += 1
    user.save(update_fields=["is_active", "session_generation"])


def reset_password(user: User, *, password: str, by: User, address: str | None = None) -> None:
    """Give a user a new first password, to be changed at their next sign-in.

    Their sessions end, because the password has changed.
    """
    _validated(password, user)
    user.set_password(password)
    user.password_must_change = True
    user.first_password_set_on = sign_in.today()
    user.save(update_fields=["password", "password_must_change", "first_password_set_on"])
    sign_in.log_account_event(
        AccessKind.PASSWORD_RESET, user, detail=f"By {by.full_name}"[:200], address=address
    )


@transaction.atomic
def reset_second_factor(user: User, *, by: User, address: str | None = None) -> None:
    """Clear a user's passkeys and authenticator app and end their sessions."""
    user = User.objects.select_for_update().get(pk=user.pk)
    user.second_factor_secret = ""
    user.second_factor_confirmed = False
    user.passkeys = {}
    # Every session made with the old second factor ends (OWASP ASVS 5.0, 7.4.3).
    user.session_generation += 1
    user.save(
        update_fields=[
            "second_factor_secret",
            "second_factor_confirmed",
            "passkeys",
            "session_generation",
        ]
    )
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
    user: User,
    *,
    current: str,
    new: str,
    again: str,
    code: str = "",
    just_signed_in: bool = False,
    address: str | None = None,
) -> None:
    """Change the signed-in user's own password.

    The current password is asked for again, and a code from the
    authenticator as well unless the user signed in with one in the last
    few minutes (OWASP ASVS 5.0, 7.5.1). The code is checked last, so that
    it is not used up by a change that is refused for another reason.
    """
    if not check_password(current, user.password):
        raise RefusedError("The Current Password Is Not Right")
    if new != again:
        raise RefusedError("The Two New Passwords Differ")
    if new == current:
        raise RefusedError("The New Password Is the Same as the Current One")
    _validated(new, user)
    if not just_signed_in and not sign_in.confirm_code(user, code, address):
        raise CodeRefusedError("The Code From Your Authenticator Application Is Not Right")
    user.set_password(new)
    user.password_must_change = False
    user.first_password_set_on = None
    user.save(update_fields=["password", "password_must_change", "first_password_set_on"])
    sign_in.log_account_event(AccessKind.PASSWORD_CHANGED, user, address=address)
