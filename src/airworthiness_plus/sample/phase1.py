"""The sample's records for Continuing Airworthiness, the Rest (Phase 1 of the canvas build).

Everything here is from design-system/SampleData.md and the boards of
Phase 1, made through the same services as the pages. It is added when a
new sample is built. Today in the sample world is 18 November 2026.
"""

from datetime import date
from decimal import Decimal

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components import services as component_services
from airworthiness_plus.components.models import Basis as LimitBasis
from airworthiness_plus.components.models import Component
from airworthiness_plus.configuration import services as configuration_services
from airworthiness_plus.configuration.models import ItemState, Product
from airworthiness_plus.contracts import services as contract_services
from airworthiness_plus.contracts.models import Contract, OrderedBy, Scope
from airworthiness_plus.defects import services as defect_services
from airworthiness_plus.defects.models import Basis, Decision, Defect
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.history.session import working_for
from airworthiness_plus.modifications import services as modification_services
from airworthiness_plus.modifications.models import Classification, Data, OwnerDecision, Route
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Person, StaffGroup
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Basis as ProgrammeBasis
from airworthiness_plus.programme.models import Programme, WorkDone
from airworthiness_plus.releases import services as release_services
from airworthiness_plus.releases.models import IssuedBy, Release

PA28 = "Piper PA-28 Series (Lycoming)"

_PILOT = Basis.PILOT_NON_REQUIRED
_STAFF = Basis.CERTIFYING_STAFF
_NOT = Decision.NOT_DEFERRABLE
_DEFERRED = Decision.DEFERRED

# SampleData.md, Defects: Aircraft Registration, defect, note, found, chapter,
# system, decision, who deferred it, the certifying staff named, decided,
# rectification, closed. The first four are open; the next two were closed in
# the last 30 days; the last three are those the Repeat Defects board counts.
DEFECTS: tuple[
    tuple[str, str, str, date, int, str, Decision, str, str, date, str, date | None], ...
] = (
    ("G-DGHI", "Stabilator Trim Cable Frayed at Pulley", "Trim Check", date(2026, 11, 14),
     27, "Flight Controls", _NOT, "", "Chris Moore", date(2026, 11, 14), "", None),
    ("G-ABCD", "Left Landing Light Inoperative", "Placarded, Daylight Only", date(2026, 11, 3),
     33, "Lights", _DEFERRED, _PILOT, "", date(2026, 11, 3), "", None),
    ("G-BXYZ", "Cabin Entry Step Loose", "No Effect on Flight, Step Out of Use",
     date(2026, 10, 28), 53, "Fuselage", _DEFERRED, _STAFF, "Sam Patel", date(2026, 10, 28),
     "", None),
    ("G-EJKL", "Right Headset Socket Crackle", "Left Socket Serviceable", date(2026, 11, 12),
     23, "Communications", _DEFERRED, _PILOT, "", date(2026, 11, 12), "", None),
    ("G-ABCD", "Right Main Tyre Worn to Limit", "", date(2026, 10, 22),
     32, "Landing Gear", _NOT, "", "", date(2026, 10, 22), "Tyre Replaced", date(2026, 10, 22)),
    ("G-CDEF", "Propeller Spinner Crack", "", date(2026, 11, 2),
     61, "Propeller", _NOT, "", "Chris Moore", date(2026, 11, 2), "Spinner Replaced",
     date(2026, 11, 4)),
    ("G-ABCD", "Landing Light Inoperative", "", date(2026, 2, 10),
     33, "Lights", _DEFERRED, _PILOT, "", date(2026, 2, 10), "Lamp Replaced", date(2026, 2, 12)),
    ("G-DGHI", "Landing Light Inoperative", "", date(2026, 6, 16),
     33, "Lights", _DEFERRED, _PILOT, "", date(2026, 6, 16), "Lamp Replaced", date(2026, 6, 19)),
    ("G-DGHI", "Stabilator Trim Cable Wear", "", date(2025, 12, 9),
     27, "Flight Controls", _DEFERRED, _STAFF, "Chris Moore", date(2025, 12, 9),
     "Cable Tension Adjusted", date(2025, 12, 16)),
)  # fmt: skip

# The Repeat Defects board: the action taken for a type rating and chapter.
REPEAT_ACTIONS = (
    (PA28, 33, "Add Lamp Holder Check to 50-Hour Check"),
    (PA28, 27, "Pulley Alignment, WP-2026-046"),
)


def _certifying(name: str) -> Person:
    """Return the member of certifying staff of a sample that has just been built.

    Only for a new sample, where each name of SampleData.md is one person.
    A living organisation is never searched by name.
    """
    return Person.objects.get(full_name=name, staff_group=StaffGroup.CERTIFYING)


def add_defects(ours: Organisation, by: User, fleet: dict[str, Aircraft]) -> list[Defect]:
    """Add the defects of SampleData.md and the actions on repeat defects.

    ``by`` is the user who records them: Planning and Records.
    """
    added = []
    with working_for(ours.id, by.id):
        for (
            registration,
            title,
            note,
            found_on,
            chapter,
            system,
            decision,
            basis,
            staff,
            decided_on,
            rectification,
            closed_on,
        ) in DEFECTS:
            aircraft = Aircraft.objects.get(pk=fleet[registration].pk)
            work = None
            if closed_on is not None and title == "Right Main Tyre Worn to Limit":
                # The tyre was replaced by the pilot-owner: the work done is already recorded.
                work = (
                    WorkDone.objects.filter(aircraft=aircraft, dated=closed_on, by_pilot_owner=True)
                    .order_by("id")
                    .first()
                )
            added.append(
                defect_services.record_defect(
                    aircraft,
                    title=title,
                    note=note,
                    found_on=found_on,
                    chapter=chapter,
                    system=system,
                    decision=decision,
                    basis=basis,
                    decided_on=decided_on,
                    decided_by=_certifying(staff) if staff else None,
                    rectification=rectification,
                    closed_on=closed_on,
                    work_done=work,
                )
            )
    return added


def add_repeat_actions(ours: Organisation, by: User) -> None:
    """Add what was done about the repeat defects, as the Continuing Airworthiness Manager."""
    with working_for(ours.id, by.id):
        for type_rating, chapter, action in REPEAT_ACTIONS:
            defect_services.record_repeat_action(
                ours, type_rating=type_rating, chapter=chapter, action=action
            )


# SampleData.md, Commercial, and the Contracts board: Aircraft Registration,
# the limited tasks (none for every task) and the day signed.
CONTRACTS: tuple[tuple[str, str, date], ...] = (
    ("G-BXYZ", "", date(2025, 1, 15)),
    ("G-CDEF", "", date(2024, 4, 8)),
    ("G-DGHI", "", date(2025, 3, 4)),
    ("G-HKLM", "", date(2026, 11, 9)),
    ("G-ABCD", "Maintenance Programme Review and Airworthiness Review", date(2026, 3, 2)),
)

# The Contracts board, Maintenance Work Orders. G-FMNO has no contract: a work order only.
WORK_ORDERS: tuple[tuple[str, str, OrderedBy, date], ...] = (
    ("G-ABCD", "Landing Light Replacement", OrderedBy.OWNER, date(2026, 11, 12)),
    ("G-DGHI", "Stabilator Trim Cable Rectification", OrderedBy.MANAGER, date(2026, 11, 14)),
    ("G-FMNO", "50-Hour Check", OrderedBy.OWNER, date(2026, 11, 16)),
)


def add_contracts(ours: Organisation, by: User, fleet: dict[str, Aircraft]) -> list[Contract]:
    """Add the contracts and work orders of SampleData.md.

    ``by`` is the Continuing Airworthiness Manager.
    """
    added = []
    with working_for(ours.id, by.id):
        for registration, tasks, signed_on in CONTRACTS:
            added.append(
                contract_services.draw_up_contract(
                    Aircraft.objects.get(pk=fleet[registration].pk),
                    scope=Scope.LIMITED if tasks else Scope.ALL,
                    tasks=tasks,
                    type_of_operation="[Type of Operation]",
                    owner_address=f"[Owner Address {registration}]",
                    signed_on=signed_on,
                )
            )
        for registration, work, ordered_by, agreed_on in WORK_ORDERS:
            contract_services.add_work_order(
                Aircraft.objects.get(pk=fleet[registration].pk),
                work=work,
                ordered_by=ordered_by,
                agreed_on=agreed_on,
            )
    return added


# SampleData.md, Work in Progress, and the Release to Service board: WP-2026-043,
# G-CDEF, released on 4 November 2026 by Chris Moore and in the records the next
# day. The airframe hours that day are made up, below the 7,720.0 of 11 November.
CDEF_WORK = ("100-Hour Check", "Propeller Spinner Replaced")
CDEF_HOURS = Decimal("7715.0")
CDEF_REFERENCE = "[Release Reference WP-2026-043]"


def add_releases(ours: Organisation, by: User, fleet: dict[str, Aircraft]) -> list[Release]:
    """Add the work of WP-2026-043 and its certificates, as Planning and Records."""
    added = []
    with working_for(ours.id, by.id):
        cdef = Aircraft.objects.get(pk=fleet["G-CDEF"].pk)
        chris = _certifying("Chris Moore")
        for description in CDEF_WORK:
            work = programme_services.record_work(
                cdef,
                description=description,
                dated=date(2026, 11, 4),
                hours=CDEF_HOURS,
                cycles=0,
            )
            added.append(
                release_services.record_certificate(
                    work,
                    reference=CDEF_REFERENCE,
                    kind=IssuedBy.ORGANISATION,
                    issued_by=chris,
                    issued_on=date(2026, 11, 4),
                    recorded_on=date(2026, 11, 5),
                )
            )
    return added


_RECOMMENDED = LimitBasis.RECOMMENDATION

# SampleData.md, Components, and the Components board. Each: the component, its
# limit, then its fitting: Aircraft Registration, position, the day fitted, the
# airframe hours then, the component's own hours then, and the day it was new or
# last overhauled. The days and the hours when fitted are made up so that the
# hours since new or overhaul are the board's on 18 November 2026.
COMPONENTS: tuple[tuple[dict[str, object], dict[str, object]], ...] = (
    (
        {"name": "Propeller, Fixed Pitch", "part_number": "[Part Number Propeller G-CDEF]",
         "serial_number": "[Serial Number Propeller G-CDEF]", "basis": _RECOMMENDED,
         "limit_hours": Decimal("2000"), "limit_months": 72,
         "source": "[Propeller Manufacturer's Service Information]"},
        {"aircraft": "G-CDEF", "position": "Propeller", "fitted_on": date(2020, 11, 2),
         "airframe_hours_fitted": Decimal("6319.5"), "hours_at_fitting": Decimal("16.5"),
         "life_from": date(2020, 11, 2), "release_document": "Release Certificate on File"},
    ),
    (
        {"name": "Propeller, Fixed Pitch, on Loan", "part_number": "[Part Number Loan Propeller]",
         "serial_number": "[Serial Number Loan Propeller]", "basis": LimitBasis.NONE},
        {"aircraft": "G-CDEF", "position": "Propeller", "fitted_on": date(2026, 11, 4),
         "airframe_hours_fitted": Decimal("7715.0"), "hours_at_fitting": Decimal("0.0"),
         "release_document": "[Release Reference WP-2026-043]"},
    ),
    (
        {"name": "Engine, Lycoming O-360", "serial_number": "[Serial Number Engine G-DGHI]",
         "basis": LimitBasis.ON_CONDITION, "review_hours": Decimal("100"),
         "last_review_hours": Decimal("9800.0"), "last_review_on": date(2026, 10, 20),
         "source": "Departure From the Manufacturer's 2,000 Hours or 12 Years"},
        {"aircraft": "G-DGHI", "position": "Engine", "fitted_on": date(2018, 6, 4),
         "airframe_hours_fitted": Decimal("7734.3"), "hours_at_fitting": Decimal("0.0"),
         "life_from": date(2018, 6, 4)},
    ),
    (
        {"name": "Emergency Locator Transmitter Battery",
         "part_number": "[Part Number Battery G-ABCD]", "basis": LimitBasis.DATE,
         "limit_date": date(2027, 2, 28), "date_label": "Battery Date"},
        {"aircraft": "G-ABCD", "position": "Emergency Locator Transmitter",
         "fitted_on": date(2022, 2, 14), "airframe_hours_fitted": Decimal("5890.0"),
         "hours_at_fitting": Decimal("0.0")},
    ),
    (
        {"name": "Fire Extinguisher", "part_number": "[Part Number Extinguisher G-BXYZ]",
         "basis": LimitBasis.DATE, "limit_date": date(2027, 3, 31),
         "date_label": "Label Inspection Date"},
        {"aircraft": "G-BXYZ", "position": "Cabin", "fitted_on": date(2022, 4, 1),
         "airframe_hours_fitted": Decimal("2950.0"), "hours_at_fitting": Decimal("0.0")},
    ),
    (
        {"name": "Engine, Lycoming O-360", "serial_number": "[Serial Number Engine G-CDEF]",
         "basis": _RECOMMENDED, "limit_hours": Decimal("2000"),
         "source": "[Engine Manufacturer's Service Instruction]"},
        {"aircraft": "G-CDEF", "position": "Engine", "fitted_on": date(2019, 3, 12),
         "airframe_hours_fitted": Decimal("5951.5"), "hours_at_fitting": Decimal("0.0"),
         "life_from": date(2019, 3, 12)},
    ),
    (
        {"name": "Vacuum Pump", "part_number": "[Part Number Vacuum Pump G-ABCD]",
         "basis": _RECOMMENDED, "limit_hours": Decimal("500"),
         "source": "[Vacuum Pump Manufacturer's Service Information]"},
        {"aircraft": "G-ABCD", "position": "Engine", "fitted_on": date(2026, 4, 6),
         "airframe_hours_fitted": Decimal("6230.6"), "hours_at_fitting": Decimal("0.0"),
         "life_from": date(2026, 4, 6)},
    ),
)  # fmt: skip

OWN_PROPELLER = "[Serial Number Propeller G-CDEF]"


def add_components(ours: Organisation, by: User, fleet: dict[str, Aircraft]) -> list[Component]:
    """Add the components of SampleData.md, each with its fitting, as Planning and Records.

    G-CDEF's own propeller was removed at its 6-year limit on 2 November 2026
    and is at [Propeller Organisation], due back 25 November 2026; the
    aircraft flies on a loan propeller fitted on 4 November.
    """
    added = []
    with working_for(ours.id, by.id):
        for component, fitting in COMPONENTS:
            one = component_services.add_component(ours, **component)  # type: ignore[arg-type]
            values = dict(fitting)
            aircraft = Aircraft.objects.get(pk=fleet[str(values.pop("aircraft"))].pk)
            fitted = component_services.fit_component(one, aircraft, **values)  # type: ignore[arg-type]
            if one.serial_number == OWN_PROPELLER:
                component_services.remove_component(
                    fitted,
                    removed_on=date(2026, 11, 2),
                    airframe_hours_removed=Decimal("7715.0"),
                    removal_reason="Removed at 6-Year Limit",
                    sent_to="[Propeller Organisation]",
                    due_back_on=date(2026, 11, 25),
                )
            added.append(one)
    return added


# SampleData.md, Modifications and Repairs, and the Modifications board. Service
# bulletins: Aircraft Registration, bulletin, reference, classification, the day
# sent to the owner, the reminder, the decision, its detail and the day recorded.
BULLETINS: tuple[
    tuple[str, str, str, Classification, date, date | None, OwnerDecision, str, date | None], ...
] = (
    ("G-ABCD", "Seat Rail and Stop Inspection", "[Service Bulletin Reference 1]",
     Classification.RECOMMENDED, date(2026, 2, 16), None, OwnerDecision.ACCEPTED,
     "Every 50-Hour Check", date(2026, 3, 2)),
    ("G-ABCD", "Engine Valve Guide Inspection", "[Service Bulletin Reference 2]",
     Classification.RECOMMENDED, date(2026, 2, 16), None, OwnerDecision.ACCEPTED,
     "Every 100-Hour Check", date(2026, 3, 2)),
    ("G-BXYZ", "Alternator Mounting Bracket Inspection", "[Service Bulletin Reference 3]",
     Classification.RECOMMENDED, date(2026, 11, 10), date(2026, 11, 24), OwnerDecision.AWAITING,
     "", None),
    ("G-EJKL", "Seat Belt Replacement", "[Service Bulletin Reference 4]",
     Classification.OPTIONAL, date(2026, 5, 20), None, OwnerDecision.DECLINED,
     "Belts On Condition, Annual Check", date(2026, 6, 6)),
)  # fmt: skip

# Changes and repairs: Aircraft Registration, change or repair, approval route,
# data (ML.A.304), reference, mass effect in Kilograms and the day embodied.
CHANGES: tuple[tuple[str, str, Route, Data | str, str, str, date | None], ...] = (
    ("G-BXYZ", "Panel-Mounted Navigator", Route.STANDARD_CHANGE, "",
     "[Standard Change Reference 1]", "1.2", date(2026, 10, 12)),
    ("G-FMNO", "Light-Emitting Diode Landing Light", Route.MINOR_CHANGE,
     Data.DESIGN_ORGANISATION, "[Minor Change Reference]", "-0.3", date(2026, 4, 14)),
    ("G-DGHI", "Left Wingtip Repair, Hangar Damage", Route.STRUCTURAL_REPAIR_DATA,
     Data.DESIGN_ORGANISATION, "", "0.0", date(2025, 7, 18)),
    ("G-ABCD", "Mode S Transponder with Position Output", Route.STANDARD_CHANGE, "",
     "[Standard Change Reference 2]", "0.4", date(2022, 5, 10)),
    ("G-CDEF", "Propeller Overhaul", Route.SAME_PART, "", "", "0.0", None),
)  # fmt: skip

# Weight and balance: Aircraft Registration, the day last weighed, the issue of
# the weight schedule and the day it was issued. The days are made up.
WEIGHINGS: tuple[tuple[str, date, int, date], ...] = (
    ("G-BXYZ", date(2019, 6, 14), 6, date(2019, 6, 14)),
    ("G-DGHI", date(2017, 3, 9), 9, date(2017, 3, 9)),
    ("G-ABCD", date(2022, 5, 20), 4, date(2022, 5, 20)),
    ("G-CDEF", date(2021, 9, 3), 3, date(2021, 9, 3)),
    ("G-EJKL", date(2020, 7, 22), 2, date(2020, 7, 22)),
    # Issue 5 took in the landing light of April 2026.
    ("G-FMNO", date(2018, 4, 5), 5, date(2026, 4, 20)),
)


def add_modifications(ours: Organisation, by: User, fleet: dict[str, Aircraft]) -> None:
    """Add the service bulletins, changes, repairs, weighings and weight schedules.

    As Planning and Records. No reweigh threshold is set: it is the
    organisation's to set, and has no default.
    """

    def aircraft(registration: str) -> Aircraft:
        return Aircraft.objects.get(pk=fleet[registration].pk)

    with working_for(ours.id, by.id):
        for (
            registration,
            title,
            reference,
            classification,
            sent_on,
            reminder_on,
            decision,
            detail,
            decided_on,
        ) in BULLETINS:
            modification_services.record_bulletin(
                aircraft(registration),
                title=title,
                reference=reference,
                classification=classification,
                sent_on=sent_on,
                reminder_on=reminder_on,
                decision=decision,
                detail=detail,
                decided_on=decided_on,
            )
        for registration, title, route, data, reference, mass, embodied_on in CHANGES:
            modification_services.record_change(
                aircraft(registration),
                title=title,
                route=route,
                data_kind=data,
                reference=reference,
                mass_effect=Decimal(mass),
                embodied_on=embodied_on,
            )
        for registration, weighed_on, issue, issued_on in WEIGHINGS:
            modification_services.record_weighing(
                aircraft(registration),
                weighed_on=weighed_on,
                reference=f"[Weighing Report {registration}]",
            )
            modification_services.record_schedule(
                aircraft(registration), issue=issue, issued_on=issued_on
            )


# SampleData.md, Maintenance Programme Inputs, and the Maintenance Programmes
# board: the departures of G-DGHI's programme from the manufacturer's
# instructions. Task, manufacturer, programme, compensating measures, justification.
DEPARTURES: tuple[tuple[str, str, str, str, str], ...] = (
    ("Engine Overhaul, Lycoming O-360", "2,000 Hours or 12 Years",
     "On Condition, Reviewed Every 100 Hours",
     "Oil Analysis Every 50 Hours, Compression and Borescope Every 100 Hours",
     "Club Use, About 300 Hours a Year"),
    ("Vacuum Pump Replacement", "500 Hours", "On Condition", "Standby Vacuum Source Fitted",
     "Pump Checked Every 50 Hours"),
)  # fmt: skip

# The annual review of G-FMNO's programme, 4 of 6 complete: the point, what was
# found and whether it is complete.
FMNO_REVIEW: dict[str, tuple[str, bool]] = {
    "results": ("2 Defects, No Repeats", True),
    "airworthiness_review": ("27 April 2026, Programme Adequate", True),
    "revisions": ("Maintenance Manual Revision [Revision] to Check", False),
    "configuration": ("No Change, Private Flying", True),
    "pilot_owners": ("Awaiting Owner Confirmation", False),
    "mandatory": ("Checked 16 November 2026", True),
}


def add_programme_records(ours: Organisation, by: User, fleet: dict[str, Aircraft]) -> None:
    """Add G-DGHI's programme and its departures, and G-FMNO's annual review in progress.

    As the Continuing Airworthiness Manager. G-DGHI's programme is on the
    manufacturer's instructions, last reviewed on 4 March 2026, as the
    Maintenance Programmes board has it.
    """
    with working_for(ours.id, by.id):
        dghi = programme_services.set_up_programme(
            Aircraft.objects.get(pk=fleet["G-DGHI"].pk),
            basis=ProgrammeBasis.INSTRUCTIONS,
            reference="[Programme Reference]",
            hours_per_day=Decimal("0.8"),
        )
        programme_services.record_review(dghi, date(2026, 3, 4))
        for task, manufacturer, says, measures, justification in DEPARTURES:
            programme_services.add_departure(
                dghi,
                task=task,
                manufacturer=manufacturer,
                programme_says=says,
                compensating_measures=measures,
                justification=justification,
                recorded_on=date(2026, 3, 4),
                owner_copy_sent_on=date(2026, 3, 4),
            )
        fmno = Programme.objects.get(aircraft_id=fleet["G-FMNO"].pk)
        review = programme_services.start_annual_review(fmno, date(2026, 11, 9))
        points: dict[str, object] = {}
        for name, (note, done) in FMNO_REVIEW.items():
            points[f"{name}_note"] = note
            points[f"{name}_done"] = done
        programme_services.note_annual_review(review, **points)


# The Directives board, Sources: source, what it covers, a note, the day last
# checked, and the next check as a day or in words.
SOURCES: tuple[tuple[str, str, str, date, date | None, str], ...] = (
    ("Civil Aviation Authority", "United Kingdom Directives, All Aircraft", "",
     date(2026, 11, 16), date(2026, 11, 30), ""),
    ("CAP 747 Mandatory Requirements for Airworthiness", "Generic Requirements and Concessions",
     "Issue [Issue]", date(2026, 11, 16), None, "Each Amendment"),
    ("Federal Aviation Administration",
     "Piper and Cessna Airframes, Lycoming Engines, Sensenich and McCauley Propellers",
     "State of Design, Biweekly [Reference]", date(2026, 11, 16), date(2026, 11, 30), ""),
    ("European Union Aviation Safety Agency", "Robin and Grob Airframes", "State of Design",
     date(2026, 11, 16), date(2026, 11, 30), ""),
)  # fmt: skip


def add_sources(ours: Organisation, by: User) -> None:
    """Add the sources checked for new directives, as Planning and Records."""
    with working_for(ours.id, by.id):
        for name, covers, note, checked_on, next_check_on, words in SOURCES:
            source = directive_services.add_source(ours, name=name, covers=covers, note=note)
            directive_services.record_source_check(
                source, checked_on=checked_on, next_check_on=next_check_on, next_check_note=words
            )


# The Transfers board: the ten items of G-HKLM's transfer in, started 9 November
# 2026, 4 of 10 complete. The state of each and its note.
HKLM_ITEMS: tuple[tuple[ItemState, str], ...] = (
    (ItemState.COMPLETE, "Piper PA-38 Series (Lycoming)"),
    (ItemState.COMPLETE, "Signed 9 November 2026, [Owner Name G-HKLM]"),
    (ItemState.NOT_APPLICABLE, "United Kingdom Register"),
    (ItemState.COMPLETE, "[Previous Organisation], Sent 12 November 2026"),
    (ItemState.IN_PROGRESS, "Engine Logbook Volume 1 Requested 13 November 2026"),
    (ItemState.IN_PROGRESS, "Lucy Grant"),
    (ItemState.OPEN, ""),
    (ItemState.OPEN, ""),
    (ItemState.OPEN, ""),
    (ItemState.OPEN, ""),
)

_AIRFRAME, _ENGINE, _PROPELLER = Product.AIRFRAME, Product.ENGINE, Product.PROPELLER
_PART = "[Part Number]"
# The Set Up Configuration board, Tracked Positions: product, chapter, position,
# whether it is a major item, the part number, the serial number, the source and
# whether it is recorded. 8 of the 12 are recorded.
HKLM_POSITIONS: tuple[tuple[Product, int, str, bool, str, str, str, bool], ...] = (
    (_ENGINE, 72, "Engine, Lycoming O-235", True, _PART, "[Serial Number Engine G-HKLM]",
     "Engine Logbook", True),
    (_PROPELLER, 61, "Propeller, Fixed Pitch", True, _PART, "[Serial Number Propeller G-HKLM]",
     "Propeller Logbook", True),
    (_ENGINE, 74, "Left Magneto", False, _PART, "[Serial Number Left Magneto]", "Engine Logbook",
     True),
    (_ENGINE, 74, "Right Magneto", False, _PART, "", "Engine Logbook, Volume 1 Requested", False),
    (_ENGINE, 73, "Carburettor", False, _PART, "[Serial Number Carburettor]", "Engine Logbook",
     True),
    (_AIRFRAME, 37, "Vacuum Pump", False, _PART, "", "Not in Records Received", False),
    (_AIRFRAME, 25, "Emergency Locator Transmitter", False, _PART,
     "[Serial Number Emergency Locator Transmitter]", "Airframe Logbook", True),
    (_AIRFRAME, 25, "Emergency Locator Transmitter Battery", False, _PART, "",
     "Airframe Logbook, Expiry [Date]", False),
    (_AIRFRAME, 34, "Mode S Transponder", False, _PART, "[Serial Number Transponder]",
     "Standard Change Record", True),
    (_AIRFRAME, 23, "Very High Frequency Radio, 8.33 Kilohertz", False, _PART,
     "[Serial Number Radio]", "Airframe Logbook", True),
    (_AIRFRAME, 33, "Landing Light", False, _PART, "", "Physical Survey, 12 November 2026", True),
    (_AIRFRAME, 25, "Fire Extinguisher", False, "", "", "Not in Records Received", False),
)  # fmt: skip

# Step 5 of the board: the changes embodied, and the position each changed.
HKLM_CHANGES = (
    ("Mode S Transponder", "[Standard Change Reference 3]", date(2021, 6, 8),
     "Mode S Transponder"),
    ("8.33 Kilohertz Radio", "[Standard Change Reference 4]", date(2018, 9, 3),
     "Very High Frequency Radio, 8.33 Kilohertz"),
)  # fmt: skip


def add_set_up(ours: Organisation, by: User, fleet: dict[str, Aircraft]) -> None:
    """Add G-HKLM's transfer checklist and the set-up of its configuration.

    As the Continuing Airworthiness Manager. The contract of 9 November
    2026 is already recorded. The baseline is not signed: four positions
    are not recorded, the landing light needs a recorded change, and the
    propeller's overhaul date is missing, as the board has it.
    """
    with working_for(ours.id, by.id):
        hklm = Aircraft.objects.get(pk=fleet["G-HKLM"].pk)
        transfer = configuration_services.start_transfer(hklm, started_on=date(2026, 11, 9))
        for item, (state, note) in zip(transfer.items.all(), HKLM_ITEMS, strict=True):
            if state != ItemState.OPEN:
                configuration_services.set_item(item, state=state, note=note)

        fitted = {}
        for name, serial, values in (
            ("Engine, Lycoming O-235-L2C", "[Serial Number Engine G-HKLM]",
             {"basis": LimitBasis.NONE}),
            ("Propeller, Fixed Pitch", "[Serial Number Propeller G-HKLM]",
             {"basis": _RECOMMENDED, "limit_hours": Decimal("2000"), "limit_months": 72}),
        ):  # fmt: skip
            component = component_services.add_component(
                ours,
                name=name,
                serial_number=serial,
                **values,
            )
            component_services.fit_component(
                component,
                hklm,
                position="Propeller" if "Propeller" in name else "Engine",
                fitted_on=date(2019, 5, 2),
                airframe_hours_fitted=Decimal("2150.0"),
                hours_at_fitting=Decimal("0.0"),
            )
            fitted[serial] = component

        changes = {}
        for title, reference, embodied_on, changed in HKLM_CHANGES:
            changes[changed] = modification_services.record_change(
                hklm,
                title=title,
                route=Route.STANDARD_CHANGE,
                reference=reference,
                mass_effect=Decimal("0.0"),
                embodied_on=embodied_on,
            )
        for product, chapter, name, major, part, serial, source, recorded in HKLM_POSITIONS:
            position = configuration_services.add_position(
                hklm,
                product=product,
                chapter=chapter,
                name=name,
                tracked=True,
                major=major,
                part_number=part,
                source=source,
            )
            if recorded:
                configuration_services.record_position(
                    position,
                    source=source,
                    part_number=part,
                    serial_number=serial,
                    needs_change=name == "Landing Light",
                    change=changes.get(name),
                    component=fitted.get(serial),
                )
