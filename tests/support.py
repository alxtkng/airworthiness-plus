"""Shared test set-up: the sample organisation, its people and its fleet.

Everything here is from design-system/SampleData.md. Today in the sample
world is 18 November 2026.
"""

from dataclasses import dataclass

from django.http import HttpResponse
from django.test import Client
from django.utils import timezone

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.programme.models import Task
from airworthiness_plus.sample import build
from tests.conftest import as_owner

# The sample itself is built by the application (``airworthiness_plus.sample``),
# so the organisation that is seeded on a server is the one tested here.
TODAY = build.TODAY
FLEET = build.FLEET
CERTIFICATES_BEFORE = build.CERTIFICATES_BEFORE
SCOPE = build.SCOPE
BACKEND = "airworthiness_plus.accounts.backends.OrganisationBackend"


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
            name=build.NAME,
            approval_reference=build.APPROVAL_REFERENCE,
            address=build.ADDRESS,
            privileges=list(Privilege),
            scope_of_work=SCOPE,
            first_user_username="accountable.manager@your-organisation.example",
            first_user_full_name="[Accountable Manager]",
        )
        other, stranger = provision_organisation(
            name="[Other Organisation]",
            approval_reference="UK.CAO.[Other Number]",
            # Every privilege, as ours has: what keeps it out is that it is another
            # organisation, and nothing else.
            privileges=list(Privilege),
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username="name@other-organisation.example",
            first_user_full_name="[Other Name]",
        )
    with working_for(other.id, stranger.id):
        User.objects.filter(pk=stranger.pk).update(
            roles=[Role.ADMINISTRATOR, Role.CONTINUING_AIRWORTHINESS_MANAGER]
        )
        stranger.refresh_from_db()

    staff = build.add_people(ours, administrator)
    return Sample(
        ours,
        administrator,
        staff.lucy,
        staff.planner,
        staff.reviewer,
        staff.reader,
        other,
        stranger,
    )


def add_sample_fleet(sample: Sample) -> dict[str, Aircraft]:
    """Add the six aircraft of the Fleet and the Transfer In, as Lucy Grant."""
    return build.add_fleet(sample)


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
    """Add the programmes, tasks and work done of SampleData.md."""
    return build.add_programmes(sample, fleet)


SampleReviews = build.Reviews


def add_sample_reviews(sample: Sample, fleet: dict[str, Aircraft]) -> build.Reviews:
    """Add the review staff and certificates of SampleData.md."""
    return build.add_reviews(sample, fleet)


# REQ-193, written out here and not taken from the application: amber for what
# is due soon or waiting, red for what is overdue or stops the aircraft, green
# only for Serviceable.
_DOTS = {
    "Serviceable": "ok",
    "Due Soon": "due",
    "Due": "due",
    "Within Tolerance": "due",
    "To Assess": "due",
    "Overdue": "stop",
    "Unserviceable": "stop",
}


def dot(word: str) -> str:
    """Return a status as the page writes it: a coloured dot and the word."""
    return f'<span class="status status-{_DOTS[word]}">{word}</span>'


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def call(client: Client, method: str, path: str) -> HttpResponse:
    return get(client, path) if method == "GET" else post(client, path)
