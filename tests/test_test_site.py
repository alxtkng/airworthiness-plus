"""The test site: the owner's work done at start, then the service as its own role.

operations/test-site.md, ADR-0003. The test site holds the sample
organisation and nothing else. These tests hold it to that, and hold the
running service to the rule of the server: it never has the owner's
credentials (ADR-0002, threat TH-024).
"""

import io
import json
import os
import re
import secrets
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext

from airworthiness_plus.accounts import sign_in, users
from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import APPLICATION_ROLE, SIGNING_IN_SETTING
from airworthiness_plus.logistics.models import Supplier
from airworthiness_plus.sample import second, suppliers, test_site
from airworthiness_plus.sample.management.commands import prepare_test_site
from airworthiness_plus.sample.management.commands.seed_sample_organisation import ADMINISTRATOR
from tests.conftest import as_owner

ROOT = Path(__file__).resolve().parent.parent
ROLE = "airworthiness_test_site_check"
PASSWORD = secrets.token_urlsafe(24)
FIRST_PASSWORD = secrets.token_urlsafe(24)
SECOND_PASSWORD = secrets.token_urlsafe(24)
OWNERS, SERVICES, FIRST = (secrets.token_urlsafe(12) for _ in range(3))

HOSTED = {
    "AIRWORTHINESS_DATABASE_NAME": "airworthiness",
    "AIRWORTHINESS_DATABASE_USER": "airworthiness_service",
    "AIRWORTHINESS_DATABASE_PASSWORD": SERVICES,
    test_site.OWNER_USER: "airworthiness_owner",
    test_site.OWNER_PASSWORD: OWNERS,
    test_site.ADMINISTRATOR_PASSWORD: FIRST,
    "RENDER_EXTERNAL_HOSTNAME": "airworthiness-plus-test.onrender.com",
}


# The environment each program is given


def test_the_owners_work_is_given_the_owners_credentials_and_the_role_to_make() -> None:
    owner = test_site.owner_environment(HOSTED)
    assert owner["AIRWORTHINESS_DATABASE_USER"] == "airworthiness_owner"
    assert owner["AIRWORTHINESS_DATABASE_PASSWORD"] == OWNERS
    assert owner["AIRWORTHINESS_DATABASE_OWNER_WORK"] == "true"
    assert owner[test_site.SERVICE_USER] == "airworthiness_service"
    assert owner[test_site.SERVICE_PASSWORD] == SERVICES
    assert owner["AIRWORTHINESS_DATABASE_NAME"] == "airworthiness"


def test_the_running_service_is_given_nothing_of_the_owners() -> None:
    """ADR-0002, threat TH-024: the application never holds the owner's credentials."""
    service = test_site.service_environment({**HOSTED, "AIRWORTHINESS_DATABASE_OWNER_WORK": "true"})
    assert service["AIRWORTHINESS_DATABASE_USER"] == "airworthiness_service"
    assert service["AIRWORTHINESS_DATABASE_PASSWORD"] == SERVICES
    assert "AIRWORTHINESS_DATABASE_OWNER_WORK" not in service
    assert not [name for name in service if name.startswith(test_site.PREFIX)]
    kept = " ".join(service.values())
    assert OWNERS not in kept and FIRST not in kept


def test_the_service_answers_to_the_name_the_host_gave_unless_one_is_set() -> None:
    service = test_site.service_environment(HOSTED)
    assert service["AIRWORTHINESS_ALLOWED_HOSTS"] == "airworthiness-plus-test.onrender.com"
    named = {**HOSTED, "AIRWORTHINESS_ALLOWED_HOSTS": "test.example"}
    assert test_site.service_environment(named)["AIRWORTHINESS_ALLOWED_HOSTS"] == "test.example"


@pytest.mark.parametrize(
    "absent",
    [
        test_site.OWNER_USER,
        test_site.OWNER_PASSWORD,
        test_site.ADMINISTRATOR_PASSWORD,
        "AIRWORTHINESS_DATABASE_USER",
        "AIRWORTHINESS_DATABASE_PASSWORD",
    ],
)
def test_a_start_with_a_value_missing_is_refused_and_names_it(absent: str) -> None:
    environment = {name: value for name, value in HOSTED.items() if name != absent}
    with pytest.raises(test_site.RefusedError, match=absent):
        test_site.owner_environment(environment)


def test_the_service_is_never_started_as_the_owner() -> None:
    same = {**HOSTED, "AIRWORTHINESS_DATABASE_USER": "airworthiness_owner"}
    with pytest.raises(test_site.RefusedError, match="does not sign in as the owner"):
        test_site.owner_environment(same)


# The start itself


class Started(Exception):
    """Stands in for the service taking the place of the program."""


@pytest.fixture
def start(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Record what ``main`` runs, in place of running it."""
    seen: dict[str, Any] = {"code": 0}

    def run(command: Sequence[str], **options: Any) -> subprocess.CompletedProcess[bytes]:
        seen["owner_command"], seen["owner_environment"] = list(command), options["env"]
        return subprocess.CompletedProcess(command, seen["code"])

    def become(name: str, command: Sequence[str], environment: dict[str, str]) -> NoReturn:
        seen["service_command"], seen["service_environment"] = list(command), environment
        raise Started

    for name in list(os.environ):
        if name.startswith(("AIRWORTHINESS_", "RENDER_")):
            monkeypatch.delenv(name)
    for name, value in HOSTED.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(os, "execvpe", become)
    return seen


def test_the_owners_work_comes_first_and_then_the_service_takes_over(start: dict[str, Any]) -> None:
    with pytest.raises(Started):
        test_site.main(["gunicorn", "airworthiness_plus.wsgi:application"])
    assert start["owner_command"][1:] == ["-m", "django", "prepare_test_site"]
    assert start["owner_environment"]["AIRWORTHINESS_DATABASE_USER"] == "airworthiness_owner"
    assert start["owner_environment"]["AIRWORTHINESS_DATABASE_OWNER_WORK"] == "true"
    assert start["service_command"] == ["gunicorn", "airworthiness_plus.wsgi:application"]
    assert start["service_environment"]["AIRWORTHINESS_DATABASE_USER"] == "airworthiness_service"
    assert OWNERS not in " ".join(start["service_environment"].values())


def test_the_service_is_not_started_when_the_owners_work_fails(start: dict[str, Any]) -> None:
    start["code"] = 1
    assert test_site.main(["gunicorn"]) == 1
    assert "service_command" not in start


def test_a_start_that_is_refused_runs_nothing(
    start: dict[str, Any], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert test_site.main([]) == 2
    monkeypatch.delenv(test_site.OWNER_PASSWORD)
    assert test_site.main(["gunicorn"]) == 2
    assert test_site.OWNER_PASSWORD in capsys.readouterr().err
    assert "owner_command" not in start and "service_command" not in start


# The owner's work, against the database


def one(statement: str, parameters: Sequence[Any] = ()) -> Any:
    with connection.cursor() as cursor:
        cursor.execute(statement, list(parameters))
        return cursor.fetchone()[0]


def mark_the_database() -> None:
    """Mark the test database as the test site's own, as an empty one is marked."""
    with connection.cursor() as cursor:
        name = connection.ops.quote_name(connection.settings_dict["NAME"])
        cursor.execute(f"COMMENT ON DATABASE {name} IS %s", [prepare_test_site.MARK])


@pytest.fixture
def given(monkeypatch: pytest.MonkeyPatch, settings: Any) -> None:
    """The values the start passes to the owner's work."""
    settings.DATABASE_OWNER_WORK = True
    monkeypatch.setenv(test_site.SERVICE_USER, ROLE)
    monkeypatch.setenv(test_site.SERVICE_PASSWORD, PASSWORD)
    monkeypatch.setenv(test_site.ADMINISTRATOR_PASSWORD, FIRST_PASSWORD)
    monkeypatch.setenv(test_site.SECOND_ADMINISTRATOR_PASSWORD, SECOND_PASSWORD)


def prepare() -> str:
    output = io.StringIO()
    call_command("prepare_test_site", stdout=output, verbosity=0)
    return output.getvalue()


@pytest.mark.django_db
def test_a_database_not_made_for_the_test_site_is_refused(given: None) -> None:
    """The sample can never be removed, so it goes only into a database marked for it."""
    with as_owner():
        with pytest.raises(CommandError, match="not made for the test site"):
            prepare()
        assert one("SELECT count(*) FROM pg_roles WHERE rolname = %s", [ROLE]) == 0
        assert not prepare_test_site.sample_is_set_up()


@pytest.mark.django_db
def test_an_empty_database_is_marked_as_the_test_sites_own(
    given: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with as_owner():
        monkeypatch.setattr(connection.introspection, "table_names", lambda cursor=None: [])
        prepare_test_site.claim_database()
        marked = one(
            "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
            "WHERE datname = current_database()"
        )
        assert marked == prepare_test_site.MARK
        monkeypatch.undo()
        prepare_test_site.claim_database()


@pytest.mark.django_db
def test_the_owners_work_is_refused_to_the_applications_own_role(
    given: None, settings: Any
) -> None:
    settings.DATABASE_OWNER_WORK = False
    with as_owner():
        mark_the_database()
        with pytest.raises(CommandError, match="owner of the tables"):
            prepare()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "absent", [test_site.SERVICE_USER, test_site.SERVICE_PASSWORD, test_site.ADMINISTRATOR_PASSWORD]
)
def test_the_owners_work_names_a_value_it_was_not_given(
    given: None, monkeypatch: pytest.MonkeyPatch, absent: str
) -> None:
    monkeypatch.delenv(absent)
    with as_owner(), pytest.raises(CommandError, match=absent):
        prepare()


@pytest.mark.django_db
def test_the_role_and_the_sample_are_made_once_and_a_second_start_changes_neither(
    given: None,
) -> None:
    with as_owner():
        mark_the_database()
        with CaptureQueriesContext(connection) as sent:
            first = prepare()
        assert first.splitlines() == [
            "Service Role Made",
            "Sample Organisation Set Up",
            f"Administrator {ADMINISTRATOR}",
            # The second sample organisation, which holds Part-CAMO and Part-145 (REQ-218).
            "Second Sample Organisation Set Up",
            f"Administrator {second.ADMINISTRATOR}",
        ]
        # The role can sign in, has no power of its own, and is a member of the
        # application's role and of nothing else (ADR-0002).
        powers = one(
            "SELECT rolcanlogin AND NOT (rolsuper OR rolcreaterole OR rolcreatedb "
            "OR rolbypassrls OR rolreplication) FROM pg_roles WHERE rolname = %s",
            [ROLE],
        )
        assert powers is True
        memberships = one(
            "SELECT array_agg(pg_get_userbyid(roleid)::text) FROM pg_auth_members "
            "WHERE member = (SELECT oid FROM pg_roles WHERE rolname = %s)",
            [ROLE],
        )
        assert memberships == [APPLICATION_ROLE]
        # The database is sent the hash of each password, never the password.
        statements = " ".join(query["sql"] for query in sent.captured_queries)
        assert "SCRAM-SHA-256$" in statements
        assert PASSWORD not in statements and FIRST_PASSWORD not in statements
        assert PASSWORD not in first and FIRST_PASSWORD not in first
        assert SECOND_PASSWORD not in statements and SECOND_PASSWORD not in first

        assert prepare_test_site.sample_is_set_up()
        again = prepare()
        assert again.splitlines() == [
            "Service Role Password Set Again",
            "Sample Organisation Already Set Up",
            "Second Sample Organisation Already Set Up",
        ]
        assert one("SELECT count(*) FROM pg_roles WHERE rolname = %s", [ROLE]) == 1
        # Seen as the sign-in page sees it: the Administrator, whose first password works.
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SELECT set_config(%s, %s, true)", [SIGNING_IN_SETTING, ADMINISTRATOR])
            administrator = User.objects.get(username=ADMINISTRATOR)
            assert administrator.check_password(FIRST_PASSWORD)
            assert not administrator.check_password(PASSWORD)
            # A first password, as every other is: changed at the first
            # sign-in and good for 7 days (review of 20 November 2026, finding 8).
            assert administrator.password_must_change
            assert administrator.first_password_set_on == sign_in.today()


@pytest.mark.django_db
def test_an_existing_test_site_gets_only_its_missing_sample_suppliers(
    given: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with as_owner():
        mark_the_database()
        with monkeypatch.context() as earlier:
            earlier.setattr(suppliers, "add", lambda organisation, actor: 0)
            prepare()
        administrator = prepare_test_site.administrator_named(ADMINISTRATOR)
        assert administrator is not None
        with working_for(administrator.organisation_id, administrator.id):
            existing = Supplier.objects.create(
                organisation_id=administrator.organisation_id, name="[Oil Supplier]"
            )
        assert "Suppliers of the Sample Added, 4 Suppliers" in prepare()
        assert "Suppliers of the Sample Added" not in prepare()
        with working_for(administrator.organisation_id, administrator.id):
            assert Supplier.objects.count() == 5
            assert not existing.evaluations.exists()


def second_administrator() -> User | None:
    return prepare_test_site.administrator_named(second.ADMINISTRATOR)


@pytest.mark.django_db
@pytest.mark.parametrize("value", ["", FIRST_PASSWORD])
def test_the_second_organisation_is_not_set_up_without_a_first_password_of_its_own(
    given: None, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """Independent review of 24 November 2026, finding 9. With no value, or with the first
    Administrator's, the start sets up nothing for the second organisation, says so,
    and carries on. Given one later, the next start sets it up."""
    monkeypatch.setenv(test_site.SECOND_ADMINISTRATOR_PASSWORD, value)
    reason = (
        f"{test_site.SECOND_ADMINISTRATOR_PASSWORD} Is Not Set in the Environment"
        if not value
        else "Its Administrator Has a First Password of Its Own"
    )
    with as_owner():
        mark_the_database()
        first = prepare()
        assert first.splitlines() == [
            "Service Role Made",
            "Sample Organisation Set Up",
            f"Administrator {ADMINISTRATOR}",
            f"Second Sample Organisation Not Set Up: {reason}",
        ]
        assert FIRST_PASSWORD not in first
        assert second_administrator() is None
        assert one("SELECT count(*) FROM organisations_organisation") == 1
        assert prepare().splitlines()[-1] == f"Second Sample Organisation Not Set Up: {reason}"
        monkeypatch.setenv(test_site.SECOND_ADMINISTRATOR_PASSWORD, SECOND_PASSWORD)
        assert prepare().splitlines()[-2:] == [
            "Second Sample Organisation Set Up",
            f"Administrator {second.ADMINISTRATOR}",
        ]
        theirs = second_administrator()
        assert theirs is not None
        assert theirs.check_password(SECOND_PASSWORD) and not theirs.check_password(FIRST_PASSWORD)


@pytest.mark.django_db
@pytest.mark.parametrize("taken", second.USERNAMES)
def test_a_start_never_fails_because_a_user_name_of_the_second_sample_is_taken(
    given: None, monkeypatch: pytest.MonkeyPatch, taken: str
) -> None:
    """Finding 9. Any Administrator of the first organisation can add a user under a name
    the second sample would use. The start then says so and carries on, at every
    start, and makes nothing of the second organisation."""
    with as_owner():
        mark_the_database()
        monkeypatch.delenv(test_site.SECOND_ADMINISTRATOR_PASSWORD)
        prepare()
        monkeypatch.setenv(test_site.SECOND_ADMINISTRATOR_PASSWORD, SECOND_PASSWORD)
        first = prepare_test_site.administrator_named(ADMINISTRATOR)
        assert first is not None
        with working_for(first.organisation_id, first.id):
            users.add_user(
                organisation=first.organisation,
                username=taken,
                full_name="[Taken Name]",
                roles=[],
                password=users.new_first_password(),
            )
        for _ in range(2):
            assert prepare().splitlines() == [
                "Service Role Password Set Again",
                "Sample Organisation Already Set Up",
                "Second Sample Organisation Not Set Up: One of Its User Names Is Already Taken",
            ]
        assert one("SELECT count(*) FROM organisations_organisation") == 1
        assert one("SELECT count(*) FROM people_person") == 16


@pytest.mark.django_db
def test_a_role_with_powers_or_other_memberships_is_not_taken_over(given: None) -> None:
    with as_owner():
        mark_the_database()
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE ROLE {ROLE} LOGIN CREATEDB IN ROLE {APPLICATION_ROLE}")
        with pytest.raises(CommandError, match="without powers of its own"):
            prepare()
        # A member of the application's role and of another as well: the
        # check is "alone", not "is a member" (review of 20 November 2026).
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER ROLE {ROLE} NOCREATEDB")
            cursor.execute("CREATE ROLE review_other_role NOLOGIN")
            cursor.execute(f"GRANT review_other_role TO {ROLE}")
        with pytest.raises(CommandError, match=f"not a member of {APPLICATION_ROLE} alone"):
            prepare()
        with connection.cursor() as cursor:
            cursor.execute(f"REVOKE review_other_role FROM {ROLE}")
            cursor.execute(f"REVOKE {APPLICATION_ROLE} FROM {ROLE}")
        with pytest.raises(CommandError, match=f"not a member of {APPLICATION_ROLE} alone"):
            prepare()
        assert not prepare_test_site.sample_is_set_up()


@pytest.mark.django_db
def test_the_owner_is_never_made_the_services_role(
    given: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    with as_owner():
        mark_the_database()
        monkeypatch.setenv(test_site.SERVICE_USER, one("SELECT current_user"))
        with pytest.raises(CommandError, match="does not sign in as the owner"):
            prepare()


# The host's set-up file


def blueprint() -> str:
    return (ROOT / "render.yaml").read_text(encoding="utf-8")


def test_the_test_site_starts_the_service_exactly_as_the_image_does() -> None:
    """The start is the owner's work followed by the Dockerfile's own command, unchanged."""
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    written = re.findall(r"^CMD (\[.*?\])$", dockerfile, flags=re.M | re.S)[-1]
    image_command = json.loads(written.replace("\\\n", ""))
    started = re.search(r"^ +dockerCommand: (.+)$", blueprint(), flags=re.M)
    assert started is not None
    assert started.group(1).split() == [
        "python",
        "-m",
        "airworthiness_plus.sample.test_site",
        *image_command,
    ]


def test_the_set_up_file_gives_every_value_the_start_needs_and_holds_no_secret() -> None:
    """Threat TH-063: every secret is generated by the host or taken from its database."""
    text = blueprint()
    entries = re.findall(r"^ +- key: (\S+)\n((?: {8,}\S.*\n)+)", text, flags=re.M)
    values = {key: body for key, body in entries}
    for name in (
        "AIRWORTHINESS_SECRET_KEY",
        "AIRWORTHINESS_DATABASE_NAME",
        "AIRWORTHINESS_DATABASE_HOST",
        "AIRWORTHINESS_DATABASE_PORT",
        "AIRWORTHINESS_DATABASE_USER",
        "AIRWORTHINESS_DATABASE_PASSWORD",
        test_site.OWNER_USER,
        test_site.OWNER_PASSWORD,
        test_site.ADMINISTRATOR_PASSWORD,
        test_site.SECOND_ADMINISTRATOR_PASSWORD,
    ):
        assert name in values, name
    # Each Administrator's first password is a value of its own (finding 9 of 24 November 2026).
    for name in (test_site.ADMINISTRATOR_PASSWORD, test_site.SECOND_ADMINISTRATOR_PASSWORD):
        assert "generateValue: true" in values[name], name
    for name, body in values.items():
        if "PASSWORD" in name or "SECRET" in name:
            assert "generateValue: true" in body or "fromDatabase:" in body, name
            assert "value:" not in body, name
    assert "AIRWORTHINESS_DEBUG" not in text
    assert "AIRWORTHINESS_DATABASE_OWNER_WORK" not in values
    assert text.count("plan: free") == 2
