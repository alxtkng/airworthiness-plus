# Demo Guide

Date: 24 November 2026. What can be shown on the test site, in what order, signed in as whom.

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
2. Point to the four panels: Continuing Airworthiness, People, Documentation, Organisation.
3. Point to G-DGHI at the top: Unserviceable, in red.
4. Open a row with the arrow. The detail gives the rule and its reference.
5. Follow the link in the Page column. It goes to the page that holds the item.

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
2. **One aircraft.** Open G-ABCD. Show the tabs: Record, Maintenance Programme, Airworthiness Directives, Maintenance Data, Airworthiness Review.
3. **Maintenance Programme.** Open it. Open How It Was Calculated on a task. It shows the rule, the inputs and the source.
4. **Airworthiness Directives.** Open it. Show a directive that is Applicable, one Not Applicable and one still to assess.
5. **Airworthiness Reviews.** Open the Airworthiness Reviews tab of Aircraft. Show G-EJKL's certificate and the 90-day window.
6. **Maintenance Data.** Open Maintenance Data, under Documentation. Show the manual that is not held, at the top.
7. **Records.** Open Records, under Organisation. Show Records Export. Export one aircraft.
8. **Read Only.** Sign in as the reader. Try to open Add an Aircraft. It is refused.

## Part 3. Continuing Airworthiness, the Rest (Phase 1)

Sign in as Lucy Grant. The sample of this part is on the test site once its database has been remade from the sample (Issue 100).

### The Fleet

1. Open Aircraft. Next Due and Remaining are two columns. Choose the heading Remaining to sort by it.
2. Choose Due in 30 Days: three aircraft. Choose Unserviceable: G-DGHI alone.
3. Type a registration in the search above the table.

### Maintenance Programmes

1. Open Maintenance Programmes. Every aircraft of the Fleet is listed with its programme and when its annual review is due.
2. G-DGHI and G-EJKL say No Maintenance Programme Set Up. Open one: the programme is set up on the aircraft's own page.

### Aircraft Configuration

1. Open Aircraft Configuration, under Continuing Airworthiness. It opens on Components and Life Limits: 7 tracked, the nearest limit first.
2. G-CDEF's own propeller is Off-Wing, due back 25 November 2026. Open it: fitted in 2020, removed at its 6-year limit, and directive applicability to check before refit.
3. Go back. Open the detail of G-CDEF's engine, then How What Remains Was Calculated: 1,780.0 hours since overhaul, 220.0 left, ML.A.503.
4. G-DGHI's engine is On Condition: Review at 9,900.0.
5. Choose Add a Component. Type a name, choose Service Life Limit and 500 hours. Add it, then record its installation on G-ABCD at today's airframe hours.
6. Open the tab Airworthiness Directives. It says G-CDEF's propeller is away, with the applicability check before refit.
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
3. Open it. Open How the Limit Was Calculated: the day of the decision, the organisation's 30 days, and ML.A.403.
4. Open Deferral Limits. It is the Settings page, where the 30 days are set.
5. Go back. Choose Record a Defect. Choose G-FMNO, Deferred, Pilot-in-Command. Record it. Its limit is 30 days from the day decided.
6. Open the tab Repeat Defects. Landing light failures on the Piper PA-28: 3 in 12 months, a Repeat, with the action taken.
7. Open the Dashboard. The deferred defects are in Continuing Airworthiness, each with its limit and days remaining.
8. Open G-DGHI under Aircraft. Choose Record as Serviceable. It is refused: a defect that is Not Deferrable is open.

Say: the limit is the organisation's own number of days; the regulation gives none. The rule is ML.A.403.

### Release to Service

1. Open Release to Service. The counts are at the top: 3 issued in the last 30 days, 1 not yet in the records.
2. G-ABCD's tyre comes first: Due 21 November 2026. Open its detail, then How the Release Was Calculated: 30 days, ML.A.305(a).
3. G-CDEF's two certificates were issued by Chris Moore and entered the next day.
4. Choose Record the Certificate for the tyre. Choose Pilot-Owner, type a name and a licence number. Record it. It is now in the records, and gone from the Dashboard.
5. Point to Who May Release, with the point of ML.A.801 for each.

Say: the system records a certificate that was issued. It does not issue one.

### Contracts

1. Open Contracts. Five contracts: four for every task, and G-ABCD's for the programme review and the airworthiness review. G-HKLM's says Records Transfer.
2. Open G-DGHI's contract. It shows what Appendix I to Part-ML has a contract contain, as it stood when signed.
3. Go back. Three work orders. G-FMNO's says No Contract, Work Order Only, in its detail.
4. Choose Record a Work Order. Choose G-BXYZ, type the work, Owner, a day. It appears under G-BXYZ's contract.

## What Cannot Be Shown Yet

The rest of Phase 1 (set up configuration, the transfer checklist, the tabs of the aircraft record, departures and the annual review checklist of a programme, and the sources of directives) and Phases 2 to 9 of `prompts/canvas-build.md`: work packages, stores, tools, hazards, audits, training, documents, quotes, invoices and the Marketplace. This guide gains a part as each phase is finished.
