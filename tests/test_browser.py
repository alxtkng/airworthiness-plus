"""The table script, run in a real browser (REQ-194; design-system/Components.md).

Each page is made by the application as in every other test. It is then
given to a browser with the stylesheet, the script and the response's own
headers, so the Content Security Policy applies as it does in service. No
server is started, and the browser reaches nothing but what this test hands
it.

The browser is the one named by AIRWORTHINESS_BROWSER, or the one installed
beside the tests, or the Chrome on the machine. In the pipeline a missing
browser fails the test; elsewhere the test is skipped and says so.
"""

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.test import Client
from playwright.sync_api import (
    BrowserType,
    ConsoleMessage,
    Error,
    Page,
    Route,
    sync_playwright,
)

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    make_sample,
    signed_in,
)

pytestmark = pytest.mark.django_db

ORIGIN = "https://airworthiness.test"
INSTALLED = Path("/opt/pw-browsers/chromium")


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


@pytest.fixture
def sample() -> Sample:
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    add_sample_reviews(sample, fleet)
    return fleet


def made(client: Client, path: str) -> HttpResponse:
    response = client.get(path, secure=True)
    assert response.status_code == 200, path
    return response  # type: ignore[return-value]


def launch(chromium: BrowserType):  # type: ignore[no-untyped-def]
    named = os.environ.get("AIRWORTHINESS_BROWSER")
    if named:
        return chromium.launch(executable_path=named)
    if INSTALLED.exists():
        return chromium.launch(executable_path=str(INSTALLED))
    return chromium.launch(channel="chrome")


def in_browser(
    pages: Mapping[str, HttpResponse],
    check: Callable[[Page], None],
    *,
    width: int = 1280,
    script: bool = True,
) -> None:
    """Open a browser that is served only ``pages`` and the static files, and run ``check``.

    The pages are made before this is called: the browser's event loop and
    the database do not share a thread happily.
    """
    problems: list[str] = []

    def serve(route: Route) -> None:
        path = urlsplit(route.request.url).path
        if path in pages:
            response = pages[path]
            route.fulfill(status=200, headers=dict(response.headers), body=response.content)
            return
        found = finders.find(path.removeprefix("/static/")) if path.startswith("/static/") else None
        if found:
            route.fulfill(path=found)
        else:
            problems.append(f"asked for {path}")
            route.fulfill(status=404, body="")

    def heard(message: ConsoleMessage) -> None:
        if message.type == "error":
            problems.append(message.text)

    with sync_playwright() as driver:
        try:
            browser = launch(driver.chromium)
        except Error as error:
            if os.environ.get("CI"):
                raise
            pytest.skip(f"No browser to run the script in: {error.message.splitlines()[0]}")
        try:
            context = browser.new_context(
                viewport={"width": width, "height": 900}, java_script_enabled=script
            )
            context.route("**/*", serve)
            page = context.new_page()
            page.on("console", heard)
            page.on("pageerror", lambda error: problems.append(str(error)))
            check(page)
        finally:
            browser.close()
    # Nothing was refused by the Content Security Policy, and nothing else was asked for.
    assert problems == []


def data_rows(page: Page):  # type: ignore[no-untyped-def]
    return page.locator("main table.compact tbody tr:not(.detail)")


def heights(page: Page) -> list[float]:
    return [
        round(box["height"], 1)
        for box in data_rows(page).evaluate_all(
            "rows => rows.map(row => ({height: row.getBoundingClientRect().height}))"
        )
    ]


def test_each_row_of_the_fleet_is_one_line_at_any_width(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-194. Six aircraft, six rows of one line each; nothing wraps when the
    window is narrow, and what does not fit ends in an ellipsis."""
    pages = {"/": made(signed_in(sample.reader), "/")}
    seen: dict[int, list[float]] = {}

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}/")
        assert page.locator("html.js").count() == 1
        assert data_rows(page).count() == 6
        seen[page.viewport_size["width"]] = heights(page)  # type: ignore[index]
        wrapping = page.locator("main table.compact tbody tr:not(.detail) td").evaluate_all(
            """cells => cells.filter(cell => {
                const style = getComputedStyle(cell);
                return style.display !== 'none'
                    && (style.whiteSpace !== 'nowrap' || style.textOverflow !== 'ellipsis');
            }).length"""
        )
        assert wrapping == 0
        # One line: the text of a cell is no taller than one line of it.
        tall = page.locator("main table.compact tbody tr:not(.detail) td").evaluate_all(
            """cells => cells.filter(cell => {
                const style = getComputedStyle(cell);
                if (style.display === 'none' || !cell.textContent.trim()) return false;
                const range = document.createRange();
                range.selectNodeContents(cell);
                return range.getBoundingClientRect().height > 1.5 * parseFloat(style.lineHeight);
            }).length"""
        )
        assert tall == 0

    for width in (1280, 700, 360):
        in_browser(pages, check, width=width)
    assert len(set(seen[1280])) == 1  # every row the same height
    assert seen[700] == seen[1280]
    assert seen[360] == seen[1280]


def test_a_row_opens_on_click_and_by_keyboard(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-194; Components.md, Expandable Rows. The button says whether the row
    is open; the detail holds every column, with those kept out of the row."""
    pages = {"/": made(signed_in(sample.reader), "/")}

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}/")
        table = page.locator("main table.compact").first
        headings = table.locator("thead th").all_text_contents()
        assert headings[0].strip() == "Details"
        hidden = table.locator("thead th.in-detail")
        assert hidden.count() >= 1
        assert all(not heading.is_visible() for heading in hidden.all())
        row = data_rows(page).first
        button = row.get_by_role("button", name="Show Details")
        assert button.get_attribute("aria-expanded") == "false"
        assert page.locator("tr.detail").count() == 0

        button.click()
        assert button.get_attribute("aria-expanded") == "true"
        detail = page.locator("tr.detail")
        assert detail.count() == 1
        assert detail.is_visible()
        # The detail follows its row and spans the table.
        assert row.evaluate("row => row.nextElementSibling.className") == "detail"
        shown = table.locator("thead th:not(.in-detail)").count()
        assert detail.locator("td").get_attribute("colspan") == str(shown)
        # Every column with a value is there by its heading, the hidden ones too.
        terms = detail.locator("dt").all_text_contents()
        assert set(terms) <= set(headings[1:])
        assert set(hidden.all_text_contents()) & set(terms)
        assert all(text.strip() for text in detail.locator("dd").all_text_contents())

        button.click()
        assert button.get_attribute("aria-expanded") == "false"
        assert not detail.is_visible()

        button.focus()
        page.keyboard.press("Enter")
        assert (button.get_attribute("aria-expanded"), detail.is_visible()) == ("true", True)
        page.keyboard.press("Space")
        assert (button.get_attribute("aria-expanded"), detail.is_visible()) == ("false", False)
        # Opening one row leaves the others one line each.
        button.click()
        assert len(set(heights(page))) == 1

    in_browser(pages, check)


def test_a_form_in_a_table_is_moved_to_the_detail_not_copied(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-194. A column that holds a form is shown only in the detail, and there
    is still one of each control on the page, with its forgery token."""
    path = "/review-staff/"
    pages = {path: made(signed_in(sample.administrator), path)}
    before = pages[path].content.decode().count('name="months"')
    assert before == 2  # one for each of the two review staff

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}{path}")
        row = data_rows(page).first
        assert row.locator("form").count() >= 1
        assert not row.locator("form").first.is_visible()
        row.get_by_role("button", name="Show Details").click()
        detail = page.locator("tr.detail")
        form = detail.locator("form").first
        assert form.is_visible()
        assert form.locator('input[name="csrfmiddlewaretoken"]').count() == 1
        assert form.get_attribute("action").startswith("/review-staff/")  # type: ignore[union-attr]
        # Moved, not copied.
        assert row.locator("form").count() == 0
        assert page.locator('main table input[name="months"]').count() == before

    in_browser(pages, check)


def test_a_plain_table_and_a_page_without_the_script_show_everything(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-194. A table marked plain is left alone. With no script, every cell
    of every table is shown: nothing depends on the script to be read."""
    lucy = signed_in(sample.lucy)
    pages = {"/": made(lucy, "/"), "/imports/": made(lucy, "/imports/")}

    def plain(page: Page) -> None:
        page.goto(f"{ORIGIN}/imports/")
        assert page.locator("main table[data-plain]").count() == 1
        assert page.locator("main table[data-plain].compact").count() == 0
        assert page.locator("main table[data-plain] .disclosure").count() == 0

    def without(page: Page) -> None:
        page.goto(f"{ORIGIN}/")
        assert page.locator("html.js").count() == 0
        assert page.locator("main table.compact").count() == 0
        cells = page.locator("main table tbody td")
        assert cells.count() > 0
        assert all(cell.is_visible() for cell in cells.all())
        headings = page.locator("main table thead th")
        assert all(heading.is_visible() for heading in headings.all())

    in_browser(pages, plain)
    in_browser(pages, without, script=False)


def test_how_a_figure_was_worked_out_opens_inside_a_row(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-139, REQ-194. The working of a figure is kept out of the row, takes the
    full width of the detail, and opens to show its rule, its inputs and its source."""
    path = "/review-staff/"
    pages = {path: made(signed_in(sample.reader), path)}

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}{path}")
        row = data_rows(page).first
        summary = page.get_by_text("How Recency Was Worked Out", exact=True)
        assert not summary.first.is_visible()
        row.get_by_role("button", name="Show Details").click()
        detail = page.locator("tr.detail")
        wide = detail.locator("dl > div.wide")
        assert wide.count() == 1
        assert wide.locator("dt").first.text_content() == "How It Was Worked Out"
        # Full width: as wide as the list it sits in, where the other values share a line.
        widths = detail.evaluate(
            """row => [row.querySelector('dl > div.wide').getBoundingClientRect().width,
                       row.querySelector('dl').getBoundingClientRect().width,
                       row.querySelector('dl > div:not(.wide)').getBoundingClientRect().width]"""
        )
        assert widths[0] == widths[1]
        assert widths[2] < widths[1] / 2
        source = wide.get_by_text("AMC1 CAO.A.045(c) and (d)", exact=True)
        assert not source.is_visible()
        wide.locator("summary").click()
        assert source.is_visible()
        assert wide.get_by_text("Recency Rests On", exact=True).is_visible()

    in_browser(pages, check)
