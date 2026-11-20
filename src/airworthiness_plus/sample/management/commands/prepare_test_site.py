"""Make a database ready for the test site (operations/test-site.md).

    AIRWORTHINESS_DATABASE_OWNER_WORK=true python manage.py prepare_test_site

Run by the owner of the tables each time the test site starts, by
``airworthiness_plus.sample.test_site``. It brings the tables up to date,
makes the role the service signs in to the database as, and sets up the
sample organisation if it is not there. A second run changes nothing but
that role's password, which is set again to the one given.

The test site holds the sample and nothing else, and the sample can never
be removed once it is in a database. So this works only on a database it
found empty and marked as the test site's own, and refuses any other: it
cannot be turned on real records. Nothing it is given is written to its
output.
"""

import os
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from psycopg import sql

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.sql import APPLICATION_ROLE, SIGNING_IN_SETTING
from airworthiness_plus.sample.management.commands.seed_sample_organisation import (
    ADMINISTRATOR,
    seed,
)
from airworthiness_plus.sample.test_site import (
    ADMINISTRATOR_PASSWORD,
    SERVICE_PASSWORD,
    SERVICE_USER,
)

# The comment that marks a database as the test site's own.
MARK = "Airworthiness+ test site. The sample organisation only."

# What the role the service signs in as must not be able to do (ADR-0002).
POWERS = "rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls OR rolreplication"


def given(name: str) -> str:
    """Return the value of ``name`` from the environment, or refuse."""
    value = os.environ.get(name, "")
    if not value:
        raise CommandError(f"{name} must be set in the environment")
    return value


def claim_database() -> None:
    """Mark an empty database as the test site's own, or refuse one that is neither.

    The mark is a comment on the database. It is made before any table, so
    a start that fails part way is taken up again by the next.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT datname, shobj_description(oid, 'pg_database') FROM pg_database "
            "WHERE datname = current_database()"
        )
        name, comment = cursor.fetchone()
        if comment == MARK:
            return
        if connection.introspection.table_names(cursor):
            raise CommandError(
                "This database was not made for the test site. "
                "The test site starts from an empty database and holds the sample alone"
            )
        cursor.execute(
            sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(name), sql.Literal(MARK))
        )


def sample_is_set_up() -> bool:
    """Return whether the sample organisation's Administrator exists.

    The owner of the tables is shown no organisation's rows (ADR-0002), so
    this asks as the sign-in page does: for one user, by name. A user name
    is used once across every organisation.
    """
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [SIGNING_IN_SETTING, ADMINISTRATOR])
        found: bool = User.objects.filter(username=ADMINISTRATOR).exists()
        cursor.execute("SELECT set_config(%s, '', true)", [SIGNING_IN_SETTING])
    return found


def service_role(name: str, password: str) -> bool:
    """Make the role the service signs in as, or set its password again.

    The role is a member of the application's role and nothing more, and
    has no power of its own (ADR-0002). The password is hashed here, so the
    database is never sent it and cannot log it. Return whether the role
    was made.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        if cursor.fetchone() == (name,):
            raise CommandError("The service does not sign in as the owner of the tables")
        hashed = connection.connection.pgconn.encrypt_password(
            password.encode(), name.encode(), b"scram-sha-256"
        ).decode()
        role, secret = sql.Identifier(name), sql.Literal(hashed)
        cursor.execute(f"SELECT {POWERS} FROM pg_roles WHERE rolname = %s", [name])  # noqa: S608
        found = cursor.fetchone()
        if found is None:
            cursor.execute(
                sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS "
                    "PASSWORD {} IN ROLE {}"
                ).format(role, secret, sql.Identifier(APPLICATION_ROLE))
            )
            return True
        cursor.execute(
            "SELECT array_agg(pg_get_userbyid(roleid)::text) FROM pg_auth_members "
            "WHERE member = (SELECT oid FROM pg_roles WHERE rolname = %s)",
            [name],
        )
        memberships = cursor.fetchone()
        if found[0] or memberships != ([APPLICATION_ROLE],):
            raise CommandError(
                f"The role {name} exists and is not a member of {APPLICATION_ROLE} alone, "
                "without powers of its own"
            )
        cursor.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(role, secret))
        return False


class Command(BaseCommand):
    """Bring the tables up to date, make the service's role and seed the sample."""

    help = "Make a database ready for the test site. For the sample organisation only."

    def handle(self, *args: Any, **options: Any) -> None:
        """Refuse real records, then do the owner's work for the test site."""
        if not settings.DATABASE_OWNER_WORK:
            raise CommandError("Run as the owner of the tables: AIRWORTHINESS_DATABASE_OWNER_WORK")
        user, password = given(SERVICE_USER), given(SERVICE_PASSWORD)
        administrator = given(ADMINISTRATOR_PASSWORD)
        claim_database()
        call_command("migrate", interactive=False, verbosity=options["verbosity"])
        made = service_role(user, password)
        self.stdout.write("Service Role Made" if made else "Service Role Password Set Again")
        if sample_is_set_up():
            self.stdout.write("Sample Organisation Already Set Up")
            return
        seed(administrator)
        self.stdout.write("Sample Organisation Set Up")
        self.stdout.write(f"Administrator {ADMINISTRATOR}")
