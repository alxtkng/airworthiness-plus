"""The role matrix: every action against every role (REQ-006, REQ-007).

The expected answers are read from the record, design-system/Decisions.md,
Roles and Permissions, so the record and the code cannot drift apart. The
answers that matter most to airworthiness are also written out by hand
below.
"""

import importlib
import inspect
import pkgutil
from pathlib import Path

import pytest
from django.db import IntegrityError, transaction

import airworthiness_plus
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import MATRIX, Action, Role, permitted
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.interface import field_rules
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.organisations.models import Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from tests.conftest import as_owner

DECISIONS = Path(__file__).resolve().parent.parent / "design-system" / "Decisions.md"


def recorded_matrix() -> dict[tuple[str, str], bool]:
    """Return (action, role) -> permitted, as written in Decisions.md."""
    text = DECISIONS.read_text(encoding="utf-8")
    section = text.split("## Roles and Permissions", 1)[1].split("\n## ", 1)[0]
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.startswith("|") and not line.startswith("|---")
    ]
    header, body = rows[0], rows[1:]
    assert header[0] == "Action"
    found: dict[tuple[str, str], bool] = {}
    for row in body:
        for role, cell in zip(header[1:], row[1:], strict=True):
            assert cell in ("Yes", "No"), f"{row[0]}, {role}: {cell!r}"
            found[(row[0], role)] = cell == "Yes"
    return found


RECORDED = recorded_matrix()


def test_the_record_and_the_code_list_the_same_actions_and_roles() -> None:
    """REQ-006. One matrix: nothing in the code that is not in the record, or the reverse."""
    assert {action for action, _ in RECORDED} == {action.value for action in Action}
    assert {role for _, role in RECORDED} == set(Role.values)
    assert set(MATRIX) == set(Action)
    assert len(RECORDED) == len(Action) * len(Role) == 150


@pytest.mark.parametrize(("action", "role"), sorted(RECORDED))
def test_every_action_against_every_role(action: str, role: str) -> None:
    """REQ-006. Each of the 115 cells of the matrix in Decisions.md."""
    assert permitted([role], Action(action)) is RECORDED[(action, role)]


def test_only_airworthiness_review_staff_review_and_issue() -> None:
    """REQ-109, ML.A.903, CAO.A.045."""
    for action in (
        Action.CARRY_OUT_AIRWORTHINESS_REVIEW,
        Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE,
    ):
        assert MATRIX[action] == {Role.AIRWORTHINESS_REVIEW_STAFF}


def test_only_the_continuing_airworthiness_manager_decides_applicability() -> None:
    """Hazard H-002. A directive is not marked Not Applicable by a records entry."""
    assert MATRIX[Action.DECIDE_DIRECTIVE_APPLICABILITY] == {Role.CONTINUING_AIRWORTHINESS_MANAGER}
    assert MATRIX[Action.CHANGE_MAINTENANCE_PROGRAMME] == {Role.CONTINUING_AIRWORTHINESS_MANAGER}


def test_read_only_can_view_and_nothing_else() -> None:
    """REQ-007."""
    allowed = {action for action in Action if permitted([Role.READ_ONLY], action)}
    assert allowed == {Action.VIEW_RECORDS}


def test_the_administrator_does_not_change_airworthiness_records() -> None:
    """REQ-007. Users, people and the organisation record only, with viewing, export and
    the problem log."""
    allowed = {action for action in Action if permitted([Role.ADMINISTRATOR], action)}
    assert allowed == {
        Action.VIEW_RECORDS,
        Action.EXPORT_RECORDS,
        Action.MANAGE_USERS_AND_ROLES,
        Action.CHANGE_ORGANISATION_RECORD,
        Action.ADD_OR_CHANGE_PERSON,
        Action.ADD_TO_PROBLEM_LOG,
    }
    for role in Role:
        if role is not Role.ADMINISTRATOR:
            assert not permitted([role], Action.MANAGE_USERS_AND_ROLES)


def test_every_role_can_view() -> None:
    """REQ-007."""
    assert MATRIX[Action.VIEW_RECORDS] == set(Role)


def test_no_role_and_an_unknown_role_are_refused_everything() -> None:
    """REQ-006. An action outside the matrix is refused."""
    for action in Action:
        assert not permitted([], action)
        assert not permitted(["Superuser"], action)
        assert not permitted(["administrator"], action)


def test_two_roles_give_what_either_gives() -> None:
    """REQ-007. SampleData.md, People: Lucy Grant holds two functions."""
    lucy = [Role.AIRWORTHINESS_REVIEW_STAFF, Role.CONTINUING_AIRWORTHINESS_MANAGER]
    assert permitted(lucy, Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE)
    assert permitted(lucy, Action.DECIDE_DIRECTIVE_APPLICABILITY)
    assert not permitted(lucy, Action.MANAGE_USERS_AND_ROLES)


@pytest.fixture
def lucy() -> User:
    with as_owner():
        _, user = provision_organisation(
            name="[Your Organisation]",
            approval_reference="UK.CAO.[Number]",
            privileges=list(Privilege),
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username="lucy.grant@your-organisation.example",
            first_user_full_name="Lucy Grant",
        )
    return user


@pytest.mark.django_db
def test_the_first_user_of_an_organisation_is_its_administrator(lucy: User) -> None:
    """REQ-004, REQ-007. Set up once; the Administrator then adds the others."""
    assert lucy.roles == [Role.ADMINISTRATOR]
    assert lucy.may(Action.MANAGE_USERS_AND_ROLES)
    assert not lucy.may(Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE)


@pytest.mark.django_db
def test_an_inactive_user_may_do_nothing(lucy: User) -> None:
    """REQ-010."""
    lucy.is_active = False
    for action in Action:
        assert not lucy.may(action)


@pytest.mark.django_db
def test_a_change_of_role_is_in_the_history(lucy: User) -> None:
    """REQ-009. Who changed the roles, when, and what they were before and after."""
    with working_for(lucy.organisation_id, lucy.id):
        User.objects.filter(pk=lucy.pk).update(
            roles=[Role.ADMINISTRATOR, Role.AIRWORTHINESS_REVIEW_STAFF]
        )
        entry = Event.of(lucy).last()
    assert entry is not None
    assert (entry.action, entry.changed) == ("Changed", ["roles"])
    assert (entry.actor_id, entry.actor_name) == (lucy.id, "Lucy Grant")
    assert entry.before_json is not None
    assert entry.after_json is not None
    assert '"roles": ["Administrator"]' in entry.before_json
    assert '"roles": ["Administrator", "Airworthiness Review Staff"]' in entry.after_json


@pytest.mark.django_db
def test_a_role_that_is_not_in_the_matrix_cannot_be_stored(lucy: User) -> None:
    """REQ-006. The database refuses a role the matrix does not know."""
    with (
        working_for(lucy.organisation_id, lucy.id),
        pytest.raises(IntegrityError, match="user_has_known_roles"),
        transaction.atomic(),
    ):
        User.objects.filter(pk=lucy.pk).update(roles=["Superuser"])


# What each action may set (OWASP ASVS 5.0, 8.1.2)


def test_every_address_is_written_down_as_one_that_reads_or_one_that_sets() -> None:
    """REQ-006. A new address cannot be added without saying what it may set."""
    names = {str(pattern.name) for pattern in field_rules.patterns()}
    assert set(field_rules.WRITES) & field_rules.READS == set()
    assert set(field_rules.WRITES) | field_rules.READS == names


def test_every_address_that_sets_something_needs_an_action_or_is_named_as_open() -> None:
    """REQ-006. The action is read from the address itself, not written twice."""
    rules = {rule.name: rule for rule in field_rules.rules()}
    assert set(rules) == set(field_rules.WRITES)
    without = {name for name, rule in rules.items() if rule.action is None}
    assert without == set(field_rules.WITHOUT_AN_ACTION)
    for pattern in field_rules.patterns():
        if pattern.name in field_rules.READS:
            assert isinstance(pattern.callback.action, Action), pattern.name  # type: ignore[attr-defined]
    assert rules["issue_certificate"].action == Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE
    assert rules["issue_certificate"].who == "Airworthiness Review Staff"


def test_every_form_belongs_to_an_address_that_sets_something() -> None:
    """REQ-006. A new form, and a new field on a form, reach the document by themselves."""
    used = {one for sets in field_rules.WRITES.values() for one in sets if not isinstance(one, str)}
    declared = set()
    for module in pkgutil.walk_packages(airworthiness_plus.__path__, "airworthiness_plus."):
        if ".migrations" in module.name or ".management" in module.name:
            continue
        for value in vars(importlib.import_module(module.name)).values():
            if (
                inspect.isclass(value)
                and issubclass(value, Form)
                and value is not Form
                and value.__module__ == module.name
            ):
                declared.add(value)
    assert declared == used
    add_user = next(rule for rule in field_rules.rules() if rule.name == "add_user")
    assert add_user.sets == (
        "Person Already Recorded, With No Sign-In",
        "Full Name of a New Person",
        "User Name",
        "Roles",
        "Code From the Administrator's Authenticator Application",
    )


def test_the_document_is_what_the_code_says() -> None:
    """OWASP ASVS 5.0, 8.1.2. The table is made by ``python manage.py field_rules``."""
    written = Path(__file__).parent.parent / "architecture" / "fields-by-action.md"
    assert field_rules.written_table(written.read_text()) == field_rules.table()
    assert field_rules.with_table(written.read_text()) == written.read_text()
