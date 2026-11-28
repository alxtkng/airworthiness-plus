"""Accessibility: the rules every page meets, WCAG 2.2 Level AA (REQ-383 to REQ-410).

design-system/Accessibility.md sets out the rules and the audit. These tests
check what can be checked without a person:

- every colour pair of the stylesheet, recalculated from the stylesheet
  itself, in light and dark, standard and high contrast (SC 1.4.3, 1.4.6,
  1.4.11)
- the structure of every page the sample organisation reaches, as the
  server writes it: language, title, skip link, landmarks, one ``h1``, the
  order of headings, a label for every field and a scope for every column
  heading (SC 1.3.1, 2.4.1, 2.4.2, 2.4.6, 3.1.1, 3.3.2, 4.1.2)

The scan with axe-core in a real browser, at 320 pixels and in both colour
schemes, is in ``tests/test_browser.py``. A keyboard and screen reader pass by
a person is still needed; Accessibility.md lists what it covers.
"""

import re
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlsplit

import pytest
from django.test import Client

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.aircraft import services as aircraft_services
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    post,
    signed_in,
)

ROOT = Path(__file__).resolve().parent.parent
STYLES = (
    ROOT / "src" / "airworthiness_plus" / "interface" / "static" / "interface" / "app.css"
).read_text(encoding="utf-8")

# The title separator, an en dash: Decisions.md, Accessibility.
DASH = "\N{EN DASH}"

# Contrast (REQ-383, REQ-384, REQ-406)


def luminance(colour: str) -> float:
    """Relative luminance, as WCAG 2.2 defines it (Understanding SC 1.4.3)."""
    value = colour.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def declarations(text: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", text))


def themed(value: str) -> dict[str, str]:
    """Read ``light-dark(#a, #b)`` as both themes, or one colour as both."""
    found = re.fullmatch(r"light-dark\((#[0-9a-f]{6}), (#[0-9a-f]{6})\)", value.strip())
    if found:
        return {"light": found.group(1), "dark": found.group(2)}
    return {"light": value.strip(), "dark": value.strip()}


def palette(contrast: str) -> dict[str, dict[str, str]]:
    """Every colour of the stylesheet for one contrast setting, by theme."""
    standard = declarations(STYLES.split(":root {", 1)[1].split("}", 1)[0])
    colours = {name: value for name, value in standard.items() if "#" in value}
    if contrast == "high":
        colours |= declarations(
            STYLES.split(':root[data-contrast="high"] {', 1)[1].split("}", 1)[0]
        )
    return {name: themed(value) for name, value in colours.items()}


SURFACES = ("background-100", "background-200", "gray-100")
# Text: at least 4.5:1 (SC 1.4.3); 7:1 in high contrast for muted text (SC 1.4.6).
TEXT = ("gray-900", "gray-1000")
# What a person needs to see a control or its state: at least 3:1 (SC 1.4.11).
NON_TEXT = ("control-border", "focus-ring", "status-ok-edge", "status-due-edge", "status-stop-edge")


@pytest.mark.parametrize("contrast", ["standard", "high"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_every_colour_pair_meets_its_contrast(theme: str, contrast: str) -> None:
    """REQ-383, REQ-384, REQ-406. Recalculated from app.css; the thresholds are WCAG 2.2's."""
    colours = palette(contrast)
    low: list[str] = []
    for text in TEXT:
        need = 7.0 if contrast == "high" else 4.5
        for surface in (*SURFACES, "gray-200"):
            found = ratio(colours[text][theme], colours[surface][theme])
            if found < need:
                low.append(f"{text} on {surface} {found:.2f}")
    for mark in NON_TEXT:
        for surface in SURFACES:
            found = ratio(colours[mark][theme], colours[surface][theme])
            if found < 3.0:
                low.append(f"{mark} on {surface} {found:.2f}")
    # The primary button: background-100 text on a gray-1000 fill.
    found = ratio(colours["background-100"][theme], colours["gray-1000"][theme])
    if found < 4.5:
        low.append(f"primary button {found:.2f}")
    if contrast == "high":
        for line in ("gray-400", "control-border"):
            for surface in ("background-100", "background-200"):
                found = ratio(colours[line][theme], colours[surface][theme])
                if found < 7.0:
                    low.append(f"{line} on {surface} {found:.2f}")
    assert low == []


def test_the_divider_is_never_the_edge_of_a_control() -> None:
    """REQ-384. gray-400 is below 3:1, so inputs, selects and buttons use control-border."""
    assert ratio("#ebebeb", "#ffffff") < 3
    controls = STYLES.split("\nbutton,\n.button {", 1)[1].split("}", 1)[0]
    assert "var(--control-border)" in controls
    fields = STYLES.split('input:not([type="checkbox"])', 1)[1].split("}", 1)[0]
    assert "var(--control-border)" in fields


def test_focus_motion_and_targets_come_from_tokens() -> None:
    """REQ-390, REQ-391, REQ-395, REQ-408, REQ-409."""
    focus = STYLES.split("\n:focus-visible {", 1)[1].split("}", 1)[0]
    assert "var(--focus-width) solid var(--focus-ring)" in focus
    assert "var(--focus-offset)" in focus
    assert re.findall(r"transition:[^;]*", STYLES) == ["transition: transform var(--motion)"]
    reduced = STYLES.split("@media (prefers-reduced-motion: reduce)", 1)[1].split("}\n}", 1)[0]
    assert "--motion: 0ms" in reduced
    comfortable = STYLES.split(':root[data-density="comfortable"] {', 1)[1].split("}", 1)[0]
    assert "--target-minimum: 44px" in comfortable
    disclosure = STYLES.split("\n.disclosure button {", 1)[1].split("}", 1)[0]
    assert "width: var(--target-minimum)" in disclosure
    assert "@media (forced-colors: active)" in STYLES


# Structure of every page (REQ-393, REQ-394, REQ-396, REQ-402, REQ-404)


class Structure(HTMLParser):
    """What a page's markup says about its language, landmarks, headings and fields."""

    FIELDS = frozenset({"input", "select", "textarea"})
    UNLABELLED = frozenset({"hidden", "submit", "button", "reset", "image"})

    def __init__(self) -> None:
        super().__init__()
        self.lang = ""
        self.title = ""
        self.in_title = False
        self.first_in_body: tuple[str, dict[str, str]] | None = None
        self.in_body = False
        self.in_main = 0
        self.main = 0
        self.headings: list[int] = []
        self.label_for: set[str] = set()
        self.label_depth = 0
        self.fields: list[tuple[str, dict[str, str], bool]] = []
        self.in_head = 0
        self.headers: list[dict[str, str]] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        found = {name: value or "" for name, value in attributes}
        if tag == "html":
            self.lang = found.get("lang", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "body":
            self.in_body = True
        elif self.in_body and self.first_in_body is None:
            self.first_in_body = (tag, found)
        if tag == "main":
            self.main += 1
            self.in_main += 1
        if self.in_main and re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "label":
            self.label_depth += 1
            if "for" in found:
                self.label_for.add(found["for"])
        if tag in self.FIELDS and found.get("type", "") not in self.UNLABELLED:
            self.fields.append((tag, found, self.label_depth > 0))
        if tag == "thead":
            self.in_head += 1
        if tag == "th" and self.in_head:
            self.headers.append(found)
        if tag == "a" and "href" in found:
            self.links.append(found["href"])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "main":
            self.in_main -= 1
        elif tag == "label":
            self.label_depth -= 1
        elif tag == "thead":
            self.in_head -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data

    def problems(self) -> list[str]:
        found = []
        if self.lang != "en-GB":
            found.append(f"lang {self.lang!r}")
        title = " ".join(self.title.split())
        if (
            not title.endswith(f" {DASH} Airworthiness+")
            or title.startswith(DASH)
            or title.count("Airworthiness+") > 1
        ):
            found.append(f"title {title!r}")
        first = self.first_in_body
        if not first or first[0] != "a" or first[1].get("href") != "#content":
            found.append("skip link is not first")
        if self.main != 1:
            found.append(f"{self.main} main landmarks")
        if self.headings.count(1) != 1 or (self.headings and self.headings[0] != 1):
            found.append(f"headings {self.headings}")
        for before, after in zip(self.headings, self.headings[1:], strict=False):
            if after > before + 1:
                found.append(f"heading skips from h{before} to h{after}")
                break
        for tag, attributes, wrapped in self.fields:
            if not (
                wrapped
                or attributes.get("id", "") in self.label_for
                or "aria-labelledby" in attributes
            ):
                found.append(f"{tag} {attributes.get('name', '')!r} has no visible label")
        for header in self.headers:
            if header.get("scope") != "col":
                found.append("column heading without scope")
                break
        return found


@pytest.fixture
def sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)
    monkeypatch.setattr(sign_in, "today", lambda: TODAY)


def walk(
    client: Client, start: str = "/", limit: int = 600, least: int = 100
) -> dict[str, list[str]]:
    """Follow every link on the site from ``start``, once each, and check each page."""
    seen: set[str] = set()
    queue = deque([start])
    found: dict[str, list[str]] = {}
    while queue and len(seen) < limit:
        address = queue.popleft()
        if address in seen:
            continue
        seen.add(address)
        response = client.get(address, follow=True, secure=True)
        if response.status_code != 200 or "text/html" not in response.get("Content-Type", ""):
            continue
        structure = Structure()
        structure.feed(response.content.decode())
        if problems := structure.problems():
            found[address] = problems
        for link in structure.links:
            target, _ = urldefrag(link)
            parts = urlsplit(target)
            if not target or parts.scheme or parts.netloc or not target.startswith("/"):
                continue
            if "sign-out" in target or "export" in target or "download" in target:
                continue
            queue.append(target)
    assert len(seen) >= least, len(seen)
    return found


@pytest.mark.django_db
@pytest.mark.usefixtures("sample_day")
def test_every_page_has_its_structure(sample: Sample) -> None:
    """REQ-393, REQ-394, REQ-396, REQ-402, REQ-404. Every page the sample reaches, by role."""
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    add_sample_reviews(sample, fleet)
    found: dict[str, list[str]] = {}
    for user in (sample.lucy, sample.administrator):
        found |= walk(signed_in(user))
    found |= {
        path: problems
        for path, problems in walk(Client(), "/sign-in/", least=1).items()
        if path.startswith("/sign-in")
    }
    assert found == {}


def test_the_check_of_structure_finds_what_it_should() -> None:
    """The checker itself: each rule is broken once and found."""
    structure = Structure()
    structure.feed(
        '<html lang="en"><head><title>Airworthiness+</title></head><body><div></div>'
        "<main><h2>A</h2><h4>B</h4><input name=x><table><thead><tr><th>C</th></tr></thead></table>"
        "</main></body></html>"
    )
    problems = structure.problems()
    assert problems == [
        "lang 'en'",
        "title 'Airworthiness+'",
        "skip link is not first",
        "headings [2, 4]",
        "heading skips from h2 to h4",
        "input 'x' has no visible label",
        "column heading without scope",
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("sample_day")
def test_a_form_with_errors_opens_on_a_summary_that_links_to_each_field(sample: Sample) -> None:
    """REQ-397 (SC 3.3.1, 3.3.3). The GOV.UK pattern: a summary, then each message by its field."""
    response = post(signed_in(sample.lucy), "/aircraft/add/", registration="G-ABCD", hours="x")
    body = response.content.decode()
    assert response.status_code == 200
    summary = body.split('<div class="error-summary"', 1)[1].split("</div>", 1)[0]
    assert "data-error-summary" in summary and 'tabindex="-1"' in summary
    assert "<h2" in summary and "There Is a Problem" in summary
    targets = re.findall(r'<a href="#([^"]+)">', summary)
    assert targets
    for target in targets:
        # The field is there, says it is invalid, and is described by its own message.
        field = re.search(rf'<(?:input|select|textarea)[^>]*\bid="{target}"[^>]*>', body)
        assert field, target
        assert 'aria-invalid="true"' in field.group(0), target
        assert f'aria-describedby="{target}_error' in field.group(0) or (
            f"{target}_error" in field.group(0)
        ), target
        assert f'id="{target}_error"' in body, target
