"""The illustrative Stores locations, named as the Goods In sample recorded them.

The sample adds the register entries only. RX-002 stays Awaiting Stock Posting so the
demonstration starts from the approved contract: a person resolves and posts it.
"""

from datetime import date

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import services, stores
from airworthiness_plus.logistics.models import LocationKind, StoreLocation
from airworthiness_plus.organisations.models import Organisation

# The primary sample's approval reference and day (sample.build), kept here to avoid a cycle.
APPROVAL_REFERENCE = "UK.CAO.[Number]"
DAY = date(2026, 11, 18)

LOCATIONS = (
    ("[Serviceable Stores Bay]", LocationKind.SERVICEABLE, "Dry, Controlled Temperature"),
    ("[Secure Quarantine Store]", LocationKind.QUARANTINE, "Locked, Access Restricted"),
)


def add(organisation: Organisation, actor: User) -> int:
    """Add the two sample locations once, to the primary sample organisation only."""
    if organisation.approval_reference != APPROVAL_REFERENCE:
        return 0
    with working_for(organisation.id, actor.id), transaction.atomic():
        organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
        if not services.maintenance_approvals(organisation, DAY):
            return 0
        count = 0
        for name, kind, conditions in LOCATIONS:
            if StoreLocation.objects.filter(organisation=organisation, name__iexact=name).exists():
                continue
            stores.add_location(
                organisation,
                name=name,
                kind=kind,
                holds_components=True,
                holds_standard_parts=kind == LocationKind.SERVICEABLE,
                holds_materials=kind == LocationKind.SERVICEABLE,
                secure=True,
                storage_conditions=conditions,
            )
            count += 1
        return count
