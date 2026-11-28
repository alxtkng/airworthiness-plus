# Accessibility Conformance Report, Outline

Airworthiness+ against WCAG 2.2 Level AA (ISO/IEC 40500:2025), criterion by criterion, in the shape of the ITI VPAT 2.5 WCAG edition. This is an outline: the conformance level of each criterion is set only after the manual pass in `design-system/Accessibility.md`. Until then, nothing here is a claim of conformance.

- **Product:** Airworthiness+, private beta, the Django application and its pages
- **Report date:** draft of 28 November 2026
- **Evaluation methods:** automated (axe-core 4.14.0; the project's own tests, ADR-0011); manual pass to come (NVDA, VoiceOver, keyboard, zoom, text spacing, Windows contrast themes)
- **Terms, when set:** Supports; Partially Supports; Does Not Support; Not Applicable
- 4.1.1 Parsing is obsolete and removed from WCAG 2.2, so it is not listed

| Criterion | Level | How It Is Met | Evidence | Conformance Level |
|---|---|---|---|---|
| 1.1.1 Non-text Content | A | Icons are beside words and hidden from assistive technology; icon-only buttons are named (Show Details) | axe-core scans | To Be Set After the Manual Pass |
| 1.2.1 Audio-only and Video-only (Prerecorded) | A | No audio or video | Not Applicable | Not Applicable |
| 1.2.2 Captions (Prerecorded) | A | No video | Not Applicable | Not Applicable |
| 1.2.3 Audio Description or Media Alternative (Prerecorded) | A | No video | Not Applicable | Not Applicable |
| 1.2.4 Captions (Live) | AA | No live media | Not Applicable | Not Applicable |
| 1.2.5 Audio Description (Prerecorded) | AA | No video | Not Applicable | Not Applicable |
| 1.3.1 Info and Relationships | A | Native headings, lists, tables with `th scope="col"` and names, labelled fields, fieldsets for radio groups | test_accessibility, axe-core; screen reader pass to come | To Be Set After the Manual Pass |
| 1.3.2 Meaningful Sequence | A | Source order is reading order | Manual pass | To Be Set After the Manual Pass |
| 1.3.3 Sensory Characteristics | A | No instruction relies on shape, place or sound | Manual pass | To Be Set After the Manual Pass |
| 1.3.4 Orientation | AA | No orientation lock | Manual pass on a tablet | To Be Set After the Manual Pass |
| 1.3.5 Identify Input Purpose | AA | Sign-in fields carry `autocomplete`. Personal fields elsewhere (names, email) to be checked | To be assessed | To Be Set After the Manual Pass |
| 1.4.1 Use of Color | A | Every status dot has its word; links in text are underlined | test_interface, axe-core | To Be Set After the Manual Pass |
| 1.4.2 Audio Control | A | No audio | Not Applicable | Not Applicable |
| 1.4.3 Contrast (Minimum) | AA | Every token pair recalculated on each pull request; see Accessibility.md, Contrast Results | test_accessibility, test_canvas_accessibility, axe-core | To Be Set After the Manual Pass |
| 1.4.4 Resize Text | AA | Text Size setting and browser zoom | Manual pass at 200% | To Be Set After the Manual Pass |
| 1.4.5 Images of Text | AA | No images of text | Not Applicable | Not Applicable |
| 1.4.10 Reflow | AA | No sideways scrolling of the page at 320 pixels; wide tables scroll in their box | axe-core walk at 320 pixels | To Be Set After the Manual Pass |
| 1.4.11 Non-text Contrast | AA | control-border, focus-ring and status dot edges at 3:1 or more | test_accessibility | To Be Set After the Manual Pass |
| 1.4.12 Text Spacing | AA | No fixed heights on text | Manual pass with a text spacing bookmarklet | To Be Set After the Manual Pass |
| 1.4.13 Content on Hover or Focus | AA | No tooltips | Not Applicable | Not Applicable |
| 2.1.1 Keyboard | A | Native controls only; rows open with a button | test_browser, tests/e2e keyboard journey; keyboard pass to come | To Be Set After the Manual Pass |
| 2.1.2 No Keyboard Trap | A | No custom widgets | Manual pass | To Be Set After the Manual Pass |
| 2.1.4 Character Key Shortcuts | A | No single-key shortcuts | Not Applicable | Not Applicable |
| 2.2.1 Timing Adjustable | A | Signed-in sessions end after 30 minutes idle (60 on managed devices) with no warning or way to extend. This does not meet the criterion. A warning with a way to extend is needed; it is a decision for Alex King against the session rules of OWASP ASVS 5.0 | Does Not Support until decided | Does Not Support |
| 2.2.2 Pause, Stop, Hide | A | Nothing moves, blinks or updates on its own | Not Applicable | Not Applicable |
| 2.3.1 Three Flashes or Below Threshold | A | Nothing flashes | Not Applicable | Not Applicable |
| 2.4.1 Bypass Blocks | A | Skip to Main Content first on every page; landmarks | test_accessibility | To Be Set After the Manual Pass |
| 2.4.2 Page Titled | A | A title on every page, its own or its view, then Airworthiness+ | test_accessibility | To Be Set After the Manual Pass |
| 2.4.3 Focus Order | A | Source order; focus moves to the error summary | Manual pass | To Be Set After the Manual Pass |
| 2.4.4 Link Purpose (In Context) | A | Links name their record, such as a registration | axe-core; manual pass | To Be Set After the Manual Pass |
| 2.4.5 Multiple Ways | AA | Sidebar, breadcrumb, section tabs and links in content | Manual pass | To Be Set After the Manual Pass |
| 2.4.6 Headings and Labels | AA | One h1 and ordered headings on every page; Title Case labels | test_accessibility | To Be Set After the Manual Pass |
| 2.4.7 Focus Visible | AA | One 2 pixel focus ring from a token | test_accessibility; manual pass | To Be Set After the Manual Pass |
| 2.4.11 Focus Not Obscured (Minimum) | AA | Nothing is sticky | Manual pass | To Be Set After the Manual Pass |
| 2.5.1 Pointer Gestures | A | No path or multipoint gestures | Not Applicable | Not Applicable |
| 2.5.2 Pointer Cancellation | A | Native buttons act on release | Not Applicable beyond native behaviour | Not Applicable |
| 2.5.3 Label in Name | A | Visible label starts every accessible name, including the table search | test_accessibility, axe-core | To Be Set After the Manual Pass |
| 2.5.4 Motion Actuation | A | No motion input | Not Applicable | Not Applicable |
| 2.5.7 Dragging Movements | AA | Nothing is dragged in the application or on the canvas | Not Applicable | Not Applicable |
| 2.5.8 Target Size (Minimum) | AA | 24 pixels or spaced; 44 in Comfortable | axe-core walk; two findings fixed 28 November 2026 | To Be Set After the Manual Pass |
| 3.1.1 Language of Page | A | lang="en-GB" | test_accessibility | To Be Set After the Manual Pass |
| 3.1.2 Language of Parts | AA | No passages in another language | Not Applicable | Not Applicable |
| 3.2.1 On Focus | A | Focus changes nothing | Manual pass | To Be Set After the Manual Pass |
| 3.2.2 On Input | A | Filters are links; forms submit on their button | Manual pass | To Be Set After the Manual Pass |
| 3.2.3 Consistent Navigation | AA | One base template for every page | test_interface | To Be Set After the Manual Pass |
| 3.2.4 Consistent Identification | AA | Components.md; the same words for the same thing | Inspection | To Be Set After the Manual Pass |
| 3.2.6 Consistent Help | A | No help mechanism is built yet; when the Help item is built it stays at the foot of the sidebar | Not Applicable until Help is built | Not Applicable |
| 3.3.1 Error Identification | A | Error summary and message by each field | test_accessibility, test_display | To Be Set After the Manual Pass |
| 3.3.2 Labels or Instructions | A | Visible connected labels | test_accessibility | To Be Set After the Manual Pass |
| 3.3.3 Error Suggestion | AA | Messages say what is wrong; Django's default messages to be reviewed for how to fix | Manual pass | To Be Set After the Manual Pass |
| 3.3.4 Error Prevention (Legal, Financial, Data) | AA | Certificates and releases are reviewed before issue and cannot be altered after; whether each legal record can be checked and confirmed before it is final is to be assessed page by page | To be assessed | To Be Set After the Manual Pass |
| 3.3.7 Redundant Entry | A | Forms pre-fill from the record | Manual pass of each process | To Be Set After the Manual Pass |
| 3.3.8 Accessible Authentication (Minimum) | AA | No puzzle or memory test; password managers and paste work; passkeys offered | tests/e2e passkey journey; manual pass with password managers | To Be Set After the Manual Pass |
| 4.1.2 Name, Role, Value | A | Native elements; aria-expanded on disclosures; aria-current on navigation | axe-core | To Be Set After the Manual Pass |
| 4.1.3 Status Messages | AA | Rows shown after a search, and the canvas Marketplace count, are polite live regions | test_browser; screen reader pass | To Be Set After the Manual Pass |

## Open Items

- **SC 2.2.1 Timing Adjustable.** The idle time limit has no warning. A decision for Alex King.
- **SC 3.3.4 Error Prevention.** Each page that makes a legal record final is to be assessed for a check-and-confirm step.
- **SC 1.3.5 Identify Input Purpose.** Personal fields outside sign-in are to be given `autocomplete` values where they ask for the person's own details.
