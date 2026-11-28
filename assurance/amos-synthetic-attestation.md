# Synthetic work card attestation rehearsal

This increment starts from integration baseline `d1da03f` and implements REQ-380 in the synthetic workflow described by [ADR-0011](../architecture/decisions/ADR-0011-synthetic-work-card-attestation.md). The training status in the product and archive identifies the evidence as a synthetic electronic attestation.

| AMOS case | Local exercise and expected result | Remaining work |
|---|---|---|
| 7 | The 390-pixel browser journey previews both revisions, the named performer and current authority. A critical inspection remains outstanding after the attestation archives. Automated checks refuse expired and wrong-type grants. | Maintenance organisation to review the independent-inspection action, release evidence, handover and installation procedures. |
| 8 | Normal sign-in and preview save no attestation. The form requires explicit consent and rejects an altered intent or an intervening work card change, then accepts a reviewed current version. | Maintenance organisation and trust-service specialist to agree the signature level, provider evidence and validation for each operational action. |
| 9 | On the normal form, aged verification prompts for step-up. Cancelling keeps the archive absent. Password plus authenticator verification allows the same authorised performer to attest. A different account with the work card role cannot submit the intent. | Per-flight technical-log provenance and authorised transcription need their own implementation and workflow test. |
| 11 | The live journey issues a synthetic work card and records completion. The prior work package tests cover superseded data, missing inspection and same-person inspection. The attestation retains revision IDs and inspection status. | Structured step schema and per-step completion and inspection are open. Content and adapter rights belong to the maintenance-data owner. |
| 13 | Retained evidence and its history are written atomically. Duplicate completion keeps one record. A forced exception after the archive insert rolls back both the record and history and retry succeeds. | A signing job that can complete before an external archive, with a durable queue and recovery, is open. |
| 14 | The aircraft export retains the exact archived JSON text, digest, event ID evidence and grant. The existing manifest and history verifier accepts the archive. | Trust-service specialist and receiving organisation to exercise separate trust acquisition, offline identity and history validation, and assess PDF/A and PAdES. |

Cases 12, 15 and 16 depend on the trust model, external provider and independent receiver. The organisation's compliance monitoring and maintenance functions have yet to review the operational policy. This slice does not supply the signed correction or the receiving reconstruction for the integrated aircraft trial.

## Reproduce

Use the disposable PostgreSQL and Playwright setup in the [browser guide](../tests/e2e/README.md). The automated fixtures and browser service enable the flag only for the isolated run. The business date is 18 November 2026. Use normal account verification time and the fixture's generated credentials.

```sh
uv run pytest -q tests/test_work_card_attestation.py tests/test_data_layer.py \
  tests/test_roles.py tests/test_security.py tests/test_e2e_inventory.py \
  tests/test_exports.py tests/test_work_packages.py \
  tests/e2e/test_records.py::test_synthetic_work_card_attestation_at_mobile_width \
  tests/e2e/test_records.py::test_work_package_from_draft_to_release
```

The first run exposed the required `WP-` package reference prefix and the general export test's expectation that every type is always populated. The pilot now uses `WP-SYNTHETIC-`, and a dedicated test verifies export of a populated pilot record while the ordinary sample stays unpopulated.

The populated upgrade rehearsal applied migration `planning.0005_workcardattestation` to a sample seeded with `planning.0004_freeze_issue_check` current. PostgreSQL 16.14 retained all 280 preceding history events and the same aggregate of ordered event hashes. Django reported no pending model migrations.

## Executed results

At code revision `958a947`, the focused run passed all 305 checks in 105.50 seconds, including the normal mobile browser form and existing release flow. Formatting, lint, typing and traceability passed. The full run collected 1,449 checks, with 1,434 passes and 15 failures in live browser scenarios. The pilot browser run reached step-up and then refused the preview token during a run with substantial elapsed-time discontinuities on the host. The same scenario passed in the focused run. Two failing existing persona scenarios passed in isolation. The passkey enrolment scenario failed in isolated runs on both the branch and the clean integration baseline. A separate run excluding the live browser directory reported 1,382 passes and one standalone browser sorting timeout. The affected sort scenario passed when repeated separately.
