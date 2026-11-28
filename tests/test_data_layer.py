"""Tests that try to break the record rules directly against the database.

Organisation scoping (REQ-002, REQ-003, REQ-004; threat TH-020) and the
append-only history (REQ-130, REQ-131; threats TH-021, TH-022, TH-025) are
enforced by PostgreSQL. These tests go underneath the application: raw SQL
as the application's database role, and as the owner of the tables.

The organisation and people are from design-system/SampleData.md. The
second organisation is a placeholder that exists only to be kept out.
"""

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from django.apps import apps
from django.db import DatabaseError, IntegrityError, connection, transaction

from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import (
    HASH_ALGORITHM,
    Event,
    Record,
    RecordsAreNeverDeletedError,
)
from airworthiness_plus.history.session import _current, _set, working_for
from airworthiness_plus.history.sql import APPLICATION_ROLE, protect_record_table
from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from tests.conftest import as_owner

pytestmark = pytest.mark.django_db

SCOPE = (
    "Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less; Sailplanes and Powered "
    "Sailplanes (management and review only); Piston Engines, Lycoming and Continental; "
    "C14 Landing Gear; C16 Propellers"
)

# Tables Django itself creates. They hold no records and the application
# role has no access to them at all.
FRAMEWORK_TABLES = {
    "django_migrations",
    "django_content_type",
    "django_session",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
}


@dataclass(frozen=True)
class Two:
    """The sample organisation with one user, and another organisation with one user."""

    ours: Organisation
    lucy: User
    other: Organisation
    stranger: User


@pytest.fixture
def two() -> Two:
    with as_owner():
        ours, lucy = provision_organisation(
            name="[Your Organisation]",
            approval_reference="UK.CAO.[Number]",
            privileges=list(Privilege),
            scope_of_work=SCOPE,
            first_user_username="lucy.grant@your-organisation.example",
            first_user_full_name="Lucy Grant",
        )
        other, stranger = provision_organisation(
            name="[Other Organisation]",
            approval_reference="UK.CAO.[Other Number]",
            privileges=[Privilege.CONTINUING_AIRWORTHINESS_MANAGEMENT],
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username="name@other-organisation.example",
            first_user_full_name="[Other Name]",
        )
    return Two(ours, lucy, other, stranger)


@contextmanager
def refused(message: str) -> Iterator[None]:
    """Expect the database to refuse, and keep the test's transaction usable."""
    with pytest.raises(DatabaseError, match=message), transaction.atomic():
        yield


Value = str | int | uuid.UUID


def run(sql: str, *parameters: Value) -> int:
    """Run raw SQL on the application's connection and return the number of rows touched."""
    with connection.cursor() as cursor:
        cursor.execute(sql, parameters)
        return int(cursor.rowcount)


def one(sql: str, *parameters: Value) -> object:
    with connection.cursor() as cursor:
        cursor.execute(sql, parameters)
        row = cursor.fetchone()
    assert row is not None
    return row[0]


def add_chris(two: Two) -> User:
    """Lucy Grant adds Chris Moore to the sample organisation."""
    with working_for(two.ours.id, two.lucy.id):
        return User.objects.create_user(
            organisation=two.ours,
            username="chris.moore@your-organisation.example",
            full_name="Chris Moore",
        )


# The application's database role


def test_the_application_role_has_no_special_powers() -> None:
    """Threats TH-020, TH-024. Not a superuser, cannot bypass row-level security,
    cannot sign in by itself, and owns no table."""
    assert one("SELECT current_user") == APPLICATION_ROLE
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT rolsuper, rolbypassrls, rolcanlogin, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname = %s",
            [APPLICATION_ROLE],
        )
        assert cursor.fetchone() == (False, False, False, False, False)
    assert one("SELECT count(*) FROM pg_tables WHERE tableowner = %s", APPLICATION_ROLE) == 0


def test_the_application_role_can_make_nothing_of_its_own() -> None:
    """Threat TH-026. No table, temporary table, function or trigger of its own,
    so it cannot build a way round the history."""
    assert one("SELECT has_schema_privilege(current_user, current_schema(), 'CREATE')") is False
    assert one("SELECT has_database_privilege(current_user, current_database(), 'TEMP')") is False
    assert one("SELECT has_database_privilege(current_user, current_database(), 'CREATE')") is False
    with refused("permission denied"):
        run("CREATE TEMPORARY TABLE planted (id integer)")
    with refused("permission denied"):
        run("CREATE TABLE planted (id integer)")
    with refused("permission denied"):
        run("CREATE FUNCTION planted() RETURNS integer LANGUAGE sql AS 'SELECT 1'")
    with refused("must be owner"):
        run("ALTER TABLE accounts_user DISABLE TRIGGER history_write")
    with refused("must be owner"):
        run("ALTER TABLE accounts_user DISABLE ROW LEVEL SECURITY")
    with refused("permission denied"):
        run("SET session_replication_role = replica")


def test_every_table_is_under_the_record_rules() -> None:
    """REQ-002, REQ-003, REQ-131. The build fails if a table is added without
    row-level security, the history trigger and the refusal of deletion, or
    if the application is given more than it needs on any table."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity, "
            "  ARRAY(SELECT polname::text FROM pg_policy WHERE polrelid = c.oid ORDER BY 1), "
            "  ARRAY(SELECT tgname::text FROM pg_trigger "
            "         WHERE tgrelid = c.oid AND NOT tgisinternal ORDER BY 1), "
            "  ARRAY(SELECT p FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE',"
            "         'TRUNCATE','REFERENCES','TRIGGER']) AS p "
            "         WHERE has_table_privilege(%s, c.oid, p) ORDER BY 1) "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = current_schema() AND c.relkind = 'r' ORDER BY 1",
            [APPLICATION_ROLE],
        )
        tables = {row[0]: row[1:] for row in cursor.fetchall()}

    assert FRAMEWORK_TABLES <= set(tables)
    for name in FRAMEWORK_TABLES - {"django_session"}:
        assert tables[name][4] == [], f"{name}: the application has no access"
    # Sessions are made and removed as users sign in and out. They are not records.
    assert tables["django_session"][4] == ["DELETE", "INSERT", "SELECT", "UPDATE"]

    # Every other table is a table of records. A new one needs no entry here
    # unless it is given less than, or something beyond, the usual.
    records = set(tables) - FRAMEWORK_TABLES - {"history_event", "accounts_accessentry"}
    assert {"organisations_organisation", "accounts_user", "aircraft_aircraft"} <= records
    usual = ["INSERT", "SELECT", "UPDATE"]
    privileges_expected = {
        # The application cannot create an organisation (REQ-004).
        "organisations_organisation": ["SELECT", "UPDATE"],
        # An entry of hours and cycles is added and never changed (REQ-025).
        "aircraft_utilisationentry": ["INSERT", "SELECT"],
        # Compliance with a directive is added and never changed (REQ-066).
        "directives_compliance": ["INSERT", "SELECT"],
        # A check of the amendment status is added and never changed (REQ-082).
        "maintenance_data_amendmentcheck": ["INSERT", "SELECT"],
        # An entry of the problem log and its notes are added and never changed (REQ-172).
        "acceptance_problem": ["INSERT", "SELECT"],
        "acceptance_problemnote": ["INSERT", "SELECT"],
        # A load, its values and their checks are added and never changed (REQ-170).
        "imports_load": ["INSERT", "SELECT"],
        "imports_loadedvalue": ["INSERT", "SELECT"],
        "imports_valuecheck": ["INSERT", "SELECT"],
        # That a part of the sample was added is recorded once and never changed (REQ-218).
        "sample_added": ["INSERT", "SELECT"],
        # What was done about a repeat defect is added and never changed (REQ-227).
        "defects_repeataction": ["INSERT", "SELECT"],
        "defects_aircraftdrawing": ["INSERT", "SELECT"],
        "defects_damageentry": ["INSERT", "SELECT"],
        "defects_flightevent": ["INSERT", "SELECT"],
        "defects_flightreport": ["INSERT", "SELECT"],
        "defects_flightreportrelease": ["INSERT", "SELECT"],
        # A certificate of release to service is added and never changed (REQ-261).
        "releases_release": ["INSERT", "SELECT"],
        "releases_historicalreleaseevidence": ["INSERT", "SELECT"],
        "people_maintenanceauthorisation": ["INSERT", "SELECT"],
        "people_maintenanceauthorisationwithdrawal": ["INSERT", "SELECT"],
        "people_experienceevidence": ["INSERT", "SELECT"],
        "people_experiencewithdrawal": ["INSERT", "SELECT"],
        "people_recurrenttraining": ["INSERT", "SELECT"],
        "planning_workcardattestation": ["INSERT", "SELECT"],
        "planning_workcardstepsignoff": ["INSERT", "SELECT"],
        # Supplier identities and their evaluation evidence are retained (REQ-343).
        "logistics_supplier": ["INSERT", "SELECT"],
        "logistics_supplierevaluation": ["INSERT", "SELECT"],
        "logistics_subcontractorassessment": ["INSERT", "SELECT"],
        "logistics_receipt": ["INSERT", "SELECT"],
        "logistics_receivingcheck": ["INSERT", "SELECT"],
        "logistics_receivingdisposition": ["INSERT", "SELECT"],
        "logistics_stockentry": ["SELECT"],
        # The Stores ledger is append-only. A location is withdrawn, never rewritten (REQ-358).
        "logistics_stockresolution": ["INSERT", "SELECT"],
        "logistics_stockposting": ["INSERT", "SELECT"],
        "logistics_stockcount": ["INSERT", "SELECT"],
        "logistics_stockmovement": ["INSERT", "SELECT"],
        "logistics_stockappointment": ["INSERT", "SELECT"],
        "logistics_stockappointmentwithdrawal": ["INSERT", "SELECT"],
        "logistics_stockallocation": ["INSERT", "SELECT"],
        "logistics_stocksubstitution": ["INSERT", "SELECT"],
        "tooling_workpackageapproval": ["INSERT", "SELECT"],
        "tooling_toolissue": ["INSERT", "SELECT"],
        "tooling_toolpreuseinspection": ["INSERT", "SELECT"],
        "tooling_tooluse": ["INSERT", "SELECT"],
        "tooling_toolreturn": ["INSERT", "SELECT"],
        "tooling_historicaltoolclaim": ["INSERT", "SELECT"],
        "tooling_releasegeneralverification": ["INSERT", "SELECT"],
        "tooling_tool": ["INSERT", "SELECT"],
        "tooling_toolserviceproviderauthorisation": ["INSERT", "SELECT"],
        "tooling_calibrationorder": ["INSERT", "SELECT"],
        "tooling_calibrationmovement": ["INSERT", "SELECT"],
        "tooling_calibrationcertificate": ["INSERT", "SELECT"],
        "tooling_calibrationresult": ["INSERT", "SELECT"],
        "tooling_certificatedecision": ["INSERT", "SELECT"],
        "tooling_toolimpactcase": ["SELECT"],
        "tooling_calibrationreinstatement": ["INSERT", "SELECT"],
        "tooling_toolcontrolrevision": ["INSERT", "SELECT"],
        "tooling_toolcontrolevent": ["INSERT", "SELECT"],
        "tooling_tooldelegation": ["INSERT", "SELECT"],
        "tooling_tooldelegationwithdrawal": ["INSERT", "SELECT"],
        "staffing_review": ["INSERT", "SELECT"],
        "staffing_report": ["INSERT", "SELECT"],
        "staffing_absence": ["INSERT", "SELECT"],
        "staffing_publishedroster": ["INSERT", "SELECT"],
        "staffing_publishedshift": ["INSERT", "SELECT"],
        "staffing_dispatchassignment": ["INSERT", "SELECT"],
        "staffing_dispatchwindow": ["INSERT", "SELECT"],
        # A transfer and a signed baseline are added and never changed (REQ-267, REQ-274).
        "configuration_transfer": ["INSERT", "SELECT"],
        "configuration_baseline": ["INSERT", "SELECT"],
        # A weighing and an issue of the weight schedule are added and never changed (REQ-254).
        "modifications_weighing": ["INSERT", "SELECT"],
        "modifications_weightschedule": ["INSERT", "SELECT"],
    }
    # While a user name is being checked at sign-in, that one user can be read.
    extra_policies = {"accounts_user": ["sign_in_lookup"]}
    extra_triggers = {
        "logistics_receipt": {"receipt_rules"},
        "logistics_receivingcheck": {"receiving_check_rules"},
        "logistics_receivingdisposition": {
            "receiving_disposition_rules",
            "receiving_disposition_verified_evidence",
            "stock_from_acceptance",
        },
        "logistics_stockentry": {"history_refuse_update", "stock_requires_acceptance"},
        "logistics_storelocation": {"keep_store_location_station", "store_location_rules"},
        "logistics_stockresolution": {"history_refuse_update", "stock_resolution_rules"},
        "logistics_stockposting": {
            "history_refuse_update",
            "stock_posting_rules",
            "stock_posting_intake",
        },
        "logistics_stockcount": {"history_refuse_update", "stock_count_rules"},
        "logistics_stockmovement": {
            "history_refuse_update",
            "stock_movement_rules",
            "stores_movement_reservations",
        },
        "logistics_stockappointment": {"history_refuse_update"},
        "logistics_stockappointmentwithdrawal": {"history_refuse_update"},
        "logistics_stockallocation": {"history_refuse_update", "stores_allocation_rules"},
        "logistics_stocksubstitution": {"history_refuse_update", "stores_stock_substitution_rules"},
        "tooling_tool": {"history_refuse_update", "tooling_tool_a_check_evidence"},
        "tooling_toolserviceproviderauthorisation": {
            "history_refuse_update",
            "calibration_link_rules",
        },
        "tooling_workpackageapproval": {"history_refuse_update", "tooling_custody_links"},
        "tooling_toolissue": {"history_refuse_update", "tooling_custody_links"},
        "tooling_toolpreuseinspection": {"history_refuse_update", "tooling_custody_links"},
        "tooling_tooluse": {"history_refuse_update", "tooling_custody_links"},
        "tooling_toolreturn": {"history_refuse_update", "tooling_custody_links"},
        "tooling_historicaltoolclaim": {"history_refuse_update", "tooling_custody_links"},
        "tooling_releasegeneralverification": {
            "history_refuse_update",
            "tooling_validate_release_verification",
        },
        "tooling_calibrationorder": {"history_refuse_update", "calibration_link_rules"},
        "tooling_calibrationmovement": {"history_refuse_update", "calibration_link_rules"},
        "tooling_calibrationcertificate": {"history_refuse_update", "calibration_link_rules"},
        "tooling_calibrationresult": {
            "history_refuse_update",
            "calibration_link_rules",
            "case_from_calibration_result",
        },
        "tooling_certificatedecision": {"history_refuse_update", "calibration_link_rules"},
        "tooling_toolimpactcase": {"history_refuse_update"},
        "tooling_calibrationreinstatement": {"history_refuse_update", "calibration_link_rules"},
        "tooling_toolcontrolrevision": {
            "history_refuse_update",
            "tooling_revision_a_check_evidence",
        },
        "tooling_toolcontrolevent": {"history_refuse_update", "tooling_event_a_check_evidence"},
        "tooling_tooldelegation": {"history_refuse_update"},
        "tooling_tooldelegationwithdrawal": {"history_refuse_update"},
        # The approval it was set up with is changed only by the owner (REQ-200).
        "organisations_organisation": {"serial_floor_guard", "set_up_approval_guard"},
        "organisations_approval": {"approval_guard"},
        # A sign-in keeps its person after every change (REQ-204).
        "people_person": {"sign_in_keeps_its_person"},
        # A sign-in belongs to a person (REQ-204).
        "accounts_user": {"user_has_a_person"},
        "aircraft_utilisationentry": {"utilisation_fits"},
        # Not made Serviceable while a defect that is Not Deferrable is open (REQ-221).
        # Nor moved to the Fleet with an item of its transfer checklist open (REQ-269).
        "aircraft_aircraft": {"open_defect_guard", "transfer_complete_guard"},
        # An item keeps its transfer; a position its aircraft; a baseline what it showed.
        "configuration_transferitem": {"transferitem_rules"},
        "configuration_position": {"position_rules"},
        "configuration_baseline": {"baseline_keeps"},
        # A defect keeps its decision and who made it (REQ-225).
        "defects_defect": {
            "defect_rules",
            "defect_certification_evidence",
            "defect_timing",
            "keep_ata_section",
            "defect_refuse_synthetic_certification",
        },
        # A contract and a work order keep what they said when recorded (REQ-241).
        "defects_aircraftdrawing": {"history_refuse_update", "validate_aircraft_record_links"},
        "defects_damageentry": {"history_refuse_update", "validate_aircraft_record_links"},
        "defects_flightevent": {"history_refuse_update"},
        "defects_flightreport": {"history_refuse_update", "validate_aircraft_record_links"},
        "defects_flightreportrelease": {"history_refuse_update", "validate_aircraft_record_links"},
        "contracts_contract": {"contract_rules"},
        "contracts_workorder": {"workorder_rules"},
        "staffing_handover": {"handover_rules", "handover_card_rules"},
        "staffing_dispatchassignment": {
            "dispatch_assignment_rules",
            "dispatch_assignment_immutable",
        },
        "staffing_dispatchwindow": {"dispatch_window_rules", "dispatch_window_immutable"},
        "staffing_shift": {"roster_shift_rules"},
        "staffing_publishedroster": {"publication_rules"},
        "staffing_publishedshift": {"published_shift_week"},
        "planning_workpackage": {"work_package_evidence"},
        "planning_workcard": {
            "work_card_evidence",
            "work_card_amendment_evidence",
            "work_card_structure_evidence",
        },
        "planning_workcardstepsignoff": {"step_sign_off_evidence", "step_refuse_update"},
        "planning_workcardattestation": {"attestation_evidence", "attestation_refuse_update"},
        "planning_workcardsigningjob": {"signing_job_evidence"},
        # A certificate keeps the work, the staff and the approval as they stood (REQ-261).
        "releases_release": {
            "release_rules",
            "release_certification_evidence",
            "release_grounding_guard",
            "release_refuse_synthetic_certification",
            "release_work_package_snapshot",
            "tooling_release_needs_verification",
            "release_selected_approval",
        },
        "releases_historicalreleaseevidence": {"historical_release_period"},
        "programme_workdone": {
            "release_entry_fixed",
            "work_performer",
            "preserve_completion_evidence",
        },
        # A fitting keeps what it said, and its removal is added once (REQ-235).
        "components_component": {"review_fitting_rules"},
        "components_installation": {"installation_rules", "fitting_usage_rules"},
        # A decision on a service bulletin, and a change or repair, are fixed (REQ-250, REQ-252).
        "modifications_bulletin": {"bulletin_rules"},
        "modifications_change": {"change_rules"},
        # A departure and a completed annual review keep what they said (REQ-285, REQ-287).
        "programme_departure": {"departure_rules"},
        "programme_annualreview": {"annualreview_rules"},
        "directives_applicability": {"no_bulk_insert", "no_bulk_update"},
        "maintenance_data_revision": {"never_current_again"},
        "reviews_certificate": {
            "certificate_serial",
            "certificate_fixed",
            "certificate_identity",
            "certificate_authorisation_terms",
        },
        # An extension keeps what it showed when it was made (REQ-110).
        "reviews_extension": {"extension_keeps", "extension_fixed"},
        "people_experienceevidence": {"experience_replacement"},
        "people_maintenanceauthorisation": {"maintenance_authorisation_replacement"},
        "reviews_reviewstaff": {"reviewstaff_fixed"},
        "reviews_review": {"review_fixed", "review_keeps_confirmed_authorisation_scope"},
        "reviews_reviewitem": {"reviewitem_fixed"},
    }
    required_triggers = {"history_refuse_delete", "history_refuse_truncate", "history_write"}
    for name in sorted(records):
        enabled, forced, policies, triggers, privileges = tables[name]
        assert (enabled, forced) == (True, True), name
        assert policies == ["organisation_scope", *extra_policies.get(name, [])], name
        assert required_triggers <= set(triggers), name
        others = set(triggers) - required_triggers - extra_triggers.get(name, set())
        assert all(trigger.startswith("same_organisation_") for trigger in others), name
        assert privileges == privileges_expected.get(name, usual), name

    # A record refers only to records of its own organisation: every column
    # that refers to another record has the trigger that checks it.
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT child.relname, attribute.attname::text, parent.relname "
            "FROM pg_constraint c "
            "JOIN pg_class child ON child.oid = c.conrelid "
            "JOIN pg_class parent ON parent.oid = c.confrelid "
            "JOIN pg_attribute attribute "
            "  ON attribute.attrelid = c.conrelid AND attribute.attnum = c.conkey[1] "
            "WHERE c.contype = 'f' ORDER BY 1, 2"
        )
        references = cursor.fetchall()
    checked = 0
    for child, column, parent in references:
        if child in records and parent in records and parent != "organisations_organisation":
            assert f"same_organisation_{column}" in tables[child][3], f"{child}.{column}"
            checked += 1
    assert checked >= 3

    # The access log is added to and never changed (REQ-009).
    enabled, forced, policies, triggers, privileges = tables["accounts_accessentry"]
    assert (enabled, forced) == (True, True)
    assert policies == ["entries_added", "organisation_scope", "sign_in_lookup"]
    assert triggers == ["access_time", "history_refuse_change", "history_refuse_truncate"]
    assert privileges == ["INSERT", "SELECT"]

    enabled, forced, policies, triggers, privileges = tables["history_event"]
    assert (enabled, forced) == (True, True)
    assert policies == ["organisation_scope"]
    assert triggers == ["history_chain", "history_refuse_change", "history_refuse_truncate"]
    assert privileges == ["INSERT", "SELECT"]


def test_every_model_is_a_record_or_the_history() -> None:
    """REQ-131. A model that is not a record has to be added here on purpose."""
    for model in apps.get_models():
        if model._meta.db_table in FRAMEWORK_TABLES:
            continue
        assert issubclass(model, Record) or model in (Event, AccessEntry), model


def test_a_record_table_is_never_given_delete() -> None:
    """REQ-131."""
    with pytest.raises(ValueError, match="SELECT, INSERT or UPDATE only"):
        protect_record_table("aircraft_aircraft", privileges=("SELECT", "DELETE"))
    with pytest.raises(ValueError, match="plain identifier"):
        protect_record_table("aircraft; DROP TABLE accounts_user")


# Organisation scoping


def test_with_no_organisation_set_there_are_no_rows(two: Two) -> None:
    """REQ-003, threat TH-020, planned test T-SEC-013."""
    assert Organisation.objects.count() == 0
    assert User.objects.count() == 0
    assert Event.objects.count() == 0
    assert one("SELECT count(*) FROM organisations_organisation") == 0
    assert one("SELECT count(*) FROM accounts_user") == 0
    assert one("SELECT count(*) FROM history_event") == 0


def test_an_organisation_sees_only_its_own_records(two: Two) -> None:
    """REQ-003, AMC1 CAO.A.100(f) point (d)(2)(i)."""
    with working_for(two.ours.id, two.lucy.id):
        assert list(Organisation.objects.all()) == [two.ours]
        assert list(User.objects.all()) == [two.lucy]
        assert {event.organisation_id for event in Event.objects.all()} == {two.ours.id}
        assert not User.objects.filter(pk=two.stranger.pk).exists()
        assert not Organisation.objects.filter(pk=two.other.pk).exists()
        assert one("SELECT count(*) FROM accounts_user WHERE id = %s", two.stranger.id) == 0
    with working_for(two.other.id, two.stranger.id):
        assert list(User.objects.all()) == [two.stranger]


def test_an_organisation_cannot_change_another_organisations_records(two: Two) -> None:
    """REQ-004, threat TH-020, AMC1 CAO.A.100(f) point (d)(2)(ii)."""
    with working_for(two.ours.id, two.lucy.id):
        assert User.objects.filter(pk=two.stranger.pk).update(full_name="Changed") == 0
        assert Organisation.objects.filter(pk=two.other.pk).update(name="Changed") == 0
        assert run("UPDATE accounts_user SET full_name = 'Changed'") == 1  # Lucy only
        with refused("row-level security"):
            User.objects.create_user(
                organisation=two.other,
                username="planted@your-organisation.example",
                full_name="Planted",
            )
        with refused("row-level security|never moves"):
            run(
                "UPDATE accounts_user SET organisation_id = %s WHERE id = %s",
                two.other.id,
                two.lucy.id,
            )
    with as_owner():
        assert one("SELECT full_name FROM accounts_user WHERE id = %s", two.stranger.id) == (
            "[Other Name]"
        )
        assert one("SELECT name FROM organisations_organisation WHERE id = %s", two.other.id) == (
            "[Other Organisation]"
        )


def test_the_application_cannot_create_an_organisation(two: Two) -> None:
    """REQ-004. Setting up an organisation is not open to the application's role."""
    with working_for(two.ours.id, two.lucy.id), refused("permission denied"):
        run(
            "INSERT INTO organisations_organisation "
            "(id, name, approval_type, approval_reference, privileges, scope_of_work) "
            "VALUES (%s, 'Planted', 'Part-CAO', 'UK.CAO.[Number]', '{Maintenance}', 'None')",
            uuid.uuid4(),
        )


def test_the_session_settings_end_with_the_transaction() -> None:
    """Threat TH-020. Nothing carries over to the next request on the same connection."""
    assert _current() == ("", "")
    organisation, user = uuid.uuid4(), uuid.uuid4()
    with working_for(organisation, user):
        assert _current() == (str(organisation), str(user))
        with working_for(None):
            assert _current() == ("", "")
        assert _current() == (str(organisation), str(user))
    assert _current() == ("", "")

    with pytest.raises(RuntimeError), working_for(organisation, user):
        raise RuntimeError
    assert _current() == ("", "")

    # Set without being put back: the end of the transaction clears it.
    with transaction.atomic():
        _set(str(organisation), str(user))
        transaction.set_rollback(True)
    assert _current() == ("", "")


# Who made a change


def test_a_change_with_no_signed_in_user_is_refused(two: Two) -> None:
    """REQ-130, threat TH-022, planned test T-SEC-016."""
    with working_for(two.ours.id), refused("No signed-in user"):
        User.objects.filter(pk=two.lucy.pk).update(full_name="Changed")


def test_a_change_by_a_user_of_another_organisation_is_refused(two: Two) -> None:
    """REQ-004, threat TH-020."""
    with working_for(two.ours.id, two.stranger.id), refused("not an active user"):
        User.objects.filter(pk=two.lucy.pk).update(full_name="Changed")


def test_a_user_who_has_left_is_kept_and_can_no_longer_act(two: Two) -> None:
    """REQ-010. Made inactive, never deleted; past entries keep the name."""
    chris = add_chris(two)
    with working_for(two.ours.id, chris.id):
        Organisation.objects.filter(pk=two.ours.pk).update(scope_of_work=SCOPE + "; C5 Batteries")
    with working_for(two.ours.id, two.lucy.id):
        User.objects.filter(pk=chris.pk).update(is_active=False)
    with working_for(two.ours.id, chris.id), refused("not an active user"):
        Organisation.objects.filter(pk=two.ours.pk).update(scope_of_work=SCOPE)
    with working_for(two.ours.id, two.lucy.id):
        assert User.objects.filter(pk=chris.pk, is_active=False).exists()
        entry = Event.of(two.ours).last()
        assert entry is not None
        assert (entry.actor_id, entry.actor_name) == (chris.id, "Chris Moore")


# The history


def test_every_change_writes_who_when_what_before_and_after(two: Two) -> None:
    """REQ-130, threat TH-022."""
    started = datetime.now(UTC) - timedelta(seconds=5)
    chris = add_chris(two)
    with working_for(two.ours.id, two.lucy.id):
        User.objects.filter(pk=chris.pk).update(full_name="Christopher Moore")
        created, changed = Event.of(chris)

    assert (created.sequence, created.action, created.changed) == (1, "Created", [])
    assert (created.actor_id, created.actor_name) == (two.lucy.id, "Lucy Grant")
    assert created.organisation_id == two.ours.id
    assert created.before_json is None
    assert created.after_json is not None
    assert json.loads(created.after_json)["full_name"] == "Chris Moore"
    assert started <= created.at <= datetime.now(UTC) + timedelta(seconds=5)
    assert created.previous_hash == ""

    assert (changed.sequence, changed.action, changed.changed) == (2, "Changed", ["full_name"])
    assert changed.before_json is not None
    assert changed.after_json is not None
    assert json.loads(changed.before_json)["full_name"] == "Chris Moore"
    assert json.loads(changed.after_json)["full_name"] == "Christopher Moore"
    assert changed.previous_hash == created.hash


def test_a_save_that_changes_nothing_writes_no_history(two: Two) -> None:
    """REQ-130. The history holds changes, not saves."""
    with working_for(two.ours.id, two.lucy.id):
        before = Event.of(two.lucy).count()
        two.lucy.save()
        assert Event.of(two.lucy).count() == before


def test_a_password_is_never_written_to_the_history(two: Two) -> None:
    """Threat TH-001. That it changed is recorded; its value is not."""
    with working_for(two.ours.id, two.lucy.id):
        two.lucy.set_password("a long phrase nobody else knows")
        two.lucy.save()
        entry = Event.of(two.lucy).last()
        assert entry is not None
        assert entry.changed == ["password"]
        for stored in Event.of(two.lucy).values_list("before_json", "after_json"):
            for text in stored:
                assert text is None or "password" not in json.loads(text)


def test_setting_up_an_organisation_is_recorded_against_the_database_role(two: Two) -> None:
    """REQ-130. Work done as the owner of the tables is not passed off as a user's."""
    with working_for(two.ours.id, two.lucy.id):
        (entry,) = Event.of(two.ours)
    assert entry.actor_id is None
    assert entry.actor_name.startswith("Database Role ")
    assert entry.action == "Created"


def test_the_application_cannot_change_or_remove_history(two: Two) -> None:
    """REQ-131, threat TH-021, planned test T-SEC-014."""
    with working_for(two.ours.id, two.lucy.id):
        # The organisation, the approval it holds, its first user and that user's person.
        assert one("SELECT count(*) FROM history_event") == 4
        with refused("permission denied"):
            run("UPDATE history_event SET actor_name = 'Someone Else'")
        with refused("permission denied"):
            run("DELETE FROM history_event")
        with refused("permission denied"):
            run("TRUNCATE history_event")
        with refused("History is written only by a change to a record"):
            run(
                "INSERT INTO history_event (organisation_id, record_type, record_id, action, "
                "changed, after_json) VALUES (%s, 'accounts_user', %s, 'Created', '{}', '{}')",
                two.ours.id,
                uuid.uuid4(),
            )
        entry = Event.of(two.lucy).get()
        with pytest.raises(RecordsAreNeverDeletedError):
            entry.save()
        with pytest.raises(RecordsAreNeverDeletedError):
            entry.delete()
        with pytest.raises(RecordsAreNeverDeletedError):
            Event.objects.all().delete()


def test_the_owner_of_the_tables_cannot_change_or_remove_history_either(two: Two) -> None:
    """REQ-131, threats TH-021, TH-025, planned test T-SEC-014. The trigger
    refuses whoever asks, including a superuser."""
    with as_owner():
        assert one("SELECT count(*) FROM history_event") == 8
        with refused("never changed in place or deleted"):
            run("UPDATE history_event SET actor_name = 'Someone Else'")
        with refused("never changed in place or deleted"):
            run("DELETE FROM history_event")
        with refused("History is written only by a change to a record"):
            run(
                "INSERT INTO history_event (organisation_id, record_type, record_id, action, "
                "changed, after_json) VALUES (%s, 'accounts_user', %s, 'Created', '{}', '{}')",
                two.ours.id,
                uuid.uuid4(),
            )
        # PostgreSQL will not consider TRUNCATE while foreign key checks are waiting.
        run("SET CONSTRAINTS ALL IMMEDIATE")
        with refused("never changed in place or deleted"):
            run("TRUNCATE history_event CASCADE")
        assert one("SELECT count(*) FROM history_event") == 8


def test_a_record_is_never_deleted_by_anyone(two: Two) -> None:
    """REQ-131. No delete in the application, no privilege for its role, and a
    trigger that refuses the owner."""
    with working_for(two.ours.id, two.lucy.id):
        with pytest.raises(RecordsAreNeverDeletedError):
            two.lucy.delete()
        with pytest.raises(RecordsAreNeverDeletedError):
            User.objects.all().delete()
        with pytest.raises(RecordsAreNeverDeletedError):
            Organisation.objects.all().delete()
        for table in ("accounts_user", "organisations_organisation"):
            with refused("permission denied"):
                run(f"DELETE FROM {table}")  # noqa: S608
            with refused("permission denied"):
                run(f"TRUNCATE {table} CASCADE")
    with as_owner():
        run("SET CONSTRAINTS ALL IMMEDIATE")
        for table in ("accounts_user", "organisations_organisation"):
            with refused("never changed in place or deleted"):
                run(f"DELETE FROM {table}")  # noqa: S608
            with refused("never changed in place or deleted"):
                run(f"TRUNCATE {table} CASCADE")
        assert one("SELECT count(*) FROM accounts_user") == 2


def test_a_record_keeps_its_identifier_and_its_organisation(two: Two) -> None:
    """REQ-002, REQ-130. Otherwise a history could be cut loose from its record."""
    with working_for(two.ours.id, two.lucy.id), refused("identifier of a record never changes"):
        run("UPDATE accounts_user SET id = %s WHERE id = %s", uuid.uuid4(), two.lucy.id)
    with as_owner(), refused("never moves to another organisation"):
        run(
            "UPDATE accounts_user SET organisation_id = %s WHERE id = %s",
            two.other.id,
            two.lucy.id,
        )


# The hash chain


def everything() -> list[Event]:
    with as_owner():
        return list(Event.objects.all())


def test_the_chain_holds_and_the_database_and_the_check_agree(two: Two) -> None:
    """Threat TH-021, planned test T-SEC-015. The database writes each hash;
    ``chain.expected_hash`` computes it again, separately, in Python."""
    chris = add_chris(two)
    with working_for(two.ours.id, two.lucy.id):
        User.objects.filter(pk=chris.pk).update(full_name="Christopher Moore")
        User.objects.filter(pk=chris.pk).update(full_name="Chris Moore")
    entries = everything()
    # Two organisations, each with its approval, its first user and that user's person;
    # Chris Moore and his person; his name changed twice.
    assert len(entries) == 12
    assert chain.problems(entries) == []
    assert all(len(entry.hash) == 64 for entry in entries)
    with as_owner():
        assert one("SELECT count(*) FROM history_event e WHERE hash <> history_event_hash(e)") == 0


def test_an_altered_entry_is_detected(two: Two) -> None:
    """Threats TH-021, TH-025, planned test T-SEC-015. Someone with the
    database to themselves switches the triggers off and rewrites an entry."""
    chris = add_chris(two)
    with working_for(two.ours.id, two.lucy.id):
        User.objects.filter(pk=chris.pk).update(full_name="Christopher Moore")
        first, second = Event.of(chris)
    with as_owner():
        run("SET LOCAL session_replication_role = replica")
        run(
            "UPDATE history_event SET after_json = replace(after_json, 'Chris Moore', 'X') "
            "WHERE id = %s",
            first.id,
        )
        run("SET LOCAL session_replication_role = origin")
    assert chain.problems(everything()) == [
        chain.ChainProblem(first.id, "Has been altered since it was written")
    ]

    # Covering the tracks by rewriting the hash breaks the link from the next entry.
    with as_owner():
        run("SET LOCAL session_replication_role = replica")
        run("UPDATE history_event e SET hash = history_event_hash(e) WHERE id = %s", first.id)
        run("SET LOCAL session_replication_role = origin")
    assert chain.problems(everything()) == [
        chain.ChainProblem(second.id, "Does not follow the entry before it")
    ]


def test_every_entry_names_how_it_was_hashed(two: Two) -> None:
    """OWASP ASVS 5.0, 11.2.2. The name is kept with each entry, so the way of
    hashing can change later and the entries written before can still be checked."""
    chris = add_chris(two)
    entries = everything()
    assert {entry.hash_algorithm for entry in entries} == {HASH_ALGORITHM}
    with working_for(two.ours.id, two.lucy.id):
        (first,) = Event.of(chris)
    with as_owner():
        run("SET LOCAL session_replication_role = replica")
        run("UPDATE history_event SET hash_algorithm = 'another' WHERE id = %s", first.id)
        run("SET LOCAL session_replication_role = origin")
    assert chain.problems(everything()) == [
        chain.ChainProblem(first.id, "Was hashed in a way this version does not know")
    ]


def test_a_removed_entry_is_detected(two: Two) -> None:
    """Threats TH-021, TH-025, planned test T-SEC-015."""
    chris = add_chris(two)
    with working_for(two.ours.id, two.lucy.id):
        User.objects.filter(pk=chris.pk).update(full_name="Christopher Moore")
        User.objects.filter(pk=chris.pk).update(full_name="Chris Moore")
        _, second, third = Event.of(chris)
    with as_owner():
        run("SET LOCAL session_replication_role = replica")
        run("DELETE FROM history_event WHERE id = %s", second.id)
        run("SET LOCAL session_replication_role = origin")
    assert chain.problems(everything()) == [
        chain.ChainProblem(third.id, "An entry is missing before this one")
    ]


# The organisation record


def test_the_organisation_record_holds_its_approval(two: Two) -> None:
    """REQ-001. SampleData.md, Organisation: Part-CAO, UK.CAO.[Number], all four privileges."""
    with working_for(two.ours.id, two.lucy.id):
        ours = Organisation.objects.get()
    assert (ours.name, ours.approval_type, ours.approval_reference) == (
        "[Your Organisation]",
        "Part-CAO",
        "UK.CAO.[Number]",
    )
    assert ours.privileges == [
        "Maintenance",
        "Continuing Airworthiness Management",
        "Airworthiness Review",
        "Permit to Fly",
    ]
    assert ours.scope_of_work == SCOPE


@pytest.mark.parametrize(
    ("privileges", "constraint"),
    [
        ([], "organisation_has_known_privileges"),
        (["Design"], "organisation_has_known_privileges"),
        (["Airworthiness Review"], "organisation_review_needs_maintenance_or_management"),
        (["Maintenance", "Permit to Fly"], "organisation_permit_to_fly_needs_review"),
    ],
)
def test_privileges_follow_cao_a_095(two: Two, privileges: list[str], constraint: str) -> None:
    """REQ-001, CAO.A.095. Airworthiness review needs maintenance or continuing
    airworthiness management (point (c)); permit to fly needs airworthiness
    review (point (d)); one or more privileges (point (e))."""
    with (
        working_for(two.ours.id, two.lucy.id),
        pytest.raises(IntegrityError, match=constraint),
        transaction.atomic(),
    ):
        Organisation.objects.filter(pk=two.ours.pk).update(privileges=privileges)


@pytest.mark.parametrize(
    "privileges",
    [
        ["Maintenance"],
        ["Continuing Airworthiness Management", "Airworthiness Review"],
        ["Maintenance", "Airworthiness Review", "Permit to Fly"],
    ],
)
def test_privileges_allowed_by_cao_a_095(two: Two, privileges: list[str]) -> None:
    """REQ-001, CAO.A.095."""
    with working_for(two.ours.id, two.lucy.id):
        assert Organisation.objects.filter(pk=two.ours.pk).update(privileges=privileges) == 1


def test_one_account_for_each_person(two: Two) -> None:
    """REQ-005. A user name belongs to one person."""
    with (
        working_for(two.ours.id, two.lucy.id),
        pytest.raises(IntegrityError),
        transaction.atomic(),
    ):
        User.objects.create_user(
            organisation=two.ours, username=two.lucy.username, full_name="Second Person"
        )
