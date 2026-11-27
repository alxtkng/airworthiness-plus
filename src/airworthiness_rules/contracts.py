"""Continuing airworthiness management contracts (REQ-240 to REQ-249).

UK Regulation (EU) No 1321/2014, Appendix I to Annex Vb (Part-ML), read in
the Civil Aviation Authority Regulatory Library on 27 November 2026. The
contract states: "In case of any non-conformity with this contract, by
either of the signatories, the contract will become null. In such a case,
the owner will retain full responsibility for every task linked to the
continuing airworthiness of the aircraft, and the owner will inform the
CAA within 2 weeks about the termination of the contract."

The appendix also has the organisation and the owner each inform the Civil
Aviation Authority whenever the contract is denounced by either party. It
gives no period for that.

Ours, not the regulation's: 2 weeks are counted as 14 days from the day
the contract ended.
"""

from datetime import date

from airworthiness_rules.dates import add_days

OWNER_NOTICE_DAYS = 14
"""Appendix I to Part-ML: the owner informs the CAA within 2 weeks. Counted as 14 days."""


def owner_notice_deadline(ended_on: date) -> date:
    """Return the last day for the owner to tell the Civil Aviation Authority (REQ-243).

    For a contract that became null through non-conformity: 2 weeks from
    the day it ended.
    """
    return add_days(ended_on, OWNER_NOTICE_DAYS)


def in_force(signed_on: date, ended_on: date | None, day: date) -> bool:
    """Return whether a contract signed and ended on these days was in force on ``day``.

    From the day it was signed up to and including the day it ended.
    """
    if ended_on is not None and ended_on < signed_on:
        raise ValueError("A contract does not end before it is signed")
    return signed_on <= day and (ended_on is None or day <= ended_on)
