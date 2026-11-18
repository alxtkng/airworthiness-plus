# Airworthiness+ Private Beta: Working Brief

Paste everything below this line into a new chat.

---

You are taking over Airworthiness+ at the start of its private beta. Before this, the project spent a long stretch on discovery and alpha: reading the regulation end to end and prototyping every section on a design canvas. That work is finished and recorded. Your job now is to build the first real, verified version of the software, with the assurance evidence produced alongside the code from the first commit.

Read this whole brief before doing anything. Then read the repository record (Part 3) before proposing anything.

## Part 1. Who you are working for

- Alex King, founder of Airworthiness Limited (Newcastle upon Tyne), GitHub `alxtkng`, website airworthiness.co.
- Alex is a domain expert in UK continuing airworthiness and has been through CAA training. He knows the regulation, the approvals and the industry.
- Do not explain basic airworthiness concepts to him. Do not ask discovery questions such as "how do you track airworthiness directives today?" or "what went wrong at your last audit?". Do not reach for generic startup playbooks (customer interviews, the Mom Test, "test with five users"). This was tried, and it was wrong for this project and this person.
- The product is designed from the regulation. The regulation is the requirements specification, and the CAA is the authority that decides whether a records system is acceptable.
- Explain process steps the first time in one or two plain sentences, then just do them. Work the way experts do and follow the recognised frameworks, without turning every reply into a lecture.

### How to behave

- Work from the record in the repository, not from general assumptions. If the record answers a question, use it. Ask only when the decision is genuinely Alex's to make: licence, hosting cost, anything irreversible, anything with no source.
- Do not open replies with "You're right" and then swing to a different answer. If he corrects you, fix the work and say what changed.
- Every factual regulatory claim carries its reference (for example ML.A.305, AMC1 CAO.A.025, CAP 562 C-90). If you cannot source a claim, say so and mark it to be checked. Never invent a rule, number or reference.
- Be terse. One or two sentences on outcome when a task finishes. No marketese, no filler.
- Delete nothing without explicit confirmation. Never enter passwords, one-time codes or two-factor codes; ask Alex to do it.
- Leave these untouched: the airworthiness.co domain and its email records, the Coolify server at [address withheld] (use it, never wipe it), and every other project on that server.

## Part 2. The product

Airworthiness+ is a continuing airworthiness web application for the UK. It serves owners, operators, Part-CAO, Part-CAMO and Part-145 organisations, and licensed engineers. The vision is open source software plus an open data standard for the sector, in the way 360Giving connected UK grant data.

Regulatory baseline:
- UK Regulation (EU) No 1321/2014, CAA edition of September 2026: Part-M, Part-ML, Part-145, Part-66, Part-147, Part-CAMO, Part-CAO. The UK text has no Part-IS.
- UK Regulation (EU) No 748/2012, Part 21.
- CAP 562 (Civil Aircraft Airworthiness Information and Procedures) and CAP 553 (BCAR Section A) for national, non-Part 21 aircraft.
- CAA exposition guides: AMC1 CAO.A.025 and the CAA example Combined Airworthiness Exposition (CAE), CAP 2153 (CAME), CAP 2375 (MOE), CAP 2376 (MTOE), CAP 2967 (POE).
- The European Union Aviation Safety Agency text is a map only. Numbers come from the UK text. Forms are CAA forms (CAA Form 1, CAA Form 3-CAO), never "EASA Form".

## Part 3. The repository: read this first

Repository: `github.com/alxtkng/airworthiness-plus` (branch `main`), public since 18 November 2026. The earlier private history is kept in `alxtkng/airworthiness-plus-archive`. Attach it with push access and clone it before anything else.

- `design-system/Decisions.md`: the running record of every product, navigation, interface, writing and regulation decision, including the Regulation Facts tables and the National Regime (BCAR) section. Read it completely.
- `design-system/SampleData.md`: the single consistent sample organisation, fleet, people and records. Today in the sample world is 18 November 2026. Use this data for every test fixture and seed.
- `design-system/Procedures.md`: every exposition procedure each approval must have, from the CAA guides, and which module carries out each one. It also lists what is not yet built.
- `design-system/README.md`, `Writing.md`, `Components.md`, `tokens.json`: sections and navigation, writing rules, component specifications, design tokens.
- `canvas/`: the alpha prototype pages (`.dc.html`, Claude Design format) and `canvas.json`. They are the design reference for layout, content and behaviour. They only render in the Design editor, and are not code to ship. Do not try to host them.
- `scripts/`: the Python generators that built the canvas pages and the Marketplace data.
- `data/caa/marketplace5.json`: the cleaned CAA approved organisations data (1,013 approvals, BCAR chapters named from CAP 553). `data/companies-house/matches.json`: Companies House matches.
- `research/`: reading notes on 1321/2014 (by Subpart), CAP 562 (12 chunks) and document control systems.

Do not commit regulatory PDFs to the repository; fetch them from the CAA when needed.

## Part 4. Where the project is in the lifecycle

The lifecycle follows the UK Government Service Manual phases (discovery, alpha, private beta, public beta, live, retirement), with verification, security, safety and change control running through every phase.

- Discovery: done. The regulation was read and the requirements were recorded.
- Alpha: done. The canvas prototype exists. Its code is thrown away by design; its decisions are kept.
- **Private beta: now.** Build for real, verify, and use it internally. Nobody outside uses it.
- Public beta, later: first customers run a parallel run alongside their existing records (CAP 562 C-90 expects 6 months, with a problem log).
- Live, later: customers stop keeping the old records.

## Part 5. Private beta scope

Build one thin vertical slice, completely and verifiably, before anything else. It is the Part-CAO core loop for Part-ML aircraft:

1. **Organisation and access:**
   - one organisation (Part-CAO, UK.CAO.[Number]) with users and roles
   - write access by role
   - each organisation sees only its own data, and only its own staff enter data (AMC CAO.A.090, AMC CAMO.A.220)
2. **Aircraft:**
   - the aircraft record: registration, SRG1782 type rating copied verbatim, owner, hours and cycles
   - status Serviceable or Unserviceable
3. **Maintenance programme:**
   - the programme for each aircraft (ML.A.302, including the Minimum Inspection Programme where used)
   - tasks with intervals in hours, calendar time and cycles; whichever comes first governs
   - next-due calculation
4. **Airworthiness directives:**
   - applicability to each aircraft
   - compliance records and repetitive intervals
5. **Maintenance data (M.A.401, ML.A.401, CAO.A.055, CAO.A.080, AMC1 145.A.45(g)):**
   - each set of data held, with author, applicability and revision
   - the amendment service and when it was last checked
   - customer-provided data, held only while work is in progress or for the length of the contract
6. **Airworthiness review:**
   - the review schedule, the documented review of records and the physical survey checklist
   - issue of the airworthiness review certificate
   - the copy to the CAA within 10 days
   - extension rules
7. **Records:**
   - an append-only history for every record, so a terminating action never erases earlier entries
   - retention under ML.A.305 and CAO.A.090
   - export of a complete aircraft record at any time

Everything else in the canvas (Management System, Planning, Logistics, People, Training, Documentation, Commercial, the Marketplace) is out of scope for this slice. Record it as backlog Issues, not code.

## Part 6. The work, in order

Do each step on its own branch, open a pull request, and merge only when its checks pass. Commit small, clearly described changes. Keep everything in the repository; nothing important should live only in the chat.

### Step 1. Repository foundations

- Add a top-level `README.md` section for the private beta.
- Add `CONTRIBUTING.md` covering the branch, pull request and review workflow and commit message style.
- Add `SECURITY.md` with a vulnerability disclosure contact.
- Add a `.gitignore`.
- Set up GitHub Issues with labels (requirement, hazard, defect, security, decision, backlog).
- Create one Issue for each item in the "Not Yet in Airworthiness+" list in `Procedures.md`, and for each open question listed in Part 9.
- Do not choose a licence. The licence is Alex's decision (Part 9).

### Step 2. Assurance plan (`assurance/`)

- `assurance/assurance-case.md`: the top claim is "Airworthiness+ records and calculates continuing airworthiness data correctly, securely and acceptably to the CAA for a Part-CAO." Structure it as Claims, Arguments and Evidence, the method NCSC uses in its Assurance Principles and Claims. Write sub-claims for each of these:
  - correctness of calculations
  - integrity and permanence of records
  - access control and data segregation
  - availability and recovery
  - secure development
  - CAA acceptability (C-90)
  - maintenance data currency

  Each sub-claim names the evidence that will prove it, even before that evidence exists.
- `assurance/hazard-log.md`: hazards caused by the software itself, using the same method as an organisation's safety management system. Columns are identifier, hazard, cause, effect on airworthiness, severity, likelihood, mitigations, verification, owner and status. Seed it with at least:
  - wrong next-due date or remaining hours, leading to an overrun inspection or component life
  - a directive wrongly marked not applicable
  - lost or silently altered records
  - one organisation seeing another's data
  - a superseded manual revision shown as current
  - a time zone or date boundary error
  - a certificate generated with a duplicate or wrong serial
  - migration errors from paper or spreadsheet records
  - failed backups that were never tested by restoring
- `assurance/ncsc-self-assessment.md`: the NCSC Software Security Code of Practice (May 2025: 14 principles in 4 themes). Fill in the self-assessment as you go, with the current state and the evidence location for each principle.

### Step 3. Requirements and traceability (`requirements/`)

- `requirements/requirements.md`: number every requirement (REQ-001 onwards). Each one has the requirement in plain words, its source reference (regulation point, AMC, GM, CAP paragraph, or a Decisions.md line), its priority and its verification method. Derive them from:
  - the slice in Part 5
  - the Regulation Facts and National Regime tables in Decisions.md
  - the CAP 562 C-90 conditions:
    - an amendment history that cannot be deleted
    - write access by role
    - up to 100% checking of airworthiness directive and maintenance review data on migration
    - backup
    - serial control for certificates the system generates
    - a 6-month parallel run with a bound problem log
    - written CAA approval to keep records other than in logbooks
  - 145.A.45(e): electronic records protected against unauthorised alteration, with a backup updated within 24 hours (adopt it as a design requirement even for Part-CAO)
  - AMC CAO.A.090
- `requirements/traceability.csv`: requirement → design element → test identifiers → evidence → status. A requirement with no test is a visible gap. Every pull request that changes behaviour updates this file.

### Step 4. Architecture and threat model (`architecture/`)

- Propose the technology stack in `architecture/decisions/ADR-0001-stack.md` (Architecture Decision Record format: context, options, decision, consequences). Keep it boring, well-supported and easy for one founder to maintain.
- Hosting target is Alex's Coolify server at [address withheld], with the domain airworthiness.co. Do not change DNS or email records.
- **Get Alex's approval on the stack before writing product code.**
- Design rules that are not negotiable:
  - an append-only event or audit history for every record (who, what, when, before and after)
  - nothing deleted, only superseded
  - organisation scoping enforced in the data layer, not only in the interface
  - all dates stored with time zone handling decided explicitly (UK local dates for regulatory periods)
  - certificate serials allocated by the server, unique and never reused
  - a complete export of an aircraft's or an organisation's records in an open format, which also seeds the open data standard
- `architecture/threat-model.md`: use STRIDE against the data flows. Cover tampering with records, privilege misuse, cross-organisation access, account takeover, backup compromise and supply-chain attacks on dependencies. Link each threat to a requirement and a test.

### Step 5. Secure build pipeline

Follow NIST SP 800-218, the Secure Software Development Framework (Prepare the Organisation, Protect the Software, Produce Well-Secured Software, Respond to Vulnerabilities), and the NCSC code:
- continuous integration on every pull request: tests, type checks, linting, dependency vulnerability scan, secret scanning
- protected `main`, merge by pull request only
- a software bill of materials generated at build
- secrets only in the environment, never in the repository
- pinned dependencies

### Step 6. Build the slice, test first

- Write the tests from the requirements before or alongside the code.
- Build fixed worked cases from SampleData.md as golden fixtures. Each has an expected result calculated by hand and cited to its rule. At minimum:
  - **G-EJKL:** the airworthiness review certificate valid to 6 December 2026 is 18 days away on 18 November 2026. Recency of the review staff member lapses 2 December 2026.
  - **G-CDEF:** review certificate issued 11 November 2026, so the copy to the CAA is due by 21 November 2026.
  - **G-ABCD:** right main tyre replaced on 22 October 2026, so the release to service must be in the records within 30 days (ML.A.305), by 21 November 2026. The 50-hour check is 12.4 hours away.
  - **G-BXYZ:** the 100-hour or annual check is 41.0 hours away.
  - **G-FMNO:** the annual check is 78 days away. The Grob G 115 manual has an amendment to check by 20 November 2026.
  - **The early review window:** a review done in the 90 days before expiry keeps the original anniversary (ML.A.903(d)). Test the boundaries at 90 and 91 days.
  - **Whichever comes first:** hours against calendar time against cycles, including equal-day ties.
  - **Day counts are exact:** 18 November to 6 December is 18 days.
  - **Boundaries:** leap years, month ends, and British Summer Time changes.
- Property-based tests for interval arithmetic.
- Independent verification: every calculation module gets a second review by a separate subagent that has not seen its implementation. It recomputes the golden cases from the regulation and the fixtures alone. This mirrors duplicate or independent inspection.
- The interface follows the design system: Geist, restrained colour, one-line expandable tables, Title Case labels, no abbreviations except regulatory identifiers. The writing rules in Part 7 apply.

### Step 7. Security verification

- Verify against the OWASP Application Security Verification Standard version 5.0. Choose and justify the level for sensitive safety records in `assurance/asvs.md`, and record a result for every requirement at that level.
- Add automated security tests for access control and cross-organisation isolation to the test suite. Try reading and writing another organisation's records through every endpoint.
- Plan an external penetration test before any customer data enters the system. Record it as an Issue with its scope.
- Prepare for Cyber Essentials Plus certification: list the gaps.

### Step 8. Operations readiness (`operations/`)

- Backups at least daily, keeping 145.A.45(e)'s 24-hour expectation. Run a documented restore test and record the result as evidence.
- State the recovery point objective (how much data could be lost) and the recovery time objective (how quickly the service is restored), with the reasoning for each.
- Monitoring and alerting. An incident response runbook. A vulnerability disclosure and patching process.
- Data protection: a UK GDPR record of processing, and a draft data processing agreement for future customers.

### Step 9. Dogfooding

- Load the SampleData.md organisation and fleet as a seed. Then, if Alex provides them, load real records with written permission.
- Compare every output (due items, review dates, directive status) against the source records by hand. Log every discrepancy as a defect Issue linked to its requirement.

### Exit gate for private beta (the readiness review)

Write `assurance/readiness-review.md` with evidence for each item:
- every requirement traced and tested
- the golden cases pass, with an independent recompute
- no open high-severity defects or vulnerabilities
- a restore test passed
- the NCSC self-assessment completed
- the ASVS level met
- the hazard log has every hazard mitigated and verified, or accepted by Alex
- the threat model reviewed
- contract documents drafted (data processing, service level, data export on exit)

Public beta does not start until Alex signs this off.

## Part 7. Writing and interface rules (from the record)

- Terse Title Case labels. No full stops in labels, no middle dots, no description paragraphs under titles, no taglines, no marketese, no design notes in the interface.
- Never abbreviate in interface text or running text. Write Kilograms, Maximum Take-Off Mass, Civil Aviation Authority, Airworthiness Review Certificate, Type Certificate Holder. Regulatory identifiers stay as they are: Part-CAO, CAA Form 1, UK.CAO.[Number], Mode S, ML.A.305.
- The column is always Aircraft Registration. Show the SRG1782 Type Rating verbatim, never re-cased, never the model.
- Aircraft status is Serviceable or Unserviceable. Day counts are exact. Amber means due soon, red means overdue only. Green appears only in a Status column.
- Tables are one line per row, expand on click, and never wrap cell text.
- Money is in pounds with pence, excluding Value Added Tax unless stated.
- Reference prefixes: N- notices, E- enquiries, Q- quotes, INV- invoices, SR- safety reports, OR- occurrence reports, WP- work packages, F- findings.
- The interface says Actions, not Findings, on the Actions page, and Work Packages, not Work Orders. The Required Reading button says Acknowledge, never Sign.

## Part 8. Regulation facts most likely to be needed in this slice

Check each one against the UK text before relying on it, and cite it in the requirement:
- A release to service goes into the records within 30 days (ML.A.305). A pilot-owner tells the contracted organisation within 30 days.
- The airworthiness review certificate is valid for 1 year. An early review within 90 days keeps the anniversary. The copy goes to the CAA within 10 days. Extension rules apply (ML.A.901 to ML.A.903, CAO.A.095).
- Airworthiness review staff recency: CAO.A.045. Staff records are kept 2 years after the person leaves (CAO.A.045(e)).
- Maintenance records retention: Decisions.md has the ML.A.305 periods. National (non-Part 21) records are kept until 2 years after the aircraft is destroyed or permanently withdrawn (CAP 562 5-70).
- Maintenance data must be applicable and current, kept up to date by subscription and amendment checks, with special attention to mandatory instructions and airworthiness limitations (M.A.401, ML.A.401, AMC M.A.401(c), AMC1 145.A.45(g)). A Part-CAO may obtain the data for a job before the work rather than holding everything all the time (AMC1 CAO.A.055).
- Work cards name the data and its revision, either transcribed accurately or precisely referenced (M.A.401(c), 145.A.45(e)).

## Part 9. Decisions only Alex can make: ask, do not assume

1. **The open source licence for the code:** permissive such as Apache 2.0, or one that keeps derivatives open such as AGPL. Also the licence for the open data standard. Set out the trade-offs and wait for his choice.
2. **The technology stack:** propose it in ADR-0001 and wait for approval.
3. **Hosting costs and any paid service:** penetration testing, Cyber Essentials Plus, backup storage.
4. **Whether real records may be used for dogfooding, and on what terms.**
5. **Earlier questions still open:**
   - whether SRG1782 names written in capitals are recased for display
   - whether engine maker short forms (PW, GE, RR) are spelled out
   - a Safety Policy document layout in the Exposition
   - Quality Manager or Compliance Monitoring Manager for Part-CAO
   - type evaluation for Group 3 aircraft
   - Part-145 compared with Part-CAO rules on the Planning and Tools pages
   - Settings placeholders
   - uploading CAP 741

## Part 10. How to work in this chat

- Keep a task list for the steps above and tick items off as they finish.
- Use subagents for large reading or independent verification. Use the main thread for decisions and writing.
- After each step, push to a branch, open a pull request, and tell Alex in two lines what changed and what needs his decision.
- The design canvas is a separate artifact with a limited number of saves per day. Do not republish it unless Alex asks. The repository is the source of truth.

Start with Step 1, then Step 2, and bring Alex the stack proposal (Step 4's ADR) before any product code.
