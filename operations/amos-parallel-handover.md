# Synthetic parallel handover and fallback

The source organisation's established aircraft record governs the trial. Its records lead supplies the aircraft export and reads the pending work in the Maintenance Forecast. The receiver's planner compares the handover material and owns discrepancy logging. The source records lead owns the response to each discrepancy. The accountable manager of each organisation owns the decision to start or resume an operational trial under its applicable approved procedures.

## Entry and training

| Readiness item | Evidence and owner |
| --- | --- |
| Scope | One synthetic aircraft G-EJKL, with the source record and receiver exercise segregated by organisation. The trial lead records registrations, account roles and release revision. |
| Training | Sender exports the selected aircraft and locates its deferred defect limit. Receiver checks the archive, records a discrepancy and practises escalation. Both roles locate the authoritative record after fallback. The trial lead records completion by role. |
| Reconciliation | Receiver checks aircraft identity, open defect and due limit, recurring inspection and next due, and correction history. Record time, rekeyed entries, records that differ and evidence that cannot be verified. Open a Problem Log entry for each difference. |
| Decision | Continue the rehearsal only when the source remains available and the roles can explain how they will stop. Before any operational change, the responsible managers review training, reconciliation, recovery and the applicable approval route. |

## Stop, fallback and resume

1. Stop the transfer if aircraft identity differs, a required record or dependency is missing, a due or restriction value differs, signing evidence cannot be verified at the required level, or the established record becomes inaccessible.
2. Record the discrepancy, date, responsible role and escalation action in the Problem Log. Refer the difference to the source records lead. Keep the problem open until independently reconciled.
3. Return to the established source record. In the local rehearsal, reopen the sender's forecast, export the aircraft again and compare the structured records with the initial export. For a service failure, use the separate recovery procedure and reconcile subsequent entries before the service is reopened. [Backup and restore](backup-and-restore.md)
4. After reconciliation, the managers decide whether to resume. Log decision, reasons, open items, ownership and next review. For operational use, identify who handles user questions and technical incidents, the stabilisation review interval, and the criteria for ending enhanced support.

## Executable exercise

Run `AIRWORTHINESS_E2E=1 uv run pytest tests/e2e/test_parallel_handover.py` using disposable PostgreSQL and the live browser setup. The test introduces an unresolved date discrepancy as a synthetic comparison value. The receiver records and escalates it. The sender returns to the forecast and compares an aircraft archive with the opening record set. This tests procedural fallback to an always-available source. Service restoration, signed transfer and operational cutover have separate evidence requirements. [Live test setup](../tests/e2e/README.md)

For a real parallel run, the approval holders confirm the controlling exposition or procedure and any competent-authority involvement before commencing. The trial lead records the names of the participants, evidence of training and the decisions and correspondence that apply to the proposed change. [Assurance readiness review](../assurance/readiness-review.md)

## Synthetic cutover and stabilisation

Run `bash operations/rehearse-amos-cutover.sh PRIOR_WORKTREE PYTHON PG_BINDIR` from the candidate. Use the Python interpreter from the locked environment and the PostgreSQL 16 or later binaries. The run creates a private cluster and populates the prior schema. It compares the history hash aggregate and inventory of aircraft, open defects, pending work orders and problem entries after migration and native restore. It checks records in both schemas and measures restore time. Retain this log alongside the separate browser training checkpoint, two-organisation stop-and-fallback result and three-record reconciliation. The previous schema and its restored database remain the reference for the synthetic fallback.

The trial lead records a decision for the rehearsal after comparing the two states. Stop and retain both copies on a discrepancy. Before a hosted rehearsal, Airworthiness Limited supplies an authorised isolated environment, sample data, backup storage and a trial recovery owner. Verify an off-host backup, restore to a new database, the service switch, time and recovery point, and reconciliation of any changes recorded since the restored snapshot. During stabilisation the records lead reviews unresolved reconciliation and support entries at the intervals agreed by the operator. The responsible accountable managers record their operational go/no-go and the next review. Where the change requires authority acceptance or approval, retain the reference and scope in a separate entry.
