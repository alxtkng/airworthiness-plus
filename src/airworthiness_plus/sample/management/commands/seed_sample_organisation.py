"""Set up the sample organisation of design-system/SampleData.md (Step 9 of private beta).

    AIRWORTHINESS_DATABASE_OWNER_WORK=true python manage.py seed_sample_organisation

Run once, by the owner of the tables, on a system that holds no real
records. It makes the organisation, its Administrator with the password
typed at the prompt, one user for each other role with no password, and
the fleet with its programmes, directives, maintenance data and review
certificates. The Administrator then gives the other users their first
passwords on the Users page.

Every name that is not real is in square brackets, and the records are
dated for the sample world, in which today is 18 November 2026.
"""

import getpass
from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.sample import build

ADMINISTRATOR = "accountable.manager@your-organisation.example"


def seed(password: str) -> Organisation:
    """Build the sample organisation, with ``password`` for its Administrator."""
    try:
        with transaction.atomic():
            organisation, administrator = provision_organisation(
                name=build.NAME,
                approval_reference=build.APPROVAL_REFERENCE,
                address=build.ADDRESS,
                privileges=list(Privilege),
                scope_of_work=build.SCOPE,
                first_user_username=ADMINISTRATOR,
                first_user_full_name="[Accountable Manager]",
                first_user_password=password,
            )
            build.build(organisation, administrator)
    except ValidationError as error:
        raise CommandError("; ".join(error.messages)) from error
    return organisation


class Command(BaseCommand):
    """Create the sample organisation and its records."""

    help = "Set up the sample organisation of design-system/SampleData.md."

    def handle(self, *args: Any, **options: Any) -> None:
        """Ask for the Administrator's password, then build the sample."""
        if Organisation.objects.filter(approval_reference=build.APPROVAL_REFERENCE).exists():
            raise CommandError("The sample organisation is already set up")
        password = getpass.getpass("Administrator Password: ")
        if password != getpass.getpass("Administrator Password Again: "):
            raise CommandError("The two passwords differ")
        organisation = seed(password)
        self.stdout.write(f"Organisation {organisation.id}")
        self.stdout.write(f"Administrator {ADMINISTRATOR}")
        self.stdout.write("7 Aircraft, 4 Directives, 4 Sets of Maintenance Data, 7 Certificates")
