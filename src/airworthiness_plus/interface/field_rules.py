"""What each action may set, written down from the code (OWASP ASVS 5.0, 8.1.2).

The role matrix says who may take each action. This says, for every address
that changes something, which action it needs and which values it may set.
The values of a form are read from the form itself, so the document cannot
fall behind it; a value taken outside a form is named here. A test fails if
an address or a form is missing from the two tables below, and if the table
in ``architecture/fields-by-action.md`` is not the one ``table()`` returns.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from django import forms
from django.urls import URLPattern, get_resolver

from airworthiness_plus.acceptance import forms as acceptance
from airworthiness_plus.accounts import user_forms as accounts
from airworthiness_plus.accounts.roles import MATRIX, Action, Role
from airworthiness_plus.aircraft import forms as aircraft
from airworthiness_plus.components import forms as components
from airworthiness_plus.configuration import forms as configuration
from airworthiness_plus.contracts import forms as contracts
from airworthiness_plus.customers import forms as customers
from airworthiness_plus.defects import forms as defects
from airworthiness_plus.directives import forms as directives
from airworthiness_plus.imports import forms as imports
from airworthiness_plus.logistics import forms as logistics
from airworthiness_plus.maintenance_data import forms as maintenance_data
from airworthiness_plus.modifications import forms as modifications
from airworthiness_plus.organisations import forms as organisations
from airworthiness_plus.people import forms as people
from airworthiness_plus.planning import forms as planning
from airworthiness_plus.programme import forms as programme
from airworthiness_plus.releases import forms as releases
from airworthiness_plus.reviews import forms as reviews
from airworthiness_plus.staffing import dispatch_forms as dispatch
from airworthiness_plus.staffing import forms as staffing
from airworthiness_plus.staffing import roster_forms as roster
from airworthiness_plus.tooling import calibration_forms as calibration
from airworthiness_plus.tooling import forms as tooling

Sets = tuple[type[forms.Form] | str, ...]

# Every address that changes something, by its name, with what it may set: the
# fields of a form, or a value named in words where the address takes it itself.
WRITES: dict[str, Sets] = {
    "authorise_tool_provider": (calibration.ProviderForm,),
    "place_calibration_order": (calibration.OrderForm,),
    "calibration_movement": (calibration.MovementForm,),
    "record_calibration_certificate": (calibration.CertificateForm,),
    "record_calibration_result": (calibration.ResultForm,),
    "decide_calibration_certificate": (calibration.DecisionForm,),
    "reinstate_calibrated_tool": (calibration.ReinstateForm,),
    "add_tool": (tooling.RegistrationForm,),
    "add_tool_control": (tooling.ControlForm,),
    "add_tool_event": (tooling.EventForm,),
    "add_tool_delegation": (tooling.DelegationForm,),
    "withdraw_tool_delegation": (tooling.WithdrawalForm,),
    "assess_subcontractor": (logistics.SubcontractorAssessmentForm,),
    "add_supplier": (logistics.NewSupplierForm,),
    "evaluate_supplier": (logistics.EvaluationForm,),
    "receive_item": (logistics.ReceiptForm,),
    "record_receiving_check": (logistics.ReceivingCheckForm,),
    "record_receiving_disposition": (logistics.ReceivingDispositionForm,),
    "stores_lookup_exercise": (logistics.StoresExerciseForm,),
    "add_stores_appointment": (logistics.StoresAppointmentForm,),
    "withdraw_stores_appointment": (logistics.StoresWithdrawalForm,),
    "add_stores_location": (logistics.StoresLocationForm,),
    "withdraw_stores_location": (logistics.StoresWithdrawalForm,),
    "record_posting_evidence": (logistics.PostingEvidenceForm,),
    "post_disposition": (logistics.StockPostingForm,),
    "move_stock": (logistics.StockMovementForm,),
    "count_stock": (logistics.StockCountForm,),
    "adjust_stock": (logistics.StockAdjustmentForm,),
    "add_roster_shift": (roster.ShiftForm,),
    "dispatch_assign": (dispatch.AssignmentForm,),
    "dispatch_move": (dispatch.MoveAssignmentForm,),
    "dispatch_break": (dispatch.BreakForm,),
    "dispatch_turnaround": (dispatch.TurnaroundForm,),
    "withdraw_roster_shift": (roster.WithdrawShiftForm,),
    "publish_roster": (roster.PublicationForm,),
    "record_handover": (roster.HandoverForm,),
    "acknowledge_handover": (),
    "record_bank_holiday": (roster.BankHolidayForm,),
    "record_shift_pattern": (roster.ShiftPatternForm,),
    "record_staffing_minimum": (roster.StaffingMinimumForm,),
    "change_planning_settings": (roster.SettingsForm,),
    "record_staffing_hours": (staffing.DemandForm,),
    "review_staffing_plan": (staffing.ReviewForm,),
    "record_staffing_shortfall": (staffing.ReportForm,),
    "record_staff_absence": (staffing.AbsenceForm,),
    "build_work_package": (planning.BuildPackageForm,),
    "link_package_order": (planning.LinkOrderForm,),
    "add_work_card": (planning.WorkCardForm,),
    "issue_work_package": (),
    "complete_work_card": (planning.WorkCompletionForm,),
    "attest_work_card": (planning.AttestationForm,),
    "sign_work_card_step": (planning.StepSignOffForm,),
    "inspect_work_card": (planning.InspectionForm,),
    "release_work_package": (planning.PackageReleaseForm,),
    "add_aircraft": (aircraft.AddAircraftForm,),
    "aircraft_details": (aircraft.DetailsForm,),
    "change_owner": (aircraft.OwnerForm,),
    "add_customer": (customers.CustomerForm,),
    "change_customer": (customers.CustomerForm,),
    "draw_up_contract": (contracts.ContractForm,),
    "end_contract": (contracts.EndContractForm,),
    "contract_authority_told": (contracts.AuthorityToldForm,),
    "add_work_order": (contracts.WorkOrderForm,),
    "close_work_order": (contracts.CloseWorkOrderForm,),
    "record_historical_release_evidence": (releases.HistoricalReleaseEvidenceForm,),
    "record_release_certificate": (releases.CertificateForm,),
    "record_defect": (defects.DefectForm,),
    "close_defect": (defects.CloseForm,),
    "record_repeat_action": (defects.RepeatActionForm,),
    "add_component": (components.ComponentForm,),
    "fit_component": (components.FitForm,),
    "remove_component": (components.RemoveForm,),
    "review_component": (components.ReviewForm,),
    "component_life_from": (components.LifeFromForm,),
    "change_component_limit": (components.LimitForm,),
    "record_change": (modifications.ChangeForm,),
    "embody_change": (modifications.EmbodiedForm,),
    "record_bulletin": (modifications.BulletinForm,),
    "decide_bulletin": (modifications.DecisionForm,),
    "record_weighing": (modifications.WeighingForm,),
    "record_weight_schedule": (modifications.ScheduleForm,),
    "enter_utilisation": (aircraft.UtilisationForm,),
    "make_unserviceable": (aircraft.UnserviceableForm,),
    "make_serviceable": (),
    "add_counter": (aircraft.CounterForm,),
    "records_received": (aircraft.RecordsReceivedForm, "Whether the Transfer Is Complete"),
    "start_transfer": (),
    "set_transfer_item": (configuration.ItemForm,),
    "add_position": (configuration.PositionForm,),
    "record_position": (configuration.RecordPositionForm,),
    "sign_baseline": (),
    "set_up_programme": (programme.ProgrammeForm,),
    "add_task": (programme.TaskForm,),
    "record_review": (programme.ReviewForm,),
    "add_departure": (programme.DepartureForm,),
    "departure_copy_sent": (programme.DepartureDateForm,),
    "withdraw_departure": (programme.DepartureDateForm,),
    "start_annual_review": (),
    "note_annual_review": (programme.AnnualReviewForm,),
    "complete_annual_review": (programme.CompleteReviewForm,),
    "record_work": (programme.WorkForm,),
    "retire_task": (),
    "record_release": (),
    "add_directive": (directives.DirectiveForm,),
    "add_directive_source": (directives.SourceForm,),
    "check_directive_source": (directives.SourceCheckForm,),
    "decide_directive": (directives.DecisionForm,),
    "comply_directive": (directives.ComplianceForm,),
    "terminate_directive": (directives.TerminationForm,),
    "add_data": (maintenance_data.DataSetForm,),
    "add_revision": (maintenance_data.RevisionForm,),
    "record_check": (maintenance_data.CheckForm,),
    "customer_status": (maintenance_data.CustomerStatusForm,),
    "end_holding": (maintenance_data.EndHoldingForm,),
    "add_maintenance_authorisation": (people.MaintenanceAuthorisationForm,),
    "withdraw_maintenance_authorisation": (people.MaintenanceAuthorisationWithdrawalForm,),
    "record_maintenance_experience": (people.ExperienceEvidenceForm,),
    "withdraw_maintenance_experience": (people.ExperienceWithdrawalForm,),
    "add_recurrent_training": (people.RecurrentTrainingForm,),
    "add_person": (people.PersonForm,),
    "change_person": (people.PersonForm,),
    "add_review_staff": (reviews.ReviewStaffForm,),
    "record_review_authorisation": (reviews.ReviewAuthorisationForm,),
    "update_involvement": (reviews.InvolvementForm,),
    "record_restoration": (reviews.RestorationForm,),
    "record_certificate": (reviews.CertificateForm,),
    "start_review": (reviews.ReviewStartForm,),
    "review_details": (reviews.DetailsForm,),
    "issue_certificate": ("Password and Authenticator Code",),
    "record_review_item": (reviews.ItemForm,),
    "close_review_finding": (reviews.ClosureForm,),
    "void_certificate": (reviews.VoidForm,),
    "extend_certificate": (reviews.ExtensionForm, "Password and Authenticator Code"),
    "certificate_copy_sent": (reviews.CopySentForm,),
    "extension_copy_sent": (reviews.CopySentForm,),
    "export_organisation": (),
    "export_aircraft": (),
    "load_import": (imports.LoadForm,),
    "check_import": (
        "For Each Value Loaded: That It Agrees with the Source, or the Value in the Source",
    ),
    "add_problem": (acceptance.ProblemForm,),
    "add_problem_note": (acceptance.NoteForm,),
    "record_records_approval": (acceptance.ApprovalForm,),
    "record_parallel_run": (acceptance.ParallelRunForm,),
    "change_organisation_details": (organisations.DetailsForm,),
    "record_approval_held": (organisations.ApprovalHeldForm,),
    "end_approval_held": (organisations.EndApprovalForm,),
    "set_lead_times": (organisations.LeadTimesForm,),
    "set_reweigh_threshold": (organisations.ReweighThresholdForm,),
    "set_deferral_limits": (organisations.DeferralLimitsForm,),
    "add_user": (accounts.AddUserForm, "Password and Authenticator Code"),
    "set_user_roles": (
        accounts.RolesForm,
        "Password and Authenticator Code",
    ),
    "set_user_active": (
        "Active or Inactive",
        "Password and Authenticator Code",
    ),
    "reset_user_password": ("Password and Authenticator Code",),
    "reset_user_second_factor": ("Password and Authenticator Code",),
    "end_user_sessions": ("Code From the Administrator's Authenticator Application",),
    "change_password": (accounts.ChangePasswordForm,),
    "end_other_sessions": ("Code From Your Authenticator Application",),
    "end_session": ("Code From Your Authenticator Application",),
    "passkey_sign_in": ("User Name", "Passkey Response"),
    "verify_passkey": ("Passkey Response",),
    "add_passkey": ("Passkey Name", "Passkey Response"),
    "remove_passkey": ("Passkey", "Password and Authenticator Code"),
    "passkey_settings": ("Password and Authenticator Code",),
    "sign_in": ("User Name", "Password"),
    "code": ("Code From the Authenticator Application",),
    "set_up": ("Code From the Authenticator Application",),
    "sign_out": (),
}

# Every address that only shows something.
READS = frozenset(
    {
        "home",
        "staff_roster",
        "dispatch_board",
        "load_and_capacity",
        "planning_settings",
        "suppliers",
        "goods_in",
        "goods_receipt",
        "stores_stock",
        "stock_entry",
        "quarantine_hold",
        "stores_locations",
        "stores_appointments",
        "tool_register",
        "tool_providers",
        "tool_provider",
        "calibration_order",
        "calibration_certificate",
        "tool_record",
        "tool_delegations",
        "supplier",
        "staffing_plan",
        "work_packages",
        "work_package",
        "dashboard",
        "transfers",
        "set_up_configuration",
        "aircraft_forecast",
        "aircraft_configuration",
        "baseline",
        "contracts",
        "contract",
        "release_to_service",
        "release_certificate",
        "programmes",
        "components",
        "modifications",
        "weight_and_balance",
        "component",
        "defects",
        "maintenance_history",
        "aircraft_maintenance_history",
        "defect",
        "repeat_defects",
        "aircraft",
        "programme",
        "directives",
        "directive_status",
        "maintenance_data",
        "data_set",
        "aircraft_data",
        "review_schedule",
        "review_staff",
        "staff_recency",
        "maintenance_experience",
        "organisation_chart",
        "staff",
        "customers",
        "customer",
        "person",
        "aircraft_review",
        "review",
        "certificate",
        "records_export",
        "imports",
        "import_report",
        "problem_log",
        "organisation",
        "settings",
        "users",
        "access_log",
    }
)

# Addresses open to anyone signed in, whatever their roles, and those of sign-in itself.
ANY_SIGNED_IN = "Any Signed-In User, for Themselves"
SIGNING_IN = "Anyone, to Sign In or Out"
WITHOUT_AN_ACTION = {
    "verify_passkey": ANY_SIGNED_IN,
    "add_passkey": ANY_SIGNED_IN,
    "remove_passkey": ANY_SIGNED_IN,
    "passkey_settings": ANY_SIGNED_IN,
    "passkey_sign_in": SIGNING_IN,
    "change_password": ANY_SIGNED_IN,
    "end_other_sessions": ANY_SIGNED_IN,
    "end_session": ANY_SIGNED_IN,
    "sign_in": SIGNING_IN,
    "code": SIGNING_IN,
    "set_up": SIGNING_IN,
    "sign_out": SIGNING_IN,
}


@dataclass(frozen=True)
class Rule:
    """One address that changes something."""

    name: str
    address: str
    action: Action | None
    does: str
    sets: tuple[str, ...]

    @property
    def who(self) -> str:
        if self.action is None:
            return WITHOUT_AN_ACTION[self.name]
        return ", ".join(role.label for role in Role if role in MATRIX[self.action])


def patterns() -> list[URLPattern]:
    """Return every address of the application."""
    return [p for p in get_resolver().url_patterns if isinstance(p, URLPattern) and p.name]


def _labels(sets: Sets) -> Iterator[str]:
    for one in sets:
        if isinstance(one, str):
            yield one
        else:
            yield from (str(field.label) for field in one.base_fields.values())


def rules() -> list[Rule]:
    """Return every address that changes something, in the order of the addresses."""
    found = []
    for pattern in patterns():
        name = str(pattern.name)
        if name not in WRITES:
            continue
        view = pattern.callback
        does = (view.__doc__ or "").strip().splitlines()[0].rstrip(".")
        found.append(
            Rule(
                name=name,
                address="/" + str(pattern.pattern),
                action=getattr(view, "action", None),
                does=does,
                sets=tuple(_labels(WRITES[name])),
            )
        )
    return found


START = "<!-- The table below is written by the command. Do not edit it by hand. -->"
END = "<!-- End of the table written by the command. -->"


def table() -> str:
    """Return the table of architecture/fields-by-action.md."""
    lines = [
        "| Action | Roles | Address | What It Does | Values It May Set |",
        "|---|---|---|---|---|",
    ]
    for rule in rules():
        action = rule.action.value if rule.action is not None else "None"
        sets = "; ".join(rule.sets) if rule.sets else "None"
        lines.append(f"| {action} | {rule.who} | `{rule.address}` | {rule.does} | {sets} |")
    return "\n".join(lines)


def written_table(document: str) -> str:
    """Return the table as it stands in the document."""
    return document.split(START, 1)[1].split(END, 1)[0].strip()


def with_table(document: str) -> str:
    """Return the document with its table made afresh."""
    before, rest = document.split(START, 1)
    after = rest.split(END, 1)[1]
    return f"{before}{START}\n\n{table()}\n\n{END}{after}"
