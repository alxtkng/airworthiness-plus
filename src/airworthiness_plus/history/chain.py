"""Check the hash chain of the history (threats TH-021, TH-025).

The hash of an entry is the SHA-256, in hexadecimal, of these twelve
fields in this order, each written as its length in bytes of UTF-8, a
colon, the value and a comma:

1. the hash of the entry before it for the same record, or nothing
2. the organisation identifier
3. the record type
4. the record identifier
5. the sequence number, starting at 1
6. the action
7. the identifier of the user who made the change, or nothing
8. the name of that user
9. the time in Coordinated Universal Time, as 2026-11-18T09:30:00.000000Z
10. the names of the columns that changed, joined by commas
11. the record before the change, exactly as stored, or nothing
12. the record after the change, exactly as stored

The database computes the hash when it writes the entry. This module
computes it again, separately, from what is stored.
"""

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC

from airworthiness_plus.history.models import HASH_ALGORITHM, Event


@dataclass(frozen=True)
class ChainProblem:
    """One entry of the history that does not agree with the chain."""

    event_id: int
    reason: str


def expected_hash(event: Event) -> str:
    """Return the hash the entry should carry, from its stored fields."""
    fields = (
        event.previous_hash,
        str(event.organisation_id),
        event.record_type,
        str(event.record_id),
        str(event.sequence),
        event.action,
        str(event.actor_id) if event.actor_id is not None else "",
        event.actor_name,
        event.at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        ",".join(event.changed),
        event.before_json or "",
        event.after_json or "",
    )
    payload = "".join(f"{len(field.encode())}:{field}," for field in fields)
    return hashlib.sha256(payload.encode()).hexdigest()


def problems(events: Iterable[Event]) -> list[ChainProblem]:
    """Return every entry that breaks the chain. An empty list means it holds.

    For each record the sequence must run 1, 2, 3 with none missing, each
    entry must carry the hash of the one before it, and each hash must be
    the one its fields give. Entries removed from the end of a record's
    history cannot be seen from the chain alone; that needs the off-server
    backup (threat TH-025).
    """
    found: list[ChainProblem] = []
    ordered = sorted(
        events, key=lambda e: (str(e.organisation_id), e.record_type, str(e.record_id), e.sequence)
    )
    previous: Event | None = None
    for event in ordered:
        same_record = previous is not None and (
            previous.organisation_id,
            previous.record_type,
            previous.record_id,
        ) == (event.organisation_id, event.record_type, event.record_id)
        expected_sequence = previous.sequence + 1 if same_record and previous else 1
        expected_previous = previous.hash if same_record and previous else ""
        if event.sequence != expected_sequence:
            found.append(ChainProblem(event.pk, "An entry is missing before this one"))
        elif event.previous_hash != expected_previous:
            found.append(ChainProblem(event.pk, "Does not follow the entry before it"))
        if event.hash_algorithm != HASH_ALGORITHM:
            found.append(ChainProblem(event.pk, "Was hashed in a way this version does not know"))
        elif event.hash != expected_hash(event):
            found.append(ChainProblem(event.pk, "Has been altered since it was written"))
        previous = event
    return found
