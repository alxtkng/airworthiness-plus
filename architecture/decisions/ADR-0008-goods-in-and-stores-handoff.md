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

## Stores PR 1: once-only posting and the location ledger

28 November 2026. Alex King approved the receipt-to-stock contract, its legacy mapping
rules and the REQ-357 clarification (`assurance/phase-4-stores-handoff.md`). REQ-358.

- The `StockEntry` above stays the link to an acceptance. It credits nothing. An
  accepted line with an entry shows **Awaiting Stock Posting**, every blocking reason
  and zero available quantity until it is posted.
- Stores records a dated `StockResolution` from the original evidence: unit (Each or
  Litre), part number, serial, batch or lot and standard or specification as the class
  requires, the location and the shelf-life basis and boundary. A correction appends a
  later resolution. The receipt, the disposition and the entry are never changed. The
  free-text destination stays as Goods In recorded it.
- `StockPosting` is unique on the disposition. Its insert trigger takes the
  disposition's transaction lock, copies the received quantity and the latest
  resolution, checks the location's kind, class and state, the identity for the class,
  the shelf-life basis against the receipt and that a serial has no other custody, and
  refuses an acceptance whose structured evidence is blank. A second trigger writes the
  opening intake movement in the same statement, so a failure leaves neither.
- A quarantine decision posts to a secure quarantine location as blocked custody with
  zero availability. A supplier return is never posted.
- Balances are derived from `StockMovement`. Every movement takes the lot's
  transaction lock and the database refuses an overspend, a wrong unit scale, a split
  serial, an incompatible or withdrawn destination and a move of an open hold to
  serviceable Stores. A `StockCount` reads the ledger quantity in the database and
  changes nothing. An adjustment applies one current count's variance once, by the
  Adjust Stock From a Count action.
- All five tables are under ADR-0002: forced row-level security, same-organisation
  parent checks, database-written hashed history and no update or delete, except that a
  location can be withdrawn. They are in the organisation export.
- Legacy acceptances use the same resolution and posting path. Reconciliation posts
  each resolved, unblocked disposition and is safe to repeat.

Not in PR 1: Goods In capturing unit and structured identity at receipt and choosing
the location register entry at disposition (the producer side of the contract),
reservations, work-package issue and final disposal. Organisation procedures, appointments and the manufacturer's shelf-life
convention stay **To Be Checked**. The warning lead time uses the organisation's Due
Soon days.

## Work-package custody and station balances

The AMOS pilot extends PR #167 with Logistics `0009_station` and `0010_maintenance_custody`. Existing ledger rows, identifiers and event hashes carry forward. Station and location codes are separate. Earlier locations stay unassigned. The Stock board shows exact identity and condition by station, location and unit, including configured zero-quantity locations when an identity is selected.

New custody actions use a dated appointment, the signed-in person and the current maintenance approval. Reservation and issue require unfinished work on an issued card and an open written order. Issue rechecks shelf life, eligibility, physical custody and the active reservation. A return restores physical custody in secure quarantine. A later new receiving decision governs any subsequent admission to serviceable stock. PostgreSQL serialises the new custody actions with published movements using the existing lot lock. An identical replay returns its original result.

An alternate approval requires a current certifying grant naming the actual aircraft. It binds the required and substitute identities, lot, issued card revision and applicable parts-data reference. Reservation and issue check that the linked approval, grant, work and revision still apply. The operator confirms its appointment, approval and actual source procedures before operational use. [Stores acceptance and scope](../../assurance/amos-evidence-matrix.md)

## Stores appointments for the ledger, 28 November 2026

The dated Stores appointments that #170 introduced for reservation, issue, return
and quarantine now also cover resolving and posting, moving, counting and adjusting
(migration 0011). The app role permits each action. The appointment authorises it:
the signed-in person must hold a current appointment for that duty on the record's
date, under a maintenance approval held that day, with no withdrawal in force. The
service refuses otherwise and hides the control. PostgreSQL checks the same rule on
every resolution, posting, count, transfer and adjustment it is asked to insert, so a
direct request cannot bypass it. The intake written by a posting is covered by the
posting's check. Records made before the rule keep their history unchanged, and no
appointment is inferred for them. The free-text destination recorded at disposition
is labelled as such, so it is not read as a register location.
