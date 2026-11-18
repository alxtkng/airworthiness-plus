"""The parallel run before an organisation relies on the system (REQ-173).

The organisation runs the system beside its existing records for 6
months. The day the 6 months pass is the same day of the month 6 months
after the start, or the last day of that month if it is shorter.
"""

from datetime import date

from airworthiness_rules.dates import add_months

PARALLEL_RUN_MONTHS = 6


def parallel_run_passes_on(started_on: date) -> date:
    """Return the day on which 6 months of parallel running have passed."""
    return add_months(started_on, PARALLEL_RUN_MONTHS)


def parallel_run_passed(started_on: date, today: date) -> bool:
    """Return whether 6 months of parallel running have passed by ``today``."""
    return today >= parallel_run_passes_on(started_on)
