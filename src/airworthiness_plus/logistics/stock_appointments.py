"""Dated authority for the new maintenance custody actions."""

from datetime import date
from uuid import UUID

from django.db import connection, transaction
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.models import StockAppointment, StockAppointmentWithdrawal
from airworthiness_plus.logistics.services import RefusedError, maintenance_approvals
from airworthiness_plus.organisations.models import Approval
from airworthiness_plus.people.models import Person


def lock_submission(scope: str, submission: UUID) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT logistics_lock_stock(%s, %s)", [scope, submission])


def current(user: User, action: str, day: date) -> StockAppointment | None:
    if not user.is_active or not user.may(Action.MOVE_STOCK):
        return None
    return (
        StockAppointment.objects.filter(
            organisation_id=user.organisation_id,
            approval__in=maintenance_approvals(user.organisation, day),
            person__user=user,
            starts_on__lte=day,
            ends_on__gte=day,
            action=action,
        )
        .filter(Q(person__joined_on__isnull=True) | Q(person__joined_on__lte=day))
        .filter(Q(person__left_on__isnull=True) | Q(person__left_on__gte=day))
        .exclude(withdrawal__withdrawn_on__lte=day)
        .order_by("-starts_on", "-entered_at", "-pk")
        .first()
    )


@transaction.atomic
def appoint(
    user: User,
    *,
    request_id: UUID,
    person: Person,
    approval: Approval,
    action: str,
    starts_on: date,
    ends_on: date,
    evidence: str,
) -> StockAppointment:
    if not user.is_active or not user.may(Action.MANAGE_STORE_LOCATIONS):
        raise ActionRefusedError(Action.MANAGE_STORE_LOCATIONS)
    day = aircraft_services.today()
    lock_submission(f"stock-appointment:{user.organisation_id}", request_id)
    existing = StockAppointment.objects.filter(
        organisation_id=user.organisation_id,
        submission=request_id,
    ).first()
    evidence = evidence.strip()
    if existing is not None:
        if (
            existing.person_id,
            existing.approval_id,
            existing.action,
            existing.starts_on,
            existing.ends_on,
            existing.evidence,
        ) != (person.pk, approval.pk, action, starts_on, ends_on, evidence):
            raise RefusedError("This Submission Already Records a Different Appointment")
        return existing
    if (
        person.organisation_id != user.organisation_id
        or person.user_id is None
        or approval not in maintenance_approvals(user.organisation, day)
        or ends_on < max(starts_on, day)
        or not evidence
    ):
        raise RefusedError("Choose a Signed-In Person, Current Approval, Dates and Signed Evidence")
    return StockAppointment.objects.create(
        organisation_id=user.organisation_id,
        person=person,
        approval=approval,
        action=action,
        starts_on=starts_on,
        ends_on=ends_on,
        evidence=evidence,
        submission=request_id,
    )


@transaction.atomic
def withdraw(user: User, appointment: StockAppointment, evidence: str) -> None:
    if not user.is_active or not user.may(Action.MANAGE_STORE_LOCATIONS):
        raise ActionRefusedError(Action.MANAGE_STORE_LOCATIONS)
    lock_submission("stock-appointment-withdrawal", appointment.pk)
    if appointment.organisation_id != user.organisation_id or not evidence.strip():
        raise RefusedError("Choose an Appointment in This Organisation and Give the Evidence")
    StockAppointmentWithdrawal.objects.get_or_create(
        organisation_id=user.organisation_id,
        appointment=appointment,
        defaults={"withdrawn_on": aircraft_services.today(), "evidence": evidence.strip()},
    )
