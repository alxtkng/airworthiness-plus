"""Every form route has a named browser scenario or an explicit coverage gap."""

import ast
import csv
from pathlib import Path

from airworthiness_plus.interface.field_rules import WRITES


def test_every_form_route_is_in_the_browser_inventory() -> None:
    directory = Path(__file__).parent / "e2e"
    with (directory / "form-coverage.tsv").open(encoding="utf-8", newline="") as manifest:
        rows = list(csv.DictReader(manifest, delimiter="\t"))
    routes = [row["Route"] for row in rows]
    assert len(routes) == len(set(routes))
    assert set(routes) == set(WRITES)
    scenarios = {
        node.name
        for module in directory.glob("test_*.py")
        for node in ast.parse(module.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }
    for row in rows:
        notes = row["Scenario or gap"]
        if row["Route"] == "retire_task":
            assert notes == "No on-screen retirement control on the maintenance programme page"
        else:
            assert set(notes.split(", ")) <= scenarios, row
