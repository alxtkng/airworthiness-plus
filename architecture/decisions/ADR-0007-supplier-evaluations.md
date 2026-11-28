# ADR 0007. Supplier identities and evaluation history

27 November 2026

REQ-340 to REQ-343 build on the Phase 4 decision to share a register within an organisation. One supplier identity can have several dated evaluations against the organisation's maintenance approvals. PostgreSQL scopes both the supplier and the linked approval to the organisation, and application roles append evaluations. The same actor and audit rules apply as for the other organisation records.

The register shows the latest evaluation by evaluation date, then by entry time, for each currently held maintenance approval. The evaluation retains the approval reference as recorded. If an approval is re-recorded under a different reference, the new reference needs its own evaluation. Historic evaluations stay on the supplier record and in the organisation export. The recorded next date reflects the organisation's procedure. The calendar due status is independent of the evaluation decision. Goods In will record the outcome of checking the individual item and its documents.

## Maintenance subcontractor assessments

28 November 2026

REQ-348 and REQ-349 add evidence of maintenance subcontractor controls under the organisation's own approval. The scope is the specialised services described in CAO.A.095(a)(2) for Part-CAO and the subcontractor controls described in AMC1 145.A.75(b) for Part-145.

Each assessment uses the existing supplier identity and records the approval reference in force on the assessment date. The organisation can record controls or suspend the scope while retaining earlier entries. Only the Continuing Airworthiness Manager records assessments. The records are append-only and appear in organisation exports. Recording an assessment leaves the supplier evaluation, work package and release records independent.
