"""Signing in: a password, then a code from an authenticator application.

REQ-008 and REQ-009; threats TH-001 and TH-002. Every attempt is written
to the access log, and the log is what decides whether a user name is
locked and whether a code has been used before, so there is no counter
that could be reset.

While a user name is being checked no organisation is known. For that
moment the database lets the application read the one user with that name
and the access log entries for that name, and nothing else
(``airworthiness_plus.history.sql.CREATE_SIGN_IN``).
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import connection, transaction
from django.db.models import Max
from django.utils import timezone

from airworthiness_plus.accounts import totp
from airworthiness_plus.accounts.models import AccessEntry, AccessKind, User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import SIGNING_IN_SETTING

# Ours, not the regulation's (Decisions.md, Roles and Permissions).
LOCK_AFTER_FAILURES = 5
LOCK_MINUTES = 15


def current_time() -> datetime:
    """Return the present moment. Tests replace this to move time on."""
    return timezone.now()


def _find(username: str, *, active_only: bool = False) -> User | None:
    """Return the user with this name, if the database will show one."""
    users = User.objects.filter(username=username)
    if active_only:
        users = users.filter(is_active=True)
    found: User | None = users.first()
    return found


@contextmanager
def _checking(username: str) -> Iterator[None]:
    """Let the database show the user and access log entries for ``username`` only."""
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config(%s, %s, true)", [SIGNING_IN_SETTING, username])
        yield
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config(%s, '', true)", [SIGNING_IN_SETTING])


def _log(
    kind: AccessKind,
    username: str,
    *,
    user: User | None = None,
    detail: str = "",
    counter: int | None = None,
    address: str | None = None,
) -> None:
    AccessEntry.objects.create(
        organisation_id=user.organisation_id if user else None,
        user=user,
        username=username[:254],
        kind=kind,
        detail=detail,
        code_counter=counter,
        address=address,
    )


def _locked(username: str) -> bool:
    """Return whether too many attempts have failed for ``username`` lately.

    Five failures within 15 minutes, counted since the last time the user
    signed in, lock the name until 15 minutes after the fifth.
    """
    since = current_time() - timedelta(minutes=LOCK_MINUTES)
    recent = AccessEntry.objects.filter(username=username, at__gte=since)
    last_success = recent.filter(kind=AccessKind.SIGNED_IN).aggregate(last=Max("id"))["last"]
    failures = recent.filter(kind=AccessKind.SIGN_IN_FAILED)
    if last_success is not None:
        failures = failures.filter(id__gt=last_success)
    return failures.count() >= LOCK_AFTER_FAILURES


def _refuse_if_locked(username: str, address: str | None) -> bool:
    if not _locked(username):
        return False
    user = _find(username)
    _log(AccessKind.SIGN_IN_REFUSED_WHILE_LOCKED, username, user=user, address=address)
    return True


def check_password_for(username: str, password: str, address: str | None = None) -> User | None:
    """First step. Return the user if the password is right, or None.

    The caller learns nothing about why: an unknown name, a wrong password,
    an inactive user and a locked name all give None. The reason is in the
    access log. This does not sign the user in.
    """
    if not username.strip():
        # No name was given, so there is no name to look up, lock or log against.
        make_password(password)
        return None
    with _checking(username):
        if _refuse_if_locked(username, address):
            return None
        user = _find(username)
        if user is None:
            # Spend the same time as for a real user, so timing does not
            # show which names exist.
            make_password(password)
            _log(AccessKind.SIGN_IN_FAILED, username, detail="Unknown User Name", address=address)
            return None
        if not check_password(password, user.password):
            _log(
                AccessKind.SIGN_IN_FAILED,
                username,
                user=user,
                detail="Wrong Password",
                address=address,
            )
            return None
        if not user.is_active:
            _log(
                AccessKind.SIGN_IN_FAILED,
                username,
                user=user,
                detail="Inactive User",
                address=address,
            )
            return None
        return user


def secret_to_set_up(username: str) -> str | None:
    """Return the secret for a user who has not yet confirmed a second factor.

    Makes one if there is none. Returns None once a second factor is
    confirmed: it is never shown again.
    """
    with _checking(username):
        user = _find(username, active_only=True)
    if user is None or user.second_factor_confirmed:
        return None
    if not user.second_factor_secret:
        with working_for(user.organisation_id, user.id):
            user.second_factor_secret = totp.new_secret()
            user.save(update_fields=["second_factor_secret"])
    return user.second_factor_secret


def _last_counter(user_id: uuid.UUID) -> int | None:
    last: int | None = AccessEntry.objects.filter(user_id=user_id).aggregate(
        last=Max("code_counter")
    )["last"]
    return last


def check_code_for(username: str, code: str, address: str | None = None) -> User | None:
    """Second step. Return the user if the code is right, or None.

    Called only after ``check_password_for`` has returned this user. A
    right code is entered in the access log as Signed In, with its step, so
    it cannot be used again. For a user confirming a second factor for the
    first time, that is entered as well.
    """
    with _checking(username):
        if _refuse_if_locked(username, address):
            return None
        user = _find(username, active_only=True)
        if user is None or not user.second_factor_secret:
            _log(AccessKind.SIGN_IN_FAILED, username, user=user, detail="No Code", address=address)
            return None
        counter = totp.matching_counter(
            user.second_factor_secret, code, current_time(), after=_last_counter(user.id)
        )
        if counter is None:
            _log(
                AccessKind.SIGN_IN_FAILED, username, user=user, detail="Wrong Code", address=address
            )
            return None
        if not user.second_factor_confirmed:
            with working_for(user.organisation_id, user.id):
                user.second_factor_confirmed = True
                user.save(update_fields=["second_factor_confirmed"])
            _log(AccessKind.SECOND_FACTOR_SET_UP, username, user=user, address=address)
        _log(AccessKind.SIGNED_IN, username, user=user, counter=counter, address=address)
        return user


def log_signed_out(user: User, address: str | None = None) -> None:
    """Enter a sign-out in the access log."""
    _log(AccessKind.SIGNED_OUT, user.username, user=user, address=address)


def log_records_exported(user: User, detail: str, address: str | None = None) -> None:
    """Enter an export of records in the access log (threat TH-080)."""
    _log(AccessKind.RECORDS_EXPORTED, user.username, user=user, detail=detail, address=address)


def log_account_event(
    kind: AccessKind, user: User, *, detail: str = "", address: str | None = None
) -> None:
    """Enter a change to a user's password or second factor in the access log."""
    _log(kind, user.username, user=user, detail=detail, address=address)


def log_action_refused(user: User, action: str, address: str | None = None) -> None:
    """Enter a refused action in the access log (REQ-009)."""
    _log(AccessKind.ACTION_REFUSED, user.username, user=user, detail=action, address=address)
