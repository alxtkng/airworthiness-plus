"""How a line of the server log is written (OWASP ASVS 5.0, 16.2.2, 16.2.4).

Each event is one line. A traceback, or a value with a line break in it,
is kept on that line with each break written as \\n, so a log reader sees
one event per line and a value sent by a visitor cannot start a line of
its own (corrected 20 November 2026: a traceback ran over many lines).
"""

import logging
import time


class UtcFormatter(logging.Formatter):
    """Write each event on one line, the time in Coordinated Universal Time."""

    converter = time.gmtime  # type: ignore[assignment]
    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03dZ"

    def format(self, record: logging.LogRecord) -> str:
        """Return the event as one line."""
        text = super().format(record)
        return text.replace("\r", "\\r").replace("\n", "\\n")
