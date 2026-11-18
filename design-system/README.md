# Airworthiness+

Continuing airworthiness software for light aircraft, small Part-CAO organisations, owners and syndicates. The interface is a working tool for engineers and Continuing Airworthiness Managers: calm, precise and dense with real information, never decorated.

## Principles

1. **Information first.** Every element carries a fact someone needs. No decorative cards, gradients, illustrations or emoji.
2. **One source.** Every page uses these tokens and the components in the Components section. A page never invents its own size, colour, spacing or line.
3. **Crisp, not faint.** Geist looks right at full contrast and weight 500 for anything short. Grey is for metadata only.
4. **One line between things.** Content is separated by a single hairline or by space. Two lines are never stacked.
5. **Status is a square and a word.** A 10px coloured square always sits beside a word that says the same thing, so colour is never the only signal.
6. **Regulatory words.** Section and page names use the terms in Part-M, Part-ML, Part-CAO and the CAA's guidance, such as continuing airworthiness, airworthiness review and certificate of release to service.

## Typography

Follows Geist's published roles (vercel.com/geist/typography). Geist for everything, Geist Mono only for references such as WP-2026-047.

- **Label 14 is the default.** Table values, menus, tabs and sidebar items are 14px at weight 400 in `gray-1000`. Strong (500) is for the first column of a table, list row titles and fact values.
- **Secondary text goes under, not beside.** A title is followed on the next line by Label 13 or Label 14 in `gray-900`, like "Import Project" over its description on the Vercel dashboard. Grey text never sits on the same line as a heading.
- **Headings stay small.** Heading 24 is the one page title. Sections use Heading 16. There is nothing larger inside the app.
- **Two text colours only.** `gray-1000` for primary text and `gray-900` for secondary.
- Numbers use tabular figures, so columns line up.

## Colour

Follows Geist's colour steps (vercel.com/geist/colors).

- `background-100` is the go-to background. `background-200` is used sparingly, for the sidebar and table header rows.
- Borders are `gray-400`, hover `gray-500`.
- The primary button is `gray-1000` with white text. Every other button is secondary: `background-100` with a `gray-400` border.
- Status colours appear only as the round 10px status dot.

## Lines and Spacing

- 1px `gray-400` is the only line, and two lines never stack.
- Page padding is 32px at the top and 40px at the sides. Sections are 40px apart.
- Radii follow Geist materials: `material-base` 6px for every surface on the page, `material-medium` 12px for raised surfaces and menus.

## Navigation

One element for each job. Nothing repeats another.

| Job | Element |
|---|---|
| Global navigation | The sidebar. One item per section. |
| Location | The breadcrumb in the Top Bar, ending at the section, such as Continuing Airworthiness / Aircraft. |
| Local navigation | The section tabs, directly under the breadcrumb, sharing its one line. |
| Contextual navigation | Links inside the content, such as a registration or a work package reference. |
| Filtering | A segmented control in the content, labelled All, then each subset. Never repeats a tab name. |

- **No visible page title on section pages.** The breadcrumb names the section and the tabs name the view. The page keeps a hidden heading for screen readers.
- **Record pages** (an aircraft, a component, a work package) show the record as Heading 24 with its type on the line under it. The breadcrumb stops at the parent, such as Continuing Airworthiness / Aircraft.
- **No back and forward buttons.** The browser has them.
- **No open-record tabs.** They suit people with many documents open at once, which is not how this app is used.
- **A trial replaces something.** A new navigation pattern is only added if it says which element it replaces.

## Sections

The sidebar follows 1321/2014. Items show only for the approvals that need them (Owner, Part-CAO, Part-CAMO, Part-145).

| Section | Items |
|---|---|
| Continuing Airworthiness | Aircraft, Defects, Maintenance Programmes, Aircraft Configuration, Release to Service, Contracts |
| Management System | Hazard Log, Safety Reports, Occurrence Reports, Compliance Monitoring, Actions |
| Planning | Work Packages, Manhours and Capacity |
| Logistics | Goods In, Stores, Tools and Equipment, Suppliers |
| People | Staff (All Staff, Organisation Chart), Authorisations (Authorisations, Recency) |
| Training | Recurrent Training, Aircraft Maintenance Licence, Competency Assessments |
| Documentation | Manuals and Procedures (including the Combined Airworthiness Exposition), Revisions, Required Reading, Notices |
| Organisation | Approval and Scope, Changes, Oversight |
| Commercial | Marketplace, Enquiries and Quotes (Enquiries, Quotes), Customers, Invoices |

### Training

Training is its own section, separate from People. It holds two different things:

- **Recurrent Training:** training repeated on a cycle, such as Human Factors, Electrical Wiring Interconnection System and Fuel Tank Safety, plus continuation training. Tracked per person with due dates.
- **Aircraft Maintenance Licence:** the journey to a Part-66 licence and its type ratings, as an ordered process with tabs in this order:
  1. **Basic Examinations:** Part-66 modules, examined by a Part-147 organisation or the Civil Aviation Authority.
  2. **Experience Logbook:** basic experience recorded in the CAP 741 logbook.
  3. **Type Training:** Part-147 type course, with a Theory element and a Practical element.
  4. **On the Job Training:** only for the first type rating in the first licence category, recorded in an on the job training logbook.

## Restraint

Checked against six signs of AI-generated interfaces. Every element has to earn its place.

1. **Copy.** No description paragraph under a page title. A section gets one short meta line only when it says something the content cannot, such as "4 of 6 inputs complete". No "Example data" footers, and no design notes in the interface.
2. **Coloured borders.** None. Colour sits only in status marks.
3. **Chips.** Only for filters and counts on tabs. Everything else is plain text.
4. **Dots.** A status dot means something. Amber and red flag what needs attention. Green appears only in a Status column or the Status fact, never as decoration on every row. Checklists use all three to show progress.
5. **Labels.** No eyebrow labels above headings. The Top Bar breadcrumb gives location, so the title stands alone. Labels are in Title Case.
6. **Space.** 40 pixels between sections. No summary strip that repeats the table below it. Remove before adding.

## Iconography

Line icons only, 16px in the sidebar and 18px in the top bar, drawn on a 24px grid with a 1.75 stroke and round caps and joins, in the colour of the text beside them. Icons always sit beside a word; an icon-only button has a label for screen readers. No filled icons, no emoji, no logos of other companies.

## Writing

See the Writing section for the full content style guide. In short: title case for headings, labels, tabs, buttons and table headers; sentence case only for full sentences; never abbreviate; British English; no middle dots.
