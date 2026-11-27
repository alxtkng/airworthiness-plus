"""Work package transitions and the hand-off to the aircraft records."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import transaction

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
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Task, WorkDone
from airworthiness_plus.releases import services as release_services
from airworthiness_plus.releases.models import IssuedBy
from airworthiness_rules.intervals import TaskKind


class RefusedError(ValueError):
    """The requested transition lacks the necessary evidence."""


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
    return WorkCard.objects.create(
        organisation_id=package.organisation_id,
        package=package,
        title=title,
        data_set=data_set,
        instruction=instruction,
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
def issue_package(package: WorkPackage) -> None:
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
        card.revision = revision
        card.issue_check_due = data_set.check_due
        card.save(update_fields=["revision", "issue_check_due"])
    package.issued_on = today
    package.save(update_fields=["issued_on"])


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
    qualification, evidence = qualification.strip(), evidence.strip()
    if not qualification or not evidence:
        raise RefusedError("Give Evidence of Qualification and Satisfactory Independent Inspection")
    card.inspector = inspector
    card.inspected_on = inspected_on
    card.qualification = qualification
    card.inspection_evidence = evidence
    card.save(update_fields=["inspector", "inspected_on", "qualification", "inspection_evidence"])


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
) -> None:
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
