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
