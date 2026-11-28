"""The design canvas meets the same rules as the application (REQ-383 to REQ-404).

Each canvas page carries its colours in the ``t`` object of its script, one
for light and one for dark. Every pair a page uses for text, and every edge of
a control, is recalculated here, and the markup is checked for the parts a
page needs: language, skip link, main landmark, focus ring, reduced motion,
named tables and visible search labels. The pages render only in the Design
editor, so nothing here runs them.
"""

import re
from pathlib import Path

import pytest

from tests.test_accessibility import ratio

CANVAS = Path(__file__).resolve().parent.parent / "canvas"
PAGES = sorted(CANVAS.glob("*.dc.html"))
SHARED = {"Sidebar.dc.html", "Tabs.dc.html", "TopBar.dc.html"}
WRAPPERS = {"Dark.dc.html", "DisplayDark.dc.html"}


def themes(text: str) -> list[dict[str, str]]:
    """The ``t`` objects of a page: ``const t = dark ? { ... } : { ... };``."""
    found = re.search(r"const t = dark\s*\?\s*(\{[^}]*\})\s*:\s*(\{[^}]*\})", text)
    if not found:
        return []
    return [dict(re.findall(r"(\w+): '(#[0-9A-Fa-f]{6})'", part)) for part in found.groups()]


@pytest.mark.parametrize("path", PAGES, ids=lambda path: path.name)
def test_every_canvas_colour_pair_meets_its_contrast(path: Path) -> None:
    """REQ-383, REQ-384 (SC 1.4.3, 1.4.11), light and dark."""
    low = []
    for t in themes(path.read_text(encoding="utf-8")):
        surfaces = [t[name] for name in ("bg", "sidebar", "field", "active") if name in t]
        for text in ("text", "muted", "body", "nav"):
            for surface in surfaces:
                if text in t and ratio(t[text], surface) < 4.5:
                    low.append(f"{text} {t[text]} on {surface}")
        for edge in ("sBorder", "control"):
            for surface in surfaces:
                if edge in t and ratio(t[edge], surface) < 3:
                    low.append(f"{edge} {t[edge]} on {surface}")
        if "pBg" in t and ratio(t["pBg"], t["pFg"]) < 4.5:
            low.append("primary button")
    assert low == []


@pytest.mark.parametrize(
    "path", [path for path in PAGES if path.name not in WRAPPERS], ids=lambda path: path.name
)
def test_every_canvas_page_has_its_structure(path: Path) -> None:
    """REQ-390, REQ-393, REQ-395, REQ-396, REQ-402, REQ-403, REQ-404."""
    text = path.read_text(encoding="utf-8")
    assert '<html lang="en-GB">' in text
    assert ":focus-visible{outline:2px solid var(--focus);outline-offset:2px}" in text
    if path.name in SHARED:
        return
    assert '<a class="skip" href="#main">Skip to Main Content</a>' in text
    assert '<main id="main"' in text
    assert "prefers-reduced-motion: reduce" in text
    assert text.count("<h1") == 1
    for table in re.findall(r"<table\b[^>]*>", text):
        assert "aria-labelledby=" in table or "aria-label=" in table, table[:80]
    # A search box keeps its visible Search label; a placeholder never stands in for one.
    for field in re.findall(r'<input type="search"[^>]*>', text):
        assert "aria-label=" not in field, field[:80]
    assert "sBorder: '#EBEBEB'" not in text and "sBorder: '#2E2E2E'" not in text


def test_the_sidebar_search_has_a_visible_label_and_a_control_edge() -> None:
    """REQ-384, REQ-396."""
    text = (CANVAS / "Sidebar.dc.html").read_text(encoding="utf-8")
    assert "<span>Search</span>" in text
    assert 'aria-label="Search aircraft' not in text
    assert "border: 1px solid {{t.control}}" in text


def test_the_marketplace_count_is_a_status_message() -> None:
    """REQ-403 (SC 4.1.3). The count of results is read out when a filter changes it."""
    text = (CANVAS / "Marketplace.dc.html").read_text(encoding="utf-8")
    assert '<span role="status"' in text and "{{countLabel}}</span>" in text


def test_the_display_page_is_a_settings_tab_in_both_themes() -> None:
    """REQ-405 to REQ-410. Display sits under Settings; DisplayDark shows it dark."""
    tabs = (CANVAS / "Tabs.dc.html").read_text(encoding="utf-8")
    assert "['display', 'Display', 'Display.dc.html']" in tabs
    dark = (CANVAS / "DisplayDark.dc.html").read_text(encoding="utf-8")
    assert '<dc-import name="Display" dark="{{true}}"' in dark
    display = (CANVAS / "Display.dc.html").read_text(encoding="utf-8")
    assert 'id="compact-h"' in display and 'id="comfortable-h"' in display
    assert "width: 44px; height: 44px" in display
