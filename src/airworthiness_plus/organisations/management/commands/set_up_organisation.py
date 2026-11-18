"""Set up a new organisation and its Administrator, from the command line.

Run as the owner of the tables, by Airworthiness Limited, once for each
organisation:

    AIRWORTHINESS_DATABASE_OWNER_WORK=true python manage.py set_up_organisation

The password is typed at a prompt and is never an argument, so it is not
left in the shell history or the process list.
"""

import getpass
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from airworthiness_plus.organisations.models import Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation


class Command(BaseCommand):
    """Create one organisation and its first user."""

    help = "Set up a new organisation and its Administrator."

    def handle(self, *args: Any, **options: Any) -> None:
        """Ask for the details, then create the organisation."""
        name = input("Organisation Name: ").strip()
        reference = input("Approval Reference: ").strip()
        scope = input("Scope of Work: ").strip()
        privileges = [
            privilege
            for privilege in Privilege
            if input(f"Privilege, {privilege.label} (Yes or No): ").strip() == "Yes"
        ]
        full_name = input("Administrator Full Name: ").strip()
        username = input("Administrator User Name: ").strip()
        password = getpass.getpass("Administrator Password: ")
        if password != getpass.getpass("Administrator Password Again: "):
            raise CommandError("The two passwords differ")
        try:
            organisation, user = provision_organisation(
                name=name,
                approval_reference=reference,
                privileges=privileges,
                scope_of_work=scope,
                first_user_username=username,
                first_user_full_name=full_name,
                first_user_password=password,
            )
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error
        self.stdout.write(f"Organisation {organisation.id}")
        self.stdout.write(f"Administrator {user.id}")
