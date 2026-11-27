"""Make a database ready for the test site (operations/test-site.md).

    AIRWORTHINESS_DATABASE_OWNER_WORK=true python manage.py prepare_test_site

Run by the owner of the tables each time the test site starts, by
``airworthiness_plus.sample.test_site``. It brings the tables up to date,
makes the role the service signs in to the database as, and sets up the
two sample organisations if they are not there. A sample seeded before the
canvas build is given what it lacks, and nothing that is there is changed.
A second run changes nothing but that role's password, which is set again
to the one given.

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
from django.db import IntegrityError, connection, transaction
from psycopg import sql

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import APPLICATION_ROLE, SIGNING_IN_SETTING
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.sample import build, planning, second, top_up
from airworthiness_plus.sample.management.commands.seed_sample_organisation import (
    ADMINISTRATOR,
    seed,
)
from airworthiness_plus.sample.test_site import (
    ADMINISTRATOR_PASSWORD,
    SECOND_ADMINISTRATOR_PASSWORD,
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


def administrator_named(username: str) -> User | None:
    """Return the user of this name, if there is one.

    The owner of the tables is shown no organisation's rows (ADR-0002), so
    this asks as the sign-in page does: for one user, by name. A user name
    is used once across every organisation.
    """
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [SIGNING_IN_SETTING, username])
        found: User | None = User.objects.filter(username=username).first()
        cursor.execute("SELECT set_config(%s, '', true)", [SIGNING_IN_SETTING])
    return found


def sample_is_set_up() -> bool:
    """Return whether the sample organisation's Administrator exists."""
    return administrator_named(ADMINISTRATOR) is not None


def complete_the_people(administrator: User) -> int:
    """Give a sample seeded before person records the people it lacks (REQ-218).

    Once, and only what is missing: ``build.add_person_records`` says how.
    Nothing that anyone has recorded is changed, nobody is found by name,
    and no sign-in is touched. Return how many people were added.
    """
    with working_for(administrator.organisation_id, administrator.id):
        ours = Organisation.objects.get(pk=administrator.organisation_id)
        return build.add_person_records(ours, administrator)


def bring_phase_1(administrator: User) -> list[str]:
    """Give a sample seeded before Phase 1 of the canvas build what it lacks (REQ-294).

    Once, and only what is missing: ``top_up.add_phase_1`` says how. It
    changes nothing that is there, looks nobody up by name, and whatever
    goes wrong the start carries on. Return a line for each part added.
    """
    try:
        with working_for(administrator.organisation_id, administrator.id):
            ours = Organisation.objects.get(pk=administrator.organisation_id)
            return top_up.add_phase_1(ours, administrator)
    except Exception as error:
        return [f"Phase 1 of the Sample Not Brought Up to Date: {type(error).__name__}"]


def bring_work_packages(administrator: User) -> str:
    """Add the draft planning sample to earlier test-site databases."""
    try:
        with working_for(administrator.organisation_id, administrator.id):
            ours = Organisation.objects.get(pk=administrator.organisation_id)
            aircraft = top_up.aircraft_of_the_sample().get("G-EJKL")
            if aircraft is not None and planning.add_work_packages(ours, administrator, aircraft):
                return "Work Packages of the Sample Added, 1 Work Package"
    except Exception as error:
        return f"Sample Work Package Not Added: {type(error).__name__}"
    return ""


def second_organisation() -> str:
    """Set up the second sample organisation if it can be, and say what was done.

    Its Administrator has a first password of its own, never the first
    organisation's (independent review of 24 November 2026, finding 9).
    With none given, or with a user name of its sample already taken, it
    is not set up, the start says so and carries on: the test site still
    starts. Nothing given is written to the output.
    """
    found = administrator_named(second.ADMINISTRATOR)
    if found is not None:
        # The name alone does not say so: anyone may have been added under it.
        with working_for(found.organisation_id):
            theirs = Organisation.objects.get(pk=found.organisation_id)
        if theirs.approval_reference == second.APPROVAL_REFERENCE:
            return "Second Sample Organisation Already Set Up"
        return "Second Sample Organisation Not Set Up: One of Its User Names Is Already Taken"
    password = os.environ.get(SECOND_ADMINISTRATOR_PASSWORD, "")
    if not password:
        return (
            "Second Sample Organisation Not Set Up: "
            f"{SECOND_ADMINISTRATOR_PASSWORD} Is Not Set in the Environment"
        )
    if password == os.environ.get(ADMINISTRATOR_PASSWORD, ""):
        return (
            "Second Sample Organisation Not Set Up: "
            "Its Administrator Has a First Password of Its Own"
        )
    try:
        second.seed(password)
    except IntegrityError:
        # A user name is used once across every organisation, and the database
        # holds that. Nothing was made: ``seed`` is one piece of work.
        return "Second Sample Organisation Not Set Up: One of Its User Names Is Already Taken"
    return f"Second Sample Organisation Set Up\nAdministrator {second.ADMINISTRATOR}"


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
        first = administrator_named(ADMINISTRATOR)
        if first is not None:
            self.stdout.write("Sample Organisation Already Set Up")
            added = complete_the_people(first)
            if added:
                self.stdout.write(f"People of the Sample Brought Up to Date, {added} Added")
            for line in bring_phase_1(first):
                self.stdout.write(line)
            work_packages = bring_work_packages(first)
            if work_packages:
                self.stdout.write(work_packages)
        else:
            seed(administrator)
            self.stdout.write("Sample Organisation Set Up")
            self.stdout.write(f"Administrator {ADMINISTRATOR}")
        # The second sample organisation holds Part-CAMO and Part-145 (REQ-218).
        self.stdout.write(second_organisation())
