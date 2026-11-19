"""The Users page and the change of password (REQ-005 to REQ-010; threats TH-001, TH-002, TH-008).

The people are those of design-system/SampleData.md. Passwords are made
afresh for each run.
"""

import html
import re
import secrets
import uuid
from datetime import UTC, datetime, time, timedelta

import pytest
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts import sign_in, users
from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.accounts.roles import Action, Role, permitted
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.interface.formatting import long_date
from airworthiness_rules.dates import uk_today
from tests.conftest import as_owner
from tests.support import Sample, make_sample, signed_in
from tests.test_sign_in import Clock, code_now, get, give_password, post

pytestmark = pytest.mark.django_db

FIRST = secrets.token_urlsafe(18)
SECOND = secrets.token_urlsafe(18)
THIRD = secrets.token_urlsafe(18)
FOURTH = secrets.token_urlsafe(18)
NEW = "new.person@your-organisation.example"
# Two passwords the rules refuse: one too short, one on the list of common passwords.
WEAK = "short"
COMMON = "pass" + "word12345"


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    moving = Clock()
    monkeypatch.setattr(sign_in, "current_time", moving.read)
    return moving


@pytest.fixture
def sample() -> Sample:
    return make_sample()


@pytest.fixture
def new_user(sample: Sample) -> User:
    """A user added by the Administrator with a first password."""
    with working_for(sample.ours.id, sample.administrator.id):
        return users.add_user(
            organisation=sample.ours,
            username=NEW,
            full_name="[New Person]",
            roles=[Role.PLANNING_AND_RECORDS],
            password=FIRST,
        )


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def sign_in_with(client: Client, clock: Clock, username: str, password: str) -> HttpResponse:
    """Password, then the code, setting the second factor up on the first occasion."""
    clock.advance(seconds=31)
    first = give_password(client, username, password)
    assert first.status_code == 302, "password refused"
    if first["Location"] == "/sign-in/set-up/":
        assert get(client, "/sign-in/set-up/").status_code == 200
    return post(client, first["Location"], code=code_now(username, clock))


def shown_password(response: HttpResponse) -> str:
    """Return the first password a page shows, once, after it is made."""
    found = re.search(r"Shown Once: <code>([^<]+)</code>", response.content.decode())
    assert found is not None
    return html.unescape(found.group(1))


def log_of(user: User) -> list[tuple[str, str]]:
    with as_owner():
        return [(entry.kind, entry.detail) for entry in AccessEntry.objects.filter(user_id=user.pk)]


# Adding a user


def test_the_administrator_adds_a_user_with_roles_and_a_first_password(
    sample: Sample, clock: Clock
) -> None:
    """REQ-005, REQ-007. The addition is in the history, and the password is not."""
    administrator = signed_in(sample.administrator)
    response = post(
        administrator,
        "/users/add/",
        full_name="[New Person]",
        username=NEW,
        roles="Planning and Records",
    )
    assert response.status_code == 200
    # The system makes the first password and shows it once, on this page only.
    given = shown_password(response)
    assert len(given) >= 12
    assert "First Password for [New Person], Shown Once" in response.content.decode()
    given_on = uk_today(clock.now)
    until = long_date(given_on + timedelta(days=7))
    assert f"To Be Changed by {until}" in response.content.decode()
    with working_for(sample.ours.id, sample.administrator.id):
        person = User.objects.get(username=NEW)
        assert person.roles == ["Planning and Records"]
        assert person.organisation_id == sample.ours.id
        assert person.password_must_change
        assert person.check_password(given)
        assert person.first_password_set_on == given_on
        created = Event.of(person).get()
        assert created.actor_id == sample.administrator.id
        assert "password" not in (created.after_json or "").replace(
            "password_must_change", ""
        ).replace("first_password_set_on", "")
        assert given not in (created.after_json or "")
    body = page(administrator, "/users/")
    assert "<td>[New Person]</td>" in body
    assert "<td>Active, Password to Be Changed</td>" in body
    assert "<td>Not Set Up</td>" in body
    assert FIRST not in body


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"username": "not an address"}, "Give a Full Name and a User Name That Is an Email"),
        ({"full_name": ""}, "Give a Full Name"),
        ({"roles": "Owner"}, "Give a Full Name"),
        # Taken in this organisation, and taken in another: the same answer (TH-001).
        ({"username": "lucy.grant@your-organisation.example"}, "This User Name Cannot Be Used"),
        ({"username": "name@other-organisation.example"}, "This User Name Cannot Be Used"),
    ],
)
def test_a_user_who_cannot_be_added_is_refused_with_the_reason(
    sample: Sample, values: dict[str, str], message: str
) -> None:
    """REQ-005, threat TH-001."""
    administrator = signed_in(sample.administrator)
    given = {
        "full_name": "[New Person]",
        "username": NEW,
        "roles": "Read Only",
    } | values
    response = post(administrator, "/users/add/", **given)
    assert response.status_code == 200
    assert message in response.content.decode()
    assert "Shown Once" not in response.content.decode()
    with as_owner():
        assert not User.objects.filter(full_name="[New Person]").exists()


def test_a_password_the_rules_refuse_is_refused_wherever_it_is_set(
    sample: Sample, new_user: User
) -> None:
    """Threat TH-001. Too short, or a common password, by the service and at a change."""
    with working_for(sample.ours.id, sample.administrator.id):
        for password, message in ((WEAK, "too short"), (COMMON, "too common")):
            with pytest.raises(users.RefusedError, match=message):
                users.add_user(
                    organisation=sample.ours,
                    username="another@your-organisation.example",
                    full_name="[Another Person]",
                    roles=[],
                    password=password,
                )
            with pytest.raises(users.RefusedError, match=message):
                users.reset_password(new_user, password=password, by=sample.administrator)
        # A first password the system makes always passes the rules.
        for _ in range(20):
            users.reset_password(
                new_user, password=users.new_first_password(new_user), by=sample.administrator
            )


# The first password


def test_a_first_password_is_changed_before_anything_else(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """REQ-008, threat TH-001. Every page sends the user to change it, and nothing is done."""
    client = Client()
    assert sign_in_with(client, clock, NEW, FIRST).status_code == 302
    for path in ("/", "/reviews/", "/records-export/"):
        response = get(client, path)
        assert (response.status_code, response["Location"]) == (302, "/account/password/")
    response = post(client, "/problem-log/add/", problem="[Problem]")
    assert (response.status_code, response["Location"]) == (302, "/account/password/")
    assert "changed before anything else" in page(client, "/account/password/")

    refusals = [
        ({"current": SECOND, "new": SECOND, "again": SECOND}, "The Current Password Is Not Right"),
        ({"current": FIRST, "new": SECOND, "again": THIRD}, "The Two New Passwords Differ"),
        ({"current": FIRST, "new": FIRST, "again": FIRST}, "The New Password Is the Same"),
        ({"current": FIRST, "new": WEAK, "again": WEAK}, "This password is too short"),
        ({"current": FIRST, "new": SECOND}, "Give the Current Password and the New Password"),
    ]
    for values, message in refusals:
        assert message in post(client, "/account/password/", **values).content.decode()
    done = post(client, "/account/password/", current=FIRST, new=SECOND, again=SECOND)
    assert (done.status_code, done["Location"]) == (302, "/")
    # This session continues, and the pages now answer.
    assert get(client, "/").status_code == 200
    assert post(client, "/problem-log/add/", problem="[Problem]").status_code == 302
    assert ("Password Changed", "") in log_of(new_user)
    # The first password no longer signs in; the new one does.
    clock.advance(seconds=31)
    assert give_password(Client(), NEW, FIRST).status_code == 200
    assert sign_in_with(Client(), clock, NEW, SECOND)["Location"] == "/"


def test_changing_a_password_ends_the_users_other_sessions(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """Threat TH-002. The session that made the change continues; any other ends."""
    here, elsewhere = Client(), Client()
    sign_in_with(here, clock, NEW, FIRST)
    sign_in_with(elsewhere, clock, NEW, FIRST)
    post(here, "/account/password/", current=FIRST, new=SECOND, again=SECOND)
    assert get(here, "/").status_code == 200
    response = get(elsewhere, "/")
    assert (response.status_code, response["Location"][:9]) == (302, "/sign-in/")


def test_every_role_can_change_its_own_password(sample: Sample) -> None:
    """REQ-008. The page needs sign-in and no role."""
    for user in sample.by_role().values():
        assert "<h1>Change Password</h1>" in page(signed_in(user), "/account/password/")
    response = get(Client(), "/account/password/")
    assert (response.status_code, response["Location"][:9]) == (302, "/sign-in/")


def test_a_first_password_stops_working_after_7_days(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """OWASP ASVS 5.0, 6.4.1. Good on the seventh day after it is given, refused on the eighth."""
    assert new_user.first_password_set_on is not None
    seventh = new_user.first_password_set_on + timedelta(days=7)
    # Noon in Coordinated Universal Time is the same date in the United Kingdom.
    clock.now = datetime.combine(seventh, time(12), tzinfo=UTC)
    assert give_password(Client(), NEW, FIRST).status_code == 302
    clock.now = datetime.combine(seventh + timedelta(days=1), time(12), tzinfo=UTC)
    refused = give_password(Client(), NEW, FIRST)
    assert refused.status_code == 200
    assert "User Name or Password Not Accepted" in refused.content.decode()
    assert ("Sign-In Failed", "First Password Expired") in log_of(new_user)
    # A new one from the Administrator works again, for 7 days from that day.
    with working_for(sample.ours.id, sample.administrator.id):
        users.reset_password(new_user, password=THIRD, by=sample.administrator)
    assert give_password(Client(), NEW, THIRD).status_code == 302
    # A password the user has chosen never expires.
    client = Client()
    sign_in_with(client, clock, NEW, THIRD)
    post(client, "/account/password/", current=THIRD, new=SECOND, again=SECOND)
    clock.advance(days=400)
    assert give_password(Client(), NEW, SECOND).status_code == 302


def test_a_change_of_password_needs_a_code_unless_just_signed_in(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """OWASP ASVS 5.0, 7.5.1; threat TH-002. A session left open is not enough to
    change the password: after 5 minutes the authenticator is asked for again."""
    client = Client()
    sign_in_with(client, clock, NEW, FIRST)
    assert 'name="code"' not in page(client, "/account/password/")
    post(client, "/account/password/", current=FIRST, new=SECOND, again=SECOND)
    clock.advance(minutes=6)
    assert 'name="code"' in page(client, "/account/password/")
    change = {"current": SECOND, "new": THIRD, "again": THIRD}
    for code in ("", "000000"):
        refused = post(client, "/account/password/", **change, code=code)
        assert (
            "The Code From Your Authenticator Application Is Not Right" in refused.content.decode()
        )
    assert ("Sign-In Failed", "Wrong Code at a Change of Password") in log_of(new_user)
    # A refusal for another reason does not use the code up.
    code = code_now(NEW, clock)
    weak = post(client, "/account/password/", current=SECOND, new=WEAK, again=WEAK, code=code)
    assert "too short" in weak.content.decode()
    done = post(client, "/account/password/", **change, code=code)
    assert (done.status_code, done["Location"]) == (302, "/")
    assert ("Code Accepted", "") in log_of(new_user)
    # The code that was used cannot be used again, here or to sign in.
    again = post(client, "/account/password/", current=THIRD, new=FOURTH, again=FOURTH, code=code)
    assert "Is Not Right" in again.content.decode()
    other = Client()
    assert give_password(other, NEW, THIRD).status_code == 302
    assert post(other, "/sign-in/code/", code=code).status_code == 200
    # The next code works.
    clock.advance(seconds=31)
    later = post(
        client,
        "/account/password/",
        current=THIRD,
        new=FOURTH,
        again=FOURTH,
        code=code_now(NEW, clock),
    )
    assert later.status_code == 302


# The user's own sessions (OWASP ASVS 5.0, 7.5.2)


def ends(body: str) -> list[str]:
    """Return the identifier of each session the page offers to end."""
    return re.findall(r'action="/account/sessions/([0-9a-f-]{36})/end/"', body)


def test_a_user_sees_their_sessions_and_ends_one(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """OWASP ASVS 5.0, 7.5.2; threat TH-002. Each session is shown with when it
    began, when it was last used, where from and in what; this one is marked
    and cannot be ended from the list. Only the user's own are shown or ended."""
    here = Client(HTTP_USER_AGENT="[Browser Here]", REMOTE_ADDR="192.0.2.1")
    elsewhere = Client(HTTP_USER_AGENT="[Browser Elsewhere]", REMOTE_ADDR="192.0.2.7")
    sign_in_with(here, clock, NEW, FIRST)
    post(here, "/account/password/", current=FIRST, new=SECOND, again=SECOND)
    sign_in_with(elsewhere, clock, NEW, SECOND)
    planner = signed_in(sample.planner)

    body = page(here, "/account/password/")
    assert body.count("<td>This Session</td>") == 1
    for text in ("[Browser Here]", "[Browser Elsewhere]", "192.0.2.1", "192.0.2.7"):
        assert text in body, text
    (other,) = ends(body)
    # Nobody else is shown it, or can end it; and a session that is not there is not found.
    assert other not in page(planner, "/account/password/")
    assert post(planner, f"/account/sessions/{other}/end/").status_code == 404
    assert post(here, f"/account/sessions/{uuid.uuid4()}/end/").status_code == 404
    assert get(elsewhere, "/").status_code == 200

    ended = post(here, f"/account/sessions/{other}/end/")
    assert (ended.status_code, ended["Location"]) == (302, "/account/password/")
    assert get(elsewhere, "/")["Location"].startswith("/sign-in/")
    assert get(here, "/").status_code == 200
    assert ends(page(here, "/account/password/")) == []
    assert ("Sessions Ended", "One Session, by [New Person]") in log_of(new_user)


def test_ending_a_session_needs_a_code_unless_just_signed_in(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """OWASP ASVS 5.0, 7.5.2: having authenticated again with at least one
    factor. More than 5 minutes after sign-in a code is asked for, to end one
    session or every other."""
    here, elsewhere, third = Client(), Client(), Client()
    sign_in_with(here, clock, NEW, FIRST)
    post(here, "/account/password/", current=FIRST, new=SECOND, again=SECOND)
    sign_in_with(elsewhere, clock, NEW, SECOND)
    sign_in_with(third, clock, NEW, SECOND)
    clock.advance(minutes=6)
    one, _ = ends(page(here, "/account/password/"))
    for path, what in (
        (f"/account/sessions/{one}/end/", "End a Session"),
        ("/account/sessions/", "Sign Out Everywhere Else"),
    ):
        asked = post(here, path)
        assert asked.status_code == 200
        assert f"<h1>{what}</h1>" in asked.content.decode()
        assert "Is Not Right" in post(here, path, code="000000").content.decode()
        assert len(ends(page(here, "/account/password/"))) == (2 if "end/" in path else 1)
        clock.advance(seconds=31)
        done = post(here, path, code=code_now(NEW, clock))
        assert (done.status_code, done["Location"]) == (302, "/account/password/")
    assert ends(page(here, "/account/password/")) == []
    assert get(here, "/").status_code == 200
    for gone in (elsewhere, third):
        assert get(gone, "/")["Location"].startswith("/sign-in/")


# Roles and leaving


def test_roles_are_set_by_the_administrator_and_the_change_is_in_the_history(
    sample: Sample, new_user: User
) -> None:
    """REQ-006, REQ-007."""
    administrator = signed_in(sample.administrator)
    address = f"/users/{new_user.id}/roles/"
    key = f"{new_user.id}-roles"
    response = administrator.post(
        address, {key: ["Read Only", "Planning and Records"]}, secure=True
    )
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.administrator.id):
        person = User.objects.get(pk=new_user.pk)
        # Stored in the order of the matrix, whatever order they were ticked in.
        assert person.roles == ["Planning and Records", "Read Only"]
        last = Event.of(person).order_by("-sequence")[0]
        assert (last.changed, last.actor_id) == (["roles"], sample.administrator.id)
    refused = administrator.post(address, {key: ["Owner"]}, secure=True)
    assert "A Role Is One of the Five Roles" in refused.content.decode()
    # No role at all is allowed: the user can then do nothing.
    administrator.post(address, {}, secure=True)
    with working_for(sample.ours.id, sample.administrator.id):
        person = User.objects.get(pk=new_user.pk)
        assert person.roles == []
        assert not any(permitted(person.roles, action) for action in Action)


def test_an_organisation_always_has_an_active_administrator(sample: Sample, new_user: User) -> None:
    """REQ-005. The last Administrator cannot lose the role or be made inactive."""
    administrator = signed_in(sample.administrator)
    own = sample.administrator.id
    lost = administrator.post(f"/users/{own}/roles/", {f"{own}-roles": ["Read Only"]}, secure=True)
    assert "An Organisation Always Has an Active Administrator" in lost.content.decode()
    gone = post(administrator, f"/users/{own}/active/", active="no")
    assert "A User Does Not Make Themselves Inactive" in gone.content.decode()
    # With a second Administrator, the first may give the role up.
    key = f"{new_user.id}-roles"
    administrator.post(f"/users/{new_user.id}/roles/", {key: ["Administrator"]}, secure=True)
    with working_for(sample.ours.id, sample.administrator.id):
        with pytest.raises(users.RefusedError, match="Always Has an Active Administrator"):
            # An inactive Administrator does not count.
            User.objects.filter(pk=new_user.pk).update(is_active=False)
            users.set_roles(User.objects.get(pk=own), [Role.READ_ONLY])
        User.objects.filter(pk=new_user.pk).update(is_active=True)
    done = administrator.post(f"/users/{own}/roles/", {f"{own}-roles": ["Read Only"]}, secure=True)
    assert done.status_code == 302
    # No longer an Administrator: the page now refuses.
    assert get(administrator, "/users/").status_code == 403


def test_a_user_made_inactive_is_signed_out_and_stays_in_the_record(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """REQ-010. Nothing is deleted; the user can be made active again."""
    client = Client()
    sign_in_with(client, clock, NEW, FIRST)
    administrator = signed_in(sample.administrator)
    assert post(administrator, f"/users/{new_user.id}/active/", active="no").status_code == 302
    response = get(client, "/account/password/")
    assert (response.status_code, response["Location"][:9]) == (302, "/sign-in/")
    clock.advance(seconds=31)
    assert give_password(Client(), NEW, FIRST).status_code == 200
    assert "<td>Inactive, Password to Be Changed</td>" in page(administrator, "/users/")
    post(administrator, f"/users/{new_user.id}/active/", active="yes")
    assert sign_in_with(Client(), clock, NEW, FIRST).status_code == 302


# Lost passwords and lost authenticators


def test_the_administrator_sets_a_new_first_password(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """REQ-008, threat TH-002. The user's sessions end, and the new password is changed first."""
    client = Client()
    sign_in_with(client, clock, NEW, FIRST)
    post(client, "/account/password/", current=FIRST, new=SECOND, again=SECOND)
    administrator = signed_in(sample.administrator)
    # Anything typed by the Administrator is ignored: the system makes the password.
    made = post(administrator, f"/users/{new_user.id}/password/", password=WEAK)
    assert made.status_code == 200
    third = shown_password(made)
    assert third not in (WEAK, FIRST, SECOND)
    assert "First Password for [New Person], Shown Once" in made.content.decode()
    assert third not in page(administrator, "/users/")  # shown once
    response = get(client, "/")
    assert (response.status_code, response["Location"][:9]) == (302, "/sign-in/")
    again = Client()
    assert sign_in_with(again, clock, NEW, third).status_code == 302
    assert get(again, "/")["Location"] == "/account/password/"
    assert ("Password Set by an Administrator", "By [Accountable Manager]") in log_of(new_user)
    with working_for(sample.ours.id, sample.administrator.id):
        last = Event.of(new_user).order_by("-sequence")[0]
        assert "password" in last.changed
        assert third not in (last.after_json or "")


def test_the_administrator_resets_a_lost_second_factor(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """REQ-008. The user sets a second factor up again at their next sign-in."""
    signed_before = Client()
    sign_in_with(signed_before, clock, NEW, FIRST)
    administrator = signed_in(sample.administrator)
    assert "<td>Set Up</td>" in page(administrator, "/users/")
    assert post(administrator, f"/users/{new_user.id}/second-factor/").status_code == 302
    # The session made with the old second factor has ended.
    assert get(signed_before, "/")["Location"].startswith("/sign-in/")
    clock.advance(seconds=31)
    first = give_password(Client(), NEW, FIRST)
    assert first["Location"] == "/sign-in/set-up/"
    assert ("Second Factor Reset", "By [Accountable Manager]") in log_of(new_user)


def test_the_administrator_gives_a_code_to_change_how_another_signs_in(
    sample: Sample, new_user: User, clock: Clock
) -> None:
    """OWASP ASVS 5.0, 7.5.1; threat TH-002. An Administrator's session left open
    cannot be used to take over another user's sign-in."""
    name = "second.administrator@your-organisation.example"
    with working_for(sample.ours.id, sample.administrator.id):
        second = users.add_user(
            organisation=sample.ours,
            username=name,
            full_name="[Second Administrator]",
            roles=[Role.ADMINISTRATOR],
            password=FOURTH,
        )
    administrator = Client()
    sign_in_with(administrator, clock, name, FOURTH)
    post(administrator, "/account/password/", current=FOURTH, new=THIRD, again=THIRD)
    clock.advance(minutes=6)
    for path, what, at, logged in (
        (
            "password",
            "Give [New Person] a New First Password",
            "a New First Password",
            "Password Set by an Administrator",
        ),
        (
            "second-factor",
            "Reset Second Factor of [New Person]",
            "a Reset of a Second Factor",
            "Second Factor Reset",
        ),
    ):
        address = f"/users/{new_user.id}/{path}/"
        asked = post(administrator, address)
        assert asked.status_code == 200
        assert f"<h1>{what}</h1>" in asked.content.decode()
        assert "Shown Once" not in asked.content.decode()
        wrong = post(administrator, address, code="000000")
        assert "Is Not Right" in wrong.content.decode()
        assert ("Sign-In Failed", f"Wrong Code at {at}") in log_of(second)
        assert logged not in [kind for kind, _ in log_of(new_user)]
        clock.advance(seconds=31)
        done = post(administrator, address, code=code_now(name, clock))
        assert "Is Not Right" not in done.content.decode()
        assert logged in [kind for kind, _ in log_of(new_user)]
    with as_owner():
        new_user.refresh_from_db()
    assert not new_user.check_password(FIRST)


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)


def addresses(user: User):  # type: ignore[no-untyped-def]
    manage = Action.MANAGE_USERS_AND_ROLES
    return [
        ("GET", "/users/", manage),
        ("POST", "/users/add/", manage),
        ("POST", f"/users/{user.id}/roles/", manage),
        ("POST", f"/users/{user.id}/active/", manage),
        ("POST", f"/users/{user.id}/password/", manage),
        ("POST", f"/users/{user.id}/second-factor/", manage),
    ]


def call(client: Client, method: str, path: str) -> HttpResponse:
    return get(client, path) if method == "GET" else post(client, path)


def test_another_organisations_users_are_not_shown_or_changed(
    sample: Sample, new_user: User
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. The stranger is an Administrator."""
    stranger = signed_in(sample.stranger)
    body = page(stranger, "/users/")
    assert "[New Person]" not in body
    assert "Lucy Grant" not in body
    for method, path, _ in addresses(new_user)[2:]:
        assert call(stranger, method, path).status_code == 404, path
    with as_owner():
        person = User.objects.get(pk=new_user.pk)
        assert (person.is_active, person.roles) == (True, ["Planning and Records"])


@pytest.mark.parametrize(
    "role",
    [
        "Continuing Airworthiness Manager",
        "Airworthiness Review Staff",
        "Planning and Records",
        "Read Only",
    ],
)
def test_only_the_administrator_manages_users(sample: Sample, new_user: User, role: str) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    for method, path, _ in addresses(new_user):
        assert call(client, method, path).status_code == 403, f"{role} {method} {path}"
    with working_for(sample.ours.id, user.id):
        assert AccessEntry.objects.filter(user=user, kind="Action Refused").count() == 6


def test_the_users_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, new_user: User
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    anonymous = Client()
    for method, path, _ in addresses(new_user):
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.administrator, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in [*addresses(new_user), ("POST", "/account/password/", None)]:
        if method == "POST":
            assert post(forged, path).status_code == 403, path
