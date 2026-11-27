"""The sample organisation, its people, its fleet and their records (Step 9 of private beta).

Everything here is from design-system/SampleData.md, with placeholders
in square brackets for anything that would otherwise look real. The
records are made through the same services as the pages, so every rule
applies to them. The tests build their sample from this module, so the
organisation that is seeded is the one the tests check.

Today in the sample world is 18 November 2026.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter, CounterKind
from airworthiness_plus.customers import services as customer_services
from airworthiness_plus.customers.models import Customer
from airworthiness_plus.customers.models import Kind as CustomerKind
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.directives.models import Decision, Directive
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import DataSet, Evidence, Kind
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Basis, InspectionCategory, Task
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.reviews.models import Certificate, ReviewStaff
from airworthiness_plus.sample import phase1, planning
from airworthiness_plus.sample.models import Added, Part
from airworthiness_rules.intervals import Interval, Reading, TaskKind

TODAY = date(2026, 11, 18)

NAME = "[Your Organisation]"
APPROVAL_REFERENCE = "UK.CAO.[Number]"
ADDRESS = "[Organisation Address]"
SCOPE = (
    "Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less; Sailplanes and Powered "
    "Sailplanes (management and review only); Piston Engines, Lycoming and Continental; "
    "C14 Landing Gear; C16 Propellers"
)

GROB = "Grob G115/120 Series (Lycoming)"
PA38 = "Piper PA-38 Series (Lycoming)"
C172 = "Cessna/Reims-Cessna 172/F172 Series (Lycoming)"

# SampleData.md, Fleet: Aircraft Registration, Type Rating, Owned By, Airframe Hours.
FLEET = (
    ("G-DGHI", "Piper PA-28 Series (Lycoming)", "Flying Club", "9874.3"),
    ("G-EJKL", "Cessna/Reims-Cessna 152/F152 Series (Lycoming)", "Pilot-Owner", "11206.8"),
    ("G-ABCD", "Piper PA-28 Series (Lycoming)", "Pilot-Owner", "6412.6"),
    ("G-BXYZ", C172, "Syndicate of 6", "3318.0"),
    ("G-FMNO", GROB, "Pilot-Owner", "4950.2"),
    ("G-CDEF", "Robin DR 400 series (Lycoming)", "Syndicate of 4", "7731.5"),
)

# SampleData.md, Commercial: 7 customers, one for each aircraft. The Customers
# board gives the name, the kind and the month each became a customer; the
# first day of the month is taken. Each name is written apart from the others,
# so that one can be told from another.
CUSTOMERS: dict[str, tuple[str, CustomerKind, int | None, date]] = {
    "G-DGHI": ("[Flying Club Name]", CustomerKind.FLYING_CLUB, None, date(2025, 3, 1)),
    "G-EJKL": ("[Owner Name G-EJKL]", CustomerKind.PILOT_OWNER, None, date(2025, 12, 1)),
    "G-ABCD": ("[Owner Name G-ABCD]", CustomerKind.PILOT_OWNER, None, date(2026, 3, 1)),
    "G-BXYZ": ("[Syndicate Name G-BXYZ]", CustomerKind.SYNDICATE, 6, date(2025, 1, 1)),
    "G-FMNO": ("[Owner Name G-FMNO]", CustomerKind.PILOT_OWNER, None, date(2024, 5, 1)),
    "G-CDEF": ("[Syndicate Name G-CDEF]", CustomerKind.SYNDICATE, 4, date(2024, 4, 1)),
    "G-HKLM": ("[Owner Name G-HKLM]", CustomerKind.PILOT_OWNER, None, date(2026, 11, 1)),
}

# SampleData.md, Fleet: Review Certificate Valid To. G-CDEF is shown after its
# review of 11 November 2026; before it the certificate was valid to 2 December 2026.
# Lucy Grant's reviews from before these records (SampleData.md, recency figures).
# The sample does not say who issued the earlier certificates of G-EJKL and G-CDEF.
LUCY_BEFORE = frozenset({"G-DGHI", "G-ABCD", "G-BXYZ", "G-FMNO"})
CERTIFICATES_BEFORE = (
    ("G-DGHI", date(2027, 5, 19)),
    ("G-EJKL", date(2026, 12, 6)),
    ("G-ABCD", date(2027, 3, 14)),
    ("G-BXYZ", date(2027, 8, 2)),
    ("G-FMNO", date(2027, 4, 27)),
    ("G-CDEF", date(2026, 12, 2)),
)


class People(Protocol):
    """The organisation and one person for each role."""

    @property
    def ours(self) -> Organisation: ...
    @property
    def administrator(self) -> User: ...
    @property
    def lucy(self) -> User: ...
    @property
    def planner(self) -> User: ...
    @property
    def reviewer(self) -> User: ...
    @property
    def reader(self) -> User: ...


@dataclass(frozen=True)
class Staff:
    """The sample organisation and its people."""

    ours: Organisation
    administrator: User
    lucy: User  # Airworthiness Review Staff and Continuing Airworthiness Manager
    planner: User  # Planning and Records
    reviewer: User  # Airworthiness Review Staff only
    reader: User  # Read Only


@dataclass(frozen=True)
class Reviews:
    """The review staff and the certificate issued for G-CDEF."""

    lucy: ReviewStaff
    reviewer: ReviewStaff
    cdef: Certificate


def add_people(ours: Organisation, administrator: User) -> Staff:
    """Add one user for each role. None has a password until the Administrator gives one."""

    def add(username: str, full_name: str, *roles: Role) -> User:
        return User.objects.create_user(
            organisation=ours,
            username=f"{username}@your-organisation.example",
            full_name=full_name,
            roles=list(roles),
        )

    with working_for(ours.id, administrator.id):
        lucy = add(
            "lucy.grant",
            "Lucy Grant",
            Role.AIRWORTHINESS_REVIEW_STAFF,
            Role.CONTINUING_AIRWORTHINESS_MANAGER,
        )
        planner = add("planning", "[Planning and Records Name]", Role.PLANNING_AND_RECORDS)
        reviewer = add("review", "[Review Name]", Role.AIRWORTHINESS_REVIEW_STAFF)
        reader = add("reader", "[Read Only Name]", Role.READ_ONLY)
    add_person_records(ours, administrator)
    with working_for(ours.id, administrator.id):
        sam = Person.objects.get(full_name="Sam Patel")
        people_services.record_recurrent_training(
            sam,
            subject="Human Factors",
            evidence_reference="[Training Certificate]",
            completed_on=date(2024, 12, 6),
            due_on=date(2026, 12, 6),
        )
    return Staff(ours, administrator, lucy, planner, reviewer, reader)


# SampleData.md, People, and the Staff board: name, role, staff group, who they
# report to, employment, licence, the day they joined and the day they left.
# Each person is listed after the person they report to. Five have a sign-in,
# named in ``SIGN_INS``.
_M, _C, _R, _O = (
    StaffGroup.MANAGEMENT,
    StaffGroup.CERTIFYING,
    StaffGroup.REVIEW,
    StaffGroup.OTHER,
)
_CONTRACTED = Employment.CONTRACTED
_MANAGER = "[Continuing Airworthiness Manager]"
_MAINTENANCE = "[Maintenance Manager]"
_COMPLIANCE = "[Compliance Monitoring Manager]"
PEOPLE: tuple[
    tuple[str, str, StaffGroup, str, Employment, str, date | None, date | None], ...
] = (
    ("[Accountable Manager]", "Accountable Manager", _M, "", Employment.EMPLOYED, "", None, None),
    (_MANAGER, "Continuing Airworthiness Manager", _M, "[Accountable Manager]",
     Employment.EMPLOYED, "", None, None),
    (_MAINTENANCE, "Maintenance Manager", _M, "[Accountable Manager]",
     Employment.EMPLOYED, "", None, None),
    (_COMPLIANCE, "Compliance Monitoring Manager", _M, "[Accountable Manager]",
     Employment.EMPLOYED, "", None, None),
    ("Lucy Grant", "Airworthiness Review Staff", _R, _MANAGER, Employment.EMPLOYED, "", None, None),
    ("[Review Name]", "Airworthiness Review Staff", _R, _MANAGER,
     Employment.EMPLOYED, "", None, None),
    ("[Planning and Records Name]", "Planning and Records", _O, _MAINTENANCE,
     Employment.EMPLOYED, "", date(2026, 9, 1), None),
    ("Chris Moore", "Certifying Staff", _C, _MAINTENANCE,
     Employment.EMPLOYED, "Part-66 B1.2", None, None),
    ("Sam Patel", "Certifying Staff", _C, _MAINTENANCE,
     Employment.EMPLOYED, "Part-66 B1.2", None, None),
    ("[Certifying Staff Name]", "Certifying Staff", _C, _MAINTENANCE,
     _CONTRACTED, "Part-66 L2", None, None),
    ("[Contract Engineer]", "Certifying Staff", _C, _MAINTENANCE,
     _CONTRACTED, "Part-66 B1.2", None, None),
    ("Ellie Ward", "Mechanic, Trainee", _O, _MAINTENANCE,
     Employment.EMPLOYED, "Working Toward Part-66 B1.2", date(2025, 1, 6), None),
    ("[Independent Auditor]", "Auditor", _O, _COMPLIANCE, _CONTRACTED, "", None, None),
    # A sign-in of the sample for the Read Only role. Not a person of SampleData.md.
    ("[Read Only Name]", "", _O, "", Employment.EMPLOYED, "", None, None),
    # Former airworthiness review staff: left 30 June 2025.
    ("[Former Review Name]", "Airworthiness Review Staff", _R, "",
     Employment.EMPLOYED, "", None, date(2025, 6, 30)),
)  # fmt: skip


DOMAIN = "your-organisation.example"
# The sign-ins of the sample, by the name of the person each belongs to. A
# sign-in of the sample is known by its user name, which the sample gave it and
# which is used once across every organisation. Nobody is found by their name:
# two people may share one (independent review of 24 November 2026, finding 4).
SIGN_INS = {
    "[Accountable Manager]": f"accountable.manager@{DOMAIN}",
    "Lucy Grant": f"lucy.grant@{DOMAIN}",
    "[Planning and Records Name]": f"planning@{DOMAIN}",
    "[Review Name]": f"review@{DOMAIN}",
    "[Read Only Name]": f"reader@{DOMAIN}",
}


def _says_only_a_name(person: Person) -> bool:
    """Return whether the record is as it was made with its sign-in: a name and no more."""
    return (
        not person.role
        and not person.licence
        and person.staff_group == StaffGroup.OTHER
        and person.employment == Employment.EMPLOYED
        and person.reports_to_id is None
        and person.joined_on is None
        and person.left_on is None
    )


def add_person_records(ours: Organisation, administrator: User) -> int:
    """Add the people of SampleData.md to the organisation, once. Return how many were added.

    Run when the sample is built, and by the test site at every start for a
    sample seeded before person records (``operations/test-site.md``). It
    adds what is missing and changes nothing that anyone has recorded
    (REQ-218; independent review of 24 November 2026, finding 3):

    - once it has run for an organisation it does nothing more, ever. A
      record says that it has, so a person renamed since is not added again;
    - a sample given its people before that record was kept has people with
      no sign-in already. It is taken as done, and nothing is added;
    - otherwise each person with no sign-in is added, and the record of each
      sample sign-in, known by its user name, is completed if it still says
      only a name. Nobody is found by name, and no person who already has a
      record is given a reporting line.

    Every record is made or changed through the services the pages use, so
    every check applies.
    """
    with working_for(ours.id, administrator.id):
        if Added.objects.filter(part=Part.PEOPLE).exists():
            return 0
        if Person.objects.filter(user__isnull=True).exists():
            Added.objects.create(organisation=ours, part=Part.PEOPLE)
            return 0
        sign_ins = {
            user.username: user for user in User.objects.filter(username__in=SIGN_INS.values())
        }
        found: dict[str, Person] = {}
        added = 0
        for name, role, group, above, employment, licence, joined, left in PEOPLE:
            reports_to = found.get(above) if above else None
            user = sign_ins.get(SIGN_INS.get(name, ""))
            if user is None:
                found[name] = people_services.add_person(
                    organisation=ours,
                    full_name=name,
                    role=role,
                    staff_group=group,
                    reports_to=reports_to,
                    employment=employment,
                    licence=licence,
                    joined_on=joined,
                    left_on=left,
                )
                added += 1
                continue
            person = Person.objects.get(user=user)
            if _says_only_a_name(person):
                people_services.change_person(
                    person,
                    full_name=person.full_name,
                    role=role,
                    staff_group=group,
                    reports_to=reports_to,
                    employment=employment,
                    licence=licence,
                    joined_on=joined,
                    left_on=None,
                    by=administrator,
                )
            found[name] = person
        Added.objects.create(organisation=ours, part=Part.PEOPLE)
    return added


def add_fleet(people: People) -> dict[str, Aircraft]:
    """Add the six aircraft of the Fleet and the Transfer In, as Lucy Grant."""
    fleet: dict[str, Aircraft] = {}

    def customer(registration: str) -> Customer:
        name, kind, members, since = CUSTOMERS[registration]
        return customer_services.add_customer(
            organisation=people.ours, name=name, kind=kind, members=members, customer_since=since
        )

    with working_for(people.ours.id, people.lucy.id):
        for registration, type_rating, _, hours in FLEET:
            fleet[registration] = aircraft_services.add_aircraft(
                organisation=people.ours,
                registration=registration,
                type_rating=type_rating,
                customer=customer(registration),
                airframe=Reading(TODAY, Decimal(hours), 0),
            )
        # G-DGHI: Unserviceable, Stabilator Trim Cable, grounded since 14 November.
        aircraft_services.make_unserviceable(
            fleet["G-DGHI"], "Stabilator Trim Cable", date(2026, 11, 14)
        )
        # G-HKLM: Transfer In, Records 14 of 18 Received.
        fleet["G-HKLM"] = aircraft_services.add_aircraft(
            organisation=people.ours,
            registration="G-HKLM",
            type_rating=PA38,
            customer=customer("G-HKLM"),
            records_expected=18,
            records_received=14,
        )
    return fleet


def add_programmes(people: People, fleet: dict[str, Aircraft]) -> dict[str, Task]:
    """Add the programmes, tasks and work done of SampleData.md, Maintenance Programme Inputs.

    G-BXYZ and G-FMNO are taken to be on the Minimum Inspection Programme.
    G-ABCD and G-CDEF are on the design approval holder's instructions.
    """
    tasks: dict[str, Task] = {}

    def airframe(registration: str) -> Counter:
        return fleet[registration].counters.get(kind=CounterKind.AIRFRAME)

    def done(registration: str, task: Task, on: date, hours: str) -> None:
        programme_services.record_work(
            fleet[registration],
            task=task,
            description=task.title,
            dated=on,
            hours=Decimal(hours),
            cycles=0,
            release_reference="[Release Reference]",
            release_recorded_on=on,
        )

    with working_for(people.ours.id, people.lucy.id):
        abcd = programme_services.set_up_programme(
            fleet["G-ABCD"],
            basis=Basis.INSTRUCTIONS,
            reference="[Programme Reference]",
            hours_per_day=Decimal("0.8"),
        )
        tasks["G-ABCD"] = programme_services.add_task(
            abcd,
            title="50-Hour Check",
            kind=TaskKind.PROGRAMME_TASK,
            counter=airframe("G-ABCD"),
            source="[Maintenance Manual Reference]",
            interval=Interval(hours=Decimal("50")),
        )
        done("G-ABCD", tasks["G-ABCD"], date(2026, 10, 2), "6375.0")

        for registration, title, on, hours, rate in (
            ("G-BXYZ", "100-Hour or Annual Check", date(2026, 7, 30), "3259.0", "0.5"),
            ("G-FMNO", "Annual Check", date(2026, 2, 4), "4912.0", "0.2"),
        ):
            programme = programme_services.set_up_programme(
                fleet[registration],
                basis=Basis.MINIMUM_INSPECTION_PROGRAMME,
                inspection_category=InspectionCategory.AEROPLANE,
                reference="[Programme Reference]",
                hours_per_day=Decimal(rate),
            )
            tasks[registration] = programme_services.add_task(
                programme,
                title=title,
                kind=TaskKind.MINIMUM_INSPECTION_PROGRAMME,
                counter=airframe(registration),
                source="ML.A.302(d), AMC1 ML.A.302(d)",
                interval=Interval(hours=Decimal("100"), months=12),
            )
            done(registration, tasks[registration], on, hours)

        # G-CDEF: the engine counts hours since its overhaul; overhaul every 2,000 hours.
        cdef = programme_services.set_up_programme(
            fleet["G-CDEF"],
            basis=Basis.INSTRUCTIONS,
            reference="[Programme Reference]",
            hours_per_day=Decimal("0.6"),
        )
        engine = aircraft_services.add_counter(fleet["G-CDEF"], CounterKind.ENGINE, "Engine 1")
        aircraft_services.enter_utilisation(engine, Reading(TODAY, Decimal("1780.0"), 0))
        tasks["G-CDEF"] = programme_services.add_task(
            cdef,
            title="Engine Overhaul",
            kind=TaskKind.PROGRAMME_TASK,
            counter=engine,
            source="[Engine Manufacturer's Service Instruction]",
            interval=Interval(hours=Decimal("2000")),
            starts=Reading(date(2019, 3, 12), Decimal("0.0"), 0),
        )
        programme_services.record_review(cdef, date(2026, 11, 11))
    return tasks


def add_reviews(people: People, fleet: dict[str, Aircraft]) -> Reviews:
    """Add the review staff and certificates of SampleData.md.

    Lucy Grant: accepted 9 June 2023; last review 11 November 2026, G-CDEF.
    The other review staff member: 4 months of continuing airworthiness
    work, recency lapsing 2 December 2026, so their last review is taken
    as 2 December 2025.
    """
    with working_for(people.ours.id, people.administrator.id):
        lucy = review_services.add_review_staff(
            user=people.lucy,
            authorisation_reference="[Authorisation Reference 1]",
            accepted_on=date(2023, 6, 9),
            # Her review of G-BXYZ, whose certificate runs to 2 August 2027.
            last_review_before_records=date(2026, 8, 2),
        )
        reviewer = review_services.add_review_staff(
            user=people.reviewer,
            authorisation_reference="[Authorisation Reference 2]",
            accepted_on=date(2021, 3, 1),
            months_involved=4,
            last_review_before_records=date(2025, 12, 2),
        )
    with working_for(people.ours.id, people.lucy.id):
        for registration, valid_to in CERTIFICATES_BEFORE:
            hers = registration in LUCY_BEFORE
            review_services.record_certificate(
                fleet[registration],
                reference=f"[Certificate Reference {registration}]",
                issued_on=valid_to.replace(year=valid_to.year - 1),
                valid_to=valid_to,
                issued_by=lucy if hers else None,
                issued_elsewhere_by="" if hers else "[Recorded From the Aircraft Records]",
            )
        cdef = review_services.issue_certificate(
            fleet["G-CDEF"],
            staff=lucy,
            issued_on=date(2026, 11, 11),
            airframe_hours=Decimal("7720.0"),
        )
    return Reviews(lucy, reviewer, cdef)


def add_directives(people: People, fleet: dict[str, Aircraft]) -> dict[int, Directive]:
    """Add four directives, and for G-ABCD: one repeating, one not applicable,
    one not yet decided, one to be done once."""
    abcd = fleet["G-ABCD"]
    with working_for(people.ours.id, people.lucy.id):
        recorded = {
            number: directive_services.record_directive(
                organisation=people.ours,
                number=f"[Directive Number {number}]",
                authority="Civil Aviation Authority",
                subject=subject,
                effective_date=effective,
            )
            for number, subject, effective in (
                (1, "[Fuel Selector Valve Inspection]", date(2026, 6, 1)),
                (2, "[Propeller Hub Inspection]", date(2026, 3, 3)),
                (3, "[Seat Rail Inspection]", date(2026, 11, 2)),
                (4, "[Placard Installation]", date(2026, 10, 1)),
            )
        }
        counter = abcd.counters.get(kind=CounterKind.AIRFRAME)
        # 1: first within 50 hours of 6,300.0 on 1 June 2026, then every 100 hours.
        repeating = directive_services.decide(
            directive=recorded[1],
            aircraft=abcd,
            decision=Decision.APPLICABLE,
            basis="Fuel Selector Valve Part Number Fitted, Logbook Checked",
            decided_by=people.lucy,
            action=directive_services.Action(
                counter=counter,
                starts=Reading(date(2026, 6, 1), Decimal("6300.0"), 0),
                first=Interval(hours=Decimal("50")),
                repeat=Interval(hours=Decimal("100")),
            ),
        )
        directive_services.record_compliance(
            repeating,
            method="Inspected in Accordance with Paragraph 2",
            dated=date(2026, 7, 20),
            hours=Decimal("6350.0"),
            cycles=0,
            release_reference="[Release Reference 4]",
            release_recorded_on=date(2026, 7, 20),
        )
        directive_services.decide(
            directive=recorded[2],
            aircraft=abcd,
            decision=Decision.NOT_APPLICABLE,
            basis="Propeller Model Not Fitted, Logbook Checked",
            decided_by=people.lucy,
        )
        # 4: once, within 3 months of 1 October 2026.
        directive_services.decide(
            directive=recorded[4],
            aircraft=abcd,
            decision=Decision.APPLICABLE,
            basis="All Serial Numbers",
            decided_by=people.lucy,
            action=directive_services.Action(
                counter=counter,
                starts=Reading(date(2026, 10, 1), Decimal("6370.0"), 0),
                first=Interval(months=3),
            ),
        )
    return recorded


def add_maintenance_data(people: People) -> dict[str, DataSet]:
    """Add the maintenance data of SampleData.md, Documentation."""
    with working_for(people.ours.id, people.planner.id):
        sets = {
            # Grob G 115 manual: amendment to check by 20 November 2026 (G-FMNO).
            "grob": data_services.record_data(
                title="Grob G 115 Maintenance Manual",
                author="[Type Certificate Holder]",
                kind=Kind.INSTRUCTIONS,
                applies_to=[GROB],
                amendment_service="[Amendment Service]",
                revision_date=date(2026, 3, 1),
                organisation=people.ours,
                revision="[Revision]",
            ),
            # Piper PA-38 Series manual not held, needed for G-HKLM.
            "pa38": data_services.record_data(
                organisation=people.ours,
                title="Piper PA-38 Series Maintenance Manual",
                author="[Type Certificate Holder]",
                kind=Kind.INSTRUCTIONS,
                applies_to=[PA38],
                held=False,
            ),
            # CAP 747, checked 16 November 2026.
            "cap747": data_services.record_data(
                title="CAP 747 Mandatory Requirements for Airworthiness",
                author="Civil Aviation Authority",
                kind=Kind.AUTHORITY,
                mandatory=True,
                amendment_service="[Amendment Service]",
                revision_date=date(2026, 9, 1),
                organisation=people.ours,
                revision="[Revision]",
            ),
            # G-BXYZ owner-provided supplementary type certificate instructions,
            # confirmed current in writing 2 June 2026.
            "bxyz": data_services.record_data(
                title="[Supplementary Type Certificate Instructions]",
                author="[Supplementary Type Certificate Holder]",
                kind=Kind.INSTRUCTIONS,
                applies_to=[C172],
                revision_date=date(2025, 5, 1),
                provided_by="Syndicate of 6",
                evidence=Evidence.WRITTEN_CONFIRMATION,
                evidence_dated=date(2026, 6, 2),
                organisation=people.ours,
                revision="[Revision]",
            ),
        }
        data_services.record_check(
            sets["grob"],
            checked_by=people.planner,
            checked_on=date(2026, 11, 2),
            result="No Amendment",
            next_due=date(2026, 11, 20),
        )
        data_services.record_check(
            sets["cap747"],
            checked_by=people.planner,
            checked_on=date(2026, 11, 16),
            result="No Amendment",
            next_due=date(2026, 11, 30),
        )
    return sets


def add_other_work(people: People, fleet: dict[str, Aircraft]) -> None:
    """Add work that is not a task of a programme.

    G-ABCD: right main tyre replaced by the pilot-owner on 22 October 2026
    at 6,390.0 airframe hours; its release is not yet in the records, and
    is due there by 21 November 2026 (REQ-051).
    """
    with working_for(people.ours.id, people.planner.id):
        programme_services.record_work(
            fleet["G-ABCD"],
            description="Right Main Tyre Replaced",
            dated=date(2026, 10, 22),
            hours=Decimal("6390.0"),
            cycles=0,
            by_pilot_owner=True,
            pilot_owner_told_on=date(2026, 10, 23),
        )


def build(ours: Organisation, administrator: User) -> Staff:
    """Add everything of the sample to an organisation that has only its Administrator."""
    people = add_people(ours, administrator)
    fleet = add_fleet(people)
    add_programmes(people, fleet)
    add_other_work(people, fleet)
    # Continuing Airworthiness, the Rest (Phase 1 of the canvas build).
    phase1.add_defects(ours, people.planner, fleet)
    phase1.add_repeat_actions(ours, people.lucy)
    phase1.add_contracts(ours, people.lucy, fleet)
    phase1.add_releases(ours, people.planner, fleet)
    phase1.add_components(ours, people.planner, fleet)
    phase1.add_modifications(ours, people.planner, fleet)
    phase1.add_programme_records(ours, people.lucy, fleet)
    phase1.add_sources(ours, people.planner)
    phase1.add_set_up(ours, people.lucy, fleet)
    add_reviews(people, fleet)
    add_directives(people, fleet)
    add_maintenance_data(people)
    planning.add_work_packages(ours, people.planner, fleet["G-EJKL"])
    return people
