"""Check an export against itself (threat TH-081, planned test T-SEC-019).

This module uses only the Python standard library and nothing else of the
system, so that whoever receives an export can run it, or write the same
check from the description in the export's README.

It answers one question: is this file as the system wrote it? Every file
must have the SHA-256 the manifest gives it, every entry of the history
must carry the hash its fields give and follow the entry before it, and
every record must be what the last entry of its history says. A file
altered by someone who then recalculates every hash still agrees with
itself; that is caught by comparing the SHA-256 of the manifest with the
one the system logged when it made the export.
"""

import hashlib
import io
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from typing import Any

MANIFEST = "manifest.json"
# The one way a history entry has been hashed so far. An entry that names
# another is reported, not guessed at.
ALGORITHM = "sha256-fields-1"
HASHED_FIELDS = (
    "previous_hash",
    "organisation_id",
    "record_type",
    "record_id",
    "sequence",
    "action",
    "actor_id",
    "actor_name",
    "at",
    "changed",
    "before",
    "after",
)


@dataclass(frozen=True)
class Verdict:
    """What the check found. No problems means the export agrees with itself."""

    manifest_sha256: str
    problems: tuple[str, ...]


def entry_hash(entry: dict[str, Any]) -> str:
    """Return the hash an entry of the history should carry, from its fields.

    The twelve fields in order, each written as its length in bytes of
    UTF-8, a colon, the value and a comma. Nothing is written as an empty
    value; the changed columns are joined by commas.
    """
    payload = ""
    for name in HASHED_FIELDS:
        value = entry[name]
        if name == "changed":
            text = ",".join(value)
        elif value is None:
            text = ""
        else:
            text = str(value)
        payload += f"{len(text.encode())}:{text},"
    return hashlib.sha256(payload.encode()).hexdigest()


def _history_problems(name: str, entries: list[dict[str, Any]]) -> list[str]:
    problems = []
    previous: dict[str, Any] | None = None
    for entry in entries:
        label = f"{name}, record {entry['record_id']}, entry {entry['sequence']}"
        same = previous is not None and previous["record_id"] == entry["record_id"]
        expected_sequence = previous["sequence"] + 1 if same and previous else 1
        expected_previous = previous["hash"] if same and previous else ""
        if entry["sequence"] != expected_sequence:
            problems.append(f"{label}: an entry is missing before this one")
        elif entry["previous_hash"] != expected_previous:
            problems.append(f"{label}: does not follow the entry before it")
        if entry.get("hash_algorithm", ALGORITHM) != ALGORITHM:
            problems.append(f"{label}: was hashed in a way this check does not know")
        elif entry["hash"] != entry_hash(entry):
            problems.append(f"{label}: has been altered since it was written")
        previous = entry
    return problems


def _record_problems(
    name: str, records: list[dict[str, Any]], entries: list[dict[str, Any]]
) -> list[str]:
    last: dict[str, dict[str, Any]] = {}
    for entry in entries:
        last[entry["record_id"]] = json.loads(entry["after"])
    problems = [
        f"{name}, record {record['id']}: is not what the last entry of its history says"
        for record in records
        if last.get(record["id"]) != record
    ]
    if len(records) != len(last):
        problems.append(f"{name}: the records and the history are not of the same records")
    return problems


def verify(content: bytes) -> Verdict:
    """Check an export, given as the bytes of the file."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
        manifest_bytes = archive.read(MANIFEST)
        manifest = json.loads(manifest_bytes)
        listed: dict[str, str] = manifest["files"]
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError):
        return Verdict("", ("This is not an export of records, or its manifest cannot be read",))
    problems: list[str] = []
    # Two files of one name: a reader may open either, and only the last is
    # checked below, so the export cannot be said to be as it was written.
    names = archive.namelist()
    for name in sorted(name for name, count in Counter(names).items() if count > 1):
        problems.append(f"{name}: is in the export more than once")
    present = set(names) - {MANIFEST}
    for name in sorted(present - set(listed)):
        problems.append(f"{name}: is not in the manifest")
    for name in sorted(set(listed) - present):
        problems.append(f"{name}: is in the manifest and not in the export")
    files: dict[str, bytes] = {}
    for name in sorted(present & set(listed)):
        files[name] = archive.read(name)
        if hashlib.sha256(files[name]).hexdigest() != listed[name]:
            problems.append(f"{name}: has been altered since the export was made")
    for name, data in files.items():
        if not name.startswith("history/"):
            continue
        table = name.removeprefix("history/").removesuffix(".json")
        try:
            entries = json.loads(data)
            records = json.loads(files[f"records/{table}.json"])
            problems += _history_problems(table, entries)
            problems += _record_problems(table, records, entries)
        except (KeyError, ValueError, TypeError):
            problems.append(f"{table}: its records or its history cannot be read")
    return Verdict(hashlib.sha256(manifest_bytes).hexdigest(), tuple(problems))
