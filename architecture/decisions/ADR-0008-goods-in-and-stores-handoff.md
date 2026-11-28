# ADR 0008. Goods In and the first Stores entry

28 November 2026

REQ-353 to REQ-357 add receiving inspection and the first Stores entry under
[CAO.A.050(c)](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/05830_CAOA050_Components_equipment_and_tools.htm)
and
[145.A.42](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/02%20145/2%20Regs/01648%20145.A.42%20Components.htm).
The organisation's receiving procedure applies the classification and segregation
rules relevant to its approval. It references retrievable evidence and records
which release, conformity statement or permitted exception the inspector relied on.
The inspector assesses the documents and the installation decision follows under the
applicable maintenance data.

Each receipt represents one delivery line with a common identity and disposition.
The receipt, observations and final disposition are append-only. A returned or
quarantined line retains the same traceable identity, evidence and movement record.
The receipt records supplier or owner source and intended aircraft or work package
as references from the delivery. Stock reservation and issue to a work package are
later Stores actions.

A PostgreSQL trigger records the initial stock entry in the same transaction as the
acceptance. It can insert only from the accepted disposition, and each disposition
can have only one stock entry. The application role can read these entries. The
stock page follows the immutable link back to the disposition and receipt for
identity, quantity, release evidence and location. The organisation export carries
the same linked records and history. The database records its automatic stock action
under the database role. The linked disposition keeps the application actor.

The migration gives existing accepted draft receipts a linked Stores entry using
the original decision. Missing structured evidence stays blank and the original
inspection record remains available. New acceptance requires an evidence reference
and the class-specific evidence fields.

## Stores posting, 28 November 2026

Alex King, Goods In owner, approved the receipt-to-stock contract recorded in
`assurance/phase-4-stores-handoff.md` on 28 November 2026, with its legacy
mappings and the REQ-357 clarification. REQ-358 implements it in Stores PR 1.

The stock entry stays the permanent link to the acceptance. It no longer stands
for a quantity in stock. Stores posts the disposition once, keyed by its
identifier, from the persisted decision and a dated posting-evidence record. The
evidence resolves the unit and exact quantity, the separate part, serial, batch
and specification, the shelf-life basis and a location from the Stores location
register. A legacy acceptance and a new one take the same path. Until the
evidence is complete the entry shows Awaiting Stock Posting, every blocking
reason and zero available. A quarantine is posted as blocked custody in a
secure quarantine location, with zero available. A supplier return is never
posted.

The posting row and its opening movement are written by one statement: an
after-insert trigger writes the movement, so neither can exist without the
other. A unique link on the disposition and an advisory lock on its identifier
let one caller post. A replay that would use the same evidence returns the
original posting. One that would use later evidence is a conflict and the
original stands. Balances are derived from append-only movements. Each
movement takes a per-lot lock in the database, and the database refuses a
quantity that does not fit its unit, a move beyond the source balance, an
incompatible or withdrawn destination and an adjustment the ledger no longer
matches. A count records the ledger quantity the database read and changes
nothing. A separately appointed person applies its variance.

Each Stores action needs a current dated appointment for the signed-in
person's own record, under a maintenance approval held that day, as well as the
app role. The Administrator transcribes appointments and does not act in
Stores. The database checks the appointment again on every insert.

Goods In does not yet capture the unit, the separate identifiers or a register
location at receipt and disposition. Until it does, new acceptances are
resolved through the same Stores posting evidence. Reservations, issue to a work
package and final disposal are later pull requests. The organisation's
procedures, appointments, warning lead time and manufacturer cut-offs are To Be
Checked.

## Local AMOS custody extension (REQ-359)

The live trial keeps the original acceptance link and uses the immutable disposition UUID to post an evidenced ledger credit once. Legacy acceptance may remain visible with unverified identity, physical location, unit or shelf-life basis and zero available stock. Stores records dated assessments separately. Location and station codes are independent. Quantities are grouped by station, store and unit for an exact part-number or specification lookup. Configured stores remain visible with zero quantity when appropriate. [Producer review and evidence](../../assurance/phase-4-stores-handoff.md)

A separate custody action reserves or issues a lot against unfinished work on an issued package with an open written order. The issue retains the applicable parts-data reference and identity. It rechecks shelf life, physical and allocatable custody and the current Stores appointment. A release of reservation restores availability, and physical return or quarantine creates segregated custody under a retained action and reason. The application and PostgreSQL serialise competing action on the same lot. A retry uses the earlier result for identical request details. This local design preserves the original receiver and acceptance records. Confirm procedure, technical eligibility evidence and roles with the approval holder before applying it to operational records.

An alternate needs separate evidence from the signed-in certifying person with a current grant naming the actual aircraft. The record pins the issued card revision, package, lot, required identity, substitute identity and applicable parts-data reference. At reservation and issue, the service and PostgreSQL recheck the evidence, current card and grant. The Stores appointment governs physical custody. The separate approval documents technical eligibility under the applicable procedure. The operator verifies the grant syntax, applicability and approved parts data before deployment.
