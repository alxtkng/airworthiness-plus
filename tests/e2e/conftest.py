"""Start the real service against fresh clones of a disposable, seeded database."""

import json
import os
import secrets
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import psycopg
import pytest
from django.contrib.sessions.backends.db import SessionStore
from django.core import signing
from playwright.sync_api import Browser, sync_playwright
from psycopg import sql

from airworthiness_plus.accounts.middleware import VERIFIED_AT_KEY
from airworthiness_plus.accounts.roles import Role

ROOT = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if os.environ.get("AIRWORTHINESS_E2E") != "1":
        skip = pytest.mark.skip(reason="Set AIRWORTHINESS_E2E=1 to run live browser tests")
        for item in items:
            if item.path.is_relative_to(ROOT / "tests" / "e2e"):
                item.add_marker(skip)


@dataclass(frozen=True)
class Account:
    username: str
    role: Role
    password: str = field(repr=False, default_factory=lambda: secrets.token_urlsafe(24))
    new_password: str = field(repr=False, default_factory=lambda: secrets.token_urlsafe(24))


def accounts_for(domain: str) -> tuple[Account, ...]:
    return tuple(
        Account(f"{name}@{domain}.example", role)
        for name, role in (
            ("accountable.manager", Role.ADMINISTRATOR),
            ("manager", Role.CONTINUING_AIRWORTHINESS_MANAGER),
            ("review", Role.AIRWORTHINESS_REVIEW_STAFF),
            ("planning", Role.PLANNING_AND_RECORDS),
            ("reader", Role.READ_ONLY),
        )
    )


@pytest.fixture(scope="session")
def personas() -> dict[str, tuple[Account, ...]]:
    return {name: accounts_for(name) for name in ("your-organisation", "second-organisation")}


@dataclass(frozen=True)
class Database:
    admin: psycopg.Connection[tuple[Any, ...]]
    template: str
    env: dict[str, str] = field(repr=False)


@pytest.fixture(scope="session")
def seeded_database(
    tmp_path_factory: pytest.TempPathFactory, personas: dict[str, tuple[Account, ...]]
) -> Iterator[Database]:
    dsn = os.environ.get("AIRWORTHINESS_E2E_POSTGRES")
    if not dsn:
        pytest.fail("Set AIRWORTHINESS_E2E_POSTGRES to a disposable local PostgreSQL cluster")
    # libpq values are passed directly to the subprocess. No credential is printed.
    params = psycopg.conninfo.conninfo_to_dict(dsn)
    host = str(params.get("host") or "")
    if not (host in {"", "localhost", "127.0.0.1", "::1"} or host.startswith("/")):
        pytest.fail("The end-to-end suite requires a local PostgreSQL cluster")
    if "hostaddr" in params or not host:
        pytest.fail("Set an explicit loopback host or Unix socket directory")
    if "," in host:
        pytest.fail("Use exactly one local PostgreSQL host")
    prefix = f"airworthiness_e2e_{secrets.token_hex(6)}"
    owner, runtime, template = (f"{prefix}_{suffix}" for suffix in ("owner", "service", "seed"))
    ident = sql.Identifier
    env = dict(
        os.environ,
        DJANGO_SETTINGS_MODULE="airworthiness_plus.settings",
        AIRWORTHINESS_DATABASE_NAME=template,
        AIRWORTHINESS_DATABASE_HOST=host,
        AIRWORTHINESS_DATABASE_PORT=str(params.get("port") or "5432"),
        AIRWORTHINESS_ALLOWED_HOSTS="127.0.0.1,localhost",
        AIRWORTHINESS_DEBUG="false",
        AIRWORTHINESS_BEHIND_PROXY="false",
        AIRWORTHINESS_SECRET_KEY=secrets.token_urlsafe(50),
        AIRWORTHINESS_STATIC_ROOT=str(tmp_path_factory.mktemp("e2e-static")),
    )
    owner_password, runtime_password = (secrets.token_urlsafe(24) for _ in range(2))
    with psycopg.connect(dsn, autocommit=True) as admin:
        try:
            for name, password in ((owner, owner_password), (runtime, runtime_password)):
                admin.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                        ident(name), sql.Literal(password)
                    )
                )
            admin.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(ident(template), ident(owner))
            )
            admin.execute(
                "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles "
                "WHERE rolname = 'airworthiness_application') THEN "
                "CREATE ROLE airworthiness_application NOLOGIN; END IF; END $$"
            )
            admin.execute(sql.SQL("GRANT airworthiness_application TO {}").format(ident(runtime)))
            owner_env = dict(
                env,
                AIRWORTHINESS_DATABASE_USER=owner,
                AIRWORTHINESS_DATABASE_PASSWORD=owner_password,
                AIRWORTHINESS_DATABASE_OWNER_WORK="true",
            )
            run = partial(subprocess.run, cwd=ROOT, env=owner_env, check=True, timeout=90)
            run(
                [sys.executable, "-m", "tests.e2e.server", "seed"],
                input=json.dumps(
                    [[asdict(person) for person in group] for group in personas.values()]
                ),
                text=True,
            )
            run([sys.executable, "manage.py", "collectstatic", "--noinput", "--verbosity", "0"])
            yield Database(
                admin,
                template,
                dict(
                    env,
                    AIRWORTHINESS_DATABASE_USER=runtime,
                    AIRWORTHINESS_DATABASE_PASSWORD=runtime_password,
                    AIRWORTHINESS_DATABASE_OWNER_WORK="false",
                ),
            )
        finally:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(ident(template))
            )
            for name in (runtime, owner):
                admin.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(ident(name)))


@dataclass(frozen=True)
class RunningSite:
    address: str
    name: str
    database: Database

    def advance_verification_age(self, session_key: str) -> None:
        """Move the test session beyond the fresh-verification window."""
        env = self.database.env
        with psycopg.connect(self.database.admin.info.dsn, dbname=self.name) as connection:
            row = connection.execute(
                "SELECT session_data FROM django_session WHERE session_key = %s", (session_key,)
            ).fetchone()
            assert row is not None
            key, salt = env["AIRWORTHINESS_SECRET_KEY"], SessionStore().key_salt
            data = signing.loads(row[0], key=key, salt=salt, fallback_keys=[])
            data[VERIFIED_AT_KEY] = (datetime.now(UTC) - timedelta(minutes=6)).isoformat()
            encoded = signing.dumps(data, key=key, salt=salt, compress=True)
            connection.execute(
                "UPDATE django_session SET session_data = %s WHERE session_key = %s",
                (encoded, session_key),
            )


@pytest.fixture
def running_site(seeded_database: Database, tmp_path: Path) -> Iterator[RunningSite]:
    database = seeded_database
    name = database.template.replace("_seed", f"_{secrets.token_hex(4)}")
    database.admin.execute(
        sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            sql.Identifier(name), sql.Identifier(database.template)
        )
    )
    ready = tmp_path / "server-address"
    try:
        command = [sys.executable, "-m", "tests.e2e.server", str(ready)]
        with subprocess.Popen(  # noqa: S603
            command, cwd=ROOT, env=dict(database.env, AIRWORTHINESS_DATABASE_NAME=name)
        ) as server:
            try:
                deadline = time.monotonic() + 15
                while server.poll() is None and time.monotonic() < deadline:
                    if ready.is_file() and (address := ready.read_text()):
                        yield RunningSite(address, name, database)
                        return
                    time.sleep(0.05)
                pytest.fail("The loopback application did not start")
            finally:
                if server.poll() is None:
                    server.terminate()
                    try:
                        server.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait()
    finally:
        database.admin.execute(
            sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
        )


@pytest.fixture
def live_site(running_site: RunningSite) -> str:
    return running_site.address


@pytest.fixture(scope="session")
def chromium() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        executable = os.environ.get("AIRWORTHINESS_BROWSER")
        browser = (
            playwright.chromium.launch(executable_path=executable)
            if executable
            else playwright.chromium.launch()
        )
        try:
            yield browser
        finally:
            browser.close()
