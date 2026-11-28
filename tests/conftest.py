"""Test set-up: build the database as its owner, then test as the application.

The application works as a database role that owns nothing and is subject
to row-level security. The test database is created and migrated as the
connecting user, who owns the tables, and every test then runs as the
application role, as it does in service.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, cast

import pytest
from django.conf import settings
from django.db import connection

from airworthiness_plus.history.sql import APPLICATION_ROLE

if TYPE_CHECKING:
    from tests.support import Sample


@pytest.fixture
def sample() -> "Sample":
    from tests.support import make_sample

    return make_sample()


@pytest.fixture(scope="session")
def django_db_modify_db_settings() -> None:
    """Create and migrate the test database as the owner."""
    options = cast("dict[str, Any]", settings.DATABASES["default"]["OPTIONS"])
    options.pop("assume_role", None)


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup: None) -> Iterator[None]:
    """Switch every later connection to the application role."""
    connection.settings_dict["OPTIONS"]["assume_role"] = APPLICATION_ROLE
    connection.close()
    yield
    connection.settings_dict["OPTIONS"].pop("assume_role", None)
    connection.close()


@contextmanager
def as_owner() -> Iterator[None]:
    """Do the enclosed work as the owner of the tables, then return to the application role."""
    with connection.cursor() as cursor:
        cursor.execute("SET ROLE NONE")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f"SET ROLE {APPLICATION_ROLE}")


# A role made for the tests: it owns the tables and has no other power.
OWNER_WITHOUT_POWERS = "airworthiness_test_owner"


@contextmanager
def as_owner_who_is_not_a_superuser(
    *,
    functions: tuple[str, ...] = (),
) -> Iterator[None]:
    """Do the enclosed work as an owner of every table who is not a superuser.

    The tests build the database as the connecting user, who is a superuser:
    row-level security never holds a superuser, so ``as_owner`` does not
    show how the owner's work goes on a server, where the owner is an
    ordinary role held by row-level security like any other (ADR-0002;
    independent review of 24 November 2026). Here every table is given, for
    the length of the work, to a role with no power but owning them. The
    change of owner is undone afterwards, and is within the test's own
    transaction in any case. A migration replacing a function can include
    that function's fixed signature in the transfer.
    """
    role = connection.ops.quote_name(OWNER_WITHOUT_POWERS)
    with connection.cursor() as cursor:
        cursor.execute("SET ROLE NONE")
        cursor.execute("SELECT current_user")
        (builder,) = cursor.fetchone()
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [OWNER_WITHOUT_POWERS])
        if cursor.fetchone() is None:
            cursor.execute(
                f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"
            )
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = current_schema() ORDER BY 1"
        )
        tables = [connection.ops.quote_name(name) for (name,) in cursor.fetchall()]
        # A table with checks still waiting cannot change owner.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE; SET CONSTRAINTS ALL DEFERRED")
        for table in tables:
            cursor.execute(f"ALTER TABLE {table} OWNER TO {role}")
        # An owner makes tables of its own, as a migration does.
        cursor.execute(f"GRANT CREATE ON SCHEMA public TO {role}")
        for function in functions:
            cursor.execute(f"ALTER FUNCTION {function} OWNER TO {role}")
        cursor.execute(f"SET ROLE {role}")
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SET ROLE NONE")
            cursor.execute(f"REVOKE CREATE ON SCHEMA public FROM {role}")
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE; SET CONSTRAINTS ALL DEFERRED")
            for table in tables:
                cursor.execute(f"ALTER TABLE {table} OWNER TO {connection.ops.quote_name(builder)}")
            for function in functions:
                cursor.execute(
                    f"ALTER FUNCTION {function} OWNER TO {connection.ops.quote_name(builder)}"
                )
            cursor.execute(f"SET ROLE {APPLICATION_ROLE}")


@pytest.fixture(autouse=True)
def fast_passwords(settings: Any) -> None:
    """Hash passwords quickly in tests. One test puts the real hasher back."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
