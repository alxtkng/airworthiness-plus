# Decisions

The running record for Airworthiness+. Read it before any change, and check every page against it before publishing. Newest decisions go at the top of each list.

## Product

- The repository is public from 18 November 2026, decided by Alex King. Its history was rewritten first to remove the server address and private notes; the original is kept private as `airworthiness-plus-archive`. Pull requests 1, 2, 41, 42 and 43 appear here as closed placeholders so that their numbers still resolve. `main` is protected: changes arrive only by pull request with passing checks.
- Licence, decided by Alex King on 18 November 2026: the application code is AGPL-3.0-only, copyright Airworthiness Limited. Reason: a hosted modified version must publish its source, so the code cannot be taken closed; the copyright holder can still license commercially or relax the licence later. Outside contributions wait for a contributor agreement. The licence for the open data standard is not yet decided; the recommendation on record is CC BY 4.0 for its documentation and Apache-2.0 for its schema and tooling (Issue #25).
- Airworthiness+ is a continuing airworthiness web app for owners, operators, Part-CAO, Part-CAMO and Part-145 organisations and licensed engineers, mainly in the United Kingdom.
- Vision: open source with an open data standard for the sector, in the way 360Giving connected grant data.
- Regulation baseline: UK Regulation (EU) No 1321/2014, Civil Aviation Authority edition of September 2026, and UK Regulation (EU) No 748/2012. The European Union Aviation Safety Agency text is a map only; numbers come from the UK text.
- Forms are Civil Aviation Authority forms: CAA Form 1, CAA Form 15c, CAA Form 3-CAO. Never "EASA Form".
- Aircraft types come from SRG1782 (Version 16, 11 August 2026), copied verbatim and never re-cased.

## Navigation

- The sidebar follows 1321/2014. See Sections in the README.
- Items show only for the approvals that need them: Owner, Part-CAO, Part-CAMO, Part-145. The canvas shows All.
- Documentation is its own section: Manuals and Procedures (the Combined Airworthiness Exposition opens from it), Revisions, Required Reading, Notices. Organisation keeps Approval and Scope, Changes and Oversight. Changes holds changes to the approval; document revisions live in Revisions.
- Maintenance Data is its own module in Documentation, shown to every approval and to owners, because it is its own requirement in every Part: M.A.401 and ML.A.401 (what counts as applicable data), 145.A.45, CAO.A.055 and CAO.A.080, CAMO.A.325. It holds five things:
  - Data Held: each set of data with author, the types or ratings it applies to, revision and when the amendment status was last checked. Applicable data is the Civil Aviation Authority's requirements, airworthiness directives, the type and supplementary type certificate holders' instructions for continued airworthiness, component manufacturers' instructions and the organisation's own modified instructions (M.A.401(b))
  - Amendment status: a subscription to each amendment service, a check that every amendment has arrived, and monitoring of status, with special attention to mandatory instructions and airworthiness limitations (AMC M.A.401(c) 5, AMC1 145.A.45(g))
  - Data Queries: inaccurate, incomplete or ambiguous data is recorded as a safety report and notified to the author, and the record kept until the author clarifies it (145.A.45(c), AMC1 145.A.45(c))
  - Customer Data: held only while the work is in progress or for the contract, with its amendment status shown by written confirmation, the work order or the customer's amendment list (145.A.45(a)(g), CAO.A.055(a), CAO.A.080, CAMO.A.325)
  - Modified maintenance instructions, Part 145 only: demonstrated to compliance monitoring, approved, the author informed, never for Critical Design Configuration Control Limitations (145.A.45(d), AMC1 145.A.45(d))
- Every work card names the maintenance data and its revision, transcribed accurately or precisely referenced (M.A.401(c), 145.A.45(e)). A Part-CAO need not hold all data all the time, but the data for a job must be held before the work starts (AMC1 CAO.A.055), so a work package checks its data is held and current before it is issued
- Data must be close to the aircraft for the people doing the work, with enough terminals (AMC M.A.401(c) 1 and 2, AMC 145.A.45(f))
- Required Reading, not Read and Sign, and the button is Acknowledge, never Sign, so it is not mistaken for a certifying signature. Regulators name the outcome, not the feature: ORO.MLR.100(e) (all personnel made aware of changes relevant to their duties), SRG1773 Revision Acknowledge form, GM1 145.A.200(a)(4) safety communication. Comparable systems (Centrik, Comply365, Q-Pulse, Web Manuals, EFOS by Evoke) keep acknowledgement inside their documents area.
- Every new starter gets the exposition as their first Required Reading item (CAP 2375 model text, MOE 3.6.2).
- Required Reading is assigned by exposition part to the people whose tasks it touches (AMC2 CAO.A.025(a)); a full revision goes to all staff.
- The Exposition record lists every procedure the guide requires (59 for Part-CAO, AMC1 CAO.A.025) with the module that does it, or Not Yet in Airworthiness+. See Procedures.md for every approval.
- Training is its own section: Recurrent Training, Aircraft Maintenance Licence, Competency Assessments.
- The Aircraft Maintenance Licence tabs run in order: Basic Examinations, Experience Logbook (CAP 741), Type Training (Theory and Practical), On the Job Training (first type rating in the first licence category only).
- Training pages show the Part-147 course route only; type evaluation for Group 3 aircraft (66.A.45(d)) is not shown yet.
- Actions, not Findings: the Actions page holds actions from hazards and from findings. Findings live in Compliance Monitoring.
- Work Packages, not Work Orders: a work order is the customer's written request and sits under Contracts. A work package is how the work is planned.
- Internal findings live in Compliance Monitoring; findings raised by the Civil Aviation Authority live in Organisation, Oversight. Both use Level 1 and Level 2.
- Form pages (Report a Safety Issue, Competency Assessment Form) link back to their list in the breadcrumb.
- References: N- notices, E- enquiries, Q- quotes, INV- invoices, SR- safety reports, OR- occurrence reports, WP- work packages, F- findings.
- Commercial covers the customer side and trade: Marketplace (find organisations), Enquiries and Quotes (an accepted quote is the written work order shown under Contracts), Customers (one record per owner or operator), Invoices (raised on release to service). Suppliers stay in Logistics because supplier evaluation is a quality requirement; the Marketplace links to it.
- Frameworks behind Commercial: two-sided platform (liquidity before network effects; supply seeded from the CAA lists), CRM (operational, collaborative, analytical), Kraljic matrix for suppliers, SCOR (Plan, Source, Transform, Deliver, Return, Enable), ATA Spec 2000 (Chapter 9 traceability, Chapter 16 release certificates), org-id.guide identifiers for the open data standard.
- Part 145 ratings are standardised by product: Aircraft Maintenance (A1 to A4, limited to SRG1782 type names, or a standard group description such as Single Piston Engine Aeroplanes, Metal Structure, 5,700 Kilograms or Less), Engine Maintenance (B1 to B3, limited to SRG1782 bracket engine terms such as CFM56, IAE V2500, Lycoming), Component Maintenance (C1 to C22, Appendix II class names) and Non-Destructive Testing (D1, by method: Eddy Current, Liquid Penetrant, Magnetic Particle, Ultrasonic, Radiography, Thermography). The Civil Aviation Authority list does not publish base or line per aircraft rating, so it is marked Not Published until the organisation claims its listing.
- The Marketplace is organised by legal entity, with each approval (such as UK.145.01384) as a child, because one company often holds several approvals at several locations. Entities are grouped by Companies House number (org-id GB-COH), matched on 18 November 2026: 951 of 1,013 approvals carry a number (549 companies, 13 matches of medium or low confidence). Approvals without one (foreign organisations, Crown Dependency companies, colleges, the Ministry of Defence, sole traders) fall back to normalised legal name.
- No locations in the Marketplace. The address on the Civil Aviation Authority list is the principal place of business (CAP1539), not where work is done; real sites are in each exposition and not published. No Location column, address, map or location search. An organisation may add its own sites when it claims its listing.
- Marketplace rows carry only what is needed to choose: organisation with company number, approvals, and for each approval its reference and ratings. No status unless suspended, no facts grid, no repeated reference, no design notes. Opening an approval shows its ratings, one line per class with its limitations, then the actions.
- Marketplace limitations are cleansed: exposition-level detail is removed entirely (capability list and exposition references, task-only scopes such as borescope inspection or blade blending); acronyms spelled out (Auxiliary Power Unit, Non-Destructive Testing); shouting capitals recased except SRG1782 names, which stay verbatim; engine makers follow SRG1782 forms (PW, PWC, GE, RR, CFM, Honeywell for Garrett and AlliedSignal). Organisation names stay exactly as the Civil Aviation Authority lists them (Ltd, Plc and t/a kept).
- Marketplace results are a list, not a table: one line per organisation (name, company number, what it is approved for). Opening it shows every approval at once, one level only: reference and type, then ratings grouped by product, one class per line, one aircraft or engine type per line. No nested disclosure, no truncated detail, no tooltips.
- SRG1769 is the Details of Nominated Personnel form, not a type list.
- Money uses £ with pence, excluding Value Added Tax unless stated.
- Logistics, not Parts, Tools and Equipment. Goods In (receiving inspection, CAP 3037), Stores (stock, quarantine and scrap), Tools and Equipment, Suppliers.
- Management System, not Safety Management, so it fits Part-CAO's quality system as well as safety management.
- No Pilot Phone or Log a Flight screen for now.

## Interface

- Geist, applied by its own rules. Restrained colour. No AI slop.
- No visible page title on section pages; record pages show Heading 24 with the type under it.
- Tables are one line per row and expand on click. See Data Table in Components.
- Aircraft status is Serviceable or Unserviceable.
- Status dots: amber and red only, green only in a Status column.
- Percentages use the % sign.
- Day counts are exact: from 18 November to 6 December is 18 days. Amber for due soon, red only when overdue.
- The interface of private beta, decided 19 November 2026 (REQ-190 to REQ-196). Ours, within the design system:
  - the stylesheet is written by hand from `tokens.json`, one custom property for each token, light and dark. A test fails if a value differs from its token or if a colour is written anywhere else
  - the sidebar for the slice: Continuing Airworthiness (Aircraft); People (Authorisations, which holds airworthiness review staff and their recency); Documentation (Maintenance Data); Organisation (Approval and Scope, Records, Users). Records and Users are not in the README's list of sections: Records holds Import, Records Export and the Problem Log as its tabs, and Users is shown to the Administrator only
  - Aircraft has the tabs Fleet, Transfers, Airworthiness Directives and Airworthiness Review. An aircraft's own page has the tabs Record, Maintenance Programme, Airworthiness Directives, Maintenance Data and Airworthiness Review
  - a status mark is a round dot and a word: green for Serviceable in a Status column, amber for Due Soon, Due, Within Tolerance and To Assess, red for Overdue and Unserviceable. Any other word is written with no dot
  - a table is one line for each row. A button opens a detail row with every column's full value; a column that holds a form, or one marked as secondary, is shown only in the detail. Without the script every table shows everything. The verification report of an import is left as it is, so that values can be ticked down the page
  - a form label has no colon after it. A page carries no script and no style of its own
  - not yet built from Components.md: sorting and filtering of tables, numbers aligned right, the summary strip and icons beside sidebar items
- Backup and restore, decided 19 November 2026 (REQ-150 to REQ-154). Ours, with the numbers for Alex King to confirm:
  - one backup every 24 hours and before every migration, encrypted on the server to a key the server does not hold, checked by a checksum, and copied to storage elsewhere that can be added to and not deleted from
  - the backup is made by a database role that reads every record and writes nothing. The same role runs the check of the records
  - a restore is always into a new, empty database. After it the records are checked against their history, and each organisation states the highest certificate serial it has issued, which the next serial then follows. The stated serial can be raised by the owner of the records, never lowered, and never set by the application
  - recovery point objective 24 hours; recovery time objective the next working day; daily backups kept 35 days and monthly ones 12 months; a restore test every 3 months
- The sample organisation, decided 19 November 2026 (Step 9). `python manage.py seed_sample_organisation` loads the organisation, people, fleet, programmes, directives, maintenance data and review certificates of `SampleData.md`, through the same services as the pages. The tests build their sample from the same code. Only the Administrator is given a password, typed at the prompt; the others get theirs on the Users page. It is for a system that holds no real records, and it refuses to run twice
- When a release went into the records, decided 19 November 2026 (REQ-051), after dogfooding found work from before these records began shown as entered late. The day the release was entered in the aircraft's records can be given when work or compliance is recorded; it is on or after the day of the work and not after today. Left empty, it is today. An import takes the day of the work, because the file reproduces a record that already existed
- Import, decided 18 November 2026 (REQ-170, REQ-171; hazard H-008). Ours:
  - a file is CSV in UTF-8 with fixed column headings. A date is written 2026-11-18 or 18 November 2026 and nothing else, because 03/04/2026 can be read two ways. Hours have at most one decimal place and no comma; cycles are whole numbers. At most 1 megabyte and 2,000 rows
  - a file is loaded whole or not at all, and every row that cannot be loaded is named with its reason. Each row makes its records through the same services as the pages, so the same rules refuse the same things. An import never changes a decision already recorded
  - three kinds of file in the slice: Aircraft and Totals; Airworthiness Directive Status, one row for each directive and aircraft with the decision, its basis and the last compliance; Airworthiness Review Certificates. A repeating action of a directive, and the tasks and work done of a maintenance programme, are entered through the pages
  - every value loaded is kept as it was written in the file. The verification report shows each beside what the source says, with who checked it and when, the proportion checked rounded down to a whole percent, and how many differ. A value is checked by ticking that it agrees or by typing what the source says; nothing is ticked for the person and there is no control that ticks every value. A value can be checked again and every check is kept
  - a value that differs is corrected through the pages, where the correction is in the history; the report goes on showing what was imported
  - Import Records is for the Continuing Airworthiness Manager, because a file of directive status records decisions on applicability. Check Imported Records is open to the Continuing Airworthiness Manager, Airworthiness Review Staff, and Planning and Records. Hours and cycles are checked by a second person, not the one who loaded the file (hazards H-008 and H-011); any other value may be checked by either, and the report shows who loaded and who checked
- Acceptance records, decided 18 November 2026 (REQ-172 to REQ-174, REQ-176). Ours:
  - the problem log is a list of entries. An entry is the problem, who raised it and the day. The action, the solution and any later note are each added to it with the person and the day; nothing is changed or removed, and the application has no permission to do either. An entry is Open, then Action Taken, then Solved once a solution is added; entries not solved come first
  - dates in the problem log are the day the entry or note is added. Nothing is back-dated
  - the Organisation page shows the organisation record, the reference and date of the written approval to keep records in the system, and the day the parallel run began with the day its 6 months pass: the same day of the month 6 months later, or the last day of that month if it is shorter. The Administrator records both
  - a change that extends the system into a new function regulated by the Civil Aviation Authority is recorded as an architecture decision before it is released, so that the organisation can tell the authority (`CONTRIBUTING.md`)
- Records export, decided 18 November 2026 (REQ-134 to REQ-136; hazard H-012; threats TH-080 to TH-082). Ours:
  - an export is a ZIP file of JSON, with CSV copies for reading in a spreadsheet, and a README that describes every file and how to check it. No software of ours is needed to read it
  - what the export says of a record is taken from the history: a record is what the last entry of its history says, and every entry is included with its hash. A test compares this with the database for every type of record
  - an aircraft's export holds the aircraft, its counters and entries, programme, tasks, work done, every directive the organisation records with the decisions and compliance for this aircraft, the maintenance data for its type rating, and its certificates, extensions and reviews. People are given by name only. The organisation's export holds every record and the access log
  - each export is entered in the access log with the SHA-256 of its manifest, and the Records Export page lists them. A file that has been altered, even with every hash recalculated, has a different manifest SHA-256
  - the check is a part of the system that uses only the Python standard library, run as `python manage.py verify_export`, with no database
  - a type of record that is not in the export fails the build
- Airworthiness review certificates, decided 18 November 2026 (REQ-100 to REQ-116; hazards H-007, H-010, H-013). Ours, except where a source is given:
  - a certificate has one date, its date of issue, and the 90 days of ML.A.903(d) are measured from it
  - a certificate issued by the organisation takes its serial from the database, in order from 1, and its reference is the approval reference, then ARC, then the serial in four digits: UK.CAO.[Number]-ARC-0001. A certificate issued elsewhere keeps the reference it carries. A voided certificate stays, and its serial is not used again. What a certificate says is never altered
  - an extension records each of the three conditions of ML.A.901(c) as confirmed; the system refuses a third in a row, one more than 30 days early and one after expiry
  - a certificate is Due Soon at 30 days; the 90-day window is shown in words
  - review staff are recorded by the Administrator. Recency is tested for the day of issue. A lapse is recorded when it is found and stands until a review under supervision is recorded (AMC1 CAO.A.045(d)); nothing entered afterwards stands in for it
  - on the Fleet, an Unserviceable aircraft shows Rectify Defect as its next due; otherwise the airworthiness review is set beside the programme tasks by its days remaining
  - the review is the 16 points of ML.A.903(a)(1) to (11) and (c)(1) to (5), each under a short label of ours with the point number as its reference. Each starts as To Be Verified. A result is Satisfactory, Finding or Not Applicable, and comes with the evidence sampled; Not Applicable is offered only for (a)(9) and (a)(11), which the regulation words as if required
  - a review belongs to the member of review staff who started it. Only that person records its results and issues its certificate; anyone else is refused and the refusal is logged. Holding the role is not enough: the person is on the review staff record
  - the certificate is issued from the review, on the day, and only when nothing is outstanding. The page lists what is outstanding, each with its reference: a point with no result, an open finding (ML.A.903(e)(2)), who assisted at the survey where the person is not qualified under Part-66 (ML.A.903(b)), a programme discrepancy not addressed (ML.A.903(e)(3)), recency (CAO.A.045(c)), and any entry of CAA Form 15c not yet held
  - ML.A.903(h) says the maintenance programme may be reviewed with the airworthiness review. The review therefore states one of: Not Reviewed with This Review, None Found, Found and Addressed, Found, Not Yet Addressed. Only the last stops the certificate
  - the certificate page carries every entry of CAA Form 15c, Issue 2 (Appendix IV to Part-ML), read from the form in the Regulatory Library on 18 November 2026. Labels follow the writing rules, so the form's ARC Reference is Certificate Reference and its Authorisation No is Authorisation Number. The aircraft record gains Aircraft Manufacturer and Manufacturer's Designation, the organisation gains its address, and an extension records the airframe hours on its date, taken from the latest entry. Airframe hours are asked for every aircraft; the form's exception for balloons and airships is not built
  - once the certificate is issued the review and its points are fixed: the database refuses any change, to the owner of the tables as well. A void certificate keeps its review; a new review is started
- Maintenance data, decided 18 November 2026 (REQ-080 to REQ-089; hazard H-005). A set of data is one of the five kinds of ML.A.401(b). It is Held, Not Held or No Longer Held. Held and Current means held, with an amendment check that is not overdue. Data needed but not held is recorded as Not Held so that it shows first, with overdue checks; among those, data carrying mandatory instructions or airworthiness limitations comes first. The date of the next amendment check is entered at each check; the regulation sets no period. A new revision supersedes the current one, and the database refuses to make a superseded revision current again. Data applies to an aircraft when the aircraft's type rating is among those the data names, matched exactly. Ours, except where a source is given.
- Airworthiness directives, decided 18 November 2026 (REQ-060 to REQ-068; hazard H-002). Every directive an organisation records is assessed against every one of its aircraft: until a decision is recorded for an aircraft the directive shows as Applicability to Assess, and no decision is offered in advance. A decision is Applicable or Not Applicable, with its basis, the person and the date, made for one aircraft at a time; the database refuses a statement that would mark more than one aircraft Not Applicable. An action with a limit, done once or repeating, is a task of the aircraft's programme, as ML.A.302(c)(4) requires, calculated by the same rules with no tolerance (ML.A.303). A terminating action ends the repetition and leaves every earlier record. Which directives to record is the organisation's; the system holds no list of directives of its own. Ours, except where a source is given.
- Hours and cycles entries, decided 18 November 2026 (REQ-024, REQ-025; hazard H-011). An entry is a total on a date. It is refused if it is dated after today, below any entry on or before its date, above any entry after it, or more than 24 hours a day above another. More than 10.0 hours or 100 cycles a day needs the person entering it to confirm, and the entry is marked. The days counted between two entries are the days between their dates plus one. Every pair of entries is measured, not only neighbours. A wrong entry is superseded by a correction and stays in the record; an entry is never changed. The current total is the latest entry. These numbers are ours, not the regulation's.
- Tolerance, decided 18 November 2026: a tolerance never moves a due point. Each limit shows its due point and, where a tolerance applies, the last point the tolerance allows. A limit that has been passed while its tolerance has not is Within Tolerance, shown in amber with the words and what remains of the tolerance; it is Overdue, in red, only once the tolerance is passed. The task counts as due from the limit itself, and the task is shown by its worst limit: one limit Overdue makes the task Overdue. A tolerance is accepted only for an inspection of the Minimum Inspection Programme (ML.A.302(d)(1)) and is refused for an airworthiness directive, an airworthiness limitation or a life limit (ML.A.303, GM1 ML.A.302(c)(4)). When the calendar tolerance ends after the airworthiness review certificate, the system says so (AMC1 ML.A.302(d)). The states, words and colours are ours, not the regulation's.
- Whichever comes first, decided 18 November 2026: every limit of a task (hours, cycles, calendar) is always calculated exactly and shown. To say which comes first, limits in hours or cycles are projected to a date using the aircraft's planning utilisation, rounded down to whole days so the projection is never late. Limits that fall on the same day are shown together. With no planning utilisation recorded, no limit is ranked above another and all are shown. The projection is for planning only; the task is due when any limit is reached.
- A calendar interval in months lands on the same day of the month, or on the last day of a shorter month (31 January plus 1 month is 28 or 29 February). Our rule, not the regulation's.
- Due Soon defaults, decided 18 November 2026 and adjustable for each organisation: 30 days, 10.0 hours or 10 cycles remaining, whichever limit governs. An airworthiness review certificate is Due Soon at 30 days; the 90-day early review window is shown in words, not colour. A regulatory deadline of 30 days or fewer (release to service in the records, copy of the review certificate to the Civil Aviation Authority) is Due Soon from the day it starts. These numbers are ours, not the regulation's.
- The Fleet lists aircraft under management. An aircraft being transferred in appears on the Transfers tab until its records are complete.

## Roles and Permissions

Decided 18 November 2026 (REQ-006, REQ-007). Write access by role is a condition of CAP 562 C-90; which role may do what is ours, derived from the people in `SampleData.md`, except where a source is given below. `airworthiness_plus/accounts/roles.py` holds the same matrix, and a test fails the build if the two differ.

- A user may hold more than one role, as Lucy Grant is both Airworthiness Review Staff and in continuing airworthiness. An action is permitted if any role held permits it.
- A user with no role, and an inactive user, may do nothing.
- The Administrator manages users and the organisation record and does not change airworthiness records. An Administrator can give themselves another role; the change is in the history.
- Read Only can view and nothing else.
- Only Airworthiness Review Staff carry out a review and issue a certificate (ML.A.903, CAO.A.045). Issue also needs a current authorisation, which is REQ-109 and separate from the role.
- An extension is open to the Continuing Airworthiness Manager and to Airworthiness Review Staff, because the regulation gives the privilege to the organisation under both continuing airworthiness management and airworthiness review (CAO.A.095(b)(4), (c)(1)(ii)). Who within the organisation signs an extension is for its exposition; this reading is to be confirmed by Alex King.
- Only the Continuing Airworthiness Manager changes the maintenance programme and decides whether a directive applies (hazard H-002). The programme review may also be recorded by Airworthiness Review Staff, who may carry it out with the airworthiness review (ML.A.302(c)(9)).
- Second factor at sign-in, decided 18 November 2026: codes from an authenticator application, the time-based one-time password of RFC 6238. It needs no new dependency. A code can be phished where a passkey cannot, so passkeys are considered again when the verification level is set in Step 7 (REQ-008).
- Sign-in, decided 18 November 2026 (REQ-008, REQ-009; threats TH-001, TH-002). These numbers are ours, to be set against the verification level in Step 7:
  - a password of at least 12 characters, then a code; the code must follow the password within 5 minutes; a code is accepted for its own 30 seconds, changed on 19 November 2026 from the 30 seconds either side as well to meet OWASP ASVS 5.0 6.5.5, and only once
  - the first time, the user adds the account to an authenticator application from a key shown once, and confirms a code
  - 5 failed attempts for a user name within 15 minutes, counted since the last sign-in, lock that name until 15 minutes after the fifth; wrong codes count as wrong passwords do
  - a session ends when the browser closes, 30 minutes after its last request, 12 hours after sign-in whatever happens, when the user signs out, when the user is made inactive, and when the password changes
  - the page gives the same answer for an unknown name, a wrong password, an inactive user and a locked name; the reason is in the access log
- Users, decided 18 November 2026 (REQ-005 to REQ-010). Ours:
  - the Administrator adds a user with a full name, a user name that is an email address and roles. The first password reaches the person by a route other than the system, and is changed by them before any other page answers
  - a first password is made by the system, changed on 19 November 2026 from one chosen by the Administrator to meet OWASP ASVS 5.0 6.4.1. It is random, of 16 characters, passes the password rules, is shown once to the Administrator on the page that follows, and is stored only as a hash. It works up to the seventh day after the day it is given, by the date in the United Kingdom, and not after; the Administrator then gives another
  - a user name is used once across every organisation. A name that is taken, here or elsewhere, gets the same answer
  - a user may hold no role, and can then do nothing. An organisation always has an active Administrator: the last one cannot lose the role or be made inactive, and nobody makes themselves inactive
  - a user who leaves is made inactive, never deleted. Their sessions end at once
  - a lost password is replaced by the Administrator with a new first password; a lost authenticator is reset by the Administrator, and the user sets a second factor up again at the next sign-in. Both are entered in the access log with who did it. A user changes their own password by giving the current one; their other sessions end
  - a change to how someone signs in needs a fresh sign-in, decided 19 November 2026 to meet OWASP ASVS 5.0 7.5.1 (threat TH-002). Within 5 minutes of signing in nothing more is asked. After that, a user changing their own password gives a code as well as the current password, and an Administrator giving a new first password or resetting a second factor gives a code from their own authenticator application. The code is used up as one at sign-in is, and a wrong one counts towards the lock. Changing roles, making a user inactive and ending sessions do not ask for a code: none of them lets anyone sign in as someone else
- Security settings, decided 19 November 2026 against OWASP ASVS 5.0 Level 2 (`assurance/asvs.md`). Ours:
  - every response carries a Content Security Policy that allows the application's own stylesheet, script, fonts and images and nothing else, with no inline script or style; no response is kept by the browser except the static files; the application answers GET, HEAD and POST only
  - the session and forgery cookies are named with the `__Host-` prefix, so a browser accepts them only over HTTPS and for this host alone. Strict Transport Security covers subdomains of the service's own host name; it says nothing about the domain above it
  - a password is refused if it contains the name of the product, the regulator, the approval or the user's organisation, as well as what Django already refuses. Any character is allowed, and at least 64 characters
  - a user can end every other session of theirs, and the Administrator can end every session of a user. Both are entered in the access log. The number of sessions a user may have at once is not limited. Resetting a second factor ends the user's sessions
  - there is no rule on which characters a password is made of, so a password of digits alone is accepted if it is long enough and not a common one
  - the address logged for a request is the one the reverse proxy saw, and only when the service is told it runs behind one
  - unexpected errors go to standard error, one line each with the time in Coordinated Universal Time. No request body, password or session identifier is logged
  - every entry of the history names how its hash was made, decided 19 November 2026 to meet OWASP ASVS 5.0 11.2.2. The name today is `sha256-fields-1`: SHA-256 over the fields of the entry in the order the export's README gives. If the way of hashing is ever changed, new entries carry a new name and the entries written before are still checked by the old one. The check in the system and the check that comes with an export both report an entry whose name they do not know
- Certificates from before these records, decided 19 November 2026 (REQ-110, REQ-113; dogfooding D-3). Ours:
  - a certificate the organisation's own review staff issued before these records is recorded against that person, with the reference it was issued with and no serial of the system. It is entered on the aircraft's Airworthiness Review page or loaded by an import, by whoever may add or change aircraft
  - it is dated no later than the person's last review before these records, which the Administrator states on the review staff record. Recording one therefore cannot change whether the person has recent experience, and cannot stand in for a review carried out in these records. The database holds to the same rule
  - the Administrator cannot move that date to before a certificate of the person already recorded
  - no copy to the Civil Aviation Authority is tracked for it: that copy was owed under the records it came from
  - the copy of an extension is tracked whoever issued the certificate, because the extension is the organisation's own (ML.A.903(f)). Before 19 November 2026 it was tracked only for certificates issued in the system; dogfooding D-6
- Access log, decided 18 November 2026 (REQ-009): every sign-in, failed sign-in, sign-out, second factor set-up and refused action, with the user name, the time from the database clock and the network address. It is added to and never changed. An organisation sees its own entries. A change of role is in the history of the user record instead.

| Action | Administrator | Continuing Airworthiness Manager | Airworthiness Review Staff | Planning and Records | Read Only |
|---|---|---|---|---|---|
| View Records | Yes | Yes | Yes | Yes | Yes |
| Export Records | Yes | Yes | Yes | Yes | No |
| Manage Users and Roles | Yes | No | No | No | No |
| Change Organisation Record | Yes | No | No | No | No |
| Add or Change Aircraft | No | Yes | No | Yes | No |
| Enter Utilisation | No | Yes | No | Yes | No |
| Change Maintenance Programme | No | Yes | No | No | No |
| Record Maintenance Programme Review | No | Yes | Yes | No | No |
| Record Accomplishment | No | Yes | No | Yes | No |
| Record Airworthiness Directive | No | Yes | No | Yes | No |
| Decide Directive Applicability | No | Yes | No | No | No |
| Record Directive Compliance | No | Yes | No | Yes | No |
| Record Maintenance Data | No | Yes | No | Yes | No |
| Record Amendment Check | No | Yes | No | Yes | No |
| Carry Out Airworthiness Review | No | No | Yes | No | No |
| Issue Airworthiness Review Certificate | No | No | Yes | No | No |
| Extend Airworthiness Review Certificate | No | Yes | Yes | No | No |
| Record Copy Sent to the Civil Aviation Authority | No | Yes | Yes | Yes | No |
| Add to Problem Log | Yes | Yes | Yes | Yes | No |
| Import Records | No | Yes | No | No | No |
| Check Imported Records | No | Yes | Yes | Yes | No |

## Writing

- Terse Title Case labels, no full stops, no middle dots.
- Never abbreviate: Kilograms, Maximum Take-Off Mass, Type Certificate Holder, Civil Aviation Authority in running text. Identifiers stay as they are: Part-CAO, CAA Form 1, UK.CAO.[Number], Mode S.
- The column is always Aircraft Registration. Show the Type Rating, never the model.
- No marketese, no taglines, no description paragraph under a title.

## Regulation Facts in Use

Confirmed against the UK text in the Civil Aviation Authority Regulatory Library (regulatorylibrary.caa.co.uk/1321-2014) on 18 November 2026: ML.A.302, ML.A.303, ML.A.305, ML.A.901, ML.A.903, AMC1 ML.A.302, AMC1 ML.A.302(c), AMC1 ML.A.302(d), GM1 ML.A.302, GM1 ML.A.302(c)(3), GM1 ML.A.302(c)(4), CAO.A.045, AMC1 CAO.A.045, CAO.A.055, AMC1 CAO.A.055, CAO.A.080, AMC1 CAO.A.080, CAO.A.090, CAO.A.095, AMC1 CAO.A.100(f), ML.A.401, AMC M.A.401(c), AMC1 145.A.45(g) and Appendices I and II to Part-ML. That reading corrected three sources below: the conditions for contracted software are in AMC1 CAO.A.100(f) point (d)(2), and a search of the library finds no AMC to CAO.A.090; the Minimum Inspection Programme intervals and tolerance are in the rule itself, ML.A.302(d)(1), and the annual review of the programme is ML.A.302(c)(9). Other rows are as recorded during discovery and are confirmed as each is used (Issue #38).

| Fact | Value | Source |
|---|---|---|
| Certificate of release to service in records | Not later than 30 days after the day the maintenance task is completed | ML.A.305(a), M.A.305 |
| Pilot-owner tells contracted organisation | Within 30 days of the task | Appendix I to Part-ML |
| Airworthiness review certificate validity | 1 year; extendable at most two consecutive times by 1 year each, by a CAMO or CAO that has managed the aircraft for the previous 12 months | ML.A.901(a), ML.A.901(c) |
| Early extension | Up to 30 days before expiry, keeps the review pattern | ML.A.901(d) |
| Early airworthiness review | Up to 90 days before expiry, keeps the review pattern | ML.A.903(d) |
| Copy of review certificate to the Civil Aviation Authority | Within 10 days of the date of issue or extension | ML.A.903(f) |
| Airworthiness review staff recency | 6 months of continuing airworthiness management in every 2-year period, or 1 review in the last 12-month period | CAO.A.045(c), AMC1 CAO.A.045(c). CAMO.A.305, for Part-CAMO, is To Be Checked |
| Certifying staff authorisation | Licence valid, 6 months (or 100 days) of experience in 2 years, recurrent training in 2 years | CAO.A.040, 66.A.20(b), 145.A.35 |
| Minimum Inspection Programme | Aeroplanes, touring motor gliders and balloons: annual or 100 hours, whichever first, tolerance 1 month or 10 hours. Sailplanes and powered sailplanes other than touring motor gliders: annual, tolerance 1 month. Next interval from when the inspection is done | ML.A.302(d)(1)(a), (b); AMC1 ML.A.302(d) |
| Tolerance and the review certificate | Using the 1-month tolerance for the annual inspection may result in an expired airworthiness review certificate | AMC1 ML.A.302(d) |
| Tolerance is a one-time extension | The tolerance is a permitted variation for a one-time extension of the interval; scheduled maintenance does not otherwise deviate from the programme | GM1 ML.A.302(c)(3), GM1 ML.A.302 |
| No Minimum Inspection Programme for airships and rotorcraft | Programme based on the design approval holder's instructions | ML.A.302(d) |
| Airworthiness directive | Carried out within the requirements of the directive unless the Civil Aviation Authority specifies otherwise | ML.A.303 |
| Mandatory continuing airworthiness information | Intervals cannot be extended by a CAMO or CAO; escalation is approved by the Civil Aviation Authority | GM1 ML.A.302(c)(4) |
| Maintenance programme review | At least annually | ML.A.302(c)(9) |
| Occurrence report | Within 72 hours, then a follow-up | ML.A.202, M.A.202 |
| Part-CAO own-procedure changes | Notified within 15 days | CAO.A.105 |
| Level 2 finding | Corrective action within 3 months, extendable with a plan | CAO.B.050, CAMO.B.350 |
| Authority oversight cycle | 24 months, up to 36 or 48 with good record | CAMO.B.305, 145.B.305 |
| Internal audit | Every item every 12 months, up to 100% extension | CAO.A.100, CAMO.A.200 |
| Contract ended for non-compliance | Owner tells the authority within 2 weeks | Appendix I to Part-ML |
| Maintenance records retention | 36 months after release; totals and directive status 12 months after withdrawal | ML.A.305(h) |
| Human factors training | Within 6 months of joining, then every 2 years | 145.A.30(e) |
| Fuel tank safety training | Phase 1 within 6 months, Phase 2 within 12 months, then every 2 years | AMC 145.A.30(e) |
| Airworthiness review staff records | Kept 2 years after the person leaves | CAO.A.045(e) |
| Lapsed airworthiness review staff | Restored by 1 review under supervision | AMC1 CAO.A.045(d) |
| Component classes | Serviceable with release document, unserviceable, unsalvageable, standard part, material | M.A.501, ML.A.501, 145.A.42 |
| Unsalvageable items | Secure area, mutilated, or kept for training or research, with a named person responsible | ML.A.504, AMC1 CAO.A.030(n) |
| Finding levels | Level 1 lowers safety or seriously endangers flight safety, immediate action; Level 2 may lower safety | CAMO.B.350, CAO.B.050 |
| Internal audit independence | Auditors independent of the area audited; plan includes unannounced and product audits | AMC CAO.A.100 |
| Basic examinations | Part-147 organisation or the Civil Aviation Authority; pass 75%; valid 10 years; retake after 90 days (30 with retraining); 3 attempts in 12 months | 66.A.25, Appendix II to Part-66 |
| Type training | Theory and practical completed within 3 years before application; pass 75% | Appendix III to Part-66 |
| On the job training | First type rating in first category; within 3 years; 50% of tasks after theory; mentor 1 year in category; assessor 3 years and not the mentor | 66.A.45(c), Appendix III Section 6 |
| Manhour plan | Reviewed at least every 3 months; shortfall over 25% in a month reported; at least half of each shift employed | AMC 145.A.30(d); Part-CAO needs enough staff, CAO.A.035(d) |
| Defect deferral | Pilot-in-command, minimum equipment list, or certifying staff; limit from the maintenance data | ML.A.403 |
| Contracted software for records | Not subcontracting, but described in the exposition and approved by the Civil Aviation Authority, provided that each organisation has access to its own data only, data is entered only by the organisation's personnel, and the data can be retrieved at any time | AMC1 CAO.A.100(f) point (d)(2). The Part-CAMO equivalent, recorded during discovery as AMC CAMO.A.220, is To Be Checked |
| Part-CAO privileges | Maintenance; continuing airworthiness management; airworthiness review, with maintenance or continuing airworthiness management; permit to fly, with airworthiness review. One or more | CAO.A.095(a) to (e) |
| Part-CAO records | Maintenance records and associated maintenance data 3 years from release; continuing airworthiness records, review certificates and permits to fly 2 years from permanent withdrawal; protected from damage, alteration and theft; backup hardware in a different location; transferred with the aircraft or when the organisation closes | CAO.A.090(a) to (g) |

## National Regime

Source: CAP 562 Issue 4 Amendment 3 (January 2020), read in full. Its wording predates the UK leaving the European Union Aviation Safety Agency: "EASA aircraft" reads as Part 21 aircraft and "non-EASA" or "Annex II" as Non-Part 21 aircraft. That mapping is ours, not the text's. Leaflets B-40 and 70-80 now sit in separate Supplementary Amendments and are not covered here.

- Every aircraft record carries a regime: Part 21 or Non-Part 21. The regime decides the release wording, licence checks, schedule type and which approvals can sign
- Non-Part 21 aircraft hold a National Certificate of Airworthiness or a Permit to Fly; a Permit to Fly does not expire but needs a 12-month Certificate of Validity
- An orphan United Kingdom type loses Certificate of Airworthiness eligibility and moves to a Permit to Fly
- Marketplace shows each British Civil Airworthiness Requirements approval by the chapter the Civil Aviation Authority lists (A8-1, A8-9, A8-15, A8-21, A8-23, A8-24, A8-25, A8-26, A8-6), never as a bare "BCAR"
- Chapter names come from the CAP 553 (BCAR Section A, Issue 8 Amendment 1) contents, shortened by dropping "Approval of Organisations Responsible for" and the Group codes, with "Non-EASA" written as Non-Part 21 as the Civil Aviation Authority now does:
  - A8-1 Primary Companies (Group A1)
  - A8-6 Test Houses (Group B4)
  - A8-9 Flight Under B Conditions (Groups F1, F3, F4)
  - A8-15 Aeroplanes and Rotorcraft Not Exceeding 2,730 Kilograms, Maintenance (Group M3)
  - A8-21 Design or Production (Groups DOA and POA)
  - A8-23 Maintenance of Non-Part 21 Aircraft (M1)
  - A8-24 Maintenance of Non-Part 21 Aircraft Below 5,700 Kilograms or Single Engined Helicopters (M2; full title adds "not used for Commercial Air Transport or State purposes")
  - A8-25 Continuing Airworthiness Management Organisation
  - A8-25 Supplement 2 Initial Permit to Fly Reports, Military Design and Service
  - A8-26 Supporting Recreational Aviation
  - Type Responsibility Agreement for the listings the Civil Aviation Authority marks (TRA)

| Fact | Value | Source |
|---|---|---|
| National approvals | A8-1 and A8-2 production; A8-8 Group E3 design; A8-9 flight test; A8-10 welders; A8-15 maintenance; A8-18 airships; A8-20 ex-military over 2,730 Kilograms (E4 design, M5 maintenance); A8-21 design and production; A8-25 continuing airworthiness management | CAP 562 Chapters B and C, 51-90 |
| Cancelled chapters | A8-1, -2, -4 to -7, -9, -16 and -19 cancelled 28 September 2005, except for organisations designing or building Non-Part 21 aircraft | CAP 562 C-20 |
| National-only certificates | Certificate of Maintenance Review, Certificate of Release to Service for national work, Certificate of Fitness for Flight, Flight Release Certificate, Star Inspection | CAP 562 C-20 2.6.1, H-10 |
| Duplicate inspection | Two signatures before release whenever controls or vital points are disturbed | BCAR A6-2; CAP 562 20-80 |
| Section L licences | Categories A, B, C, D, X, R; issued only for Non-Part 21 aircraft since November 2006; not usable above 5,700 Kilograms | CAP 562 H-10, H-20, H-30 |
| Certifying recency | 6 months' relevant work in the preceding 24 months | CAP 562 H-20 |
| Schedule over 2,730 Kilograms | Non-commercial aircraft need an approved maintenance schedule (since 1 April 1995) | CAP 562 5-40 |
| Weight and Centre of Gravity Schedule | Required above 2,730 Kilograms; a Load and Distribution Schedule at or below | CAP 562 8-10 |
| Re-weighing over 5,700 Kilograms | First within 2 years of manufacture, then at least every 5 years | CAP 562 8-10 |
| Permitted variations | Not applied to retirement lives or mandatory items; one approved schedule at a time | CAP 562 5-30, 5-40 |
| Lifed components | Record hours, flights, landings and pressurised flights (2 pounds per square inch or more) | CAP 562 51-80 |
| Records retention, Non-Part 21 | Until 2 years after the aircraft is destroyed or permanently withdrawn | CAP 562 5-70 |
| Computerised records | Amendment history that cannot be deleted, write access by role, up to 100% check of directive and review data on migration, controlled certificate serials, 6-month parallel run, written approval to keep records outside logbooks | CAP 562 C-90 |
| Parts release, Non-Part 21 | Civil Aviation Authority Approved Certificate | CAP 562 Chapter B |
