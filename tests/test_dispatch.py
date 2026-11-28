"""Database guarantees and archive reconstruction for dispatch records."""

import io
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.exports.build import build
from airworthiness_plus.exports.verify import verify
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.organisations.models import Approval, ApprovalType
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning import services as plan
from airworthiness_plus.staffing import dispatch, roster
from airworthiness_plus.staffing.dispatch_models import DispatchAssignment, DispatchWindow
from airworthiness_plus.staffing.roster_models import Handover
from airworthiness_plus.staffing.services import RefusedError
from tests.conftest import as_owner, as_owner_who_is_not_a_superuser
from tests.support import TODAY, Sample, add_sample_fleet

pytestmark = pytest.mark.django_db


def _on(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 18, hour, minute, tzinfo=UTC)


def test_dispatch_archive_retains_changes_and_database_rejects_foreign_links(
    sample: Sample,
) -> None:
    plane = add_sample_fleet(sample)["G-ABCD"]
    with working_for(sample.ours.id, sample.planner.id):
        package = plan.build_package(
            plane,
            reference="WP-DISPATCH-TEST",
            title="Replace lamp",
            location="Hangar 2",
            starts_on=TODAY,
            ends_on=TODAY,
        )
        manual = data.record_data(
            organisation=sample.ours,
            title="Dispatch Instructions",
            author="Synthetic aircraft manufacturer",
            kind=Kind.INSTRUCTIONS,
            applies_to=[plane.type_rating],
            revision="1",
            revision_date=TODAY,
            check_due=TODAY,
        )
        card = plan.add_card(
            package,
            title="Lamp installation and function check",
            data_set=manual,
            instruction="Chapter 33",
            planned_hours=Decimal("1.0"),
        )
        sam = Person.objects.get(full_name="Sam Patel")
        lucy = Person.objects.get(user=sample.lucy)
        approval = Approval.objects.get(approval=ApprovalType.PART_CAO)
        day = roster.add_shift(
            actor=sample.planner,
            approval=approval,
            person=sam,
            area="Hangar 2",
            shift_name="Day",
            starts_at=_on(8),
            ends_at=_on(17),
            break_minutes=30,
            other_minutes=0,
            maintenance=True,
        )
        night = roster.add_shift(
            actor=sample.planner,
            approval=approval,
            person=lucy,
            area="Hangar 2",
            shift_name="Night",
            starts_at=_on(16),
            ends_at=_on(22),
            break_minutes=30,
            other_minutes=0,
            maintenance=True,
        )
        initial = dispatch.assign(
            actor=sample.planner,
            card=card,
            shift=day,
            starts_at=_on(12),
            ends_at=_on(13),
            reason="First slot",
        )
        dispatch.add_window(
            actor=sample.planner,
            shift=day,
            starts_at=_on(12),
            ends_at=_on(12, 30),
            note="Scheduled break",
        )
        before = dispatch.day_board(TODAY, sample.ours)
        assert before.assignments[0][1] == ["Overlaps a recorded break"]
        moved = dispatch.assign(
            actor=sample.planner,
            card=card,
            shift=night,
            previous=initial,
            starts_at=_on(17),
            ends_at=_on(18),
            reason="Shift boundary",
        )
        with pytest.raises(RefusedError, match="Assignment Has Changed"):
            dispatch.assign(
                actor=sample.planner,
                card=card,
                shift=night,
                previous=initial,
                starts_at=_on(18),
                ends_at=_on(19),
                reason="Stale form",
            )
        with pytest.raises(DatabaseError), transaction.atomic():
            DispatchAssignment.objects.filter(pk=initial.pk).update(reason="Rewritten")
        with as_owner(), pytest.raises(DatabaseError), transaction.atomic():
            DispatchAssignment.objects.filter(pk=initial.pk).update(reason="Rewritten as owner")
        assert Event.of(initial).get().action == "Created"
        assert Event.of(moved).get().actor_id == sample.planner.pk
        handover = roster.record_handover(
            actor=sample.planner,
            package=package,
            card=card,
            outgoing=sam,
            incoming=lucy,
            handed_at=_on(16, 45),
            stage="Lamp to check",
            parts="Tools checked",
        )
        with pytest.raises(RefusedError, match="Incoming Person"):
            roster.acknowledge(handover, sample.planner)
    with working_for(sample.ours.id, sample.lucy.id):
        roster.acknowledge(handover, sample.lucy)
        with pytest.raises(RefusedError, match="Once"):
            roster.acknowledge(handover, sample.lucy)
        archive = build(sample.ours, by=sample.lucy)
        assert verify(archive.content).problems == ()
    with zipfile.ZipFile(io.BytesIO(archive.content)) as files:
        assignments = json.loads(files.read("records/staffing_dispatchassignment.json"))
        records = {row["id"]: row for row in assignments}
        assert records[str(moved.pk)]["supersedes_id"] == str(initial.pk)
        assert records[str(initial.pk)]["reason"] == "First slot"
        windows = json.loads(files.read("records/staffing_dispatchwindow.json"))
        assert windows[0]["shift_id"] == str(day.pk)
        handovers = json.loads(files.read("records/staffing_handover.json"))
        assert handovers[0]["card_id"] == str(card.pk)
        assert handovers[0]["actor_id"] == str(sample.lucy.pk)
        history = json.loads(files.read("history/staffing_handover.json"))
        assert [item["action"] for item in history] == ["Created", "Changed"]
        assert history[1]["previous_hash"] == history[0]["hash"]

    with working_for(sample.other.id, sample.stranger.id):
        assert not DispatchAssignment.objects.exists()
        assert not DispatchWindow.objects.exists()
        with pytest.raises(DatabaseError), transaction.atomic():
            DispatchWindow.objects.create(
                organisation=sample.other,
                shift_id=day.pk,
                starts_at=_on(12),
                ends_at=_on(12, 30),
                note="Forged break",
            )


def _prior_handover(
    sample: Sample,
    aircraft: Aircraft,
    executor: MigrationExecutor,
) -> tuple[Handover, str]:
    old = executor.loader.project_state([("staffing", "0006_planning_evidence_rules")]).apps
    handover_model = old.get_model("staffing", "Handover")
    with working_for(sample.ours.id, sample.planner.id):
        package = plan.build_package(
            aircraft,
            reference="WP-DISPATCH-LEGACY",
            title="Carry inspection forward",
            location="Hangar 2",
            starts_on=TODAY,
            ends_on=TODAY,
        )
        handover = handover_model.objects.create(
            organisation_id=sample.ours.id,
            package_id=package.pk,
            outgoing_id=Person.objects.get(full_name="Sam Patel").pk,
            incoming_id=Person.objects.get(user=sample.lucy).pk,
            stage="Avionics inspection outstanding",
            parts="Tag in place",
            handed_at=_on(16, 45),
            overlap=15,
            overlap_target=15,
        )
        return handover, Event.of(handover).get().hash


def test_dispatch_migration_preserves_populated_handover_history(sample: Sample) -> None:
    aircraft = add_sample_fleet(sample)["G-ABCD"]
    with as_owner():
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        executor.migrate([("staffing", "0006_planning_evidence_rules")])
    old_handover, original_hash = _prior_handover(sample, aircraft, executor)
    with as_owner_who_is_not_a_superuser():
        MigrationExecutor(connection).migrate(latest)
    with working_for(sample.ours.id, sample.lucy.id):
        handover = Handover.objects.get(pk=old_handover.pk)
        assert handover.card_id is None
        assert handover.stage == "Avionics inspection outstanding"
        assert Event.of(handover).get().hash == original_hash
        roster.acknowledge(handover, sample.lucy)
        handover.refresh_from_db()
        assert handover.acknowledged_at is not None
        assert handover.acknowledged_at <= timezone.now()
        assert Event.of(handover).get(sequence=2).previous_hash == original_hash
        assert verify(build(sample.ours, by=sample.lucy).content).problems == ()
