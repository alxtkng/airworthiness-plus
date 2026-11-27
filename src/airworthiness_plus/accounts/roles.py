"""Roles and the role matrix (REQ-006, REQ-007).

Write access is by role (CAP 562 C-90). The matrix below is the only place
that says which role may take which action. It is recorded in
``design-system/Decisions.md``, Roles and Permissions, and a test fails
the build if the two differ.

A user may hold more than one role, as a person may hold more than one
function. An action is permitted if any role the user holds permits it.
"""

from collections.abc import Iterable
from enum import Enum

from django.db import models


class Role(models.TextChoices):
    """The roles in the private beta slice (REQ-007)."""

    ADMINISTRATOR = "Administrator", "Administrator"
    CONTINUING_AIRWORTHINESS_MANAGER = (
        "Continuing Airworthiness Manager",
        "Continuing Airworthiness Manager",
    )
    AIRWORTHINESS_REVIEW_STAFF = "Airworthiness Review Staff", "Airworthiness Review Staff"
    PLANNING_AND_RECORDS = "Planning and Records", "Planning and Records"
    READ_ONLY = "Read Only", "Read Only"


class Action(Enum):
    """Everything a user can do in the slice. The value is the name shown."""

    VIEW_RECORDS = "View Records"
    EXPORT_RECORDS = "Export Records"
    MANAGE_USERS_AND_ROLES = "Manage Users and Roles"
    CHANGE_ORGANISATION_RECORD = "Change Organisation Record"
    ADD_OR_CHANGE_PERSON = "Add or Change Person"
    ADD_OR_CHANGE_AIRCRAFT = "Add or Change Aircraft"
    ADD_OR_CHANGE_CUSTOMER = "Add or Change Customer"
    ENTER_UTILISATION = "Enter Utilisation"
    CHANGE_MAINTENANCE_PROGRAMME = "Change Maintenance Programme"
    RECORD_MAINTENANCE_PROGRAMME_REVIEW = "Record Maintenance Programme Review"
    RECORD_ACCOMPLISHMENT = "Record Accomplishment"
    RECORD_DEFECT = "Record Defect"
    RECORD_REPEAT_DEFECT_ACTION = "Record Repeat Defect Action"
    DRAW_UP_OR_END_CONTRACT = "Draw Up or End Contract"
    RECORD_WORK_ORDER = "Record Work Order"
    RECORD_RELEASE_CERTIFICATE = "Record Certificate of Release to Service"
    RECORD_AIRCRAFT_CONFIGURATION = "Record Aircraft Configuration"
    SIGN_CONFIGURATION_BASELINE = "Sign Configuration Baseline"
    RECORD_AIRWORTHINESS_DIRECTIVE = "Record Airworthiness Directive"
    DECIDE_DIRECTIVE_APPLICABILITY = "Decide Directive Applicability"
    RECORD_DIRECTIVE_COMPLIANCE = "Record Directive Compliance"
    RECORD_MAINTENANCE_DATA = "Record Maintenance Data"
    RECORD_AMENDMENT_CHECK = "Record Amendment Check"
    CARRY_OUT_AIRWORTHINESS_REVIEW = "Carry Out Airworthiness Review"
    ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE = "Issue Airworthiness Review Certificate"
    EXTEND_AIRWORTHINESS_REVIEW_CERTIFICATE = "Extend Airworthiness Review Certificate"
    RECORD_COPY_SENT_TO_THE_AUTHORITY = "Record Copy Sent to the Civil Aviation Authority"
    ADD_TO_PROBLEM_LOG = "Add to Problem Log"
    IMPORT_RECORDS = "Import Records"
    CHECK_IMPORTED_RECORDS = "Check Imported Records"


_ADMINISTRATOR = Role.ADMINISTRATOR
_MANAGER = Role.CONTINUING_AIRWORTHINESS_MANAGER
_REVIEW = Role.AIRWORTHINESS_REVIEW_STAFF
_RECORDS = Role.PLANNING_AND_RECORDS
_READ_ONLY = Role.READ_ONLY

MATRIX: dict[Action, frozenset[Role]] = {
    Action.VIEW_RECORDS: frozenset({_ADMINISTRATOR, _MANAGER, _REVIEW, _RECORDS, _READ_ONLY}),
    Action.EXPORT_RECORDS: frozenset({_ADMINISTRATOR, _MANAGER, _REVIEW, _RECORDS}),
    Action.MANAGE_USERS_AND_ROLES: frozenset({_ADMINISTRATOR}),
    Action.CHANGE_ORGANISATION_RECORD: frozenset({_ADMINISTRATOR}),
    Action.ADD_OR_CHANGE_PERSON: frozenset({_ADMINISTRATOR}),
    Action.ADD_OR_CHANGE_AIRCRAFT: frozenset({_MANAGER, _RECORDS}),
    Action.ADD_OR_CHANGE_CUSTOMER: frozenset({_MANAGER, _RECORDS}),
    Action.ENTER_UTILISATION: frozenset({_MANAGER, _RECORDS}),
    Action.CHANGE_MAINTENANCE_PROGRAMME: frozenset({_MANAGER}),
    Action.RECORD_MAINTENANCE_PROGRAMME_REVIEW: frozenset({_MANAGER, _REVIEW}),
    Action.RECORD_ACCOMPLISHMENT: frozenset({_MANAGER, _RECORDS}),
    Action.RECORD_DEFECT: frozenset({_MANAGER, _RECORDS}),
    Action.RECORD_REPEAT_DEFECT_ACTION: frozenset({_MANAGER}),
    Action.DRAW_UP_OR_END_CONTRACT: frozenset({_MANAGER}),
    Action.RECORD_WORK_ORDER: frozenset({_MANAGER, _RECORDS}),
    Action.RECORD_RELEASE_CERTIFICATE: frozenset({_MANAGER, _RECORDS}),
    Action.RECORD_AIRCRAFT_CONFIGURATION: frozenset({_MANAGER, _RECORDS}),
    Action.SIGN_CONFIGURATION_BASELINE: frozenset({_MANAGER}),
    Action.RECORD_AIRWORTHINESS_DIRECTIVE: frozenset({_MANAGER, _RECORDS}),
    Action.DECIDE_DIRECTIVE_APPLICABILITY: frozenset({_MANAGER}),
    Action.RECORD_DIRECTIVE_COMPLIANCE: frozenset({_MANAGER, _RECORDS}),
    Action.RECORD_MAINTENANCE_DATA: frozenset({_MANAGER, _RECORDS}),
    Action.RECORD_AMENDMENT_CHECK: frozenset({_MANAGER, _RECORDS}),
    Action.CARRY_OUT_AIRWORTHINESS_REVIEW: frozenset({_REVIEW}),
    Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE: frozenset({_REVIEW}),
    Action.EXTEND_AIRWORTHINESS_REVIEW_CERTIFICATE: frozenset({_MANAGER, _REVIEW}),
    Action.RECORD_COPY_SENT_TO_THE_AUTHORITY: frozenset({_MANAGER, _REVIEW, _RECORDS}),
    Action.ADD_TO_PROBLEM_LOG: frozenset({_ADMINISTRATOR, _MANAGER, _REVIEW, _RECORDS}),
    Action.IMPORT_RECORDS: frozenset({_MANAGER}),
    Action.CHECK_IMPORTED_RECORDS: frozenset({_MANAGER, _REVIEW, _RECORDS}),
}


def permitted(roles: Iterable[str], action: Action) -> bool:
    """Return whether any of ``roles`` permits ``action``.

    An action missing from the matrix, a role that is not a role, and a
    user with no role are all refused.
    """
    allowed = MATRIX.get(action, frozenset())
    return any(role in allowed for role in roles)
