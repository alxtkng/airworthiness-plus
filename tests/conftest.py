"""Test set-up: build the database as its owner, then test as the application.

The application works as a database role that owns nothing and is subject
to row-level security. The test database is created and migrated as the
connecting user, who owns the tables, and every test then runs as the
application role, as it does in service.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

import pytest
from django.conf import settings
from django.db import connection

from airworthiness_plus.history.sql import APPLICATION_ROLE


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


@pytest.fixture(autouse=True)
def fast_passwords(settings: Any) -> None:
    """Hash passwords quickly in tests. One test puts the real hasher back."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
