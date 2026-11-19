"""Where each page sits: the sidebar, the breadcrumb and the section tabs (REQ-196).

One element for each job (design-system/README.md, Navigation). The sidebar
is global navigation, one item for each section. The breadcrumb says where
the page is and ends at the section. The tabs are the views of one section.
Every address of the application belongs to exactly one item;
``tests/test_interface.py`` fails if one does not.
"""

from dataclasses import dataclass, field

from django.http import HttpRequest

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action


@dataclass(frozen=True)
class Tab:
    """One view of a section."""

    label: str
    address: str


@dataclass(frozen=True)
class Item:
    """One item of the sidebar: a section, its first page and every address inside it."""

    label: str
    address: str
    action: Action = Action.VIEW_RECORDS
    tabs: tuple[Tab, ...] = ()
    inside: frozenset[str] = field(default_factory=frozenset)

    def holds(self, address: str) -> bool:
        """Return whether the page at ``address`` belongs to this section."""
        own = {self.address} | {tab.address for tab in self.tabs}
        return address in own or address in self.inside


@dataclass(frozen=True)
class Group:
    """A group of the sidebar, named as Regulation 1321/2014 names things."""

    label: str
    items: tuple[Item, ...]


GROUPS: tuple[Group, ...] = (
    Group(
        "Continuing Airworthiness",
        (
            Item(
                "Aircraft",
                "home",
                tabs=(
                    Tab("Fleet", "home"),
                    Tab("Transfers", "transfers"),
                    Tab("Airworthiness Directives", "directives"),
                    Tab("Airworthiness Review", "review_schedule"),
                ),
                inside=frozenset(
                    {
                        "add_aircraft",
                        "aircraft",
                        "aircraft_details",
                        "enter_utilisation",
                        "make_unserviceable",
                        "make_serviceable",
                        "add_counter",
                        "records_received",
                        "programme",
                        "set_up_programme",
                        "add_task",
                        "record_review",
                        "record_work",
                        "retire_task",
                        "record_release",
                        "add_directive",
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
        ),
    ),
    Group(
        "People",
        (
            Item(
                "Authorisations",
                "review_staff",
                inside=frozenset({"add_review_staff", "update_involvement", "record_restoration"}),
            ),
        ),
    ),
    Group(
        "Documentation",
        (
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
            Item(
                "Records",
                "imports",
                tabs=(
                    Tab("Import", "imports"),
                    Tab("Records Export", "records_export"),
                    Tab("Problem Log", "problem_log"),
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
            ),
            Item(
                "Users",
                "users",
                action=Action.MANAGE_USERS_AND_ROLES,
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
            ),
        ),
    ),
)

# Pages that belong to the person, not to a section.
OUTSIDE = frozenset(
    {"sign_in", "code", "set_up", "sign_out", "change_password", "end_other_sessions"}
)


def place(address: str) -> tuple[Group, Item] | None:
    """Return the group and item the page at ``address`` belongs to."""
    for group in GROUPS:
        for item in group.items:
            if item.holds(address):
                return group, item
    return None


def navigation(request: HttpRequest) -> dict[str, object]:
    """Give every page its sidebar, its breadcrumb and its section tabs."""
    user = request.user
    if not isinstance(user, User):
        return {}
    match = request.resolver_match
    address = match.url_name if match and match.url_name else ""
    found = place(address)
    sidebar = [
        (group.label, [(item, found is not None and item is found[1]) for item in shown])
        for group in GROUPS
        if (shown := [item for item in group.items if user.may(item.action)])
    ]
    tabs: list[tuple[Tab, bool]] = []
    if found and address in {tab.address for tab in found[1].tabs}:
        tabs = [(tab, tab.address == address) for tab in found[1].tabs]
    return {"sidebar": sidebar, "place": found, "section_tabs": tabs}
