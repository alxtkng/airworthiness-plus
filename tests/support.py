"""Shared test set-up: the sample organisation, its people and its fleet.

Everything here is from design-system/SampleData.md. Today in the sample
world is 18 November 2026.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.test import Client
from django.utils import timezone

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft import services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Basis, InspectionCategory, Task
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.reviews.models import Certificate, ReviewStaff
from airworthiness_rules.intervals import Interval, Reading, TaskKind
from tests.conftest import as_owner

TODAY = date(2026, 11, 18)
BACKEND = "airworthiness_plus.accounts.backends.OrganisationBackend"

SCOPE = (
    "Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less; Sailplanes and Powered "
    "Sailplanes (management and review only); Piston Engines, Lycoming and Continental; "
    "C14 Landing Gear; C16 Propellers"
)

# SampleData.md, Fleet: Aircraft Registration, Type Rating, Owned By, Airframe Hours.
FLEET = (
    ("G-DGHI", "Piper PA-28 Series (Lycoming)", "Flying Club", "9874.3"),
    ("G-EJKL", "Cessna/Reims-Cessna 152/F152 Series (Lycoming)", "Pilot-Owner", "11206.8"),
    ("G-ABCD", "Piper PA-28 Series (Lycoming)", "Pilot-Owner", "6412.6"),
    ("G-BXYZ", "Cessna/Reims-Cessna 172/F172 Series (Lycoming)", "Syndicate of 6", "3318.0"),
    ("G-FMNO", "Grob G115/120 Series (Lycoming)", "Pilot-Owner", "4950.2"),
    ("G-CDEF", "Robin DR 400 series (Lycoming)", "Syndicate of 4", "7731.5"),
)


@dataclass(frozen=True)
class Sample:
    """The sample organisation, one user for each role, and another organisation."""

    ours: Organisation
    administrator: User
    lucy: User  # Airworthiness Review Staff and Continuing Airworthiness Manager
    planner: User  # Planning and Records
    reviewer: User  # Airworthiness Review Staff only
    reader: User  # Read Only
    other: Organisation
    stranger: User

    def by_role(self) -> dict[str, User]:
        return {
            "Administrator": self.administrator,
            "Continuing Airworthiness Manager": self.lucy,
            "Planning and Records": self.planner,
            "Airworthiness Review Staff": self.reviewer,
            "Read Only": self.reader,
        }


def make_sample() -> Sample:
    """Set up the sample organisation and another one that exists to be kept out."""
    with as_owner():
        ours, administrator = provision_organisation(
            name="[Your Organisation]",
            approval_reference="UK.CAO.[Number]",
            privileges=list(Privilege),
            scope_of_work=SCOPE,
            first_user_username="accountable.manager@your-organisation.example",
            first_user_full_name="[Accountable Manager]",
        )
        other, stranger = provision_organisation(
            name="[Other Organisation]",
            approval_reference="UK.CAO.[Other Number]",
            privileges=[Privilege.CONTINUING_AIRWORTHINESS_MANAGEMENT],
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username="name@other-organisation.example",
            first_user_full_name="[Other Name]",
        )
    with working_for(other.id, stranger.id):
        User.objects.filter(pk=stranger.pk).update(
            roles=[Role.ADMINISTRATOR, Role.CONTINUING_AIRWORTHINESS_MANAGER]
        )
        stranger.refresh_from_db()

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
    return Sample(ours, administrator, lucy, planner, reviewer, reader, other, stranger)


def add_sample_fleet(sample: Sample) -> dict[str, Aircraft]:
    """Add the six aircraft of the Fleet and the Transfer In, as Lucy Grant."""
    fleet: dict[str, Aircraft] = {}
    with working_for(sample.ours.id, sample.lucy.id):
        for registration, type_rating, owner, hours in FLEET:
            fleet[registration] = services.add_aircraft(
                organisation=sample.ours,
                registration=registration,
                type_rating=type_rating,
                owner=owner,
                airframe=Reading(TODAY, Decimal(hours), 0),
            )
        # G-DGHI: Unserviceable, Stabilator Trim Cable, grounded since 14 November.
        services.make_unserviceable(fleet["G-DGHI"], "Stabilator Trim Cable", date(2026, 11, 14))
        # G-HKLM: Transfer In, Records 14 of 18 Received.
        fleet["G-HKLM"] = services.add_aircraft(
            organisation=sample.ours,
            registration="G-HKLM",
            type_rating="Piper PA-38 Series (Lycoming)",
            owner="[Owner Name]",
            records_expected=18,
            records_received=14,
        )
    return fleet


def signed_in(user: User) -> Client:
    """Return a browser already signed in as ``user``. Sign-in has its own tests."""
    client = Client()
    client.force_login(user, backend=BACKEND)
    session = client.session
    now = timezone.now().isoformat()
    session["organisation"] = str(user.organisation_id)
    session["signed_in_at"] = now
    session["last_seen"] = now
    session.save()
    return client


def add_sample_programmes(sample: Sample, fleet: dict[str, Aircraft]) -> dict[str, Task]:
    """Add the programmes, tasks and work done of SampleData.md, Maintenance Programme Inputs.

    G-BXYZ and G-FMNO are taken to be on the Minimum Inspection Programme.
    G-ABCD and G-CDEF are on the design approval holder's instructions.
    """
    tasks: dict[str, Task] = {}

    def airframe(registration: str):  # type: ignore[no-untyped-def]
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

    with working_for(sample.ours.id, sample.lucy.id):
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
        engine = services.add_counter(fleet["G-CDEF"], CounterKind.ENGINE, "Engine 1")
        services.enter_utilisation(engine, Reading(TODAY, Decimal("1780.0"), 0))
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


# SampleData.md, Fleet: Review Certificate Valid To. G-CDEF is shown after its
# review of 11 November 2026; before it the certificate was valid to 2 December 2026.
CERTIFICATES_BEFORE = (
    ("G-DGHI", date(2027, 5, 19)),
    ("G-EJKL", date(2026, 12, 6)),
    ("G-ABCD", date(2027, 3, 14)),
    ("G-BXYZ", date(2027, 8, 2)),
    ("G-FMNO", date(2027, 4, 27)),
    ("G-CDEF", date(2026, 12, 2)),
)


@dataclass(frozen=True)
class SampleReviews:
    """The review staff and the certificate issued for G-CDEF."""

    lucy: ReviewStaff
    reviewer: ReviewStaff
    cdef: Certificate


def add_sample_reviews(sample: Sample, fleet: dict[str, Aircraft]) -> SampleReviews:
    """Add the review staff and certificates of SampleData.md.

    Lucy Grant: accepted 9 June 2023; last review 11 November 2026, G-CDEF.
    The other review staff member: 4 months of continuing airworthiness
    work, recency lapsing 2 December 2026, so their last review is taken
    as 2 December 2025.
    """
    with working_for(sample.ours.id, sample.administrator.id):
        lucy = review_services.add_review_staff(
            user=sample.lucy,
            authorisation_reference="[Authorisation Reference 1]",
            accepted_on=date(2023, 6, 9),
            # Her review of G-BXYZ, whose certificate runs to 2 August 2027.
            last_review_before_records=date(2026, 8, 2),
        )
        reviewer = review_services.add_review_staff(
            user=sample.reviewer,
            authorisation_reference="[Authorisation Reference 2]",
            accepted_on=date(2021, 3, 1),
            months_involved=4,
            last_review_before_records=date(2025, 12, 2),
        )
    with working_for(sample.ours.id, sample.lucy.id):
        for registration, valid_to in CERTIFICATES_BEFORE:
            review_services.record_certificate(
                fleet[registration],
                reference=f"[Certificate Reference {registration}]",
                issued_on=valid_to.replace(year=valid_to.year - 1),
                valid_to=valid_to,
                issued_elsewhere_by="[Recorded From the Aircraft Records]",
            )
        cdef = review_services.issue_certificate(
            fleet["G-CDEF"],
            staff=lucy,
            issued_on=date(2026, 11, 11),
            airframe_hours=Decimal("7720.0"),
        )
    return SampleReviews(lucy, reviewer, cdef)
