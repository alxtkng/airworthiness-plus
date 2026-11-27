"""WebAuthn ceremonies and credential verification for the accounts service."""

import json
import re
from datetime import timedelta
from typing import Literal, TypedDict, cast
from urllib.parse import urlsplit

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.http import HttpRequest
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
    parse_authentication_credential_json,
)
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialCreationOptions,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialRequestOptions,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.sessions import identifier_of

Purpose = Literal["sign-in", "verify", "register"]
CEREMONY_SECONDS = 180
MAX_KEYS = 10


class Ceremony(TypedDict):
    binding: str
    purpose: Purpose
    origin: str
    rp_id: str
    challenge: str
    account: str


class Refused(ValueError):
    """The request does not contain a usable passkey ceremony or response."""


def _site(request: HttpRequest) -> tuple[str, str]:
    origin = f"{request.scheme}://{request.get_host()}"
    rp_id = urlsplit(origin).hostname
    if not rp_id or (not request.is_secure() and rp_id not in ("localhost", "127.0.0.1")):
        raise Refused("Passkeys Need a Secure Connection")
    return origin, rp_id


def start(
    request: HttpRequest, purpose: Purpose, account: str, user: User | None = None
) -> dict[str, object]:
    """Issue site-bound options and a single-use server-side ceremony."""
    origin, rp_id = _site(request)
    if not request.session.session_key or not request.session.exists(request.session.session_key):
        request.session.create()
    key = request.session.session_key
    if key is None:
        raise Refused("Start Again to Use a Passkey")
    request.session.modified = True
    descriptors = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(identifier))
        for identifier, passkey in (user.passkeys.items() if user is not None else ())
        if passkey["rp_id"] == rp_id
    ]
    options: PublicKeyCredentialCreationOptions | PublicKeyCredentialRequestOptions
    if purpose == "register":
        if user is None:
            raise Refused("Sign In to Add a Passkey")
        options = generate_registration_options(
            rp_id=rp_id,
            rp_name="Airworthiness+",
            user_id=user.pk.bytes,
            user_name=user.username,
            user_display_name=user.full_name,
            timeout=CEREMONY_SECONDS * 1000,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.REQUIRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=descriptors,
        )
    else:
        options = generate_authentication_options(
            rp_id=rp_id,
            timeout=CEREMONY_SECONDS * 1000,
            allow_credentials=descriptors,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
    ceremony: Ceremony = {
        "binding": str(identifier_of(key)),
        "purpose": purpose,
        "origin": origin,
        "rp_id": rp_id,
        "challenge": bytes_to_base64url(options.challenge),
        "account": account,
    }
    # A row separate from the browser session can be locked and consumed even
    # when several tabs finish at once. Browser session saves cannot restore it.
    store = SessionStore()
    store["passkey_ceremony"] = dict(ceremony)
    store.set_expiry(timedelta(seconds=CEREMONY_SECONDS))
    store.create()
    return {"ceremony": store.session_key, "publicKey": json.loads(options_to_json(options))}


def take(request: HttpRequest, purpose: Purpose, identifier: object) -> Ceremony:
    """Read and consume options for this browser, purpose and site."""
    key = request.session.session_key
    if (
        key is None
        or not isinstance(identifier, str)
        or not re.fullmatch("[a-z0-9]{32}", identifier)
    ):
        raise Refused("Start Again to Use a Passkey")
    record = (
        Session.objects.select_for_update()
        .filter(session_key=identifier, expire_date__gt=timezone.now())
        .first()
    )
    raw = record.get_decoded().get("passkey_ceremony") if record else None
    origin, rp_id = _site(request)
    if (
        record is None
        or not isinstance(raw, dict)
        or raw.get("purpose") != purpose
        or raw.get("binding") != str(identifier_of(key))
        or raw.get("origin") != origin
        or raw.get("rp_id") != rp_id
    ):
        raise Refused("Start Again to Use a Passkey")
    record.delete()
    return cast(Ceremony, raw)


def add(user: User, ceremony: Ceremony, credential: dict[str, object], name: str) -> None:
    """Verify a new credential and store its public key on the locked user record."""
    if len(user.passkeys) >= MAX_KEYS:
        raise Refused("Remove a Passkey Before Adding Another")
    try:
        result = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(ceremony["challenge"]),
            expected_rp_id=ceremony["rp_id"],
            expected_origin=ceremony["origin"],
            require_user_verification=True,
        )
    except (WebAuthnException, ValueError, TypeError) as error:
        raise Refused("Passkey Not Accepted") from error
    identifier = bytes_to_base64url(result.credential_id)
    if identifier in user.passkeys:
        raise Refused("This Passkey Is Already Added")
    user.passkeys[identifier] = {
        "name": name,
        "rp_id": ceremony["rp_id"],
        "public_key": bytes_to_base64url(result.credential_public_key),
        "sign_count": result.sign_count,
    }
    user.save(update_fields=["passkeys"])


def verify(user: User, ceremony: Ceremony, response: dict[str, object]) -> bool:
    """Verify the authenticator assertion and update its counter, under the account lock."""
    try:
        credential = parse_authentication_credential_json(response)
        identifier = bytes_to_base64url(credential.raw_id)
        saved = user.passkeys.get(identifier)
        if saved is None or saved["rp_id"] != ceremony["rp_id"]:
            return False
        if credential.response.user_handle not in (None, user.pk.bytes):
            return False
        result = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(ceremony["challenge"]),
            expected_rp_id=ceremony["rp_id"],
            expected_origin=ceremony["origin"],
            credential_public_key=base64url_to_bytes(saved["public_key"]),
            credential_current_sign_count=saved["sign_count"],
            require_user_verification=True,
        )
    except (WebAuthnException, ValueError, TypeError):
        return False
    if result.new_sign_count != saved["sign_count"]:
        saved["sign_count"] = result.new_sign_count
        user.save(update_fields=["passkeys"])
    return True
