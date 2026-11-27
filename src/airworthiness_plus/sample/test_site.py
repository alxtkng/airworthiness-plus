"""Start the test site: do the owner's work, then run the service as its own role.

    python -m airworthiness_plus.sample.test_site gunicorn airworthiness_plus.wsgi:application ...

The test site (operations/test-site.md) runs on a host that gives a
service no way to run a command before it starts and no terminal. So the
owner's work, which on the server is done by hand before the service is
started (operations/deployment.md), is done here each time the container
starts: the tables are brought up to date, the role the service signs in
as is made, and the sample organisation is set up if it is not there.

The service is then started in place of this program, with the owner's
credentials and the Administrator's first password taken out of its
environment. The running service holds only its own role's credentials,
as it does on the server (ADR-0002, threat TH-024).

This is for the sample organisation only, and is never used on the server.
It imports nothing from Django: the settings are read by the programs it
starts, each with the environment made for it.
"""

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence

PREFIX = "AIRWORTHINESS_TEST_SITE_"

# Set by the host for the test site alone.
OWNER_USER = PREFIX + "OWNER_USER"
OWNER_PASSWORD = PREFIX + "OWNER_PASSWORD"
ADMINISTRATOR_PASSWORD = PREFIX + "ADMINISTRATOR_PASSWORD"
# The first password of the second sample organisation's Administrator: its
# own, never the first's. Without it the second organisation is not set up.
SECOND_ADMINISTRATOR_PASSWORD = PREFIX + "SECOND_ADMINISTRATOR_PASSWORD"

# Passed on to ``prepare_test_site``: the role to make for the service.
SERVICE_USER = PREFIX + "SERVICE_USER"
SERVICE_PASSWORD = PREFIX + "SERVICE_PASSWORD"

DATABASE_USER = "AIRWORTHINESS_DATABASE_USER"
# The name of a setting, not a password.
DATABASE_PASSWORD = "AIRWORTHINESS_DATABASE_PASSWORD"  # noqa: S105  # pragma: allowlist secret
OWNER_WORK = "AIRWORTHINESS_DATABASE_OWNER_WORK"
ALLOWED_HOSTS = "AIRWORTHINESS_ALLOWED_HOSTS"

# The host name the host gives the service, used when none is set by hand.
HOST_NAME_FROM_THE_HOST = "RENDER_EXTERNAL_HOSTNAME"


class RefusedError(Exception):
    """The environment is not one the test site can start from."""


def owner_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Return the environment for the owner's work, or refuse.

    The service's own role and password are passed on under other names,
    so that the role can be made.
    """
    needed = (OWNER_USER, OWNER_PASSWORD, ADMINISTRATOR_PASSWORD, DATABASE_USER, DATABASE_PASSWORD)
    missing = [name for name in needed if not environment.get(name)]
    if missing:
        raise RefusedError(f"Not set in the environment: {', '.join(missing)}")
    if environment[OWNER_USER] == environment[DATABASE_USER]:
        raise RefusedError("The service does not sign in as the owner of the tables")
    return {
        **environment,
        DATABASE_USER: environment[OWNER_USER],
        DATABASE_PASSWORD: environment[OWNER_PASSWORD],
        OWNER_WORK: "true",
        SERVICE_USER: environment[DATABASE_USER],
        SERVICE_PASSWORD: environment[DATABASE_PASSWORD],
    }


def service_environment(environment: Mapping[str, str]) -> dict[str, str]:
    """Return the environment for the running service: nothing of the owner's."""
    kept = {
        name: value
        for name, value in environment.items()
        if not name.startswith(PREFIX) and name != OWNER_WORK
    }
    if not kept.get(ALLOWED_HOSTS) and environment.get(HOST_NAME_FROM_THE_HOST):
        kept[ALLOWED_HOSTS] = environment[HOST_NAME_FROM_THE_HOST]
    return kept


def main(arguments: Sequence[str]) -> int:
    """Do the owner's work, then become the service named by ``arguments``."""
    if not arguments:
        print("Give the command that starts the service", file=sys.stderr)
        return 2
    try:
        owner = owner_environment(os.environ)
    except RefusedError as error:
        print(error, file=sys.stderr)
        return 2
    prepare = [sys.executable, "-m", "django", "prepare_test_site"]
    # The command is fixed text; nothing in it comes from a request.
    done = subprocess.run(prepare, env=owner, check=False)  # noqa: S603
    if done.returncode != 0:
        return done.returncode
    sys.stdout.flush()
    os.execvpe(arguments[0], list(arguments), service_environment(os.environ))  # noqa: S606


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
