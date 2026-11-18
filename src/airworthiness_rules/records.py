"""Deadlines for entries in the continuing airworthiness records."""

from datetime import date

from airworthiness_rules.dates import add_days

RELEASE_RECORD_DAYS = 30
"""ML.A.305(a): the certificate of release to service is entered not later
than 30 days after the day the maintenance task is completed."""


def release_record_deadline(completed: date) -> date:
    """Return the last day for the release to service to be in the records (REQ-051)."""
    return add_days(completed, RELEASE_RECORD_DAYS)
