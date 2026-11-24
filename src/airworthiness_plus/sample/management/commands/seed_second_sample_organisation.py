"""Set up the second sample organisation of design-system/SampleData.md (REQ-218).

    AIRWORTHINESS_DATABASE_OWNER_WORK=true python manage.py seed_second_sample_organisation

Run once, by the owner of the tables, on a system that holds no real
records. It makes an organisation that holds Part-CAMO and Part-145, its
Administrator with the password typed at the prompt, its other users with
no password, its people, two customers and two aircraft.

Every name that is not real is in square brackets.
"""

import getpass
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.sample import second


class Command(BaseCommand):
    """Create the second sample organisation and its records."""

    help = "Set up the second sample organisation, which holds Part-CAMO and Part-145."

    def handle(self, *args: Any, **options: Any) -> None:
        """Ask for the Administrator's password, then build the sample."""
        if Organisation.objects.filter(approval_reference=second.APPROVAL_REFERENCE).exists():
            raise CommandError("The second sample organisation is already set up")
        password = getpass.getpass("Administrator Password: ")
        if password != getpass.getpass("Administrator Password Again: "):
            raise CommandError("The two passwords differ")
        organisation = second.seed(password)
        self.stdout.write(f"Organisation {organisation.id}")
        self.stdout.write(f"Administrator {second.ADMINISTRATOR}")
        self.stdout.write("5 People, 2 Customers, 2 Aircraft")
