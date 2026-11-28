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
from airworthiness_plus.history.session import working_for
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.reviews.models import ReviewStaff
from airworthiness_plus.sample import build
from tests.accessibility_scan import violations
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db

ORIGIN = "https://airworthiness.test"
INSTALLED = Path("/opt/pw-browsers/chromium")


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


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
    colour_scheme: str = "light",
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
                viewport={"width": width, "height": 900},
                java_script_enabled=script,
                color_scheme=colour_scheme,  # type: ignore[arg-type,unused-ignore]
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
    from airworthiness_plus.imports.models import LoadKind
    from tests.test_imports import FLEET_FILE, load

    lucy = signed_in(sample.lucy)
    records = FLEET_FILE.replace(b"G-ABCD", b"G-ZABC").replace(b"G-EJKL", b"G-ZEJK")
    loaded = load(sample, LoadKind.AIRCRAFT, records)
    report = f"/imports/{loaded.id}/"
    pages = {"/": made(lucy, "/"), report: made(lucy, report)}

    def plain(page: Page) -> None:
        page.goto(ORIGIN + report)
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
        assert widths[0] == pytest.approx(widths[1], abs=0.5)
        assert widths[2] < widths[1] / 2
        source = wide.get_by_text("AMC1 CAO.A.045(c) and (d)", exact=True)
        assert not source.is_visible()
        wide.locator("summary").click()
        assert source.is_visible()
        assert wide.get_by_text("Recency Rests On", exact=True).is_visible()

    in_browser(pages, check)


def column(page: Page, heading: str) -> list[str]:
    """Return the text of one column of the first table, row by row as shown."""
    return page.evaluate(  # type: ignore[no-any-return]
        """heading => {
            const table = document.querySelector('main table.compact');
            const heads = [...table.tHead.rows[0].cells].map(cell => cell.textContent.trim());
            const index = heads.indexOf(heading);
            return [...table.tBodies[0].rows]
                .filter(row => !row.classList.contains('detail'))
                .map(row => row.cells[index].textContent.trim());
        }""",
        heading,
    )


def test_a_table_sorts_by_a_column_as_dates_numbers_and_status(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-196; Components.md, Sorting. One click sorts ascending, a second
    descending, and only the sorted column says so. Dates sort as dates and
    numbers as numbers, not as text: 11,206.8 comes after 9,874.3, and 6
    December 2026 before 14 March 2027. A Status column sorts red first. A row
    that is open keeps its detail beneath it."""
    pages = {"/": made(signed_in(sample.reader), "/")}
    by_expiry = ["G-EJKL", "G-ABCD", "G-FMNO", "G-DGHI", "G-BXYZ", "G-CDEF"]
    by_hours = ["G-BXYZ", "G-FMNO", "G-ABCD", "G-CDEF", "G-DGHI", "G-EJKL"]

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}/")
        table = page.locator("main table.compact").first
        served = column(page, "Aircraft Registration")
        assert table.locator("thead th[aria-sort]").count() == 0

        expiry = table.get_by_role("button", name="Review Certificate Valid To")
        expiry.click()
        assert column(page, "Aircraft Registration") == by_expiry
        sorted_heads = table.locator("thead th[aria-sort]")
        assert sorted_heads.count() == 1
        assert sorted_heads.get_attribute("aria-sort") == "ascending"
        expiry.click()
        assert column(page, "Aircraft Registration") == by_expiry[::-1]
        assert sorted_heads.get_attribute("aria-sort") == "descending"

        table.get_by_role("button", name="Airframe Hours").click()
        assert column(page, "Aircraft Registration") == by_hours
        assert table.locator("thead th[aria-sort]").count() == 1
        assert sorted_heads.text_content().strip() == "Airframe Hours"  # type: ignore[union-attr]

        # Red first: the Unserviceable aircraft, then the rest in the order they were in.
        table.get_by_role("button", name="Status").click()
        assert column(page, "Aircraft Registration")[0] == "G-DGHI"

        # An open row takes its detail with it.
        first = data_rows(page).first
        first.get_by_role("button", name="Show Details").click()
        table.get_by_role("button", name="Aircraft Registration").click()
        assert column(page, "Aircraft Registration") == sorted(served)
        opened = page.locator("main table.compact tbody tr.open")
        assert opened.locator("td").nth(1).text_content().strip() == "G-DGHI"  # type: ignore[union-attr]
        assert opened.evaluate("row => row.nextElementSibling.className") == "detail"
        assert page.locator("tr.detail").is_visible()
        # Sorting by keyboard, and every row is still one line.
        expiry.focus()
        page.keyboard.press("Enter")
        assert column(page, "Aircraft Registration") == by_expiry
        assert len(set(heights(page))) == 1

    in_browser(pages, check)


def test_numbers_align_right_and_empty_cells_sort_last(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-196; Components.md, Data Table: numbers align right. A cell with
    nothing in it comes last whichever way the column is sorted."""
    build.add_directives(sample, fleet)
    path = f"/aircraft/{fleet['G-ABCD'].id}/directives/"
    pages = {"/": made(signed_in(sample.reader), "/"), path: made(signed_in(sample.reader), path)}

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}/")
        aligned = page.evaluate(
            """() => {
                const table = document.querySelector('main table.compact');
                const heads = [...table.tHead.rows[0].cells];
                const index = heads.findIndex(c => c.textContent.trim() === 'Airframe Hours');
                const body = [...table.tBodies[0].rows].map(row => row.cells[index]);
                const cells = [heads[index], ...body];
                const other = getComputedStyle(table.tBodies[0].rows[0].cells[1]).textAlign;
                return [cells.map(cell => getComputedStyle(cell).textAlign), other];
            }"""
        )
        assert set(aligned[0]) == {"right"}
        assert aligned[1] in ("left", "start")

        page.goto(f"{ORIGIN}{path}")
        due = page.locator("main table.compact").first.get_by_role("button", name="Next Due")
        due.click()
        ascending = column(page, "Next Due")
        due.click()
        descending = column(page, "Next Due")
        assert [bool(text) for text in ascending] == [True, True, False, False]
        assert [bool(text) for text in descending] == [True, True, False, False]
        assert ascending[:2] == descending[1::-1]

    in_browser(pages, check)


MINUS = "\u2212"  # the minus sign the application writes, not a hyphen


def mark(kind: str, word: str) -> str:
    return f'<span class="status status-{kind}">{word}</span>'


SORTING_PAGE = f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><title>Sorting</title>
<link rel="stylesheet" href="/static/interface/app.css">
<script src="/static/interface/app.js" defer></script></head>
<body><main><table>
<thead><tr><th>Name</th><th class="number">Hours</th><th>Dated</th><th>Remaining</th>
<th>Status</th></tr></thead>
<tbody>
<tr><td>A</td><td class="number">874.3</td><td>1 March 2026</td><td>9 Days</td>
<td>{mark("due", "Due Soon")}</td></tr>
<tr><td>B</td><td class="number">1,206.8</td><td>28 February 2026</td><td>10 Days</td>
<td>{mark("stop", "Overdue")}</td></tr>
<tr><td>C</td><td class="number">12.0</td><td>2 January 2027</td><td>{MINUS}3 Days</td>
<td>{mark("due", "Within Tolerance")}</td></tr>
<tr><td>D</td><td class="number">99.9</td><td>10 March 2026</td><td>100 Days</td>
<td>{mark("due", "Due")}</td></tr>
<tr><td>E</td><td class="number"></td><td>No Certificate Recorded</td><td>{MINUS}40 Days</td>
<td data-attention></td></tr>
<tr><td>F</td><td class="number">5.0</td><td>3 March 2026</td><td>50 Days</td>
<td>{mark("ok", "Serviceable")}</td></tr>
</tbody></table></main></body></html>"""


def test_the_sort_reads_numbers_and_dates_not_their_text() -> None:
    """REQ-196. A table made for the purpose, with values that sorting as text
    gets wrong, written as the application writes them: 1,206.8 is more than
    874.3; 28 February comes before 1 March; 40 days overdue, with the minus
    sign the application uses, comes before 3 days overdue and both before 9
    days remaining. A cell that is not a date in a column of dates comes after
    the dates either way, and an empty cell last. A Status column runs from a
    row nobody can place, through Overdue, Within Tolerance, Due and Due Soon,
    to what needs nothing. Found wanting by the independent review of 19
    November 2026."""
    pages = {"/sorting/": HttpResponse(SORTING_PAGE)}
    orders = (
        # 5.0, 12.0, 99.9, 874.3, 1,206.8, then the empty cell
        ("Hours", ["F", "C", "D", "A", "B", "E"], ["B", "A", "D", "C", "F", "E"]),
        # 28 February, 1 March, 3 March, 10 March, 2 January 2027, then what is not a date
        ("Dated", ["B", "A", "F", "D", "C", "E"], ["C", "D", "F", "A", "B", "E"]),
        # -40, -3, 9, 10, 50, 100
        ("Remaining", ["E", "C", "A", "B", "F", "D"], ["D", "F", "B", "A", "C", "E"]),
        ("Status", ["E", "B", "C", "D", "A", "F"], ["F", "A", "D", "C", "B", "E"]),
    )

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}/sorting/")
        table = page.locator("main table.compact")
        for heading, ascending, descending in orders:
            button = table.get_by_role("button", name=heading)
            button.click()
            assert column(page, "Name") == ascending, heading
            button.click()
            assert column(page, "Name") == descending, heading

    in_browser(pages, check)


def searching_page() -> str:
    """Return a page with a table of 12 rows and a table of 4."""
    words = ["Alpha", "Bravo", "Charlie", "Delta"]
    long_rows = "".join(
        f"<tr><td>Item {n:02d}</td><td>{words[n % 4]}</td><td>Kept {'Apart' if n == 7 else 'Here'}"
        f"</td><td><form><label>Result <select name='result'><option>Alpha</option>"
        f"<option>Finding</option></select></label><button type='submit'>Record Alpha</button>"
        f"</form></td></tr>"
        for n in range(1, 13)
    )
    short_rows = "".join(f"<tr><td>Short {n}</td><td>Alpha</td></tr>" for n in range(1, 5))
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><title>Searching</title>
<link rel="stylesheet" href="/static/interface/app.css">
<script src="/static/interface/app.js" defer></script></head>
<body><main>
<table id="long"><thead><tr><th>Name</th><th>Word</th><th data-detail>Where</th>
<th>Record</th></tr></thead>
<tbody>{long_rows}</tbody></table>
<table id="short"><thead><tr><th>Name</th><th>Word</th></tr></thead>
<tbody>{short_rows}</tbody></table>
</main></body></html>"""


def test_a_short_table_that_asks_for_it_is_searched() -> None:
    """REQ-282. The Fleet board shows its search always. A table of 4 rows that
    asks for it has the search and the count, and is searched as a long one is."""
    body = searching_page().replace('<table id="short">', '<table id="short" data-search="always">')
    pages = {"/searching/": HttpResponse(body)}

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}/searching/")
        assert page.get_by_label("Search This Table").count() == 2
        count = page.locator(".table-scroll:has(#short) + p[role=status]")
        assert count.text_content() == "4 of 4 Shown"
        page.get_by_label("Search This Table").nth(1).fill("short 3")
        assert count.text_content() == "1 of 4 Shown"

    in_browser(pages, check)


def shown_names(page: Page) -> list[str]:
    return page.evaluate(  # type: ignore[no-any-return]
        """() => [...document.querySelectorAll('#long tbody tr:not(.detail)')]
            .filter(row => row.getBoundingClientRect().height > 0)
            .map(row => row.cells[1].textContent.trim())"""
    )


def test_a_long_table_is_searched_and_says_how_many_rows_it_shows() -> None:
    """REQ-196; Components.md, Filtering. A table of more than 10 rows has a
    search above it and a count beneath it. Every word typed must be in the
    row, whatever its case, in any column, including one kept in the detail.
    A row that is hidden takes its detail with it and gets it back."""
    pages = {"/searching/": HttpResponse(searching_page())}

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}/searching/")
        search = page.get_by_label("Search This Table")
        assert search.count() == 1  # the table of 4 rows has none
        count = page.locator(".table-scroll:has(#long) + p[role=status]")
        assert count.text_content() == "12 of 12 Shown"

        # Items 4, 8 and 12 hold Alpha: 4 % 4, 8 % 4 and 12 % 4 are 0.
        search.fill("alpha")
        assert shown_names(page) == ["Item 04", "Item 08", "Item 12"]
        assert count.text_content() == "3 of 12 Shown"
        search.fill("ALPHA  08")
        assert shown_names(page) == ["Item 08"]
        # A word that is only in the column kept in the detail.
        search.fill("apart")
        assert shown_names(page) == ["Item 07"]
        search.fill("nothing like this")
        assert shown_names(page) == []
        assert count.text_content() == "0 of 12 Shown"
        # What a form offers is not what the row holds: every row has the option
        # Finding and the button Record Alpha, and neither is searched.
        search.fill("finding")
        assert shown_names(page) == []
        search.fill("record")
        assert shown_names(page) == []

        # An open row is hidden with its detail, and comes back open.
        search.fill("")
        first = page.locator("#long tbody tr:not(.detail)").first
        first.get_by_role("button", name="Show Details").click()
        detail = page.locator("#long tr.detail")
        assert detail.is_visible()
        search.fill("charlie")
        assert not first.is_visible()
        assert not detail.is_visible()
        # Sorting does not bring hidden rows back.
        page.locator("#long").get_by_role("button", name="Name").click()
        page.locator("#long").get_by_role("button", name="Name").click()
        assert shown_names(page) == ["Item 10", "Item 06", "Item 02"]
        # The same once a form has been moved into an open detail.
        search.fill("finding")
        assert shown_names(page) == []
        search.fill("")
        assert len(shown_names(page)) == 12
        assert detail.is_visible()
        assert count.text_content() == "12 of 12 Shown"
        # The short table was left alone.
        assert page.locator("#short tbody tr").count() == 4

    in_browser(pages, check)


def test_the_search_works_on_a_real_page_under_its_content_security_policy(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-196. The 16 points of an airworthiness review: more than 10 rows, so
    the table is searched, on a page served with the application's own headers."""
    with working_for(sample.ours.id, sample.lucy.id):
        staff = ReviewStaff.objects.get(user=sample.lucy)
        review = review_services.start_review(fleet["G-ABCD"], staff=staff)
    path = f"/reviews/{review.id}/"
    pages = {path: made(signed_in(sample.lucy), path)}
    assert "Content-Security-Policy" in pages[path].headers

    def check(page: Page) -> None:
        page.goto(f"{ORIGIN}{path}")
        count = page.locator("main p[role=status]").first
        assert count.text_content() == "16 of 16 Shown"
        page.get_by_label("Search This Table").first.fill("ML.A.903(c)")
        assert count.text_content() == "5 of 16 Shown"  # the survey, points (c)(1) to (5)

    in_browser(pages, check)


def test_aircraft_tabs_and_import_guidance_fit_a_phone(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    manager = signed_in(sample.lucy)
    aircraft = f"/aircraft/{fleet['G-CDEF'].id}/"
    imports = "/imports/"

    def check(page: Page) -> None:
        page.goto(ORIGIN + aircraft)
        assert page.locator(".tabs a").last.bounding_box() is not None
        assert (
            page.locator(".tabs a").last.evaluate("(link) => link.getBoundingClientRect().right")
            <= 390
        )
        assert page.evaluate("document.documentElement.scrollWidth") == 390

        page.goto(ORIGIN + imports)
        guidance = page.locator("main table").last
        assert guidance.get_by_role("button", name="Show Details").count() == 3
        guidance.get_by_role("button", name="Show Details").first.press("Enter")
        assert guidance.get_by_role("row").filter(has_text="Column Headings").count() >= 1

    in_browser(
        {aircraft: made(manager, aircraft), imports: made(manager, imports)}, check, width=390
    )


@pytest.mark.parametrize("colour_scheme", ["light", "dark"])
@pytest.mark.parametrize("width", [1280, 320])
def test_the_main_pages_pass_the_accessibility_scan(
    sample: Sample, fleet: dict[str, Aircraft], width: int, colour_scheme: str
) -> None:
    """REQ-383 to REQ-404. axe-core, WCAG 2.2 Levels A and AA, at desktop and 320 pixels
    (SC 1.4.10), in both colour schemes. A row is opened, as a person would, and the
    page is scanned again. Every page is scanned in the live walk (tests/e2e)."""
    manager = signed_in(sample.lucy)
    aircraft = f"/aircraft/{fleet['G-ABCD'].id}/"
    paths = [
        "/dashboard/",
        "/",
        aircraft,
        aircraft + "programme/",
        aircraft + "directives/",
        "/reviews/",
        "/defects/",
        "/imports/",
        "/settings/",
        "/account/password/",
    ]
    pages = {path: made(manager, path) for path in paths}
    pages["/aircraft/add/"] = post(manager, "/aircraft/add/", registration="G-ABCD", hours="x")
    pages["/sign-in/"] = made(Client(), "/sign-in/")
    found: dict[str, list[str]] = {}

    def check(page: Page) -> None:
        for path in pages:
            page.goto(ORIGIN + path)
            problems = violations(page)
            opener = page.get_by_role("button", name="Show Details").first
            if opener.count():
                opener.click()
                problems += violations(page)
            # Content reflows: no scrolling in two directions at 320 pixels (SC 1.4.10).
            if width == 320 and page.evaluate(
                "document.documentElement.scrollWidth > document.documentElement.clientWidth"
            ):
                problems.append("the page scrolls sideways")
            if problems:
                found[path] = problems

    in_browser(pages, check, width=width, colour_scheme=colour_scheme)
    assert found == {}
