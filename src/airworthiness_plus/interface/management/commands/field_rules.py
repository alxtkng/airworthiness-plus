"""Write the table of what each action may set into architecture/fields-by-action.md."""

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from airworthiness_plus.interface.field_rules import with_table

DOCUMENT = Path(settings.BASE_DIR).parent.parent / "architecture" / "fields-by-action.md"


class Command(BaseCommand):
    help = "Make the table in architecture/fields-by-action.md afresh from the code."

    def handle(self, *args: Any, **options: Any) -> None:
        DOCUMENT.write_text(with_table(DOCUMENT.read_text()))
        self.stdout.write(f"Written {DOCUMENT.name}")
