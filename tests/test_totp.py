"""Authenticator codes against the test values printed in RFC 4226 and RFC 6238.

The expected values are not worked here: they are the published ones, for
the published secret, the ASCII text 12345678901234567890.
"""

import base64
from datetime import UTC, datetime

import pytest

from airworthiness_plus.accounts import totp

RFC_KEY = b"12345678901234567890"
RFC_SECRET = base64.b32encode(RFC_KEY).decode("ascii")


@pytest.mark.parametrize(
    ("counter", "expected"),
    [
        (0, "755224"),
        (1, "287082"),
        (2, "359152"),
        (3, "969429"),
        (4, "338314"),
        (5, "254676"),
        (6, "287922"),
        (7, "162583"),
        (8, "399871"),
        (9, "520489"),
    ],
)
def test_counter_based_codes_match_rfc_4226(counter: int, expected: str) -> None:
    """REQ-008. RFC 4226, Appendix D."""
    assert totp.hotp(RFC_KEY, counter) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (59, "94287082"),
        (1111111109, "07081804"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
        (2000000000, "69279037"),
        (20000000000, "65353130"),
    ],
)
def test_time_based_codes_match_rfc_6238(seconds: int, expected: str) -> None:
    """REQ-008. RFC 6238, Appendix B, the SHA-1 column: 8 digits, 30-second step."""
    moment = datetime.fromtimestamp(seconds, UTC)
    assert totp.hotp(RFC_KEY, totp.counter_at(moment), digits=8) == expected


def test_the_step_is_30_seconds() -> None:
    """REQ-008. 59 seconds is step 1; 60 seconds is step 2."""
    assert totp.counter_at(datetime.fromtimestamp(29, UTC)) == 0
    assert totp.counter_at(datetime.fromtimestamp(30, UTC)) == 1
    assert totp.counter_at(datetime.fromtimestamp(59, UTC)) == 1
    assert totp.counter_at(datetime.fromtimestamp(60, UTC)) == 2
    with pytest.raises(ValueError, match="time zone"):
        totp.counter_at(datetime(2026, 11, 18, 12, 0))  # noqa: DTZ001


def test_a_code_is_accepted_for_its_own_30_seconds_and_no_longer() -> None:
    """REQ-008, OWASP ASVS 5.0 6.5.5. Step 1, from 30 to 59 seconds, is the code
    287082 (RFC 4226). A second before or after that step it is refused."""
    for second, accepted in ((29, False), (30, True), (59, True), (60, False), (89, False)):
        found = totp.matching_counter(
            RFC_SECRET, "287082", datetime.fromtimestamp(second, UTC), after=None
        )
        assert found == (1 if accepted else None), second


def test_a_used_code_is_refused() -> None:
    """REQ-008, threat TH-001. Once step 1 has been accepted, its code is spent,
    and so is any earlier one; the code for step 2 (359152) is good in step 2."""
    moment = datetime.fromtimestamp(59, UTC)
    assert totp.matching_counter(RFC_SECRET, "287082", moment, after=1) is None
    assert totp.matching_counter(RFC_SECRET, "755224", moment, after=1) is None
    assert totp.matching_counter(RFC_SECRET, "359152", moment, after=1) is None
    later = datetime.fromtimestamp(60, UTC)
    assert totp.matching_counter(RFC_SECRET, "359152", later, after=1) == 2
    assert totp.matching_counter(RFC_SECRET, "359152", later, after=2) is None


@pytest.mark.parametrize("submitted", ["", "28708", "2870820", "28708a", "000000", "287 0821"])
def test_anything_but_the_right_six_digits_is_refused(submitted: str) -> None:
    """REQ-008."""
    assert (
        totp.matching_counter(RFC_SECRET, submitted, datetime.fromtimestamp(59, UTC), after=None)
        is None
    )


def test_spaces_in_a_typed_code_are_ignored() -> None:
    """REQ-008. Authenticator applications show the code as 287 082."""
    assert (
        totp.matching_counter(RFC_SECRET, " 287 082 ", datetime.fromtimestamp(59, UTC), after=None)
        == 1
    )


def test_a_new_secret_is_160_random_bits_in_base_32() -> None:
    """REQ-008. RFC 4226 recommends a shared secret of 160 bits."""
    first, second = totp.new_secret(), totp.new_secret()
    assert first != second
    assert len(base64.b32decode(first)) == 20
    assert len(first) == 32


def test_the_set_up_address_names_the_account_and_the_settings() -> None:
    """REQ-008."""
    address = totp.set_up_address(RFC_SECRET, "lucy.grant@your-organisation.example")
    assert address == (
        "otpauth://totp/Airworthiness%2B%3Alucy.grant%40your-organisation.example"
        f"?secret={RFC_SECRET}&issuer=Airworthiness%2B&algorithm=SHA1&digits=6&period=30"
    )
