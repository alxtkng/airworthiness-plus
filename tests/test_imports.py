"""The import of records and its verification report (REQ-170, REQ-171; hazard H-008).

The files are written from design-system/SampleData.md. Today in the
sample world is 18 November 2026.
"""

import hashlib
import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter
from airworthiness_plus.directives.models import Applicability, Compliance, Directive
from airworthiness_plus.history.session import working_for
from airworthiness_plus.imports import services
from airworthiness_plus.imports.layouts import AIRCRAFT, CERTIFICATES, DIRECTIVES
from airworthiness_plus.imports.models import Load, LoadedValue, LoadKind, ValueCheck
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.reviews.models import Certificate
from tests.conftest import as_owner
from tests.support import TODAY, Sample, get, page, signed_in

pytestmark = pytest.mark.django_db
D = Decimal


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


def csv_of(columns: tuple[str, ...], *rows: tuple[str, ...]) -> bytes:
    lines = [",".join(columns)]
    for row in rows:
        assert len(row) == len(columns)
        lines.append(",".join(f'"{cell}"' for cell in row))
    return ("\r\n".join(lines) + "\r\n").encode()


EJKL = (
    "G-EJKL",
    "Cessna/Reims-Cessna 152/F152 Series (Lycoming)",
    "[Aircraft Serial Number]",
    "",
    "",
    "Pilot-Owner",
    "18 November 2026",
    "11206.8",
    "0",
)
ABCD = (
    "G-ABCD",
    "Piper PA-28 Series (Lycoming)",
    "",
    "",
    "",
    "Pilot-Owner",
    "2026-11-18",
    "6412.6",
    "4236",
)
FLEET_FILE = csv_of(AIRCRAFT, EJKL, ABCD)

DIRECTIVE_ROWS = (
    (
        "G-EJKL",
        "[Directive Number 1]",
        "Civil Aviation Authority",
        "[Directive Subject 1]",
        "2026-06-01",
        "Applicable",
        "[Basis From the Logbook]",
        "2026-09-01",
        "11150.0",
        "0",
        "[Method]",
        "[Release Reference]",
    ),
    (
        "G-ABCD",
        "[Directive Number 1]",
        "Civil Aviation Authority",
        "[Directive Subject 1]",
        "2026-06-01",
        "Not Applicable",
        "[Serial Number Outside the Range]",
        "",
        "",
        "",
        "",
        "",
    ),
)
DIRECTIVE_FILE = csv_of(DIRECTIVES, *DIRECTIVE_ROWS)

CERTIFICATE_ROW = (
    "G-EJKL",
    "[Certificate Reference G-EJKL]",
    "6 December 2025",
    "6 December 2026",
    "[Issuing Organisation]",
    "",
    "11100.0",
)
CERTIFICATE_FILE = csv_of(CERTIFICATES, CERTIFICATE_ROW)


def load(sample: Sample, kind: LoadKind, content: bytes, source: str = "[Logbooks]") -> Load:
    with working_for(sample.ours.id, sample.lucy.id):
        return services.load(
            organisation=sample.ours,
            by=sample.lucy,
            kind=kind,
            source=source,
            file_name="file.csv",
            content=content,
        )


@pytest.fixture
def fleet_load(sample: Sample) -> Load:
    return load(sample, LoadKind.AIRCRAFT, FLEET_FILE)


def post(client: Client, path: str, **values: object) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


# Loading


def test_a_file_of_aircraft_makes_the_aircraft_and_keeps_every_value(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-170. The records are made by the same services as the pages; every value is kept."""
    with working_for(sample.ours.id, sample.lucy.id):
        ejkl = Aircraft.objects.get(registration="G-EJKL")
        assert ejkl.type_rating == "Cessna/Reims-Cessna 152/F152 Series (Lycoming)"
        assert ejkl.serial_number == "[Aircraft Serial Number]"
        reading = aircraft_services.current_reading(Counter.objects.get(aircraft=ejkl))
        assert reading is not None
        assert (reading.on, reading.hours, reading.cycles) == (TODAY, D("11206.8"), 0)
        abcd = aircraft_services.current_reading(
            Counter.objects.get(aircraft__registration="G-ABCD")
        )
        assert abcd is not None
        assert (abcd.hours, abcd.cycles) == (D("6412.6"), 4236)
        assert (fleet_load.rows, fleet_load.loaded_by, fleet_load.loaded_on) == (
            2,
            sample.lucy,
            TODAY,
        )
        assert fleet_load.file_sha256 == hashlib.sha256(FLEET_FILE).hexdigest()
        values = list(LoadedValue.objects.filter(load=fleet_load))
    # 9 columns for G-EJKL less 2 left empty, and 9 for G-ABCD less 3.
    assert len(values) == 7 + 6
    first = [(value.row, value.subject, value.field, value.value) for value in values[:2]]
    assert first == [
        (2, "G-EJKL", "Aircraft Registration", "G-EJKL"),
        (2, "G-EJKL", "Type Rating", "Cessna/Reims-Cessna 152/F152 Series (Lycoming)"),
    ]
    # The value is kept as it was written in the file, not as it was understood.
    assert (2, "G-EJKL", "Totals Dated", "18 November 2026") in [
        (value.row, value.subject, value.field, value.value) for value in values
    ]


def test_directive_status_and_review_certificates_are_loaded(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-170, REQ-171. One directive, decided for each aircraft by its own row (H-002)."""
    load(sample, LoadKind.DIRECTIVES, DIRECTIVE_FILE)
    load(sample, LoadKind.CERTIFICATES, CERTIFICATE_FILE)
    with working_for(sample.ours.id, sample.lucy.id):
        directive = Directive.objects.get()
        assert (directive.number, directive.effective_date) == (
            "[Directive Number 1]",
            date(2026, 6, 1),
        )
        decisions = {
            decision.aircraft.registration: decision
            for decision in Applicability.objects.select_related("aircraft")
        }
        assert decisions["G-EJKL"].decision == "Applicable"
        assert decisions["G-EJKL"].basis == "[Basis From the Logbook]"
        assert decisions["G-EJKL"].decided_by == sample.lucy
        assert decisions["G-ABCD"].decision == "Not Applicable"
        compliance = Compliance.objects.get()
        assert compliance.applicability == decisions["G-EJKL"]
        assert (compliance.work.dated, compliance.work.hours) == (date(2026, 9, 1), D("11150.0"))
        certificate = Certificate.objects.get()
        assert (certificate.reference, certificate.issued_on, certificate.valid_to) == (
            "[Certificate Reference G-EJKL]",
            date(2025, 12, 6),
            date(2026, 12, 6),
        )
        assert certificate.airframe_hours == D("11100.0")


def test_a_certificate_of_the_organisations_own_is_loaded_against_its_review_staff(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-170, REQ-110; Issue 71, D-3. The row names the review staff member by
    authorisation reference in place of an issuer elsewhere. The certificate keeps
    its reference and is held to the person's last review before these records."""
    with working_for(sample.ours.id, sample.administrator.id):
        lucy = review_services.add_review_staff(
            user=sample.lucy,
            authorisation_reference="[Authorisation Reference 1]",
            accepted_on=date(2023, 6, 9),
            last_review_before_records=date(2025, 12, 6),
        )
    row = dict(zip(CERTIFICATES, CERTIFICATE_ROW, strict=True))
    own = row | {
        "Issued By": "",
        "Review Staff Authorisation Reference": lucy.authorisation_reference,
    }
    for change, message in (
        ({"Issued By": "[Issuing Organisation]"}, "Row 2: A Certificate Is Issued by Review Staff"),
        ({"Review Staff Authorisation Reference": "[Unknown]"}, "Row 2: [Unknown] Is Not the"),
        ({"Date of Issue": "7 December 2025"}, "Row 2: A Certificate From Before These Records"),
    ):
        refused_row = own | change
        content = csv_of(CERTIFICATES, tuple(refused_row[column] for column in CERTIFICATES))
        with pytest.raises(services.RefusedError) as refused:
            load(sample, LoadKind.CERTIFICATES, content)
        assert message in str(refused.value)
    neither = row | {"Issued By": ""}
    with pytest.raises(services.RefusedError, match="Has Its Reference and Its Issuer"):
        load(
            sample,
            LoadKind.CERTIFICATES,
            csv_of(CERTIFICATES, tuple(neither[column] for column in CERTIFICATES)),
        )
    load(
        sample,
        LoadKind.CERTIFICATES,
        csv_of(CERTIFICATES, tuple(own[column] for column in CERTIFICATES)),
    )
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = Certificate.objects.get()
        assert (certificate.issued_by, certificate.from_before_records) == (lucy, True)
        assert (certificate.reference, certificate.serial_number) == (
            "[Certificate Reference G-EJKL]",
            None,
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"Totals Dated": "18/11/2026"}, "Row 3: Totals Dated Is Written 2026-11-18 or"),
        ({"Totals Dated": "2026-02-30"}, "Row 3: Totals Dated Is Written"),
        ({"Totals Dated": "2026-11-19"}, "Row 3: "),  # after today
        ({"Airframe Hours": "6,412.6"}, "Row 3: Airframe Hours Is a Number with at Most One"),
        ({"Airframe Hours": "6412.65"}, "Row 3: Airframe Hours Is a Number with at Most One"),
        ({"Airframe Hours": "-1.0"}, "Row 3: Airframe Hours Is a Number"),
        ({"Airframe Cycles": "42.5"}, "Row 3: Airframe Cycles Is a Whole Number"),
        ({"Owned By": ""}, "Row 3: Nothing Given for Owned By"),
        ({"Aircraft Registration": "G-EJKL"}, "Row 3: G-EJKL Is Already Recorded"),
        ({"Aircraft Registration": "G-ABCDEFGHIJ"}, "Row 3: Aircraft Registration Is at Most"),
    ],
)
def test_a_file_with_a_row_that_cannot_be_loaded_is_not_loaded_at_all(
    sample: Sample, change: dict[str, str], message: str
) -> None:
    """REQ-170, hazard H-008. The row and the reason are given, and nothing is kept."""
    row = dict(zip(AIRCRAFT, ABCD, strict=True)) | change
    content = csv_of(AIRCRAFT, EJKL, tuple(row[column] for column in AIRCRAFT))
    with pytest.raises(services.RefusedError) as refused:
        load(sample, LoadKind.AIRCRAFT, content)
    assert message in str(refused.value)
    with working_for(sample.ours.id, sample.lucy.id):
        assert Aircraft.objects.count() == 0
        assert (Load.objects.count(), LoadedValue.objects.count()) == (0, 0)


def test_a_file_that_is_not_as_described_is_refused(sample: Sample, fleet_load: Load) -> None:
    """REQ-170, threat TH-007. Wrong headings, wrong kind, not text, too large, no source."""
    cases = [
        (LoadKind.DIRECTIVES, FLEET_FILE, "[Logbooks]", "The First Row Is the Column Headings"),
        (LoadKind.AIRCRAFT, b"\xff\xfe\x00", "[Logbooks]", "The File Is Not Text in UTF-8"),
        (LoadKind.AIRCRAFT, csv_of(AIRCRAFT), "[Logbooks]", "The File Has No Rows"),
        (LoadKind.AIRCRAFT, FLEET_FILE + b"x" * 1_000_000, "[Logbooks]", "Larger Than 1 Megabyte"),
        (LoadKind.AIRCRAFT, FLEET_FILE, " ", "Say Which Records the File Was Taken From"),
        (
            LoadKind.AIRCRAFT,
            ",".join(AIRCRAFT).encode() + b"\r\nG-XXXX,only two\r\n",
            "[Logbooks]",
            "Row 2: Has 2 Values, Not 9",
        ),
    ]
    for kind, content, source, message in cases:
        with pytest.raises(services.RefusedError, match=message):
            load(sample, kind, content, source)
    # A directive for an aircraft that is not recorded, and a second decision for one that is.
    unknown = csv_of(DIRECTIVES, ("G-ZZZZ", *DIRECTIVE_ROWS[0][1:]))
    with pytest.raises(services.RefusedError, match="Row 2: G-ZZZZ Is Not Recorded"):
        load(sample, LoadKind.DIRECTIVES, unknown)
    load(sample, LoadKind.DIRECTIVES, DIRECTIVE_FILE)
    with pytest.raises(services.RefusedError, match="Already Has a Decision for G-EJKL"):
        load(sample, LoadKind.DIRECTIVES, DIRECTIVE_FILE)
    half = csv_of(
        DIRECTIVES, ("G-EJKL", "[Directive Number 2]", *DIRECTIVE_ROWS[0][2:8], "", "", "", "")
    )
    with pytest.raises(services.RefusedError, match="Compliance Has Its Date, Hours and Cycles"):
        load(sample, LoadKind.DIRECTIVES, half)
    with working_for(sample.ours.id, sample.lucy.id):
        assert Load.objects.count() == 2
        assert Directive.objects.count() == 1


# The verification report


def test_the_report_shows_every_value_beside_its_source_and_who_checked_it(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-170, REQ-171. Through the pages: loaded by one person, checked by another."""
    planner = signed_in(sample.planner)
    address = f"/imports/{fleet_load.id}/"
    body = page(planner, address)
    assert "<dt>Checked Against Source</dt><dd>0 of 13 Checked, 0%</dd>" in body
    assert body.count("<td>Not Checked</td>") == 13
    assert "<dt>Loaded</dt><dd>18 November 2026, Lucy Grant</dd>" in body
    with working_for(sample.ours.id, sample.planner.id):
        values = {
            (value.subject, value.field): str(value.id)
            for value in LoadedValue.objects.filter(load=fleet_load)
        }
    agreed = {
        f"agrees_{identifier}": "on"
        for (subject, _), identifier in values.items()
        if subject == "G-EJKL"
    }
    # The source says G-ABCD has 6,421.6 hours: two figures were transposed in the file.
    wrong = values[("G-ABCD", "Airframe Hours")]
    response = post(planner, f"{address}check/", **agreed, **{f"source_{wrong}": "6421.6"})
    assert response.status_code == 302
    body = page(signed_in(sample.reader), address)
    # 7 of 13 is 53.8%: shown rounded down. 8 checked is 61.5%.
    assert "<dt>Checked Against Source</dt><dd>8 of 13 Checked, 61%</dd>" in body
    assert "<dt>Differ From Source</dt><dd>1</dd>" in body
    assert body.count("<td>Agrees with Source</td>") == 7
    assert "<td>6412.6</td>\n<td>6421.6</td>\n<td>Differs From Source</td>" in body
    assert body.count("<td>18 November 2026, [Planning and Records Name]</td>") == 8
    listing = page(signed_in(sample.reader), "/imports/")
    assert "<td>8 of 13 Checked, 61%</td>" in listing
    assert "<td>[Logbooks]</td>" in listing

    # The rest are checked: 100% only when every value is.
    rest = {
        f"agrees_{identifier}": "on"
        for (subject, field), identifier in values.items()
        if subject == "G-ABCD" and field != "Airframe Hours"
    }
    post(planner, f"{address}check/", **rest)
    assert "13 of 13 Checked, 100%" in page(planner, address)
    # A value can be checked again; the earlier check is kept and the latest is shown.
    post(signed_in(sample.reviewer), f"{address}check/", **{f"agrees_{wrong}": "on"})
    body = page(planner, address)
    assert "<td>18 November 2026, [Review Name], Check 2</td>" in body
    assert "<dt>Differ From Source</dt><dd>0</dd>" in body
    with working_for(sample.ours.id, sample.planner.id):
        assert ValueCheck.objects.filter(value_id=uuid.UUID(wrong)).count() == 2


def test_a_value_cannot_both_agree_and_differ_and_nothing_is_ticked_for_the_person(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-171, hazard H-014. No value is checked unless a person says so."""
    client = signed_in(sample.planner)
    address = f"/imports/{fleet_load.id}/"
    body = page(client, address)
    assert " checked" not in body
    assert "Check All" not in body
    assert post(client, f"{address}check/").status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        assert ValueCheck.objects.count() == 0
        value = LoadedValue.objects.filter(load=fleet_load)[0]
    both = {f"agrees_{value.id}": "on", f"source_{value.id}": "[Something Else]"}
    refused = post(client, f"{address}check/", **both)
    assert "A Value Either Agrees with the Source or Differs From It" in refused.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        assert ValueCheck.objects.count() == 0


def test_hours_and_cycles_are_checked_by_a_second_person(sample: Sample, fleet_load: Load) -> None:
    """REQ-171, hazards H-008 and H-011. The person who loaded the file checks the rest."""
    lucy = signed_in(sample.lucy)
    address = f"/imports/{fleet_load.id}/"
    with working_for(sample.ours.id, sample.lucy.id):
        values = {
            (value.subject, value.field): str(value.id)
            for value in LoadedValue.objects.filter(load=fleet_load)
        }
    for field in ("Airframe Hours", "Airframe Cycles"):
        refused = post(lucy, f"{address}check/", **{f"agrees_{values['G-EJKL', field]}": "on"})
        assert "Hours and Cycles Are Checked by a Second Person" in refused.content.decode()
    # Nothing of a refused check is kept, including the values that came with it.
    both = {
        f"agrees_{values['G-EJKL', 'Owned By']}": "on",
        f"agrees_{values['G-EJKL', 'Airframe Hours']}": "on",
    }
    post(lucy, f"{address}check/", **both)
    with working_for(sample.ours.id, sample.lucy.id):
        assert ValueCheck.objects.count() == 0
    assert (
        post(
            lucy, f"{address}check/", **{f"agrees_{values['G-EJKL', 'Owned By']}": "on"}
        ).status_code
        == 302
    )
    planner = signed_in(sample.planner)
    post(planner, f"{address}check/", **{f"agrees_{values['G-EJKL', 'Airframe Hours']}": "on"})
    with working_for(sample.ours.id, sample.lucy.id):
        assert ValueCheck.objects.count() == 2


def test_a_load_its_values_and_their_checks_are_never_changed(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-170, REQ-131. The application has no permission to change or remove them."""
    with working_for(sample.ours.id, sample.lucy.id):
        value = LoadedValue.objects.filter(load=fleet_load)[0]
        services.record_checks(fleet_load, by=sample.lucy, agreed=[str(value.id)], differing={})
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            Load.objects.filter(pk=fleet_load.pk).update(source="[Changed]")
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            LoadedValue.objects.filter(pk=value.pk).update(value="[Changed]")
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            ValueCheck.objects.update(agrees=False)


def test_a_file_is_loaded_through_the_page(sample: Sample) -> None:
    """REQ-170. The page says how a file is written, and gives the reasons a file is refused."""
    lucy = signed_in(sample.lucy)
    body = page(lucy, "/imports/")
    assert "<td>Aircraft and Totals</td><td>Aircraft Registration, Type Rating, " in body
    bad = SimpleUploadedFile("fleet.csv", FLEET_FILE.replace(b"11206.8", b"11,206.8"))
    refused = post(
        lucy, "/imports/load/", kind="Aircraft and Totals", source="[Logbooks]", file=bad
    )
    assert "Row 2: Airframe Hours Is a Number with at Most One Decimal" in refused.content.decode()
    nothing = post(lucy, "/imports/load/", kind="Aircraft and Totals", source="[Logbooks]")
    assert "Choose What the File Holds" in nothing.content.decode()
    good = SimpleUploadedFile("fleet.csv", FLEET_FILE)
    response = post(
        lucy, "/imports/load/", kind="Aircraft and Totals", source="[Logbooks]", file=good
    )
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.lucy.id):
        record = Load.objects.get()
        assert record.file_name == "fleet.csv"
    assert response["Location"] == f"/imports/{record.id}/"
    assert ">G-EJKL</a>" in page(lucy, "/")


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)


def addresses(record: Load):  # type: ignore[no-untyped-def]
    return [
        ("GET", "/imports/", Action.VIEW_RECORDS),
        ("POST", "/imports/load/", Action.IMPORT_RECORDS),
        ("GET", f"/imports/{record.id}/", Action.VIEW_RECORDS),
        ("POST", f"/imports/{record.id}/check/", Action.CHECK_IMPORTED_RECORDS),
    ]


def call(client: Client, method: str, path: str) -> HttpResponse:
    return get(client, path) if method == "GET" else post(client, path)


def test_another_organisations_imports_are_not_found_or_shown(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. Read and write."""
    stranger = signed_in(sample.stranger)
    assert "[Logbooks]" not in page(stranger, "/imports/")
    assert get(stranger, f"/imports/{fleet_load.id}/").status_code == 404
    # The stranger is an Administrator and a manager of another organisation.
    with working_for(sample.ours.id, sample.lucy.id):
        value = LoadedValue.objects.filter(load=fleet_load)[0]
    response = post(stranger, f"/imports/{fleet_load.id}/check/", **{f"agrees_{value.id}": "on"})
    assert response.status_code == 404
    with as_owner():
        assert ValueCheck.objects.count() == 0


@pytest.mark.parametrize(
    "role", ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"]
)
def test_the_import_pages_follow_the_role_matrix(
    sample: Sample, fleet_load: Load, role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    refusals = 0
    for method, path, action in addresses(fleet_load):
        status = call(client, method, path).status_code
        if permitted(user.roles, action):
            assert status in (200, 302), f"{role} {method} {path}"
        else:
            assert status == 403, f"{role} {method} {path}"
            refusals += 1
    with working_for(sample.ours.id, user.id):
        logged = AccessEntry.objects.filter(user=user, kind="Action Refused").count()
    assert logged == refusals
    expected = {
        "Administrator": 2,
        "Airworthiness Review Staff": 1,
        "Planning and Records": 1,
        "Read Only": 2,
    }
    assert refusals == expected[role]


def test_the_import_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, fleet_load: Load
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    anonymous = Client()
    for method, path, _ in addresses(fleet_load):
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.lucy, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in addresses(fleet_load):
        if method == "POST":
            assert post(forged, path).status_code == 403, path
