"""Check an export of records against itself.

    python manage.py verify_export G-EJKL-records-2026-11-18.zip

Needs no database. Compare the SHA-256 it prints with the one on the
Records Export page of the system that made the export.
"""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from airworthiness_plus.exports.verify import verify


class Command(BaseCommand):
    """Check one export file."""

    help = "Check an export of records against itself."
    requires_system_checks: Any = []

    def add_arguments(self, parser: CommandParser) -> None:
        """Take the path of the export."""
        parser.add_argument("path")

    def handle(self, *args: Any, **options: Any) -> None:
        """Print what the check found, and fail if it found anything."""
        verdict = verify(Path(options["path"]).read_bytes())
        for problem in verdict.problems:
            self.stderr.write(problem)
        if verdict.problems:
            raise CommandError("The export does not agree with itself")
        self.stdout.write("The export agrees with itself")
        self.stdout.write(f"Manifest SHA-256 {verdict.manifest_sha256}")
