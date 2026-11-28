"""Aggregate the published lot/location ledger without mixing stock units."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from airworthiness_plus.logistics.models import (
    ItemClass,
    StockPosting,
    StockResolution,
    StoreLocation,
)
from airworthiness_plus.logistics.stores import Position


def matches(record: StockPosting | StockResolution, classification: str, identity: str) -> bool:
    """Compare the canonical identity for the received class, ignoring case."""
    if classification in (ItemClass.STANDARD, ItemClass.MATERIAL):
        recorded = record.specification
    else:
        recorded = record.part_number
    return recorded.casefold() == identity.casefold()


@dataclass
class Total:
    name: str
    unit: str
    on_hand: Decimal = Decimal(0)
    reserved: Decimal = Decimal(0)
    available: Decimal = Decimal(0)

    def add(self, position: Position) -> None:
        self.on_hand += position.on_hand
        self.reserved += position.reserved
        self.available += position.available


@dataclass(frozen=True)
class Summary:
    network: list[Total]
    stations: list[Total]
    locations: list[Total]


def summarise(positions: list[Position], configured: Iterable[StoreLocation]) -> Summary:
    """Include empty active stores and preserve custody at locations since withdrawn."""
    units = sorted({position.lot.unit for position in positions}) or [""]
    locations: dict[str, dict[str, Total]] = defaultdict(dict)
    stations: dict[str, dict[str, Total]] = defaultdict(dict)
    network = {unit: Total("Network", unit) for unit in units}

    for place in configured:
        if place.station:
            for unit in units:
                locations[place.name][unit] = Total(place.name, unit)
                stations[place.station][unit] = Total(place.station, unit)

    for position in positions:
        unit = position.lot.unit
        name = position.location.name
        station = position.location.station or "Unassigned"
        locations[name].setdefault(unit, Total(name, unit)).add(position)
        stations[station].setdefault(unit, Total(station, unit)).add(position)
        network[unit].add(position)

    return Summary(
        list(network.values()),
        [total for name in sorted(stations) for _, total in sorted(stations[name].items())],
        [total for name in sorted(locations) for _, total in sorted(locations[name].items())],
    )
