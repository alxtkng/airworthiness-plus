"""What can be done to aircraft records. Views check the role first, then call these."""

import json
import uuid
from datetime import date

from django.db import transaction

from airworthiness_plus.aircraft.models import (
    Aircraft,
    Counter,
    CounterKind,
    Regime,
    Stage,
    Status,
    UtilisationEntry,
)
from airworthiness_plus.customers import services as customer_services
from airworthiness_plus.customers.models import Customer
from airworthiness_plus.history.models import Event
from airworthiness_plus.organisations.models import Organisation
from airworthiness_rules.dates import uk_today, utc_now
from airworthiness_rules.intervals import Reading
from airworthiness_rules.utilisation import Verdict, check_entry, current_total


class ConfirmationNeededError(Exception):
    """The gain in hours or cycles is unusual and has not been confirmed (REQ-025)."""


class NotServiceableError(ValueError):
    """Something recorded stops the aircraft being made Serviceable (REQ-221)."""


class TransferNotCompleteError(Exception):
    """Records are still outstanding, so the aircraft stays out of the Fleet (REQ-027)."""


def today() -> date:
    """Return today's date in the United Kingdom (REQ-137)."""
    return uk_today(utc_now())


@transaction.atomic
def add_aircraft(
    *,
    organisation: Organisation,
    registration: str,
    type_rating: str,
    owner: str = "",
    customer: Customer | None = None,
    regime: Regime = Regime.PART_21,
    serial_number: str = "",
    manufacturer: str = "",
    designation: str = "",
    airframe: Reading | None = None,
    records_expected: int | None = None,
    records_received: int = 0,
) -> Aircraft:
    """Add an aircraft with its airframe counter.

    With ``records_expected`` the aircraft is a Transfer In and stays out
    of the Fleet until every record is received (REQ-027). ``airframe`` is
    the first entry of airframe hours and cycles, if it is known.

    The owner is a customer (REQ-208): either ``customer``, or the customer
    named ``owner``, who is made if nobody of that name is recorded.
    """
    if (customer is None) == (not owner.strip()):
        raise customer_services.RefusedError("Choose a Customer or Name a New One")
    if customer is None:
        customer = customer_services.named(organisation, owner)
    transfer = records_expected is not None
    aircraft = Aircraft.objects.create(
        organisation=organisation,
        registration=registration,
        type_rating=type_rating,
        serial_number=serial_number,
        manufacturer=manufacturer,
        designation=designation,
        customer=customer,
        regime=regime,
        stage=Stage.TRANSFER_IN if transfer else Stage.FLEET,
        records_expected=records_expected,
        records_received=records_received if transfer else None,
    )
    counter = add_counter(aircraft, CounterKind.AIRFRAME)
    if airframe is not None:
        enter_utilisation(counter, airframe)
    return aircraft


def add_counter(
    aircraft: Aircraft, kind: CounterKind, position: str = "", serial_number: str = ""
) -> Counter:
    """Add the airframe, an engine or a propeller as a counter (REQ-020, REQ-059)."""
    return Counter.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        kind=kind,
        position=position,
        serial_number=serial_number,
    )


def current_entries(counter: Counter) -> list[UtilisationEntry]:
    """Return the entries of ``counter`` that have not been superseded, oldest first."""
    return list(counter.entries.filter(superseded_by__isnull=True))


def current_reading(counter: Counter) -> Reading | None:
    """Return the current total of ``counter``: its latest entry (REQ-024)."""
    return current_total(entry.reading for entry in current_entries(counter))


@transaction.atomic
def enter_utilisation(
    counter: Counter,
    reading: Reading,
    *,
    confirmed: bool = False,
    supersedes: UtilisationEntry | None = None,
) -> UtilisationEntry:
    """Add an entry of hours and cycles (REQ-024, REQ-025).

    The entry is checked against the entries around it by
    ``airworthiness_rules.utilisation.check_entry``, and again by the
    database. An unusual gain is refused until it comes back confirmed. To
    correct an entry, pass it as ``supersedes``: it stays in the record and
    the new entry takes its place.
    """
    others = [entry.reading for entry in current_entries(counter) if entry != supersedes]
    verdict = check_entry(reading, others=others, today=today())
    if verdict is Verdict.NEEDS_CONFIRMATION and not confirmed:
        raise ConfirmationNeededError
    return UtilisationEntry.objects.create(
        organisation_id=counter.organisation_id,
        counter=counter,
        dated=reading.on,
        hours=reading.hours,
        cycles=reading.cycles,
        supersedes=supersedes,
        confirmed_unusual=verdict is Verdict.NEEDS_CONFIRMATION,
    )


def record_details(
    aircraft: Aircraft, *, serial_number: str, manufacturer: str, designation: str
) -> None:
    """Record what CAA Form 15c says of the aircraft besides its registration."""
    aircraft.serial_number = serial_number.strip()
    aircraft.manufacturer = manufacturer.strip()
    aircraft.designation = designation.strip()
    aircraft.save(update_fields=["serial_number", "manufacturer", "designation"])


def change_owner(aircraft: Aircraft, customer: Customer) -> None:
    """Record another customer as the owner. The history keeps who it was (REQ-208)."""
    aircraft.customer = customer
    aircraft.save(update_fields=["customer"])


def every_owner(aircraft: Aircraft) -> set[uuid.UUID]:
    """Return every customer that has ever owned the aircraft, as its history shows.

    The history holds the record after each change (REQ-130), and so every
    customer the aircraft has been given. The owner today is among them.
    """
    owners = {aircraft.customer_id}
    for after in Event.of(aircraft).values_list("after_json", flat=True):
        customer = json.loads(after or "{}").get("customer_id")
        if customer:
            owners.add(uuid.UUID(customer))
    return owners


def make_unserviceable(aircraft: Aircraft, reason: str, since: date) -> None:
    """Record the aircraft as Unserviceable, with the reason and the date (REQ-023)."""
    aircraft.status = Status.UNSERVICEABLE
    aircraft.unserviceable_reason = reason
    aircraft.unserviceable_since = since
    aircraft.save(update_fields=["status", "unserviceable_reason", "unserviceable_since"])


def make_serviceable(aircraft: Aircraft) -> None:
    """Record the aircraft as Serviceable (REQ-023). The history keeps the earlier status.

    Refused while a defect that is Not Deferrable is open: such a defect is
    rectified before further flight (ML.A.403(a); REQ-221). The database
    refuses it too.
    """
    # Defects are built on aircraft, so they are looked up here and not at the top.
    from airworthiness_plus.defects.models import Decision, Defect

    stops = Defect.objects.filter(
        aircraft=aircraft, decision=Decision.NOT_DEFERRABLE, closed_on__isnull=True
    ).first()
    if stops is not None:
        raise NotServiceableError(f"Open Defect That Is Not Deferrable, ML.A.403(a): {stops.title}")
    aircraft.status = Status.SERVICEABLE
    aircraft.unserviceable_reason = ""
    aircraft.unserviceable_since = None
    aircraft.save(update_fields=["status", "unserviceable_reason", "unserviceable_since"])


def record_received(aircraft: Aircraft, received: int) -> None:
    """Update how many of the expected records have arrived for a Transfer In (REQ-027)."""
    aircraft.records_received = received
    aircraft.save(update_fields=["records_received"])


@transaction.atomic
def complete_transfer(aircraft: Aircraft) -> None:
    """Move a Transfer In to the Fleet, once every record is received (REQ-027)."""
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    if aircraft.stage != Stage.TRANSFER_IN:
        raise TransferNotCompleteError("Only an Aircraft Being Transferred In Can Be Moved")
    if aircraft.records_received != aircraft.records_expected:
        raise TransferNotCompleteError(
            f"Records Received, {aircraft.records_received} of {aircraft.records_expected}"
        )
    # The checklist is built on aircraft, so it is looked up here and not at the top.
    from airworthiness_plus.configuration import services as configuration_services

    outstanding = configuration_services.stops_the_fleet(aircraft)
    if outstanding:
        raise TransferNotCompleteError("Items Still Open: " + "; ".join(outstanding))
    aircraft.stage = Stage.FLEET
    aircraft.records_received = None
    aircraft.records_expected = None
    aircraft.save(update_fields=["stage", "records_received", "records_expected"])
