# Data Export on Exit: Draft

**Draft for a solicitor. Not legal advice.** It describes what the product does today, which is what the contract term should promise.

## The Promise

An organisation can leave at any time and take everything with it, in a form it can read without us.

## What the Organisation Receives

The export of the organisation (REQ-135), which it can make itself from the Records Export page at any time, before or after giving notice:

- every record of every type, as it stands;
- the whole history of every record: every change, who made it and when, with the value before and after, including superseded entries;
- the access log;
- a README inside the file that describes every part of it and how to check it.

It is a ZIP file of JSON, with CSV copies for a spreadsheet. No software of ours is needed to read it. It holds no password and no second-factor key.

An export of one aircraft's complete record (REQ-134) is made the same way, for an aircraft that moves to another organisation or owner (CAO.A.090(f), transfer of records).

## How the Organisation Knows It Is Complete and Unaltered

- A type of record that is not in the export cannot be added to the product: the build fails (REQ-136).
- Each export is logged with the SHA-256 of its manifest, shown on the Records Export page.
- `python -m django verify_export <file>` checks a file against itself with no database: every file's checksum, the hash of every history entry, the chain, and each record against its history. The method is described in the export, so that anyone can write the same check.

## What Is Not in the Export

- Files attached to records. The product does not store any yet.
- Other organisations' records.
- The service's own server and proxy logs.

## After the Organisation Has Left

1. The organisation confirms in writing that it has its export and has checked it.
2. Its users are made inactive.
3. Its data is removed from the live service within [30] days of that confirmation, and from backups as they expire, within [13] months.

**This step cannot be done by the product today.** Nothing is ever deleted through the application, by design, and the owner of the tables is refused as well. Removing an organisation's records at the end of a contract needs a procedure of its own, run on the server by the owner of the database with the protections lifted for that organisation alone, recorded, and witnessed by the organisation. It is not written or built. It must be before the first customer's data is held, and it needs Alex King's decision on the periods, because the organisation remains responsible for keeping its records for the periods the regulation sets (ML.A.305, CAO.A.090) and will rely on its export to do so.

## If the Company Stops Trading

The organisation's protection is the same export, which it should make on a schedule of its own and keep. [For the solicitor: whether more is offered, such as source code already being public under its licence, which it is.]
