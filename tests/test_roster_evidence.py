"""Checks for roster evidence and calendar boundaries."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.contracts import services as orders
from airworthiness_plus.contracts.models import OrderedBy
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.organisations.models import Approval, ApprovalType
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning import services as plan
from airworthiness_plus.staffing import roster
from airworthiness_plus.staffing.models import Absence, AbsenceType
from airworthiness_plus.staffing.roster_models import Settings
from tests.support import TODAY, add_sample_fleet, make_sample

pytestmark = pytest.mark.django_db


def test_monday_rest_and_overnight_absence_follow_the_full_shift() -> None:
    sample = make_sample()
    with working_for(sample.ours.id, sample.planner.id):
        approval = Approval.objects.get()
        sam = Person.objects.get(full_name="Sam Patel")
        for starts, ends in (
            (datetime(2026, 11, 14, 23, 30, tzinfo=UTC), datetime(2026, 11, 15, 23, tzinfo=UTC)),
            (datetime(2026, 11, 16, 1, tzinfo=UTC), datetime(2026, 11, 16, 5, tzinfo=UTC)),
            (datetime(2026, 11, 22, 21, tzinfo=UTC), datetime(2026, 11, 23, 2, tzinfo=UTC)),
        ):
            roster.add_shift(
                actor=sample.planner,
                approval=approval,
                person=sam,
                area="Hangar",
                shift_name="Day Shift",
                starts_at=starts,
                ends_at=ends,
                break_minutes=0,
                other_minutes=0,
                maintenance=True,
            )
        Absence.objects.create(
            organisation=sample.ours,
            person=sam,
            kind=AbsenceType.HOLIDAY,
            starts_on=date(2026, 11, 23),
            ends_on=date(2026, 11, 23),
        )
        checked = roster.check_shifts(date(2026, 11, 16), Settings(organisation=sample.ours))
        assert checked[0].rest == 120 and "Short Rest" in checked[0].flags
        assert "Staff Absence" in checked[-1].flags


def test_late_check_does_not_make_earlier_expired_instructions_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = [TODAY]
    monkeypatch.setattr(aircraft_services, "today", lambda: clock[0])
    sample = make_sample()
    aircraft = add_sample_fleet(sample)["G-DGHI"]
    with working_for(sample.ours.id, sample.planner.id):
        package = plan.build_package(
            aircraft,
            reference="WP-VERIFY",
            title="Work",
            location="Hangar",
            starts_on=TODAY,
            ends_on=date(2026, 11, 24),
        )
        manual = data.record_data(
            organisation=sample.ours,
            title="Probe Manual",
            author="Piper",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="1",
            revision_date=date(2026, 11, 1),
            check_due=TODAY,
        )
        card = plan.add_card(
            package,
            title="Check",
            data_set=manual,
            instruction="Chapter 27",
            planned_hours=Decimal("4.0"),
        )
        order = orders.add_work_order(
            aircraft, work=package.title, ordered_by=OrderedBy.MANAGER, agreed_on=TODAY
        )
        plan.link_order(package, order)
        plan.issue_package(package)
        clock[0] = date(2026, 11, 23)
        data.record_check(
            manual,
            checked_by=sample.planner,
            checked_on=date(2026, 11, 23),
            result="Amendments checked",
            next_due=date(2026, 12, 5),
        )
        person = Person.objects.get(full_name="Sam Patel")
        with pytest.raises(plan.RefusedError, match="Current"):
            plan.record_completion(
                card,
                performed_by=person,
                completed_on=date(2026, 11, 20),
                sign_off_reference="Signed",
                hours=Decimal("0.0"),
                cycles=0,
            )


def test_disjoint_part145_duties_cannot_mask_contractor_only_crew() -> None:
    sample = make_sample()
    from airworthiness_plus.organisations import approvals
    from airworthiness_plus.people.models import Employment

    with working_for(sample.ours.id, sample.planner.id):
        approval = approvals.record(
            sample.ours, approval=ApprovalType.PART_145, reference="UK.145.00001"
        )
        employed = Person.objects.create(
            full_name="Employed worker", organisation=sample.ours, employment=Employment.EMPLOYED
        )
        contracted = Person.objects.create(
            full_name="Contracted worker",
            organisation=sample.ours,
            employment=Employment.CONTRACTED,
        )
        for person, start, end in [(employed, 8, 12), (contracted, 12, 16)]:
            roster.add_shift(
                actor=sample.planner,
                approval=approval,
                person=person,
                area="Hangar",
                shift_name="Maintenance Cover",
                starts_at=datetime(2026, 11, 18, start, tzinfo=UTC),
                ends_at=datetime(2026, 11, 18, end, tzinfo=UTC),
                break_minutes=0,
                other_minutes=0,
                maintenance=True,
            )
        checked = roster.check_shifts(date(2026, 11, 16), Settings(organisation=sample.ours))
        assert any(one.below_half for one in roster.crews(checked)), roster.crews(checked)


def test_midnight_and_calendar_week_capacity_boundaries() -> None:
    from airworthiness_plus.staffing.capacity import weekly_loads

    sample = make_sample()
    with working_for(sample.ours.id, sample.planner.id):
        approval = Approval.objects.get()
        sam = Person.objects.get(full_name="Sam Patel")
        chris = Person.objects.get(full_name="Chris Moore")
        sam.left_on = date(2026, 11, 22)
        sam.save(update_fields=["left_on"])
        roster.add_shift(
            actor=sample.planner,
            approval=approval,
            person=sam,
            area="Hangar",
            shift_name="Late Shift",
            starts_at=datetime(2026, 11, 22, 20, tzinfo=UTC),
            ends_at=datetime(2026, 11, 23, 0, tzinfo=UTC),
            break_minutes=0,
            other_minutes=0,
            maintenance=True,
        )
        roster.add_shift(
            actor=sample.planner,
            approval=approval,
            person=chris,
            area="Hangar",
            shift_name="Night Shift",
            starts_at=datetime(2026, 11, 22, 23, tzinfo=UTC),
            ends_at=datetime(2026, 11, 23, 5, tzinfo=UTC),
            break_minutes=0,
            other_minutes=0,
            maintenance=True,
        )
        settings = Settings(organisation=sample.ours)
        first, second = weekly_loads(date(2026, 11, 16), 2, settings)
        assert (first.available, second.available) == (Decimal("5"), Decimal("5"))
