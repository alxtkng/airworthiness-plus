"""Security checks across the whole application (REQ-132; Step 7 of private beta).

Each module's own tests try every one of its pages as another
organisation, as each role, without signing in and with a forged request.
The tests here go over every address the application has, so that a page
added later cannot be left out, and check what every response carries.

Threats TH-002 to TH-008; planned tests T-SEC-005 to T-SEC-009; OWASP
ASVS 5.0 chapters 3, 6, 7, 13, 14 and 16.
"""

import logging
import re
import uuid
from datetime import date
from typing import Any, cast

import pytest
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import HttpResponse
from django.test import Client, RequestFactory
from django.urls import URLPattern, get_resolver

from airworthiness_plus.accounts import users
from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.accounts.permissions import address_of
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.session import working_for
from airworthiness_plus.interface.logs import UtcFormatter
from airworthiness_plus.interface.security import CONTENT_SECURITY_POLICY
from tests.conftest import as_owner
from tests.support import TODAY, Sample, add_sample_fleet, make_sample, signed_in

pytestmark = pytest.mark.django_db

SIGN_IN_PAGES = {"sign_in", "code", "set_up"}


def routes() -> list[tuple[str, str]]:
    """Return (name, address) for every address, with a made-up identifier where one is asked."""
    found = []
    for pattern in get_resolver().url_patterns:
        assert isinstance(pattern, URLPattern), "every address is listed in one place"
        assert pattern.name, "every address has a name"
        path = "/" + re.sub(r"<uuid:[a-z_]+>", str(uuid.uuid4()), str(pattern.pattern))
        found.append((pattern.name, path))
    return found


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


@pytest.fixture
def sample() -> Sample:
    return make_sample()


# Every address


def test_no_address_answers_without_sign_in() -> None:
    """REQ-008, threat TH-008. Every address but the sign-in pages sends a stranger to sign in."""
    anonymous = Client()
    assert len(routes()) > 60
    for name, path in routes():
        for method in ("get", "post"):
            response = getattr(anonymous, method)(path, secure=True)
            if name in SIGN_IN_PAGES:
                # The sign-in pages answer, or send back to the first step, or refuse the method.
                assert response.status_code in (200, 302, 405), f"{method} {path}"
            elif name == "sign_out":
                assert response.status_code in (302, 405), f"{method} {path}"
                assert method == "get" or response["Location"] == "/sign-in/"
            else:
                assert response.status_code in (302, 405), f"{method} {path}"
                if response.status_code == 302:
                    assert response["Location"].startswith("/sign-in/"), f"{method} {path}"
            assert b"G-" not in response.content


def test_every_write_refuses_a_forged_request(sample: Sample) -> None:
    """Threat TH-003, planned test T-SEC-005. No POST is accepted without the token of the page."""
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.administrator, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    refused = 0
    for _, path in routes():
        response = forged.post(path, {}, secure=True)
        assert response.status_code in (403, 405), path
        refused += response.status_code == 403
    assert refused > 50
    with as_owner():
        assert AccessEntry.objects.filter(kind="Action Refused").count() == 0


def test_nothing_is_changed_by_a_get(sample: Sample) -> None:
    """OWASP ASVS 5.0, 3.5.3. Reading every page as each role writes nothing to the records."""
    add_sample_fleet(sample)
    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM history_event")
        before = cursor.fetchone()
    for user in sample.by_role().values():
        client = signed_in(user)
        for _, path in routes():
            assert get(client, path).status_code in (200, 302, 403, 404, 405), path
    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM history_event")
        assert cursor.fetchone() == before


def test_a_method_the_application_does_not_use_is_refused(sample: Sample) -> None:
    """OWASP ASVS 5.0, 13.4.4. TRACE, PUT, PATCH, DELETE and OPTIONS get no page."""
    client = signed_in(sample.reader)
    for method in ("trace", "put", "patch", "delete", "options"):
        response = getattr(client, method)("/", secure=True)
        assert response.status_code == 405, method
        assert response["Allow"] == "GET, HEAD, POST"
        assert b"G-" not in response.content


def test_a_sign_in_with_nothing_in_it_is_refused_like_any_other() -> None:
    """Threat TH-001. Found by the test above on 19 November 2026: this was a server error."""
    for values in ({}, {"username": "", "password": ""}, {"username": "  ", "password": "x"}):
        response = Client().post("/sign-in/", values, secure=True)
        assert response.status_code == 200
        assert "User Name or Password Not Accepted" in response.content.decode()
    with as_owner():
        assert AccessEntry.objects.count() == 0


# What every response carries


def test_every_response_carries_the_security_headers(sample: Sample) -> None:
    """Threats TH-004, TH-005; planned test T-SEC-007; OWASP ASVS 5.0, 3.4.1 to 3.4.6, 14.3.2."""
    add_sample_fleet(sample)
    responses = [
        get(Client(), "/sign-in/"),
        get(Client(), "/"),  # sent to sign in
        get(signed_in(sample.reader), "/"),
        get(signed_in(sample.reader), "/users/"),  # refused
        get(signed_in(sample.reader), f"/aircraft/{uuid.uuid4()}/"),  # not found
        post(signed_in(sample.planner), "/records-export/organisation/"),  # a file
        Client().put("/", secure=True),  # method not allowed
    ]
    assert [r.status_code for r in responses] == [200, 302, 200, 403, 404, 200, 405]
    for response in responses:
        policy = response["Content-Security-Policy"]
        assert policy == CONTENT_SECURITY_POLICY
        assert "no-store" in response["Cache-Control"]
        assert response["X-Content-Type-Options"] == "nosniff"
        assert response["Referrer-Policy"] == "same-origin"
        assert response["Cross-Origin-Opener-Policy"] == "same-origin"
        assert response["X-Frame-Options"] == "DENY"
        assert response["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
        assert "camera=()" in response["Permissions-Policy"]
        if response.get("Content-Type", "").startswith("text/html"):
            assert response["Content-Type"] == "text/html; charset=utf-8"
    for directive in (
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "object-src 'none'",
        "form-action 'self'",
    ):
        assert directive in CONTENT_SECURITY_POLICY
    assert "unsafe" not in CONTENT_SECURITY_POLICY
    assert "*" not in CONTENT_SECURITY_POLICY
    assert "http" not in CONTENT_SECURITY_POLICY


def test_cookies_are_for_this_host_over_https_and_hidden_from_scripts(sample: Sample) -> None:
    """Threat TH-002; planned test T-SEC-003; OWASP ASVS 5.0, 3.3.1 to 3.3.4."""
    assert settings.SESSION_COOKIE_NAME == "__Host-sessionid"
    assert settings.CSRF_COOKIE_NAME == "__Host-csrftoken"
    client = Client()
    get(client, "/sign-in/")
    token = client.cookies["__Host-csrftoken"]
    assert (token["secure"], token["path"], token["domain"], token["samesite"]) == (
        True,
        "/",
        "",
        "Lax",
    )
    client = signed_in(sample.reader)
    get(client, "/")
    session = client.cookies["__Host-sessionid"]
    assert (session["secure"], session["httponly"], session["path"], session["domain"]) == (
        True,
        True,
        "/",
        "",
    )
    assert session["samesite"] == "Lax"
    assert not session["max-age"]  # ends when the browser closes


def test_signing_out_asks_the_browser_to_forget(sample: Sample) -> None:
    """OWASP ASVS 5.0, 14.3.1."""
    response = post(signed_in(sample.reader), "/sign-out/")
    assert response["Clear-Site-Data"] == '"cache", "storage"'


# Hostile input (T-SEC-006) and large requests (T-SEC-009)

HOSTILE = (
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "'; DROP TABLE aircraft_aircraft; --",
    "{{ 7*7 }}{% debug %}",
    '=HYPERLINK("[Address]")',
)


def test_hostile_text_is_stored_and_shown_as_text(sample: Sample) -> None:
    """Threat TH-004, planned test T-SEC-006. Markup, SQL and template code are only words."""
    planner = signed_in(sample.planner)
    for text in HOSTILE:
        assert post(planner, "/problem-log/add/", problem=text).status_code == 302
    post(
        planner,
        "/aircraft/add/",
        registration="G-TEST",
        type_rating=HOSTILE[0],
        owner=HOSTILE[2],
        regime="Part 21",
    )
    with working_for(sample.ours.id, sample.planner.id):
        aircraft = Aircraft.objects.get(registration="G-TEST")
        assert (aircraft.type_rating, aircraft.owner) == (HOSTILE[0], HOSTILE[2])
    for path in ("/problem-log/", "/", f"/aircraft/{aircraft.id}/"):
        body = get(planner, path).content.decode()
        assert "<script>alert" not in body
        assert "<img src=x" not in body
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    log = get(planner, "/problem-log/").content.decode()
    assert "{{ 7*7 }}{% debug %}" in log
    assert "49" not in re.sub(r"[0-9a-f-]{36}", "", log)
    # A search address with markup in it is not found, and is not echoed.
    echoed = get(planner, "/aircraft/%3Cscript%3Ealert(1)%3C/script%3E/")
    assert echoed.status_code == 404
    assert b"<script>alert" not in echoed.content


def test_a_request_that_is_too_large_is_refused(sample: Sample) -> None:
    """Threat TH-007, planned test T-SEC-009. One megabyte for a form."""
    planner = signed_in(sample.planner)
    response = post(planner, "/problem-log/add/", problem="x" * 1_000_001)
    assert response.status_code == 400
    with working_for(sample.ours.id, sample.planner.id):
        from airworthiness_plus.acceptance.models import Problem

        assert Problem.objects.count() == 0


def test_an_error_page_says_nothing_of_the_inside(sample: Sample) -> None:
    """OWASP ASVS 5.0, 13.4.2, 16.5.1. No debug page, no trace, no setting."""
    assert settings.DEBUG is False
    for response in (
        get(signed_in(sample.reader), f"/aircraft/{uuid.uuid4()}/"),
        get(signed_in(sample.reader), "/users/"),
        get(signed_in(sample.reader), "/no-such-page/"),
    ):
        body = response.content.decode()
        for inside in ("Traceback", "airworthiness_plus", "SECRET", "django", "SELECT"):
            assert inside not in body, inside


# Passwords, sessions and logging


def test_a_password_is_not_built_on_a_word_anyone_would_try(sample: Sample) -> None:
    """Threat TH-001; OWASP ASVS 5.0, 6.1.2, 6.2.9, 6.2.11."""
    with working_for(sample.ours.id, sample.administrator.id):
        user = User.objects.select_related("organisation").get(pk=sample.lucy.pk)
    for refused in (
        "Airworthiness-2026-Fleet",
        "my air worthy record 77",
        "CAA approved engineer",
        "UK.CAO.[Number] records",
        "Your Organisation rules 9",
    ):
        with pytest.raises(ValidationError, match="too easy to guess"):
            validate_password(refused, user)
    # A long passphrase of ordinary words is welcome, and so is any character.
    validate_password("correct horse battery staple, 64 characters and more " * 2, user)
    validate_password("ñandú çedilla Ω 98 täglich", user)


def test_a_users_sessions_can_all_be_ended(sample: Sample) -> None:
    """Threat TH-002; OWASP ASVS 5.0, 7.4.5, 7.5.2. By the user, and by the Administrator."""
    here, elsewhere = signed_in(sample.planner), signed_in(sample.planner)
    assert get(elsewhere, "/").status_code == 200
    assert post(here, "/account/sessions/").status_code == 302
    assert get(here, "/").status_code == 200
    assert get(elsewhere, "/").status_code == 302
    administrator = signed_in(sample.administrator)
    assert post(administrator, f"/users/{sample.planner.id}/sessions/").status_code == 302
    assert get(here, "/").status_code == 302
    with as_owner():
        ended = AccessEntry.objects.filter(kind="Sessions Ended", user_id=sample.planner.id)
        assert [entry.detail for entry in ended] == [
            "By [Planning and Records Name]",
            "By [Accountable Manager]",
        ]
    # Another organisation's user is not found, and only an Administrator may.
    assert (
        post(signed_in(sample.stranger), f"/users/{sample.planner.id}/sessions/").status_code == 404
    )
    assert (
        post(signed_in(sample.reader), f"/users/{sample.planner.id}/sessions/").status_code == 403
    )
    with working_for(sample.ours.id, sample.administrator.id):
        users.end_sessions(sample.reader, by=sample.administrator)


def test_the_address_of_a_request_is_what_the_proxy_saw(settings: object) -> None:
    """OWASP ASVS 5.0, 4.1.3, 15.3.4. What the client claims about its address is ignored."""
    factory = RequestFactory()
    claimed = factory.get("/", HTTP_X_FORWARDED_FOR="203.0.113.9", REMOTE_ADDR="198.51.100.7")
    assert address_of(claimed) == "198.51.100.7"
    settings.BEHIND_PROXY = True  # type: ignore[attr-defined]
    through = factory.get(
        "/", HTTP_X_FORWARDED_FOR="203.0.113.9, 192.0.2.44", REMOTE_ADDR="10.0.0.2"
    )
    assert address_of(through) == "192.0.2.44"
    nonsense = factory.get("/", HTTP_X_FORWARDED_FOR="<script>", REMOTE_ADDR="10.0.0.2")
    assert address_of(nonsense) is None
    assert address_of(factory.get("/", REMOTE_ADDR="10.0.0.2")) is None


def test_a_line_of_the_server_log_has_its_time_in_coordinated_universal_time() -> None:
    """OWASP ASVS 5.0, 16.2.1, 16.2.2, 16.3.4. Errors go to standard error, one line each."""
    config = cast(dict[str, Any], settings.LOGGING)
    assert config["root"]["handlers"] == ["standard_error"]
    assert config["loggers"]["django"]["level"] == "WARNING"
    record = logging.LogRecord("django.request", logging.ERROR, "", 0, "Failed", None, None)
    record.created, record.msecs = 1_795_000_000.0, 0.0
    line = UtcFormatter("%(asctime)s %(levelname)s %(name)s %(message)s").format(record)
    assert line == "2026-11-18T11:06:40.000Z ERROR django.request Failed"


def test_today_in_these_tests_is_the_sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sample world is 18 November 2026; nothing here depends on the clock."""
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    assert aircraft_services.today() == date(2026, 11, 18)
