# Record of Processing and Data Classification

Step 8 of private beta. Date: 19 November 2026. OWASP ASVS 5.0, 14.1.1, 14.1.2.

## Status of This Document

A working draft by the build session, **not legal advice**. Every statement of what the UK General Data Protection Regulation or the Data Protection Act 2018 requires is from memory and is **To Be Checked** against the legislation and the Information Commissioner's Office guidance, by someone qualified, before public beta. The legislation could not be read in the build session.

Details of the company that are not in the repository are placeholders in square brackets.

## Who Is Who

| | Private Beta | Public Beta and After |
|---|---|---|
| The records of an organisation | There is none but the sample, which holds no real person | The organisation is the controller. Airworthiness Limited is its processor and acts on its instructions (`../contracts/data-processing-agreement-draft.md`) |
| Accounts of the company's own people | Airworthiness Limited is the controller | The same |

- Controller for the company's own processing: Airworthiness Limited, [Registered Address], [Company Number].
- Contact for data protection: [Name], contact@airworthiness.co.
- Registration with the Information Commissioner's Office: [To Be Confirmed by Alex King].

## What Is Processed

| Data | About Whom | Why | Where From | Protection Level |
|---|---|---|---|---|
| Full name, user name (an email address), roles, whether active | Each user | To give each person their own account and to show who made each entry, which the regulation requires of records (CAP 562 C-90, To Be Checked) | The organisation's Administrator | Personal |
| Password hash; second-factor key | Each user | Sign-in | The user | Secret. Never shown, never exported, never in the history |
| Access log: user name, time, network address, what happened | Each user; anyone who tries a user name | To detect misuse and to investigate | The service | Personal |
| History: the name of whoever made each change | Each user | So that every entry shows who made it and nothing is silently altered (CAO.A.090, CAP 562 C-90) | The service | Personal, inside records the regulation requires to be kept |
| Review staff: authorisation reference, date accepted, months of experience, last review, date left | Airworthiness review staff | CAO.A.045: the organisation must show its review staff are authorised and recent | The organisation | Personal |
| Aircraft records: owner, and names written in free text such as who assisted at a survey or who provided data | Owners, who may be private people; others named | The continuing airworthiness record of the aircraft (ML.A.305, CAO.A.090) | The organisation | Personal where the owner is a person |
| Airworthiness records themselves: hours, tasks, directives, certificates | The aircraft | The purpose of the system | The organisation | Safety records. Not personal, but their integrity matters more than their secrecy |
| Sessions | Each signed-in user | To keep a user signed in | The service | Secret while live |

No special category data is asked for. Nothing is used for marketing, profiling or automated decisions about people. No data is sent to any third party by the application.

## Protection Required for Each Level

| Level | Encrypted in Transit | Encrypted at Rest | Integrity | Who May Read | In Logs | In Exports |
|---|---|---|---|---|---|---|
| Secret | Yes | Password: hashed. Second-factor key: not encrypted in private beta, by a decision of 19 November 2026 (`../keys-and-secrets.md`) | By the database | No one; the service checks against it | Never | Never |
| Personal | Yes | In the database, on the server's disk; in backups, encrypted | History and hash chain | The organisation's own users, by role | Names and addresses in the access log only | Yes, to the organisation itself |
| Safety records | Yes | As Personal | History and hash chain; fixed once certified | The organisation's own users | No | Yes |

## Lawful Basis, To Be Checked

For an organisation's records, the basis is the organisation's to determine as controller. The likely one is that keeping these records, and showing who made each entry, is required of it by law: Regulation (EU) No 1321/2014 as retained, Part-CAO and Part-ML. For the company's own accounts: its legitimate interest in running and securing the service.

## Kept For How Long

| Data | Period | Source |
|---|---|---|
| Airworthiness records and their history | The periods of REQ-133: at least 36 months after release for maintenance records; until 12 months after an aircraft is permanently withdrawn for its totals and directive status; Part-CAO records 3 years, and continuing airworthiness records 2 years after withdrawal | ML.A.305; CAO.A.090(b), (c) |
| Review staff records | 2 years after the person leaves | CAO.A.045(e) |
| User accounts | A user who leaves is made inactive, not removed, because their name is on entries that must be kept | REQ-010 |
| Access log | **Not decided** | None |
| Server and proxy logs | 90 days, proposed | None |
| Backups | 35 days daily, 12 months monthly, proposed | None |

## Open Questions for Alex King and a Qualified Adviser

1. **Nothing is ever deleted, by design.** The regulation requires that for airworthiness records for stated periods. It does not obviously require it for the access log, which holds network addresses, or for records after their period has run. How long each is kept, and how anything is removed when its time comes given that the application cannot delete, need an answer before public beta.
2. **A person's rights** to see, correct or erase their data. Access can be met from an export. Correction is by a superseding entry. Erasure of a name from records that must be kept is likely refused on the ground that the law requires the record; this needs confirming.
3. **Where the data is.** The country of the server and of the backup storage, and whether either is outside the United Kingdom, are not recorded in the repository.
4. **Sub-processors.** The hosting provider and the backup storage provider, once chosen.
5. **Registration** with the Information Commissioner's Office, and whether a data protection impact assessment is needed.
6. **Failed sign-ins with an unknown user name** are logged with the name that was typed, which could be anything, including someone's password typed in the wrong box. Whether to keep the typed name is a question.
