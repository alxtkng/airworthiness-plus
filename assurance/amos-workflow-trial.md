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
