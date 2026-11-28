"""Preview and archive one synthetic work-card completion attestation."""

import hashlib
import json
from typing import Any

from django.conf import settings
from django.contrib.auth import HASH_SESSION_KEY
from django.contrib.sessions.backends.base import SessionBase
from django.core import signing
from django.db import transaction

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.middleware import recent_verification
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person, StaffGroup
from airworthiness_plus.planning.models import WorkCard, WorkCardAttestation, WorkPackage
from airworthiness_plus.planning.services import RefusedError, _person_on

POLICY = "synthetic-work-card-completion-1"
CONSENT = "I attest to the recorded completion shown on this synthetic work card."
SALT = "planning.work-card-attestation"


def available(package: WorkPackage) -> bool:
    return settings.SYNTHETIC_WORK_CARD_ATTESTATION and package.reference.startswith(
        "WP-SYNTHETIC-"
    )


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _scope(card: WorkCard) -> str:
    return MaintenanceAuthorisation.SYNTHETIC_COMPLETION_SCOPE + card.package.aircraft.type_rating


def preview(
    card: WorkCard, actor: User, *, lock: bool = False
) -> tuple[dict[str, Any], MaintenanceAuthorisation]:
    if not available(card.package) or not actor.may(Action.RECORD_WORK_CARD):
        raise RefusedError("Synthetic Attestation Is Unavailable")
    if (
        card.completed_on is None
        or card.revision is None
        or card.performed_revision is None
        or card.performed_by_id is None
        or actor.organisation_id != card.organisation_id
    ):
        raise RefusedError("Only the Named Performer May Attest to Recorded Completion")
    today = aircraft_services.today()
    people = Person.objects.select_for_update() if lock else Person.objects
    person = people.get(pk=card.performed_by_id)
    if person.user_id != actor.pk:
        raise RefusedError("Only the Named Performer May Attest to Recorded Completion")
    _person_on(person, card.package, today)
    scope = _scope(card)
    grants = MaintenanceAuthorisation.objects.filter(person=person, scope=scope).select_related(
        "withdrawal"
    )
    grant = next(
        (grant for grant in grants if grant.term_on(today) == "Within Recorded Dates"), None
    )
    if person.staff_group != StaffGroup.CERTIFYING or grant is None:
        raise RefusedError("No Current Synthetic Authorisation Covers This Task and Aircraft Type")
    version = Event.of(card).last()
    if version is None:
        raise RefusedError("The Work Card Version Could Not Be Established")
    content = {
        "policy": POLICY,
        "consent": CONSENT,
        "card_id": str(card.pk),
        "card_version": version.sequence,
        "card_version_hash": version.hash,
        "work_package": card.package.reference,
        "aircraft_id": str(card.package.aircraft_id),
        "aircraft_registration": card.package.aircraft.registration,
        "aircraft_type": card.package.aircraft.type_rating,
        "task": card.title,
        "instruction": card.instruction,
        "issued_revision_id": str(card.revision_id),
        "issued_revision": card.revision.revision,
        "used_revision_id": str(card.performed_revision_id),
        "used_revision": card.performed_revision.revision,
        "completed_on": card.completed_on.isoformat(),
        "source_evidence": card.sign_off_reference,
        "hours": str(card.hours),
        "cycles": card.cycles,
        "inspection_status": (
            "Recorded" if card.inspected_on else "Pending" if card.critical else "Not Required"
        ),
        "performer_id": str(person.pk),
        "actor_id": str(actor.pk),
        "actor_name": person.full_name,
        "authorisation_id": str(grant.pk),
        "authorisation_reference": grant.reference,
        "authorisation_scope": grant.scope,
        "authorisation_valid_from": grant.valid_from.isoformat(),
        "authorisation_valid_to": grant.valid_to.isoformat() if grant.valid_to else None,
    }
    return content, grant


def intent(content: dict[str, Any]) -> str:
    return signing.dumps(_digest(_json(content)), salt=SALT)


@transaction.atomic
def attest(card: WorkCard, actor: User, token: str, session: SessionBase) -> WorkCardAttestation:
    actor = User.objects.select_for_update().get(pk=actor.pk)
    # Package changes and card evidence use the same package lock.
    WorkPackage.objects.select_for_update().get(pk=card.package_id)
    card = WorkCard.objects.get(pk=card.pk)
    verified_at = recent_verification(session)
    if (
        verified_at is None
        or actor.password_must_change
        or session.get(HASH_SESSION_KEY) != actor.get_session_auth_hash()
    ):
        raise RefusedError("Verify Your Identity Before Attesting")
    content, grant = preview(card, actor, lock=True)
    try:
        reviewed = signing.loads(token, salt=SALT, max_age=600)
    except signing.BadSignature as error:
        raise RefusedError("Review the Current Work Card Before Attesting") from error
    if reviewed != _digest(_json(content)):
        raise RefusedError("The Evidence Has Changed. Review the Current Work Card")
    prior = WorkCardAttestation.objects.filter(card=card).first()
    if prior is not None:
        if json.loads(prior.evidence)["reviewed_content"] != content:
            raise RefusedError("The Work Card Already Has an Archived Synthetic Attestation")
        return prior
    evidence = _json(
        {
            "reviewed_content": content,
            "attested_at": sign_in.current_time().isoformat(),
            "verified_at": verified_at.isoformat(),
        }
    )
    return WorkCardAttestation.objects.create(
        organisation_id=card.organisation_id,
        card=card,
        actor=actor,
        authorisation=grant,
        evidence=evidence,
        sha256=_digest(evidence),
    )
