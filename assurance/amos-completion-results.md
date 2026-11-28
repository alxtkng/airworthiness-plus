# AMOS local completion evidence

28 November 2026. The validation branch started at `5b18ede` and integrated `origin/main` `91f9176`, retaining the calibration decision as ADR-0010. The transfer pilot is ADR-0012. Aircraft records, dispatch and the structured work-card pilot were built and verified in separate worktrees, then tested together. The provisional Stores producer contract and candidate source are recorded separately. [Case evidence and dependencies](amos-evidence-matrix.md) · [Stores producer review](phase-4-stores-handoff.md)

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

## Release evidence boundaries

The local release exercise uses disposable PostgreSQL 16.14, Python 3.13, Chromium 158, Node.js 24 and OpenSSL 3.5.9. The data set is synthetic. Raw logs, public verification material, the two receiver databases and reconciliation outputs are retained in the workspace folder `amos-completion-evidence-2026-11-28`. The locally stopped PostgreSQL cluster and the normal-form captures are separate from any hosted service. [Rehearsal procedure](../operations/amos-parallel-handover.md)

| Owner | Prerequisite | Next evidence |
| --- | --- | --- |
| Alex King as likely Goods In producer owner and the requirements owner | Confirm the checked producer revision, responsibility for as-received data and legacy evidence, and the proposed clarification to REQ-357 | Record approval and repeat representative cases with the applicable receiving and Stores procedures |
| Structures, technical records and operator maintenance leads | Applicable approval and aircraft population, source content and rights, authorised people and procedures | Lightning record and flight-log provenance through the operator's actual workflow and independent drawing or source review |
| Airworthiness Limited and Airlines for America | Applicable licensed ATA revisions and agreed publication terms | Exercise Spec 2500 and the agreed Spec 2000 Chapter 16–18 profiles with an independent operator system |
| Approval holder, trust-service specialist and signing provider | Per-action approval basis, sandbox contract and access, provider proof format, record preservation policy | Complete sandbox identity, digest, timing, decline, delay, replay, archive and recovery cases, then validate the selected PDF/A and PAdES profile independently |
| Issuing and receiving records leads | Agreed bilateral trust procedure, identity enrollment and authentic status distribution | Independently receive, update and verify issuer trust, maintenance authority and time evidence through the operator's routes |
| Airworthiness Limited and independent assessor | Commissioned assessment, signed scope and isolated authorised deployment | Record findings and retests against the candidate. [Issue #40](https://github.com/alxtkng/airworthiness-plus/issues/40) |
| Hosting and operator trial owners | Authorised hosted environment, backup access, participants, training and change classification | Measure hosted recovery, parallel reconciliation and stabilisation. Record operator go/no-go and any authority acceptance separately |
