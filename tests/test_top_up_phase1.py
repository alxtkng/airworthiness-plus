"""The test site's top-up of the Phase 1 sample (REQ-294).

A test site database seeded before Phase 1 of the canvas build is given
the Phase 1 records of design-system/SampleData.md at its next start. The
rules are those the independent review of 24 November 2026 set for the
first top-up (finding 3): it adds only what is missing, changes nothing
that exists, runs once, never links by name, and never fails the start.

By hand, for a sample as ``main`` seeded it before Phase 1:

- Defects: 7 of the 9, and both actions on repeats: 9 records. The two
  deferred by named certifying staff are left out; nobody is looked up.
- Contracts: 5 contracts and 3 work orders: 8.
- Components: 7, each with its fitting.
- Modifications and weighings: 4 bulletins, 5 changes, 6 weighings and 6
  issues of the schedule: 21.
- Departures and annual review: G-DGHI's programme, its 2 departures and
  G-FMNO's review in progress: 4.
- Sources of directives: 4.
- Transfer and configuration: G-HKLM's checklist and its 12 positions: 13.
- The certificates of release to service of WP-2026-043 are left out:
  they name Chris Moore.
"""

from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Status
from airworthiness_plus.components.models import Component, Installation
from airworthiness_plus.configuration.models import Baseline, Position, Transfer, TransferItem
from airworthiness_plus.contracts import services as contract_services
from airworthiness_plus.contracts.models import Contract, Scope, WorkOrder
from airworthiness_plus.defects import services as defect_services
from airworthiness_plus.defects.models import Basis, Decision, Defect, RepeatAction
from airworthiness_plus.directives.models import Source
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import APPLICATION_ROLE
from airworthiness_plus.modifications.models import Bulletin, Change, Weighing, WeightSchedule
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.programme.models import AnnualReview, Departure
from airworthiness_plus.releases.models import Release
from airworthiness_plus.sample import build, phase1, top_up
from airworthiness_plus.sample.management.commands import prepare_test_site
from airworthiness_plus.sample.models import Added, Part
from tests.conftest import as_owner_who_is_not_a_superuser
from tests.support import TODAY, Sample, make_sample

pytestmark = pytest.mark.django_db

ADDED = [
    "Defects of the Sample Added, 9 Records",
    "Contracts of the Sample Added, 8 Records",
    "Components of the Sample Added, 7 Records",
    "Modifications and Weighings of the Sample Added, 21 Records",
    "Departures and Annual Review of the Sample Added, 4 Records",
    "Sources of Directives of the Sample Added, 4 Records",
    "Transfer and Configuration of the Sample Added, 13 Records",
]
COUNTED = (
    Defect, RepeatAction, Contract, WorkOrder, Release, Component, Installation, Bulletin,
    Change, Weighing, WeightSchedule, Departure, AnnualReview, Source, Transfer, TransferItem,
    Position, Baseline,
)  # fmt: skip


@pytest.fixture(autouse=True)
def sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


@pytest.fixture
def seeded() -> Sample:
    """The sample as ``main`` seeded it before Phase 1 of the canvas build."""
    sample = make_sample()
    fleet = build.add_fleet(sample)
    build.add_programmes(sample, fleet)
    build.add_other_work(sample, fleet)
    build.add_reviews(sample, fleet)
    build.add_directives(sample, fleet)
    build.add_maintenance_data(sample)
    return sample


def counts(sample: Sample) -> dict[str, int]:
    with working_for(sample.ours.id, sample.reader.id):
        return {model.__name__: model.objects.count() for model in COUNTED}


def history(sample: Sample) -> dict[tuple[str, Any], int]:
    """Return the number of history entries of every record the organisation holds."""
    with working_for(sample.ours.id, sample.reader.id):
        found: dict[tuple[str, Any], int] = {}
        for record_type, record_id, sequence in Event.objects.values_list(
            "record_type", "record_id", "sequence"
        ):
            key = (record_type, record_id)
            found[key] = max(found.get(key, 0), sequence)
        return found


def unchanged(before: dict[tuple[str, Any], int], after: dict[tuple[str, Any], int]) -> bool:
    """Return whether every record held before has not one history entry more."""
    return all(after[key] == sequence for key, sequence in before.items())


def test_a_sample_seeded_before_phase_1_is_given_its_records_once(seeded: Sample) -> None:
    """REQ-294. Golden: what is added, counted by hand in the heading of this file.
    Not one record that was there has a history entry more. A second start adds
    nothing and changes nothing."""
    assert set(counts(seeded).values()) == {0}
    before = history(seeded)
    assert prepare_test_site.bring_phase_1(seeded.administrator) == ADDED
    assert counts(seeded) == {
        "Defect": 7,
        "RepeatAction": 2,
        "Contract": 5,
        "WorkOrder": 3,
        "Release": 0,
        "Component": 9,
        "Installation": 9,
        "Bulletin": 4,
        "Change": 7,
        "Weighing": 6,
        "WeightSchedule": 6,
        "Departure": 2,
        "AnnualReview": 1,
        "Source": 4,
        "Transfer": 1,
        "TransferItem": 10,
        "Position": 12,
        "Baseline": 0,
    }
    once = history(seeded)
    assert unchanged(before, once)
    with working_for(seeded.ours.id, seeded.reader.id):
        assert sorted(Added.objects.values_list("part", flat=True)) == sorted(
            set(Part.values) - {Part.WORK_PACKAGES, Part.STAFFING_PLAN}
        )
        # Nobody was looked up: no defect names a person.
        assert not Defect.objects.exclude(decided_by__isnull=True).exists()
        assert set(Defect.objects.values_list("decided_by_name", flat=True)) == {""}
        assert not Defect.objects.exclude(work_done__isnull=True).exists()
        # G-DGHI was Unserviceable already, so its grounding defect is recorded.
        cable = Defect.objects.get(title="Stabilator Trim Cable Frayed at Pulley")
        assert cable.aircraft.status == Status.UNSERVICEABLE
        assert cable.aircraft.unserviceable_reason == "Stabilator Trim Cable"
        # G-HKLM's checklist as the board has it: 4 of 10, the contract borne out.
        states = list(TransferItem.objects.values_list("state", flat=True))
        assert states.count("Complete") == 3 and states.count("Not Applicable") == 1
        assert chain.problems(list(Event.objects.all())) == []
    assert prepare_test_site.bring_phase_1(seeded.administrator) == []
    assert history(seeded) == once


def test_a_top_up_after_the_sample_was_edited_changes_nothing_and_links_nobody(
    seeded: Sample,
) -> None:
    """REQ-294. After the kinds of edit the review of 24 November 2026 made: Chris
    Moore is renamed, G-ABCD is given another registration, G-DGHI is made
    Serviceable and G-HKLM is moved to the Fleet. Nothing is recorded against the
    aircraft that is no longer the sample's, G-DGHI is not grounded again, nobody
    is looked up, and no record that was there is touched."""
    with working_for(seeded.ours.id, seeded.administrator.id):
        chris = Person.objects.get(full_name="Chris Moore")
        people_services.change_person(
            chris,
            full_name="[Chris Moore Renamed]",
            role=chris.role,
            staff_group=StaffGroup(chris.staff_group),
            reports_to=chris.reports_to,
            employment=Employment(chris.employment),
            licence=chris.licence,
            joined_on=chris.joined_on,
            left_on=chris.left_on,
            by=seeded.administrator,
        )
    with working_for(seeded.ours.id, seeded.lucy.id):
        abcd = Aircraft.objects.get(registration="G-ABCD")
        Aircraft.objects.filter(pk=abcd.pk).update(registration="G-ZZZZ")
        aircraft_services.make_serviceable(Aircraft.objects.get(registration="G-DGHI"))
        hklm = Aircraft.objects.get(registration="G-HKLM")
        aircraft_services.record_received(hklm, 18)
        aircraft_services.complete_transfer(hklm)
    before = history(seeded)
    assert prepare_test_site.bring_phase_1(seeded.administrator) == [
        # G-EJKL's socket, G-CDEF's spinner, G-DGHI's lamp of June, and one action.
        "Defects of the Sample Added, 4 Records",
        # G-ABCD's contract and work order are left out.
        "Contracts of the Sample Added, 6 Records",
        # The battery and the vacuum pump were G-ABCD's.
        "Components of the Sample Added, 5 Records",
        # 2 bulletins, 4 changes, 5 weighings and 5 issues.
        "Modifications and Weighings of the Sample Added, 16 Records",
        "Departures and Annual Review of the Sample Added, 4 Records",
        "Sources of Directives of the Sample Added, 4 Records",
    ]
    assert unchanged(before, history(seeded))
    with working_for(seeded.ours.id, seeded.reader.id):
        renamed = Aircraft.objects.get(pk=abcd.pk)
        for model in (Defect, Contract, WorkOrder, Bulletin, Change, Weighing, WeightSchedule):
            assert not model.objects.filter(aircraft=renamed).exists(), model
        assert not Installation.objects.filter(aircraft=renamed).exists()
        dghi = Aircraft.objects.get(registration="G-DGHI")
        assert dghi.status == Status.SERVICEABLE
        assert not Defect.objects.filter(title="Stabilator Trim Cable Frayed at Pulley").exists()
        assert not Defect.objects.exclude(decided_by__isnull=True).exists()
        assert list(RepeatAction.objects.values_list("chapter", flat=True)) == [33]
        # G-HKLM is of the Fleet now: no checklist is started for it.
        assert not Transfer.objects.exists() and not Position.objects.exists()
        assert Person.objects.filter(full_name="Chris Moore").count() == 0
    assert prepare_test_site.bring_phase_1(seeded.administrator) == []


def test_an_aircraft_is_the_samples_only_by_its_registration_and_its_type_rating(
    seeded: Sample,
) -> None:
    """REQ-294. G-BXYZ has been given another type rating: it is no longer the
    aircraft the sample described, though its registration is the sample's. Nothing
    is recorded against it; everything else is added."""
    with working_for(seeded.ours.id, seeded.lucy.id):
        bxyz = Aircraft.objects.get(registration="G-BXYZ")
        Aircraft.objects.filter(pk=bxyz.pk).update(type_rating="[Another Type Rating]")
    before = history(seeded)
    said = prepare_test_site.bring_phase_1(seeded.administrator)
    assert said == [
        ADDED[0],
        # G-BXYZ's contract; its fire extinguisher; its bulletin, change, weighing and issue.
        "Contracts of the Sample Added, 7 Records",
        "Components of the Sample Added, 6 Records",
        "Modifications and Weighings of the Sample Added, 17 Records",
        *ADDED[4:],
    ]
    assert unchanged(before, history(seeded))
    with working_for(seeded.ours.id, seeded.reader.id):
        for model in (Defect, Contract, WorkOrder, Bulletin, Change, Weighing, WeightSchedule,
                      Installation):  # fmt: skip
            assert not model.objects.filter(aircraft=bxyz).exists(), model


def test_a_sample_that_holds_a_part_already_is_given_none_of_it() -> None:
    """REQ-294. It adds only what is missing. A sample that holds a defect of its own
    is given no defect of the sample, and every other part."""
    sample = make_sample()
    fleet = build.add_fleet(sample)
    build.add_programmes(sample, fleet)
    build.add_other_work(sample, fleet)
    with working_for(sample.ours.id, sample.planner.id):
        own = defect_services.record_defect(
            Aircraft.objects.get(pk=fleet["G-EJKL"].pk),
            title="[Their Own Defect]",
            found_on=TODAY,
            chapter=33,
            system="Lights",
            decision=Decision.DEFERRED,
            basis=Basis.PILOT_NON_REQUIRED,
            decided_on=TODAY,
        )
    before = history(sample)
    assert prepare_test_site.bring_phase_1(sample.administrator) == ADDED[1:]
    assert unchanged(before, history(sample))
    with working_for(sample.ours.id, sample.reader.id):
        assert list(Defect.objects.values_list("title", flat=True)) == [own.title]
        assert not RepeatAction.objects.exists()
        assert Added.objects.filter(part=Part.DEFECTS).exists()


def test_a_sample_built_whole_is_given_nothing() -> None:
    """REQ-294. A sample built after Phase 1 holds every part. The start records
    each as done and adds nothing: seven entries more in the history, those seven."""
    sample = make_sample()
    fleet = build.add_fleet(sample)
    build.add_programmes(sample, fleet)
    build.add_other_work(sample, fleet)
    phase1.add_defects(sample.ours, sample.planner, fleet)
    phase1.add_repeat_actions(sample.ours, sample.lucy)
    phase1.add_contracts(sample.ours, sample.lucy, fleet)
    phase1.add_releases(sample.ours, sample.planner, fleet)
    phase1.add_components(sample.ours, sample.planner, fleet)
    phase1.add_modifications(sample.ours, sample.planner, fleet)
    phase1.add_programme_records(sample.ours, sample.lucy, fleet)
    phase1.add_sources(sample.ours, sample.planner)
    phase1.add_set_up(sample.ours, sample.lucy, fleet)
    held = counts(sample)
    assert held["Defect"] == 9 and held["Release"] == 2 and held["Position"] == 12
    before = history(sample)
    assert prepare_test_site.bring_phase_1(sample.administrator) == []
    assert counts(sample) == held
    after = history(sample)
    assert unchanged(before, after)
    assert len(after) == len(before) + 7
    assert prepare_test_site.bring_phase_1(sample.administrator) == []
    assert history(sample) == after


def test_a_part_that_fails_is_undone_whole_said_and_never_tried_again(
    seeded: Sample, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-294. It never fails the start, and it runs once. A fault part way through
    the components leaves no component behind, is said in one line that names no
    record, and the other parts are added. The next start does not try again."""
    calls = {"made": 0}
    real = top_up._one_component

    def faulty(*args: Any, **kwargs: Any) -> None:
        calls["made"] += 1
        if calls["made"] == 3:
            raise RuntimeError("[A Fault Naming Something Private]")
        real(*args, **kwargs)

    monkeypatch.setattr(top_up, "_one_component", faulty)
    before = history(seeded)
    said = prepare_test_site.bring_phase_1(seeded.administrator)
    assert said == [
        ADDED[0],
        ADDED[1],
        "Components of the Sample Not Added: RuntimeError",
        *ADDED[3:],
    ]
    assert "Private" not in " ".join(said)
    assert unchanged(before, history(seeded))
    with working_for(seeded.ours.id, seeded.reader.id):
        # Two were made before the fault, and both are undone. G-HKLM's two are its own part.
        assert Component.objects.count() == 2
        assert not Installation.objects.exclude(aircraft__registration="G-HKLM").exists()
        assert Added.objects.filter(part=Part.COMPONENTS).exists()
        assert chain.problems(list(Event.objects.all())) == []
    monkeypatch.setattr(top_up, "_one_component", real)
    assert prepare_test_site.bring_phase_1(seeded.administrator) == []
    assert calls["made"] == 3
    # A fault outside any part does not stop the start either.
    monkeypatch.setattr(top_up, "aircraft_of_the_sample", lambda: 1 / 0)
    assert prepare_test_site.bring_phase_1(seeded.administrator) == [
        "Phase 1 of the Sample Not Brought Up to Date: ZeroDivisionError"
    ]


def test_an_item_the_records_do_not_bear_out_is_left_open(seeded: Sample) -> None:
    """REQ-294. The organisation has drawn up a contract of its own, for G-BXYZ, so
    the contracts of the sample are not added. G-HKLM then has no contract, and
    the Management Contract of its checklist, which the sample records as
    complete, is left open: the rule every page obeys refuses it, and the rest of
    the part goes on."""
    with working_for(seeded.ours.id, seeded.lucy.id):
        contract_services.draw_up_contract(
            Aircraft.objects.get(registration="G-BXYZ"),
            scope=Scope.ALL,
            tasks="",
            type_of_operation="[Their Own]",
            owner_address="[Their Own Address]",
            signed_on=date(2026, 1, 5),
        )
    assert prepare_test_site.bring_phase_1(seeded.administrator) == [ADDED[0], *ADDED[2:]]
    with working_for(seeded.ours.id, seeded.reader.id):
        assert Contract.objects.count() == 1 and not WorkOrder.objects.exists()
        item = TransferItem.objects.get(number=2)
        assert (item.state, item.note) == ("Open", "")
        assert TransferItem.objects.filter(state="Complete").count() == 2
        assert Position.objects.count() == 12


def test_the_phase_1_top_up_runs_as_an_owner_who_is_not_a_superuser(seeded: Sample) -> None:
    """The test site's owner is held by row-level security as the application is
    (ADR-0002). The top-up is run as an owner of every table with no other power."""
    with as_owner_who_is_not_a_superuser():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user, session_user")
            current, _ = cursor.fetchone()
            assert current != APPLICATION_ROLE
        assert prepare_test_site.bring_phase_1(seeded.administrator) == ADDED
        assert prepare_test_site.bring_phase_1(seeded.administrator) == []
    assert counts(seeded)["Position"] == 12


def test_a_part_is_recorded_once_and_is_one_the_sample_has(seeded: Sample) -> None:
    """REQ-294. The database holds it: each part once for an organisation, and only
    a part that is known."""
    prepare_test_site.bring_phase_1(seeded.administrator)
    with working_for(seeded.ours.id, seeded.administrator.id):
        for part in set(Part.values) - {Part.WORK_PACKAGES, Part.STAFFING_PLAN}:
            with pytest.raises(IntegrityError, match="sample_part_added_once"):
                with transaction.atomic():
                    Added.objects.create(organisation=seeded.ours, part=part)
        with pytest.raises(IntegrityError, match="sample_part_is_known"), transaction.atomic():
            Added.objects.create(organisation=seeded.ours, part="[Unknown]")
