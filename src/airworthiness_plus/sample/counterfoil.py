"""Install the Counterfoil review snapshot on the marked test site only."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from airworthiness_plus.accounts.models import User
from airworthiness_plus.contracts.models import OrderedBy, WorkOrder
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.services import add_person
from airworthiness_plus.planning import services
from airworthiness_plus.planning.models import WorkPackage
from airworthiness_plus.sample import build, top_up

REFERENCE = "WP-2026-046"
TITLE = "Stabilator Trim Cable Rectification"
START = date(2026, 11, 16)
ORDER_DATE = date(2026, 11, 14)
CARDS = (
    ("Gain Access, Cabin Floor and Tail Cone Panels", "2.0", False, 16, "0.0"),
    ("Remove Frayed Stabilator Trim Cable", "1.5", False, 17, "0.0"),
    ("Inspect Pulleys, Fairleads and Trim Drum", "1.5", False, 17, "0.0"),
    ("Replace Aft Trim Cable Pulley", "2.0", True, 18, "0.0"),
    ("Install New Stabilator Trim Cable", "4.0", True, 18, "0.0"),
    ("Rig Cable Tension, Stops and Travel", "3.0", True, None, "1.0"),
    ("Refit Panels, General Verification and Functional Check", "2.0", False, None, "0.0"),
)


def add_review_package(administrator: User) -> UUID | None:
    """Add the documented snapshot once without rewriting existing sample records."""
    with working_for(administrator.organisation_id, administrator.id):
        organisation = Organisation.objects.select_for_update().get(
            pk=administrator.organisation_id
        )
        if organisation.approval_reference != build.APPROVAL_REFERENCE:
            return None
        if WorkPackage.objects.filter(reference=REFERENCE).exists():
            return None

        aircraft = top_up.aircraft_of_the_sample().get("G-DGHI")
        if aircraft is None:
            return None
        order = WorkOrder.objects.get(
            aircraft=aircraft, work=TITLE, ordered_by=OrderedBy.MANAGER, agreed_on=ORDER_DATE
        )
        if WorkPackage.objects.filter(order=order).exists():
            return None
        defect = aircraft.defects.get(
            title__in=("Stabilator Trim Cable", "Stabilator Trim Cable Frayed at Pulley"),
            found_on=ORDER_DATE,
            closed_on__isnull=True,
        )
        performer = add_person(
            organisation=organisation,
            full_name="[Counterfoil Sample Engineer]",
            role="Sample Maintenance Performer",
        )
        data_set = data_services.record_data(
            organisation=organisation,
            title="[Counterfoil Sample PA-28 Maintenance Instructions]",
            author="Sample",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="[Sample Revision]",
            revision_date=ORDER_DATE,
            check_due=date(2026, 11, 30),
        )
        # This runs during test-site preparation, before the web workers start.
        # Use the canvas snapshot's dates and the same services as the forms.
        with patch("airworthiness_plus.aircraft.services.today", return_value=START):
            package = services.build_package(
                aircraft,
                reference=REFERENCE,
                title=TITLE,
                location="Bay 1",
                starts_on=START,
                ends_on=date(2026, 11, 19),
                defect=defect,
            )
            services.link_order(package, order)
            cards = [
                (
                    services.add_card(
                        package,
                        title=title,
                        data_set=data_set,
                        instruction="Chapter 27 (Synthetic Sample)",
                        planned_hours=Decimal(hours),
                        critical=critical,
                        inspection_hours=Decimal(inspection),
                    ),
                    day,
                )
                for title, hours, critical, day, inspection in CARDS
            ]
            services.issue_package(package)
        with patch("airworthiness_plus.aircraft.services.today", return_value=date(2026, 11, 18)):
            for number, (card, day) in enumerate(cards, start=1):
                if day is not None:
                    services.record_completion(
                        card,
                        performed_by=performer,
                        completed_on=date(2026, 11, day),
                        sign_off_reference=f"Synthetic Counterfoil Work Card {number}",
                        hours=Decimal("9874.3"),
                        cycles=0,
                    )
        return package.pk
