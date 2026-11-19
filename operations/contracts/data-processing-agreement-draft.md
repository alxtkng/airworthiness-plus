# Data Processing Agreement: Draft

**Draft for a solicitor. Not legal advice. Not to be signed as it stands.** References to the UK General Data Protection Regulation are from memory and To Be Checked.

Between [Organisation Name], [Approval Reference] (the Controller) and Airworthiness Limited, [Company Number], [Registered Address] (the Processor).

## 1. What This Covers

The Processor provides Airworthiness+, in which the Controller keeps continuing airworthiness records. Those records contain personal data. This agreement sets the terms on which the Processor handles that data for the Controller, as Article 28 of the UK General Data Protection Regulation requires of a controller and its processor.

| | |
|---|---|
| Subject Matter | Hosting and operating the Controller's records in Airworthiness+ |
| Duration | The term of the service agreement, and afterwards until the data is returned and removed under clause 11 |
| Nature and Purpose | Storing, displaying, calculating from, backing up and exporting the Controller's records |
| Kinds of Personal Data | Names, user names (email addresses), roles, authorisation references and experience of review staff, names of aircraft owners and others named in records, network addresses and sign-in events |
| People Concerned | The Controller's staff and contractors who use or are named in the system; aircraft owners; others the Controller names in its records |

No special category data is asked for and the Controller agrees not to enter any.

## 2. Instructions

The Processor handles the data only on the Controller's written instructions, of which this agreement and the Controller's use of the service are the first. The Processor tells the Controller if it thinks an instruction breaks the law.

The Processor's staff do not enter, change or remove the Controller's records. Records are entered only by the Controller's own people (AMC1 CAO.A.100(f) point (d)(2)). The service has no administration route into an organisation's records.

## 3. Confidentiality

Everyone the Processor allows to reach the systems is bound to confidentiality.

## 4. Security

The Processor keeps the measures in the Schedule. They are assessed against OWASP ASVS 5.0 Level 2 and tested by an independent party before the Controller's data is held. The Processor may improve them and will not weaken them without telling the Controller.

## 5. Others Who Process the Data

The Processor uses the sub-processors in the Schedule and no others. It tells the Controller at least [30] days before adding or replacing one, and the Controller may object. Each is held to terms no weaker than these.

## 6. Where the Data Is

The data is kept in [Country]. It is not moved outside the United Kingdom without the Controller's agreement and the safeguards the law requires.

## 7. People's Rights

The Processor helps the Controller answer a request from a person about their data. In practice: the Controller can see and export everything itself at any time. A correction is made by a new entry that supersedes the old one, because records are never altered in place. Where the Controller must keep a record by law, a name in it is not removed.

## 8. Breaches

The Processor tells the Controller without undue delay, and within [24] hours of becoming aware, of any breach of the Controller's personal data: what happened, what data, what has been done. The Controller decides whether to notify the Information Commissioner's Office and the people concerned, and the Processor helps.

## 9. Help With the Controller's Duties

The Processor gives the Controller what it reasonably needs to show it meets its duties on security, breach notification and impact assessments.

## 10. Audit

The Processor makes available what is needed to show it keeps to this agreement: the published assurance documents, the results of penetration tests in summary, and answers to reasonable questions. An audit on site is by agreement, at the Controller's cost, no more than once a year unless there has been a breach.

## 11. At the End

When the service ends the Controller receives its complete records as set out in `data-export-on-exit.md`. The Processor then removes the Controller's data from the live service within [30] days and from backups as they expire, within [13] months, unless the law requires the Processor to keep it.

## 12. Liability and Law

[For the solicitor.] The law of England and Wales.

## Schedule

### Security Measures, as Built

- Each organisation's records separated in the database, not only in the application.
- Each user has their own account, with a password and a second factor; access by role.
- A history of every change that cannot be altered, with a chained hash.
- Encryption in transit. Backups encrypted before leaving the server, with the key held elsewhere.
- Daily backup, with a tested restore.
- No data sent to any third party by the application.
- Logging of sign-ins, refused actions and exports.

### Sub-Processors

| Sub-Processor | What It Does | Where |
|---|---|---|
| [Hosting Provider] | The server | [Country] |
| [Backup Storage Provider] | Encrypted backups, which it cannot read | [Country] |
