"""Reconstruct the synthetic aircraft handover in a separate SQLite receiver."""

import argparse
import hashlib
import io
import json
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from airworthiness_plus.exports.verify import verify


class TransferError(ValueError):
    """The receiver could not reconcile this aircraft transfer."""


def _records(archive: ZipFile, table: str, organisation_id: str) -> dict[str, dict[str, Any]]:
    if f"history/{table}.json" not in archive.namelist():
        raise TransferError(f"Missing history for {table}")
    rows = json.loads(archive.read(f"records/{table}.json"))
    indexed = {row["id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise TransferError(f"Duplicate record in {table}")
    if any(row["organisation_id"] != organisation_id for row in rows):
        raise TransferError(f"Wrong organisation in {table}")
    return indexed


def _related(row: dict[str, Any], key: str, parent: dict[str, Any]) -> None:
    if row[key] != parent["id"]:
        raise TransferError(f"Incorrect or missing dependency for {key}")


def read_transfer(
    content: bytes,
    *,
    expected_digest: str,
    aircraft_id: str,
    defect_id: str,
    inspection_id: str,
    correction_id: str,
) -> dict[str, Any]:
    """Compare the received manifest digest and reconstruct the three pilot records."""
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            manifest_bytes = archive.read("manifest.json")
            if hashlib.sha256(manifest_bytes).hexdigest() != expected_digest:
                raise TransferError("Manifest digest differs from the separately supplied value")
            manifest = json.loads(manifest_bytes)
            if manifest["format"] != "Airworthiness+ Records Export" or manifest["version"] != 1:
                raise TransferError("Unsupported aircraft archive format or version")
            if not manifest["aircraft"] or manifest["aircraft"]["id"] != aircraft_id:
                raise TransferError("The archive is for a different aircraft")
            verdict = verify(content)
            if verdict.problems:
                raise TransferError("; ".join(verdict.problems))
            issuer = manifest["organisation"]["id"]
            aircraft = _records(archive, "aircraft_aircraft", issuer)[aircraft_id]
            if aircraft["registration"] != manifest["aircraft"]["registration"]:
                raise TransferError("Aircraft registration differs from the manifest")
            defect = _records(archive, "defects_defect", issuer)[defect_id]
            _related(defect, "aircraft_id", aircraft)
            if defect["closed_on"] is not None or defect["decision"] != "Deferred":
                raise TransferError("The trial defect is not open and deferred")
            date.fromisoformat(defect["limit_on"])

            task = _records(archive, "programme_task", issuer)[inspection_id]
            programme = _records(archive, "programme_programme", issuer)[task["programme_id"]]
            _related(programme, "aircraft_id", aircraft)
            completions = [
                record
                for record in _records(archive, "programme_workdone", issuer).values()
                if record["task_id"] == inspection_id
            ]
            if not completions or any(
                record["aircraft_id"] != aircraft_id for record in completions
            ):
                raise TransferError("The inspection has no matching aircraft completion")
            completion = max(completions, key=lambda record: date.fromisoformat(record["dated"]))
            days = task["interval_days"]
            if (
                type(days) is not int
                or days <= 0
                or any(
                    task[f"interval_{unit}"] is not None for unit in ("months", "hours", "cycles")
                )
            ):
                raise TransferError("The receiver pilot supports inspections with a day interval")
            next_due = date.fromisoformat(completion["dated"]) + timedelta(days=days)

            readings = _records(archive, "aircraft_utilisationentry", issuer)
            correction = readings[correction_id]
            original = readings[correction["supersedes_id"]]
            counter = _records(archive, "aircraft_counter", issuer)[task["counter_id"]]
            _related(counter, "aircraft_id", aircraft)
            _related(correction, "counter_id", counter)
            _related(original, "counter_id", counter)
            selected = {
                "aircraft_aircraft": {aircraft_id},
                "aircraft_counter": {counter["id"]},
                "aircraft_utilisationentry": {original["id"], correction_id},
                "defects_defect": {defect_id},
                "programme_programme": {programme["id"]},
                "programme_task": {inspection_id},
                "programme_workdone": {completion["id"]},
            }
            history = {
                table: [
                    entry
                    for entry in json.loads(archive.read(f"history/{table}.json"))
                    if entry["record_id"] in identifiers
                ]
                for table, identifiers in selected.items()
            }
            return {
                "source_organisation_id": issuer,
                "aircraft": aircraft,
                "defect": defect,
                "inspection": task,
                "last_completion": completion,
                "next_due": next_due.isoformat(),
                "original_reading": original,
                "corrected_reading": correction,
                "issuer_trust": "Indeterminate",
                "signature": "Unsigned Utilisation Correction",
                "history": history,
                "manifest_sha256": expected_digest,
            }
    except TransferError:
        raise
    except (AttributeError, BadZipFile, KeyError, OverflowError, TypeError, ValueError) as error:
        raise TransferError("Missing or invalid record or dependency in trial archive") from error


def import_transfer(database: Path, received: dict[str, Any]) -> bool:
    """Store a reconciled snapshot once. Return False when the snapshot was already imported."""
    content = json.dumps(received, sort_keys=True, separators=(",", ":"))
    issuer = received["source_organisation_id"]
    aircraft_id = received["aircraft"]["id"]
    with closing(sqlite3.connect(database, isolation_level="IMMEDIATE")) as connection, connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS handover (
                issuer TEXT NOT NULL,
                aircraft_id TEXT NOT NULL,
                evidence TEXT NOT NULL,
                PRIMARY KEY (issuer, aircraft_id)
            )"""
        )
        inserted = connection.execute(
            "INSERT INTO handover VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
            (issuer, aircraft_id, content),
        )
        if inserted.rowcount == 1:
            return True
        (existing,) = connection.execute(
            "SELECT evidence FROM handover WHERE issuer = ? AND aircraft_id = ?",
            (issuer, aircraft_id),
        ).fetchone()
        if existing != content:
            raise TransferError("Existing aircraft snapshot differs and needs reconciliation")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("database", type=Path)
    parser.add_argument("--manifest-digest", required=True)
    parser.add_argument("--aircraft-id", required=True)
    parser.add_argument("--defect-id", required=True)
    parser.add_argument("--inspection-id", required=True)
    parser.add_argument("--correction-id", required=True)
    parser.add_argument("--signatures", type=Path, help="Detached synthetic reading signatures")
    parser.add_argument("--trust", type=Path, help="Trust file supplied by the trial custodian")
    parser.add_argument(
        "--trust-sha256", help="Trust digest supplied independently to the receiver"
    )
    parser.add_argument("--timestamps", type=Path, help="RFC 3161 responses for both signatures")
    parser.add_argument(
        "--tsa-root", type=Path, help="TSA root certificate from the trust custodian"
    )
    parser.add_argument("--tsa-root-sha256", help="TSA root digest supplied independently")
    options = parser.parse_args()
    signing = (options.signatures, options.trust, options.trust_sha256)
    if any(value is not None for value in signing) and not all(signing):
        parser.error("Signed import requires --signatures, --trust and --trust-sha256")
    timing = (options.timestamps, options.tsa_root, options.tsa_root_sha256)
    if any(value is not None for value in timing) and (not all(timing) or not all(signing)):
        parser.error(
            "Timestamped import requires signed evidence, --timestamps, --tsa-root "
            "and --tsa-root-sha256"
        )
    try:
        received = read_transfer(
            options.archive.read_bytes(),
            expected_digest=options.manifest_digest,
            aircraft_id=options.aircraft_id,
            defect_id=options.defect_id,
            inspection_id=options.inspection_id,
            correction_id=options.correction_id,
        )
        if options.signatures is not None:
            from verify_handover_signatures import verify_signatures

            received.update(
                verify_signatures(
                    received,
                    options.signatures.read_bytes(),
                    options.trust.read_bytes(),
                    options.trust_sha256,
                )
            )
        if options.timestamps is not None:
            from verify_handover_timestamps import verify_timestamps

            received.update(
                verify_timestamps(
                    received["signatures"],
                    options.timestamps.read_bytes(),
                    options.tsa_root.read_bytes(),
                    options.tsa_root_sha256,
                )
            )
        imported = import_transfer(options.database, received)
    except (OSError, sqlite3.Error, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps({"imported": imported, **received}, indent=2))


if __name__ == "__main__":
    main()
