"""Sign in, verify again, and manage passkeys."""

import json
from typing import Any, cast

from django.contrib.auth import HASH_SESSION_KEY, update_session_auth_hash
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from airworthiness_plus.accounts import passkeys, sign_in
from airworthiness_plus.accounts.middleware import VERIFIED_AT_KEY, recently_verified
from airworthiness_plus.accounts.models import AccessKind, User
from airworthiness_plus.accounts.permissions import address_of, signed_in
from airworthiness_plus.accounts.views import _complete
from airworthiness_plus.history.session import working_for


def _json(request: HttpRequest) -> dict[str, Any]:
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeError) as error:
        raise passkeys.Refused("The Passkey Request Was Not Understood") from error
    if not isinstance(data, dict):
        raise passkeys.Refused("The Passkey Request Was Not Understood")
    return data


def _error(error: passkeys.Refused, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": str(error)}, status=status)


def _credential(data: dict[str, Any]) -> dict[str, object]:
    credential = data.get("credential")
    if not isinstance(credential, dict):
        raise passkeys.Refused("Passkey Not Accepted")
    return credential


@never_cache
@require_POST
def passkey_sign_in(request: HttpRequest) -> JsonResponse:
    """Begin or complete a passkey sign-in."""
    if request.user.is_authenticated:
        return JsonResponse({"redirect": reverse("dashboard")})
    address = address_of(request)
    try:
        data = _json(request)
        if "ceremony" not in data:
            name = data.get("username")
            if not isinstance(name, str):
                raise passkeys.Refused("Give Your User Name")
            name = name.strip()
            if not name or len(name) > sign_in.USERNAME_LENGTH or "\x00" in name:
                raise passkeys.Refused("Give Your User Name")
            return JsonResponse(passkeys.start(request, "sign-in", name))
        ceremony = passkeys.take(request, "sign-in", data.get("ceremony"))
        username = ceremony["account"]
        with sign_in._checking(username):
            if sign_in._refuse_if_locked(username, address):
                return _error(passkeys.Refused("Passkey Not Accepted"))
            user = sign_in._find(username, active_only=True)
            if user is not None:
                with working_for(user.organisation_id, user.pk):
                    user = User.objects.select_for_update().get(pk=user.pk)
                    if (
                        user.is_active
                        and not user.password_must_change
                        and isinstance(credential := data.get("credential"), dict)
                        and passkeys.verify(user, ceremony, credential)
                    ):
                        sign_in._log(
                            AccessKind.SIGNED_IN,
                            username,
                            user=user,
                            detail="Passkey",
                            address=address,
                        )
                        response = _complete(request, user)
                        return JsonResponse({"redirect": response["Location"]})
            sign_in._log(
                AccessKind.SIGN_IN_FAILED,
                username,
                user=user,
                detail="Passkey Not Accepted",
                address=address,
            )
        raise passkeys.Refused("Passkey Not Accepted")
    except passkeys.Refused as error:
        return _error(error)


def _verify_again(request: HttpRequest, user: User, data: dict[str, Any]) -> JsonResponse:
    if "ceremony" not in data:
        if not user.passkeys or user.password_must_change:
            raise passkeys.Refused("Use Your Password and Authenticator Code")
        return JsonResponse(passkeys.start(request, "verify", str(user.pk), user))
    ceremony = passkeys.take(request, "verify", data["ceremony"])
    if ceremony["account"] != str(user.pk):
        raise passkeys.Refused("Passkey Not Accepted")
    address = address_of(request)
    user = User.objects.select_for_update().get(pk=user.pk)
    if sign_in._refuse_if_locked(user.username, address):
        raise passkeys.Refused("Passkey Not Accepted")
    if not (
        user.is_active
        and not user.password_must_change
        and request.session.get(HASH_SESSION_KEY) == user.get_session_auth_hash()
        and passkeys.verify(user, ceremony, _credential(data))
    ):
        sign_in._log(
            AccessKind.SIGN_IN_FAILED,
            user.username,
            user=user,
            detail="Passkey Not Accepted",
            address=address,
        )
        raise passkeys.Refused("Passkey Not Accepted")
    sign_in.log_account_event(AccessKind.IDENTITY_VERIFIED, user, detail="Passkey", address=address)
    request.session.cycle_key()
    request.session[VERIFIED_AT_KEY] = sign_in.current_time().isoformat()
    return JsonResponse({"verified": True})


@never_cache
@signed_in
@require_POST
def verify_passkey(request: HttpRequest) -> JsonResponse:
    """Verify a signed-in user's passkey before a sensitive action."""
    user = cast(User, request.user)
    try:
        return _verify_again(request, user, _json(request))
    except passkeys.Refused as error:
        return _error(error)


@never_cache
@signed_in
@require_http_methods(["GET", "POST"])
def passkey_settings(request: HttpRequest) -> HttpResponse:
    """Show a user's passkeys and options to register or revoke them."""
    user = cast(User, request.user)
    if user.password_must_change:
        return redirect("change_password")
    if request.method == "POST":
        from airworthiness_plus.accounts.user_views import code_page

        asked = code_page(
            request,
            "Verify Your Identity",
            "Changing Passkeys",
            ("passkey_settings", "Back to Passkeys"),
            full=True,
        )
        return asked if asked is not None else redirect("passkey_settings")
    return render(
        request,
        "accounts/passkeys.html",
        {"passkeys": user.passkeys, "verification_needed": not recently_verified(request.session)},
    )


@never_cache
@signed_in
@require_POST
def add_passkey(request: HttpRequest) -> JsonResponse:
    """Register a passkey after recent verification."""
    user = cast(User, request.user)
    if user.password_must_change or not recently_verified(request.session):
        return _error(passkeys.Refused("Verify Your Identity First"), 403)
    try:
        data = _json(request)
        if "ceremony" not in data:
            return JsonResponse(passkeys.start(request, "register", str(user.pk), user))
        ceremony = passkeys.take(request, "register", data["ceremony"])
        name = data.get("name")
        if (
            ceremony["account"] != str(user.pk)
            or not isinstance(name, str)
            or not 1 <= len(name.strip()) <= 80
        ):
            raise passkeys.Refused("Give This Passkey a Name of 1 to 80 Characters")
        user = User.objects.select_for_update().get(pk=user.pk)
        if (
            request.session.get(HASH_SESSION_KEY) != user.get_session_auth_hash()
            or not user.is_active
        ):
            raise passkeys.Refused("Sign In Again to Add a Passkey")
        passkeys.add(user, ceremony, _credential(data), name.strip())
        sign_in.log_account_event(AccessKind.PASSKEY_ADDED, user, address=address_of(request))
        return JsonResponse({"redirect": reverse("passkey_settings")})
    except passkeys.Refused as error:
        return _error(error)


@never_cache
@signed_in
@require_POST
def remove_passkey(request: HttpRequest) -> HttpResponse:
    """Revoke a passkey and end the other sessions for this account."""
    from airworthiness_plus.accounts.user_views import code_page

    user = cast(User, request.user)
    if user.password_must_change:
        return redirect("change_password")
    asked = code_page(
        request,
        "Remove a Passkey",
        "Removing a Passkey",
        ("passkey_settings", "Back to Passkeys"),
        full=True,
    )
    if asked is not None:
        return asked
    user = User.objects.select_for_update().get(pk=user.pk)
    if request.session.get(HASH_SESSION_KEY) != user.get_session_auth_hash() or not user.is_active:
        return redirect("sign_in")
    identifier = request.POST.get("passkey", "")
    if identifier in user.passkeys:
        user.passkeys.pop(identifier)
        user.session_generation += 1
        user.save(update_fields=["passkeys", "session_generation"])
        sign_in.log_account_event(AccessKind.PASSKEY_REMOVED, user, address=address_of(request))
        update_session_auth_hash(request, user)
    return redirect("passkey_settings")
