"""Airworthiness review certificate rules for Part-ML aircraft.

Source: UK Regulation (EU) No 1321/2014, ML.A.901 and ML.A.903, read in the
Civil Aviation Authority Regulatory Library on 18 November 2026.
"""

from datetime import date

from airworthiness_rules.dates import add_days, add_years, days_between

VALIDITY_YEARS = 1
"""ML.A.901(a): the certificate is valid for 1 year."""

REVIEW_ANTICIPATION_DAYS = 90
"""ML.A.903(d): the review may be anticipated by at most 90 days without
loss of continuity of the airworthiness review pattern."""

EXTENSION_ANTICIPATION_DAYS = 30
"""ML.A.901(d): the extension may be anticipated by at most 30 days without
loss of continuity of the airworthiness review pattern."""

MAX_CONSECUTIVE_EXTENSIONS = 2
"""ML.A.901(c): at most two consecutive extensions, one year each."""

COPY_TO_AUTHORITY_DAYS = 10
"""ML.A.903(f): a copy goes to the Civil Aviation Authority within 10 days
of the date of issue or extension."""


class ExtensionNotPermittedError(ValueError):
    """The extension asked for is outside what ML.A.901(c) and (d) allow."""


def days_to_expiry(today: date, valid_to: date) -> int:
    """Return the exact days from ``today`` to the last day of validity (REQ-100)."""
    return days_between(today, valid_to)


def review_keeps_pattern(reviewed: date, valid_to: date) -> bool:
    """Return whether a review on ``reviewed`` keeps the review pattern (REQ-102).

    True from 90 days before expiry up to and including the expiry date.
    """
    return 0 <= days_between(reviewed, valid_to) <= REVIEW_ANTICIPATION_DAYS


def valid_to_after_review(reviewed: date, previous_valid_to: date | None) -> date:
    """Return the last day of validity of a certificate issued after a review.

    Inside the 90-day window the new date is 1 year after the previous one,
    whatever day the review was done (REQ-102, ML.A.903(d)).

    Otherwise (first certificate, review more than 90 days early, or review
    after expiry) the certificate is valid for 1 year from the review
    (REQ-101, ML.A.901(a)). Whether that year ends on the anniversary or the
    day before is REQ-103, still To Be Checked; the anniversary is used.
    """
    if previous_valid_to is not None and review_keeps_pattern(reviewed, previous_valid_to):
        return add_years(previous_valid_to, VALIDITY_YEARS)
    return add_years(reviewed, VALIDITY_YEARS)


def valid_to_after_extension(extended: date, valid_to: date, consecutive_extensions: int) -> date:
    """Return the last day of validity after an extension (REQ-104, REQ-106).

    ``consecutive_extensions`` is the number of extensions already made since
    the last full review. A third is refused (ML.A.901(c)). An extension is
    accepted from 30 days before expiry up to and including the expiry date
    (ML.A.901(d)); the new date is 1 year after the previous one.
    """
    if consecutive_extensions < 0:
        raise ValueError("consecutive_extensions cannot be negative")
    if consecutive_extensions >= MAX_CONSECUTIVE_EXTENSIONS:
        raise ExtensionNotPermittedError(
            "ML.A.901(c): a certificate may be extended at most two consecutive times"
        )
    remaining = days_between(extended, valid_to)
    if remaining > EXTENSION_ANTICIPATION_DAYS:
        raise ExtensionNotPermittedError(
            "ML.A.901(d): an extension may be anticipated by at most 30 days"
        )
    if remaining < 0:
        raise ExtensionNotPermittedError("The certificate has expired; a review is needed")
    return add_years(valid_to, VALIDITY_YEARS)


def copy_to_authority_deadline(issued_or_extended: date) -> date:
    """Return the last day to send the copy to the Civil Aviation Authority (REQ-111)."""
    return add_days(issued_or_extended, COPY_TO_AUTHORITY_DAYS)
