"""Set up a new organisation and its first user.

The application's own database role cannot create an organisation: this is
run by Airworthiness Limited with the credentials used for migrations, once
for each organisation. After it, only the organisation's own users enter
or change its data (REQ-004, AMC1 CAO.A.100(f) point (d)(2)).
"""

import uuid
from collections.abc import Sequence

from django.contrib.auth.password_validation import validate_password

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import ApprovalType, Organisation, Privilege


def provision_organisation(
    *,
    name: str,
    approval_reference: str,
    privileges: Sequence[Privilege],
    scope_of_work: str,
    first_user_username: str,
    first_user_full_name: str,
    first_user_password: str | None = None,
) -> tuple[Organisation, User]:
    """Create the organisation and one Administrator, who can then add the others.

    With no password the Administrator cannot sign in until one is set.
    """
    if first_user_password is not None:
        validate_password(first_user_password)
    identifier = uuid.uuid4()
    with working_for(identifier):
        organisation = Organisation.objects.create(
            id=identifier,
            name=name,
            approval_type=ApprovalType.PART_CAO,
            approval_reference=approval_reference,
            privileges=list(privileges),
            scope_of_work=scope_of_work,
        )
        user = User.objects.create_user(
            organisation=organisation,
            username=first_user_username,
            full_name=first_user_full_name,
            roles=[Role.ADMINISTRATOR],
            password=first_user_password,
        )
    return organisation, user
