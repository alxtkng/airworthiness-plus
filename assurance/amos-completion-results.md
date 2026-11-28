# AMOS completion evidence

28 November 2026. The validation branch started at `5b18ede` and initially integrated `91f9176`, retaining the calibration decision as ADR-0010. The transfer pilot is ADR-0012. Aircraft records, dispatch, signing and Stores were built and verified in separate worktrees. Stores PR #167 merged during validation at `642f1b8` and became the integration base. Alex King recorded approval of the receipt-to-stock contract and REQ-357 clarification in the parallel work. [Case evidence and dependencies](amos-evidence-matrix.md) · [Stores producer review](phase-4-stores-handoff.md) · [Merged Stores PR #167](https://github.com/alxtkng/airworthiness-plus/pull/167)

## G-EJKL reconciliation

The live browser trial starts with G-EJKL's open deferred headset defect. The continuing airworthiness manager records a programme and repeat inspection with an applicable synthetic instruction, issued revision 2 and `Clearance 1.2 mm`. The same role records a reading of 11,208.6 hours and corrects it to 11,207.0. The sender exports the original before correction and signs it with the offline trial signer. The correction is linked to the signed predecessor. The recipient imports the final aircraft export and separately supplied synthetic trust, independently calculates the next due date as 18 December 2026 and replays the transfer. The actual signatory assertions come from detached synthetic signatures. The work-card provider queue is exercised through its own normal screen. [Browser trial and fallback](../tests/e2e/test_parallel_handover.py) · [Mobile queue and retry](../tests/e2e/test_records.py)

The project-format comparison additionally used two independently implemented receivers. Each preserved source UUIDs and found zero missing or changed mapped fields. The Python receiver checked the archive history and the reading signatures. The JavaScript receiver recomputed the due date and independently verified both signatures and the synthetic grant against the separate trust input. The updated trust snapshot verified in a fresh receiving database. The receivers refused unsupported versions, duplicates, missing or dangling dependencies, wrong aircraft, altered evidence and absent or expired authority in their respective acceptance checks. Acceptance uses the mapped subset of the archive. The source remains the reference for all other records. [Reconciliation format and verification](../architecture/decisions/ADR-0012-aircraft-transfer-pilot.md)

The retained complete synthetic renewal fixture was imported and replayed with both generations verified. The predecessor revocation status for the exact retained historical tokens remains indeterminate. The G-EJKL signing time is signer-asserted. The RFC 3161 exercises establish proof that each relevant signature existed by the verified token time. Maintenance authority was tested under a synthetic grant only. [Renewal report](gejkl-evidence-renewal.md) · [Historical status report](gejkl-historical-timestamp-status.md)

## Executed comparisons and early runs

| Revision or source | Selection | Result |
| --- | --- | --- |
| `e7a2743` | Original baseline selection with PostgreSQL and live Playwright | 230 passed |
| `8edecac` | Full non-live pytest command with the live directory disabled | 1,490 passed, 76 live cases skipped, three failures in the programme table, title-case labels and dispatch form declaration |
| `8edecac` | Initial full live walk | Interrupted after seven passes. Dispatch previous and next links extended graph discovery across the calendar. The dedicated dispatch case now exercises both links, and the graph walk traverses finite application links |
| `4669e5a` | Integrated security, role, database and focused browser pack with real post-signing archive refusal and retry | 321 passed, one dispatch form declaration failure. The display and retry of a retained signed result passed. The declaration failure passed on targeted rerun after `7284d91` |
| `4669e5a` | Two signed receiving implementations | Passed. The Python receiving transaction and checks took 0.017 seconds. The JavaScript receiver took 0.717 seconds for import, 0.690 for replay and 0.563 for the independently pinned update. Both kept the original identifiers and matched all mapped fields |
| `e7a2743` | Three-record signed transfer from normal forms | Passed, including replay. The earlier browser attempt lacked setup of the aircraft's programme. The rerun creates it through the normal form before adding the inspection |
| `3cff07d` | Populated upgrade and native rollback | Both retained 280 history entries with an identical digest, seven aircraft, four open defects, three pending orders and no prior problem entries. Prior and candidate record checks found zero discrepancies. Native restore took 0.937 seconds |

The early mixed-worktree baseline attempt reported 200 passes and 30 failures while files changed under an already-seeded browser service. Its results remain in the logs. The fixed-revision baseline above is the reproducible baseline selection. The historic 43-check renewal run remains focused evidence.

## Published Stores migration

The full pre-port candidate `3c2e110` passed 1,498 non-live checks and 78 live browser checks after the targeted corrections. Its alternate implementation of Logistics 0007 and 0008 was present only in the local candidate. A disposable upgrade from the published PR #167 schema refused that candidate when it encountered its former `logistics_storesappointment` dependency. The port uses PR #167's published `StoreLocation`, `StockResolution` and `StockPosting` with both published migration files byte-identical to `642f1b8`. Previous test totals belong to the pre-port implementation.

The published-state fixture provisions four actual stock postings and five movements with open legacy, quarantine and return states. For the station-only intermediate revision `8575fe8`, the fixture preserved every published record projection and the exact event identities and hashes through migration, normal signed-in reads and native restore. Both source and recovered copies reported zero record-chain discrepancies. The retained fixture checks main 7, station-prefix ZRH 8, network 10, physical quarantine 2 with zero available and tenant refusal. The separate station acceptance test uses configured station codes, with ZRH Line 1, BSL 1, LUG 1 and GVA 0 explicitly visible.

The final code revision `523f094` applied `0009_station` and `0010_maintenance_custody` over actual published records. All 72 original Stores audit events and every published Stores record identifier matched before migration, after migration, after signed-in export and after restore. The identical projection digest was `b6885df7003f56e7b01ad15be96f6420727ac16623c25515e9f6b6a2f3e95f0c`. The manifest and history verifier accepted all three signed-in archives. The prior `5b18ede` populated cutover also passed against this revision and restored 280 previous history entries, seven aircraft, four open defects and three pending orders in 0.912 seconds. Both rehearsals reported zero record discrepancies. Reusable source and the exact logs are under `pr167-migration` and `pr167-original-prior-cutover.log` in the local evidence folder.

The first published-main intermediate run at `8575fe8` reported 129 passes and one older signed-record upgrade test calling a retired test helper argument. Its targeted rerun passed. The next custody export selection at `da1554d` reported 28 passes and one failure in the same upgrade check because its restricted owner fixture transferred only table ownership. The final test gives the temporary migration owner the published balance function it replaces. The actual populated-schema migration and restore kept their existing migration owner throughout.

## Final candidate checks

| Selection at `523f094` | Result |
| --- | --- |
| Full non-live pytest suite in five disposable PostgreSQL shards | 1,492 passed, zero failures or skips |
| Full live Playwright suite in five disposable PostgreSQL shards with exhaustive persona navigation | 78 passed, zero failures or skips |
| Original baseline selection rerun on the final candidate | 230 passed, zero failures or skips |
| Focused signed transfer and normal-form G-EJKL replay | Two passed. Both receivers matched all mapped fields and preserved the IDs. The measured import time was 0.017 seconds for Python and 2.072 seconds for JavaScript. JavaScript replay took 1.079 seconds and re-import against the separately updated synthetic trust took 1.967 seconds |
| Retained renewal fixture replay | The complete chain verified. The exact retained predecessor tokens still have indeterminate revocation status |
| Local release checks | Ruff lint and format, strict mypy, all 249 traceability rows, locked environment and secret scan passed. Dependency audit found no known vulnerabilities and the SBOM was retained |

The final local implementation candidate was `523f094`. Logs prefixed `pr167-final-` identify those local runs. The local suite totals exclude the separately reported baseline, focused reruns and migration rehearsals.

## Post-merge CI on main

PR #170 merged to `main` on 28 November 2026 as `5c0c81e9df21052790fdc0bb0ce628015162d7dd`. GitHub Actions Checks run #46148864025 was triggered by that push and completed successfully on its first attempt. [Merge commit](https://github.com/alxtkng/airworthiness-plus/commit/5c0c81e9df21052790fdc0bb0ce628015162d7dd) · [CI run](https://github.com/alxtkng/airworthiness-plus/actions/runs/46148864025)

| Check | Verified result |
| --- | --- |
| PostgreSQL-backed pytest | 1,494 passed. The job deferred 78 browser tests to the dedicated live step |
| Live Playwright | All 78 passed with exhaustive persona navigation enabled |
| Quality and supply chain | Locked dependency installation, Ruff lint and formatting, mypy, dependency audit, secret scan and traceability passed. The dependency audit reported no known vulnerabilities |
| Container build and runtime smoke test | The service image built. The smoke test found the expected static CSS and Geist font, verified that `/app/.git` was absent and ran Gunicorn 23.0.0 as UID 10001. [Job log](https://github.com/alxtkng/airworthiness-plus/actions/runs/46148864025/job/140990784427) |
| Software bill of materials | Generated and uploaded by CI. [SBOM artifact](https://github.com/alxtkng/airworthiness-plus/actions/runs/46148864025/artifacts/15265566100) |

## Open operational acceptance evidence

The local release exercise used synthetic records with disposable PostgreSQL 16.14, Python 3.13, Chromium 158, Node.js 24 and OpenSSL 3.5.9. Raw logs, public verification material, the two receiver databases and reconciliation outputs are retained in the workspace folder `amos-completion-evidence-2026-11-28`. The following evidence is still open as of the post-merge run. [Case-level status](amos-evidence-matrix.md) · [Rehearsal procedure](../operations/amos-parallel-handover.md)

| Owner | Prerequisite | Next evidence |
| --- | --- | --- |
| Approval holder and operator Stores lead | Applicable authority and maintenance data, staff appointments and the operator’s receiving and custody procedures | Repeat representative receiving, exact and alternate issue, quarantine and return journeys against the approved procedures. The product-level producer contract approval is recorded separately |
| Structures, technical records and operator maintenance leads | Applicable approval, authorised source data and drawings, appointed staff and procedures | Exercise maintenance history, lightning damage, flight-log provenance, dispatch and handover with operational users. Confirm drawing applicability and revision, manufacturer work-card source rights and the applicable inspection procedure |
| Airworthiness Limited, Airlines for America and the receiving operator | Applicable licensed ATA revisions and agreed publication terms | Exercise Spec 2500 and the agreed Spec 2000 Chapter 16–18 profiles with an independent operator system |
| Approval holder, trust-service specialist, signing provider and archivist | Per-action signature assurance, authorised sandbox access, provider proof format and record preservation policy | Run authenticated provider identity, digest, timing, decline, delay, replay and recovery cases. Validate the selected PDF/A and PAdES profile independently and exercise the storage adapter if the deployment requires one |
| Issuing and receiving records leads | Bilateral trust procedure, identity enrollment, independent trust distribution and authentic status services | Rehearse trust updates and rollover, and independently verify issuer trust, maintenance authority and time evidence. Revocation status remains indeterminate for the exact retained predecessor tokens |
| Airworthiness Limited and independent assessor | Commissioned penetration test with agreed scope and an isolated authorised deployment | Record findings and retests before use of customer data. [Open issue #40](https://github.com/alxtkng/airworthiness-plus/issues/40) |
| Hosting and operator trial owners | Authorised hosted environment, backup access, recovery owner, participants, training and change classification | Exercise hosted backup and restore, parallel reconciliation, fallback, cutover and stabilisation. Record the operator's go/no-go decision and any applicable competent-authority acceptance |
