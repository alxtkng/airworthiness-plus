"""Synthetic lookup exercise independent of the operational stock register."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Holding:
    station: str
    store: str
    quantity: int
    reserved: int = 0
    condition: str = "Serviceable"
    reason: str = ""

    @property
    def available(self) -> int:
        return self.quantity - self.reserved if self.condition == "Serviceable" else 0


@dataclass(frozen=True)
class Balance:
    on_hand: int
    reserved: int
    available: int


def balance(holdings: tuple[Holding, ...]) -> Balance:
    return Balance(
        on_hand=sum(row.quantity for row in holdings),
        reserved=sum(row.reserved for row in holdings),
        available=sum(row.available for row in holdings),
    )


OPENING = (
    Holding("ZRH", "Main", 7),
    Holding("ZRH", "Line", 1),
    Holding("BSL", "Main", 1),
    Holding("LUG", "Main", 1),
    Holding("GVA", "Main", 0),
)
AFTER_HOLDS = (
    Holding("ZRH", "Main", 6, reserved=1),
    Holding("ZRH", "Quarantine", 1, condition="Quarantined", reason="Identity check unresolved"),
    *OPENING[1:],
)
HOLDS_STEP = 3
QUESTIONS = (
    ("store", "How many items are on hand at ZRH Main?", 7),
    ("station", "How many items are on hand across ZRH?", 8),
    ("network", "How many items are on hand across the network?", 10),
    ("available", "How many items remain available across the network?", 8),
)
