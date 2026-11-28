# AMOS case 4 Stores lookup exercise

The baseline is `d1da03fe508109a5f123c20ee3e86cee7c559725`. A user with record-view access and a current maintenance approval can open **Practise Stock Lookup** from **Stores → Stock**. Use the sample Read Only user for the exercise. The checkpoint lasts for the signed-in session. Exercise answers never enter the organisation's Stores records.

| Step | Expected result |
| --- | --- |
| Check the opening holdings | ZRH Main has 7, ZRH Line has 1, BSL has 1, LUG has 1 and GVA has 0. |
| Answer 7 for ZRH Main and return to Stock | Reopening the exercise resumes the ZRH station question. |
| Answer 8 for ZRH and 10 for the network | Network on-hand quantity stays 10. ZRH Main holds 6, of which 1 is reserved. ZRH Quarantine holds 1 with zero available and an unresolved identity check as the reason. |
| Answer 8 for network availability | The exercise completes. Total custody remains 10 with 1 reserved and 8 available. |
| Submit an incorrect quantity or repeat an earlier answer | The incorrect answer leaves the question in place with a reason. Repeating an earlier answer leaves the saved checkpoint in place. |

The fixture, movements described by the scenario, questions and expected answers are Airworthiness+ training design decisions. They use synthetic trim cables. The exercise demonstrates the distinction between custody, allocation and availability. The operational posting contract still requires Goods In owner confirmation of the producer revision, evidence and identity mappings, units and location rules. Confirm appointments and package eligibility with the applicable maintenance organisation and the Planning owner before exercising operational reservation, issue, returns, alternates or quarantine. Verify the operational ledger, reconciliations, tenant isolation, retries and concurrent issues with a populated upgrade, disposable PostgreSQL and live routes after those controls exist.

## Automated evidence

- `test_stores_exercise_checks_answers_and_rejects_stale_submissions` checks incorrect and duplicate answers, separate session progress and absence of Stores entries.
- `test_stores_lookup_exercise_resumes_at_saved_question` starts in Stores with the sample Read Only user and checks the balances and saved checkpoint at 320 px using Playwright keyboard activation.
- The exercise adds one form to the fields-by-action and browser coverage inventories. It uses the existing Django session storage.
- Local verification on disposable PostgreSQL 16.14 and Chromium 158.0.8127.37 passed all 245 selected checks with no skips. The selection was `tests/test_stores_exercise.py`, `tests/e2e/test_stores_exercise.py`, `tests/test_receiving.py`, `tests/e2e/test_receiving.py`, `tests/test_roles.py` and `tests/test_e2e_inventory.py`. The first live test used an exact accessible row name and failed because the responsive table adds a Details control. The corrected locator passed at the same viewport.
- Ruff lint and formatting, mypy and traceability passed. The initial broader run on the pre-inventory working tree was stopped after 62 passes. That run provides no full-suite result for this revision.
