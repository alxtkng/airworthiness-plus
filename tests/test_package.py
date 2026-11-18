"""Checks on the rules package itself."""

import ast
from pathlib import Path

import airworthiness_rules

PACKAGE = Path(airworthiness_rules.__file__).parent
FORBIDDEN = {"django", "psycopg"}


def test_rules_package_imports_no_framework_or_database() -> None:
    """ADR-0001: the rules package has no Django or database imports."""
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert name.split(".")[0] not in FORBIDDEN, f"{path.name} imports {name}"
