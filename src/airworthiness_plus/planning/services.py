"""Work package transitions and the hand-off to the aircraft records."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts.models import Outcome, WorkOrder
from airworthiness_plus.defects.models import Defect
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.directives.models import Applicability, Decision
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.maintenance_data.models import DataSet, Holding, Revision
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import ApprovalType, Organisation, Privilege
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person, StaffGroup
from airworthiness_plus.planning.models import WorkCard, WorkCardStepSignOff, WorkPackage
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Task, WorkDone
from airworthiness_plus.releases import services as release_services
from airworthiness_plus.releases.models import IssuedBy
from airworthiness_plus.tooling import custody
from airworthiness_plus.tooling.release_evidence import Verification
from airworthiness_rules.intervals import TaskKind


class RefusedError(ValueError):
    """The requested transition lacks the necessary evidence."""


def synthetic_available(package: WorkPackage) -> bool:
    return settings.SYNTHETIC_WORK_CARD_ATTESTATION and package.reference.startswith(
        "WP-SYNTHETIC-"
    )


def _for_maintenance(aircraft: Aircraft, on: date) -> None:
    if not approvals.may_act_on(
        aircraft.organisation, on, ApprovalType.PART_145, Privilege.MAINTENANCE
    ):
        raise RefusedError("An Approval Covering Maintenance Is Needed")


@transaction.atomic
def build_package(
    aircraft: Aircraft,
    *,
    reference: str,
    title: str,
    location: str,
    starts_on: date,
    ends_on: date,
    defect: Defect | None = None,
) -> WorkPackage:
    Organisation.objects.select_for_update().only("id").get(pk=aircraft.organisation_id)
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    _for_maintenance(aircraft, aircraft_services.today())
    reference, title, location = reference.strip().upper(), title.strip(), location.strip()
    if not reference.startswith("WP-") or len(reference) <= 3 or not title or not location:
        raise RefusedError("Give the Work Package a Reference Beginning WP-, Work and Location")
    if starts_on > ends_on:
        raise RefusedError("The Planned End Is on or After the Planned Start")
    if defect is not None and defect.aircraft_id != aircraft.id:
        raise RefusedError("The Defect Belongs to Another Aircraft")
    if WorkPackage.objects.filter(reference=reference).exists():
        raise RefusedError("This Work Package Reference Is Already Recorded")
    return WorkPackage.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        reference=reference,
        title=title,
        location=location,
        starts_on=starts_on,
        ends_on=ends_on,
        defect=defect,
    )


def _locked_draft(package: WorkPackage) -> WorkPackage:
    package = WorkPackage.objects.select_for_update().get(pk=package.pk)
    if package.issued_on is not None:
        raise RefusedError("Only a Draft Work Package Can Be Changed")
    return package


@transaction.atomic
def link_order(package: WorkPackage, order: WorkOrder) -> None:
    package = _locked_draft(package)
    order = WorkOrder.objects.select_for_update().get(pk=order.pk)
    if order.aircraft_id != package.aircraft_id:
        raise RefusedError("The Work Order Belongs to Another Aircraft")
    if order.closed_on is not None:
        raise RefusedError("Choose an Open Work Order")
    package.order = order
    package.save(update_fields=["order"])


def _check_scope(package: WorkPackage, task: Task | None, directive: Applicability | None) -> None:
    if task is not None and directive is not None:
        raise RefusedError("Choose a Programme Task or an Airworthiness Directive")
    if task is not None and task.kind == TaskKind.AIRWORTHINESS_DIRECTIVE.value:
        raise RefusedError("Select the Airworthiness Directive for Directive Compliance")
    if task is not None and (task.programme.aircraft_id != package.aircraft_id or task.retired):
        raise RefusedError("Choose a Current Programme Task for This Aircraft")
    if directive is not None and (
        directive.aircraft_id != package.aircraft_id
        or directive.decision != Decision.APPLICABLE
        or directive.terminated_on is not None
    ):
        raise RefusedError("Choose an Applicable Airworthiness Directive for This Aircraft")


@transaction.atomic
def add_card(
    package: WorkPackage,
    *,
    title: str,
    data_set: DataSet,
    instruction: str,
    planned_hours: Decimal,
    inspection_hours: Decimal = Decimal("0"),
    critical: bool = False,
    task: Task | None = None,
    directive: Applicability | None = None,
    structured_steps: str = "",
) -> WorkCard:
    package = _locked_draft(package)
    title, instruction = title.strip(), instruction.strip()
    if not title or not instruction:
        raise RefusedError("Give the Work Card a Task and an Instruction Reference")
    if planned_hours <= 0 or inspection_hours < 0 or (not critical and inspection_hours != 0):
        raise RefusedError(
            "Give Positive Planned Hours and Count Inspection Hours for Critical Tasks"
        )
    if data_set.organisation_id != package.organisation_id:
        raise RefusedError("Choose Maintenance Data From This Organisation")
    _check_scope(package, task, directive)
    if task is not None and package.cards.filter(task=task).exists():
        raise RefusedError("This Programme Task Already Has a Work Card in the Package")
    if directive is not None and package.cards.filter(directive=directive).exists():
        raise RefusedError("This Airworthiness Directive Already Has a Work Card in the Package")
    steps = []
    source_revision = None
    if structured_steps.strip():
        if not synthetic_available(package):
            raise RefusedError("Structured Work Cards Are Available Only for Synthetic Packages")
        for source in structured_steps.splitlines():
            source = source.strip()
            if source:
                steps.append(
                    {
                        "instruction": source.removeprefix("*").strip(),
                        "critical": source.startswith("*"),
                    }
                )
        if len(steps) > 30 or any(not item["instruction"] for item in steps):
            raise RefusedError("Enter Up to 30 Nonempty Instructions")
        if any(item["critical"] for item in steps) and not critical:
            raise RefusedError("Mark the Card Critical When It Contains a Critical Step")
        data_set = DataSet.objects.select_for_update().get(pk=data_set.pk)
        source_revision = data_services.current_revision(data_set)
        _check_data(
            package,
            data_set,
            source_revision,
            aircraft_services.today(),
            checked_until=data_set.check_due,
        )
    return WorkCard.objects.create(
        organisation_id=package.organisation_id,
        package=package,
        title=title,
        data_set=data_set,
        instruction=instruction,
        structured_revision=source_revision,
        steps=steps,
        planned_hours=planned_hours,
        inspection_hours=inspection_hours,
        critical=critical,
        task=task,
        directive=directive,
    )


def _check_data(
    package: WorkPackage,
    data_set: DataSet,
    revision: Revision | None,
    on: date,
    *,
    checked_until: date | None,
) -> None:
    if (
        (
            data_set.holding != Holding.HELD
            and not (data_set.no_longer_held_on is not None and on < data_set.no_longer_held_on)
        )
        or revision is None
        or revision.revision_date > on
        or checked_until is None
        or checked_until < on
        or (
            package.issued_on is None
            and data_set.evidence_dated is not None
            and data_set.evidence_dated > on
        )
        or (data_set.applies_to and package.aircraft.type_rating not in data_set.applies_to)
    ):
        raise RefusedError(f"Maintenance Data Must Be Applicable, Held and Current: {data_set}")


@transaction.atomic
def issue_package(package: WorkPackage, *, approval: str = "") -> None:
    Organisation.objects.select_for_update(no_key=True).only("id").get(pk=package.organisation_id)
    package = _locked_draft(package)
    today = aircraft_services.today()
    _for_maintenance(package.aircraft, today)
    if package.order_id is None:
        raise RefusedError("An Agreed Work Order Is Needed Before Issue")
    order = WorkOrder.objects.select_for_update().get(pk=package.order_id)
    if order.closed_on is not None or order.agreed_on > today:
        raise RefusedError("The Work Order Must Be Open and Agreed Before Issue")
    cards = list(package.cards.select_related("task__programme", "directive").order_by("pk"))
    if not cards:
        raise RefusedError("Add at Least One Work Card Before Issue")
    keys = {card.data_set_id for card in cards}
    data = {
        item.pk: item
        for item in DataSet.objects.select_for_update().filter(pk__in=keys).order_by("pk")
    }
    for card in cards:
        _check_scope(package, card.task, card.directive)
        data_set = data[card.data_set_id]
        revision = data_services.current_revision(data_set)
        _check_data(package, data_set, revision, today, checked_until=data_set.check_due)
        if card.steps and (
            not synthetic_available(package) or revision != card.structured_revision
        ):
            raise RefusedError("The Structured Work Card Source Is Superseded or Unavailable")
        card.revision = revision
        card.issue_check_due = data_set.check_due
        card.save(update_fields=["revision", "issue_check_due"])
    package.issued_on = today
    package.save(update_fields=["issued_on"])
    try:
        custody.pin_approval(
            package, approval, today, "Governing approval recorded at package issue"
        )
    except custody.RefusedError as error:
        raise RefusedError(str(error)) from error


def _locked_issued(package_id: UUID) -> WorkPackage:
    package = WorkPackage.objects.select_for_update().get(pk=package_id)
    if package.issued_on is None or package.released_on is not None:
        raise RefusedError("The Work Package Must Be Issued and Open")
    if package.order_id is None:
        raise RefusedError("An Agreed Work Order Is Needed")
    order = WorkOrder.objects.select_for_update().get(pk=package.order_id)
    if order.outcome == Outcome.WITHDRAWN:
        raise RefusedError("The Work Order Has Been Withdrawn")
    return package


def _person_on(person: Person, package: WorkPackage, on: date) -> None:
    if (
        person.organisation_id != package.organisation_id
        or (person.joined_on is not None and on < person.joined_on)
        or (person.left_on is not None and on > person.left_on)
    ):
        raise RefusedError("The Named Person Must Be With the Organisation on That Day")


def synthetic_authorisation(
    card: WorkCard, actor: User, person: Person, on: date, *, inspection: bool = False
) -> MaintenanceAuthorisation:
    if not synthetic_available(card.package) or not actor.may(Action.RECORD_WORK_CARD):
        raise RefusedError("Synthetic Work Card Evidence Is Unavailable")
    if person.user_id != actor.pk or actor.organisation_id != card.organisation_id:
        raise RefusedError("Sign In as the Named Person for This Synthetic Action")
    _person_on(person, card.package, on)
    scope = MaintenanceAuthorisation.SYNTHETIC_COMPLETION_SCOPE
    if inspection:
        scope += "independent inspection: "
    scope += card.package.aircraft.type_rating
    grants = MaintenanceAuthorisation.objects.filter(person=person, scope=scope).select_related(
        "withdrawal"
    )
    grant = next((grant for grant in grants if grant.term_on(on) == "Within Recorded Dates"), None)
    if person.staff_group != StaffGroup.CERTIFYING or grant is None:
        raise RefusedError("No Current Synthetic Authorisation Covers This Task and Aircraft Type")
    return grant


@transaction.atomic
def sign_step(card: WorkCard, actor: User, number: int, evidence: str) -> WorkCardStepSignOff:
    package = _locked_issued(card.package_id)
    card = WorkCard.objects.get(pk=card.pk)
    today = aircraft_services.today()
    if (
        not synthetic_available(package)
        or card.completed_on is not None
        or not 1 <= number <= len(card.steps)
    ):
        raise RefusedError("Choose a Step on an Open Synthetic Work Card")
    data_set = DataSet.objects.select_for_update().get(pk=card.data_set_id)
    current = data_services.current_revision(data_set)
    if current != card.revision:
        raise RefusedError("The Issued Structured Work Card Source Is Superseded")
    _check_data(package, data_set, current, today, checked_until=data_set.check_due)
    prior = list(card.step_signoffs.all())
    person = Person.objects.select_for_update().filter(user=actor).first()
    if person is None:
        raise RefusedError("The Signed-In User Needs a Staff Record")
    grant = synthetic_authorisation(card, actor, person, today)
    evidence = evidence.strip()
    if not evidence:
        raise RefusedError("Record the Step Result")
    if any(step.performer_id != person.pk for step in prior):
        raise RefusedError("This Pilot Requires the Same Authorised Performer for Every Step")
    if len(prior) >= number and prior[number - 1].evidence == evidence:
        return prior[number - 1]
    if len(prior) + 1 != number:
        raise RefusedError("Sign Each Step Once in the Order Shown")
    return WorkCardStepSignOff.objects.create(
        organisation_id=card.organisation_id,
        card=card,
        number=number,
        performer=person,
        actor=actor,
        authorisation=grant,
        signed_on=today,
        evidence=evidence,
    )


@transaction.atomic
def record_completion(
    card: WorkCard,
    *,
    performed_by: Person,
    completed_on: date,
    sign_off_reference: str,
    hours: Decimal,
    cycles: int,
    supervised_by: Person | None = None,
    revision: Revision | None = None,
) -> None:
    package = _locked_issued(card.package_id)
    card = WorkCard.objects.get(pk=card.pk)
    sign_off_reference = sign_off_reference.strip()
    if card.completed_on is not None:
        raise RefusedError("The Work Card Already Holds Signed Work Evidence")
    if (
        package.issued_on is None
        or not package.issued_on <= completed_on <= aircraft_services.today()
    ):
        raise RefusedError("Work Is Completed Between Package Issue and Today")
    if not sign_off_reference or not 0 <= hours <= Decimal("9999999.9") or cycles < 0:
        raise RefusedError("Give Signed Work Evidence and the Counter Readings")
    data_set = DataSet.objects.select_for_update().get(pk=card.data_set_id)
    revision = revision or card.revision
    if card.steps:
        if not synthetic_available(package) or revision != card.structured_revision:
            raise RefusedError("The Completed Work Must Use the Pinned Structured Revision")
        signoffs = list(card.step_signoffs.all())
        if len(signoffs) != len(card.steps) or any(
            step.performer_id != performed_by.pk or step.signed_on > completed_on
            for step in signoffs
        ):
            raise RefusedError("Every Structured Step Needs the Named Performer's Sign-Off")
    effective = data_set.revisions.filter(revision_date__lte=completed_on)
    current = effective.order_by("-revision_date", "-current", "pk").first()
    if (
        revision is None
        or current is None
        or revision.data_set_id != data_set.id
        or revision.revision_date != current.revision_date
        or (current.current and revision.pk != current.pk)
    ):
        raise RefusedError("Record the Current Maintenance Data Revision Used for the Work")
    checks = data_set.checks.filter(
        checked_on__range=(package.issued_on, completed_on),
        next_due__isnull=False,
    ).order_by("-checked_on", "next_due")
    latest = checks.first()
    checked_until = latest.next_due if latest is not None else card.issue_check_due
    if checked_until is None:
        # A package issued before amendment checks carried their own due date.
        # Accept a retained issue-day check or current data for work done today.
        if completed_on == aircraft_services.today() or completed_on == package.issued_on:
            checked_until = data_set.check_due
    _check_data(package, data_set, revision, completed_on, checked_until=checked_until)
    card.performed_revision = revision
    task = card.directive.task if card.directive is not None else card.task
    _check_scope(package, card.task, card.directive)
    try:
        programme_services.check_work_counters(
            package.aircraft,
            task=task,
            dated=completed_on,
            hours=hours,
            cycles=cycles,
            historical=True,
        )
    except programme_services.RefusedError as error:
        raise RefusedError(str(error)) from error
    _person_on(performed_by, package, completed_on)
    if supervised_by is not None:
        _person_on(supervised_by, package, completed_on)
        if supervised_by.pk == performed_by.pk:
            raise RefusedError("The Supervisor and Person Doing the Work Must Be Different")
    card.performed_by = performed_by
    card.supervised_by = supervised_by
    card.completed_on = completed_on
    card.sign_off_reference = sign_off_reference
    card.hours = hours
    card.cycles = cycles
    card.save(
        update_fields=[
            "performed_by",
            "performed_revision",
            "supervised_by",
            "completed_on",
            "sign_off_reference",
            "hours",
            "cycles",
        ]
    )


@transaction.atomic
def record_inspection(
    card: WorkCard,
    *,
    inspector: Person,
    inspected_on: date,
    qualification: str,
    evidence: str,
    actor: User | None = None,
) -> None:
    package = _locked_issued(card.package_id)
    card = WorkCard.objects.get(pk=card.pk)
    if not card.critical or card.completed_on is None or card.inspected_on is not None:
        raise RefusedError("Record One Independent Inspection After the Critical Work Is Done")
    if inspector.pk in {card.performed_by_id, card.supervised_by_id}:
        raise RefusedError(
            "Independent Inspection Needs a Person Who Did Not Do or Supervise the Work"
        )
    if not card.completed_on <= inspected_on <= aircraft_services.today():
        raise RefusedError("Inspection Is Dated Between Completion of the Work and Today")
    _person_on(inspector, package, inspected_on)
    if card.steps:
        if actor is None or inspected_on != aircraft_services.today():
            raise RefusedError("The Independent Inspector Must Record Today's Synthetic Inspection")
        inspector = Person.objects.select_for_update().get(pk=inspector.pk)
        if card.step_signoffs.filter(performer=inspector).exists():
            raise RefusedError("Independent Inspection Needs a Person Who Did Not Sign a Step")
        card.inspection_authorisation = synthetic_authorisation(
            card, actor, inspector, inspected_on, inspection=True
        )
    qualification, evidence = qualification.strip(), evidence.strip()
    if not qualification or not evidence:
        raise RefusedError("Give Evidence of Qualification and Satisfactory Independent Inspection")
    card.inspector = inspector
    card.inspected_on = inspected_on
    card.qualification = qualification
    card.inspection_evidence = evidence
    card.save(
        update_fields=[
            "inspector",
            "inspected_on",
            "qualification",
            "inspection_evidence",
            "inspection_authorisation",
        ]
    )


@transaction.atomic
def release_package(
    package: WorkPackage,
    *,
    reference: str,
    issued_by: Person,
    issued_on: date,
    maintenance_authorisation: MaintenanceAuthorisation,
    scope_confirmed: bool,
    verification: str,
    general_verification: Verification | None = None,
) -> None:
    Organisation.objects.select_for_update(no_key=True).only("id").get(pk=package.organisation_id)
    package = _locked_issued(package.pk)
    verification = verification.strip()
    if not verification:
        raise RefusedError("Give Evidence of the General Verification Before Release")
    if package.issued_on is None or not package.issued_on <= issued_on <= aircraft_services.today():
        raise RefusedError("The Release Is Dated Between Package Issue and Today")
    if package.defect_id is not None:
        defect = Defect.objects.select_for_update().get(pk=package.defect_id)
        if defect.closed_on is None or defect.closed_on > issued_on:
            raise RefusedError("The Linked Defect Must Be Closed Before Release")
    cards = list(
        package.cards.select_related(
            "task__programme", "directive__aircraft", "directive__directive", "performed_by"
        ).order_by("-completed_on", "pk")
    )
    if not cards:
        raise RefusedError("A Work Package Must Have Work Cards")
    for card in cards:
        if (
            not card.signed
            or card.completed_on is None
            or card.completed_on > issued_on
            or (card.inspected_on is not None and card.inspected_on > issued_on)
        ):
            raise RefusedError(f"Signed Work and Any Independent Inspection Are Needed: {card}")
    if any(card.steps for card in cards):
        raise RefusedError("Synthetic Structured Cards Cannot Be Used for a Release Certificate")
    # The accomplishment service locks the people named on the cards.
    # Take those locks in the same order for every package.
    people = {issued_by.pk} | {card.performed_by_id for card in cards}
    list(Person.objects.select_for_update(no_key=True).filter(pk__in=people).order_by("pk"))
    works = [_record_card_work(package, card) for card in cards]
    try:
        release = release_services.record_certificate(
            works[0],
            reference=reference,
            kind=IssuedBy.ORGANISATION,
            issued_on=issued_on,
            issued_by=issued_by,
            maintenance_authorisation=maintenance_authorisation,
            scope_confirmed=scope_confirmed,
            general_verification=general_verification,
            work_package=package,
        )
        for work in works[1:]:
            programme_services.record_release(
                work, release.reference, release.work.release_recorded_on
            )
    except (programme_services.RefusedError, release_services.RefusedError) as error:
        raise RefusedError(str(error)) from error
    package.release = release
    package.released_on = issued_on
    package.verification = verification
    package.save(update_fields=["release", "released_on", "verification"])


def _record_card_work(package: WorkPackage, card: WorkCard) -> WorkDone:
    if card.completed_on is None or card.hours is None or card.cycles is None:
        raise RefusedError("Signed Work and Its Counter Readings Are Needed")
    try:
        if card.directive is not None:
            linked = directive_services.record_compliance(
                card.directive,
                method=card.title,
                dated=card.completed_on,
                hours=card.hours,
                cycles=card.cycles,
                performed_by=card.performed_by,
                historical=True,
            )
            work = linked.work
        else:
            work = programme_services.record_work(
                package.aircraft,
                description=card.title,
                dated=card.completed_on,
                hours=card.hours,
                cycles=card.cycles,
                performed_by=card.performed_by,
                historical=True,
                task=card.task,
            )
    except (programme_services.RefusedError, directive_services.RefusedError) as error:
        raise RefusedError(str(error)) from error
    card.work = work
    card.save(update_fields=["work"])
    return work
