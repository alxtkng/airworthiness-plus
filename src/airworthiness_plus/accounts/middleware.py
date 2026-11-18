"""Tie each request to its organisation and user, and end old sessions.

For the length of one request the database is told which organisation and
user the work is for (REQ-003, REQ-130). Both come from the session made
at sign-in, never from the request itself. The whole request is one
transaction, so a response is sent only after its writes are committed
(REQ-138).
"""

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from django.contrib.auth import SESSION_KEY
from django.http import HttpRequest, HttpResponse

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError, address_of
from airworthiness_plus.history.session import working_for

ORGANISATION_KEY = "organisation"
SIGNED_IN_AT_KEY = "signed_in_at"
LAST_SEEN_KEY = "last_seen"

# Ours, not the regulation's (threat TH-002). A session ends 30 minutes
# after its last request, and 12 hours after sign-in whatever happens.
IDLE_MINUTES = 30
ABSOLUTE_HOURS = 12


def _identifier(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _moment(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


class OrganisationContextMiddleware:
    """Set the organisation and user on the database session for each request."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        session = request.session
        organisation = _identifier(session.get(ORGANISATION_KEY))
        user = _identifier(session.get(SESSION_KEY))
        if organisation is None or user is None:
            organisation = user = None
        elif self._expired(session.get(SIGNED_IN_AT_KEY), session.get(LAST_SEEN_KEY)):
            session.flush()
            organisation = user = None
        else:
            session[LAST_SEEN_KEY] = sign_in.current_time().isoformat()
        with working_for(organisation, user):
            return self.get_response(request)

    @staticmethod
    def _expired(signed_in_at: object, last_seen: object) -> bool:
        now = sign_in.current_time()
        started, seen = _moment(signed_in_at), _moment(last_seen)
        if started is None or seen is None:
            return True
        return now - seen > timedelta(minutes=IDLE_MINUTES) or now - started > timedelta(
            hours=ABSOLUTE_HOURS
        )

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Enter a refused action in the access log.

        This runs after the view's own transaction has been rolled back, so
        the entry is kept although the action was not.
        """
        user = request.user
        if isinstance(exception, ActionRefusedError) and isinstance(user, User):
            sign_in.log_action_refused(user, exception.action.value, address_of(request))
