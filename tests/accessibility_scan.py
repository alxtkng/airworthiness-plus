"""The automated accessibility scan: axe-core in a real browser (REQ-383 to REQ-404).

axe-core finds about a third of what WCAG asks, by its makers' own account.
What it cannot see is listed in design-system/Accessibility.md, Manual Pass,
and is checked by a person with a keyboard and a screen reader.
"""

from typing import Any

from axe_playwright_python.sync_playwright import Axe  # type: ignore[import-untyped]

# WCAG 2.0, 2.1 and 2.2 at Levels A and AA: the standard of every page (REQ-383).
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"]

AXE = Axe()


def violations(page: Any) -> list[str]:
    """Every rule broken on the page as it stands, one line each with where."""
    results = AXE.run(
        page,
        options={"runOnly": {"type": "tag", "values": TAGS}, "resultTypes": ["violations"]},
    )
    found = []
    for violation in results.response["violations"]:
        for node in violation["nodes"]:
            found.append(f"{violation['id']}: {node['target']} {node.get('failureSummary', '')}")
    return found
