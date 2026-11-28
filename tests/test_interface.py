"""The interface: tokens, navigation, tables, status marks and the words on the page.

REQ-190, REQ-193 to REQ-196; design-system/README.md, Components.md and
Writing.md. What cannot be checked by a test is inspected at the readiness
review.
"""

import json
import re
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders
from django.test import Client
from django.urls import get_resolver

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.interface import navigation
from airworthiness_plus.interface.formatting import STATUS_MARKS
from tests.support import (
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    dot,
    page,
    signed_in,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src" / "airworthiness_plus"
TOKENS = json.loads((ROOT / "design-system" / "tokens.json").read_text(encoding="utf-8"))
STYLES = (SOURCE / "interface" / "static" / "interface" / "app.css").read_text(encoding="utf-8")
TEMPLATES = sorted(SOURCE.glob("*/templates/**/*.html"))


# Tokens (REQ-196)


def properties(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block))


def test_every_colour_space_radius_and_line_is_a_token() -> None:
    """REQ-196. The stylesheet's custom properties are the tokens, value for value."""
    light = properties(STYLES.split(":root {", 1)[1].split("}", 1)[0])
    after = STYLES.split("prefers-color-scheme: dark", 1)[1]
    dark = properties(after.split(":root {", 1)[1].split("}", 1)[0])
    for token in TOKENS["color"]["tokens"]:
        value = token["value"]
        if isinstance(value, str):
            assert light[token["name"]] == value, token["name"]
            assert token["name"] not in dark
        else:
            assert light[token["name"]] == value["light"], token["name"]
            assert dark[token["name"]] == value["dark"], token["name"]
    for group in ("spacing", "radius", "border"):
        for token in TOKENS[group]["tokens"]:
            assert light[token["name"]] == token["value"], token["name"]
    assert light["sans"] == TOKENS["type"]["families"]["sans"]
    assert light["mono"] == TOKENS["type"]["families"]["mono"]


def test_no_colour_is_written_outside_the_tokens() -> None:
    """REQ-196. A page never invents its own colour: every colour below the tokens is a token."""
    rules = STYLES.split("*,\n*::before", 1)[1]
    assert re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", rules) == []
    for template in TEMPLATES:
        text = template.read_text(encoding="utf-8")
        assert "style=" not in text, template.name
        assert "<style" not in text, template.name


def test_the_type_sizes_are_those_of_the_tokens() -> None:
    """REQ-196. Heading 24 and 16, Label 14 and 13, as the tokens give them."""
    styles = {
        style["name"]: style for group in TOKENS["type"]["groups"] for style in group["styles"]
    }
    heading = STYLES.split("\nh1 {", 1)[1].split("}", 1)[0]
    for name in ("fontSize", "lineHeight", "letterSpacing"):
        assert styles["heading-24"][name] in heading
    section = STYLES.split("\nh2 {", 1)[1].split("}", 1)[0]
    for name in ("fontSize", "lineHeight", "letterSpacing"):
        assert styles["heading-16"][name] in section
    html = STYLES.split("\nhtml {", 1)[1].split("}", 1)[0]
    assert styles["label-14"]["fontSize"] in html
    assert styles["label-14"]["lineHeight"] in html
    assert "tabular-nums" in html


def test_the_fonts_stylesheet_and_script_are_the_applications_own() -> None:
    """ADR-0001, threat TH-005. Nothing is asked of another site."""
    for name in (
        "interface/app.css",
        "interface/app.js",
        "interface/fonts/Geist-Variable.woff2",
        "interface/fonts/GeistMono-Variable.woff2",
        "interface/fonts/LICENSE.txt",
    ):
        assert finders.find(name), name
    for font in TOKENS["type"]["fonts"]:
        assert f'url("{font["file"]}")' in STYLES
    script = (SOURCE / "interface" / "static" / "interface" / "app.js").read_text()
    for text in [STYLES, script, *(t.read_text(encoding="utf-8") for t in TEMPLATES)]:
        # The one address is the name of the SVG format, which is not fetched.
        assert re.findall(r"https?://(?!www\.w3\.org/2000/svg)", text) == []
        assert re.findall(r"""["'(]//""", text) == []
    # A page carries no script of its own: only the one file (threat TH-004).
    for template in TEMPLATES:
        text = template.read_text(encoding="utf-8")
        assert re.findall(r"<script(?![^>]*\bsrc=)", text) == [], template.name
        assert re.findall(r"\bon[a-z]+=\"", text) == [], template.name


# Navigation (README, Navigation)


def test_every_address_has_its_place() -> None:
    """REQ-196. Every address belongs to one sidebar item, or to the person."""
    names = {pattern.name for pattern in get_resolver().url_patterns if pattern.name}  # type: ignore[union-attr]
    for name in sorted(names):
        placed = [item for group in navigation.GROUPS for item in group.items if item.holds(name)]
        if name in navigation.OUTSIDE:
            assert placed == [], name
        else:
            assert len(placed) == 1, name
    listed = {
        address
        for group in navigation.GROUPS
        for item in group.items
        for address in ({item.address} | {tab.address for tab in item.tabs} | item.inside)
    }
    assert listed | navigation.OUTSIDE == names


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    add_sample_reviews(sample, fleet)
    return fleet


@pytest.mark.django_db
def test_the_sidebar_the_breadcrumb_and_the_tabs_say_where_a_page_is(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-196. One element for each job; the current place is marked for screen readers."""
    client = signed_in(sample.reader)
    body = page(client, "/reviews/")
    assert '<link rel="stylesheet" href="/static/interface/app.css">' in body
    assert '<script src="/static/interface/app.js" defer></script>' in body
    sidebar = body.split('<nav aria-label="Sections">', 1)[1].split("</nav>", 1)[0]
    assert re.findall(r"<h2>([^<]+)</h2>", sidebar) == [
        "Continuing Airworthiness",
        "Planning",
        "Logistics",
        "People",
        "Documentation",
        "Organisation",
        "Commercial",
    ]
    assert re.findall(r'<a href="[^"]+"(?: aria-current="page")?>([^<]+)</a>', sidebar) == [
        "Dashboard",
        "Aircraft",
        "Defects",
        "Maintenance Programmes",
        "Aircraft Configuration",
        "Release to Service",
        "Contracts",
        "Work Packages",
        "Staffing and Capacity",
        "Goods In",
        "Suppliers",
        "Staff",
        "Authorisations",
        "Maintenance Data",
        "Approval and Scope",
        "Records",
        "Customers",
        "Settings",
    ]
    assert '<a href="/" aria-current="page">Aircraft</a>' in sidebar
    assert sidebar.count("aria-current") == 1
    crumb = body.split('aria-label="Location"', 1)[1].split("</nav>", 1)[0]
    assert "<li>Continuing Airworthiness</li>" in crumb
    assert '<li><a href="/" aria-current="location">Aircraft</a></li>' in crumb
    tabs = body.split('<nav class="tabs" aria-label="Views">', 1)[1].split("</nav>", 1)[0]
    assert re.findall(r">([^<]+)</a>", tabs) == [
        "All Aircraft",
        "Airworthiness Reviews",
        "Transfers",
    ]
    assert '<a href="/reviews/" aria-current="page">Airworthiness Reviews</a>' in tabs
    # A section page keeps its heading for screen readers and does not show it.
    assert '<h1 class="visually-hidden">Airworthiness Reviews</h1>' in body
    # The Administrator also has Users; nobody else is shown it.
    assert ">Users</a>" not in body
    assert ">Users</a>" in page(signed_in(sample.administrator), "/organisation/")


@pytest.mark.django_db
def test_a_record_page_shows_the_record_its_type_and_its_own_tabs(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-191, REQ-196. Heading 24 is the registration, with the type rating under it."""
    client = signed_in(sample.reader)
    ejkl = fleet["G-EJKL"]
    for path, active in (
        (f"/aircraft/{ejkl.id}/", "Record"),
        (f"/aircraft/{ejkl.id}/programme/", "Maintenance Programme"),
        (f"/aircraft/{ejkl.id}/directives/", "Airworthiness Directives"),
        (f"/aircraft/{ejkl.id}/maintenance-data/", "Maintenance Data"),
        (f"/aircraft/{ejkl.id}/review/", "Airworthiness Review"),
    ):
        body = page(client, path)
        assert "<h1>G-EJKL</h1>\n<p>Cessna/Reims-Cessna 152/F152 Series (Lycoming)</p>" in body, (
            path
        )
        tabs = body.split('aria-label="Views of G-EJKL">', 1)[1].split("</nav>", 1)[0]
        assert re.findall(r'aria-current="page">([^<]+)</a>', tabs) == [active], path
        assert 'aria-label="Views">' not in body, path
        assert '<li><a href="/" aria-current="location">Aircraft</a></li>' in body


@pytest.mark.django_db
def test_pages_before_sign_in_have_no_navigation() -> None:
    """Threat TH-001. Nothing of the application is shown to someone who has not signed in."""
    body = page(Client(), "/sign-in/")
    assert '<main id="content" class="alone">' in body
    assert "Sections" not in body
    assert 'class="sidebar"' not in body


# Status (REQ-193)


def test_a_status_colour_always_has_its_word() -> None:
    """REQ-193. Amber for due soon or waiting, red for overdue or unserviceable, green once."""
    assert dot("Due Soon") == '<span class="status status-due">Due Soon</span>'
    assert {word for word, mark in STATUS_MARKS.items() if mark == "ok"} == {"Serviceable"}
    assert {word for word, mark in STATUS_MARKS.items() if mark == "stop"} == {
        "Overdue",
        "Unserviceable",
    }
    # The colours are used for the dot and nowhere else.
    for name in ("status-ok", "status-due", "status-stop"):
        uses = re.findall(rf"([a-z-]+):\s*var\(--{name}\)", STYLES)
        assert set(uses) == {"background"}, name
    assert STYLES.count("var(--status-ok)") == 1


@pytest.mark.django_db
def test_the_fleet_marks_what_needs_attention(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-193. G-DGHI is Unserviceable; the others are Serviceable, in the Status column."""
    body = page(signed_in(sample.reader), "/")
    assert body.count('<span class="status status-stop">Unserviceable</span>') == 1
    assert body.count('<span class="status status-ok">Serviceable</span>') == 5


# Tables (REQ-194)


def test_a_table_is_one_line_for_each_row_and_opens_on_click() -> None:
    """REQ-194. The script makes each row one line with a button that opens its detail."""
    script = (SOURCE / "interface" / "static" / "interface" / "app.js").read_text()
    for needed in ('"aria-expanded"', '"Show Details"', '"Details"', "colSpan", "cloneNode"):
        assert needed in script, needed
    compact = STYLES.split(".js table.compact td {", 1)[1].split("}", 1)[0]
    assert "white-space: nowrap" in compact
    assert "text-overflow: ellipsis" in compact
    # A table without the script still shows everything: nothing is hidden by the stylesheet alone.
    assert re.findall(r"^(?!\.js )[^\n{]*\.in-detail[^{]*\{", STYLES, flags=re.M) == []


# Words (REQ-190, REQ-195)

SMALL = {
    "a", "an", "and", "as", "at", "but", "by", "for", "if", "in", "nor", "of", "on", "or",
    "per", "the", "to", "via", "with",
}  # fmt: skip
# Written as the regulation or the form writes them.
AS_WRITTEN = {"SHA-256", "ML.A.903(b)", "ML.A.903(e)(3)", "CAO.A.045(c)", "%"}


def label_problems(label: str) -> list[str]:
    """Return what is wrong with a label under design-system/Writing.md.

    Title Case, with the joining words in lower case except as the first
    or last word. A comma or a colon joins two labels, each read on its own.
    """
    problems: list[str] = []
    text = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", "X", label)
    text = re.sub(r"&#8217;", "\N{RIGHT SINGLE QUOTATION MARK}", text).strip()
    if not text or text == "X":
        return problems
    if text.endswith("."):
        problems.append("ends with a full stop")
    if "\N{MIDDLE DOT}" in text:
        problems.append("has a middle dot")
    if "EASA Form" in text:
        problems.append("names a form as EASA's")
    for segment in re.split(r"[,:]", text):
        words = segment.split()
        for position, word in enumerate(words):
            parts = word.split("-")
            for index, part in enumerate(parts):
                bare = part.strip("()[]\N{RIGHT SINGLE QUOTATION MARK}'")
                if not bare or not bare[0].isalpha() or word in AS_WRITTEN:
                    continue
                first = position == 0 and index == 0
                last = position == len(words) - 1 and index == len(parts) - 1
                if bare.lower() in SMALL and not (first or last):
                    if bare != bare.lower():
                        problems.append(f"{bare} is a joining word")
                elif not bare[0].isupper():
                    problems.append(f"{bare} has no capital")
    return problems


def labels() -> list[tuple[str, str]]:
    found = []
    tags = r"<(th|dt|button|h1|h2|h3|summary|label)\b[^>]*>(.*?)</\1>"
    for template in TEMPLATES:
        text = template.read_text(encoding="utf-8")
        for _, inner in re.findall(tags, text, flags=re.S):
            plain = re.sub(r"<[^>]+>", "", inner)
            found.append((f"{template.parent.name}/{template.name}", plain))
        for inner in re.findall(r"<a\b[^>]*>([^<{]+)</a>", text):
            found.append((f"{template.parent.name}/{template.name}", inner))
    for source in sorted(SOURCE.glob("**/*.py")):
        if "migrations" in source.parts:
            continue
        code = source.read_text(encoding="utf-8")
        for label in re.findall(r'\blabel="([^"]+)"', code):
            found.append((source.name, label))
    for group in navigation.GROUPS:
        found.append(("navigation", group.label))
        for item in group.items:
            found.append(("navigation", item.label))
            found += [("navigation", tab.label) for tab in item.tabs]
    return found


def test_every_label_is_title_case_with_no_full_stop() -> None:
    """REQ-190, REQ-195. Headings, table headers, buttons, links, tabs and form labels."""
    found = labels()
    assert len(found) > 300
    wrong = [
        f"{where}: {label!r}: {', '.join(problems)}"
        for where, label in found
        if (problems := label_problems(label))
    ]
    assert wrong == []


def test_the_check_of_labels_finds_what_it_should() -> None:
    """The check above is itself checked, so that it cannot pass by finding nothing."""
    assert label_problems("Aircraft Registration") == []
    assert label_problems("Record as Unserviceable") == []
    assert label_problems("Pilot-in-Command") == []
    assert label_problems("Manufacturer&#8217;s Designation") == []
    assert label_problems("Export the Record of {{ one.registration }}") == []
    assert label_problems("Aircraft registration") == ["registration has no capital"]
    assert label_problems("Record As Unserviceable") == ["As is a joining word"]
    assert label_problems("Saved.") == ["ends with a full stop"]
    assert label_problems("EASA Form 1") == ["names a form as EASA's"]


def test_no_page_names_a_form_as_easas_or_abbreviates_a_certificate() -> None:
    """REQ-195, Writing.md. CAA Form 15c, and airworthiness review certificate in full."""
    for path in [*TEMPLATES, *sorted(SOURCE.glob("**/*.py"))]:
        if "migrations" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "EASA Form" not in text, path.name
    for template in TEMPLATES:
        shown = re.sub(r"\{\{.*?\}\}|\{%.*?%\}|<[^>]+>", " ", template.read_text(encoding="utf-8"))
        for short in (" ARC ", " CRS ", " AMP ", " CAMO ", " AD ", " ADs "):
            assert short not in f" {shown} ", f"{template.name}: {short.strip()}"
