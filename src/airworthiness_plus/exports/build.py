"""Build the export of an aircraft's record or an organisation's (REQ-134, REQ-135).

The export is a ZIP file of JSON and CSV, described in the README it
carries. What it says of each record is taken from the history, the same
history the pages show: a record is what the last entry of its history
says, and every entry is included with its hash, so that the export can be
checked against itself and against the system (threat TH-081).
"""

import csv
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from django.db.models import Q

from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.defects.models import Defect
from airworthiness_plus.exports.registry import REGISTRY
from airworthiness_plus.exports.verify import MANIFEST
from airworthiness_plus.history.models import Event
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person
from airworthiness_plus.planning.models import WorkCard
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.releases.models import Release
from airworthiness_plus.reviews.models import ReviewStaff
from airworthiness_rules.dates import utc_now

FORMAT = "Airworthiness+ Records Export"
VERSION = 1
STAMP = "%Y-%m-%dT%H:%M:%S.%fZ"

README = """\
Airworthiness+ Records Export, Version 1

This file is a ZIP archive. Every file in it is text in UTF-8.

manifest.json
    What was exported, for which organisation, when (Coordinated Universal
    Time) and by whom; how many records and history entries of each type;
    and the SHA-256 of every other file in the archive.

records/<type>.json
    Every record of that type, as it stands. A record is exactly what the
    last entry of its history says. Dates are written as 2026-11-18. Hours
    are written as text with one decimal place, for example "11206.8".

records/<type>.csv
    The same records for reading in a spreadsheet. A value beginning with
    =, +, - or @ has an apostrophe put before it so that a spreadsheet
    does not run it as a formula. The JSON file is the record; the CSV is
    a convenience.

history/<type>.json
    Every entry in the history of those records, oldest first for each
    record. Nothing is ever deleted: a record that was changed or
    superseded keeps every earlier entry. Each entry has:
        organisation_id, record_type, record_id
        sequence        1 for the first entry of a record, then 2, 3
        action          Created or Changed
        actor_id, actor_name   who made the change
        at              when, as 2026-11-18T09:30:00.000000Z
        changed         the names of the columns that changed
        before, after   the record before and after, as text, exactly as stored
        previous_hash   the hash of the entry before it for the same record
        hash            the hash of this entry
        hash_algorithm  how the hash was made; sha256-fields-1 is the method below

people.json (in the export of an aircraft)
    The name of each person the records refer to by an identifier.

access-log.json (in the export of an organisation)
    Every sign-in, failed sign-in, refused action and export.

To check the export
    1. The SHA-256 of each file is the one given in manifest.json.
    2. The hash of each history entry is the SHA-256, in hexadecimal, of
       these twelve fields in this order: previous_hash, organisation_id,
       record_type, record_id, sequence, action, actor_id, actor_name, at,
       changed, before, after. Each is written as its length in bytes of
       UTF-8, a colon, the value and a comma. Nothing is written as an
       empty value. The changed columns are joined by commas.
    3. Each entry carries, as previous_hash, the hash of the entry before
       it for the same record; the first carries nothing.
    4. The SHA-256 of manifest.json is the one shown against this export
       on the Records Export page of the system that made it.
"""


@dataclass(frozen=True)
class Export:
    """An export, ready to send."""

    name: str
    subject: str
    content: bytes
    manifest_sha256: str


def neutralised(value: Any) -> str:
    """Write one value as a CSV cell that a spreadsheet will not run (threat TH-082)."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    elif isinstance(value, bool):
        text = "Yes" if value else "No"
    else:
        text = str(value)
    if isinstance(value, str) and text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def _json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode()


def _csv(records: list[dict[str, Any]]) -> bytes:
    columns = sorted({column for record in records for column in record})
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(columns)
    for record in records:
        writer.writerow([neutralised(record.get(column)) for column in columns])
    return out.getvalue().encode()


def _entry(event: Event) -> dict[str, Any]:
    return {
        "organisation_id": str(event.organisation_id),
        "record_type": event.record_type,
        "record_id": str(event.record_id),
        "sequence": event.sequence,
        "action": event.action,
        "actor_id": str(event.actor_id) if event.actor_id is not None else None,
        "actor_name": event.actor_name,
        "at": event.at.astimezone(UTC).strftime(STAMP),
        "changed": list(event.changed),
        "before": event.before_json,
        "after": event.after_json,
        "previous_hash": event.previous_hash,
        "hash": event.hash,
        "hash_algorithm": event.hash_algorithm,
    }


def _file_name(subject: str, on: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", subject).strip("-") + f"-records-{on}.zip"


def build(organisation: Organisation, *, by: User, aircraft: Aircraft | None = None) -> Export:
    """Build the export of ``aircraft``, or of the whole organisation with none."""
    files: dict[str, bytes] = {"README.txt": README.encode()}
    counts: dict[str, dict[str, int]] = {}
    for exported in REGISTRY:
        events = Event.objects.filter(record_type=exported.table)
        if aircraft is not None:
            if exported.of_aircraft is None:
                continue
            identifiers = exported.model._default_manager.filter(
                exported.of_aircraft(aircraft)
            ).values_list("pk", flat=True)
            events = events.filter(record_id__in=set(identifiers))
        entries = [_entry(event) for event in events.order_by("record_id", "sequence")]
        last: dict[str, dict[str, Any]] = {}
        for entry in entries:
            last[entry["record_id"]] = json.loads(entry["after"])
        records = [last[identifier] for identifier in sorted(last)]
        files[f"records/{exported.table}.json"] = _json(records)
        files[f"records/{exported.table}.csv"] = _csv(records)
        files[f"history/{exported.table}.json"] = _json(entries)
        counts[exported.table] = {"records": len(records), "history": len(entries)}
    if aircraft is not None:
        files["people.json"] = _json(
            {
                "users": [
                    {"id": str(user.pk), "full_name": user.full_name}
                    for user in User.objects.order_by("pk")
                ],
                "work_performers": [
                    {"id": str(person.pk), "full_name": person.full_name}
                    for person in Person.objects.filter(
                        Q(
                            pk__in=WorkDone.objects.filter(aircraft=aircraft).values(
                                "performed_by_id"
                            )
                        )
                        | Q(
                            pk__in=WorkCard.objects.filter(package__aircraft=aircraft).values(
                                "performed_by_id"
                            )
                        )
                        | Q(
                            pk__in=WorkCard.objects.filter(package__aircraft=aircraft).values(
                                "supervised_by_id"
                            )
                        )
                        | Q(
                            pk__in=WorkCard.objects.filter(package__aircraft=aircraft).values(
                                "inspector_id"
                            )
                        )
                    ).order_by("pk")
                ],
                "maintenance_authorisations": [
                    {
                        "id": str(grant.pk),
                        "person_id": str(grant.person_id),
                        "reference": grant.reference,
                        "scope": grant.scope,
                        "valid_from": grant.valid_from.isoformat(),
                        "valid_to": grant.valid_to.isoformat() if grant.valid_to else None,
                        "withdrawn_on": grant.withdrawn_on.isoformat()
                        if grant.withdrawn_on
                        else None,
                    }
                    for grant in MaintenanceAuthorisation.objects.select_related("withdrawal")
                    .filter(
                        Q(
                            pk__in=Release.objects.filter(work__aircraft=aircraft).values(
                                "maintenance_authorisation_id"
                            )
                        )
                        | Q(
                            pk__in=Defect.objects.filter(aircraft=aircraft).values(
                                "maintenance_authorisation_id"
                            )
                        )
                    )
                    .order_by("pk")
                ],
                "review_staff": [
                    {
                        "id": str(staff.pk),
                        "user_id": str(staff.user_id),
                        "authorisation_reference": staff.authorisation_reference,
                    }
                    for staff in ReviewStaff.objects.order_by("pk")
                ],
            }
        )
    else:
        files["access-log.json"] = _json(
            [
                {
                    "id": entry.pk,
                    "at": entry.at.astimezone(UTC).strftime(STAMP) if entry.at else None,
                    "kind": entry.kind,
                    "username": entry.username,
                    "user_id": str(entry.user_id) if entry.user_id else None,
                    "detail": entry.detail,
                    "address": entry.address,
                }
                for entry in AccessEntry.objects.order_by("pk")
            ]
        )
    now: datetime = utc_now()
    subject = aircraft.registration if aircraft is not None else organisation.name
    manifest = _json(
        {
            "format": FORMAT,
            "version": VERSION,
            "exported_at": now.astimezone(UTC).strftime(STAMP),
            "exported_by": by.full_name,
            "organisation": {
                "id": str(organisation.pk),
                "name": organisation.name,
                "approval_reference": organisation.approval_reference,
            },
            "aircraft": (
                {"id": str(aircraft.pk), "registration": aircraft.registration}
                if aircraft is not None
                else None
            ),
            "counts": counts,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        }
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in [(MANIFEST, manifest), *sorted(files.items())]:
            archive.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), data)
    return Export(
        name=_file_name(subject, aircraft_services.today().isoformat()),
        subject=subject,
        content=buffer.getvalue(),
        manifest_sha256=hashlib.sha256(manifest).hexdigest(),
    )
