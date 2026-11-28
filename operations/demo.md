# Demo Guide

Date: 27 November 2026. What can be shown on the test site, in what order, signed in as whom.

The test site holds sample data only. No real record is ever entered on it (`test-site.md`).

Today on the test site is the real day, not the sample's 18 November 2026. So day counts differ from `design-system/SampleData.md`, and some items will show as overdue.

## Before the Demo

Do this once, the day before.

1. Open https://airworthiness-plus-test.onrender.com. The first page can take a minute: the free host sleeps.
2. Sign in as the Administrator, `accountable.manager@your-organisation.example` (`test-site.md`, Signing In).
3. Open Users, under Organisation.
4. Give Lucy Grant a first password. The page shows it once. Write it down.
5. Do the same for `planning@your-organisation.example` and `reader@your-organisation.example`.
6. Sign out. Sign in as each of them once, set up the authenticator and choose a password.

For the second organisation, do the same with its Administrator, `accountable.manager@second-organisation.example`. Its first password is its own value in Render, `AIRWORTHINESS_TEST_SITE_SECOND_ADMINISTRATOR_PASSWORD`, never the first Administrator's. It works for 7 days from the day the second organisation was made.

## The Sample Users

| Organisation | Sign In As | Roles | Use For |
|---|---|---|---|
| [Your Organisation], Part-CAO | `accountable.manager@your-organisation.example` | Administrator | Users, Staff, Settings |
| | `lucy.grant@your-organisation.example` | Continuing Airworthiness Manager, Airworthiness Review Staff | Aircraft, programmes, directives, reviews, customers |
| | `planning@your-organisation.example` | Planning and Records | Hours, work done, maintenance data, customers |
| | `review@your-organisation.example` | Airworthiness Review Staff | Reviews only |
| | `reader@your-organisation.example` | Read Only | Showing that nothing can be changed |
| [Second Organisation], Part-CAMO and Part-145 | `accountable.manager@second-organisation.example` | Administrator | Users, Staff, Settings |
| | `manager@second-organisation.example` | Continuing Airworthiness Manager | Aircraft, customers |
| | `reader@second-organisation.example` | Read Only | Reading |

## Part 1. Foundations (Phase 0)

About 10 minutes. Sign in as Lucy Grant unless a step says otherwise.

### The Dashboard

1. Sign in. The Dashboard opens.
2. Find G-DGHI in Aircraft Restrictions. Read the recorded reason and open its supporting record.
3. Find the next deferred-defect limit in Due and Overdue when it is within the lead time. Open the defect.
4. In Needs Assessment, find an aircraft with no maintenance programme set up and open the programme.
5. Choose Full Register to see Continuing Airworthiness, Planning, People, Documentation and Organisation. Search the Continuing Airworthiness table for G-DGHI and open a row’s details.

Say: the Dashboard works nothing out. It reads the same figures as the pages.

### The Sidebar

1. Point to the groups: Continuing Airworthiness, People, Documentation, Organisation, Commercial.
2. Say: an item appears when its page is built, and only for an approval the organisation holds.

### Staff

1. Open Staff, under People.
2. Point to people with no sign-in, such as Chris Moore. Everyone has a record. Not everyone signs in.
3. Scroll to Former Staff. Open the row. It shows how Record Kept Until was worked out, with CAO.A.045(e).
4. Sign out. Sign in as the Administrator.
5. Open Staff, then Add a Person. Add someone and save.

### Customers

1. Sign in as Lucy Grant. Open Customers, under Commercial.
2. Point to the count of customers and aircraft at the top.
3. Open a customer. Its aircraft are listed.
4. Open Aircraft, then G-EJKL. Scroll to Owner of G-EJKL. Choose another customer and save.
5. Go back to Customers. The aircraft has moved.

Note: on a test site made before 24 November 2026, three aircraft share one customer named Pilot-Owner. That is what was typed before customers were records. It is put right at the next remake (`test-site.md`).

### Settings

1. Sign in as the Administrator. Open Settings, at the foot of the sidebar.
2. Show Approvals Held. Record Part-145 with a made-up reference such as UK.145.[Number]. It is added.
3. Show Deferral Limits. Each line gives its point of ML.A.403.
4. Show Alert Lead Times. Change Hours from 10.0 to 15.0 and save.
5. Open the Dashboard. G-ABCD's 50-hour check may now show, if it has under 15.0 hours left.
6. Put Hours back to 10.0.

### Two Organisations

1. Sign out. Sign in as `manager@second-organisation.example`.
2. Show the Dashboard and Aircraft. Only its two aircraft are there: G-JNOP and G-KQRS.
3. Open Settings. It holds Part-CAMO and Part-145.

Say: each organisation sees only its own records. The database enforces it, not only the pages.

## Part 2. The Core Loop (Private Beta)

About 15 minutes. Sign in as Lucy Grant.

1. **Aircraft.** Open Aircraft. Point to what comes first: what needs attention.
2. **One aircraft.** Open G-ABCD. Show the tabs: Record, Maintenance Programme, Maintenance Forecast, Airworthiness Directives, Configuration, Maintenance Data, Airworthiness Review. Open Maintenance Forecast: everything that falls due on the aircraft, the soonest first, with the next 120 days above. Open Configuration: its components, changes and weighing; for G-HKLM, its positions under five filters.
3. **Maintenance Programme.** Open it. Open How It Was Calculated on a task. It shows the rule, the inputs and the source.
4. **Airworthiness Directives.** Open it. Show a directive that is Applicable, one Not Applicable and one still to assess.
5. **Airworthiness Reviews.** Open the Airworthiness Reviews tab of Aircraft. Show G-EJKL's certificate and the 90-day window.
6. **Maintenance Data.** Open Maintenance Data, under Documentation. Show the manual that is not held, at the top.
7. **Records.** Open Records, under Organisation. Show Records Export. Export one aircraft.
8. **Read Only.** Sign in as the reader. Try to open Add an Aircraft. It is refused.

## Part 3. Continuing Airworthiness, the Rest (Phase 1)

Sign in as Lucy Grant. The sample of this part is added to the test site at its next start (REQ-294), but for the two defects and the two certificates that name certifying staff, which arrive once its database has been remade from the sample (Issue 100).

### The Fleet

1. Open Aircraft. Next Due and Remaining are two columns. Choose the heading Remaining to sort by it.
2. Choose Due in 30 Days: three aircraft. Choose Unserviceable: G-DGHI alone.
3. Type a registration in the search above the table.

### Transfers and Set Up Configuration

1. Open Aircraft, then the tab Transfers. G-HKLM's transfer started on 9 November 2026 and is 4 of 10 complete.
2. Read down its checklist. Beside Records Received and Checked the records say 14 of 18 Received. Try to record it as Complete: it is refused.
3. Choose Set Up Configuration. Read the six steps down the page: the aircraft, the product structure, the major items, the 12 tracked positions, the changes embodied, and the review.
4. Step 6 lists 6 open items, and there is no button to sign. Record the Right Magneto in step 4: 5 remain.
5. Go back to Transfers. Transfer Out and Record Export leads to the export of an aircraft's complete record.

Say: a baseline is not signed with items still open, and an aircraft does not move to the Fleet with an item of its checklist open. Both rules are ours.

### Maintenance Programmes

1. Open Maintenance Programmes. Every aircraft of the Fleet is listed with its programme and when its annual review is due.
2. G-EJKL says No Maintenance Programme Set Up. Open it: the programme is set up on the aircraft's own page.
3. Go back. G-DGHI has 2 departures. Open it: each says what the manufacturer recommends, what the programme says, the compensating measures and the justification, with the owner copy sent.
4. Go back. G-FMNO's detail says Open, 4 of 6 Complete. Open it and find Annual Review: the six points of AMC1 ML.A.302(c)(9), two still open.
5. Choose Complete the Review with today's date. It is refused, and names the two points. Tick them, save, and complete it: the programme is reviewed today.

Say: the annual review is not completed with a point still open. That rule is ours.

### Aircraft Configuration

1. Open Aircraft Configuration, under Continuing Airworthiness. It opens on Components and Life Limits: 9 tracked in the full sample, the nearest limit first.
2. G-CDEF's own propeller is Off-Wing, due back 25 November 2026. Open it: fitted in 2020, removed at its 6-year limit, and directive applicability to check before refit.
3. Go back. Open the detail of G-CDEF's engine, then How What Remains Was Calculated: 1,780.0 hours since overhaul, 220.0 left, ML.A.503.
4. G-DGHI's engine is On Condition: Review at 9,900.0.
5. Choose Add a Component. Type a name, choose Service Life Limit and 500 hours. Add it, then record its installation on G-ABCD at today's airframe hours.
6. Open the tab Airworthiness Directives. It says G-CDEF's propeller is away, with the applicability check before refit. Sources lists what the organisation checks for new directives, each with when it was last checked and next. Choose Record a Check beside one.
7. Open the Dashboard. The propeller due back is in Continuing Airworthiness.

8. Open the tab Modifications and Repairs. G-BXYZ's service bulletin is awaiting the owner, with its reminder. Below, each change or repair has its approval route and mass effect.
9. G-BXYZ's navigator says Weight Schedule Update. Follow it to Weight and Balance: +1.2 Kilograms since the weighing of 2019.
10. Point to No Reweigh Threshold Set. Sign in as the Administrator, open Settings, set the reweigh threshold to 1.0 Kilograms. G-BXYZ now says Reweigh.
11. As Lucy Grant, choose Record a Weight Schedule Issue: G-BXYZ, Issue 7, today. The navigator's records are Complete.

Say: the reweigh threshold is the organisation's own. No rule read gives one, so there is none until it is set.

Say: the hours of a component are those it had when fitted and what the airframe has flown since. No tolerance is given to a life limit.

### Defects

1. Open Defects, under Continuing Airworthiness. Four are open. G-DGHI comes first: Not Deferrable, Grounded.
2. Point to G-BXYZ: deferred by Sam Patel on 28 October 2026, limit 27 November 2026.
3. Open it. Open How the Limit Was Calculated. Look for the recorded start date, the organisation's 30 days and the ML.A.403 reference.
4. Open Deferral Limits. It is the Settings page, where the 30 days are set.
5. Go back. Choose Record a Defect. Choose G-FMNO, Deferred, Pilot-in-Command. Record it. Set the date first identified a day before the decision. Its limit is 30 days from identification.
6. Open the tab Repeat Defects. Landing light failures on the Piper PA-28: 3 in 12 months, a Repeat, with the action taken.
7. Open the Dashboard. The deferred defects are in Continuing Airworthiness, each with its limit and days remaining.
8. Open G-DGHI under Aircraft. Choose Record as Serviceable. It is refused: a defect that is Not Deferrable is open.

Say: the limit is the organisation's own number of days; the regulation gives none. The rule is ML.A.403.

### Release to Service

1. Open Release to Service. The counts are at the top: 3 issued in the last 30 days, 1 not yet in the records.
2. G-ABCD's tyre comes first: Due 21 November 2026. Open its detail, then How the Release Was Calculated: 30 days, ML.A.305(a).
3. G-CDEF's two certificates were issued by Chris Moore and entered the next day.
4. Choose Record the Certificate for the tyre. Choose Pilot-Owner, type a name and a licence number. Record it. It is now in the records, and gone from the Dashboard.
5. Point to Who May Release, with the point of ML.A.801 for each. The recording page also offers Retain Unverified Historical Evidence for a signed source dated during an earlier grounding period. That entry leaves any outstanding release deadline due.

Say: the system records a certificate that was issued. It does not issue one.

### Contracts

1. Open Contracts. Five contracts: four for every task, and G-ABCD's for the programme review and the airworthiness review. G-HKLM's says Records Transfer.
2. Open G-DGHI's contract. It shows what Appendix I to Part-ML has a contract contain, as it stood when signed.
3. Go back. Three work orders. G-FMNO's says No Contract, Work Order Only, in its detail.
4. Choose Record a Work Order. Choose G-BXYZ, type the work, Owner, a day. It appears under G-BXYZ's contract.

## Part 4. People (Phase 2)

### Staff and Authorisations

1. Open Staff and select Organisation Chart to see the current reporting lines and management personnel.
2. Open a staff record to see any recurrent training evidence. A freshly seeded sample shows Sam Patel’s Human Factors completion and 6 December 2026 renewal date.
3. Use the Administrator role to record a completed course from its reference. Return to Staff to see the latest completion for the subject.
4. Open Authorisations. Use the Recency tab to see review staff recency alongside the most recent attributed work for certifying staff. Open a maintenance authorisation to record assessed work or approved maintenance employment against its scope. The Recency tab shows the resulting duration. Withdraw a mistaken assessment with a reason to retain the evidence and remove it from the total.
5. From Authorisations, open an existing maintenance authorisation. Use a reason and an effective date when withdrawing its evidence. The original authorisation stays visible.
6. For an externally signed release or certifying-staff deferral, identify the named authorisation and confirm its scope. Enter the signed source reference for a legacy record whose authorisation evidence is unavailable. In the aircraft’s Work Done list, follow the release reference to its retained evidence after it leaves the recent-release board.

## Part 5. Planning (Phase 3)

### Work Packages

Sign in as Planning and Records and open **Planning → Work Packages → WP-2026-048**. The draft shows the annual check and right headset socket for G-EJKL and its 32.0 planned hours. Issue requires an agreed order and current maintenance data. Open a package to see the work cards, revision references and release checklist.

### Staffing Plan

Sign in as Planning and Records and open **Planning → Staffing and Capacity → Staffing Plan**. Each approval uses its own plan. In the Part-145 sample organisation the December report preserves 290 hours needed and 192 hours available, a 34% shortfall before cover. The current plan shows 88 hours of forecast contracted cover and a 3% shortfall.

### Staff Roster and Load and Capacity

Sign in as Planning and Records and open **Planning → Staffing and Capacity → Staff Roster**. A maintenance shift on 19 November from 08:00 to 19:00 with a 30-minute break records 10.5 working hours and flags the organisation's 10-hour limit. Record handover notes and sign in as the named recipient to see the acknowledgement action. **Load and Capacity** shows the roster hours and preparation demand, and links to unplanned work. **Settings → Planning** shows and, for the Administrator, edits the calculation inputs.

## Part 6. Logistics (Phase 4)

Sign in as the Continuing Airworthiness Manager and open **Logistics → Suppliers**. Find the propeller organisation and its 30 November 2026 evaluation date, and open the oil supplier to review its suspension evidence. Select **Evaluate a Supplier** to record a new sample supplier, then open that supplier and **Record an Evaluation** to append a decision. The register shows the latest decision and the supplier record retains both evaluations. Use a fictitious supplier on the test site.

On a fictitious supplier record, choose **Record Subcontractor Assessment**. Enter a specialised maintenance scope, the organisation's exposition reference, the qualification evidence and the controls. Part-145 also asks for a pre-audit reference when recording controls. Save and expand the history row to see the supporting evidence. A later suspension remains in this history alongside the earlier assessment.

### Goods In and Receiving Inspection

Open **Logistics → Goods In** as Planning and Records. Select the ELT battery to see two recorded checks and its pending disposition. Compare the two G-DGHI trim cable receipts. One was returned and the replacement was accepted. The oil receipt shows the inspection and return on consecutive dates. Open the owner-supplied alternator to see its failed check and quarantine evidence. On the accepted trim cable receipt, open **View Stores Entry**. Check the recorded location and release evidence, then follow the link back to the receipt. Open **Logistics → Stores → Stock** to find the same entry. Use **Receive an Item** with a fictitious delivery-line reference to try recording a receipt, checks and a disposition.

### Stores

Open **Logistics → Stores → Stock** as Lucy Grant. The engine oil (RX-006) is posted to Bay C with 24 L on hand and available. The bolts (RX-007) show 50 on hand with a count of 46 waiting for an authorised adjustment. The accepted trim cable (RX-002) is listed under **Awaiting Stock Posting** with its blocking reasons and nothing available. The alternator (RX-004) is a quarantine hold with its details to verify, and the two supplier returns stay in **Return History** with no stock credit. Open RX-002, use **Record Posting Evidence** with fictitious part and serial numbers and **BAY-A**, then **Post to Stock**. Move 8 L of oil to the Hangar Oil Store and see 16 L and 8 L, still 24 L in total. Apply the bolts count with **Adjust for Count**. **Locations** and **Stores Appointments** show the location rules and the dated appointments behind each action. The appointments and procedures are fictitious and To Be Checked against an exposition.

## Tools and Equipment

Open **Logistics → Tools and Equipment** in the fictitious Part-CAO organisation. Open 0201 and compare the accepted service evidence, six-month interval and 3 February 2027 deadline. Open 0210 for its condition restriction and missing service completion, then 0301 for the before-use instruction. The loaned balancing kit has a lender and no established control basis. Open 0142 to see the unresolved source evidence.

As the Administrator, open **Tool Delegations** to review the sample procedure and action coverage. As Lucy Grant, register a fictitious asset at the Hangar, record its control basis, and use **Record Tool Event** to select the matching revision and add completion evidence. Try a restriction, completed repair and authorised return using the fictitious procedure and evidence references. The marked sample site adds missing examples on upgrade. Its existing tool records are preserved.

Open **Tools and Equipment → Service Providers**. Compare C07's expected return, the previously reported deadline and the blank physical return. C06 has a physical return with a missing-traceability rejection and a calibration hold. Its order links to the original certificate revision. Record any trial certificate or point results against a new fictitious order. The order keeps prospective reinstatement separate from the open affected-work case.

## What Cannot Be Shown Yet

Choosing the type from the SRG1782 list (REQ-021) and the remaining boards in Phases 4 to 9 of `prompts/canvas-build.md` remain outside this demo. These include further Stores and tooling controls, hazards, audits, training, documents, quotes, invoices and the Marketplace.

## AMOS workflow rehearsal

Open **Maintenance History** from an aircraft or **Work Packages** to search by
aircraft, chapter or section, date and status. Use the **Report Text** and
**Corrective Action** fields to locate the corresponding evidence. From
an aircraft record, open **Damage Register** to follow a drawing marker and its equivalent list entry to the physical reference, repair and follow-up inspection. In **Technical Log**, start with a flight and filter reports by ATA and the linked part. Review the original reporter and the separately recorded recorder and certifier.

In **Stores**, open **Practise Stock Lookup** and compare ZRH Main, ZRH and the network totals. The checkpoint follows the session. With the prepared fictitious lot, use the part-number or specification lookup, reserve against issued work, issue and return it to secure quarantine under the appropriate Stores appointments. The certifying person records any applicable alternate approval separately. In **Dispatch**, move an assignment across shifts, read the conflict reasons and acknowledge an incoming handover as the named recipient.

The structured work-card signing queue needs the synthetic trial setting enabled in an isolated local environment. Follow the mobile journey and review the archived version while independent inspection is outstanding. For the two-organisation stop, fallback and cutover exercises, follow the [parallel handover protocol](amos-parallel-handover.md). The locally tested outcomes and outstanding operational evidence are in the [case matrix](../assurance/amos-evidence-matrix.md).
