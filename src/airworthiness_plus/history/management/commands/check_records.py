"""Check the records of every organisation the database role can see (REQ-153).

    AIRWORTHINESS_DATABASE_OWNER_WORK=true python -m django check_records

Run after a restore from backup, and on a schedule, by a role that can
read every organisation's records: the backup role, which reads and never
writes. For each organisation it checks that the hash chain of the
history holds, that every record has its history and every history its
record, and reports the certificate serials. It changes nothing. It ends
with an error if anything is wrong, or if it could see no organisation.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from airworthiness_plus.exports.registry import REGISTRY
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event


class Command(BaseCommand):
    """Check the hash chain and the completeness of the history."""

    help = "Check the records and their history for every organisation that can be seen."

    def handle(self, *args: Any, **options: Any) -> None:
        """Print one line for each organisation, then the verdict."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id::text, certificate_serial_floor FROM organisations_organisation "
                "ORDER BY id"
            )
            organisations = cursor.fetchall()
        if not organisations:
            raise CommandError("No organisation can be seen by this database role")
        wrong = 0
        for identifier, floor in organisations:
            events = list(Event.objects.filter(organisation_id=identifier))
            problems = chain.problems(events)
            mismatched = []
            with connection.cursor() as cursor:
                for exported in REGISTRY:
                    column = (
                        "id"
                        if exported.table == "organisations_organisation"
                        else "organisation_id"
                    )
                    cursor.execute(
                        f"SELECT count(*) FROM {exported.table} WHERE {column} = %s",  # noqa: S608
                        [identifier],
                    )
                    held = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT count(DISTINCT record_id) FROM history_event "
                        "WHERE organisation_id = %s AND record_type = %s",
                        [identifier, exported.table],
                    )
                    if cursor.fetchone()[0] != held:
                        mismatched.append(exported.table)
                cursor.execute(
                    "SELECT COALESCE(max(serial_number), 0) FROM reviews_certificate "
                    "WHERE organisation_id = %s",
                    [identifier],
                )
                serial = cursor.fetchone()[0]
            wrong += len(problems) + len(mismatched)
            self.stdout.write(
                f"Organisation {identifier}: {len(events)} History Entries, "
                f"{len(problems)} Chain Problems, "
                f"{len(mismatched)} Record Types Not Matching Their History, "
                f"Highest Certificate Serial {serial}, Highest Serial Stated {floor}"
            )
            for problem in problems:
                self.stderr.write(f"  History entry {problem.event_id}: {problem.reason}")
            for table in mismatched:
                self.stderr.write(f"  {table}: records and history are not of the same records")
        if wrong:
            raise CommandError("The records do not agree with their history")
        self.stdout.write("The Records Agree with Their History")
