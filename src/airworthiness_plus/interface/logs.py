"""How a line of the server log is written (OWASP ASVS 5.0, 16.2.2)."""

import logging
import time


class UtcFormatter(logging.Formatter):
    """Write the time of each line in Coordinated Universal Time, as 2026-11-18T09:30:00Z."""

    converter = time.gmtime  # type: ignore[assignment]
    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03dZ"
