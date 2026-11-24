"""What can be done with customer records. Views check the role first."""

from dataclasses import dataclass
from datetime import date

from airworthiness_plus.customers.models import Customer, Kind
from airworthiness_plus.organisations.models import Organisation


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


def _checked(name: str, kind: Kind | str, members: int | None) -> str:
    name = name.strip()
    if not name:
        raise RefusedError("A Customer Has a Name")
    if members is not None and kind != Kind.SYNDICATE:
        raise RefusedError("Only a Syndicate Has Members")
    if members is not None and members < 1:
        raise RefusedError("A Syndicate Has at Least 1 Member")
    return name


def add_customer(
    *,
    organisation: Organisation,
    name: str,
    kind: Kind | str = "",
    members: int | None = None,
    customer_since: date | None = None,
) -> Customer:
    """Add a customer (REQ-207)."""
    name = _checked(name, kind, members)
    return Customer.objects.create(
        organisation=organisation,
        name=name,
        kind=kind,
        members=members,
        customer_since=customer_since,
    )


def change_customer(
    customer: Customer,
    *,
    name: str,
    kind: Kind | str,
    members: int | None,
    customer_since: date | None,
) -> None:
    """Change what is recorded of a customer. Every change is in the history."""
    customer.name = _checked(name, kind, members)
    customer.kind = kind
    customer.members = members
    customer.customer_since = customer_since
    customer.save()


def named(organisation: Organisation, name: str) -> Customer:
    """Return the customer of this name, making one if there is none (REQ-208).

    Used where an owner is given by name: the Add an Aircraft page and an
    import. A name that two customers share does not say which is meant,
    and is refused.
    """
    name = name.strip()
    found = list(Customer.objects.filter(organisation=organisation, name=name)[:2])
    if len(found) > 1:
        raise RefusedError(f"More Than One Customer Is Named {name}")
    if found:
        return found[0]
    return add_customer(organisation=organisation, name=name)


@dataclass(frozen=True)
class CustomerLine:
    """One customer and the aircraft they own."""

    customer: Customer
    registrations: tuple[str, ...]


def customer_lines() -> list[CustomerLine]:
    """Return every customer of the organisation with their aircraft (REQ-210)."""
    return [
        CustomerLine(customer, tuple(aircraft.registration for aircraft in customer.aircraft.all()))
        for customer in Customer.objects.prefetch_related("aircraft")
    ]
