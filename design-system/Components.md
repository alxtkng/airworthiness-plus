# Components

The repeated parts of every page. Each is built once in the web app canvas and reused; a page never copies their markup with different values.

## Page Header

The page title (Heading 24), then the section tabs. No description paragraph, tagline or subtitle. On a record page, the record's type sits on the line under the title in Label 14, `gray-900`. Buttons sit on the right, aligned to the bottom: at most one primary, the rest secondary.

## Top Bar

One breadcrumb row, 48px high, Label 14. Parent levels are links in `gray-900`, the current section is `gray-1000` Strong, separated by a slash in `gray-500`. On section pages the line under the bar is shared with the section tabs; on record pages the bar has its own line. No open-record tabs and no back or forward buttons.

## Section Tabs

The views of one section, such as Components and Life Limits, Airworthiness Directives. `label` text; the active tab is `ink` with a 2px `ink` underline, the others `ink-muted`. One `divider` line under the row. The next element below the tabs never has a top line.

## Summary Strip

A row of counts that summarise the page: the number in `label` weight 600 and `ink`, the words in title case in `ink-secondary`. It sits on `surface-sunken` with `radius-lg` and no lines, so it never stacks against the tabs' line.

## Data Table

A `radius-lg` box with a `hairline` `divider` border. The header row is `surface-sunken` with `meta` headers. Rows are separated by one `divider` line; the last row has none. Numbers align right.

- **Compact Rows:** every row is one line. Cells are `space-4` sideways and 12px vertically, `white-space: nowrap`, truncated with an ellipsis at a maximum width. Never a second line inside a cell.
- **Expandable Rows:** the first column is a disclosure button (chevron, `aria-expanded`, accessible name Show Details) under a screen-reader-only Details header. Opening a row shows a detail row beneath it spanning every column: a label and value grid (Label 13 `gray-900` over Label 14) holding every column's full value plus anything moved out of the row, such as secondary lines, owners, notes and dates.
- **Open State:** the row and its detail share `background-200`, and the line between them is removed, so the pair reads as one row with one line under it.
- **What Moves to the Detail:** reference numbers, type ratings under registrations, status reasons, progress text and next-step dates. The row keeps only what is scanned or sorted.
- **Sorting:** column headers are buttons with `aria-sort`; one click sorts ascending, a second click descending, and only the sorted column shows an arrow. Status columns sort by severity, red first.
- **Filtering:** search first, then a segmented control for the main facet with counts, then selects for secondary facets. Show a count of rows shown out of the total under the table.
- **Tree Grid:** where records have a parent, such as a legal entity holding several approvals, the table is a tree grid (`role="treegrid"`, rows with `aria-level`). The parent row is one line with a chevron that opens its children; each child row is indented 40 pixels and has its own chevron for its details. Searching opens every parent so matches show. Use only for working records; a directory (such as the Marketplace) is a results list with one level of opening.
- **Picker Tables:** tables used to choose one item, such as the SRG1782 type list, stay one line and select on click; the choice shows in the panel above.
- **Short Tables Inside a Step or Panel:** one line, no disclosure.

## Status Label

A 10px square with `radius-status` and `space-2` before a word in `label`. Filled squares use the status colours; an open square is a 1.5px `control-border` outline. The word always says what the colour means.

## Checklist

A numbered list of steps, each a status square, a `label` line and an optional `meta` or `body` note. One `divider` above the list and one between items, none after the last.

## Callout

One sentence that needs attention, on `surface-sunken` with `radius-lg`, no border, a status square on the left and `body` text. At most one per page.

## Button

`label` text, 40px tall, `radius-md`, `space-4` sideways. Primary: `action` fill and `action-ink` text. Secondary: `surface` fill, `control-border` outline, `ink` text.

## Sidebar

Group names in `meta` and `ink-muted`; items in `label`, `ink-secondary` at rest and `ink` when active. The active item is `surface-raised` with a `divider` ring and `radius-sm`. Counts in Geist Mono `meta`. Each sidebar item is one section; views of the same data are section tabs, never more sidebar items.


## Configuration Tree

The aircraft's product structure, on the Configuration tab of each aircraft record.

- **Three layers, kept apart:** the product structure (positions from the type template), the allowed configuration (eligible part numbers and the changes that allow them) and the installed configuration (the serial number in each position now, with its history).
- **Hierarchy:** product (Airframe, Engine, Propeller), then chapter, then position. Chapter numbers follow ATA iSpec 2200, shown in Geist Mono `label-13`, never as the label alone.
- **Tree rows:** disclosure buttons with `aria-expanded`, Label 14, indented 20 pixels per level. Counts in Label 13 `gray-900`. A status dot only for amber or red items, and on a chapter when any position inside needs attention.
- **Detail panel beside the tree:** position name (Heading 16), its path, the installed item facts, Allowed Configuration, Rules (21.A.307 restrictions for primary structure and flight controls, life limits), Linked Records and Installation History.
- **Filters:** All, Life-Limited, Required, Needs Attention, Not Recorded, plus search by position, part number or serial number.
- **Setup:** a new aircraft's configuration is built with the Set Up Configuration wizard, starting from the type template, never from a blank tree.

## Organisation Chart

- The regulation's term is organisation chart showing chains of responsibility (CAO.A.025(a)(4), Exposition Chapter A.8).
- A tree: Accountable Manager at the top, the nominated persons under it, then their staff. Lines are 1 pixel `gray-400`; no coloured boxes.
- Each person is a card: name (Label 14 Strong), role (Label 13 `gray-900`), Contracted when contracted, and a status dot only when their authorisation or training needs attention.
- The Compliance Monitoring Manager reports directly to the Accountable Manager, to show independence.
- ARIA tree roles: `tree`, `treeitem` with `aria-level`, `group`.


## Accessibility Checklist

Every new page or component passes these before it is merged or published, in the application and on the canvas. Each is a rule of `Accessibility.md` and a requirement; the success criterion is in brackets.

1. **Text contrast (SC 1.4.3).** Text uses `gray-1000` or `gray-900` on the backgrounds of the tokens. No colour is written outside the tokens.
2. **Non-text contrast (SC 1.4.11).** Inputs, selects, checkboxes, secondary buttons and toggles use `control-border`, never `gray-400`. Status dots carry their edge token.
3. **Use of colour (SC 1.4.1).** Every amber or red dot has its words; green only in a Status column with its word; links in running text are underlined.
4. **Resize and reflow (SC 1.4.4, 1.4.10).** Usable at 200% and at 320 pixels with no sideways scrolling of the page. A wide table scrolls in its own box.
5. **Text spacing (SC 1.4.12).** No fixed heights on text. A truncated cell keeps its value in the detail.
6. **Hover and focus (SC 1.4.13).** No tooltips.
7. **Keyboard (SC 2.1.1, 2.1.2).** Native buttons and links only; an expandable row is a `button` with `aria-expanded`; never a clickable `div`.
8. **Focus (SC 2.4.3, 2.4.7, 2.4.11).** Focus follows reading order and shows the `focus-ring` outline; nothing sticky covers it.
9. **Target size (SC 2.5.8, 2.5.5).** 24 pixels or spaced to 24; 44 in Comfortable, from `target-minimum`.
10. **Dragging (SC 2.5.7).** Anything dragged can also be done with a single pointer.
11. **Bypass and title (SC 2.4.1, 2.4.2).** The base template’s skip link stays first; the page has its own title block or a view that names it.
12. **Headings and landmarks (SC 1.3.1, 2.4.6).** One `h1`, matching the active tab where it is hidden; `h2` sections in order; `nav`, `main` and `aria-current="page"` from the base template.
13. **Motion (SC 2.3.3).** Any transition uses the `motion` token.
14. **Labels (SC 1.3.1, 2.5.3, 3.3.2).** Every field has a visible label, connected, and the label starts its accessible name. A placeholder is never the label.
15. **Errors (SC 3.3.1, 3.3.3).** A form writes `{% error_summary form %}` and each field’s error with the identifier `id="{{ field.auto_id }}_error"`.
16. **Consistency (SC 3.2.3, 3.2.4, 3.2.6).** Sidebar, tabs and help stay where the base template puts them.
17. **Redundant entry (SC 3.3.7).** What is already known is filled in or offered to choose.
18. **Authentication (SC 3.3.8).** No puzzle or memory test; password managers and pasting work.
19. **Plain language.** Writing.md.
20. **Names and roles (SC 4.1.2).** Tables have `th scope="col"` and a name from their section heading; a choice of views is links with `aria-current`; a toggle has `aria-pressed` or is a radio group.
21. **Status messages (SC 4.1.3).** A count that changes after filtering is in `role="status"`.
22. **Language (SC 3.1.1).** `lang="en-GB"`.

The automated checks (`tests/test_accessibility.py`, `tests/test_canvas_accessibility.py`, the axe-core scans) cover rules 1, 2, 4, 9, 11, 12, 14, 15, 20, 21 and 22 in part. The rest, and the rest of those, are in the manual pass.
