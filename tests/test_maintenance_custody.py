"""The AMOS work-card custody flow on the published Stores records."""

from datetime import timedelta
from decimal import Decimal
from typing import TypedDict
from uuid import uuid4

import pytest
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.contracts import services as contracts
from airworthiness_plus.contracts.models import OrderedBy, Outcome
from airworthiness_plus.exports.build import build
from airworthiness_plus.exports.verify import verify
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics import allocations, stock_appointments, stores, substitutions
from airworthiness_plus.logistics.models import (
    AllocationKind,
    LocationKind,
    ShelfLifeBasis,
    ShelfLifeRule,
    StockAllocation,
    StockDuty,
    StockPosting,
    StockSubstitution,
    StoreLocation,
)
from airworthiness_plus.logistics.services import RefusedError, maintenance_approvals
from airworthiness_plus.maintenance_data import services as data
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.people import services as staff
from airworthiness_plus.people.models import Person, StaffGroup
from airworthiness_plus.planning import services as planning
from airworthiness_plus.planning.models import WorkCard
from tests.conftest import as_owner
from tests.support import Sample, add_sample_fleet
from tests.test_exports import opened
from tests.test_stores import TODAY, dispose, location, posted, receipt, resolve

pytestmark = pytest.mark.django_db


class WorkIdentity(TypedDict):
    card: WorkCard
    required_identity: str
    applicable_source: str


class ReservationIdentity(WorkIdentity):
    source: StoreLocation


def grant_actions(sample: Sample) -> None:
    with working_for(sample.ours.pk, sample.lucy.pk):
        approval = maintenance_approvals(sample.ours, TODAY)[0]
        person = Person.objects.get(user=sample.lucy)
        for action in StockDuty:
            stock_appointments.appoint(
                sample.lucy,
                request_id=uuid4(),
                person=person,
                approval=approval,
                action=action,
                starts_on=TODAY,
                ends_on=TODAY + timedelta(days=30),
                evidence="Synthetic signed exposition appointment",
            )


def card_for(sample: Sample) -> WorkCard:
    aircraft = add_sample_fleet(sample)["G-ABCD"]
    with working_for(sample.ours.pk, sample.lucy.pk):
        package = planning.build_package(
            aircraft,
            reference="WP-STOCK-TRIAL",
            title="Workshop installation",
            location="ZRH Main",
            starts_on=TODAY,
            ends_on=TODAY + timedelta(days=1),
        )
        dataset = data.record_data(
            organisation=sample.ours,
            title="Synthetic parts data",
            author="Synthetic supplier",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="1",
            revision_date=TODAY,
            check_due=TODAY + timedelta(days=7),
        )
        card = planning.add_card(
            package,
            title="Install the hardware",
            data_set=dataset,
            instruction="Figure 33",
            planned_hours=Decimal(1),
        )
        order = contracts.add_work_order(
            aircraft,
            work=package.title,
            ordered_by=OrderedBy.MANAGER,
            agreed_on=TODAY,
        )
        planning.link_order(package, order)
        return card


def test_exact_issue_custody_replay_reservations_and_expiry(
    sample: Sample, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    card = card_for(sample)
    with working_for(sample.ours.pk, sample.lucy.pk):
        user = sample.lucy
        person = Person.objects.get(user=user)
        source = location(sample.ours, "Main")
        other_place = location(sample.ours, "Line")
        hold = location(sample.ours, "Secure hold", LocationKind.QUARANTINE)
        posting = posted(dispose(receipt(sample.ours, "CUSTODY", quantity=10)), person, source)
        fields: ReservationIdentity = {
            "source": source,
            "card": card,
            "required_identity": "PN-713",
            "applicable_source": "Synthetic IPC revision 1 Figure 33",
        }
        with pytest.raises(RefusedError, match="Current Stores Appointment"):
            allocations.record(
                user,
                posting,
                AllocationKind.RESERVE,
                request_id=uuid4(),
                evidence="Trial",
                quantity=Decimal(3),
                **fields,
            )
        grant_actions(sample)
        with pytest.raises(RefusedError, match="Issued Package"):
            allocations.record(
                user,
                posting,
                AllocationKind.RESERVE,
                request_id=uuid4(),
                evidence="Trial",
                quantity=Decimal(3),
                **fields,
            )
        planning.issue_package(card.package)
        token = uuid4()

        def reserve() -> StockAllocation:
            return allocations.record(
                user,
                posting,
                AllocationKind.RESERVE,
                request_id=token,
                evidence="Book for installation",
                quantity=Decimal(3),
                **fields,
            )

        first = reserve()
        assert reserve() == first
        (position,) = stores.positions([posting], TODAY, 30)
        assert (position.on_hand, position.reserved, position.available) == tuple(
            map(Decimal, (10, 3, 7))
        )
        with pytest.raises(RefusedError, match="Unreserved"):
            stores.move(
                posting,
                from_location=source,
                to_location=other_place,
                quantity=Decimal(8),
                moved_on=TODAY,
                actor=person,
                authority="Published movement scope",
                evidence="Would spend reserved stock",
            )
        issue = allocations.record(
            user,
            posting,
            AllocationKind.ISSUE,
            request_id=uuid4(),
            evidence="Issue to workshop",
            preceding=first,
        )
        assert stores.balance(posting, source) == Decimal(7)
        with pytest.raises(RefusedError, match="Already Been Continued"):
            allocations.record(
                user,
                posting,
                AllocationKind.ISSUE,
                request_id=uuid4(),
                evidence="Duplicate",
                preceding=first,
            )
        returned = allocations.record(
            user,
            posting,
            AllocationKind.RETURN,
            request_id=uuid4(),
            evidence="Returned opened",
            preceding=issue,
            destination=hold,
        )
        assert stores.balance(posting, hold) == Decimal(3)
        assert sum(row.available for row in stores.positions([posting], TODAY, 30)) == Decimal(7)
        with pytest.raises(RefusedError, match="New Receiving Decision"):
            stores.move(
                posting,
                from_location=hold,
                to_location=source,
                quantity=Decimal(3),
                moved_on=TODAY,
                actor=person,
                authority="Old movement role",
                evidence="Would clear quarantine",
            )
        appointment = stock_appointments.current(user, StockDuty.QUARANTINE, TODAY)
        assert appointment is not None
        stock_appointments.withdraw(user, appointment, "Synthetic appointment withdrawal")
        assert stock_appointments.current(user, StockDuty.QUARANTINE, TODAY) is None
        archive = build(sample.ours, by=user)
        assert verify(archive.content).problems == ()
        files = opened(archive.content)
        assert any(
            row["id"] == str(returned.pk) for row in files["records/logistics_stockallocation.json"]
        )
        assert any(
            row["id"] == str(appointment.pk)
            for row in files["records/logistics_stockappointment.json"]
        )
        assert any(
            row["appointment_id"] == str(appointment.pk)
            for row in files["records/logistics_stockappointmentwithdrawal.json"]
        )
        short = posted(
            dispose(receipt(sample.ours, "EXPIRY", shelf_life_to=TODAY)),
            person,
            source,
            shelf_life_basis=ShelfLifeBasis.DATED,
            shelf_life_to=TODAY,
            shelf_life_rule=ShelfLifeRule.THROUGH,
        )
        short_hold = allocations.record(
            user,
            short,
            AllocationKind.RESERVE,
            request_id=uuid4(),
            evidence="Within shelf life",
            quantity=Decimal(1),
            **fields,
        )
        monkeypatch.setattr(aircraft_services, "today", lambda: TODAY + timedelta(days=1))
        with pytest.raises(RefusedError, match="Shelf Life"):
            allocations.record(
                user,
                short,
                AllocationKind.ISSUE,
                request_id=uuid4(),
                evidence="Too late",
                preceding=short_hold,
            )
    with working_for(sample.other.pk, sample.stranger.pk):
        assert not StockAllocation.objects.exists()


def test_alternate_approval_scope_expiry_and_issued_revision(
    sample: Sample, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    card = card_for(sample)
    grant_actions(sample)
    with working_for(sample.ours.pk, sample.administrator.pk):
        person = Person.objects.get(user=sample.lucy)
        person.staff_group = StaffGroup.CERTIFYING
        person.save(update_fields=["staff_group"])
        grant = staff.record_maintenance_authorisation(
            person,
            reference="SYN-ALT",
            scope="Part substitution approval for G-ABCD",
            valid_from=TODAY,
            valid_to=TODAY,
        )
        wrong = staff.record_maintenance_authorisation(
            person,
            reference="SYN-WRONG",
            scope="Part substitution approval for G-EJKL",
            valid_from=TODAY,
        )
    with working_for(sample.ours.pk, sample.lucy.pk):
        user = sample.lucy
        source = location(sample.ours, "Main")
        lot = posted(dispose(receipt(sample.ours, "ALTERNATE", quantity=3)), person, source)
        option = WorkIdentity(
            card=card, required_identity="PN-OLD", applicable_source="Synthetic IPC revision 4"
        )

        def approve() -> StockSubstitution:
            return substitutions.approve(
                user,
                lot,
                request_id=uuid4(),
                authorisation=grant,
                evidence="OEM list applies to this job",
                scope_confirmed=True,
                **option,
            )

        with pytest.raises(RefusedError, match="Issued Package"):
            approve()
        planning.issue_package(card.package)
        with pytest.raises(RefusedError, match="Names This Aircraft"):
            substitutions.approve(
                user,
                lot,
                request_id=uuid4(),
                authorisation=wrong,
                evidence="Wrong scope",
                scope_confirmed=True,
                **option,
            )
        approval = approve()
        assert substitutions.available(lot, TODAY).get() == approval

        def reserve() -> StockAllocation:
            return allocations.record(
                user,
                lot,
                AllocationKind.RESERVE,
                request_id=uuid4(),
                evidence="Book alternate",
                substitution=approval,
                source=source,
                quantity=Decimal(1),
                **option,
            )

        booked = reserve()
        monkeypatch.setattr(aircraft_services, "today", lambda: TODAY + timedelta(days=1))
        with pytest.raises(RefusedError, match="Authorisation Has Expired"):
            allocations.record(
                user,
                lot,
                AllocationKind.ISSUE,
                request_id=uuid4(),
                evidence="Expired",
                preceding=booked,
            )
        monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
        allocated = allocations.record(
            user,
            lot,
            AllocationKind.ISSUE,
            request_id=uuid4(),
            evidence="Eligible alternate",
            preceding=booked,
        )
        assert allocated.substitution_id == approval.pk
        archive = build(sample.ours, by=user)
        assert verify(archive.content).problems == ()
        (archived,) = opened(archive.content)["records/logistics_stocksubstitution.json"]
        assert (archived["id"], archived["authorisation_id"], archived["revision_id"]) == (
            str(approval.pk),
            str(grant.pk),
            str(approval.revision_id),
        )
        remaining = reserve()
        data.add_revision(card.data_set, revision="2", revision_date=TODAY)
        with pytest.raises(RefusedError, match="Stale Work Card"):
            allocations.record(
                user,
                lot,
                AllocationKind.ISSUE,
                request_id=uuid4(),
                evidence="Stale",
                preceding=remaining,
            )
        card.package.refresh_from_db(fields=["order"])
        order = card.package.order
        assert order is not None
        contracts.close_work_order(order, closed_on=TODAY, outcome=Outcome.WITHDRAWN)
        with pytest.raises(RefusedError, match="Issued Package"):
            allocations.record(
                user,
                lot,
                AllocationKind.ISSUE,
                request_id=uuid4(),
                evidence="Withdrawn",
                preceding=remaining,
            )
    with working_for(sample.ours.pk, sample.planner.pk):
        with pytest.raises(DatabaseError), transaction.atomic():
            StockSubstitution.objects.create(
                organisation=sample.ours,
                posting_id=lot.pk,
                card_id=card.pk,
                revision_id=approval.revision_id,
                authorisation_id=grant.pk,
                recorded_on=TODAY,
                submission=uuid4(),
                required_identity="PN-OLD",
                substitute_identity="PN-713",
                applicable_source="Synthetic IPC revision 4",
                evidence="Direct insert by another person",
                scope_confirmed=True,
            )


def test_populated_published_schema_preserves_lot_keys_and_history(
    sample: Sample, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    previous = [("logistics", "0008_stores_ledger_rules")]
    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old = executor.migrate(previous).apps
    with working_for(sample.ours.pk, sample.lucy.pk):
        person = Person.objects.get(user=sample.lucy)
        old_location = old.get_model("logistics", "StoreLocation").objects.create(
            organisation_id=sample.ours.pk,
            name="Published bay",
            kind=LocationKind.SERVICEABLE,
            holds_components=True,
        )
        place = StoreLocation.objects.defer("station").get(pk=old_location.pk)
        decision = dispose(receipt(sample.ours, "PUBLISHED-LOT", quantity=7))
        resolve(decision, person, place)
        reading = old.get_model("logistics", "StockResolution").objects.get(
            disposition_id=decision.pk
        )
        legacy = old.get_model("logistics", "StockPosting").objects.create(
            organisation_id=sample.ours.pk,
            disposition_id=decision.pk,
            resolution_id=reading.pk,
            held=False,
            unit="Each",
            quantity=Decimal(7),
            location_id=place.pk,
            location_name="Published bay",
            location_kind=LocationKind.SERVICEABLE,
            shelf_life_basis="Not Applicable",
            physical_on=decision.disposition_on,
            posted_on=TODAY,
            actor_id=person.pk,
            actor_name=person.full_name,
            authority="Published Stores authority",
        )
        initial = legacy.movements.get()
        keys = {row.pk: Event.of(row).get().hash for row in (place, reading, legacy, initial)}
    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        MigrationExecutor(connection).migrate(latest)
    with working_for(sample.ours.pk, sample.lucy.pk):
        lot = StockPosting.objects.get(pk=legacy.pk)
        assert lot.resolution_id == reading.pk
        (position,) = stores.positions([lot], TODAY, 30)
        assert position.location.pk == place.pk
        assert (position.on_hand, position.available) == (Decimal(7), Decimal(7))
        assert keys == {
            row.pk: Event.of(row).get().hash for row in (place, lot.resolution, lot, initial)
        }
