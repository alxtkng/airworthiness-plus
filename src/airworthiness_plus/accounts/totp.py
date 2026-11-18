"""Codes from an authenticator application (REQ-008).

The time-based one-time password of RFC 6238, built on the counter-based
one of RFC 4226: HMAC-SHA-1, a 30-second step and 6 digits, which is what
authenticator applications use by default. The tests check this module
against the test values printed in both documents.
"""

import base64
import hmac
import secrets
import struct
from datetime import datetime
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6
SECRET_BYTES = 20
ISSUER = "Airworthiness+"


def new_secret() -> str:
    """Return a new random secret, in the base 32 form authenticator applications take."""
    return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode("ascii")


def hotp(key: bytes, counter: int, digits: int = DIGITS) -> str:
    """Return the RFC 4226 code for ``counter``."""
    # HMAC-SHA-1 is what RFC 4226 specifies; it is used as a keyed hash here,
    # where the known weaknesses of SHA-1 do not apply.
    digest = hmac.new(key, struct.pack(">Q", counter), "sha1").digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)


def counter_at(moment: datetime) -> int:
    """Return the number of whole 30-second steps since 1 January 1970 at ``moment``."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("moment must carry a time zone")
    return int(moment.timestamp()) // STEP_SECONDS


def matching_counter(
    secret: str, submitted: str, moment: datetime, *, after: int | None
) -> int | None:
    """Return the counter whose code is ``submitted``, or None if it is not accepted.

    A code is accepted for the current 30-second step and the one either
    side of it, to allow for a clock that is a little out. A code for a
    step at or before ``after``, the last one accepted for this user, is
    refused, so a code that has been used cannot be used again.
    """
    code = "".join(submitted.split())
    if len(code) != DIGITS or not code.isdigit():
        return None
    key = base64.b32decode(secret)
    now = counter_at(moment)
    found: int | None = None
    for counter in (now - 1, now, now + 1):
        if counter < 0:
            continue
        matches = hmac.compare_digest(hotp(key, counter), code)
        if matches and (after is None or counter > after) and found is None:
            found = counter
    return found


def set_up_address(secret: str, username: str) -> str:
    """Return the address an authenticator application reads to add the account."""
    label = quote(f"{ISSUER}:{username}")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(ISSUER)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
    )
