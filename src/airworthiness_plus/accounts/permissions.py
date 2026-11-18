"""Check the role matrix on the server for every action (REQ-006, threat TH-008).

Hiding a button is never the control. A view names the action it takes;
a user whose roles do not permit it is refused, and the refusal is
entered in the access log (REQ-009).
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action


class ActionRefusedError(PermissionDenied):
    """The signed-in user's roles do not permit the action."""

    def __init__(self, action: Action) -> None:
        super().__init__(f"Not permitted: {action.value}")
        self.action = action


def address_of(request: HttpRequest) -> str | None:
    """Return the network address the request came from, as the server saw it."""
    address = request.META.get("REMOTE_ADDR")
    return str(address) if address else None


def requires(
    action: Action,
) -> Callable[[Callable[..., HttpResponse]], Callable[..., HttpResponse]]:
    """Let the view run only for a signed-in user whose roles permit ``action``."""

    def decorate(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view)
        def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            user = request.user
            if not isinstance(user, User):
                return redirect_to_login(request.get_full_path())
            if not user.may(action):
                raise ActionRefusedError(action)
            return view(request, *args, **kwargs)

        return wrapped

    return decorate
