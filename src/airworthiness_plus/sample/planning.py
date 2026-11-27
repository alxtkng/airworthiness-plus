"""The draft annual work package of the Planning board (REQ-323)."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.planning import services
from airworthiness_plus.planning.models import WorkPackage
from airworthiness_plus.sample.models import Added, Part


@transaction.atomic
def add_work_packages(organisation: Organisation, actor: User, aircraft: Aircraft) -> int:
    """Add the draft once, leaving the organisation's existing records alone."""
    with working_for(organisation.id, actor.id):
        Organisation.objects.select_for_update().only("id").get(pk=organisation.pk)
        if Added.objects.filter(part=Part.WORK_PACKAGES).exists():
            return 0
        added = 0
        if not WorkPackage.objects.filter(reference="WP-2026-048").exists():
            package = services.build_package(
                aircraft,
                reference="WP-2026-048",
                title="Annual Check, Headset Socket",
                location="Bay 1",
                starts_on=date(2026, 12, 1),
                ends_on=date(2026, 12, 4),
            )
            data_set = data_services.record_data(
                organisation=organisation,
                title="[Cessna 152 Maintenance Instructions]",
                author="Cessna",
                kind=Kind.INSTRUCTIONS,
                applies_to=[aircraft.type_rating],
                held=False,
            )
            services.add_card(
                package,
                title="Annual Check and Right Headset Socket",
                data_set=data_set,
                instruction="[Annual Check and Electrical System Instructions]",
                planned_hours=Decimal("32.0"),
            )
            added = 1
        Added.objects.create(organisation=organisation, part=Part.WORK_PACKAGES)
        return added
