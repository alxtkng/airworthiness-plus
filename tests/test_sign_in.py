"""Signing in, sessions, the access log and refused actions.

REQ-008, REQ-009, REQ-010; threats TH-001, TH-002, TH-003, TH-008. The
tests drive the pages as a browser would, over HTTPS, and read the access
log as the owner of the tables.

The people are from design-system/SampleData.md. The clock is moved by
hand: codes change every 30 seconds and sessions end after set times.
"""

import base64
import itertools
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.http import HttpResponse
from django.test import Client
from django.utils import timezone
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_plus.accounts import sign_in, totp, users
from airworthiness_plus.accounts.models import AccessEntry, AccessKind, User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.history.models import Event, RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import SIGNING_IN_SETTING
from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from tests.conftest import as_owner
from tests.support import get, post

pytestmark = pytest.mark.django_db

# Made afresh for each run, so no password is written in the repository.
PASSWORD = secrets.token_urlsafe(18)
WRONG = secrets.token_urlsafe(18)
LUCY = "lucy.grant@your-organisation.example"
STRANGER = "name@other-organisation.example"


@dataclass
class Clock:
    """A clock the tests move by hand."""

    now: datetime = field(default_factory=timezone.now)

    def advance(self, **amount: float) -> None:
        self.now += timedelta(**amount)

    def read(self) -> datetime:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    moving = Clock()
    monkeypatch.setattr(sign_in, "current_time", moving.read)
    return moving


@dataclass(frozen=True)
class People:
    ours: Organisation
    lucy: User
    other: Organisation
    stranger: User


@pytest.fixture
def people() -> People:
    with as_owner():
        ours, lucy = provision_organisation(
            name="[Your Organisation]",
            approval_reference="UK.CAO.[Number]",
            privileges=list(Privilege),
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username=LUCY,
            first_user_full_name="Lucy Grant",
            first_user_password=PASSWORD,
        )
        other, stranger = provision_organisation(
            name="[Other Organisation]",
            approval_reference="UK.CAO.[Other Number]",
            privileges=[Privilege.CONTINUING_AIRWORTHINESS_MANAGEMENT],
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username=STRANGER,
            first_user_full_name="[Other Name]",
            first_user_password=PASSWORD,
        )
        # These tests are of signing in. A first password, which must be
        # changed, is tested in tests/test_users.py and tests/test_test_site.py.
        User.objects.filter(pk__in=[lucy.pk, stranger.pk]).update(
            password_must_change=False, first_password_set_on=None
        )
    return People(ours, lucy, other, stranger)


def secret_of(username: str) -> str:
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT second_factor_secret FROM accounts_user WHERE username = %s", [username]
        )
        row = cursor.fetchone()
    assert row is not None
    return str(row[0])


def code_now(username: str, clock: Clock) -> str:
    """Return the code an authenticator application would show at this moment."""
    key = base64.b32decode(secret_of(username))
    return totp.hotp(key, totp.counter_at(clock.now))


def give_password(client: Client, username: str = LUCY, password: str = PASSWORD) -> HttpResponse:
    return post(client, "/sign-in/", username=username, password=password)


def sign_in_fully(client: Client, clock: Clock, username: str = LUCY) -> HttpResponse:
    """Password, then the code, setting the second factor up on the first occasion."""
    clock.advance(seconds=31)  # a fresh code each time
    first = give_password(client, username)
    assert first.status_code == 302, "password refused"
    if first["Location"] == "/sign-in/set-up/":
        assert get(client, "/sign-in/set-up/").status_code == 200
    return post(client, first["Location"], code=code_now(username, clock))


def log() -> list[tuple[str, str, str]]:
    """Return the access log as (user name, kind, detail), oldest first."""
    with as_owner():
        return [(entry.username, entry.kind, entry.detail) for entry in AccessEntry.objects.all()]


# The two steps


def test_first_sign_in_sets_up_the_second_factor(people: People, clock: Clock) -> None:
    """REQ-008. Password, then the key for the authenticator application, then
    a code; only then is the user signed in."""
    client = Client()
    assert get(client, "/").status_code == 302

    clock.advance(seconds=31)
    first = give_password(client)
    assert (first.status_code, first["Location"]) == (302, "/sign-in/set-up/")
    page = get(client, "/sign-in/set-up/")
    secret = secret_of(LUCY)
    assert " ".join(secret[i : i + 4] for i in range(0, 32, 4)) in page.content.decode()

    done = post(client, "/sign-in/set-up/", code=code_now(LUCY, clock))
    assert (done.status_code, done["Location"]) == (302, "/dashboard/")
    home = get(client, "/")
    assert home.status_code == 200
    body = home.content.decode()
    assert "[Your Organisation]" in body
    assert "Lucy Grant" in body
    assert "Administrator" in body
    assert log() == [
        (LUCY, "Second Factor Set Up", ""),
        (LUCY, "Signed In", ""),
    ]


def test_a_password_alone_signs_nobody_in(people: People, clock: Clock) -> None:
    """REQ-008, threat TH-001, planned test T-SEC-001."""
    client = Client()
    sign_in_fully(client, clock)
    post(client, "/sign-out/")

    assert give_password(client)["Location"] == "/sign-in/code/"
    refused = get(client, "/")
    assert (refused.status_code, refused["Location"]) == (302, "/sign-in/?next=/")
    assert post(client, "/sign-in/code/", code="000000").status_code == 200
    assert get(client, "/").status_code == 302


def test_a_returning_user_gives_a_password_and_a_code(people: People, clock: Clock) -> None:
    """REQ-008. The key is shown once, at set-up, and never again."""
    client = Client()
    sign_in_fully(client, clock)
    post(client, "/sign-out/")

    clock.advance(seconds=31)
    assert give_password(client)["Location"] == "/sign-in/code/"
    assert get(client, "/sign-in/set-up/")["Location"] == "/sign-in/code/"
    assert secret_of(LUCY) not in get(client, "/sign-in/code/").content.decode()
    assert post(client, "/sign-in/code/", code=code_now(LUCY, clock))["Location"] == "/dashboard/"
    assert get(client, "/").status_code == 200


def test_the_code_pages_need_an_accepted_password(people: People, clock: Clock) -> None:
    """REQ-008. And the code must follow the password within 5 minutes."""
    client = Client()
    assert get(client, "/sign-in/code/")["Location"] == "/sign-in/"
    assert get(client, "/sign-in/set-up/")["Location"] == "/sign-in/"
    assert post(client, "/sign-in/code/", code="123456")["Location"] == "/sign-in/"

    sign_in_fully(client, clock)
    post(client, "/sign-out/")
    clock.advance(seconds=31)
    give_password(client)
    clock.advance(minutes=5, seconds=1)
    assert post(client, "/sign-in/code/", code=code_now(LUCY, clock))["Location"] == "/sign-in/"


def test_a_wrong_password_and_an_unknown_name_look_the_same(people: People, clock: Clock) -> None:
    """Threat TH-001. The page says the same thing; the reason is in the access log."""
    client = Client()
    wrong = give_password(client, password=WRONG)
    unknown = give_password(client, username="nobody@nowhere.example")
    assert wrong.status_code == unknown.status_code == 200
    assert "User Name or Password Not Accepted" in wrong.content.decode()
    token = re.compile(r'name="csrfmiddlewaretoken" value="[^"]+"')
    assert token.sub("", wrong.content.decode()) == token.sub("", unknown.content.decode())
    assert log() == [
        (LUCY, "Sign-In Failed", "Wrong Password"),
        ("nobody@nowhere.example", "Sign-In Failed", "Unknown User Name"),
    ]
    with as_owner():
        known, nobody = AccessEntry.objects.all()
    assert (known.organisation_id, known.user_id) == (people.ours.id, people.lucy.id)
    assert (nobody.organisation_id, nobody.user_id) == (None, None)
    assert known.at is not None
    assert known.address == "127.0.0.1"


def test_a_wrong_code_and_a_used_code_are_refused(people: People, clock: Clock) -> None:
    """REQ-008, threat TH-001. A code works once."""
    client = Client()
    sign_in_fully(client, clock)
    used = code_now(LUCY, clock)
    post(client, "/sign-out/")

    give_password(client)
    again = post(client, "/sign-in/code/", code=used)
    assert again.status_code == 200
    assert "Code Not Accepted" in again.content.decode()
    wrong = "111111" if used != "111111" else "222222"
    assert post(client, "/sign-in/code/", code=wrong).status_code == 200

    clock.advance(seconds=30)
    assert post(client, "/sign-in/code/", code=code_now(LUCY, clock))["Location"] == "/dashboard/"
    assert [entry[1:] for entry in log()][-3:] == [
        ("Sign-In Failed", "Wrong Code"),
        ("Sign-In Failed", "Wrong Code"),
        ("Signed In", ""),
    ]


@pytest.mark.parametrize(
    ("username", "logged"),
    [
        (LUCY + "\x00", LUCY + "\N{REPLACEMENT CHARACTER}"),
        ("n" * 300, "n" * 254),
    ],
    ids=["a NUL character", "longer than 254 characters"],
)
def test_a_name_no_user_can_have_is_refused_like_any_unknown_name(
    people: People, clock: Clock, username: str, logged: str
) -> None:
    """Threat TH-001; review of 20 November 2026, finding 7. A server error
    before; now refused as an unknown name, and logged as one."""
    response = give_password(Client(), username=username)
    assert response.status_code == 200
    assert "User Name or Password Not Accepted" in response.content.decode()
    assert log()[-1] == (logged, "Sign-In Failed", "Unknown User Name")


def test_a_code_in_digits_other_than_0_to_9_is_refused(people: People, clock: Clock) -> None:
    """Threat TH-001; review of 20 November 2026, finding 7. Arabic-Indic
    digits gave a server error at the code step; now they are a wrong code."""
    client = Client()
    sign_in_fully(client, clock)
    post(client, "/sign-out/")
    clock.advance(seconds=31)
    give_password(client)
    other_digits = "\u0661\u0662\u0663\u0664\u0665\u0666"
    refused = post(client, "/sign-in/code/", code=other_digits)
    assert refused.status_code == 200
    assert log()[-1] == (LUCY, "Sign-In Failed", "Wrong Code")
    with working_for(people.ours.id, people.lucy.id):
        lucy = User.objects.get(pk=people.lucy.pk)
        assert not sign_in.confirm_code(lucy, other_digits)
    assert totp.matching_counter(secret_of(LUCY), other_digits, clock.now, after=None) is None


def test_a_phone_does_not_change_the_user_name_as_it_is_typed(people: People) -> None:
    """REQ-008. Found on 24 November 2026 on an iPhone: the keyboard made the
    first letter a capital, and the name, which is matched exactly, was
    refused. The field asks for no capital, no correction and no spelling check."""
    page = get(Client(), "/sign-in/").content.decode()
    field = re.search(r'<input id="username"[^>]*>', page)
    assert field is not None
    for attribute in ('autocapitalize="none"', 'autocorrect="off"', 'spellcheck="false"'):
        assert attribute in field.group(0)


def test_five_failures_lock_the_name_for_15_minutes(people: People, clock: Clock) -> None:
    """Threat TH-001, planned test T-SEC-002. The right password is refused
    while the name is locked, and the refusal is logged."""
    client = Client()
    for _ in range(5):
        assert give_password(client, password=WRONG).status_code == 200
    locked = give_password(client)
    assert locked.status_code == 200
    assert "User Name or Password Not Accepted" in locked.content.decode()
    assert log()[-1] == (LUCY, "Sign-In Refused While Locked", "")

    # Another name is not locked.
    assert give_password(client, username=STRANGER).status_code == 302

    clock.advance(minutes=14)
    assert give_password(client).status_code == 200
    clock.advance(minutes=1, seconds=1)
    assert give_password(client).status_code == 302


# The lock as a rule. The access log takes its time from the database clock,
# which the tests cannot move, so failures spread over time are written here.

T0 = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)


def at(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def test_the_lock_lasts_15_minutes_from_the_fifth_failure() -> None:
    """Threat TH-001; review of 20 November 2026, finding 6. Four failures at
    9:00, a fifth at 9:14: locked until 9:29, the fifth plus 15 minutes, not
    until 9:15, when the first leaves the window."""
    failures = [at(0)] * 4 + [at(14)]
    assert sign_in.locks(failures, at(15.5))
    assert sign_in.locks(failures, at(29))
    assert not sign_in.locks(failures, at(29) + timedelta(seconds=1))


def test_five_failures_spread_over_more_than_15_minutes_do_not_lock() -> None:
    """Threat TH-001. 9:00, 9:04, 9:08, 9:12, 9:16: 16 minutes from first to
    fifth. Five exactly 15 minutes apart do lock. Four never do."""
    assert not sign_in.locks([at(4 * n) for n in range(5)], at(16))
    assert sign_in.locks([at(3.75 * n) for n in range(5)], at(15))
    assert not sign_in.locks([at(0)] * 4, at(0))
    assert not sign_in.locks([], at(0))


@given(
    st.lists(st.integers(min_value=0, max_value=3600), max_size=9).map(sorted),
    st.integers(min_value=0, max_value=3600),
)
def test_the_lock_agrees_with_every_five_failures_counted_by_hand(
    seconds: list[int], now: int
) -> None:
    """Threat TH-001. Recounted another way: some five of the failures lie
    within 15 minutes of each other, the latest of them within 15 minutes
    of now and not after it."""
    failures = [T0 + timedelta(seconds=second) for second in seconds]
    moment = T0 + timedelta(seconds=max([now, *seconds]))
    window = timedelta(minutes=15)
    by_hand = any(
        max(five) - min(five) <= window and max(five) >= moment - window
        for five in itertools.combinations(failures, 5)
    )
    assert sign_in.locks(failures, moment) == by_hand


def test_wrong_codes_count_towards_the_lock(people: People, clock: Clock) -> None:
    """Threat TH-001. Guessing the code is limited as guessing the password is."""
    client = Client()
    sign_in_fully(client, clock)
    post(client, "/sign-out/")
    clock.advance(seconds=31)
    give_password(client)
    right = code_now(LUCY, clock)
    wrong = "111111" if right != "111111" else "222222"
    for _ in range(5):
        assert post(client, "/sign-in/code/", code=wrong).status_code == 200
    assert post(client, "/sign-in/code/", code=right).status_code == 200
    assert log()[-1] == (LUCY, "Sign-In Refused While Locked", "")


def test_a_success_clears_earlier_failures(people: People, clock: Clock) -> None:
    """Threat TH-001. Failures are counted since the last sign-in."""
    client = Client()
    for _ in range(4):
        give_password(client, password=WRONG)
    assert sign_in_fully(client, clock)["Location"] == "/dashboard/"
    post(client, "/sign-out/")
    for _ in range(4):
        give_password(client, password=WRONG)
    assert sign_in_fully(client, clock)["Location"] == "/dashboard/"


def test_sign_in_works_with_the_real_password_hasher(
    people: People, clock: Clock, settings: pytest.FixtureRequest
) -> None:
    """The other tests use a fast hasher; this one uses the one in service."""
    # The first hasher in Django's own default list.
    settings.PASSWORD_HASHERS = [  # type: ignore[attr-defined]
        "django.contrib.auth.hashers.PBKDF2PasswordHasher"
    ]
    with working_for(people.ours.id, people.lucy.id):
        people.lucy.set_password(PASSWORD)
        people.lucy.save()
        assert User.objects.get(pk=people.lucy.pk).password.startswith("pbkdf2_sha256$")
    assert sign_in_fully(Client(), clock)["Location"] == "/dashboard/"


# Sessions


def test_the_session_cookie_is_secure_and_changes_at_sign_in(people: People, clock: Clock) -> None:
    """Threat TH-002, planned tests T-SEC-003 and T-SEC-004."""
    client = Client()
    clock.advance(seconds=31)
    give_password(client)
    before = client.cookies[settings.SESSION_COOKIE_NAME].value
    get(client, "/sign-in/set-up/")
    post(client, "/sign-in/set-up/", code=code_now(LUCY, clock))
    cookie = client.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie.value != before
    assert cookie["secure"] is True
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["max-age"] == ""  # ends when the browser closes

    # The key from before sign-in is worth nothing.
    old = Client()
    old.cookies[settings.SESSION_COOKIE_NAME] = before
    assert get(old, "/").status_code == 302


def test_sign_out_ends_the_session_on_the_server(people: People, clock: Clock) -> None:
    """Threat TH-002, planned test T-SEC-004. A copied cookie stops working."""
    client = Client()
    sign_in_fully(client, clock)
    copied = client.cookies[settings.SESSION_COOKIE_NAME].value
    thief = Client()
    thief.cookies[settings.SESSION_COOKIE_NAME] = copied
    assert get(thief, "/").status_code == 200

    assert post(client, "/sign-out/")["Location"] == "/sign-in/"
    assert get(thief, "/").status_code == 302
    assert get(client, "/").status_code == 302
    assert log()[-1] == (LUCY, "Signed Out", "")
    assert get(client, "/sign-out/").status_code == 405


def test_a_session_ends_after_30_minutes_without_a_request(people: People, clock: Clock) -> None:
    """Threat TH-002."""
    client = Client()
    sign_in_fully(client, clock)
    clock.advance(minutes=29)
    assert get(client, "/").status_code == 200
    clock.advance(minutes=30)
    assert get(client, "/").status_code == 200
    clock.advance(minutes=30, seconds=1)
    assert get(client, "/").status_code == 302


def test_a_session_ends_12_hours_after_sign_in_however_busy(people: People, clock: Clock) -> None:
    """Threat TH-002. 28 requests 25 minutes apart reach 11 hours 40 minutes."""
    client = Client()
    sign_in_fully(client, clock)
    for _ in range(28):
        clock.advance(minutes=25)
        assert get(client, "/").status_code == 200
    clock.advance(minutes=25)
    assert get(client, "/").status_code == 302


def test_a_user_made_inactive_is_signed_out_and_cannot_sign_in(
    people: People, clock: Clock
) -> None:
    """REQ-010."""
    client = Client()
    sign_in_fully(client, clock)
    with as_owner(), working_for(people.ours.id):
        User.objects.filter(pk=people.lucy.pk).update(is_active=False)
    assert get(client, "/").status_code == 302
    assert give_password(Client()).status_code == 200
    assert log()[-1] == (LUCY, "Sign-In Failed", "Inactive User")


def sessions_of(user: User) -> int:
    """Return how many stored sessions name ``user``."""
    with as_owner():
        return sum(
            1
            for session in Session.objects.all()
            if session.get_decoded().get("_auth_user_id") == str(user.pk)
        )


def test_a_user_made_inactive_has_their_sessions_ended_not_suspended(
    people: People, clock: Clock
) -> None:
    """REQ-010; review of 20 November 2026, finding 2. The session is gone
    at the next request, and the browser keeping it busy does not keep it.
    Made active again, the same browser is not signed in."""
    client = Client()
    sign_in_fully(client, clock)
    with working_for(people.ours.id, people.lucy.id):
        other = users.add_user(
            organisation=people.ours,
            username="name@your-organisation.example",
            full_name="[Second Administrator]",
            roles=[Role.ADMINISTRATOR],
            password=secrets.token_urlsafe(18),
        )
    with working_for(people.ours.id, other.id):
        users.set_active(User.objects.get(pk=people.lucy.pk), active=False, by=other)
    assert get(client, "/").status_code == 302
    assert sessions_of(people.lucy) == 0
    clock.advance(minutes=25)
    assert get(client, "/").status_code == 302

    with working_for(people.ours.id, other.id):
        users.set_active(User.objects.get(pk=people.lucy.pk), active=True, by=other)
    assert get(client, "/").status_code == 302


def test_made_active_again_before_any_request_the_old_session_is_still_ended(
    people: People, clock: Clock
) -> None:
    """REQ-010; review of 20 November 2026, finding 2. Being made inactive
    ends the sessions at once, whether or not the browser asks in between."""
    client = Client()
    sign_in_fully(client, clock)
    with working_for(people.ours.id, people.lucy.id):
        other = users.add_user(
            organisation=people.ours,
            username="name@your-organisation.example",
            full_name="[Second Administrator]",
            roles=[Role.ADMINISTRATOR],
            password=secrets.token_urlsafe(18),
        )
    with working_for(people.ours.id, other.id):
        users.set_active(User.objects.get(pk=people.lucy.pk), active=False, by=other)
        users.set_active(User.objects.get(pk=people.lucy.pk), active=True, by=other)
    assert get(client, "/").status_code == 302


def test_changing_the_password_ends_other_sessions(people: People, clock: Clock) -> None:
    """Threat TH-002. A session made with the old password is refused."""
    client = Client()
    sign_in_fully(client, clock)
    with working_for(people.ours.id, people.lucy.id):
        lucy = User.objects.get(pk=people.lucy.pk)
        lucy.set_password(secrets.token_urlsafe(18))
        lucy.save()
    assert get(client, "/").status_code == 302


def test_a_session_cannot_be_pointed_at_another_organisation(people: People, clock: Clock) -> None:
    """REQ-003, threat TH-020. Each user lands in their own organisation, and a
    session altered to name another organisation resolves to nobody."""
    ours, theirs = Client(), Client()
    sign_in_fully(ours, clock)
    sign_in_fully(theirs, clock, STRANGER)
    assert "[Your Organisation]" in get(ours, "/").content.decode()
    page = get(theirs, "/").content.decode()
    assert "[Other Organisation]" in page
    assert "[Your Organisation]" not in page

    session = ours.session
    session["organisation"] = str(people.other.id)
    session.save()
    assert get(ours, "/").status_code == 302


def test_a_forged_request_is_refused(people: People, clock: Clock) -> None:
    """Threat TH-003, planned test T-SEC-005. A write with no token from the page."""
    client = Client(enforce_csrf_checks=True)
    assert give_password(client).status_code == 403
    assert post(client, "/sign-out/").status_code == 403
    assert log() == []


# Refused actions


def test_a_refused_action_is_refused_and_logged(people: People, clock: Clock) -> None:
    """REQ-006, REQ-009, threat TH-008. A user with no role may not even view."""
    client = Client()
    sign_in_fully(client, clock)
    with working_for(people.ours.id, people.lucy.id):
        User.objects.filter(pk=people.lucy.pk).update(roles=[])
    assert get(client, "/").status_code == 403
    assert log()[-1] == (LUCY, "Action Refused", "View Records")

    with working_for(people.ours.id, people.lucy.id):
        User.objects.filter(pk=people.lucy.pk).update(roles=[Role.READ_ONLY])
    assert get(client, "/").status_code == 200


# What the database allows during sign-in, and the access log


def test_checking_a_name_shows_that_user_and_no_other(people: People) -> None:
    """Threat TH-020. Before an organisation is known the application can read
    the one user whose name is being checked, and can change nobody."""
    assert User.objects.count() == 0
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [SIGNING_IN_SETTING, LUCY])
        assert [user.username for user in User.objects.all()] == [LUCY]
        assert Organisation.objects.count() == 0
        assert Event.objects.count() == 0
        assert User.objects.update(full_name="Changed") == 0
        cursor.execute("SELECT set_config(%s, '', true)", [SIGNING_IN_SETTING])
    assert User.objects.count() == 0


def test_the_access_log_is_seen_by_its_own_organisation_only(people: People, clock: Clock) -> None:
    """REQ-003, REQ-009."""
    sign_in_fully(Client(), clock)
    sign_in_fully(Client(), clock, STRANGER)
    give_password(Client(), username="nobody@nowhere.example")
    assert AccessEntry.objects.count() == 0
    with working_for(people.ours.id, people.lucy.id):
        assert {entry.username for entry in AccessEntry.objects.all()} == {LUCY}
    with working_for(people.other.id, people.stranger.id):
        assert {entry.username for entry in AccessEntry.objects.all()} == {STRANGER}
        with pytest.raises(DatabaseError, match="row-level security"), transaction.atomic():
            AccessEntry.objects.create(
                organisation=people.ours, username=LUCY, kind=AccessKind.SIGNED_IN
            )
    assert len(log()) == 5


def test_the_access_log_is_never_changed_or_removed(people: People, clock: Clock) -> None:
    """REQ-009, REQ-131. Refused for the application and for the owner."""
    sign_in_fully(Client(), clock)
    statements = (
        "UPDATE accounts_accessentry SET detail = 'Changed'",
        "DELETE FROM accounts_accessentry",
        "TRUNCATE accounts_accessentry",
    )
    with working_for(people.ours.id, people.lucy.id):
        entry = AccessEntry.objects.first()
        assert entry is not None
        with pytest.raises(RecordsAreNeverDeletedError):
            entry.save()
        with pytest.raises(RecordsAreNeverDeletedError):
            entry.delete()
        with pytest.raises(RecordsAreNeverDeletedError):
            AccessEntry.objects.all().delete()
        for statement in statements:
            with (
                pytest.raises(DatabaseError, match="permission denied"),
                transaction.atomic(),
                connection.cursor() as cursor,
            ):
                cursor.execute(statement)
    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        for statement in statements:
            with (
                pytest.raises(DatabaseError, match="never changed in place or deleted"),
                transaction.atomic(),
                connection.cursor() as cursor,
            ):
                cursor.execute(statement)
    assert len(log()) == 2


def test_the_authenticator_key_is_never_written_to_the_history(
    people: People, clock: Clock
) -> None:
    """Threat TH-001. That it was set is recorded; its value is not."""
    sign_in_fully(Client(), clock)
    secret = secret_of(LUCY)
    with working_for(people.ours.id, people.lucy.id):
        entries = list(Event.of(people.lucy))
    assert [entry.changed for entry in entries] == [
        [],
        ["first_password_set_on", "password_must_change"],  # the fixture, not a sign-in
        ["second_factor_secret"],
        ["second_factor_confirmed"],
    ]
    assert all(entry.actor_name in ("Lucy Grant",) for entry in entries[2:])
    for entry in entries:
        for text in (entry.before_json, entry.after_json):
            assert text is None or (secret not in text and "second_factor_secret" not in text)


# Setting up an organisation from the command line


def test_an_organisation_is_set_up_from_the_command_line(
    monkeypatch: pytest.MonkeyPatch, clock: Clock
) -> None:
    """REQ-004. Run by the owner of the tables; the password is typed at a prompt."""
    answers = iter(
        [
            "[Your Organisation]",
            "UK.CAO.[Number]",
            "[Organisation Address]",
            "Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            "Yes",
            "Yes",
            "Yes",
            "No",
            "Lucy Grant",
            LUCY,
        ]
    )
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt: PASSWORD)
    with as_owner():
        call_command("set_up_organisation")
        organisation = Organisation.objects.get()
    assert organisation.address == "[Organisation Address]"
    assert organisation.privileges == [
        "Maintenance",
        "Continuing Airworthiness Management",
        "Airworthiness Review",
    ]
    assert sign_in_fully(Client(), clock)["Location"] == "/dashboard/"


def test_a_weak_password_is_refused_at_set_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Threat TH-001. At least 12 characters, and not a common password."""
    answers = iter(["[Your Organisation]", "UK.CAO.[Number]", "[Organisation Address]", "Scope"])
    answers = iter([*answers, "Yes", "No", "No", "No", "Lucy Grant", LUCY])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    monkeypatch.setattr("getpass.getpass", lambda prompt: "password")
    with as_owner(), pytest.raises(CommandError, match="too short"):
        call_command("set_up_organisation")
    with as_owner():
        assert Organisation.objects.count() == 0
