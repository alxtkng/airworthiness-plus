# Airworthiness+ Canvas Build: Working Brief

Written 24 November 2026 for Alex King, after the private beta slice was finished. Paste everything below the line into a new chat, or follow it in this one.

---

You are taking over Airworthiness+ after its private beta slice was built. The slice is the Part-CAO core loop for Part-ML aircraft. Your job now is to build the rest of the design canvas, one section at a time, to the same standard, so the test site shows the whole product working.

Read this brief, then `prompts/private-beta.md`. That brief still holds for everything this one does not change.

## Part 1. Where the Project Stands

- **Built and merged:** Organisation and Access, Aircraft, Maintenance Programme, Airworthiness Directives, Maintenance Data, Airworthiness Review, Records, records export and import, and the CAA acceptance records. There are 705 tests, and 104 requirements are traced.
- **Reviewed:** two independent reviews of the code (`assurance/independent-verification/code-review-2026-11-19.md` and `code-review-2026-11-20.md`). Every finding is fixed.
- **Running:** the test site, https://airworthiness-plus-test.onrender.com, on Render's free plan in Frankfurt with sample data only (`operations/test-site.md`). Its database ends on 20 December 2026 and is remade from the sample before then (Issue 100).
- **Not ready for sign-off:** `assurance/readiness-review.md`. There is no server and no budget for one, so nothing in this build changes that verdict. No real records go in.
- **The canvas:** 66 boards in `canvas/`, in 11 sections. 13 are built in whole or in part: Fleet, the aircraft record, Add an Aircraft, Airworthiness Reviews, Maintenance Programmes, Airworthiness Directives, Maintenance Data, Transfers, Recency of review staff, Approval and Scope, and the sidebar, tabs and top bar. The rest are backlog Issues 17 to 24, which so far hold no detail.

## Part 2. What Stays the Same

Everything in `prompts/private-beta.md` Parts 1, 2, 7 and 10 still applies: who Alex is and how to behave, the regulatory baseline, the writing and interface rules, and how to work in a chat. In short:

- The regulation is the specification. Every regulatory claim carries its reference. A claim you cannot source is marked To Be Checked. Never invent a rule, a number or a reference.
- Ask Alex only about cost, anything irreversible, and anything with no source. When he says "you decide", decide, record it in `design-system/Decisions.md` as ours, and tell him.
- Delete nothing without his confirmation. Never enter passwords or codes. Never push to `main`.
- The canvas is the design reference, not code to ship. Never republish it unless he asks.
- Sample data only. Nothing real goes onto the test site.

What the private beta taught, and this build keeps:

- Push only after a clean full run of the tests on your own machine.
- The tests written with the code missed the most serious defects twice. Every phase ends with an independent review of its code by a separate session, and every finding is fixed before the next phase starts.
- A test that cannot fail is a defect. Show each new test failing before the code that makes it pass.
- Every new record type goes into the export registry, the history, row-level security and `architecture/fields-by-action.md`. The build fails if one is left out.

## Part 3. Decisions for Alex

Each one below changes what gets built. A recommendation is given for each. Decided 24 November 2026: Alex King asked for the plan to be carried out in full, and every recommendation is recorded as ours in `design-system/Decisions.md`, Canvas Build. Phase 0 needs decisions 1 to 3 before it starts. The others are needed only by the phase named.

| Number | Decision | Recommendation | Needed By |
|---|---|---|---|
| 1 | Which approvals this build serves. The canvas shows items to Owner, Part-CAO, Part-CAMO and Part-145. The sample organisation holds Part-CAO only, so many boards would never show in a demo | Add Part-CAMO and Part-145 as approvals an organisation can hold, and a second sample organisation holding both, so every board can be shown. Stay with Part-ML aircraft; Part-M aircraft come later | Phase 0 |
| 2 | A person record apart from a sign-in. Staff, certifying staff, mentors, assessors and contracted engineers are on many boards, and not all of them sign in | A person record for everyone, with a sign-in for those who use the system | Phase 0 |
| 3 | An owner or customer record in place of the free-text Owned By on each aircraft | A customer record for each owner or operator, as the Customers board shows | Phase 0 |
| 4 | The Settings board's lead times differ from the record: 15 hours against 10.0, and alerts at 60 and 30 days against Due Soon at 30 days | Keep the defaults in `Decisions.md` (10.0 hours, 10 cycles, 30 days). Add the 60-day alert for review certificates as a setting | Phase 0 |
| 5 | The sidebar hides Hazard Log and Safety Reports from Part-CAO, while Compliance Monitoring and Actions show to it | Show all four to Part-CAO, since `Decisions.md` named the section Management System to fit Part-CAO's quality system | Phase 5 |
| 6 | Rules the canvas shows with no reference anywhere: the 85% load margin and 50.0 other hours a week, the experience logbook's rules and 10-year window, on the job training retakes, the competency minimum of 5 on a scale of 1 to 10, the enquiry reply within 2 working days, quote validity, invoicing on release | Each becomes a setting the organisation keeps, with the canvas value as its default, recorded as ours, not the regulation's | The phase that uses it |
| 7 | Money. Invoices show no Value Added Tax, payment terms or way to record a payment | Record invoices and payments only. Take no payments and connect to no payment service. Value Added Tax is a rate the organisation sets | Phase 8 |
| 8 | The Marketplace publishes 1,013 real organisations from the Civil Aviation Authority lists. The data includes addresses, websites and 3 email values, one of which may be a person's own. Sole traders are listed under their own names | Build it last. Show it only to signed-in users on the test site. Leave out the email values. Have it checked for data protection before anyone outside sees it. The licence for the open data is still Issue 25 | Phase 8 |
| 9 | The questions still open from the private beta brief, Part 9 | Each is asked in the phase that needs it: SRG1782 recasing and engine maker short forms in Phase 1; Quality Manager or Compliance Monitoring Manager in Phase 5; the Safety Policy layout in Phase 6; Group 3 type evaluation and uploading CAP 741 in Phase 7; Part-145 against Part-CAO on Planning and Tools in Phases 3 and 4; Settings placeholders in Phase 0 | As listed |
| 10 | Part 147 and Part 21 Subpart G. Neither is on the canvas sidebar | Out of this build (Issues 15 and 16) | None |

## Part 4. How Each Phase Is Built

The same steps, in order, for every phase.

1. **Read.** Read every board of the phase in `canvas/`, the lines about it in `design-system/Decisions.md` and `design-system/Procedures.md`, and its backlog Issue.
2. **Sample data.** Correct `design-system/SampleData.md` where the boards contradict each other or it (known contradictions are listed under each phase). Add what the phase needs. Every test and the test site use this data.
3. **Sources.** Check every regulatory reference the boards give against the UK text in the Civil Aviation Authority's Regulatory Library. Many are not yet among the points `Decisions.md` confirmed on 18 November 2026. Record each in the Regulation Facts table, or mark it To Be Checked. A rule with no reference is recorded as ours, or put to Alex.
4. **Requirements.** Add the requirements to `requirements/requirements.md`, each with its source, and a row for each in `requirements/traceability.csv`. Each phase takes the next block of 20 numbers from REQ-200, as the core did. Add hazards to `assurance/hazard-log.md` and threats to `architecture/threat-model.md` where the phase adds them.
5. **Tests first.** Write golden cases worked by hand from the sample, each citing its rule, and property tests for any arithmetic. Show each test failing before the code is written.
6. **Build.** Follow the data layer of ADR-0002: the record base, the hashed history, row-level security, no delete. Add each action to the role matrix in `accounts/roles.py` and `Decisions.md` together. Follow the interface rules.
7. **Recompute.** For every calculation, a separate session that has not seen the code recomputes the golden cases from the regulation and the sample alone. Record it in `assurance/independent-verification/`.
8. **Review.** At the end of the phase, a separate session reviews its code without being told what it is meant to show. Fix every finding, test first, and record them, as on 19 and 20 November 2026.
9. **Records.** Update traceability, the assurance case, the hazard log, the threat model, `assurance/asvs.md` for any new surface, and `Decisions.md`, in the same pull requests as the code.
10. **Show.** Merge on a green pipeline. Check that the test site has the change. Update the demo guide (`operations/demo.md`) with what can now be shown. Update the phase's backlog Issue.

One branch and one pull request for each piece of work. A phase is many pull requests.

## Part 5. The Phases

The order follows what each phase needs from the ones before it. A phase is on the test site and can be shown as soon as it is finished.

Sizes are the readers' estimates from the boards: small is one record type, a list and a form; medium is two to four record types or a calculation; large is a workflow across many records, or many calculations. References are as the boards or `Decisions.md` give them, and each is checked at step 3 before it is relied on.

### Phase 0. Foundations

What many later boards need. Nothing here is a section of its own.

| Work | Boards | Size |
|---|---|---|
| The full sidebar, section tabs and top bar, with items shown by the approvals held. Items appear as their boards are built | Sidebar, Tabs, TopBar | Small |
| Approvals an organisation holds, beyond Part-CAO (decision 1) | Settings | Medium |
| A person record, linked to a sign-in where there is one (decision 2) | Staff | Medium |
| A customer record for owners and operators (decision 3) | Customers | Medium |
| Organisation settings: deferral limits and alert lead times (decision 4) | Settings | Medium |
| The Dashboard, one panel for each section, built up phase by phase | Home | Large, in parts |
| The demo guide, `operations/demo.md`: what to show, in what order, signed in as whom | None | Small |

### Phase 1. Continuing Airworthiness, the Rest

| Board | What It Holds | Size |
|---|---|---|
| Defects, Open and Deferred | Defects for each aircraft, the deferral decision and its limit (ML.A.403) | Medium |
| Defects, Repeat Defects | Repeat defects by type and system over 12 months, and the action taken | Small |
| Contracts | Continuing airworthiness management contracts with owners (Appendix I to Part-ML), and the work orders placed under them | Medium |
| Release to Service | Certificates of release to service, whether each reached the records within 30 days (ML.A.305(a)), and who may release (ML.A.801) | Medium |
| Components and Life Limits | Components and their limits across the fleet, nearest first, with each component's history | Large |
| Modifications and Repairs | Service bulletin decisions and every change or repair embodied, with its approval route and mass effect (ML.A.304, ML.A.503) | Medium |
| Weight and Balance | Each aircraft's last weighing and weight schedule, and the mass change since | Medium |
| Set Up Configuration | The six steps that set up a new or transferred aircraft's configuration, signed by the Continuing Airworthiness Manager | Large |
| Transfers | Transfer in as a 10-item checklist, and transfer out by export | Large |

The boards already built show more than was built. This phase adds it:

- **Fleet:** the filter by All, Due in 30 Days and Unserviceable; the Remaining column; search always shown.
- **Aircraft record:** the tabs of the board, including the forecast and configuration views.
- **Add an Aircraft:** choosing the type from the SRG1782 list. This needs the Civil Aviation Authority's list as data (REQ-021), from Alex.
- **Maintenance Programmes:** a list across the fleet, departures from the manufacturer's instructions, and the annual review checklist.
- **Airworthiness Directives:** the sources checked, each with when it was last checked.

The per-flight technical log on the aircraft record is Issue 7 (Part-CAO E.4). Build it here only if Alex says so.

Open points: what counts as the same defect for a repeat is not defined; the reweigh rule is not stated; the defects page's amber dot does not follow its own lead time; whether a configuration baseline may be signed with items still open.

### Phase 2. People

| Board | What It Holds | Size |
|---|---|---|
| Staff, All Staff | Everyone, employed or contracted, with role, licence, authorisation and recurrent training, and former staff with how long their records are kept | Medium |
| Staff, Organisation Chart | The chains of responsibility from the Accountable Manager, and the management personnel | Small |
| Authorisations | Authorisations for certifying staff and airworthiness review staff, with scope and validity | Medium |
| Authorisations, Recency | Recency for certifying staff as well as review staff: days of experience in 2 years, the 100-day alternative, and what counts (CAO.A.040, 66.A.20(b), AMC 66.A.20(b)2, CAO.A.045) | Large |

Recency for certifying staff needs the person who did each piece of work, which work done does not yet record. CAMO.A.305 for Part-CAMO review staff recency is To Be Checked.

### Phase 3. Planning

| Board | What It Holds | Size |
|---|---|---|
| Work Packages | Packages of tasks against a work order, critical tasks and their independent inspection, and the checklist to release (ML.A.402, 145.A.35). Before issue, the package checks its maintenance data is held and current (AMC1 CAO.A.055) | Large |
| Manhour Plan | Hours needed against hours available for each function, month by month, shortfalls and their reports, and the share of employed staff on each shift (145.A.30(d), AMC 145.A.30(d), CAO.A.035(d)) | Large |
| Load and Capacity | Planned hours against hours available each week, and work due and not yet planned, from the due calculation already built | Medium |
| Staff Roster | Shifts by week against fatigue limits, and shift and task handovers (145.A.47) | Large |
| Settings, Planning | The rules the plan and roster use | Medium |

Closing a package records work done against the programme and directive tasks already built. Contradictions to correct in the sample: the contract engineer's authorisation date; who installed the trim cable; whether the L2 engineer is employed or contracted.

### Phase 4. Logistics

| Board | What It Holds | Size |
|---|---|---|
| Suppliers | Approved suppliers and subcontractors, and their evaluation | Small |
| Goods In, Receiving Inspection | Each item received, through receiving inspection, to stores, return or quarantine (component classes M.A.501, ML.A.501, 145.A.42) | Large |
| Stores, Stock | Stock by class and location, shelf life, reservations against work packages, and every issue | Medium |
| Stores, Quarantine and Scrap | Unserviceable and unsalvageable items and the decision on each (ML.A.504, AMC1 CAO.A.030(n)) | Medium |
| Tools and Equipment, Register | Every tool, its control (calibration, servicing or inspection before use), next due date, and issue and return | Large |
| Tool Record | One tool's calibration history, review of work done after an out-of-limits calibration, and interim checks | Medium |
| Service Providers | Calibration orders and whether each certificate was accepted (145.A.40(b), CAO.A.050(b), AMC 145.A.40) | Medium |
| Alternative Tooling | The assessment of a tool used in place of one the maintenance data names (CAO.A.050(a), 145.A.40(a)) | Medium |
| Tooling Need Evaluations | For each type rating, the tool each task needs and how it is met | Medium |

To Be Checked on the boards: the propeller balancing kit's basis. Most of the references here are not yet confirmed against the UK text.

### Phase 5. Management System and Organisation

| Board | What It Holds | Size |
|---|---|---|
| Occurrence Reports | Reports sent outside the organisation, the 72-hour clock and the follow-up (ML.A.202, M.A.202) | Medium |
| Compliance Monitoring | The audit programme and findings, each with root cause, corrective action and verification, at Level 1 or Level 2 | Large |
| Actions | One list of actions from hazards and from findings | Medium |
| Hazard Log | Hazards assessed before and after mitigation, with a second assessment, on the severity and likelihood of CAP 795 | Medium |
| Safety Reports, and Report a Safety Issue | Confidential internal safety reports, how each was assessed, and feedback to the reporter | Medium |
| Approval and Scope | The approval certificate (CAA Form 3-CAO), privileges and scope of work | Medium |
| Changes | Changes to the approval, and whether the Civil Aviation Authority has been told within 15 days (CAO.A.105) | Medium |
| Oversight | The Civil Aviation Authority's audits of the organisation and their findings | Small |

Open points: whether an action is its own record or a view of hazards and findings; decision 5. Contradiction to correct: notice N-2026-001 is dated before the occurrence it came from.

### Phase 6. Documentation

| Board | What It Holds | Size |
|---|---|---|
| Manuals and Procedures | The register of controlled documents, with revision, owner and next review | Small |
| Revisions | Revisions in progress and issued, and what changed | Medium |
| Notices | Safety and quality notices to staff | Small |
| Required Reading | Documents and notices assigned to staff, and who has acknowledged them. The button says Acknowledge, never Sign | Medium |
| Combined Airworthiness Exposition | The 59 chapters of AMC1 CAO.A.025, each with the module that does it, Exposition Text, or Not Yet in Airworthiness+, and the revision history | Large |

The exposition's 59 chapters: 49 are done by modules, 4 are free text, and 6 are not yet in Airworthiness+. The Maintenance Data board also shows more than was built; add it here.

### Phase 7. Training

| Board | What It Holds | Size |
|---|---|---|
| Recurrent Training | Training repeated on a cycle (Human Factors, Electrical Wiring Interconnection System, Fuel Tank Safety, continuation training), for each person, with due dates (145.A.30(e)) | Medium |
| Competency Assessments, and the Assessment Form | Assessments, their effect on authorisation, support measures and triggers, and the form itself | Large |
| Basic Examinations | Part-66 module examinations toward a licence category, who examined each, and how long a pass can be used (66.A.25) | Medium |
| Experience Logbook | Basic experience as in the CAP 741 logbook, countersigned, with an export for the licence application (66.A.30) | Large |
| Type Training | Part-147 type courses, theory and practical, and the date by which the type rating must be applied for (66.A.45) | Medium |
| On the Job Training | Training for a first type rating: the task logbook, mentor and assessor, and the final assessment (Appendix III to Part-66) | Large |

The references in brackets for Basic Examinations, the Experience Logbook, Type Training and On the Job Training are in the canvas generators' comments, not on the boards. Contradictions to correct: Chris Moore's Fuel Tank Safety date; the planner's training and reassessment dates.

### Phase 8. Commercial

| Board | What It Holds | Size |
|---|---|---|
| Customers | One record for each owner or operator: their aircraft, contract, open work and money owed | Medium |
| Enquiries | Requests for work, with a reply deadline, and what became of each | Small |
| Quotes | Priced quotes. An accepted quote becomes the written work order | Medium |
| Invoices | Invoices for released work and contract fees, and what is unpaid (decision 7) | Medium |
| Marketplace | Approved organisations from the Civil Aviation Authority lists, by legal entity, to send an enquiry or add as a supplier (decision 8) | Large |

The Marketplace data is `data/caa/marketplace5.json`. The raw lists and the step that made it are not in the repository. The "For Aircraft Registration" filter is fixed to the six sample aircraft, and Claim This Listing has no process yet.

### Phase 9. Help

| Board | What It Holds | Size |
|---|---|---|
| Help | What each item holds, who it shows for, its regulatory point, the time limits behind alerts, and the competency assessment scale | Small |

Some of its references differ from the record (for example ML.A.904 against ML.A.903(f)). Correct them from the record, not the board.

## Part 6. How Long

The core took about three days of build sessions for 7 modules and 104 requirements. The rest of the canvas is about 52 boards, of which about 16 are large. Expect weeks of sessions, not days. No date is given until Phase 0 is done and its pace is known.

The test site grows with each phase, so a demo is possible at every stage. By the time Phase 1 is done, Continuing Airworthiness can be shown complete.

## Part 7. Start

1. Decisions 1 to 10 are recorded (Part 3).
2. Build Phase 0.
3. Build Phase 1, and keep going in order.

After each pull request, tell Alex in two lines what changed and what needs his decision.
