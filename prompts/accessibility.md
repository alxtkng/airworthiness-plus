# Airworthiness+ Accessibility: Working Brief

Paste everything below this line into a new chat.

---

You are making every page of Airworthiness+ accessible, in the working application and on the design canvas, and setting the rules so that every page built from now on is accessible from the start. Read this whole brief before doing anything, then read the record named in Part 2 before changing anything.

## Part 1. Who you are working for and how to behave

- Alex King, founder of Airworthiness Limited, GitHub `alxtkng`, website airworthiness.co. He is a domain expert in UK continuing airworthiness. Do not explain airworthiness to him, and do not ask him discovery questions.
- Work from the record and the standards below. Ask only when a decision is genuinely his.
- Do not open replies with "You're right" and then change course. If he corrects you, fix the work and say what changed.
- Cite the success criterion for every accessibility claim (for example WCAG 2.2 SC 1.4.11). Never invent a criterion or a number.
- Be terse. Delete nothing without his confirmation. Never enter passwords or one-time codes.

## Part 2. Where the work lives: read first

There are two targets. The real application comes first, because it is the product. The design canvas comes second, because it is the design reference that new pages are drawn from.

### The repository

`github.com/alxtkng/airworthiness-plus` (private). Attach it with push access and clone it.
- `main` is protected. Follow `CONTRIBUTING.md` exactly:
  - every change starts from a GitHub Issue with one label (use `requirement`)
  - one branch per change, named after the work (for example `req-359-accessibility-baseline`)
  - small commits
  - a pull request that passes `.github/workflows/checks.yml`
- Read before changing anything:
  - `CONTRIBUTING.md` and `README.md`
  - `design-system/Decisions.md`, `SampleData.md`, `Writing.md`, `Components.md`, `README.md`, `tokens.json`: these are the rules. Do not break them while fixing accessibility.
  - `requirements/requirements.md` and `requirements/traceability.csv`: add new requirements from the next free number. A change in behaviour updates the traceability file in the same pull request.
  - `assurance/` (assurance case, hazard log, NCSC self-assessment) and `architecture/decisions/`

### Target A: the application

A Django application under `src/airworthiness_plus/`.
- Templates live in each app's `templates/` folder (about 112 of them). The base template is `src/airworthiness_plus/interface/templates/base.html`.
- The single stylesheet is `src/airworthiness_plus/interface/static/interface/app.css`. It holds the design tokens as CSS custom properties, already has a `prefers-color-scheme: dark` block and a skip link.
- Navigation is built in `interface/navigation.py`; forms in `interface/forms.py` and `field_rules.py`.
- Tests are in `tests/`. The live browser checks use Playwright and are in `tests/e2e/` (see its README). Run every check in `CONTRIBUTING.md` locally before opening a pull request.
- Adding a dependency, such as an automated accessibility checker for the Playwright suite, is its own pull request that changes `pyproject.toml` and `uv.lock` only. Record the choice in `architecture/decisions/` if it adds a tool to the build.

### Target B: the design canvas

- In the repository: `canvas/` holds every page as `.dc.html` files (Claude Design format) plus `canvas.json`. They only render in the Design editor.
  - `scripts/gen.py` is the shared page generator. Most pages come from the other scripts in `scripts/`, which import it. Fix the generator once and regenerate, rather than hand-editing generated pages.
  - Hand-built pages that need direct edits: Marketplace, Aircraft, AddAircraft, ConfigSetup, Assessment, Staff, OrgChart, Fleet, Reviews.
  - Shared parts every page imports: `Sidebar.dc.html`, `Tabs.dc.html`, `TopBar.dc.html`.
- The live artifact is "Airworthiness+ Web App", slug `818487b9-d9ee-4e3c-8a90-a4dab1602cfe`, files under `project/`. Call `list_files` first, read the type's `SKILL.md`, and publish with `publish_files` in patch mode.
- The design system artifact is "Airworthiness+", slug `c27d6e5a-0357-40c6-957a-94c4dd400ce5`, files under `project/`.
- The account has a limited number of artifact saves per day (about 10, shared across all chats). Put the canvas change into one publish and the design system change into one publish, made only after the work is complete and checked locally. Every file published to an artifact is also committed to the repository.

## Part 3. The standards to apply

- **WCAG 2.2 at Level AA** for every page. It is the international standard ISO/IEC 40500:2025. WCAG 3 is still a working draft and does not replace WCAG 2, so do not build to it. Apply AAA only where this brief says so.
- **Legal context, for the record only:**
  - UK Equality Act 2010: the reasonable adjustments duty is anticipatory.
  - European Accessibility Act: in force since 28 June 2025, mainly for consumer services. The engineer's personal logbook would be in scope if sold in the EU.
  - Business customers will ask for an Accessibility Conformance Report and an accessibility statement.
- **Inclusive design for maintenance conditions.** Design for situational limits as well as permanent ones:
  - gloves and greasy hands
  - glare in sunlight on the apron
  - a tablet held one-handed
  - night shifts
  - fatigue, one of the Dirty Dozen human factors the users are trained on
- **Colour vision.** About 8% of men and 0.5% of women have a colour vision deficiency, mostly red-green. Colour is never the only carrier of meaning (SC 1.4.1).

## Part 4. Rules every page must meet

Check each page against every rule, in both the application and the canvas. Record a pass, or the fix you made, in the audit (Part 6).

### Perceivable
1. **Text contrast (SC 1.4.3):** at least 4.5:1, or 3:1 for large text, in both light and dark themes. Check every token pair in `app.css` and `tokens.json`, and every hard-coded colour in the templates, the canvas pages and the `t` objects in each canvas page's script.
2. **Non-text contrast (SC 1.4.11):** at least 3:1 for anything a user needs in order to see a control or its state.
   - This covers input and select borders, checkbox outlines, the segmented control's selected state, focus indicators, and the meaning-bearing status dots.
   - The current border token `#EBEBEB` (`--gray-200` and `--gray-400` in `app.css`) on white is far below 3:1. It may stay for decorative dividers, but every form control and toggle needs a border or fill that meets 3:1.
3. **Use of colour (SC 1.4.1):**
   - Every amber or red dot keeps its words, for example "5 Days Overdue". Never a dot alone.
   - Green appears only in a Status column, and always with its word.
   - Links inside running text are underlined.
4. **Text resize and reflow (SC 1.4.4, 1.4.10):** usable at 200% zoom, and the content reflows at a 320-pixel width with no two-way scrolling. Wide tables may scroll on their own, inside their bordered container, which is allowed. The one-line, no-wrap table rule stays.
5. **Text spacing (SC 1.4.12):** nothing clips or overlaps when users increase line, letter, word and paragraph spacing.
6. **Content on hover or focus (SC 1.4.13):** any tooltip can be dismissed, stays while hovered, and remains until dismissed. Prefer no tooltips; the record already rejects them.

### Operable
7. **Keyboard (SC 2.1.1, 2.1.2):**
   - Everything works by keyboard, with no traps.
   - Expandable rows use a real `button` with `aria-expanded`, as the Fleet and Reviews pages already do.
   - Clickable `div`s become buttons or links.
8. **Focus order and visible focus (SC 2.4.3, 2.4.7, 2.4.11):**
   - Order follows reading order.
   - Every focusable element shows a clearly visible focus ring that meets 3:1 in both themes. Use a 2-pixel outline offset 2 pixels, from a token.
   - Sticky headers or panels never hide the focused element.
9. **Target size (SC 2.5.8):**
   - At least 24 by 24 pixels, or spaced so a 24-pixel circle around each does not overlap another.
   - In the Comfortable density (Part 5), at least 44 by 44 (SC 2.5.5, AAA), because of gloves and tablets.
10. **Dragging (SC 2.5.7):** anything that drags, such as a reorder in the organisation chart or the planning board, also has a single-pointer alternative.
11. **Bypass blocks and page titles (SC 2.4.1, 2.4.2):** a "Skip to Main Content" link first in each page, and a unique, descriptive `<title>` on each page.
12. **Headings and landmarks (SC 1.3.1, 2.4.6):**
    - One `h1` per page. The current pages hide the `h1` visually behind the tabs, which is acceptable while it matches the active tab.
    - Sections use `h2`, in order, with no skipped levels.
    - Use the `nav` landmark for the sidebar and the tabs, `main` for the page body, and `aria-current="page"` on the active sidebar item and tab.
13. **Motion (SC 2.3.3, AAA, adopted):** honour `prefers-reduced-motion`. Any transition or animation is removed or reduced under it and under the Reduce Motion setting.

### Understandable
14. **Labels and instructions (SC 1.3.1, 2.5.3, 3.3.2):**
    - Every input has a visible label, connected with `for` and `id` or by wrapping.
    - The visible label text appears at the start of the accessible name.
    - Placeholders never replace labels.
    - Search boxes keep their visible "Search" label.
15. **Errors (SC 3.3.1, 3.3.3):** errors are announced in text next to the field, say what is wrong and how to fix it, and are linked from an error summary at the top of the form, as in the GOV.UK pattern.
16. **Consistent navigation and help (SC 3.2.3, 3.2.4, 3.2.6):** the sidebar, tabs and the Help link sit in the same place on every page.
17. **Redundant entry (SC 3.3.7):** never make people re-enter what they have already given in the same process. Pre-fill it or offer to select it.
18. **Accessible authentication (SC 3.3.8):** no puzzle or memory test to sign in. Allow password managers and pasting. Offer passkeys when the real app is built.
19. **Plain language.**
    - Keep the record's writing rules: no abbreviations except regulatory identifiers, Title Case labels, no filler.
    - Exact day counts with their unit, for example "18 Days".
    - Dates written out, for example "6 December 2026".

### Robust
20. **Names, roles and values (SC 4.1.2):**
    - Native elements first.
    - Tables are real `table` elements, with `th scope="col"`, and a `caption` or `aria-labelledby` pointing at the section heading.
    - Segmented controls use `aria-pressed` or are radio groups.
    - Tabs that switch pages are links with `aria-current`, not ARIA tab widgets.
21. **Status messages (SC 4.1.3):** counts that change after filtering, such as "7 of 12 Acknowledged" or the results count in the Marketplace, sit in a polite live region.
22. **Language (SC 3.1.1):** `lang="en-GB"` on every page. The pages already have it, so keep it.

## Part 5. Display settings: build them

Respect the device first, then offer overrides.
- In the application: store the choices per user account, as a decision, a requirement and a migration. Apply them as classes or data attributes on `html` in `base.html`, driving the tokens in `app.css`. Until the user chooses, follow the device.
- On the canvas: add a **Display** page under Settings (the Settings tab set in `Tabs.dc.html`), matching the other Settings pages.

| Setting | Options | Behaviour |
|---|---|---|
| Appearance | System, Light, Dark | System follows `prefers-color-scheme`. The existing `dark` prop on every page and shared part stays as the canvas preview switch. Dark mode avoids pure white text on pure black body backgrounds (halation for people with astigmatism): keep the `#0A0A0A` page background and check the `#000000` sidebar against its text |
| Contrast | Standard, High | High follows `prefers-contrast: more` when set to System. It strengthens borders and muted text to at least 7:1 (SC 1.4.6, AAA), for glare on the apron and low vision. Also support `forced-colors: active` (Windows contrast themes): never encode state by background colour alone; use borders and text |
| Text Size | Default, Large, Larger | Scales from the root size, independent of browser zoom |
| Density | Compact, Comfortable | Compact is today's one-line tables and controls of 24 pixels or more. Comfortable gives 44-pixel targets and more row height, for gloves and tablets |
| Reduce Motion | System, On, Off | System follows `prefers-reduced-motion` |

- Add the matching tokens to `app.css` and `tokens.json`: high contrast variants of text, muted, border and focus for both themes, and density sizes. Keep the two token sets identical in value.
- Show both themes and both densities on the canvas, so Alex can see each.
- Do not add a dyslexia font. The evidence does not support one, and Geist with good line spacing and left-aligned text already follows the British Dyslexia Association style guide.

## Part 6. The work, in order

1. **Issue and requirements.** Open the Issue. Add numbered requirements for WCAG 2.2 Level AA (the 22 rules in Part 4 and the Display settings in Part 5) to `requirements/requirements.md`, each with its success criterion as the source and Test as the verification. Add each one to `traceability.csv`.
2. **Audit.** Write `design-system/Accessibility.md` with the standard, the legal context and the settings. Include an audit table with one row per application page (every URL route and its template) and one row per canvas page and shared part, against rules 1 to 22: Pass, Fixed or Not Applicable, with a note.
3. **Fix the application, shared parts first:**
   - `app.css` tokens, focus ring and contrast
   - `base.html` landmarks, skip link and `title`
   - navigation, tabs and `aria-current`
   - form fields, labels and the error summary
   - table markup
   - then every template

   Keep each pull request reviewable: one for the stylesheet and base template, then one per section of the app.
4. **Automate the checks.**
   - Add an automated accessibility scan of every page to the Playwright suite in `tests/e2e/`, covering both colour schemes and the 320-pixel reflow width.
   - Add unit tests that parse rendered templates for one `h1`, heading order, labelled inputs and table headers.
   - Add a test that recalculates every token contrast pair in `app.css` and fails below the thresholds.
   - Wire all of it into `checks.yml` where it can run in continuous integration.
5. **Build the Display settings** in the application (decision, requirement, model, migration, view, tests).
6. **Update the canvas.** Fix `gen.py`, `Sidebar`, `Tabs` and `TopBar` and the tokens. Regenerate the generated pages, fix the hand-built pages, and add the Display page.
7. **Record the rules going forward.**
   - Add the 22 rules to `design-system/Components.md` as a checklist every new page or component must pass, in the application and the canvas, before it is merged or published.
   - Add an Accessibility section to `Decisions.md`.
   - Add a line to `CONTRIBUTING.md`: a pull request that adds or changes a page passes the accessibility checks and updates the audit.
   - Add to `assurance/`: an Accessibility Conformance Report outline (WCAG 2.2 AA, criterion by criterion) and a draft accessibility statement. Add an accessibility line to the readiness review.
8. **Be honest about the manual pass.** Automated checks catch only part of WCAG. List exactly what still needs a manual keyboard and screen reader pass in a real browser (NVDA on Windows, VoiceOver on Mac), and do not claim it has been done.
9. **Publish the canvas.** One `publish_files` to the canvas with every changed page, the shared parts, `canvas.json` and the tokens. One to the design system with `Accessibility.md`, `Components.md`, `Decisions.md` and `tokens.json`.
10. **Report** to Alex in a few lines:
    - the pull requests opened
    - what was fixed
    - the contrast results
    - what still needs the manual pass
    - how many artifact publishes are left today

## Part 7. Rules that must not be broken while fixing

- Restrained colour, Geist type, no gradients, no decorative effects, no AI slop, no taglines, no marketese, no description paragraphs, no design notes in the interface.
- The column is always Aircraft Registration. Show the SRG1782 Type Rating verbatim.
- Aircraft status is Serviceable or Unserviceable.
- Tables stay one line per row, expand on click, and never wrap cell text.
- Amber means due soon and red means overdue only; green only in a Status column.
- The Required Reading button says Acknowledge.
- No locations or addresses in the Marketplace. Organisation names stay exactly as the CAA lists them.
- If an accessibility fix seems to clash with one of these rules, keep both where possible (for example, a stronger border without adding colour). If it is truly impossible, stop and ask Alex rather than choosing.
