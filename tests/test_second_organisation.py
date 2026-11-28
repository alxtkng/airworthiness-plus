"""The second sample organisation, which holds Part-CAMO and Part-145 (REQ-218).

Decisions.md, Canvas Build, decision 1; design-system/SampleData.md, Second
Organisation. It exists so that what is shown only to a Part-CAMO or a
Part-145 can be shown, and it is kept apart from the first by the same
rules as any two organisations.
"""

import io
import re
from decimal import Decimal
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.customers.models import Customer
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import SIGNING_IN_SETTING
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.sample import build, second, test_site
from airworthiness_plus.sample.management.commands import prepare_test_site
from airworthiness_plus.sample.management.commands.seed_sample_organisation import (
    ADMINISTRATOR,
)
from airworthiness_plus.sample.management.commands.seed_sample_organisation import (
    seed as seed_first,
)
from tests.conftest import as_owner
from tests.support import TODAY, page, signed_in

pytestmark = pytest.mark.django_db

# Made up for these tests.
PASSWORD = "correct horse battery staple 2026"  # noqa: S105  # pragma: allowlist secret
SECOND_PASSWORD = "another horse battery staple 2026"  # noqa: S105  # pragma: allowlist secret
ROLE = "airworthiness_second_test"
SERVICE = "a service password for the tests"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    monkeypatch.setattr(sign_in, "today", lambda: TODAY)


@pytest.fixture
def both() -> tuple[Organisation, Organisation]:
    """Both sample organisations, as the test site holds them."""
    with as_owner():
        return seed_first(PASSWORD), second.seed(PASSWORD)


def user_named(username: str) -> User:
    """Read one user as the sign-in page does, by name."""
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT set_config(%s, %s, true)", [SIGNING_IN_SETTING, username])
        user: User = User.objects.get(username=username)
        cursor.execute("SELECT set_config(%s, '', true)", [SIGNING_IN_SETTING])
    return user


def test_the_second_organisation_is_that_of_the_sample(
    both: tuple[Organisation, Organisation],
) -> None:
    """REQ-218. SampleData.md, Second Organisation: every record it names, and no other."""
    _, theirs = both
    administrator = user_named(second.ADMINISTRATOR)
    assert administrator.organisation_id == theirs.id
    with working_for(theirs.id, administrator.id):
        organisation = Organisation.objects.get()
        assert (organisation.name, organisation.approval_type, organisation.approval_reference) == (
            "[Second Organisation]",
            "Part-CAMO",
            "UK.CAMO.[Number]",
        )
        assert organisation.privileges == []
        assert [(one.approval, one.reference) for one in approvals.held(organisation)] == [
            ("Part-CAMO", "UK.CAMO.[Number]"),
            ("Part-145", "UK.145.[Number]"),
        ]
        users = {user.full_name: user for user in User.objects.all()}
        assert {name: user.roles for name, user in users.items()} == {
            "[Second Accountable Manager]": [Role.ADMINISTRATOR],
            "[Second Continuing Airworthiness Manager]": [Role.CONTINUING_AIRWORTHINESS_MANAGER],
            "[Second Read Only Name]": [Role.READ_ONLY],
        }
        # Only the Administrator can sign in, with a first password to be changed.
        assert administrator.check_password(PASSWORD)
        assert administrator.password_must_change
        assert [user.has_usable_password() for user in users.values()].count(True) == 1
        people = {
            one.full_name: (one.role, one.staff_group, one.licence, one.user_id is not None)
            for one in Person.objects.all()
        }
        assert people == {
            "[Second Accountable Manager]": ("Accountable Manager", "Management", "", True),
            "[Second Continuing Airworthiness Manager]": (
                "Continuing Airworthiness Manager",
                "Management",
                "",
                True,
            ),
            "[Second Maintenance Manager]": ("Maintenance Manager", "Management", "", False),
            "[Second Certifying Staff Name]": (
                "Certifying Staff",
                "Certifying Staff",
                "Part-66 B1.2",
                False,
            ),
            "[Second Read Only Name]": ("", "Other Staff", "", True),
        }
        assert {one.name: one.owned_by for one in Customer.objects.all()} == {
            "[Operator Name]": "Operator",
            "[Second Owner Name]": "Pilot-Owner",
        }
        fleet = {
            one.registration: (
                one.type_rating,
                one.customer.name,
                aircraft_services.current_reading(one.counters.get(kind=CounterKind.AIRFRAME)),
            )
            for one in Aircraft.objects.select_related("customer")
        }
        assert {key: (value[0], value[1]) for key, value in fleet.items()} == {
            "G-JNOP": ("Piper PA-28 Series (Lycoming)", "[Operator Name]"),
            "G-KQRS": ("Cessna/Reims-Cessna 172/F172 Series (Lycoming)", "[Second Owner Name]"),
        }
        reading = fleet["G-JNOP"][2]
        assert reading is not None
        assert (reading.on, reading.hours) == (TODAY, Decimal("2406.5"))
        assert chain.problems(list(Event.objects.all())) == []


def test_maintenance_and_management_records_take_the_approval_for_the_activity(
    both: tuple[Organisation, Organisation],
) -> None:
    from airworthiness_plus.contracts import services as contracts
    from airworthiness_plus.contracts.models import Scope
    from airworthiness_plus.people import services as people_services
    from airworthiness_plus.programme import services as programmes
    from airworthiness_plus.releases import services as releases
    from airworthiness_plus.releases.models import IssuedBy
    from airworthiness_plus.tooling.release_evidence import Verification

    _, theirs = both
    administrator = user_named(second.ADMINISTRATOR)
    with working_for(theirs.id, administrator.id):
        aircraft = Aircraft.objects.get(registration="G-JNOP")
        staff = Person.objects.get(full_name="[Second Certifying Staff Name]")
        contract = contracts.draw_up_contract(
            aircraft,
            scope=Scope.ALL,
            type_of_operation="Private",
            owner_address="[Owner Address]",
            signed_on=TODAY,
        )
        work = programmes.record_work(
            aircraft,
            description="Inspection",
            dated=TODAY,
            hours=Decimal("2406.5"),
            cycles=0,
        )
        authorisation = people_services.record_maintenance_authorisation(
            staff, reference="CA-1", scope=aircraft.type_rating, valid_from=TODAY
        )
        certificate = releases.record_certificate(
            work,
            reference="CRS-1",
            kind=IssuedBy.ORGANISATION,
            issued_by=staff,
            issued_on=TODAY,
            maintenance_authorisation=authorisation,
            scope_confirmed=True,
            general_verification=Verification(
                "Part-145",
                TODAY,
                True,
                "None removed",
                "Fictitious Part-145 signed verification",
                "Fictitious tools accounted for",
            ),
        )
        assert contract.organisation_approval_reference == "UK.CAMO.[Number]"
        assert certificate.approval_reference == "UK.145.[Number]"
        assert certificate.general_verification.rule == "145.A.48(c)(1)"


def test_each_sample_organisation_sees_its_own_records_alone(
    both: tuple[Organisation, Organisation],
) -> None:
    """REQ-003, REQ-218. A second organisation on one system is the case the rules are for."""
    # The Administrators have a first password still to change, so the pages are
    # read as each organisation's Read Only user.
    first_administrator = user_named(ADMINISTRATOR)
    first_reader = user_named("reader@your-organisation.example")
    second_reader = user_named("reader@second-organisation.example")
    ours = page(signed_in(first_reader), "/dashboard/")
    theirs = page(signed_in(second_reader), "/dashboard/")
    assert "G-ABCD" in ours and "G-JNOP" not in ours and "G-KQRS" not in ours
    assert "G-JNOP" in theirs and "G-KQRS" in theirs
    for registration in ("G-ABCD", "G-DGHI", "G-HKLM"):
        assert registration not in theirs
    # Its two aircraft have nothing recorded yet, and the Dashboard says so.
    rows = re.findall(r"<td>(G-[A-Z]{4})</td>\s*<td>([^<]+)</td>", theirs)
    assert rows == [
        ("G-JNOP", "No Airworthiness Review Certificate Recorded"),
        ("G-JNOP", "No Maintenance Programme Set Up"),
        ("G-KQRS", "No Airworthiness Review Certificate Recorded"),
        ("G-KQRS", "No Maintenance Programme Set Up"),
    ]
    for path in ("/", "/staff/", "/customers/", "/settings/", "/organisation/"):
        body = page(signed_in(second_reader), path)
        assert "[Second Organisation]" in body, path
        assert "[Your Organisation]" not in body, path
        assert "Lucy Grant" not in body, path
    settings_page = page(signed_in(second_reader), "/settings/")
    assert "<td>Part-CAMO</td><td>UK.CAMO.[Number]</td><td>Held</td>" in settings_page
    assert "<td>Part-145</td><td>UK.145.[Number]</td><td>Held</td>" in settings_page
    with working_for(both[0].id, first_administrator.id):
        ours_aircraft = Aircraft.objects.get(registration="G-ABCD")
    client = signed_in(second_reader)
    assert client.get(f"/aircraft/{ours_aircraft.id}/", secure=True).status_code == 404


def test_the_command_sets_up_the_second_organisation_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-218. By the owner of the tables, with the password typed at the prompt."""
    monkeypatch.setattr("getpass.getpass", lambda prompt: PASSWORD)
    output = io.StringIO()
    with as_owner():
        call_command("seed_second_sample_organisation", stdout=output)
        assert Organisation.objects.count() == 1
        with pytest.raises(CommandError, match="already set up"):
            call_command("seed_second_sample_organisation", stdout=output)
        assert Organisation.objects.count() == 1
    assert f"Administrator {second.ADMINISTRATOR}" in output.getvalue()
    assert PASSWORD not in output.getvalue()


# The test site


@pytest.fixture
def given(monkeypatch: pytest.MonkeyPatch, settings: Any) -> None:
    """The values the start passes to the owner's work."""
    settings.DATABASE_OWNER_WORK = True
    monkeypatch.setenv(test_site.SERVICE_USER, ROLE)
    monkeypatch.setenv(test_site.SERVICE_PASSWORD, SERVICE)
    monkeypatch.setenv(test_site.ADMINISTRATOR_PASSWORD, PASSWORD)
    monkeypatch.setenv(test_site.SECOND_ADMINISTRATOR_PASSWORD, SECOND_PASSWORD)


def mark_the_database() -> None:
    """Mark the test database as the test site's own, as an empty one is marked."""
    with connection.cursor() as cursor:
        name = connection.ops.quote_name(connection.settings_dict["NAME"])
        cursor.execute(f"COMMENT ON DATABASE {name} IS %s", [prepare_test_site.MARK])


def prepare() -> list[str]:
    output = io.StringIO()
    call_command("prepare_test_site", stdout=output, verbosity=0)
    return output.getvalue().splitlines()


def test_a_test_site_seeded_before_the_canvas_build_is_given_what_is_missing(
    given: None,
) -> None:
    """REQ-218. The database live on 24 November 2026 held the first organisation alone.

    Its sign-ins had been given their person records by the migration, and
    nothing more. The next start adds the people of SampleData.md who have
    no sign-in, completes the records of those who do, and sets up the
    second organisation. It changes nothing that was there, and a start
    after that changes nothing at all.
    """
    with as_owner():
        mark_the_database()
        # The first organisation as it stood: its sign-ins, each with a bare person record.
        ours, administrator = provision_organisation(
            name=build.NAME,
            approval_reference=build.APPROVAL_REFERENCE,
            address=build.ADDRESS,
            privileges=list(Privilege),
            scope_of_work=build.SCOPE,
            first_user_username=ADMINISTRATOR,
            first_user_full_name="[Accountable Manager]",
            first_user_password=PASSWORD,
        )
        with working_for(ours.id, administrator.id):
            for username, name in (
                ("lucy.grant", "Lucy Grant"),
                ("planning", "[Planning and Records Name]"),
                ("review", "[Review Name]"),
                ("reader", "[Read Only Name]"),
            ):
                User.objects.create_user(
                    organisation=ours,
                    username=f"{username}@your-organisation.example",
                    full_name=name,
                )
            assert Person.objects.count() == 5
            assert set(Person.objects.values_list("role", flat=True)) == {""}
            lucy_before = Person.objects.get(full_name="Lucy Grant")
            history_before = Event.objects.filter(
                organisation=ours, record_type="accounts_user"
            ).count()

        assert prepare() == [
            "Service Role Made",
            "Sample Organisation Already Set Up",
            "People of the Sample Brought Up to Date, 10 Added",
            # From 27 November 2026 the start also adds the Phase 1 sample (REQ-294). This
            # organisation has no aircraft, so only what needs none is added.
            "Sources of Directives of the Sample Added, 4 Records",
            "Suppliers of the Sample Added, 5 Suppliers",
            "Goods In of the Sample Added, 5 Receipts",
            "Tools of the Sample Added, 5 Tools",
            "Calibration Orders of the Sample Added, 2 Orders",
            "Second Sample Organisation Set Up",
            f"Administrator {second.ADMINISTRATOR}",
        ]
        # The owner of the test database may be a superuser, whom row-level
        # security does not hold, so each question names the organisation.
        with working_for(ours.id, administrator.id):
            people = Person.objects.filter(organisation=ours)
            assert people.count() == 15
            assert people.filter(user__isnull=True).count() == 10
            lucy = people.get(full_name="Lucy Grant")
            assert lucy.pk == lucy_before.pk
            assert (lucy.role, lucy.staff_group) == (
                "Airworthiness Review Staff",
                "Airworthiness Review Staff",
            )
            assert lucy.reports_to is not None
            assert lucy.reports_to.full_name == "[Continuing Airworthiness Manager]"
            assert people.get(full_name="Chris Moore").licence == "Part-66 B1.2"
            # No sign-in was touched.
            assert (
                Event.objects.filter(organisation=ours, record_type="accounts_user").count()
                == history_before
            )
            assert User.objects.filter(organisation=ours).count() == 5
            assert chain.problems(list(Event.objects.all())) == []
        assert Organisation.objects.count() == 2
        # A first password of its own, never the first organisation's (finding 9
        # of the independent review of 24 November 2026).
        theirs = user_named(second.ADMINISTRATOR)
        assert theirs.check_password(SECOND_PASSWORD) and theirs.password_must_change
        assert not theirs.check_password(PASSWORD)
        assert not user_named(ADMINISTRATOR).check_password(SECOND_PASSWORD)

        entries = Event.objects.count()
        assert prepare() == [
            "Service Role Password Set Again",
            "Sample Organisation Already Set Up",
            "Second Sample Organisation Already Set Up",
        ]
        assert Event.objects.count() == entries
        assert Organisation.objects.count() == 2


def test_a_new_test_site_is_given_both_organisations(given: None) -> None:
    """REQ-218. An empty database, as after a remake (Issue 100)."""
    with as_owner():
        mark_the_database()
        assert prepare() == [
            "Service Role Made",
            "Sample Organisation Set Up",
            f"Administrator {ADMINISTRATOR}",
            "Second Sample Organisation Set Up",
            f"Administrator {second.ADMINISTRATOR}",
        ]
        assert Organisation.objects.count() == 2
        assert Person.objects.count() == 15 + 5
        assert Customer.objects.count() == 7 + 2
