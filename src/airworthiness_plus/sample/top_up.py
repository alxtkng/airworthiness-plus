"""Bring a sample seeded before Phase 1 of the canvas build up to date (REQ-294).

Run by the test site at every start, after the people of the sample
(``operations/test-site.md``). It follows the rules the independent review
of 24 November 2026 set for the first top-up (finding 3):

- it adds only what is missing. A part is added only where the
  organisation holds no record of that kind at all; where it holds one,
  the part is taken as done and nothing is added;
- it changes nothing that exists. Only records are added, and the few
  that are then changed are ones this top-up has just made. A defect that
  would ground an aircraft is added only where the aircraft is already
  Unserviceable; a programme is reviewed only where this top-up set it up;
- it runs once. That a part has been dealt with is recorded
  (``sample.Added``), whatever came of it, and no later start touches it;
- it never links by name. An aircraft of the sample is known by its
  registration, which is used once in an organisation, together with the
  type rating the sample gave it. No person is looked up at all: what the
  sample records against a named member of certifying staff is left out;
- it never fails the start. Each part is one piece of work: if anything of
  it is refused, the whole part is undone, the start says so in one line
  and carries on.

Every record is made through the services the pages use, so every rule
applies to it.
"""

from collections.abc import Callable
from decimal import Decimal
from functools import partial

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft, Stage, Status
from airworthiness_plus.components import services as component_services
from airworthiness_plus.components.models import Component
from airworthiness_plus.configuration import services as configuration_services
from airworthiness_plus.configuration.models import (
    Baseline,
    Position,
    Transfer,
)
from airworthiness_plus.contracts import services as contract_services
from airworthiness_plus.contracts.models import Contract, Scope, WorkOrder
from airworthiness_plus.defects import services as defect_services
from airworthiness_plus.defects.models import Decision, Defect
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.directives.models import Source
from airworthiness_plus.history.session import working_for
from airworthiness_plus.modifications import services as modification_services
from airworthiness_plus.modifications.models import (
    Bulletin,
    Change,
    Weighing,
    WeightSchedule,
)
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import AnnualReview, Departure, Programme
from airworthiness_plus.programme.models import Basis as ProgrammeBasis
from airworthiness_plus.sample import build, phase1
from airworthiness_plus.sample.models import Added, Part

Fleet = dict[str, Aircraft]

REFUSED = (
    component_services.RefusedError,
    configuration_services.RefusedError,
    contract_services.RefusedError,
    defect_services.RefusedError,
    directive_services.RefusedError,
    modification_services.RefusedError,
    programme_services.RefusedError,
)
"""What a service says when the records as they now stand do not take a row of the sample."""


def aircraft_of_the_sample() -> Fleet:
    """Return the aircraft the sample gave the organisation, by Aircraft Registration.

    An aircraft is known by its registration and the type rating the sample
    gave it, both exactly. One that has been given another registration or
    type rating since is not the sample's any more, and is left alone.
    """
    wanted = {registration: type_rating for registration, type_rating, _, _ in build.FLEET}
    wanted["G-HKLM"] = build.PA38
    return {
        aircraft.registration: aircraft
        for aircraft in Aircraft.objects.all()
        if wanted.get(aircraft.registration) == aircraft.type_rating
    }


def _row(add: Callable[[], object]) -> int:
    """Add one row of the sample, or leave it out if the records do not take it."""
    try:
        with transaction.atomic():
            add()
    except REFUSED:
        return 0
    return 1


def _defects(ours: Organisation, fleet: Fleet) -> int:
    """Add the defects that need nobody named, and what was done about the repeats."""
    added = 0
    for (
        registration,
        title,
        note,
        found_on,
        chapter,
        system,
        decision,
        basis,
        _staff,
        decided_on,
        rectification,
        closed_on,
    ) in phase1.DEFECTS:
        aircraft = fleet.get(registration)
        if aircraft is None:
            continue
        # A defect deferred by a member of certifying staff names that person. Nobody
        # is looked up, so it is sent with nobody named, and the rule of the Defects
        # page refuses it: it is left out.
        grounds = decision == Decision.NOT_DEFERRABLE and closed_on is None
        if grounds and aircraft.status != Status.UNSERVICEABLE:
            # It would make the aircraft Unserviceable, which changes what is there.
            continue
        added += _row(
            partial(
                defect_services.record_defect,
                aircraft,
                title=title,
                note=note,
                found_on=found_on,
                chapter=chapter,
                system=system,
                decision=decision,
                basis=basis,
                decided_on=decided_on,
                rectification=rectification,
                closed_on=closed_on,
            )
        )
    for type_rating, chapter, action in phase1.REPEAT_ACTIONS:
        added += _row(
            partial(
                defect_services.record_repeat_action,
                ours,
                type_rating=type_rating,
                chapter=chapter,
                action=action,
            )
        )
    return added


def _contracts(ours: Organisation, fleet: Fleet) -> int:
    """Add the contracts and the work orders of the sample."""
    added = 0
    for registration, tasks, signed_on in phase1.CONTRACTS:
        aircraft = fleet.get(registration)
        if aircraft is None:
            continue
        added += _row(
            partial(
                contract_services.draw_up_contract,
                aircraft,
                scope=Scope.LIMITED if tasks else Scope.ALL,
                tasks=tasks,
                type_of_operation="[Type of Operation]",
                owner_address=f"[Owner Address {registration}]",
                signed_on=signed_on,
            )
        )
    for registration, work, ordered_by, agreed_on in phase1.WORK_ORDERS:
        aircraft = fleet.get(registration)
        if aircraft is None:
            continue
        added += _row(
            partial(
                contract_services.add_work_order,
                aircraft,
                work=work,
                ordered_by=ordered_by,
                agreed_on=agreed_on,
            )
        )
    return added


def _one_component(
    ours: Organisation, aircraft: Aircraft, component: dict[str, object], fitting: dict[str, object]
) -> None:
    one = component_services.add_component(ours, **component)  # type: ignore[arg-type]
    values = {key: value for key, value in fitting.items() if key != "aircraft"}
    fitted = component_services.fit_component(one, aircraft, **values)  # type: ignore[arg-type]
    if one.serial_number == phase1.OWN_PROPELLER:
        component_services.remove_component(fitted, **phase1.OWN_PROPELLER_REMOVAL)  # type: ignore[arg-type]


def _components(ours: Organisation, fleet: Fleet) -> int:
    """Add the components of the sample, each with its fitting."""
    added = 0
    for component, fitting in phase1.COMPONENTS:
        aircraft = fleet.get(str(fitting["aircraft"]))
        if aircraft is None:
            continue
        added += _row(partial(_one_component, ours, aircraft, component, fitting))
    return added


def _modifications(ours: Organisation, fleet: Fleet) -> int:
    """Add the service bulletins, changes, repairs, weighings and weight schedules."""
    present = {registration for registration in fleet if registration != "G-HKLM"}
    before = (
        Bulletin.objects.count()
        + Change.objects.count()
        + Weighing.objects.count()
        + WeightSchedule.objects.count()
    )
    phase1.add_modification_rows(fleet, present)
    return (
        Bulletin.objects.count()
        + Change.objects.count()
        + Weighing.objects.count()
        + WeightSchedule.objects.count()
        - before
    )


def _programme(ours: Organisation, fleet: Fleet) -> int:
    """Add G-DGHI's programme and departures, and G-FMNO's annual review in progress.

    A programme that is there already is not reviewed or given departures:
    it is somebody's own.
    """
    added = 0
    dghi = fleet.get("G-DGHI")
    if dghi is not None and not Programme.objects.filter(aircraft=dghi).exists():
        programme = programme_services.set_up_programme(
            dghi,
            basis=ProgrammeBasis.INSTRUCTIONS,
            reference="[Programme Reference]",
            hours_per_day=Decimal("0.8"),
        )
        programme_services.record_review(programme, phase1.DGHI_REVIEWED)
        added += 1
        for task, manufacturer, says, measures, justification in phase1.DEPARTURES:
            added += _row(
                partial(
                    programme_services.add_departure,
                    programme,
                    task=task,
                    manufacturer=manufacturer,
                    programme_says=says,
                    compensating_measures=measures,
                    justification=justification,
                    recorded_on=phase1.DGHI_REVIEWED,
                    owner_copy_sent_on=phase1.DGHI_REVIEWED,
                )
            )
    fmno = fleet.get("G-FMNO")
    held = Programme.objects.filter(aircraft=fmno).first() if fmno is not None else None
    if held is not None:
        added += _row(partial(phase1.open_fmno_review, held))
    return added


def _sources(ours: Organisation, fleet: Fleet) -> int:
    """Add the sources checked for new directives."""
    phase1.add_source_rows(ours)
    return Source.objects.count()


def _set_up(ours: Organisation, fleet: Fleet) -> int:
    """Add G-HKLM's transfer checklist, positions, major items and changes."""
    hklm = fleet.get("G-HKLM")
    if hklm is None or hklm.stage != Stage.TRANSFER_IN:
        return 0
    phase1.add_set_up_rows(ours, hklm, tolerant=True)
    return 1 + Position.objects.filter(aircraft=hklm).count()


def _any(*models: type) -> Callable[[], bool]:
    return lambda: any(model.objects.exists() for model in models)  # type: ignore[attr-defined]


# Each part: what it is, whether the organisation already holds records of its
# kind, and how it is added. Components and changes come before the set-up of
# G-HKLM, which adds two of each for that aircraft.
PARTS: tuple[tuple[Part, Callable[[], bool], Callable[[Organisation, Fleet], int]], ...] = (
    (Part.DEFECTS, _any(Defect), _defects),
    (Part.CONTRACTS, _any(Contract, WorkOrder), _contracts),
    (Part.COMPONENTS, _any(Component), _components),
    (Part.MODIFICATIONS, _any(Bulletin, Change, Weighing, WeightSchedule), _modifications),
    (Part.PROGRAMME, _any(Departure, AnnualReview), _programme),
    (Part.SOURCES, _any(Source), _sources),
    (Part.SET_UP, _any(Transfer, Position, Baseline), _set_up),
)


def add_phase_1(ours: Organisation, administrator: User) -> list[str]:
    """Add the Phase 1 records of the sample that the organisation lacks, once.

    Return one line for each part that was added, or that could not be.
    Nothing given to the start, and nothing of the records, is in a line.
    """
    said = []
    with working_for(ours.id, administrator.id):
        fleet = aircraft_of_the_sample()
        for part, held, add in PARTS:
            if Added.objects.filter(part=part).exists():
                continue
            if not held():
                try:
                    with transaction.atomic():
                        count = add(ours, fleet)
                except Exception as error:
                    # The start carries on: this part is undone whole, and said.
                    said.append(f"{part.label} of the Sample Not Added: {type(error).__name__}")
                else:
                    if count:
                        said.append(f"{part.label} of the Sample Added, {count} Records")
            Added.objects.create(organisation=ours, part=part)
    return said
