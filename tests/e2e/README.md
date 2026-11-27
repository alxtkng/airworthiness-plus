# Live browser tests

The live checks complement the Django, calculation and browser tests in `tests/`.
Those tests continue to run with `uv run pytest`. The live tests use the real
WSGI application, static files, session cookies, forms and PostgreSQL records.

## Run locally

1. Start a disposable local PostgreSQL 16 or later cluster. Use a cluster
   administrator connection for fixture setup. The suite creates test databases
   and roles and tears them down. It serves on an ephemeral loopback port.
2. Run `uv sync --locked` and `uv run playwright install chromium`. An installed
   Chrome executable can be selected with `AIRWORTHINESS_BROWSER`. CI installs
   the Chromium revision tied to the locked Playwright version.
3. Set the Django environment used by the normal test suite (see
   [Contributing](../../CONTRIBUTING.md)). Set `AIRWORTHINESS_E2E_POSTGRES` to a
   connection string for the disposable cluster, including an explicit
   loopback host or Unix socket. For a local cluster using trust authentication:

   ```sh
   export AIRWORTHINESS_E2E_POSTGRES='host=127.0.0.1 dbname=postgres user=postgres'
   AIRWORTHINESS_E2E=1 uv run pytest tests/e2e -rx
   ```

   Set `AIRWORTHINESS_E2E_FULL=1` as well to follow every link offered by the
   seeded pages for each persona. The pull request job uses the shorter
   navigation check. Pushes to main and scheduled checks run the full walk.
   Browser tests fail if Chromium is unavailable.

Both sample organisations are seeded as the owner. Each scenario starts from a
clone of the seed. The running application uses a separate login that assumes
the application role. The business date is 18 November 2026. Authenticator codes
and sessions use the current time. Credentials are generated for the run.
Playwright tracing and recording are off. The loopback server uses HTTP with
local cookie settings. The existing application tests cover production HTTPS.

## Coverage and known failures

The full walk follows the pages available to the five separate sign-in roles
in both organisations. This includes the sample aircraft and their tabs,
customer records, certificates and linked form pages. It checks HTTP results
and the signed-in role. It follows normal on-screen links. Some older pages
offer links that legitimately return a permission refusal.

The form journeys exercise saved values and selected refusals. They include
aircraft, counters, programmes, directives, components, defects, contracts,
work orders, service bulletins, maintenance data, customers, settings, the
problem log, reviews and two-person import verification. They also cover
the programme departures, annual review checklist and directive sources
added in pull request 134, plus the transfer checklist and configuration
positions from pull request 135. Export tests download
both archives, run `verify_export` and check the result against the page and
selected archive contents. The fleet keyboard test operates a row at 390 pixels.

[Form coverage](form-coverage.tsv) identifies the browser case or current gap
for each form route. The inventory check in the normal suite requires an entry
when a route is added. Browser submission coverage is still partial. Forms
requiring records absent from the seed need a prerequisite journey. Use the
existing calculation, role and database tests for low-level rules. Add to the
live suite where the user journey or what is displayed matters.

`test_regressions.py` describes the three high-severity independent findings.
Their strict expected-failure markers recognise only the specified defect.
Sign-in, navigation, setup and unrelated assertion failures still fail the job.
When a product fix makes a regression test pass, remove its marker in that
fix's pull request. The default output names the expected failures.

When adding a journey, browse through the form, check the saved value after a
reload, and check what survives any refusal. Add or update the scenario in the
inventory and the relevant row in `requirements/traceability.csv`.
