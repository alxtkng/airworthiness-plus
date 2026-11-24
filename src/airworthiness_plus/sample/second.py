"""The second sample organisation: a Part-CAMO that is also a Part-145 (REQ-218).

Decisions.md, Canvas Build, decision 1: a second sample organisation holds
Part-CAMO and Part-145, so that what is shown only to those approvals can
be shown. Everything here is from design-system/SampleData.md, Second
Organisation, with placeholders in square brackets for anything that would
otherwise look real. The records are made through the same services as
the pages.

It starts small: its people, two customers and two aircraft. Each phase of
the canvas build adds what its boards need.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.customers import services as customer_services
from airworthiness_plus.customers.models import Kind
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_rules.intervals import Reading

TODAY = date(2026, 11, 18)

NAME = "[Second Organisation]"
ADDRESS = "[Second Organisation Address]"
APPROVAL_REFERENCE = "UK.CAMO.[Number]"
MAINTENANCE_REFERENCE = "UK.145.[Number]"
SCOPE = "Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less"
ADMINISTRATOR = "accountable.manager@second-organisation.example"

ACCOUNTABLE = "[Second Accountable Manager]"
MANAGER = "[Second Continuing Airworthiness Manager]"
MAINTENANCE = "[Second Maintenance Manager]"

# Aircraft Registration, Type Rating, the customer, Airframe Hours.
FLEET = (
    ("G-JNOP", "Piper PA-28 Series (Lycoming)", "[Operator Name]", "2406.5"),
    ("G-KQRS", "Cessna/Reims-Cessna 172/F172 Series (Lycoming)", "[Second Owner Name]", "5120.0"),
)
CUSTOMERS = {
    "[Operator Name]": Kind.OPERATOR,
    "[Second Owner Name]": Kind.PILOT_OWNER,
}


def build(organisation: Organisation, administrator: User) -> None:
    """Add everything of the second sample to an organisation that has only its Administrator."""

    def add(username: str, full_name: str, role: Role) -> User:
        return User.objects.create_user(
            organisation=organisation,
            username=f"{username}@second-organisation.example",
            full_name=full_name,
            roles=[role],
        )

    def record(user: User, role: str, group: StaffGroup, reports_to: Person | None) -> Person:
        person = Person.objects.get(user=user)
        people_services.change_person(
            person,
            full_name=person.full_name,
            role=role,
            staff_group=group,
            reports_to=reports_to,
            employment=Employment.EMPLOYED,
            licence="",
            joined_on=None,
            left_on=None,
        )
        return person

    with working_for(organisation.id, administrator.id):
        manager = add("manager", MANAGER, Role.CONTINUING_AIRWORTHINESS_MANAGER)
        reader = add("reader", "[Second Read Only Name]", Role.READ_ONLY)
        accountable = record(administrator, "Accountable Manager", StaffGroup.MANAGEMENT, None)
        record(manager, "Continuing Airworthiness Manager", StaffGroup.MANAGEMENT, accountable)
        record(reader, "", StaffGroup.OTHER, None)
        maintenance = people_services.add_person(
            organisation=organisation,
            full_name=MAINTENANCE,
            role="Maintenance Manager",
            staff_group=StaffGroup.MANAGEMENT,
            reports_to=accountable,
        )
        people_services.add_person(
            organisation=organisation,
            full_name="[Second Certifying Staff Name]",
            role="Certifying Staff",
            staff_group=StaffGroup.CERTIFYING,
            reports_to=maintenance,
            licence="Part-66 B1.2",
        )
    with working_for(organisation.id, manager.id):
        customers = {
            name: customer_services.add_customer(organisation=organisation, name=name, kind=kind)
            for name, kind in CUSTOMERS.items()
        }
        for registration, type_rating, customer, hours in FLEET:
            aircraft_services.add_aircraft(
                organisation=organisation,
                registration=registration,
                type_rating=type_rating,
                customer=customers[customer],
                airframe=Reading(TODAY, Decimal(hours), 0),
            )


def seed(password: str) -> Organisation:
    """Set up the second sample organisation, with ``password`` for its Administrator.

    A first password, as every other is: changed at the first sign-in and
    good for 7 days.
    """
    try:
        with transaction.atomic():
            organisation, administrator = provision_organisation(
                name=NAME,
                approval_type=ApprovalType.PART_CAMO,
                approval_reference=APPROVAL_REFERENCE,
                other_approvals=[(ApprovalType.PART_145, MAINTENANCE_REFERENCE)],
                address=ADDRESS,
                privileges=[],
                scope_of_work=SCOPE,
                first_user_username=ADMINISTRATOR,
                first_user_full_name=ACCOUNTABLE,
                first_user_password=password,
            )
            build(organisation, administrator)
    except ValidationError as error:
        raise CommandError("; ".join(error.messages)) from error
    return organisation
