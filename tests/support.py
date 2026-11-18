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
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_rules.intervals import Reading
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
