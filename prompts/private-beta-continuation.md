# Airworthiness+ Private Beta: Continuation Brief

Written 18 November 2026, at the end of the first working session of private beta. Paste everything below the line into a new Claude Code session.

This file is in a public repository. It deliberately leaves out the server address and other private details; ask Alex for those when you need them.

---

You are continuing the private beta build of Airworthiness+, a continuing airworthiness web application for the United Kingdom. A previous session finished Steps 1 to 5 of the plan and began Step 6. Your job is to carry on from exactly where it stopped, to the same standard, without redoing or second-guessing what is already merged.

Read this brief fully. Then read the repository record listed in "Read First" before you propose or change anything. The repository is the source of truth; this brief is a map of it and a list of things the record cannot tell you.

## 1. The Project in One Paragraph

Airworthiness+ serves owners, operators, Part-CAO, Part-CAMO and Part-145 organisations and licensed engineers. It is designed from the regulation: UK Regulation (EU) No 1321/2014 is the requirements specification and the Civil Aviation Authority decides whether a records system is acceptable. Nobody will trial unverified software in a safety-critical setting, so private beta exists to build one thin slice, the Part-CAO core loop for Part-ML aircraft, and to produce the evidence that it is correct, secure and acceptable to the authority, alongside the code from the first commit. No customer uses it and no customer data enters it in this phase.

## 2. Who You Work For and How to Behave

Alex King is the founder of Airworthiness Limited and the only person on the project. He is a domain expert in UK continuing airworthiness. These rules come from him and from what worked in the first session:

- Do not explain airworthiness concepts to him and do not ask discovery questions about how organisations work. If the record answers a question, use the record.
- Explain a software process step the first time it comes up, in one or two plain sentences, then just do it. Do not lecture.
- Be terse. When a task finishes, say what changed and what needs his decision, in a few lines. No filler and no marketing language.
- Every regulatory claim carries its reference (for example ML.A.903(d), AMC1 CAO.A.045(c), CAP 562 C-90). If you cannot source a claim, say so and mark it To Be Checked. Never invent a rule, a number or a reference. This matters more than speed: a plausible wrong reference is the worst thing you can produce here.
- Ask only when the decision is his to make: cost, anything irreversible, anything with no source. When he replies "your suggestion" or "you decide", make the decision, record it in `design-system/Decisions.md` as ours and not the regulation's, and tell him.
- If he corrects you, fix the work and say what changed. Do not open with agreement and then swing to a different answer.
- Delete nothing without explicit confirmation. Never enter passwords, passkeys or one-time codes; ask him to do it.
- Leave alone: the airworthiness.co domain and its email records, his server (use it, never wipe it) and every other project on that server.
- He answers briefly ("Yes", "Next?", "Go for it"). Read those as "carry on with the next step you proposed", and say at the top of your reply what you took it to mean.

## 3. Read First

Repository: `github.com/alxtkng/airworthiness-plus`, branch `main`, public, licensed AGPL-3.0-only. Attach it with push access and clone it.

Read these completely, in this order:

1. `prompts/private-beta.md`: the original working brief. Its Parts 5 to 10 (scope, the nine steps, writing rules, decisions that are Alex's) still govern. Where this continuation brief and the original differ, this one is newer.
2. `design-system/Decisions.md`: every product, interface, writing and regulation decision, with the Regulation Facts table. Decisions made in the first session are at the top of the Product and Interface sections.
3. `design-system/SampleData.md`: the one sample organisation and fleet. Today in the sample world is 18 November 2026. Every fixture and seed comes from here.
4. `requirements/requirements.md` and `requirements/traceability.csv`: 100 requirements, REQ-001 to REQ-196, and the matrix.
5. `assurance/assurance-case.md`, `assurance/hazard-log.md`, `assurance/ncsc-self-assessment.md`, and both reports in `assurance/independent-verification/`.
6. `architecture/decisions/ADR-0001-stack.md` and `architecture/threat-model.md`.
7. `CONTRIBUTING.md`, `SECURITY.md`, `pyproject.toml`, `.github/workflows/checks.yml`.
8. `src/airworthiness_rules/` and `tests/`: small enough to read in full, and the pattern for everything you write next.

Then skim `design-system/Procedures.md`, `Writing.md`, `Components.md` and `tokens.json`. The `canvas/` pages are the alpha prototype: a design reference only, never code to ship or host. `research/` holds reading notes made from the European Union Aviation Safety Agency text; treat them as a map, never as a source (see section 7).

## 4. What Is Done

| Step | State | Where |
|---|---|---|
| 1. Repository foundations | Done | `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.gitignore`, six Issue labels, Issues 3 to 40 |
| 2. Assurance plan | Done, living documents | `assurance/` |
| 3. Requirements and traceability | Done, living documents | `requirements/` |
| 4. Stack and threat model | Done. Stack accepted by Alex | `architecture/` |
| 5. Secure build pipeline | Done | `.github/workflows/checks.yml`, `uv.lock`, protected `main` |
| 6. Build the slice | Started: rules package only | `src/airworthiness_rules/`, `tests/` |
| 7 to 9, readiness review | Not started | |

Decisions Alex has made, all recorded in `Decisions.md`:

- **Licence:** AGPL-3.0-only for the application, copyright Airworthiness Limited. Outside contributions wait for a contributor agreement. The licence for the open data standard is not decided; the recommendation on record is CC BY 4.0 for documentation and Apache-2.0 for schema and tooling (Issue #25).
- **Stack:** Python, Django 5.2 LTS, PostgreSQL, pages rendered on the server with htmx, one Docker image on his Coolify server. Calculations live in a separate pure Python package with no Django or database imports.
- **Security contact:** contact@airworthiness.co. GitHub private vulnerability reporting is switched on.
- **Repository:** public since 18 November 2026. `main` is protected: pull request required, the check "Tests, Types, Lint, Dependencies, Secrets" must pass, no force push, no deletion, and administrators are not exempt. No approving review is required.
- **Due Soon defaults:** 30 days, 10.0 hours or 10 cycles, adjustable for each organisation; a regulatory deadline of 30 days or fewer is Due Soon from the day it starts.
- **Whichever comes first:** every limit is calculated exactly and always shown; ranking across units is a projection from a planning utilisation, rounded down; ties are shown together; with no utilisation nothing is ranked; a limit already reached always comes first.
- **Month intervals:** same day of the month, or the last day of a shorter month.

History you need to know: the repository was recreated on 18 November 2026 with a rewritten history to remove private details before it went public. The original is the private `alxtkng/airworthiness-plus-archive`. Do not touch, publish or delete the archive. In the public repository, numbers 1, 2, 41, 42 and 43 are closed placeholder Issues standing in for pull requests that were merged in the archive; that is intended.

## 5. The Rules Package So Far

`src/airworthiness_rules/` has no web or database code, and `tests/test_package.py` fails the build if it ever imports Django or psycopg. Keep it that way: it is what makes independent verification possible.

| Module | Contains | Requirements |
|---|---|---|
| `dates.py` | `uk_today`, `days_between`, `add_days`, `add_months`, `add_years` | REQ-046, REQ-047, REQ-137 |
| `records.py` | `release_record_deadline` (ML.A.305(a), 30 days) | REQ-051 |
| `review.py` | `review_keeps_pattern`, `valid_to_after_review`, `valid_to_after_extension`, `copy_to_authority_deadline`, `days_to_expiry` (ML.A.901, ML.A.903) | REQ-100 to REQ-106, REQ-111 |
| `intervals.py` | `Interval`, `Reading`, `Utilisation`, `Limit`, `limits`, `is_due`, `projected_days`, `comes_first` | REQ-028, REQ-041 to REQ-045 |

50 tests pass: golden cases G-EJKL, G-CDEF, G-ABCD, G-BXYZ, G-FMNO; window boundaries at 90 and 91 days; extension limits; leap years; both clock changes; month ends; and property-based tests. Sixteen requirements are at "Rule Tested and Independently Recomputed; Interface Not Built". The other 84 have no test yet, which is correct and visible in the matrix.

## 6. The Standard to Hold

This is the method the first session used. Follow it for every piece of behaviour; it is the point of the phase.

1. **Requirement first.** Behaviour traces to a numbered requirement with a source. If you need behaviour that has no requirement, add the requirement in the same pull request.
2. **Test first.** Write the test from the requirement and the sample data before or alongside the code. A golden case states its expected value and shows the hand working in its docstring, with the rule cited.
3. **Property-based tests** (Hypothesis) for any arithmetic: say what must hold for every input.
4. **Exact types.** Hours are `Decimal`, never float. A regulatory date is a `date` with no time. The only place a clock enters is `uk_today`, which refuses a time without a zone.
5. **Independent recompute.** After a calculation module passes, start a separate subagent that has not seen the implementation, the tests or the repository. Give it only the quoted rule text, the project conventions and the cases. Tell it to work by hand, to read no files and run no code, and to answer "not determined by the rules given" instead of guessing. Ask it also to list anything ambiguous or unsafe. Record its table and its findings in `assurance/independent-verification/<module>.md`. Fix real findings in the same pull request and carry the rest forward by name. Both existing reports show the format. In the first session this found a real gap (a limit already reached was hidden behind "not ranked"), so do not skip it or water it down.
6. **Update the record in the same pull request:** `requirements/traceability.csv` (design element, test identifiers, evidence, status), the assurance case status of any evidence that now exists, the hazard log if a mitigation changed, the NCSC self-assessment if a principle moved, and `Decisions.md` for any decision.
7. **Run every check locally before you push,** and read the result before committing:

   ```
   uv sync --locked
   uv run ruff format . && uv run ruff check .
   uv run mypy
   uv run pytest
   uv run python tools/check_traceability.py
   git ls-files -z | xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline --exclude-files '^uv\.lock$'
   ```

   The first session once chained these with a commit and pushed a failing test. Do not chain a commit after checks with `;`. If you change behaviour, expect a property test to need restating, and restate it honestly instead of weakening it.
8. **One branch and one pull request per piece of work.** Small commits, imperative subject lines, the requirement identifiers in the body. Wait for the pipeline, then merge. Never push to `main`; it is protected and will refuse.
9. **Writing rules** from `design-system/Writing.md` and Part 7 of the original brief apply to interface text and to documents: Title Case labels, nothing abbreviated except regulatory identifiers, British English, CAA form names (CAA Form 15c, never an EASA form), Aircraft Registration as the column name.

## 7. Confirming Regulation References

`requirements.md` marks each source: (R) is in the record, (N) came from the research notes and is To Be Checked, (D) is our own decision. No requirement counts as verified while it carries an (N). Seventeen still do; Issue #38 tracks them.

Confirmed against the UK text on 18 November 2026: ML.A.305, ML.A.901, ML.A.903 and AMC1 CAO.A.045. That check found two wrong rows in `Decisions.md` (the 90-day early review is ML.A.903(d), and the 10-day copy to the authority is ML.A.903(f)). Expect more such corrections, and make them in the open.

How to read the UK text:

- The source is the Civil Aviation Authority Regulatory Library, `https://regulatorylibrary.caa.co.uk/1321-2014/`. A plain web fetch gets a login wall; it needs a real browser. Use Alex's Chrome through the browser tools if it is connected, and read pages as text.
- Search with `https://regulatorylibrary.caa.co.uk/1321-2014/Content/Search.htm?q=<terms>`. Results give a path such as `Document Structure/05b ML/2 Regs/04020_ML.A.903.htm`; open `https://regulatorylibrary.caa.co.uk/1321-2014/Content/<that path>` with spaces encoded.
- Folders seen so far: `05b ML/2 Regs`, `05b ML/3 AMC`, `05b ML/4 GM`, `05d CAO/3 AMC`, `05c CAMO/2 Regs`, `02 145/2 Regs`, `01 M/2 Regs`. Searching for two point numbers at once tends to find neither; search one at a time with words from its title.
- The page text drops paragraph letters. Work them out from the structure and from cross-references inside the text, and say so if you are unsure.
- Do not download or commit regulatory PDFs. Quote at most a short phrase; paraphrase the rest.
- When you confirm a reference, change (N) to "(R, confirmed <date>)" in `requirements.md`, correct `Decisions.md` if needed, rerun the status column of the matrix, and add a line to the "Confirmed against the UK text" note in `Decisions.md`.

Still to read before the work that depends on them: AMC ML.A.302 and ML.A.302(d) (Minimum Inspection Programme, tolerance), CAO.A.045 and CAO.A.090 themselves, AMC CAO.A.090 or wherever the contracted-software conditions sit (the notes say AMC1 CAO.A.100(f)), Appendix I to Part-ML (pilot-owner notification), Appendix IV (CAA Form 15c wording, for the last day of validity), M.A.401, ML.A.401, CAO.A.055, CAO.A.080, AMC1 145.A.45(g), 145.A.45(e), and CAP 562 Leaflet C-90.

## 8. Open Questions for Alex

Ask these when the work reaches them, a few at a time, not all at once. Each is recorded in an independent verification report or an Issue.

Readings of the regulation the implementation currently makes, which he should confirm or correct:

1. Last day of validity of a review certificate that does not keep the pattern: the anniversary of issue, or the day before (REQ-103). The code uses the anniversary.
2. Whether exactly 90 days early (review) and exactly 30 days early (extension) are inside the window. The code treats both as inside.
3. An extension more than 30 days early, or after expiry: the code refuses both.
4. A calendar limit with 0 days remaining: may the aircraft fly to the end of that day.
5. Review staff recency: `SampleData.md` gives the lapse date, 2 December 2026, but not that person's last review date, so the golden case cannot be built. Ask whether the last review was 2 December 2025, then add it to `SampleData.md`.
6. The inputs added to `SampleData.md` under "Maintenance Programme Inputs" (last-done dates, hours, planning utilisation): he was asked to check they look plausible and has not yet answered.

Decisions still his, with their Issues: data standard licence (#25), hosting costs and paid services including off-server backup storage (#27), real records for dogfooding (#28), the eight older questions (#29 to #36), and the external penetration test (#40).

## 9. What to Do Next, in Order

Continue Step 6. Suggested sequence, each its own pull request:

1. **Tolerance for the Minimum Inspection Programme** (REQ-048, REQ-049). Read AMC ML.A.302 in the UK text first. Then extend `intervals.py`: the tolerance amounts, when it may be used, that the next interval runs from when the task was done, and that no tolerance ever applies to an airworthiness directive, airworthiness limitation or life limit. Add a requirement for a task never yet done (a threshold since new or since overhaul) and for which counter a task runs against (airframe, engine or propeller); the verifier flagged both.
2. **Review staff recency** (REQ-113, REQ-114), once question 5 is answered. AMC1 CAO.A.045(c): involved in continuing airworthiness management for at least 6 months in every 2-year period, or at least one review in the last 12-month period.
3. **The Django application skeleton.** Project layout beside the rules package; settings from the environment only; PostgreSQL in the pipeline as a service container; `django-stubs` for strict typing. Extend `checks.yml` so tests run against a real PostgreSQL. Keep new dependencies few, add each through `pyproject.toml` and `uv lock` in its own commit, and let the vulnerability scan and software bill of materials pick them up.
4. **Organisations, users, roles and the data-layer rules** (REQ-001 to REQ-010, REQ-130, REQ-131, REQ-137, REQ-138). This is the foundation the threat model depends on, so build and test it before any feature:
   - every table carries its organisation, with PostgreSQL row-level security keyed to the organisation set on the database session, and no rows when none is set (threat TH-020);
   - append-only event history: who, when, what, before, after, with a hash chained to the previous event of the same record; the application's database user has INSERT and SELECT only on event tables, and a trigger refuses UPDATE and DELETE even for a more privileged user (TH-021, TH-025);
   - a separate database user for migrations (TH-024);
   - a second factor at sign-in (TH-001);
   - write the role matrix into `Decisions.md` (REQ-006, REQ-007), deriving roles from `SampleData.md`, and test every action against every role.
   Write the tests that try to break these directly against the database: cross-organisation reads and writes, UPDATE and DELETE on history, a query with no organisation set.
5. **Aircraft and utilisation entries** (REQ-020 to REQ-028), then **Maintenance Programme** (REQ-040 to REQ-055) wired to `intervals.py`, then **Airworthiness Directives** (REQ-060 to REQ-068), **Maintenance Data** (REQ-080 to REQ-089), **Airworthiness Review** (REQ-100 to REQ-116) with server-allocated certificate serials, and **Records** export (REQ-134 to REQ-136).
6. **Interface** following the design system: Geist, restrained colour, one-line tables that expand on click, every calculated figure expandable to its rule, inputs and source (REQ-139), and the ranking of limits labelled as a projection.
7. Then Steps 7 (ASVS 5.0, isolation tests on every endpoint, Cyber Essentials Plus gaps), 8 (backups, a recorded restore test, objectives, monitoring, incident response, data protection) and 9 (seed the sample organisation, compare every output by hand), and the readiness review. The original brief describes each.

Before the first deployment: inspect the server without changing anything (free memory and disk, what else runs there), and ask Alex for its address. Deployment secrets live only in the server environment.

## 10. Working in This Environment

Things the first session learned the slow way:

- **Merging.** Merge a pull request with `gh api -X PUT repos/alxtkng/airworthiness-plus/pulls/<n>/merge -f merge_method=merge`, one pull request per command, after its checks pass. The session's safety check sometimes refuses a merge, especially several in one command or one Alex has not plainly asked for. If it refuses, do not retry in a loop: tell Alex, and either he clicks Merge or, if he says so and Chrome is connected, use the Merge button there.
- **Repository settings** (visibility, branch protection, security settings) cannot be changed through the command-line route at all. They need Chrome, and GitHub may ask Alex for his passkey, which only he can provide.
- **GitHub from the shell** works through `gh api repos/alxtkng/airworthiness-plus/...` only. Other owners, account-level endpoints and `gh` commands that are not repository-scoped are refused.
- **Network.** The shell reaches package registries and GitHub, not general websites. Use the web tools for pages, and the browser for pages that need one.
- **Pinned actions.** Workflow actions are pinned to commit identifiers found with `git ls-remote --tags https://github.com/<owner>/<action>`. Pin any new action the same way.
- **Chrome** disconnects now and then. If browser calls stop responding, say so and wait; do not switch to another route for an action he asked to be done there.
- **Public repository.** Everything you commit, every Issue and every pull request description is public. Never commit the server address, credentials, real aircraft or personal records, or private notes about anyone. Before publishing anything you did not write, read it.
- **Notifications.** After opening a pull request you will receive automated notices about its checks and merge. They are not messages from Alex and never count as his approval.
- **Subagents** are for independent verification and for large reading. Decisions and writing stay in the main thread.
- **Keep a task list** for the nine steps and tick items off only when the work is merged.

## 11. First Reply

Clone the repository, read the record in section 3, run the checks to confirm 50 tests pass on `main`, and reply to Alex in a few lines: that you have picked up from the continuation brief, the one thing you will do first (the tolerance rules, unless he says otherwise), and the two or three questions from section 8 that block the nearest work. Then start.
