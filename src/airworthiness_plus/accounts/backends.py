"""How Django finds the signed-in user for a request."""

import uuid

from django.http import HttpRequest

from airworthiness_plus.accounts.models import User


class OrganisationBackend:
    """Loads the user of a session, inside that session's organisation.

    The user is read under row-level security, with the organisation the
    session was made for, so a session can never resolve to a user of
    another organisation. A user who has been made inactive is no longer
    found, which ends their sessions (REQ-010).

    Signing in is not done here: it takes two steps
    (``airworthiness_plus.accounts.sign_in``).
    """

    def authenticate(self, request: HttpRequest | None, **credentials: object) -> None:
        """Refuse. A password alone never signs anyone in (REQ-008)."""
        return None

    def get_user(self, user_id: uuid.UUID) -> User | None:
        """Return the active user with this identifier in the current organisation."""
        found: User | None = User.objects.filter(pk=user_id, is_active=True).first()
        return found
