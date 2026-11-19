"""Import a file of records, and check each imported value against its source (REQ-170, REQ-171).

A file is loaded whole or not at all. Each row makes its records through
the same services the pages use, so the same rules refuse the same things.
Every value that was imported is then kept, to be checked against the
source by a person.
"""

import csv
import hashlib
import io
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import DatabaseError, transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.directives.models import Applicability, Decision, Directive
from airworthiness_plus.imports.layouts import COLUMNS, OPTIONAL, REGISTRATION, TOTALS
from airworthiness_plus.imports.models import Load, LoadedValue, LoadKind, ValueCheck
from airworthiness_plus.interface.formatting import MONTHS
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.reviews.models import ReviewStaff
from airworthiness_rules.intervals import Reading
from airworthiness_rules.utilisation import EntryRefusedError

MAXIMUM_BYTES = 1_000_000
MAXIMUM_ROWS = 2_000


class RefusedError(Exception):
    """The file cannot be loaded, or the check cannot be recorded. The message says why."""


class RowError(Exception):
    """One row of the file cannot be loaded."""


Row = Mapping[str, str]


def _date(row: Row, column: str) -> date:
    text = row[column]
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return date.fromisoformat(text)
        long = re.fullmatch(r"(\d{1,2}) ([A-Z][a-z]+) (\d{4})", text)
        if long and long.group(2) in MONTHS:
            return date(int(long.group(3)), MONTHS.index(long.group(2)) + 1, int(long.group(1)))
    except ValueError:
        pass
    raise RowError(f"{column} Is Written 2026-11-18 or 18 November 2026")


def _hours(row: Row, column: str) -> Decimal:
    text = row[column]
    if not re.fullmatch(r"\d+(\.\d)?", text):
        raise RowError(f"{column} Is a Number with at Most One Decimal Place and No Comma")
    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise RowError(f"{column} Is Not a Number") from error


def _whole(row: Row, column: str) -> int:
    text = row[column]
    if not re.fullmatch(r"\d+", text):
        raise RowError(f"{column} Is a Whole Number")
    return int(text)


def _aircraft(row: Row) -> Aircraft:
    aircraft = Aircraft.objects.filter(registration=row[REGISTRATION]).first()
    if aircraft is None:
        raise RowError(f"{row[REGISTRATION]} Is Not Recorded")
    return aircraft


def _load_aircraft(organisation: Organisation, by: User, row: Row) -> str:
    registration = row[REGISTRATION]
    if len(registration) > 10:
        raise RowError("Aircraft Registration Is at Most 10 Characters")
    if Aircraft.objects.filter(registration=registration).exists():
        raise RowError(f"{registration} Is Already Recorded")
    reading = Reading(
        _date(row, "Totals Dated"), _hours(row, "Airframe Hours"), _whole(row, "Airframe Cycles")
    )
    try:
        aircraft_services.add_aircraft(
            organisation=organisation,
            registration=registration,
            type_rating=row["Type Rating"],
            owner=row["Owned By"],
            serial_number=row["Aircraft Serial Number"],
            manufacturer=row["Aircraft Manufacturer"],
            designation=row["Manufacturer's Designation"],
            airframe=reading,
        )
    except (EntryRefusedError, aircraft_services.ConfirmationNeededError) as error:
        raise RowError(str(error)) from error
    return registration


def _load_directive(organisation: Organisation, by: User, row: Row) -> str:
    aircraft = _aircraft(row)
    number, authority = row["Directive Number"], row["Issuing Authority"]
    effective = _date(row, "Effective Date")
    if row["Decision"] not in Decision.values:
        raise RowError("Decision Is Applicable or Not Applicable")
    decision = Decision(row["Decision"])
    directive = Directive.objects.filter(number=number, authority=authority).first()
    if directive is None:
        directive = directive_services.record_directive(
            organisation=organisation,
            number=number,
            authority=authority,
            subject=row["Subject"],
            effective_date=effective,
        )
    elif (directive.subject, directive.effective_date) != (row["Subject"], effective):
        raise RowError(f"{number} Is Already Recorded with Another Subject or Effective Date")
    if Applicability.objects.filter(directive=directive, aircraft=aircraft).exists():
        raise RowError(f"{number} Already Has a Decision for {aircraft.registration}")
    complied = [row[column] for column in ("Last Compliance Date", "Hours at Compliance")]
    try:
        applicability = directive_services.decide(
            directive=directive,
            aircraft=aircraft,
            decision=decision,
            basis=row["Basis"],
            decided_by=by,
        )
        if any(complied) or row["Cycles at Compliance"] or row["Method of Compliance"]:
            if not all(complied) or not row["Cycles at Compliance"]:
                raise RowError("Compliance Has Its Date, Hours and Cycles")
            directive_services.record_compliance(
                applicability,
                method=row["Method of Compliance"],
                dated=_date(row, "Last Compliance Date"),
                hours=_hours(row, "Hours at Compliance"),
                cycles=_whole(row, "Cycles at Compliance"),
                release_reference=row["Release Reference"],
                # The file reproduces a record that already existed, so the release
                # was in the aircraft's records when the work was done (REQ-051).
                release_recorded_on=_date(row, "Last Compliance Date"),
            )
    except directive_services.RefusedError as error:
        raise RowError(str(error)) from error
    return f"{aircraft.registration}, {number}"


def _load_certificate(organisation: Organisation, by: User, row: Row) -> str:
    aircraft = _aircraft(row)
    column = "Airframe Flight Hours at the Time of Review"
    authorisation = row["Review Staff Authorisation Reference"]
    staff = None
    if authorisation:
        found = list(ReviewStaff.objects.filter(authorisation_reference=authorisation)[:2])
        if len(found) != 1:
            raise RowError(
                f"{authorisation} Is Not the Authorisation Reference of One Review Staff Member"
            )
        staff = found[0]
    try:
        review_services.record_certificate(
            aircraft,
            reference=row["Certificate Reference"],
            issued_on=_date(row, "Date of Issue"),
            valid_to=_date(row, "Date of Expiry"),
            issued_elsewhere_by=row["Issued By"],
            issued_by=staff,
            airframe_hours=_hours(row, column) if row[column] else None,
        )
    except review_services.RefusedError as error:
        raise RowError(str(error)) from error
    return f"{aircraft.registration}, {row['Certificate Reference']}"


LOADERS: dict[LoadKind, Callable[[Organisation, User, Row], str]] = {
    LoadKind.AIRCRAFT: _load_aircraft,
    LoadKind.DIRECTIVES: _load_directive,
    LoadKind.CERTIFICATES: _load_certificate,
}


def _rows(kind: LoadKind, content: bytes) -> list[dict[str, str]]:
    if len(content) > MAXIMUM_BYTES:
        raise RefusedError("The File Is Larger Than 1 Megabyte")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise RefusedError("The File Is Not Text in UTF-8") from error
    reader = csv.reader(io.StringIO(text, newline=""))
    table = [line for line in reader if any(cell.strip() for cell in line)]
    columns = COLUMNS[kind]
    if not table or tuple(cell.strip() for cell in table[0]) != columns:
        raise RefusedError("The First Row Is the Column Headings: " + ", ".join(columns))
    if len(table) == 1:
        raise RefusedError("The File Has No Rows")
    if len(table) - 1 > MAXIMUM_ROWS:
        raise RefusedError("The File Has More Than 2,000 Rows")
    rows = []
    for number, line in enumerate(table[1:], start=2):
        if len(line) != len(columns):
            raise RefusedError(f"Row {number}: Has {len(line)} Values, Not {len(columns)}")
        rows.append({column: cell.strip() for column, cell in zip(columns, line, strict=True)})
    return rows


@transaction.atomic
def load(
    *,
    organisation: Organisation,
    by: User,
    kind: LoadKind,
    source: str,
    file_name: str,
    content: bytes,
) -> Load:
    """Load a file. Every row is loaded, or none is and the reasons are given."""
    if not source.strip():
        raise RefusedError("Say Which Records the File Was Taken From")
    rows = _rows(kind, content)
    problems = []
    loaded: list[tuple[int, str, dict[str, str]]] = []
    for number, row in enumerate(rows, start=2):
        missing = [c for c in COLUMNS[kind] if not row[c] and c not in OPTIONAL[kind]]
        if missing:
            problems.append(f"Row {number}: Nothing Given for " + ", ".join(missing))
            continue
        try:
            with transaction.atomic():
                subject = LOADERS[kind](organisation, by, row)
        except RowError as error:
            problems.append(f"Row {number}: {error}")
        except DatabaseError:
            problems.append(f"Row {number}: The Database Refused This Row")
        else:
            loaded.append((number, subject, row))
    if problems:
        raise RefusedError("; ".join(problems))
    record = Load.objects.create(
        organisation=organisation,
        kind=kind,
        source=source.strip(),
        file_name=file_name[:200],
        file_sha256=hashlib.sha256(content).hexdigest(),
        rows=len(loaded),
        loaded_by=by,
        loaded_on=aircraft_services.today(),
    )
    LoadedValue.objects.bulk_create(
        LoadedValue(
            organisation=organisation,
            load=record,
            row=number,
            position=position,
            subject=subject,
            field=column,
            value=row[column],
        )
        for number, subject, row in loaded
        for position, column in enumerate(COLUMNS[kind], start=1)
        if row[column]
    )
    return record


@transaction.atomic
def record_checks(
    record: Load, *, by: User, agreed: Iterable[str], differing: Mapping[str, str]
) -> int:
    """Record the check of some values of a load against the source, and return how many.

    ``agreed`` names the values the person found to agree with the source.
    ``differing`` gives, for each value that does not, what the source
    says. A value can be checked again; every check is kept. Hours and
    cycles are checked by a second person, not the one who loaded the file
    (hazard H-008).
    """
    today = aircraft_services.today()
    agreed = set(agreed)
    if agreed & set(differing):
        raise RefusedError("A Value Either Agrees with the Source or Differs From It")
    count = 0
    for value in record.values.all():
        key = str(value.pk)
        if key in agreed:
            source_value = value.value
        elif differing.get(key, "").strip():
            source_value = differing[key].strip()
        else:
            continue
        if value.field in TOTALS and by.pk == record.loaded_by_id:
            raise RefusedError(
                "Hours and Cycles Are Checked by a Second Person, "
                "Not the Person Who Loaded the File"
            )
        ValueCheck.objects.create(
            organisation_id=record.organisation_id,
            value=value,
            source_value=source_value,
            agrees=source_value == value.value,
            checked_by=by,
            checked_on=today,
            position=value.checks.count() + 1,
        )
        count += 1
    return count


@dataclass(frozen=True)
class ReportLine:
    """One imported value beside what its source says, and who checked it."""

    value: LoadedValue
    check: ValueCheck | None
    checks: int

    @property
    def status(self) -> str:
        """Return Not Checked, Agrees with Source or Differs From Source."""
        if self.check is None:
            return "Not Checked"
        return "Agrees with Source" if self.check.agrees else "Differs From Source"


@dataclass(frozen=True)
class Report:
    """The verification report of a load (REQ-170, REQ-171)."""

    load: Load
    lines: list[ReportLine]

    @property
    def total(self) -> int:
        """Return how many values were imported."""
        return len(self.lines)

    @property
    def checked(self) -> int:
        """Return how many values have been checked against the source."""
        return sum(1 for line in self.lines if line.check is not None)

    @property
    def differing(self) -> int:
        """Return how many values differ from the source at their latest check."""
        return sum(1 for line in self.lines if line.check is not None and not line.check.agrees)

    @property
    def proportion(self) -> str:
        """Return the proportion checked, in whole percent, rounded down.

        Rounded down so that 100% is shown only when every value is checked.
        """
        percent = self.checked * 100 // self.total if self.total else 0
        return f"{self.checked} of {self.total} Checked, {percent}%"


def report(record: Load) -> Report:
    """Return the verification report of a load."""
    lines = []
    for value in record.values.prefetch_related("checks__checked_by"):
        checks = list(value.checks.all())
        lines.append(ReportLine(value, checks[-1] if checks else None, len(checks)))
    return Report(record, lines)


def reports() -> list[Report]:
    """Return every load with its report, newest first."""
    return [report(record) for record in Load.objects.select_related("loaded_by")]
