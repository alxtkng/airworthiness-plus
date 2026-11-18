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
- Due Soon defaults, decided 18 November 2026 and adjustable for each organisation: 30 days, 10.0 hours or 10 cycles remaining, whichever limit governs. An airworthiness review certificate is Due Soon at 30 days; the 90-day early review window is shown in words, not colour. A regulatory deadline of 30 days or fewer (release to service in the records, copy of the review certificate to the Civil Aviation Authority) is Due Soon from the day it starts. These numbers are ours, not the regulation's.
- The Fleet lists aircraft under management. An aircraft being transferred in appears on the Transfers tab until its records are complete.

## Writing

- Terse Title Case labels, no full stops, no middle dots.
- Never abbreviate: Kilograms, Maximum Take-Off Mass, Type Certificate Holder, Civil Aviation Authority in running text. Identifiers stay as they are: Part-CAO, CAA Form 1, UK.CAO.[Number], Mode S.
- The column is always Aircraft Registration. Show the Type Rating, never the model.
- No marketese, no taglines, no description paragraph under a title.

## Regulation Facts in Use

| Fact | Value | Source |
|---|---|---|
| Certificate of release to service in records | Within 30 days of completion | ML.A.305, M.A.305 |
| Pilot-owner tells contracted organisation | Within 30 days of the task | Appendix I to Part-ML |
| Airworthiness review certificate validity | 1 year, extendable twice by 1 year in a controlled environment | ML.A.901 |
| Early airworthiness review | Up to 90 days before expiry, keeps the expiry pattern | ML.A.901 |
| Copy of review certificate to the authority | Within 10 days | ML.A.904, Appendix I |
| Airworthiness review staff recency | 6 months of continuing airworthiness work in 2 years, or 1 review in 12 months | CAO.A.045, CAMO.A.305 |
| Certifying staff authorisation | Licence valid, 6 months (or 100 days) of experience in 2 years, recurrent training in 2 years | CAO.A.040, 66.A.20(b), 145.A.35 |
| Minimum Inspection Programme | Annual or 100 hours, whichever first; tolerance 1 month or 10 hours, next interval from when done | AMC ML.A.302 |
| Maintenance programme review | At least annually | ML.A.302 |
| Occurrence report | Within 72 hours, then a follow-up | ML.A.202, M.A.202 |
| Part-CAO own-procedure changes | Notified within 15 days | CAO.A.105 |
| Level 2 finding | Corrective action within 3 months, extendable with a plan | CAO.B.050, CAMO.B.350 |
| Authority oversight cycle | 24 months, up to 36 or 48 with good record | CAMO.B.305, 145.B.305 |
| Internal audit | Every item every 12 months, up to 100% extension | CAO.A.100, CAMO.A.200 |
| Contract ended for non-compliance | Owner tells the authority within 2 weeks | Appendix I to Part-ML |
| Maintenance records retention | 36 months after release; totals and directive status 12 months after withdrawal | ML.A.305 |
| Human factors training | Within 6 months of joining, then every 2 years | 145.A.30(e) |
| Fuel tank safety training | Phase 1 within 6 months, Phase 2 within 12 months, then every 2 years | AMC 145.A.30(e) |
| Airworthiness review staff records | Kept 2 years after the person leaves | CAO.A.045(e) |
| Lapsed airworthiness review staff | Restored by 1 review under supervision | AMC CAO.A.045 |
| Component classes | Serviceable with release document, unserviceable, unsalvageable, standard part, material | M.A.501, ML.A.501, 145.A.42 |
| Unsalvageable items | Secure area, mutilated, or kept for training or research, with a named person responsible | ML.A.504, AMC1 CAO.A.030(n) |
| Finding levels | Level 1 lowers safety or seriously endangers flight safety, immediate action; Level 2 may lower safety | CAMO.B.350, CAO.B.050 |
| Internal audit independence | Auditors independent of the area audited; plan includes unannounced and product audits | AMC CAO.A.100 |
| Basic examinations | Part-147 organisation or the Civil Aviation Authority; pass 75%; valid 10 years; retake after 90 days (30 with retraining); 3 attempts in 12 months | 66.A.25, Appendix II to Part-66 |
| Type training | Theory and practical completed within 3 years before application; pass 75% | Appendix III to Part-66 |
| On the job training | First type rating in first category; within 3 years; 50% of tasks after theory; mentor 1 year in category; assessor 3 years and not the mentor | 66.A.45(c), Appendix III Section 6 |
| Manhour plan | Reviewed at least every 3 months; shortfall over 25% in a month reported; at least half of each shift employed | AMC 145.A.30(d); Part-CAO needs enough staff, CAO.A.035(d) |
| Defect deferral | Pilot-in-command, minimum equipment list, or certifying staff; limit from the maintenance data | ML.A.403 |
| Contracted software for records | Each organisation sees only its own data; only its own staff enter data | AMC CAO.A.090, AMC CAMO.A.220 |

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
