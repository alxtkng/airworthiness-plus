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
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import connection, transaction
from django.db.models import Max
from django.utils import timezone

from airworthiness_plus.accounts import totp
from airworthiness_plus.accounts.models import AccessEntry, AccessKind, User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import SIGNING_IN_SETTING
from airworthiness_rules.dates import uk_today

# Ours, not the regulation's (Decisions.md, Roles and Permissions).
LOCK_AFTER_FAILURES = 5
LOCK_MINUTES = 15
USERNAME_LENGTH = 254  # as the user record and the access log hold it


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
        username=username[:USERNAME_LENGTH],
        kind=kind,
        detail=detail,
        code_counter=counter,
        address=address,
    )


def locks(failures: Sequence[datetime], now: datetime) -> bool:
    """Return whether these failures, oldest first, lock a name at ``now``.

    Five failures within 15 minutes lock the name until 15 minutes after
    the fifth of them. Ours, not the regulation's (threat TH-001).
    """
    window = timedelta(minutes=LOCK_MINUTES)
    first_of_five = LOCK_AFTER_FAILURES - 1
    return any(
        failures[position] >= now - window
        and failures[position] - failures[position - first_of_five] <= window
        for position in range(first_of_five, len(failures))
    )


def _locked(username: str) -> bool:
    """Return whether too many attempts have failed for ``username`` lately.

    Failures are counted since the last time the user signed in. A fifth
    failure that still locks is at most 15 minutes old, and the four before
    it at most 15 minutes older again, so 30 minutes of the log are read.
    """
    now = current_time()
    recent = AccessEntry.objects.filter(
        username=username, at__gte=now - 2 * timedelta(minutes=LOCK_MINUTES)
    )
    last_success = recent.filter(kind=AccessKind.SIGNED_IN).aggregate(last=Max("id"))["last"]
    failures = recent.filter(kind=AccessKind.SIGN_IN_FAILED)
    if last_success is not None:
        failures = failures.filter(id__gt=last_success)
    times = failures.order_by("at", "id").values_list("at", flat=True)
    return locks([moment for moment in times if moment is not None], now)


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
    if "\x00" in username or len(username) > USERNAME_LENGTH:
        # No user can have this name: the database holds neither. It is
        # refused and logged as an unknown name, as it is written, cut to
        # the length of the log and with the NUL made visible.
        shown = username.replace("\x00", "\N{REPLACEMENT CHARACTER}")[:USERNAME_LENGTH]
        make_password(password)
        with _checking(shown):
            _log(AccessKind.SIGN_IN_FAILED, shown, detail="Unknown User Name", address=address)
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
        if first_password_expired(user):
            _log(
                AccessKind.SIGN_IN_FAILED,
                username,
                user=user,
                detail="First Password Expired",
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


# Ours: how long a first password given by an Administrator stays usable.
FIRST_PASSWORD_DAYS = 7


def today() -> date:
    """Return today's date in the United Kingdom, by the clock the tests can move."""
    return uk_today(current_time())


def first_password_expired(user: User) -> bool:
    """Return whether a first password was given too long ago to be used."""
    given = user.first_password_set_on
    return (
        user.password_must_change
        and given is not None
        and today() > given + timedelta(days=FIRST_PASSWORD_DAYS)
    )


def confirm_code(
    user: User, code: str, address: str | None = None, *, at: str = "a Change of Password"
) -> bool:
    """Check a code from a user who is already signed in, and use it up.

    Asked for before a change to how a user signs in (OWASP ASVS 5.0,
    7.5.1); ``at`` names the change in the access log. A right code is logged
    with its step so that it cannot be used again, here or at sign-in. A wrong
    one counts as a failed sign-in does.
    """
    # Guesses are limited here as at sign-in: five wrong codes lock the name.
    if _locked(user.username):
        _log(AccessKind.SIGN_IN_REFUSED_WHILE_LOCKED, user.username, user=user, address=address)
        return False
    counter = None
    if user.second_factor_secret:
        counter = totp.matching_counter(
            user.second_factor_secret, code, current_time(), after=_last_counter(user.id)
        )
    if counter is None:
        _log(
            AccessKind.SIGN_IN_FAILED,
            user.username,
            user=user,
            detail=f"Wrong Code at {at}",
            address=address,
        )
        return False
    _log(AccessKind.CODE_ACCEPTED, user.username, user=user, counter=counter, address=address)
    return True


def log_account_event(
    kind: AccessKind, user: User, *, detail: str = "", address: str | None = None
) -> None:
    """Enter a change to a user's password or second factor in the access log."""
    _log(kind, user.username, user=user, detail=detail, address=address)


def log_action_refused(user: User, action: str, address: str | None = None) -> None:
    """Enter a refused action in the access log (REQ-009)."""
    _log(AccessKind.ACTION_REFUSED, user.username, user=user, detail=action, address=address)
