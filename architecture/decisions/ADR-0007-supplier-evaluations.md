# ADR 0007. Supplier identities and evaluation history

27 November 2026

REQ-340 to REQ-343 build on the Phase 4 decision to share a register within an organisation. One supplier identity can have several dated evaluations against the organisation's maintenance approvals. PostgreSQL scopes both the supplier and the linked approval to the organisation, and application roles append evaluations. The same actor and audit rules apply as for the other organisation records.

The register shows the latest evaluation by evaluation date, then by entry time, for each currently held maintenance approval. The evaluation retains the approval reference as recorded. If an approval is re-recorded under a different reference, the new reference needs its own evaluation. Historic evaluations stay on the supplier record and in the organisation export. The recorded next date reflects the organisation's procedure. The calendar due status is independent of the evaluation decision. Goods In will record the outcome of checking the individual item and its documents.
