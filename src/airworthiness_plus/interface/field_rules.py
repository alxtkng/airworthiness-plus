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
from airworthiness_plus.directives import forms as directives
from airworthiness_plus.imports import forms as imports
from airworthiness_plus.maintenance_data import forms as maintenance_data
from airworthiness_plus.programme import forms as programme
from airworthiness_plus.reviews import forms as reviews

Sets = tuple[type[forms.Form] | str, ...]

# Every address that changes something, by its name, with what it may set: the
# fields of a form, or a value named in words where the address takes it itself.
WRITES: dict[str, Sets] = {
    "add_aircraft": (aircraft.AddAircraftForm,),
    "aircraft_details": (aircraft.DetailsForm,),
    "enter_utilisation": (aircraft.UtilisationForm,),
    "make_unserviceable": (aircraft.UnserviceableForm,),
    "make_serviceable": (),
    "add_counter": (aircraft.CounterForm,),
    "records_received": (aircraft.RecordsReceivedForm, "Whether the Transfer Is Complete"),
    "set_up_programme": (programme.ProgrammeForm,),
    "add_task": (programme.TaskForm,),
    "record_review": (programme.ReviewForm,),
    "record_work": (programme.WorkForm,),
    "retire_task": (),
    "record_release": (programme.ReleaseForm,),
    "add_directive": (directives.DirectiveForm,),
    "decide_directive": (directives.DecisionForm,),
    "comply_directive": (directives.ComplianceForm,),
    "terminate_directive": (directives.TerminationForm,),
    "add_data": (maintenance_data.DataSetForm,),
    "add_revision": (maintenance_data.RevisionForm,),
    "record_check": (maintenance_data.CheckForm,),
    "customer_status": (maintenance_data.CustomerStatusForm,),
    "end_holding": (maintenance_data.EndHoldingForm,),
    "add_review_staff": (reviews.ReviewStaffForm,),
    "update_involvement": (reviews.InvolvementForm,),
    "record_restoration": (reviews.RestorationForm,),
    "record_certificate": (reviews.CertificateForm,),
    "start_review": (),
    "review_details": (reviews.DetailsForm,),
    "issue_certificate": (),
    "record_review_item": (reviews.ItemForm,),
    "close_review_finding": (reviews.ClosureForm,),
    "void_certificate": (reviews.VoidForm,),
    "extend_certificate": (reviews.ExtensionForm,),
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
    "add_user": (accounts.AddUserForm, "Code From the Administrator's Authenticator Application"),
    "set_user_roles": (
        accounts.RolesForm,
        "Code From the Administrator's Authenticator Application",
    ),
    "set_user_active": (
        "Active or Inactive",
        "Code From the Administrator's Authenticator Application",
    ),
    "reset_user_password": ("Code From the Administrator's Authenticator Application",),
    "reset_user_second_factor": ("Code From the Administrator's Authenticator Application",),
    "end_user_sessions": ("Code From the Administrator's Authenticator Application",),
    "change_password": (accounts.ChangePasswordForm,),
    "end_other_sessions": ("Code From Your Authenticator Application",),
    "end_session": ("Code From Your Authenticator Application",),
    "sign_in": ("User Name", "Password"),
    "code": ("Code From the Authenticator Application",),
    "set_up": ("Code From the Authenticator Application",),
    "sign_out": (),
}

# Every address that only shows something.
READS = frozenset(
    {
        "home",
        "transfers",
        "aircraft",
        "programme",
        "directives",
        "directive_status",
        "maintenance_data",
        "data_set",
        "aircraft_data",
        "review_schedule",
        "review_staff",
        "aircraft_review",
        "review",
        "certificate",
        "records_export",
        "imports",
        "import_report",
        "problem_log",
        "organisation",
        "users",
        "access_log",
    }
)

# Addresses open to anyone signed in, whatever their roles, and those of sign-in itself.
ANY_SIGNED_IN = "Any Signed-In User, for Themselves"
SIGNING_IN = "Anyone, to Sign In or Out"
WITHOUT_AN_ACTION = {
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
