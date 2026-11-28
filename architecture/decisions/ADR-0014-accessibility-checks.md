# ADR-0014. Accessibility checks in the build

Status: Proposed for review, 28 November 2026

Every page meets WCAG 2.2 Level AA (REQ-383 to REQ-410; `design-system/Accessibility.md`). Part of that can be checked by a machine on every pull request, so it is.

- **axe-core in the browser tests.** The checker is axe-core 4.14.0, run through `axe-playwright-python` 0.1.9, a development dependency only: it is not in the service image. axe-core is MPL-2.0 and the wrapper is MIT, both compatible with AGPL-3.0-only, and both are pinned by hash in `uv.lock`. It runs with the WCAG 2.0, 2.1 and 2.2 Level A and AA rules only, in `tests/test_browser.py` on the main pages, and in `tests/e2e/test_journeys.py` on every page the full walk reaches. The pull request job scans the Dashboard and the Fleet live; pushes to `main` and the weekly run scan every page. The script is put into the page by the test driver, not by the page, so the Content Security Policy is not loosened.
- **Our own checks beside it.** Contrast is recalculated from `app.css` with the formula of WCAG 2.2 and the thresholds of SC 1.4.3, 1.4.6 and 1.4.11, so a token change that lowers a ratio fails before a browser is opened. Every page the sample organisation reaches is parsed for its language, title, skip link, landmarks, headings, labels and column scopes. Every canvas page is checked the same way from its colour objects and markup.
- **What is not decided by a machine.** axe-core and these tests find part of what WCAG asks. Keyboard order, what a screen reader says, text spacing, zoom and Windows contrast themes are checked by a person; the list is in Accessibility.md, Manual Pass, and is not claimed as done.

Alternatives considered: Pa11y and Lighthouse need Node in the build, which the pipeline does not otherwise have. Calling axe-core from our own code would mean vendoring its script, which `CONTRIBUTING.md` does not allow.
