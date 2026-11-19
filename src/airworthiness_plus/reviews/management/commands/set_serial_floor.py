"""State the highest certificate serial an organisation has issued (REQ-154).

    AIRWORTHINESS_DATABASE_OWNER_WORK=true python -m django set_serial_floor <organisation> <serial>

Run by the owner of the records after a restore from backup, before the
service is opened again. Certificates issued after the backup was taken
are no longer in the records, but they exist: on paper, and in the copies
sent to the Civil Aviation Authority. The organisation states the highest
serial it has issued, and the next certificate follows it. The serial can
be raised and never lowered, and the change is in the history.
"""

import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import DatabaseError

from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.reviews.models import Certificate


class Command(BaseCommand):
    """Raise the serial that the next certificate must follow."""

    help = "State the highest certificate serial an organisation has issued."

    def add_arguments(self, parser: CommandParser) -> None:
        """Take the organisation identifier and the serial."""
        parser.add_argument("organisation", type=uuid.UUID)
        parser.add_argument("serial", type=int)

    def handle(self, *args: Any, **options: Any) -> None:
        """Set the floor, and say what the next serial will be."""
        identifier, serial = options["organisation"], options["serial"]
        if serial < 0:
            raise CommandError("A serial is not below zero")
        with working_for(identifier):
            organisation = Organisation.objects.filter(pk=identifier).first()
            if organisation is None:
                raise CommandError("No such organisation")
            recorded = max(
                (
                    number
                    for number in Certificate.objects.values_list("serial_number", flat=True)
                    if number is not None
                ),
                default=0,
            )
            if serial < organisation.certificate_serial_floor:
                raise CommandError(
                    f"The highest serial stated is already {organisation.certificate_serial_floor}"
                )
            organisation.certificate_serial_floor = serial
            try:
                organisation.save(update_fields=["certificate_serial_floor"])
            except DatabaseError as error:
                raise CommandError(str(error).splitlines()[0]) from error
        self.stdout.write(f"Highest Serial in the Records {recorded}")
        self.stdout.write(f"Highest Serial Stated {serial}")
        self.stdout.write(f"Next Serial {max(recorded, serial) + 1}")
