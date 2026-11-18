#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Run a management command with the application settings."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "airworthiness_plus.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
