"""A user's own sessions: what is live, and ending one (OWASP ASVS 5.0, 7.5.2).

A session is known to the user by an identifier made from its key by a
one-way hash, so the page never carries the key itself. The list is read
from the sessions the server holds: one that has run out, or that a change
of password has ended, is not on it.
"""

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth import HASH_SESSION_KEY, SESSION_KEY
from django.contrib.sessions.models import Session

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.middleware import (
    LAST_SEEN_KEY,
    SIGNED_IN_AT_KEY,
    OrganisationContextMiddleware,
)
from airworthiness_plus.accounts.models import AccessKind, User

ADDRESS_KEY = "address"
BROWSER_KEY = "browser"


def identifier_of(session_key: str) -> uuid.UUID:
    """Return the identifier a session is shown and ended by."""
    return uuid.UUID(bytes=hashlib.sha256(session_key.encode()).digest()[:16])


@dataclass(frozen=True)
class LiveSession:
    """One session of a user that can still be used."""

    identifier: uuid.UUID
    key: str
    signed_in_at: datetime
    last_seen: datetime
    address: str
    browser: str
    current: bool


def live_sessions(user: User, current_key: str | None) -> list[LiveSession]:
    """Return the user's sessions that can still be used, newest first."""
    expected = user.get_session_auth_hash()
    found = []
    for session in Session.objects.filter(expire_date__gt=sign_in.current_time()):
        data = session.get_decoded()
        if data.get(SESSION_KEY) != str(user.pk):
            continue
        if not hmac.compare_digest(str(data.get(HASH_SESSION_KEY, "")), expected):
            continue  # ended by a change of password or by Sign Out Everywhere Else
        started, seen = data.get(SIGNED_IN_AT_KEY), data.get(LAST_SEEN_KEY)
        if OrganisationContextMiddleware._expired(started, seen):
            continue
        found.append(
            LiveSession(
                identifier=identifier_of(session.session_key),
                key=session.session_key,
                signed_in_at=datetime.fromisoformat(str(started)),
                last_seen=datetime.fromisoformat(str(seen)),
                address=str(data.get(ADDRESS_KEY) or ""),
                browser=str(data.get(BROWSER_KEY) or ""),
                current=session.session_key == current_key,
            )
        )
    return sorted(found, key=lambda one: one.signed_in_at, reverse=True)


def other_session(user: User, identifier: uuid.UUID, current_key: str | None) -> LiveSession | None:
    """Return another live session of the user by its identifier, if there is one."""
    for one in live_sessions(user, current_key):
        if one.identifier == identifier and not one.current:
            return one
    return None


def end_session(user: User, session: LiveSession, address: str | None = None) -> None:
    """End one session of the user. Whoever holds it signs in again."""
    Session.objects.filter(session_key=session.key).delete()
    sign_in.log_account_event(
        AccessKind.SESSIONS_ENDED,
        user,
        detail=f"One Session, by {user.full_name}"[:200],
        address=address,
    )
