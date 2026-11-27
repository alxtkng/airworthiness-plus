"""Planning cases for the sample fleet on 18 November 2026."""

from datetime import date
from decimal import Decimal

import pytest

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts import services as contract_services
from airworthiness_plus.contracts.models import OrderedBy
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import Kind
from airworthiness_plus.people.models import Person
from tests.support import TODAY, Sample, add_sample_fleet, get, make_sample, signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(monkeypatch: pytest.MonkeyPatch) -> tuple[Sample, Aircraft]:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    sample = make_sample()
    aircraft = add_sample_fleet(sample)["G-DGHI"]
    return sample, aircraft


def test_work_packages_board_requires_sign_in_and_lists_sample_aircraft(
    setup: tuple[Sample, Aircraft],
) -> None:
    sample, _ = setup
    response = get(signed_in(sample.reader), "/work-packages/")
    assert response.status_code == 200
    assert "Work Packages" in response.content.decode()


def test_order_and_current_data_are_checked_before_issue(setup: tuple[Sample, Aircraft]) -> None:
    """AMC1 CAO.A.055. A revision due on 18 November is in date on that day."""
    from airworthiness_plus.planning import services

    sample, aircraft = setup
    with working_for(sample.ours.id, sample.planner.id):
        package = services.build_package(
            aircraft,
            reference="WP-2026-046",
            title="Stabilator Trim Cable Rectification",
            location="Bay 1",
            starts_on=TODAY,
            ends_on=date(2026, 11, 19),
        )
        manual = data_services.record_data(
            organisation=sample.ours,
            title="Maintenance Manual Chapter 27",
            author="Piper",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="1",
            revision_date=date(2026, 11, 1),
            check_due=date(2026, 11, 17),
        )
        card = services.add_card(
            package,
            title="Install New Stabilator Trim Cable",
            data_set=manual,
            instruction="Chapter 27",
            planned_hours=Decimal("4.0"),
            critical=True,
        )
        with pytest.raises(services.RefusedError, match="Work Order"):
            services.issue_package(package)
        order = contract_services.add_work_order(
            aircraft,
            work=package.title,
            ordered_by=OrderedBy.MANAGER,
            agreed_on=date(2026, 11, 14),
        )
        services.link_order(package, order)
        with pytest.raises(services.RefusedError, match="Current"):
            services.issue_package(package)
        data_services.record_check(
            manual,
            checked_by=sample.planner,
            checked_on=date(2026, 11, 17),
            result="Amendments checked",
            next_due=TODAY,
        )
        services.issue_package(package)
        current = data_services.add_revision(manual, revision="2", revision_date=TODAY)
        card.refresh_from_db()
        assert card.revision is not None and card.revision.revision == "1"
        sam = Person.objects.get(full_name="Sam Patel")
        with pytest.raises(services.RefusedError, match="Current Maintenance Data Revision"):
            services.record_completion(
                card,
                performed_by=sam,
                completed_on=TODAY,
                sign_off_reference="Signed Card 5",
                hours=Decimal("0.0"),
                cycles=0,
            )
        services.record_completion(
            card,
            performed_by=sam,
            completed_on=TODAY,
            sign_off_reference="Signed Card 5",
            hours=Decimal("0.0"),
            cycles=0,
            revision=current,
        )
        card.refresh_from_db()
        assert card.performed_revision == current
        assert card.revision is not None and card.revision.revision == "1"


def test_critical_card_needs_separate_qualified_inspector(setup: tuple[Sample, Aircraft]) -> None:
    """CAO.A.060(h), AMC4 145.A.48(c)(2). An inspector cannot inspect their own work."""
    from airworthiness_plus.planning import services

    sample, aircraft = setup
    with working_for(sample.ours.id, sample.planner.id):
        order = contract_services.add_work_order(
            aircraft,
            work="Stabilator Trim Cable Rectification",
            ordered_by=OrderedBy.MANAGER,
            agreed_on=date(2026, 11, 14),
        )
        package = services.build_package(
            aircraft,
            reference="WP-2026-046",
            title=order.work,
            location="Bay 1",
            starts_on=TODAY,
            ends_on=TODAY,
        )
        services.link_order(package, order)
        manual = data_services.record_data(
            organisation=sample.ours,
            title="Maintenance Manual Chapter 27",
            author="Piper",
            kind=Kind.INSTRUCTIONS,
            applies_to=[aircraft.type_rating],
            revision="1",
            revision_date=date(2026, 11, 1),
            check_due=TODAY,
        )
        card = services.add_card(
            package,
            title="Install New Stabilator Trim Cable",
            data_set=manual,
            instruction="Chapter 27",
            planned_hours=Decimal("4.0"),
            critical=True,
        )
        sam = Person.objects.get(full_name="Sam Patel")
        chris = Person.objects.get(full_name="Chris Moore")
        services.issue_package(package)
        with pytest.raises(services.RefusedError, match="Above the Hours"):
            services.record_completion(
                card,
                performed_by=sam,
                completed_on=TODAY,
                sign_off_reference="Wrong reading",
                hours=Decimal("9875.3"),
                cycles=0,
            )
        services.record_completion(
            card,
            performed_by=sam,
            completed_on=TODAY,
            sign_off_reference="Signed Card 5",
            hours=Decimal("0.0"),
            cycles=0,
        )
        with pytest.raises(services.RefusedError, match="Independent"):
            services.record_inspection(
                card,
                inspector=sam,
                inspected_on=TODAY,
                qualification="Scope Record 1",
                evidence="Assembly, locking, tension, travel and correct sense checked",
            )
        services.record_inspection(
            card,
            inspector=chris,
            inspected_on=TODAY,
            qualification="Scope Record 1",
            evidence="Assembly, locking, tension, travel and correct sense checked",
        )
        card.refresh_from_db()
        assert card.inspector == chris


def test_release_closes_the_package_and_reuses_certifying_staff_checks(
    setup: tuple[Sample, Aircraft],
) -> None:
    """CAO.A.060(h) and (i), ML.A.801. No record is written on failed release."""
    from airworthiness_plus.people import services as people_services
    from airworthiness_plus.planning import services
    from airworthiness_plus.programme.models import WorkDone

    sample, aircraft = setup
    with working_for(sample.ours.id, sample.planner.id):
        order = contract_services.add_work_order(
            aircraft,
            work="Check the trim indicator",
            ordered_by=OrderedBy.MANAGER,
            agreed_on=TODAY,
        )
        package = services.build_package(
            aircraft,
            reference="WP-2026-049",
            title=order.work,
            location="Bay 1",
            starts_on=TODAY,
            ends_on=TODAY,
        )
        services.link_order(package, order)
        manual = data_services.record_data(
            organisation=sample.ours,
            title="Maintenance Manual Chapter 27",
            author="Piper",
            kind=Kind.INSTRUCTIONS,
            revision="1",
            revision_date=TODAY,
            check_due=TODAY,
        )
        card = services.add_card(
            package,
            title=order.work,
            data_set=manual,
            instruction="Chapter 27",
            planned_hours=Decimal("1.0"),
            inspection_hours=Decimal("0.5"),
            critical=True,
        )
        second = services.add_card(
            package,
            title="Refit panels",
            data_set=manual,
            instruction="Chapter 27",
            planned_hours=Decimal("1.0"),
        )
        sam = Person.objects.get(full_name="Sam Patel")
        chris = Person.objects.get(full_name="Chris Moore")
        authorisation = people_services.record_maintenance_authorisation(
            sam,
            scope="Piper PA-28 aircraft maintenance release",
            valid_from=TODAY,
            reference="TEST-TRIM",
        )
        services.issue_package(package)
        services.record_completion(
            card,
            performed_by=sam,
            completed_on=TODAY,
            sign_off_reference="Signed work card",
            hours=Decimal("9874.3"),
            cycles=0,
        )
        services.record_completion(
            second,
            performed_by=sam,
            completed_on=TODAY,
            sign_off_reference="Signed panel work card",
            hours=Decimal("9874.3"),
            cycles=0,
        )
        expected = WorkDone.objects.count()

        def release(scope_confirmed: bool) -> None:
            services.release_package(
                package,
                reference="TEST-CRS-49",
                issued_by=sam,
                issued_on=TODAY,
                maintenance_authorisation=authorisation,
                scope_confirmed=scope_confirmed,
                verification="Panels refitted, checked clear of tools and loose items",
            )

        with pytest.raises(services.RefusedError, match="Independent Inspection"):
            release(True)
        services.record_inspection(
            card,
            inspector=chris,
            inspected_on=TODAY,
            qualification="Aircraft inspection scope",
            evidence="Indicator agrees with tab movement",
        )
        with pytest.raises(services.RefusedError, match="Confirm"):
            release(False)
        assert WorkDone.objects.count() == expected
        from airworthiness_plus.planning.pending import releases_waiting

        pending = releases_waiting(date(2026, 12, 19), aircraft)
        assert len(pending) == 1 and pending[0].deadline == date(2026, 12, 18)
        release(True)
        package.refresh_from_db()
        card.refresh_from_db()
        assert package.status == "Released"
        assert card.work is not None
        from airworthiness_plus.releases.models import Release

        second.refresh_from_db()
        assert second.work is not None
        assert card.work.release_reference == second.work.release_reference == "TEST-CRS-49"
        assert (
            Release.objects.get(reference="TEST-CRS-49").maintenance_authorisation == authorisation
        )
        assert WorkDone.objects.count() == expected + 2


def test_the_test_site_adds_a_draft_work_package_once(setup: tuple[Sample, Aircraft]) -> None:
    from airworthiness_plus.planning import services
    from airworthiness_plus.planning.models import WorkPackage
    from airworthiness_plus.sample.management.commands.prepare_test_site import bring_work_packages

    sample, aircraft = setup
    with working_for(sample.ours.id, sample.planner.id):
        services.build_package(
            aircraft,
            reference="WP-OTHER",
            title="Other draft",
            location="Bay 1",
            starts_on=TODAY,
            ends_on=TODAY,
        )
    assert (
        bring_work_packages(sample.administrator)
        == "Work Packages of the Sample Added, 1 Work Package"
    )
    assert bring_work_packages(sample.administrator) == ""
    with working_for(sample.ours.id, sample.reader.id):
        draft = WorkPackage.objects.get(reference="WP-2026-048")
        assert draft.reference == "WP-2026-048" and draft.status == "Draft"
        assert draft.aircraft.registration == "G-EJKL"
        assert draft.cards.get().planned_hours == Decimal("32.0")


def test_package_keeps_earlier_task_work_when_a_later_occurrence_is_recorded(
    setup: tuple[Sample, Aircraft],
) -> None:
    from airworthiness_plus.aircraft.models import CounterKind
    from airworthiness_plus.programme import services
    from airworthiness_plus.programme.models import Basis
    from airworthiness_rules.intervals import Interval, TaskKind

    sample, aircraft = setup
    with working_for(sample.ours.id, sample.planner.id):
        programme = services.set_up_programme(
            aircraft,
            basis=Basis.INSTRUCTIONS,
            reference="[G-DGHI Maintenance Programme]",
        )
        task = services.add_task(
            programme,
            title="Trim System Check",
            kind=TaskKind.PROGRAMME_TASK,
            counter=aircraft.counters.get(kind=CounterKind.AIRFRAME),
            source="Chapter 27",
            interval=Interval(hours=Decimal("50.0")),
        )
        services.record_work(
            aircraft,
            description=task.title,
            dated=TODAY,
            hours=Decimal("9874.3"),
            cycles=0,
            task=task,
        )
        work = services.record_work(
            aircraft,
            description=task.title,
            dated=date(2026, 11, 17),
            hours=Decimal("9870.0"),
            cycles=0,
            task=task,
            historical=True,
        )
        assert task.work_done.count() == 2
        assert task.work_done.order_by("dated").first() == work
