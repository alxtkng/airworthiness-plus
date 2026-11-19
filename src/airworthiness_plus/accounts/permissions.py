"""Check the role matrix on the server for every action (REQ-006, threat TH-008).

Hiding a button is never the control. A view names the action it takes;
a user whose roles do not permit it is refused, and the refusal is
entered in the access log (REQ-009).
"""

from collections.abc import Callable
from functools import wraps
from ipaddress import ip_address
from typing import Any

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action


class ActionRefusedError(PermissionDenied):
    """The signed-in user's roles do not permit the action."""

    def __init__(self, action: Action) -> None:
        super().__init__(f"Not permitted: {action.value}")
        self.action = action


def address_of(request: HttpRequest) -> str | None:
    """Return the network address the request came from.

    Behind the reverse proxy the connection comes from the proxy, which
    adds the address it saw to the end of X-Forwarded-For. Only that last
    entry is taken: anything before it was sent by the client and proves
    nothing (OWASP ASVS 5.0, 4.1.3, 15.3.4). Without a proxy the header is
    ignored altogether.
    """
    if settings.BEHIND_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        last = forwarded.rsplit(",", 1)[-1].strip()
        try:
            return str(ip_address(last))
        except ValueError:
            return None
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
            if user.password_must_change:
                return redirect("change_password")
            if not user.may(action):
                raise ActionRefusedError(action)
            return view(request, *args, **kwargs)

        # Read by interface.field_rules, which writes down what each action may set.
        wrapped.action = action  # type: ignore[attr-defined]
        return wrapped

    return decorate


def signed_in(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """Let the view run for any signed-in user, whatever their roles."""

    @wraps(view)
    def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not isinstance(request.user, User):
            return redirect_to_login(request.get_full_path())
        return view(request, *args, **kwargs)

    return wrapped
