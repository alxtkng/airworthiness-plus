"""Run one Stores race in its own process, against a committed clone of the seeded sample.

``python -m tests.stores_race <scenario> <organisation> <user>`` prints a JSON
result. Each thread has its own Django connection, so each is an independent
PostgreSQL session under the application role and row-level security.
Used by ``tests/test_stores_postgres.py`` (REQ-358, handoff cases S02 and S09).
"""

import json
import sys
import threading
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import django

BUSINESS_DATE = date(2026, 11, 18)


def _race(count: int, work: Callable[[int], Any]) -> list[str]:
    from django.db import connection

    barrier = threading.Barrier(count)
    results: list[str] = [""] * count

    def run(index: int) -> None:
        try:
            barrier.wait(timeout=20)
            outcome = work(index)
            results[index] = f"ok:{outcome}"
        except Exception as error:  # the result is reported, not raised
            results[index] = f"refused:{type(error).__name__}:{error}"
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(index,)) for index in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    return results


def main(scenario: str, organisation: UUID, user_id: UUID) -> dict[str, Any]:
    from airworthiness_plus.accounts.models import User
    from airworthiness_plus.history.session import working_for
    from airworthiness_plus.logistics import stores
    from airworthiness_plus.logistics.models import (
        ReceivingDisposition,
        ShelfLifeBasis,
        StockCount,
        StockMovement,
        StockPosting,
        StockUnit,
        StoresLocation,
    )

    def as_user[Result](work: Callable[[User], Result]) -> Result:
        with working_for(organisation, user_id):
            return work(User.objects.get(pk=user_id))

    def decision(line: str) -> ReceivingDisposition:
        return ReceivingDisposition.objects.get(receipt__delivery_reference=line)

    def place(code: str) -> StoresLocation:
        return StoresLocation.objects.get(code=code)

    def lot(line: str) -> StockPosting:
        return StockPosting.objects.get(disposition__receipt__delivery_reference=line)

    def resolve(user: User) -> None:
        stores.record_posting_evidence(
            user,
            decision("RX-002"),
            request_id=uuid4(),
            assessed_on=BUSINESS_DATE,
            evidence="Synthetic race evidence",
            unit=StockUnit.EACH,
            quantity=Decimal(1),
            part_number="PN-RACE",
            serial="SN-RACE",
            shelf_life_basis=ShelfLifeBasis.NOT_APPLICABLE,
            location=place("BAY-A"),
        )

    result: dict[str, Any] = {}
    if scenario == "post":
        as_user(resolve)
        result["results"] = _race(
            4,
            lambda _: as_user(
                lambda user: str(stores.post(user, decision("RX-002"), request_id=uuid4()).pk)
            ),
        )
    elif scenario == "overspend":
        result["results"] = _race(
            2,
            lambda _: as_user(
                lambda user: str(
                    stores.move(
                        user,
                        lot("RX-006"),
                        request_id=uuid4(),
                        source=place("BAY-C"),
                        destination=place("OIL-2"),
                        quantity=Decimal(20),
                        moved_on=BUSINESS_DATE,
                        evidence="Synthetic competing move",
                    ).pk
                )
            ),
        )
    elif scenario == "adjust_or_move":

        def work(index: int) -> str:
            def act(user: User) -> str:
                bolts = lot("RX-007")
                if index == 0:
                    taken = StockCount.objects.get(posting=bolts)
                    return str(
                        stores.adjust(user, taken, request_id=uuid4(), evidence="Synthetic").pk
                    )
                return str(
                    stores.move(
                        user,
                        bolts,
                        request_id=uuid4(),
                        source=place("BAY-B"),
                        destination=place("BAY-A"),
                        quantity=Decimal(50),
                        moved_on=BUSINESS_DATE,
                        evidence="Synthetic move of the whole drawer",
                    ).pk
                )

            return as_user(act)

        result["results"] = _race(2, work)
    elif scenario == "issue":
        from airworthiness_plus.aircraft.models import Aircraft
        from airworthiness_plus.contracts.models import WorkOrder
        from airworthiness_plus.logistics import allocations
        from airworthiness_plus.logistics.models import (
            AllocationKind,
            StockAllocation,
            StoresAction,
        )
        from airworthiness_plus.maintenance_data import services as data
        from airworthiness_plus.maintenance_data.models import Kind
        from airworthiness_plus.people.models import Person
        from airworthiness_plus.planning import services as planning

        def appoint(user: User) -> None:
            administrator = User.objects.get(
                username="accountable.manager@your-organisation.example"
            )
            with working_for(organisation, administrator.pk):
                for action in (StoresAction.RESERVE, StoresAction.ISSUE):
                    stores.record_appointment(
                        administrator,
                        request_id=uuid4(),
                        approval="Part-CAO",
                        person=Person.objects.get(user_id=user.pk),
                        action=action,
                        starts_on=BUSINESS_DATE,
                        ends_on=BUSINESS_DATE + timedelta(days=30),
                        exposition_reference="Synthetic Stores authority",
                        authority="Synthetic scope",
                    )

        def prepare(user: User) -> UUID:
            aircraft = Aircraft.objects.get(registration="G-ABCD")
            package = planning.build_package(
                aircraft,
                reference="WP-STORES-RACE",
                title="Reserve one traced part",
                location="Bay A",
                starts_on=BUSINESS_DATE,
                ends_on=BUSINESS_DATE,
            )
            manual = data.record_data(
                organisation=user.organisation,
                title="Synthetic Stores Manual",
                author="Maker",
                kind=Kind.INSTRUCTIONS,
                applies_to=[aircraft.type_rating],
                revision="1",
                revision_date=BUSINESS_DATE,
                check_due=BUSINESS_DATE + timedelta(days=7),
            )
            card = planning.add_card(
                package,
                title="Install Part",
                data_set=manual,
                instruction="Figure 33",
                planned_hours=Decimal(1),
            )
            planning.link_order(
                package, WorkOrder.objects.get(aircraft=aircraft, work="Landing Light Replacement")
            )
            planning.issue_package(package)
            posted = stores.post(user, decision("RX-002"), request_id=uuid4())
            event = allocations.record(
                user,
                posted,
                AllocationKind.RESERVE,
                request_id=uuid4(),
                source=place("BAY-A"),
                card=card,
                quantity=Decimal(1),
                required_identity="PN-RACE",
                applicable_source="Synthetic Stores Manual Revision 1 Figure 33",
                evidence="Reserve for the open job",
            )
            return event.pk

        def issue(user: User) -> str:
            event = StockAllocation.objects.get(pk=reservation_id)
            return str(
                allocations.record(
                    user,
                    event.posting,
                    AllocationKind.ISSUE,
                    preceding=event,
                    request_id=uuid4(),
                    evidence="Transferred to the workshop",
                ).pk
            )

        as_user(appoint)
        as_user(resolve)
        reservation_id = as_user(prepare)
        result["results"] = _race(2, lambda _: as_user(issue))
        result["issues"] = as_user(
            lambda _: StockAllocation.objects.filter(kind=AllocationKind.ISSUE).count()
        )
    else:
        raise SystemExit(f"Unknown scenario {scenario}")

    def ledger(user: User) -> dict[str, Any]:
        lines = stores.positions(user.organisation, BUSINESS_DATE)
        return {
            "postings": {
                str(one.disposition.receipt.delivery_reference): one.movements.count()
                for one in StockPosting.objects.select_related("disposition__receipt")
            },
            "positions": sorted(
                [
                    one.posting.disposition.receipt.delivery_reference,
                    one.location.code,
                    f"{one.on_hand.normalize():f}",
                ]
                for one in lines
            ),
            "movements": StockMovement.objects.count(),
        }

    result["ledger"] = as_user(ledger)
    return result


if __name__ == "__main__":
    django.setup()
    with patch("airworthiness_plus.aircraft.services.today", return_value=BUSINESS_DATE):
        print(json.dumps(main(sys.argv[1], UUID(sys.argv[2]), UUID(sys.argv[3]))))
