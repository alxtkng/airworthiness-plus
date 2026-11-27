"""The server-side controls for passkey ceremonies and fresh verification."""

import json
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.test import Client, override_settings

from airworthiness_plus.accounts import passkeys, sign_in
from airworthiness_plus.accounts.middleware import LAST_SEEN_KEY, SIGNED_IN_AT_KEY
from airworthiness_plus.accounts.models import AccessEntry, AccessKind, User
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from tests.support import Sample, get, signed_in

pytestmark = pytest.mark.django_db

SIGN_IN = "/sign-in/passkey/"
ADD = "/account/passkeys/add/"
VERIFY = "/account/verify/"


def send(client: Client, path: str, **payload: object) -> HttpResponse:
    return client.post(path, json.dumps(payload), content_type="application/json", secure=True)  # type: ignore[return-value]


def set_times(client: Client, *, idle: int = 0, age: int = 6) -> None:
    session = client.session
    now = sign_in.current_time()
    session[SIGNED_IN_AT_KEY] = (now - timedelta(minutes=age)).isoformat()
    session[LAST_SEEN_KEY] = (now - timedelta(minutes=idle)).isoformat()
    session.save()


def test_passkey_challenge_is_bound_to_browser_and_consumed_on_failure(sample: Sample) -> None:
    first, second = Client(), Client()
    for client in (first, second):
        assert get(client, "/sign-in/").status_code == 200
    options = send(first, SIGN_IN, username=sample.planner.username)
    assert options.status_code == 200
    data = json.loads(options.content)
    assert data["publicKey"]["userVerification"] == "required"
    challenge = data["ceremony"]
    assert send(second, SIGN_IN, ceremony=challenge, credential={}).status_code == 400
    assert Session.objects.filter(pk=challenge).exists()
    assert send(first, SIGN_IN, ceremony=challenge, credential={}).status_code == 400
    assert not Session.objects.filter(pk=challenge).exists()
    assert send(first, SIGN_IN, ceremony=challenge, credential={}).status_code == 400
    assert SESSION_KEY not in first.session


def test_passkey_registration_and_revocation_need_recent_verification(
    sample: Sample, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = signed_in(sample.planner)
    set_times(client)
    assert send(client, ADD).status_code == 403
    assert b"Your Current Password" in client.post("/account/passkeys/", secure=True).content
    assert (
        b"Your Current Password"
        in client.post("/account/passkeys/remove/", {"passkey": "absent"}, secure=True).content
    )
    with working_for(sample.ours.id, sample.planner.id):
        User.objects.filter(pk=sample.planner.pk).update(
            passkeys={
                "a2V5": {
                    "name": "Test Key",
                    "rp_id": "testserver",
                    "public_key": "a2V5",
                    "sign_count": 0,
                }
            }
        )
    seen = []

    def valid(user: User, ceremony: passkeys.Ceremony, credential: dict[str, object]) -> bool:
        seen.append((user.pk, ceremony["purpose"], credential))
        return True

    monkeypatch.setattr(passkeys, "verify", valid)
    old_session = client.cookies[settings.SESSION_COOKIE_NAME].value
    options = send(client, VERIFY)
    assert options.status_code == 200
    assert (
        send(
            client, VERIFY, ceremony=json.loads(options.content)["ceremony"], credential={}
        ).status_code
        == 200
    )
    assert seen == [(sample.planner.pk, "verify", {})]
    assert not Session.objects.filter(pk=old_session).exists()
    response = send(client, ADD)
    assert response.status_code == 200
    assert (
        json.loads(response.content)["publicKey"]["authenticatorSelection"]["userVerification"]
        == "required"
    )
    other_session = signed_in(sample.planner)
    assert (
        client.post("/account/passkeys/remove/", {"passkey": "a2V5"}, secure=True).status_code
        == 302
    )
    assert get(other_session, "/dashboard/").status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        sample.planner.refresh_from_db()
        assert not sample.planner.passkeys
        assert AccessEntry.objects.filter(kind=AccessKind.PASSKEY_REMOVED).count() == 1
        for event in Event.of(sample.planner):
            assert "passkeys" not in json.loads(event.after_json or "{}")


@pytest.mark.parametrize(
    ("limit", "idled", "status"), [(30, 31, 302), (60, 31, 200), (60, 61, 302)]
)
def test_idle_limits_are_server_side(sample: Sample, limit: int, idled: int, status: int) -> None:
    client = signed_in(sample.planner)
    set_times(client, idle=idled, age=90)
    with override_settings(SESSION_IDLE_MINUTES=limit):
        assert get(client, "/dashboard/").status_code == status


def test_managed_session_still_ends_after_twelve_hours(sample: Sample) -> None:
    client = signed_in(sample.planner)
    set_times(client, idle=1, age=721)
    assert get(client, "/dashboard/").status_code == 302
