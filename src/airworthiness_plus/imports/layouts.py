"""The columns of each kind of import file (REQ-170).

A file is CSV in UTF-8 with these column headings, exactly, in its first
row. A date is written 2026-11-18 or 18 November 2026 and nothing else,
because a date such as 03/04/2026 can be read two ways (hazard H-008).
Hours have at most one decimal place and no comma. Cycles are whole
numbers.
"""

from airworthiness_plus.imports.models import LoadKind

REGISTRATION = "Aircraft Registration"

AIRCRAFT = (
    REGISTRATION,
    "Type Rating",
    "Aircraft Serial Number",
    "Aircraft Manufacturer",
    "Manufacturer's Designation",
    "Owned By",
    "Totals Dated",
    "Airframe Hours",
    "Airframe Cycles",
)
AIRCRAFT_OPTIONAL = frozenset(
    {"Aircraft Serial Number", "Aircraft Manufacturer", "Manufacturer's Designation"}
)

DIRECTIVES = (
    REGISTRATION,
    "Directive Number",
    "Issuing Authority",
    "Subject",
    "Effective Date",
    "Decision",
    "Basis",
    "Last Compliance Date",
    "Hours at Compliance",
    "Cycles at Compliance",
    "Method of Compliance",
    "Release Reference",
)
DIRECTIVES_OPTIONAL = frozenset(
    {
        "Last Compliance Date",
        "Hours at Compliance",
        "Cycles at Compliance",
        "Method of Compliance",
        "Release Reference",
    }
)

CERTIFICATES = (
    REGISTRATION,
    "Certificate Reference",
    "Date of Issue",
    "Date of Expiry",
    "Issued By",
    "Review Staff Authorisation Reference",
    "Airframe Flight Hours at the Time of Review",
)
# A row gives one issuer: Issued By for a certificate issued elsewhere, or the
# authorisation reference of the organisation's own review staff member for one
# they issued before these records.
CERTIFICATES_OPTIONAL = frozenset(
    {
        "Issued By",
        "Review Staff Authorisation Reference",
        "Airframe Flight Hours at the Time of Review",
    }
)

# Hours and cycles: a wrong total overstates the time remaining (hazards H-008, H-011).
TOTALS = frozenset(
    {
        "Airframe Hours",
        "Airframe Cycles",
        "Hours at Compliance",
        "Cycles at Compliance",
        "Airframe Flight Hours at the Time of Review",
    }
)

COLUMNS: dict[LoadKind, tuple[str, ...]] = {
    LoadKind.AIRCRAFT: AIRCRAFT,
    LoadKind.DIRECTIVES: DIRECTIVES,
    LoadKind.CERTIFICATES: CERTIFICATES,
}
OPTIONAL: dict[LoadKind, frozenset[str]] = {
    LoadKind.AIRCRAFT: AIRCRAFT_OPTIONAL,
    LoadKind.DIRECTIVES: DIRECTIVES_OPTIONAL,
    LoadKind.CERTIFICATES: CERTIFICATES_OPTIONAL,
}
