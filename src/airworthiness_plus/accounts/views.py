"""Sign in, set up a second factor, sign out, and the first page after sign-in."""

from datetime import datetime, timedelta

from django.contrib.auth import login, logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts import sign_in, totp
from airworthiness_plus.accounts.middleware import (
    LAST_SEEN_KEY,
    ORGANISATION_KEY,
    SIGNED_IN_AT_KEY,
    VERIFIED_AT_KEY,
)
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import address_of
from airworthiness_plus.accounts.sessions import ADDRESS_KEY, BROWSER_KEY

BACKEND = "airworthiness_plus.accounts.backends.OrganisationBackend"
PENDING_KEY = "password_accepted_for"
PENDING_AT_KEY = "password_accepted_at"
PENDING_HASH_KEY = "password_accepted_hash"

# The code must follow the password within this time. Ours.
PENDING_MINUTES = 5


def _pending(request: HttpRequest) -> tuple[str, str] | None:
    """Return the user name whose password this session has just had accepted."""
    username = request.session.get(PENDING_KEY)
    accepted = request.session.get(PENDING_AT_KEY)
    proof = request.session.get(PENDING_HASH_KEY)
    if not isinstance(username, str) or not isinstance(accepted, str) or not isinstance(proof, str):
        return None
    try:
        accepted_at = datetime.fromisoformat(accepted)
    except ValueError:
        return None
    if sign_in.current_time() - accepted_at > timedelta(minutes=PENDING_MINUTES):
        return None
    return username, proof


def _complete(request: HttpRequest, user: User) -> HttpResponse:
    """Sign the user in. Django gives the session a new key here (threat TH-002)."""
    login(request, user, backend=BACKEND)
    now = sign_in.current_time().isoformat()
    request.session[ORGANISATION_KEY] = str(user.organisation_id)
    request.session[SIGNED_IN_AT_KEY] = now
    request.session[VERIFIED_AT_KEY] = now
    request.session[LAST_SEEN_KEY] = now
    # Shown to the user in the list of their own sessions (OWASP ASVS 5.0, 7.5.2).
    request.session[ADDRESS_KEY] = address_of(request) or ""
    request.session[BROWSER_KEY] = request.headers.get("User-Agent", "")[:200]
    request.session.pop(PENDING_KEY, None)
    request.session.pop(PENDING_AT_KEY, None)
    request.session.pop(PENDING_HASH_KEY, None)
    return redirect("dashboard")


@never_cache
@require_http_methods(["GET", "POST"])
def sign_in_page(request: HttpRequest) -> HttpResponse:
    """Show passkey sign-in and accept a password for the authenticator fallback."""
    if request.user.is_authenticated and request.method == "GET":
        return redirect("dashboard")
    failed = False
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = sign_in.check_password_for(username, password, address_of(request))
        if user is not None:
            request.session[PENDING_KEY] = user.username
            request.session[PENDING_AT_KEY] = sign_in.current_time().isoformat()
            request.session[PENDING_HASH_KEY] = user.get_session_auth_hash()
            return redirect("code" if user.second_factor_confirmed else "set_up")
        failed = True
    return render(request, "accounts/sign_in.html", {"failed": failed})


@never_cache
@require_http_methods(["GET", "POST"])
def code_page(request: HttpRequest) -> HttpResponse:
    """Second step: the code from the authenticator application."""
    pending = _pending(request)
    if pending is None:
        return redirect("sign_in")
    username, proof = pending
    failed = False
    if request.method == "POST":
        user = sign_in.check_code_for(
            username, request.POST.get("code", ""), address_of(request), proof=proof
        )
        if user is not None:
            return _complete(request, user)
        failed = True
    return render(request, "accounts/code.html", {"failed": failed})


@never_cache
@require_http_methods(["GET", "POST"])
def set_up_page(request: HttpRequest) -> HttpResponse:
    """First sign-in: add the account to an authenticator application and confirm a code."""
    pending = _pending(request)
    if pending is None:
        return redirect("sign_in")
    username, proof = pending
    secret = sign_in.secret_to_set_up(username, proof=proof)
    if secret is None:
        return redirect("code")
    failed = False
    if request.method == "POST":
        user = sign_in.check_code_for(
            username, request.POST.get("code", ""), address_of(request), proof=proof
        )
        if user is not None:
            return _complete(request, user)
        failed = True
    grouped = " ".join(secret[index : index + 4] for index in range(0, len(secret), 4))
    return render(
        request,
        "accounts/set_up.html",
        {"failed": failed, "secret": grouped, "address": totp.set_up_address(secret, username)},
    )


@require_POST
def sign_out(request: HttpRequest) -> HttpResponse:
    """End the session on the server."""
    user = request.user
    if isinstance(user, User):
        sign_in.log_signed_out(user, address_of(request))
    logout(request)
    response = redirect("sign_in")
    # Ask the browser to forget what it holds of the session (OWASP ASVS 5.0, 14.3.1).
    response["Clear-Site-Data"] = '"cache", "storage"'
    return response
