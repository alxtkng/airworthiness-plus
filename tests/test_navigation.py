"""The sidebar, by the approvals an organisation holds (REQ-201, REQ-202).

The expected tree is written out here by hand from the Sidebar board
(canvas/Sidebar.dc.html), read on 24 November 2026, with decision 5 of the
Canvas Build applied: Hazard Log and Safety Reports also show to Part-CAO.
The Owner of the board is not an approval and is not built.
"""

from datetime import date

import pytest
from django.urls import reverse

from airworthiness_plus.history.session import working_for
from airworthiness_plus.interface import navigation
from airworthiness_plus.organisations.models import Approval, ApprovalType
from tests.support import make_sample, signed_in

CAO, CAMO, P145 = "Part-CAO", "Part-CAMO", "Part-145"
EVERY = {CAO, CAMO, P145}
MAINTAINS = {CAO, P145}

# Group, then each item with the approvals it is shown for.
BOARD: list[tuple[str, list[tuple[str, set[str]]]]] = [
    ("", [("Dashboard", EVERY)]),
    (
        "Continuing Airworthiness",
        [
            ("Aircraft", EVERY),
            ("Defects", EVERY),
            ("Maintenance Programmes", EVERY),
            ("Aircraft Configuration", EVERY),
            ("Release to Service", MAINTAINS),
            ("Contracts", EVERY),
        ],
    ),
    (
        "Management System",
        [
            (
                "Hazard Log",
                EVERY,
            ),  # the board gives Part-CAMO and Part-145; decision 5 adds Part-CAO
            ("Safety Reports", EVERY),  # the same
            ("Occurrence Reports", EVERY),
            ("Compliance Monitoring", EVERY),
            ("Actions", EVERY),
        ],
    ),
    ("Planning", [("Work Packages", MAINTAINS), ("Manhours and Capacity", MAINTAINS)]),
    (
        "Logistics",
        [
            ("Goods In", MAINTAINS),
            ("Stores", MAINTAINS),
            ("Tools and Equipment", MAINTAINS),
            ("Suppliers", MAINTAINS),
        ],
    ),
    ("People", [("Staff", EVERY), ("Authorisations", EVERY)]),
    (
        "Training",
        [
            ("Recurrent Training", EVERY),
            ("Aircraft Maintenance Licence", EVERY),
            ("Competency Assessments", EVERY),
        ],
    ),
    (
        "Documentation",
        [
            ("Manuals and Procedures", EVERY),
            ("Maintenance Data", EVERY),
            ("Revisions", EVERY),
            ("Required Reading", EVERY),
            ("Notices", EVERY),
        ],
    ),
    ("Organisation", [("Approval and Scope", EVERY), ("Changes", EVERY), ("Oversight", EVERY)]),
    (
        "Commercial",
        [
            ("Marketplace", EVERY),
            ("Enquiries and Quotes", EVERY),
            ("Customers", EVERY),
            ("Invoices", EVERY),
        ],
    ),
    ("", [("Settings", EVERY), ("Help", EVERY)]),
]

# Section tabs, from the Tabs board (canvas/Tabs.dc.html), for the sections that have them.
TABS = {
    "Aircraft": ["All Aircraft", "Airworthiness Reviews", "Transfers"],
    "Defects": ["Open and Deferred", "Repeat Defects"],
    "Aircraft Configuration": [
        "Components and Life Limits",
        "Airworthiness Directives",
        "Modifications and Repairs",
        "Weight and Balance",
    ],
    "Goods In": ["Receiving Inspection"],
    "Stores": ["Stock", "Quarantine and Scrap"],
    "Manhours and Capacity": ["Manhour Plan", "Load and Capacity", "Staff Roster"],
    "Tools and Equipment": [
        "Register",
        "Service Providers",
        "Alternative Tooling",
        "Tooling Need Evaluations",
    ],
    "Enquiries and Quotes": ["Enquiries", "Quotes"],
    "Staff": ["All Staff", "Organisation Chart"],
    "Authorisations": ["Authorisations", "Recency"],
    "Aircraft Maintenance Licence": [
        "Basic Examinations",
        "Experience Logbook",
        "Type Training",
        "On the Job Training",
    ],
    "Settings": ["Organisation", "Planning"],
}


def of_the_board() -> list[navigation.Group]:
    """The groups as recorded, without the items that are ours and not the board's."""
    return [
        navigation.Group(group.label, tuple(item for item in group.items if not item.ours))
        for group in navigation.BOARD
    ]


def test_the_sidebar_is_the_sidebar_board() -> None:
    """REQ-201. Every group and item of the board, in its order, shown for its approvals."""
    recorded = [
        (group.label, [(item.label, set(item.shown_for)) for item in group.items])
        for group in of_the_board()
    ]
    assert recorded == BOARD
    assert sum(len(items) for _, items in BOARD) == 37
    assert {str(value) for value in ApprovalType} == EVERY


def test_the_section_tabs_are_those_of_the_tabs_board() -> None:
    """REQ-202. A tab of the board is recorded in its order; one of ours follows them."""
    for group in navigation.BOARD:
        for item in group.items:
            board = [tab.label for tab in item.tabs if not tab.ours]
            if item.ours:
                continue
            assert board == TABS.get(item.label, []), item.label


def labels(groups: list[tuple[str, list[navigation.Item]]]) -> list[tuple[str, list[str]]]:
    return [(group, [item.label for item in items]) for group, items in groups]


@pytest.mark.parametrize(
    ("held", "hidden"),
    [
        ({CAO}, set()),
        ({P145}, set()),
        ({CAO, CAMO, P145}, set()),
        (
            {CAMO},
            {
                "Release to Service",
                "Work Packages",
                "Manhours and Capacity",
                "Goods In",
                "Stores",
                "Tools and Equipment",
                "Suppliers",
            },
        ),
        ({CAMO, P145}, set()),
    ],
)
def test_an_item_is_shown_for_an_approval_held(held: set[str], hidden: set[str]) -> None:
    """REQ-201. Worked by hand from the board for each set of approvals.

    A Part-CAMO alone has no maintenance: no Release to Service, Planning
    or Logistics. Every other set of approvals of this build sees the lot.
    """
    shown = navigation.shown(of_the_board(), approvals=held, may=lambda action: True)
    expected = [
        (group, [label for label, _ in items if label not in hidden])
        for group, items in BOARD
        if any(label not in hidden for label, _ in items)
    ]
    assert labels(shown) == expected
    if held == {CAMO}:
        # A group with no item left is not shown.
        assert "Planning" not in dict(expected)
        assert "Logistics" not in dict(expected)


def test_no_approval_held_shows_nothing() -> None:
    """REQ-201. An organisation whose approvals have all ended is shown no section."""
    assert navigation.shown(of_the_board(), approvals=set(), may=lambda action: True) == []


def test_an_item_is_not_shown_to_a_user_whose_roles_do_not_permit_it() -> None:
    """REQ-006, REQ-201. The role matrix still decides; an approval held does not add to it."""
    shown = navigation.shown(navigation.BOARD, approvals=EVERY, may=lambda action: False)
    assert shown == []


def test_only_what_is_built_is_in_the_sidebar() -> None:
    """REQ-201. An item appears once its page is built, and a tab once its view is."""
    built = {item.label for group in navigation.GROUPS for item in group.items}
    every = {item.label for group in navigation.BOARD for item in group.items}
    assert built < every
    for group in navigation.GROUPS:
        for item in group.items:
            assert item.address is not None
            assert reverse(item.address).startswith("/"), item.label
            for tab in item.tabs:
                assert tab.address is not None
                assert reverse(tab.address).startswith("/"), tab.label
    not_built = [item for group in navigation.BOARD for item in group.items if item.address is None]
    assert {"Hazard Log", "Marketplace", "Help"} <= {item.label for item in not_built}
    for item in not_built:
        assert item.inside == frozenset(), item.label
        assert all(tab.address is None for tab in item.tabs), item.label


@pytest.mark.django_db
def test_a_page_shows_the_sections_of_the_approvals_held() -> None:
    """REQ-201. The page reads the approvals held now, not the one set up with."""
    sample = make_sample()
    client = signed_in(sample.reader)
    body = client.get("/", secure=True).content.decode()
    assert "<h2>Continuing Airworthiness</h2>" in body
    with working_for(sample.ours.id, sample.administrator.id):
        # Not possible on a page: the approval an organisation was set up with is not ended there.
        Approval.objects.filter(organisation=sample.ours).update(
            no_longer_held_on=date(2026, 11, 18)
        )
    body = client.get("/", secure=True).content.decode()
    sidebar = body.split('<nav aria-label="Sections">', 1)[1].split("</nav>", 1)[0]
    assert "<h2>" not in sidebar
    assert "<a " not in sidebar
