"""Checks on the application skeleton: settings, database and what is absent."""

import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.test import Client

from airworthiness_plus import environment


def test_a_missing_required_value_stops_the_application(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assurance case C5.4: secrets come only from the environment, with no fallback."""
    monkeypatch.delenv("AIRWORTHINESS_EXAMPLE", raising=False)
    with pytest.raises(ImproperlyConfigured, match="AIRWORTHINESS_EXAMPLE"):
        environment.required("AIRWORTHINESS_EXAMPLE")
    monkeypatch.setenv("AIRWORTHINESS_EXAMPLE", "")
    with pytest.raises(ImproperlyConfigured):
        environment.required("AIRWORTHINESS_EXAMPLE")
    monkeypatch.setenv("AIRWORTHINESS_EXAMPLE", "value")
    assert environment.required("AIRWORTHINESS_EXAMPLE") == "value"


def test_a_flag_is_on_only_when_set_to_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Debug mode cannot be switched on by accident: only the exact word does it."""
    for value, expected in (("true", True), ("True", False), ("1", False), ("", False)):
        monkeypatch.setenv("AIRWORTHINESS_EXAMPLE", value)
        assert environment.flag("AIRWORTHINESS_EXAMPLE") is expected
    monkeypatch.delenv("AIRWORTHINESS_EXAMPLE")
    assert environment.flag("AIRWORTHINESS_EXAMPLE") is False


def test_a_list_is_split_on_commas_without_blanks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIRWORTHINESS_EXAMPLE", "one.example, two.example,,")
    assert environment.listed("AIRWORTHINESS_EXAMPLE") == ["one.example", "two.example"]
    monkeypatch.delenv("AIRWORTHINESS_EXAMPLE")
    assert environment.listed("AIRWORTHINESS_EXAMPLE") == []


@pytest.mark.parametrize(
    "missing",
    ["AIRWORTHINESS_SECRET_KEY", "AIRWORTHINESS_DATABASE_NAME", "AIRWORTHINESS_DATABASE_USER"],
)
def test_settings_refuse_to_load_without_a_required_value(missing: str) -> None:
    """Assurance case C5.4, threat TH-063. The settings hold no default secret."""
    without = {name: value for name, value in os.environ.items() if name != missing}
    result = subprocess.run(
        [sys.executable, "-c", "import airworthiness_plus.settings"],
        env=without,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert f"{missing} must be set in the environment" in result.stderr


def test_debug_is_off_unless_asked_for() -> None:
    """The pipeline and the server run with debug off."""
    assert settings.DEBUG is False


def test_entry_times_are_stored_in_coordinated_universal_time() -> None:
    """REQ-137."""
    assert settings.USE_TZ is True
    assert settings.TIME_ZONE == "UTC"


@pytest.mark.django_db
def test_the_database_is_postgresql_and_its_session_is_in_coordinated_universal_time() -> None:
    """ADR-0001, REQ-137. The record rules rely on PostgreSQL itself."""
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version_num")
        (version,) = cursor.fetchone()
        cursor.execute("SHOW TimeZone")
        (zone,) = cursor.fetchone()
    assert int(version) >= 160000
    assert zone == "UTC"


def test_each_request_is_one_transaction() -> None:
    """REQ-138. A response is sent only after the request's writes are committed."""
    assert settings.DATABASES["default"]["ATOMIC_REQUESTS"] is True


@pytest.mark.django_db
def test_the_administration_interface_is_absent() -> None:
    """REQ-004, threat TH-024, planned test T-SEC-018."""
    assert "django.contrib.admin" not in settings.INSTALLED_APPS
    assert Client().get("/admin/", secure=True).status_code == 404
    assert Client().get("/admin/login/", secure=True).status_code == 404


def test_plain_http_is_redirected_to_https() -> None:
    """Threat TH-005, planned test T-SEC-008."""
    response = Client().get("/anything/")
    assert response.status_code == 301
    assert response["Location"].startswith("https://")


def test_cookies_are_secure_and_hidden_from_scripts() -> None:
    """Threat TH-002, planned test T-SEC-003."""
    assert settings.SESSION_COOKIE_SECURE is True
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SECURE is True


def test_django_deployment_checks_pass() -> None:
    """Threats TH-002, TH-005. Django's own deployment checklist raises nothing.

    Two checks are silenced with the reason in the settings: Strict Transport
    Security is not extended to subdomains this application does not own.
    """
    call_command("check", deploy=True, fail_level="WARNING")
    assert settings.SILENCED_SYSTEM_CHECKS == ["security.W005", "security.W021"]
