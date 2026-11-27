"""The sample's records for Continuing Airworthiness, the Rest (Phase 1 of the canvas build).

Everything here is from design-system/SampleData.md and the boards of
Phase 1, made through the same services as the pages. It is added when a
new sample is built. Today in the sample world is 18 November 2026.
"""

from datetime import date

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.defects import services as defect_services
from airworthiness_plus.defects.models import Basis, Decision, Defect
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Person, StaffGroup
from airworthiness_plus.programme.models import WorkDone

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
