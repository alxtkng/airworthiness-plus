"""Read deployment values from the environment.

Every value that differs between deployments, and every secret, comes from
the environment and never from the repository (assurance case C5.4, threat
TH-063). A missing required value stops the application from starting.
"""

import os

from django.core.exceptions import ImproperlyConfigured


def required(name: str) -> str:
    """Return the value of ``name``, or refuse to start if it is not set."""
    value = os.environ.get(name, "")
    if not value:
        raise ImproperlyConfigured(f"{name} must be set in the environment")
    return value


def optional(name: str) -> str:
    """Return the value of ``name``, or an empty string."""
    return os.environ.get(name, "")


def flag(name: str) -> bool:
    """Return whether ``name`` is set to exactly "true". Anything else is off."""
    return os.environ.get(name, "") == "true"


def listed(name: str) -> list[str]:
    """Return the comma-separated values of ``name``, without blanks."""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]
