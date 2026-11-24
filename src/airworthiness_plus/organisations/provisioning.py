"""Set up a new organisation and its first user.

The application's own database role cannot create an organisation: this is
run by Airworthiness Limited with the credentials used for migrations, once
for each organisation. After it, only the organisation's own users enter
or change its data (REQ-004, AMC1 CAO.A.100(f) point (d)(2)).
"""

import uuid
from collections.abc import Sequence

from django.contrib.auth.password_validation import validate_password

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import (
    Approval,
    ApprovalType,
    Organisation,
    Privilege,
)


def provision_organisation(
    *,
    name: str,
    approval_reference: str,
    privileges: Sequence[Privilege],
    scope_of_work: str,
    first_user_username: str,
    first_user_full_name: str,
    first_user_password: str | None = None,
    address: str = "",
    approval_type: ApprovalType = ApprovalType.PART_CAO,
    other_approvals: Sequence[tuple[ApprovalType, str]] = (),
) -> tuple[Organisation, User]:
    """Create the organisation and one Administrator, who can then add the others.

    With no password the Administrator cannot sign in until one is set. A
    password given here is a first password, as on the Users page: it is
    changed at the first sign-in, before any page answers, and is good for
    7 days. Whoever typed it, or can read it where it was kept, knows it
    only until then (independent review of 20 November 2026, finding 8).

    ``approval_type`` and ``approval_reference`` are the approval the
    organisation is set up with; ``other_approvals`` are any others it
    holds, each with its reference. Every one is recorded (REQ-200).
    """
    if first_user_password is not None:
        validate_password(first_user_password)
    identifier = uuid.uuid4()
    with working_for(identifier):
        organisation = Organisation.objects.create(
            id=identifier,
            name=name,
            approval_type=approval_type,
            approval_reference=approval_reference,
            address=address,
            privileges=list(privileges),
            scope_of_work=scope_of_work,
        )
        for approval, reference in ((approval_type, approval_reference), *other_approvals):
            Approval.objects.create(
                organisation=organisation, approval=approval, reference=reference
            )
        user = User.objects.create_user(
            organisation=organisation,
            username=first_user_username,
            full_name=first_user_full_name,
            roles=[Role.ADMINISTRATOR],
            password=first_user_password,
            password_must_change=first_user_password is not None,
            first_password_set_on=sign_in.today() if first_user_password is not None else None,
        )
    return organisation, user
