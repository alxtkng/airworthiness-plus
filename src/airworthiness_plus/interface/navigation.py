"""Where each page sits: the sidebar, the breadcrumb and the section tabs (REQ-196).

One element for each job (design-system/README.md, Navigation). The sidebar
is global navigation, one item for each section. The breadcrumb says where
the page is and ends at the section. The tabs are the views of one section.
Every address of the application belongs to exactly one item;
``tests/test_interface.py`` fails if one does not.

``BOARD`` is the whole sidebar as the Sidebar board of the canvas gives it,
with the approvals each item is shown for (REQ-201) and the tabs of the
Tabs board (REQ-202). An item or a tab has an address once its page is
built; until then it is recorded here and not shown. ``GROUPS`` is what is
built. ``tests/test_navigation.py`` holds the board written out by hand.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace

from django.http import HttpRequest

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import ApprovalType

CAO, CAMO, P145 = ApprovalType.PART_CAO, ApprovalType.PART_CAMO, ApprovalType.PART_145
# Every approval of this build. The Owner of the board is not an approval: an
# organisation here always holds one, so the Owner's sidebar is not built.
EVERY: frozenset[str] = frozenset({str(CAO), str(CAMO), str(P145)})
# The approvals that carry out maintenance. A Part-CAMO manages and does not.
MAINTAINS: frozenset[str] = frozenset({str(CAO), str(P145)})


@dataclass(frozen=True)
class Tab:
    """One view of a section. ``ours`` marks a tab that is not on the Tabs board."""

    label: str
    address: str | None = None
    ours: bool = False


@dataclass(frozen=True)
class Item:
    """One item of the sidebar: a section, its first page and every address inside it.

    ``shown_for`` is the approvals the item is for: it is shown when the
    organisation holds any of them. ``ours`` marks an item that is not on
    the Sidebar board. With no address the page is not built yet.
    """

    label: str
    address: str | None = None
    shown_for: frozenset[str] = EVERY
    action: Action = Action.VIEW_RECORDS
    tabs: tuple[Tab, ...] = ()
    inside: frozenset[str] = field(default_factory=frozenset)
    ours: bool = False

    def holds(self, address: str) -> bool:
        """Return whether the page at ``address`` belongs to this section."""
        own = {self.address} | {tab.address for tab in self.tabs}
        return address in own or address in self.inside


@dataclass(frozen=True)
class Group:
    """A group of the sidebar, named as Regulation 1321/2014 names things.

    The Dashboard at the head, and Settings and Help at the foot, stand in
    groups with no name.
    """

    label: str
    items: tuple[Item, ...]


def _tabs(*labels: str) -> tuple[Tab, ...]:
    return tuple(Tab(label) for label in labels)


BOARD: tuple[Group, ...] = (
    Group("", (Item("Dashboard", "dashboard"),)),
    Group(
        "Continuing Airworthiness",
        (
            Item(
                "Aircraft",
                "home",
                tabs=(
                    Tab("All Aircraft", "home"),
                    Tab("Airworthiness Reviews", "review_schedule"),
                    Tab("Transfers", "transfers"),
                ),
                inside=frozenset(
                    {
                        "add_aircraft",
                        "aircraft",
                        "aircraft_details",
                        "enter_utilisation",
                        "make_unserviceable",
                        "make_serviceable",
                        "change_owner",
                        "add_counter",
                        "records_received",
                        "start_transfer",
                        "set_transfer_item",
                        "set_up_configuration",
                        "aircraft_forecast",
                        "aircraft_configuration",
                        "add_position",
                        "record_position",
                        "sign_baseline",
                        "baseline",
                        "programme",
                        "set_up_programme",
                        "add_task",
                        "record_review",
                        "add_departure",
                        "departure_copy_sent",
                        "withdraw_departure",
                        "start_annual_review",
                        "note_annual_review",
                        "complete_annual_review",
                        "record_work",
                        "retire_task",
                        "record_release",
                        "directive_status",
                        "decide_directive",
                        "comply_directive",
                        "terminate_directive",
                        "aircraft_data",
                        "aircraft_review",
                        "record_certificate",
                        "start_review",
                        "review",
                        "review_details",
                        "issue_certificate",
                        "record_review_item",
                        "close_review_finding",
                        "certificate",
                        "void_certificate",
                        "extend_certificate",
                        "certificate_copy_sent",
                        "extension_copy_sent",
                        "export_aircraft",
                    }
                ),
            ),
            Item(
                "Defects",
                "defects",
                tabs=(
                    Tab("Open and Deferred", "defects"),
                    Tab("Repeat Defects", "repeat_defects"),
                ),
                inside=frozenset(
                    {"record_defect", "defect", "close_defect", "record_repeat_action"}
                ),
            ),
            Item("Maintenance Programmes", "programmes"),
            Item(
                "Aircraft Configuration",
                "components",
                tabs=(
                    Tab("Components and Life Limits", "components"),
                    Tab("Airworthiness Directives", "directives"),
                    Tab("Modifications and Repairs", "modifications"),
                    Tab("Weight and Balance", "weight_and_balance"),
                ),
                inside=frozenset(
                    {
                        "add_component",
                        "component",
                        "fit_component",
                        "remove_component",
                        "review_component",
                        "component_life_from",
                        "change_component_limit",
                        "add_directive",
                        "add_directive_source",
                        "check_directive_source",
                        "record_change",
                        "embody_change",
                        "record_bulletin",
                        "decide_bulletin",
                        "record_weighing",
                        "record_weight_schedule",
                    }
                ),
            ),
            Item(
                "Release to Service",
                "release_to_service",
                shown_for=MAINTAINS,
                inside=frozenset({"record_release_certificate"}),
            ),
            Item(
                "Contracts",
                "contracts",
                inside=frozenset(
                    {
                        "draw_up_contract",
                        "contract",
                        "end_contract",
                        "contract_authority_told",
                        "add_work_order",
                        "close_work_order",
                    }
                ),
            ),
        ),
    ),
    Group(
        "Management System",
        (
            # The board shows these two to Part-CAMO and Part-145. Decisions.md, Canvas
            # Build, decision 5, shows them to Part-CAO as well.
            Item("Hazard Log"),
            Item("Safety Reports"),
            Item("Occurrence Reports"),
            Item("Compliance Monitoring"),
            Item("Actions"),
        ),
    ),
    Group(
        "Planning",
        (
            Item("Work Packages", shown_for=MAINTAINS),
            Item(
                "Manhours and Capacity",
                shown_for=MAINTAINS,
                tabs=_tabs("Manhour Plan", "Load and Capacity", "Staff Roster"),
            ),
        ),
    ),
    Group(
        "Logistics",
        (
            Item("Goods In", shown_for=MAINTAINS, tabs=_tabs("Receiving Inspection")),
            Item("Stores", shown_for=MAINTAINS, tabs=_tabs("Stock", "Quarantine and Scrap")),
            Item(
                "Tools and Equipment",
                shown_for=MAINTAINS,
                tabs=_tabs(
                    "Register",
                    "Service Providers",
                    "Alternative Tooling",
                    "Tooling Need Evaluations",
                ),
            ),
            Item("Suppliers", shown_for=MAINTAINS),
        ),
    ),
    Group(
        "People",
        (
            Item(
                "Staff",
                "staff",
                tabs=(Tab("All Staff", "staff"), Tab("Organisation Chart")),
                inside=frozenset({"add_person", "person", "change_person"}),
            ),
            Item(
                "Authorisations",
                "review_staff",
                tabs=(Tab("Authorisations", "review_staff"), Tab("Recency")),
                inside=frozenset({"add_review_staff", "update_involvement", "record_restoration"}),
            ),
        ),
    ),
    Group(
        "Training",
        (
            Item("Recurrent Training"),
            Item(
                "Aircraft Maintenance Licence",
                tabs=_tabs(
                    "Basic Examinations",
                    "Experience Logbook",
                    "Type Training",
                    "On the Job Training",
                ),
            ),
            Item("Competency Assessments"),
        ),
    ),
    Group(
        "Documentation",
        (
            Item("Manuals and Procedures"),
            Item(
                "Maintenance Data",
                "maintenance_data",
                inside=frozenset(
                    {
                        "add_data",
                        "data_set",
                        "add_revision",
                        "record_check",
                        "customer_status",
                        "end_holding",
                    }
                ),
            ),
            Item("Revisions"),
            Item("Required Reading"),
            Item("Notices"),
        ),
    ),
    Group(
        "Organisation",
        (
            Item(
                "Approval and Scope",
                "organisation",
                inside=frozenset({"record_records_approval", "record_parallel_run"}),
            ),
            Item("Changes"),
            Item("Oversight"),
            # Records and Users are ours: the acceptance records of CAP 562 C-90
            # and the accounts of REQ-005 (Decisions.md, Interface).
            Item(
                "Records",
                "imports",
                tabs=(
                    Tab("Import", "imports", ours=True),
                    Tab("Records Export", "records_export", ours=True),
                    Tab("Problem Log", "problem_log", ours=True),
                ),
                inside=frozenset(
                    {
                        "load_import",
                        "import_report",
                        "check_import",
                        "export_organisation",
                        "add_problem",
                        "add_problem_note",
                    }
                ),
                ours=True,
            ),
            Item(
                "Users",
                "users",
                action=Action.MANAGE_USERS_AND_ROLES,
                tabs=(
                    Tab("Users", "users", ours=True),
                    Tab("Access Log", "access_log", ours=True),
                ),
                inside=frozenset(
                    {
                        "add_user",
                        "set_user_roles",
                        "set_user_active",
                        "reset_user_password",
                        "reset_user_second_factor",
                        "end_user_sessions",
                    }
                ),
                ours=True,
            ),
        ),
    ),
    Group(
        "Commercial",
        (
            Item("Marketplace"),
            Item("Enquiries and Quotes", tabs=_tabs("Enquiries", "Quotes")),
            Item(
                "Customers",
                "customers",
                inside=frozenset({"add_customer", "customer", "change_customer"}),
            ),
            Item("Invoices"),
        ),
    ),
    Group(
        "",
        (
            Item(
                "Settings",
                "settings",
                tabs=(Tab("Organisation", "settings"), Tab("Planning")),
                inside=frozenset(
                    {
                        "change_organisation_details",
                        "record_approval_held",
                        "end_approval_held",
                        "set_lead_times",
                        "set_reweigh_threshold",
                        "set_deferral_limits",
                    }
                ),
            ),
            Item("Help"),
        ),
    ),
)


def _built(board: tuple[Group, ...]) -> tuple[Group, ...]:
    """Return the groups, items and tabs of ``board`` whose pages exist."""
    groups = []
    for group in board:
        items = tuple(
            replace(item, tabs=tuple(tab for tab in item.tabs if tab.address is not None))
            for item in group.items
            if item.address is not None
        )
        if items:
            groups.append(Group(group.label, items))
    return tuple(groups)


# What is built: the sidebar a user may be shown.
GROUPS: tuple[Group, ...] = _built(BOARD)

# Pages that belong to the person, not to a section.
OUTSIDE = frozenset(
    {
        "sign_in",
        "code",
        "set_up",
        "sign_out",
        "change_password",
        "end_other_sessions",
        "end_session",
    }
)


def place(address: str) -> tuple[Group, Item] | None:
    """Return the group and item the page at ``address`` belongs to."""
    for group in GROUPS:
        for item in group.items:
            if item.holds(address):
                return group, item
    return None


def shown(
    groups: Iterable[Group], *, approvals: Iterable[str], may: Callable[[Action], bool]
) -> list[tuple[str, list[Item]]]:
    """Return the groups and items to show: for an approval held, to a role that may.

    A group with no item left is not shown (REQ-201).
    """
    held = frozenset(approvals)
    found = []
    for group in groups:
        items = [item for item in group.items if item.shown_for & held and may(item.action)]
        if items:
            found.append((group.label, items))
    return found


def navigation(request: HttpRequest) -> dict[str, object]:
    """Give every page its sidebar, its breadcrumb and its section tabs."""
    user = request.user
    if not isinstance(user, User):
        return {}
    match = request.resolver_match
    address = match.url_name if match and match.url_name else ""
    found = place(address)
    held = approvals.types_held(user.organisation)
    sidebar = [
        (label, [(item, found is not None and item is found[1]) for item in items])
        for label, items in shown(GROUPS, approvals=held, may=user.may)
    ]
    tabs: list[tuple[Tab, bool]] = []
    # One tab is no choice of views, so it is not shown.
    if found and len(found[1].tabs) > 1 and address in {tab.address for tab in found[1].tabs}:
        tabs = [(tab, tab.address == address) for tab in found[1].tabs]
    return {"sidebar": sidebar, "place": found, "section_tabs": tabs}
