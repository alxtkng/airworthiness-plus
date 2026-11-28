"""Maintenance-authorised substitutes tied to an issued work card and traced lot."""

from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import F, Q, QuerySet

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.permissions import ActionRefusedError
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics import allocations, stores
from airworthiness_plus.logistics.models import PostingKind, StockPosting, StockSubstitution
from airworthiness_plus.logistics.services import RefusedError
from airworthiness_plus.people.models import MaintenanceAuthorisation, StaffGroup
from airworthiness_plus.planning.models import WorkCard

SCOPE = "Part substitution approval for "


def authorisations(user: User, on: date) -> QuerySet[MaintenanceAuthorisation]:
    return (
        MaintenanceAuthorisation.objects.filter(
            organisation_id=user.organisation_id,
            person__user=user,
            person__staff_group=StaffGroup.CERTIFYING,
            valid_from__lte=on,
            scope__istartswith=SCOPE,
        )
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=on))
        .exclude(withdrawal__withdrawn_from__lte=on)
        .select_related("person")
    )


@transaction.atomic
def approve(
    user: User,
    posting: StockPosting,
    *,
    request_id: UUID,
    card: WorkCard,
    authorisation: MaintenanceAuthorisation,
    required_identity: str,
    applicable_source: str,
    evidence: str,
    scope_confirmed: bool,
) -> StockSubstitution:
    if not user.is_active or not user.may(Action.RECORD_RELEASE_CERTIFICATE):
        raise ActionRefusedError(Action.RECORD_RELEASE_CERTIFICATE)
    organisation = user.organisation_id
    if any(row.organisation_id != organisation for row in (posting, card, authorisation)):
        raise RefusedError("Choose Records of This Organisation")
    day = aircraft_services.today()
    stores._lock(f"stores-substitution:{organisation}:{request_id}")
    stores._lock_stock(posting)
    existing = StockSubstitution.objects.filter(
        organisation_id=organisation, submission=request_id
    ).first()
    required_identity = required_identity.strip().upper()
    applicable_source = applicable_source.strip()
    evidence = evidence.strip()
    if existing is not None:
        if (
            existing.posting_id == posting.pk
            and existing.card_id == card.pk
            and existing.authorisation_id == authorisation.pk
            and existing.authorisation.person.user_id == user.pk
            and existing.required_identity == required_identity
            and existing.applicable_source == applicable_source
            and existing.evidence == evidence
            and scope_confirmed
        ):
            return existing
        raise RefusedError("This Submission Was Already Used for Different Approval Evidence")
    scope = SCOPE + card.package.aircraft.registration
    if (
        not scope_confirmed
        or not authorisations(user, day)
        .filter(
            pk=authorisation.pk,
            scope__iexact=scope,
        )
        .exists()
    ):
        raise RefusedError("Confirm a Current Certifying Authorisation That Names This Aircraft")
    card = allocations.check_eligible_work(card, day)
    if card.revision is None or not card.revision.current:
        raise RefusedError("The Issued Work Card Revision Is No Longer Current")
    basis = posting.evidence
    alternate = (basis.part_number or basis.specification).strip().upper()
    if posting.kind != PostingKind.STOCK or posting.posted_on > day or not alternate:
        raise RefusedError("Choose a Posted Stock Lot With a Traceable Identity")
    if (
        not required_identity
        or required_identity == alternate
        or not applicable_source
        or not evidence
    ):
        raise RefusedError(
            "Record a Different Required Identity, Applicable Parts Data and Evidence"
        )
    try:
        with transaction.atomic():
            return StockSubstitution.objects.create(
                organisation_id=organisation,
                posting=posting,
                card=card,
                revision=card.revision,
                authorisation=authorisation,
                required_identity=required_identity,
                substitute_identity=alternate,
                applicable_source=applicable_source,
                evidence=evidence,
                scope_confirmed=True,
                recorded_on=day,
                submission=request_id,
            )
    except IntegrityError as error:
        raise RefusedError(
            "The Work Card, Lot or Authorisation Changed. Review the Approval Again."
        ) from error


def available(posting: StockPosting, on: date) -> QuerySet[StockSubstitution]:
    """Only present approvals that still apply to the issued work and dated grant."""
    return (
        posting.substitutions.filter(
            recorded_on__lte=on,
            revision__current=True,
            card__revision_id=F("revision_id"),
            card__completed_on__isnull=True,
            card__package__issued_on__lte=on,
            card__package__released_on__isnull=True,
            card__package__order__agreed_on__lte=on,
            card__package__order__closed_on__isnull=True,
            authorisation__valid_from__lte=on,
        )
        .filter(Q(authorisation__valid_to__isnull=True) | Q(authorisation__valid_to__gte=on))
        .exclude(authorisation__withdrawal__withdrawn_from__lte=on)
        .select_related(
            "card__package", "revision", "authorisation__person", "authorisation__withdrawal"
        )
    )
