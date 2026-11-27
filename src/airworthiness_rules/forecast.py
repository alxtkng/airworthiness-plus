"""The forecast of an aircraft: when each thing is expected to fall due (REQ-291).

A projection for planning only, never a limit: a thing is due when its
limit is reached, whatever the forecast says (REQ-044). Ours, not the
regulation's (design-system/Decisions.md, Canvas Build, Phase 1).
"""

from datetime import date

from airworthiness_rules.dates import add_days, days_between

WINDOW_DAYS = 120
"""Ours, from the Aircraft board: Next 120 Days."""


def forecast_date(today: date, days: int | None) -> date | None:
    """Return the day a limit is expected to be reached, or None if it cannot be placed.

    ``days`` is the whole days to the limit: the days to a calendar limit,
    or the projected days to a limit in hours or cycles, which are rounded
    down so that the forecast is never late. A limit already reached or
    passed is forecast for today.
    """
    if days is None:
        return None
    return today if days <= 0 else add_days(today, days)


def within_window(today: date, forecast: date | None, window: int = WINDOW_DAYS) -> bool:
    """Return whether a forecast falls within the window: today to ``window`` days on.

    What cannot be placed is not within it; it is shown apart.
    """
    if window < 0:
        raise ValueError("A window is not below zero days")
    return forecast is not None and 0 <= days_between(today, forecast) <= window
