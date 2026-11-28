# AMOS workflow validation on the Phase 4 Stores branch

28 November 2026. See the [18 screenshot cases](../research/amos-workflow-assessment.md). This run used synthetic records on the local Stores worktree at baseline `9eb703b`, with PostgreSQL 16.14 and Playwright using Chrome 158 on loopback. The handover test was added to this worktree. No live aircraft or customer records were used.

## Executed baseline

**225 existing checks passed** across the selected Django and live browser suites.

| Screenshot cases | Evidence exercised | Open work |
| --- | --- | --- |
| 1–3 | Deferral, defect closure, repeat defect actions, written work orders, repair/change records and aircraft export | Combined faceted search, damage chart and pilot-origin technical log |
| 4 | Browser receiving, recorded checks, quarantine, return and once-only handoff to the linked stock entry. Service and migration tests cover the evidence and shelf-life rules of the current receiving flow | Stock ledger, station/main/line aggregation and practical training exercise |
| 5 | Browser roster publication, a long-shift warning, capacity, outstanding inspection handover and acknowledgement by the named incoming person. Calculation checks include week and midnight boundaries | Intraday dispatch and assignment conflict trial |
| 6 and 14 | Browser aircraft and organisation archive download and verification, selected two-person imports, export isolation and retained history. Separate archive checks cover altered, missing or duplicate files | Full receiving-side import, ATA format conformance and trust material from a separate source |
| 7–13 and 16 | Passkey and recent verification controls, maintenance authorisation, applicable revision, work-package issue, inspection, release and evidence retention | In-app step signing, signer certificates, document-bound verification, signing and archive states, external provider integration, and independent security assurance |
| 15, 17–18 | Acceptance records for parallel run, problem log and written approval, plus the local archive reconciliation below | Two-organisation operational trial, independent issuer validation, training, fallback rehearsal and stabilisation |

## Executed single-aircraft handover

**One additional test passed.** It uses the synthetic G-EJKL fixture. The sender records a recurring 30-day inspection completed 10 days before the test date and exports the aircraft. The recipient check uses the archive and a reference digest from the issuing side. The assertions show:

- The unresolved defect remains open and deferred. The archived limit matches the source forecast.
- The inspection completion and interval are present. Calculation from the archive gives 20 days remaining on the fixture date and agrees with the source forecast.
- The original 11,208.6-hour reading and the corrected 11,206.8-hour reading both survive, with the correction linked to the original.
- The offline verifier accepts the archive and yields the same manifest digest as the issuing side.

The correction in this test is an existing utilisation correction. The corrected signed record, independent issuer trust and import into another operational system remain scenarios for later. The first draft of the test used the defect title alone to find the forecast line. The assertion was corrected to match the actual deferred-defect forecast label. Application code was unchanged.

## Reproduce

Use an isolated test database and the setup in the [test guide](../tests/e2e/README.md). From the worktree, run the following baseline selection using the configured Django environment with `AIRWORTHINESS_E2E=1` and `AIRWORTHINESS_E2E_POSTGRES` pointing to the disposable PostgreSQL cluster.

```sh
uv run pytest -q \
  tests/test_defects.py tests/test_modifications.py tests/test_receiving.py \
  tests/test_golden_roster.py tests/test_roster_evidence.py tests/test_work_packages.py \
  tests/test_passkeys.py tests/test_exports.py tests/test_imports.py tests/test_acceptance.py \
  tests/e2e/test_receiving.py tests/e2e/test_records.py tests/e2e/test_maintenance.py \
  tests/e2e/test_journeys.py
```

The current selection also includes the new handover test. To rerun only that case:

```sh
uv run pytest -q tests/test_exports.py::test_handover_archive_preserves_deferral_inspection_and_correction
```

## Rebased baseline and local delivery

The historical Phase 4 Stores worktree remains at `9eb703b` with its local records. Remote `main` was verified at `d1da03fe508109a5f123c20ee3e86cee7c559725`. The locked environment ran the selection above on a detached checkout of `142dda6`, which carries the earlier handover regression onto that main revision. **226 passed, with zero failures or skips**, in 259.27 seconds. The result includes the existing unsigned utilisation correction and belongs separately to the baseline.

| Revision | Increment | Local evidence |
| --- | --- | --- |
| `f48ea98`, with integration fixes at `6e2f78b` | Faceted history from Aircraft and Work Packages | Browser search joins aircraft, ATA, date and state. Chapter 25 includes 25-21 and 25-22, exact section narrows, report and rectification searches are separate, and keyboard navigation opens the source. Django exercises related defect, original written order and package links. |
| `bd7d083` | Stores training | 245 selected checks on source branch `e0b2036`. The guided exercise verifies Main 7, station 8 and network 10, two availability deductions and preserved custody. [Stores evidence](stores-lookup-exercise.md) |
| `f69a90c` | Synthetic work-card attestation, source branch `958a947` | 305 selected checks on the source branch, including the 390-pixel review, step-up and cancellation, duplicate completion, failed archive rollback and retry, evidence export and release regression. [Attestation evidence](amos-synthetic-attestation.md) |
| `5f6d8d9` | Parallel handover and fallback | Browser records and escalates a known deferred-limit discrepancy in the receiving organisation, which cannot browse the source aircraft. The sender returns to its forecast and the second archive's record and history files match byte for byte. [Procedure](../operations/amos-parallel-handover.md) |

The focused pre-integration rerun passed all 254 selected checks. The first versions of the fallback check assumed the Problem Log status stayed **Open** after escalation, selected both the export row and its new log row, and tried to decode the CSV members as JSON. The corrected run checks **Action Taken**, selects the actual aircraft record and compares archive members as bytes. The first full integrated Django run found four failures in the aircraft tab expectation, added trigger inventory, sidebar placement and heading style, plus one browser launch skip. These were investigated against the final revision below.

## Populated upgrade and database fallback

Disposable PostgreSQL 16.14. The pre-cutover database ran `142dda6`, with a synthetic organisation seeded through the existing sample builder. The candidate migrations were run from `f69a90c`. Both `defects.0005_ata_section` and `planning.0005_workcardattestation` applied successfully. Django reported no model changes requiring a migration. The original and migrated databases agreed on 280 history events with the same ordered hash fingerprint, seven aircraft, four open defects and three pending orders. `check_records` reported zero chain problems and zero record type mismatches.

PostgreSQL's native backup and restore utilities recovered the pre-cutover copy into a separate database in 0.64 seconds. Reopening that copy with the prior application revision produced the same counts, hash fingerprint and `check_records` verdict. This local run used a private disposable directory and native database utilities. The encrypted backup pipeline and a hosted rollback are separate evidence.

## Integrated trial status

The unsigned sender archive comparison and local fallback passed. The synthetic work-card attestation pilot retains explicit version-bound consent and an archive in the source app. The three-record trial remains open for independently trusted signed original and correction, receiving import and replay, and reconciliation of all three records in the receiver. See the [18-case matrix](amos-evidence-matrix.md) for per-case results, expected outcomes and owners.

## Candidate validation

The combined code revision is `6e2f78b`. Ruff lint and formatting and mypy passed. The traceability checker found 237 requirements and 237 traced entries. The complete suite outside the live browser directory passed **1,386 checks**, with no failures or skips. This includes the standalone browser checks. The focused rerun passed **25 of 26** checks, including the schema and navigation regressions, security, maintenance history, Stores and fallback. The remaining case timed out during the signing journey's existing work-card setup. The signing branch's dedicated 305-check pass and its browser rerun outcomes remain visible in the [pilot evidence](amos-synthetic-attestation.md).

The complete live browser rerun on the same code finished with **66 passes,
three failures and zero skips**. The history, Stores, signing and fallback
journeys passed. The existing session-management and second-organisation
manager navigation journeys timed out. The existing passkey journey reached
the sign-in page instead of the expected signed-in view after password and
authenticator verification. The passkey scenario also failed in an isolated
run of the integration baseline.

## Separate receiver rehearsal

The local receiver imports the unsigned G-EJKL fixture into SQLite from a
separate Python process without Django settings or access to the source
database. It retains the deferral, inspection, original and corrected reading,
and their relevant source history. The deferral status and limit agree with
the sender and the receiver independently obtains the same next due date.
Replaying the same archive leaves one snapshot. The receiver refuses a
different snapshot for the same aircraft pending reconciliation, an altered
member, a duplicate member, the wrong aircraft, an unsupported version, a
missing defect and a missing programme dependency. The receiving database
still contains the original reconciled snapshot after those refusals.
[Receiver workflow and reproduction](../architecture/decisions/ADR-0010-aircraft-transfer-pilot.md)

The receiver displays the signed record status as unsigned and issuer trust as
indeterminate. The integrated trial still requires independently trusted
signatures on both the original and corrected record, verification of relevant
maintenance authority and a signed transfer exercise.
