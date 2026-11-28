# Sample Data

Every page uses this data. Placeholders in square brackets stand for real values. Today in the mockup is 18 November 2026.

## Organisation

- [Your Organisation], Part-CAO, UK.CAO.[Number], CAA Form 3-CAO, all four privileges.
- Scope: Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less; Sailplanes and Powered Sailplanes (management and review only); Piston Engines, Lycoming and Continental; C14 Landing Gear; C16 Propellers.
- Combined Airworthiness Exposition Revision 7, approved 30 October 2026; Revision 8 in draft.

## Second Organisation

Added on 24 November 2026 (Decisions.md, Canvas Build, decision 1), so that what is shown only to a Part-CAMO or a Part-145 can be shown. It starts small, and each phase adds what its boards need. Every value is made up for the sample and is to be confirmed by Alex King.

- [Second Organisation], Part-CAMO, UK.CAMO.[Number], and Part-145, UK.145.[Number]. Address [Second Organisation Address].
- Scope: Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less. Its aircraft are Part-ML, as in the first organisation.
- People: [Second Accountable Manager] (Administrator); [Second Continuing Airworthiness Manager] (Continuing Airworthiness Manager), who reports to the Accountable Manager; [Second Maintenance Manager], no sign-in, who reports to the Accountable Manager; [Second Certifying Staff Name], Part-66 B1.2, no sign-in, who reports to the Maintenance Manager; [Second Read Only Name] (Read Only).
- Customers: [Operator Name], Operator; [Second Owner Name], Pilot-Owner.

| Aircraft Registration | Type Rating | Owned By | Airframe Hours |
|---|---|---|---|
| G-JNOP | Piper PA-28 Series (Lycoming) | Operator | 2,406.5 |
| G-KQRS | Cessna/Reims-Cessna 172/F172 Series (Lycoming) | Pilot-Owner | 5,120.0 |

No maintenance programme, directive, maintenance data or review certificate is recorded for it yet, and the Dashboard says so.

## Documentation

- Controlled documents: Combined Airworthiness Exposition Revision 7 (Revision 8 in draft); Safety Policy and Objectives Issue 3, 1 June 2026, [Accountable Manager]; Company Forms Issue 12, 30 October 2026 (Issue 13 in review, Receiving Inspection Record); Human Factors Training Syllabus Issue 2, 6 January 2026; Hangar Rules and Fire Precautions Issue 4, 12 March 2026, review due 12 December 2026.
- Required Reading, 12 staff: Exposition Revision 7 due 13 November 2026, 11 of 12, the Part-66 L2 [Name] outstanding (5 days overdue); N-2026-004 due 25 November 2026, 7 of 12; [Contract Engineer] new starter exposition reading before authorisation is issued.
- Maintenance data: manufacturers' maintenance manuals for every type in scope, checked 2 November 2026; Grob G 115 manual amendment to check by 20 November 2026 (G-FMNO); Piper PA-38 Series manual not held, needed for G-HKLM; Lycoming and Continental service information, airworthiness directives and CAP 747 checked 16 November 2026; data query SR-2026-015 (torque value on the work card differed from the manual), to assess; G-BXYZ owner-provided supplementary type certificate instructions, confirmed current in writing 2 June 2026.
- Notices: N-2026-004 Safety Notice, trim cable inspection from OR-2026-002, 18 November 2026; N-2026-003 Quality Notice, suspected unapproved parts from OR-2026-003, 8 November; N-2026-002 Quality Notice, engine oil batch rejected, 29 October; N-2026-001 Safety Notice, fuel drain checks from OR-2026-001, 3 March 2026.

## Fleet

| Aircraft Registration | Type Rating | Owned By | Status | Next Due | Remaining | Review Certificate Valid To | Airframe Hours |
|---|---|---|---|---|---|---|---|
| G-DGHI | Piper PA-28 Series (Lycoming) | Flying Club | Unserviceable, Stabilator Trim Cable | Rectify Defect | Grounded | 19 May 2027 | 9,874.3 |
| G-EJKL | Cessna/Reims-Cessna 152/F152 Series (Lycoming) | Pilot-Owner | Serviceable | Airworthiness Review | 18 Days | 6 December 2026 | 11,206.8 |
| G-ABCD | Piper PA-28 Series (Lycoming) | Pilot-Owner | Serviceable | 50-Hour Check and Left Landing Light Deferral | 12.4 Hours and 15 Days | 14 March 2027 | 6,412.6 |
| G-BXYZ | Cessna/Reims-Cessna 172/F172 Series (Lycoming) | Syndicate of 6 | Serviceable | Cabin Entry Step Deferral | 9 Days | 2 August 2027 | 3,318.0 |
| G-FMNO | Grob G115/120 Series (Lycoming) | Pilot-Owner | Serviceable | Annual Check | 78 Days | 27 April 2027 | 4,950.2 |
| G-CDEF | Robin DR 400 series (Lycoming) | Syndicate of 4 | Serviceable | Maintenance Programme Annual Review | 358 Days | 2 December 2027 | 7,731.5 |
| G-HKLM | Piper PA-38 Series (Lycoming) | Pilot-Owner | Transfer In | Records 14 of 18 Received | | | |

Corrected on 27 November 2026 from the Fleet board: what remains is a column of its own, Remaining, beside Next Due. With deferred defects included, four aircraft are Due in 30 Days on 18 November 2026: G-DGHI, Unserviceable; G-BXYZ, 9 days to its cabin entry step limit; G-ABCD, 15 days to both its check and its defect limit; G-EJKL, 18 days to its review certificate expiry. One is Unserviceable.

## Maintenance Programme Inputs

The Fleet table shows results. These are the inputs that produce them, added on 18 November 2026 so that the golden test cases can be worked by hand. The Fleet compares these results with fitted component limits, recorded annual programme reviews, deferred defect limits and review certificate expiry.

| Aircraft Registration | Task | Interval | Last Done | Airframe Hours When Done | Planning Utilisation |
|---|---|---|---|---|---|
| G-ABCD | 50-Hour Check | 50 hours | 2 October 2026 | 6,375.0 | 0.8 hours a day |
| G-BXYZ | 100-Hour or Annual Check | 100 hours or 12 months, whichever comes first | 30 July 2026 | 3,259.0 | 0.5 hours a day |
| G-FMNO | Annual Check | 100 hours or 12 months, whichever comes first | 4 February 2026 | 4,912.0 | 0.2 hours a day |

- G-ABCD: due at 6,425.0 hours; 6,425.0 less 6,412.6 is 12.4 hours.
- G-BXYZ: due at 3,359.0 hours (41.0 hours remaining) or on 30 July 2027 (254 days). At 0.5 hours a day 41.0 hours is 82 days, so hours come first.
- G-FMNO: due at 5,012.0 hours (61.8 hours remaining) or on 4 February 2027 (78 days). At 0.2 hours a day 61.8 hours is 309 days, so the calendar limit comes first.

Added on 18 November 2026 for the programme pages, to be confirmed by Alex King: G-ABCD and G-CDEF are taken to be on the design approval holder's instructions. G-CDEF's engine counts hours since its last overhaul, 0.0 on 12 March 2019, and reads 1,780.0; the overhaul is taken as every 2,000 hours, so 220.0 remain. The original Fleet board writes this as 220 Hours. G-CDEF's programme was last reviewed with its airworthiness review on 11 November 2026. The next annual programme review on 11 November 2027 is 358 days from the sample date, before the projected overhaul at 366 days and the airworthiness review certificate expiry at 379 days. The G-ABCD tyre was replaced at 6,390.0 airframe hours.

The basis of each aircraft's maintenance programme is not yet recorded here. The tolerance cases, added on 18 November 2026, take G-BXYZ and G-FMNO to be on the Minimum Inspection Programme (ML.A.302(d)(1): tolerance 1 month or 10 hours); to be confirmed by Alex King.

- G-BXYZ: the tolerance ends at 3,369.0 hours (51.0 hours remaining) or on 30 August 2027 (285 days). The review certificate is valid to 2 August 2027, so the calendar tolerance ends after it.
- G-FMNO: the tolerance ends at 5,022.0 hours (71.8 hours remaining) or on 4 March 2027 (106 days), before the review certificate's 27 April 2027.

Added on 27 November 2026 for the Maintenance Programmes list. The Maintenance Programmes board contradicts what is recorded above, and is not taken until Alex King says which is right:

- The board gives G-ABCD's programme as Owner Declared, Issue 3, based on the Minimum Inspection Programme and the manufacturer's instructions, with its annual review due 2 March 2027; G-BXYZ's as Organisation Approved, Issue 5, on the manufacturer's instructions, due 15 January 2027; G-CDEF's as Organisation Approved, Issue 2, due 8 April 2027. The record above has G-ABCD and G-CDEF on the design approval holder's instructions, G-BXYZ and G-FMNO on the Minimum Inspection Programme, and one annual review recorded: G-CDEF's, on 11 November 2026, so next by 11 November 2027.
- Who declared or approved a programme, and its issue, are not recorded yet.

Added on 27 November 2026 for departures and the annual review, from the Maintenance Programmes board, to be confirmed by Alex King:

- G-DGHI is given a programme, as the board has it: on the design approval holder's instructions, planning utilisation 0.8 hours a day (the board's Club Use, About 300 Hours a Year), last reviewed 4 March 2026, so next by 4 March 2027, 106 days from 18 November 2026. Until now the sample gave G-DGHI no programme.
- Its two departures, each recorded on 4 March 2026 with the owner copy sent that day: Engine Overhaul, Lycoming O-360, manufacturer 2,000 Hours or 12 Years, programme On Condition, Reviewed Every 100 Hours, compensating measures Oil Analysis Every 50 Hours, Compression and Borescope Every 100 Hours, justification Club Use, About 300 Hours a Year; and Vacuum Pump Replacement, manufacturer 500 Hours, programme On Condition, compensating measures Standby Vacuum Source Fitted, justification Pump Checked Every 50 Hours. The board gives no justification apart from its second line; that line is taken as it.
- G-FMNO's annual review is in progress, opened 9 November 2026 (made up), 4 of 6 complete, as the board has it: Maintenance Results This Year, 2 Defects, No Repeats; Last Airworthiness Review, 27 April 2026, Programme Adequate; Configuration, Type and Operation, No Change, Private Flying; Directives, Airworthiness Limitations and Data Sheet, Checked 16 November 2026. Open: Minimum Inspection Programme and Manufacturer's Revisions, Maintenance Manual Revision [Revision] to Check; Pilot-Owners, Awaiting Owner Confirmation.
- With 0.8 hours a day G-DGHI's engine review, 25.7 hours away, is placed at 32 days, so the Components page then reads in the board's order.

## Sources of Directives

Added on 27 November 2026 for the Airworthiness Directives board.

| Source | Covers | Last Checked | Next Check |
|---|---|---|---|
| Civil Aviation Authority | United Kingdom Directives, All Aircraft | 16 November 2026 | 30 November 2026 |
| CAP 747 Mandatory Requirements for Airworthiness, Issue [Issue] | Generic Requirements and Concessions | 16 November 2026 | Each Amendment |
| Federal Aviation Administration, State of Design, Biweekly [Reference] | Piper and Cessna Airframes, Lycoming Engines, Sensenich and McCauley Propellers | 16 November 2026 | 30 November 2026 |
| European Union Aviation Safety Agency, State of Design | Robin and Grob Airframes | 16 November 2026 | 30 November 2026 |

- Corrected on 27 November 2026: the board gives CAP 747 as last checked 2 November 2026. Documentation, above, has CAP 747 checked 16 November 2026, and the sample follows that.
- By hand for 18 November 2026: 30 November is 12 days away, inside the lead time of 30 days, so the three are Due Soon.

## Work in Progress

- WP-2026-046, G-DGHI, stabilator trim cable rectification, 5 of 7 tasks closed.
- WP-2026-047, G-ABCD, landing light replacement, issued for 19 November 2026.
- WP-2026-048, G-EJKL, annual check and headset socket, draft, 1 to 4 December 2026.
- G-ABCD right main tyre replaced by the pilot-owner on 22 October 2026; the certificate of release to service must be in the records by 21 November 2026 (30 days, ML.A.305).
- WP-2026-043, G-CDEF, 100-hour check and spinner replacement, released 4 November 2026 by Chris Moore. WP-2026-047 also includes the engine oil and filter change.
- Planning: Bay 1 and Bay 2; December certifying staff 34% short before contracted cover; [Contract Engineer] is a contracted B1.2; [Maintenance Manager] and [Compliance Monitoring Manager] as people. Organisation fatigue limits: 10-hour shift, 11 hours' rest, 48 hours a week.
- WP-2026-046, G-DGHI. Sam Patel installed the trim cable. The contracted engineer is planned for rigging. Staff records show [Contract Engineer] had no certification authorisation at the sample date. The L2 engineer is contracted and supervised by Sam Patel. Five cards have work performed, and three are signed while two of the five await the whole-system inspection. Chris Moore is planned for that inspection on 19 November at 11:00. The seven work cards total 16.0 hours. One shared inspection adds 1.0 hour.
- WP-2026-048, G-EJKL. Draft annual check and right headset socket, 1 to 4 December, Bay 1, 32.0 hours. Its written order and applicable current instructions are outstanding. This draft is the initial live Work Packages sample.
- The Part-145 staffing example has 290 December certifying hours needed and 192 employed hours before cover. Booked contracted cover is 88 hours, conditional on authorisation for its intended scope. The L2 maintenance support worker is contracted. The lowest November employed share on the illustrated maintenance shift is two of four on Wednesday 18 November.
- In the week of 16 November the illustrative maintenance roster has 122.5 onsite hours. The packages contribute 20.0 planned hours, including one hour of shared stabilator inspection. The organisation budgets 50.0 other hours.
- G-CDEF flies on a loan propeller fitted on WP-2026-043; its own propeller is at [Propeller Organisation] for overhaul, due back 25 November 2026.
- Stores: sealant shelf life ends 30 November 2026; G-FMNO owner-supplied alternator quarantined as a suspected unapproved part, reported to the Civil Aviation Authority 7 November 2026; first trim cable for G-DGHI returned 15 November (not eligible), eligible cable received 16 November; [Oil Supplier] engine oil batch rejected 28 October 2026 (no certificate of conformity), so the supplier is suspended.
- Stores roles: Chris Moore makes unserviceable decisions and is the named person for unsalvageable disposal; Chris Moore and Sam Patel do receiving inspections and hold quarantine store access.
- Open defects: G-DGHI trim cable (grounded since 14 November); G-ABCD left landing light (deferred to 3 December); G-BXYZ cabin entry step (deferred to 27 November); G-EJKL right headset socket (deferred to 12 December).
- Occurrence reports: OR-2026-003 G-FMNO suspected unapproved part (closed); OR-2026-002 G-DGHI trim cable (follow-up due); OR-2026-001 G-BXYZ fuel contamination (closed).

## Defects

Added on 27 November 2026 for the Defects and Repeat Defects boards (Phase 1 of the canvas build). The four open defects and the two closed ones are the boards'. The days marked Made Up, the chapters and the three earlier defects are made up for the sample and are to be confirmed by Alex King.

| Aircraft Registration | Defect | Found | System | Decision | Decided By | Limit | Closed |
|---|---|---|---|---|---|---|---|
| G-DGHI | Stabilator Trim Cable Frayed at Pulley, Trim Check | 14 November 2026 | Chapter 27, Flight Controls | Not Deferrable, 14 November 2026 | Chris Moore | Grounded | |
| G-ABCD | Left Landing Light Inoperative, Placarded, Daylight Only | 3 November 2026 | Chapter 33, Lights | Deferred, 3 November 2026 | Pilot-in-Command | 3 December 2026 | |
| G-BXYZ | Cabin Entry Step Loose, No Effect on Flight, Step Out of Use | 28 October 2026 | Chapter 53, Fuselage (Made Up) | Deferred, 28 October 2026 | Sam Patel | 27 November 2026 | |
| G-EJKL | Right Headset Socket Crackle, Left Socket Serviceable | 12 November 2026 | Chapter 23, Communications | Deferred, 12 November 2026 | Pilot-in-Command | 12 December 2026 | |
| G-ABCD | Right Main Tyre Worn to Limit | 22 October 2026 | Chapter 32, Landing Gear (Made Up) | Not Deferrable, 22 October 2026 | | | 22 October 2026, Tyre Replaced, Pilot-Owner Maintenance |
| G-CDEF | Propeller Spinner Crack | 2 November 2026 | Chapter 61, Propeller | Not Deferrable, 2 November 2026 | Chris Moore | | 4 November 2026, Spinner Replaced |
| G-ABCD | Landing Light Inoperative | 10 February 2026 (Made Up) | Chapter 33, Lights | Deferred, 10 February 2026 | Pilot-in-Command | 12 March 2026 | 12 February 2026, Lamp Replaced (Made Up) |
| G-DGHI | Landing Light Inoperative | 16 June 2026 (Made Up) | Chapter 33, Lights | Deferred, 16 June 2026 | Pilot-in-Command | 16 July 2026 | 19 June 2026, Lamp Replaced (Made Up) |
| G-DGHI | Stabilator Trim Cable Wear | 9 December 2025 (Made Up) | Chapter 27, Flight Controls | Deferred, 9 December 2025 | Chris Moore | 8 January 2026 | 16 December 2025, Cable Tension Adjusted (Made Up) |

- In these cases identification and decision share a date. Add the organisation's default 30 days to that date: 3 November to 3 December 2026 (15 days from 18 November), 28 October to 27 November 2026 (9 days), 12 November to 12 December 2026 (24 days).
- Repeat defects in the 12 months from 19 November 2025 to 18 November 2026: Piper PA-28 Series (Lycoming), Chapter 33, 3 (G-ABCD February and November, G-DGHI June), action Add Lamp Holder Check to 50-Hour Check; Chapter 27, 2 (G-DGHI December 2025 and November 2026), action Pulley Alignment, WP-2026-046; Cessna 152, Chapter 23, 1; Robin DR 400, Chapter 61, 1.
- Contradictions between boards, corrected here: the Repeat Defects board leaves out G-BXYZ's step and G-ABCD's tyre, which the Defects board shows; by the rule they are one each (Cessna 172, Chapter 53; Piper PA-28, Chapter 32) and the page shows them. The Defects board gives G-EJKL's socket, at 24 days, no amber dot while the Home board gives it one: with a lead time of 30 days it is Due Soon. The Repeat Defects board dates the spinner crack November; the Components board says 2 November 2026.
- The work package beside each defect on the board (WP-2026-046, WP-2026-047, Not Planned, With Airworthiness Review) is not recorded until work packages are built (Phase 3).

## Contracts

Added on 27 November 2026 for the Contracts board (Phase 1 of the canvas build).

| Aircraft Registration | Owner | Tasks Contracted | Signed | Status |
|---|---|---|---|---|
| G-BXYZ | [Syndicate Name G-BXYZ] | All Continuing Airworthiness Management Tasks | 15 January 2025 | Active |
| G-CDEF | [Syndicate Name G-CDEF] | All Continuing Airworthiness Management Tasks | 8 April 2024 | Active |
| G-DGHI | [Flying Club Name] | All Continuing Airworthiness Management Tasks | 4 March 2025 | Active |
| G-HKLM | [Owner Name G-HKLM] | All Continuing Airworthiness Management Tasks | 9 November 2026 | Records Transfer, 14 of 18 Received |
| G-ABCD | [Owner Name G-ABCD] | Maintenance Programme Review and Airworthiness Review | 2 March 2026 | Active |

| Aircraft Registration | Work Ordered | Ordered By | Agreed |
|---|---|---|---|
| G-ABCD | Landing Light Replacement | [Owner Name G-ABCD] | 12 November 2026 |
| G-DGHI | Stabilator Trim Cable Rectification | Continuing Airworthiness Manager | 14 November 2026 |
| G-FMNO | 50-Hour Check | [Owner Name G-FMNO] | 16 November 2026 |

- G-EJKL and G-FMNO have no contract: work orders only. The board writes [Owner Name] and [Syndicate Name] for several owners; the customers are those named apart on 24 November 2026.
- Appendix I to Part-ML has a contract state the type of operation and the owner's address. The board shows neither: the sample writes [Type of Operation] and [Owner Address G-BXYZ] and so on.
- The work package beside each work order on the board is not recorded until work packages are built (Phase 3).

## Release to Service

Added on 27 November 2026 for the Release to Service board (Phase 1 of the canvas build).

| Aircraft Registration | Maintenance | Issued By | Completed | In Records |
|---|---|---|---|---|
| G-CDEF | 100-Hour Check, WP-2026-043 | Chris Moore, Certifying Staff, UK.CAO.[Number] | 4 November 2026 | 5 November 2026 |
| G-CDEF | Propeller Spinner Replaced, WP-2026-043 | Chris Moore, Certifying Staff, UK.CAO.[Number] | 4 November 2026 | 5 November 2026 |
| G-ABCD | Right Main Tyre Replaced, Pilot-Owner Maintenance | [Owner Name G-ABCD], Pilot-Owner | 22 October 2026 | Due 21 November 2026 |

- The two pieces of work on G-CDEF are recorded at 7,715.0 airframe hours, made up: below the 7,720.0 of its review on 11 November 2026. Their certificate reference is written [Release Reference WP-2026-043].
- The organisation was told of the tyre on 23 October 2026, as the board has it. No certificate is recorded for it yet, so the board's Licence [Number] is not in the sample.
- By hand for 18 November 2026: 2 issued in the last 30 days (4 November is 14 days ago), 1 not yet in the records, 0 incomplete maintenance, 0 pilot-owner notices overdue.

## Components

Added on 27 November 2026 for the Components board (Phase 1 of the canvas build). The components are the board's. Every value marked Made Up, and every day and airframe figure of a fitting, is made up so that the hours since new or overhaul are the board's on 18 November 2026, and is to be confirmed by Alex King.

| Component | Fitted To | Position | Limit | Fitted | Airframe Hours When Fitted | Hours When Fitted | New or Last Overhauled |
|---|---|---|---|---|---|---|---|
| Propeller, Fixed Pitch, [Serial Number Propeller G-CDEF] | Off-Wing, From G-CDEF | Propeller | 2,000 Hours or 72 Months, Manufacturer Recommendation | 2 November 2020 (Made Up) | 6,319.5 | 16.5 (Made Up) | 2 November 2020 (Made Up) |
| Propeller, Fixed Pitch, on Loan, [Serial Number Loan Propeller] | G-CDEF | Propeller | No Limit Recorded | 4 November 2026 | 7,715.0 | 0.0 (Made Up) | |
| Engine, Lycoming O-360, [Serial Number Engine G-DGHI] | G-DGHI | Engine | On Condition, Reviewed Every 100 Hours, Last at 9,800.0 on 20 October 2026 (Made Up) | 4 June 2018 (Made Up) | 7,734.3 | 0.0 | 4 June 2018 (Made Up) |
| Emergency Locator Transmitter Battery | G-ABCD | Emergency Locator Transmitter | Battery Date, 28 February 2027 (Day Made Up) | 14 February 2022 (Day Made Up) | 5,890.0 (Made Up) | 0.0 | |
| Fire Extinguisher | G-BXYZ | Cabin (Made Up) | Label Inspection Date, 31 March 2027 (Day Made Up) | 1 April 2022 (Made Up) | 2,950.0 (Made Up) | 0.0 | |
| Engine, Lycoming O-360, [Serial Number Engine G-CDEF] | G-CDEF | Engine | 2,000 Hours, Manufacturer Recommendation | 12 March 2019 | 5,951.5 | 0.0 | 12 March 2019 |
| Vacuum Pump | G-ABCD | Engine | 500 Hours, Manufacturer Recommendation | 6 April 2026 (Made Up) | 6,230.6 | 0.0 | 6 April 2026 (Made Up) |

- By hand for 18 November 2026. G-CDEF engine: 7,731.5 less 5,951.5 is 1,780.0 hours; 220.0 remain; at 0.6 hours a day, 366 days. Vacuum pump: 6,412.6 less 6,230.6 is 182.0; 318.0 remain; at 0.8 hours a day, 397 days. G-DGHI engine: 9,874.3 less 7,734.3 is 2,140.0; review at 9,900.0, 25.7 hours remain. Battery: 102 days. Fire extinguisher: 133 days.
- G-CDEF's own propeller was removed at its 6-year limit on 2 November 2026 at 7,715.0 airframe hours, taken as the hours of WP-2026-043 two days later: 16.5 and 7,715.0 less 6,319.5 is the board's 1,412.0 hours since overhaul. It is at [Propeller Organisation], due back 25 November 2026, 7 days. The 16.5 hours it is taken to have had when fitted are made up so that the board's 6,319.5 and 1,412 both hold.
- The loan propeller's limit is not in the sample, so none is recorded.
- Counts with the full sample: 9 tracked, 1 off-wing, 1 on condition, 4 due in 6 months (the G-DGHI engine at 0.8 hours a day, the battery, the fire extinguisher and G-HKLM’s propeller with an unknown calendar limit). The board's 38 Tracked and its 3 Months and 4 Months are not taken: day counts are exact.
- The board writes the limits of the battery and the fire extinguisher as February 2027 and March 2027; the last day of each month is taken.

## Modifications and Repairs

Added on 27 November 2026 for the Modifications board (Phase 1 of the canvas build). The days marked Made Up, the days sent and the data of ML.A.304 are made up for the sample and are to be confirmed by Alex King.

| Aircraft Registration | Bulletin | Classification | Sent to the Owner | Owner Decision | Recorded |
|---|---|---|---|---|---|
| G-ABCD | Seat Rail and Stop Inspection | Recommended | 16 February 2026 (Made Up) | Accepted, Every 50-Hour Check | 2 March 2026 |
| G-ABCD | Engine Valve Guide Inspection | Recommended | 16 February 2026 (Made Up) | Accepted, Every 100-Hour Check | 2 March 2026 |
| G-BXYZ | Alternator Mounting Bracket Inspection | Recommended | 10 November 2026 | Awaiting Owner | Reminder 24 November 2026 |
| G-EJKL | Seat Belt Replacement | Optional | 20 May 2026 (Made Up) | Declined, Belts On Condition, Annual Check | 6 June 2026 |

| Aircraft Registration | Change or Repair | Approval Route | Data | Mass Effect | Embodied |
|---|---|---|---|---|---|
| G-BXYZ | Panel-Mounted Navigator | Standard Change | Requirements of Point 21.A.90B | +1.2 Kilograms | 12 October 2026 (Day Made Up) |
| G-FMNO | Light-Emitting Diode Landing Light | Minor Change | Approved by a Design Organisation (Made Up) | 0.3 Kilograms Lighter | 14 April 2026 (Day Made Up) |
| G-DGHI | Left Wingtip Repair, Hangar Damage | Manufacturer's Structural Repair Data | Approved by a Design Organisation (Made Up) | 0.0 Kilograms | 18 July 2025 (Day Made Up) |
| G-ABCD | Mode S Transponder with Position Output | Standard Change | Requirements of Point 21.A.90B | +0.4 Kilograms | 10 May 2022 (Day Made Up) |
| G-CDEF | Propeller Overhaul | Maintenance, Same Part Number | | 0.0 Kilograms | In Progress |

## Weight and Balance

Added on 27 November 2026 for the Weighing board. The board gives a year, or a month, for each weighing; the days are made up. Each schedule is taken as issued on the day of the weighing, but for G-FMNO's.

| Aircraft Registration | Last Weighed | Schedule | Changes Since Weighing | Net Change | Weight and Balance |
|---|---|---|---|---|---|
| G-BXYZ | 14 June 2019 | Issue 6, 14 June 2019 | Panel-Mounted Navigator | +1.2 Kilograms | Weight Schedule Update |
| G-DGHI | 9 March 2017 | Issue 9, 9 March 2017 | Left Wingtip Repair, Hangar Damage | 0.0 Kilograms | Current |
| G-ABCD | 20 May 2022 | Issue 4, 20 May 2022 | None | 0.0 Kilograms | Current |
| G-CDEF | 3 September 2021 | Issue 3, 3 September 2021 | None | 0.0 Kilograms | Current |
| G-EJKL | 22 July 2020 | Issue 2, 22 July 2020 | None | 0.0 Kilograms | Current |
| G-FMNO | 5 April 2018 | Issue 5, 20 April 2026 | Light-Emitting Diode Landing Light | 0.3 Kilograms Lighter | Current |

- Corrected on 27 November 2026. The Weighing board gives G-DGHI 3 Changes, All Scheduled, +4.1 Kilograms and Reweigh, Over [Threshold] Threshold. The Modifications board has one change for G-DGHI, the wingtip repair, with no mass effect. The sample follows the Modifications board: one change, 0.0 Kilograms, Current.
- No reweigh threshold is set in the sample. It has no source and no default, so the page marks nothing for a reweigh.
- G-ABCD was weighed after its transponder was fitted, so nothing has changed since, as the board has it. G-CDEF's propeller overhaul is in progress and is not counted; the board lists it with 0 Kilograms.
- G-FMNO's landing light is in Issue 5 of its schedule, dated after the light was fitted: the board says Landing Light, Scheduled.

## Transfer In and Set Up Configuration, G-HKLM

Added on 27 November 2026 for the Transfers and Set Up Configuration boards. Every date and figure marked Made Up is to be confirmed by Alex King.

- The transfer started on 9 November 2026 and is 4 of 10 complete: Type Within Scope of Approval, Complete, Piper PA-38 Series (Lycoming); Management Contract, Complete, Signed 9 November 2026, [Owner Name G-HKLM]; Import Checks, Not Applicable, United Kingdom Register; Records Handover Plan, Complete, [Previous Organisation], Sent 12 November 2026; Records Received and Checked, In Progress, Engine Logbook Volume 1 Requested 13 November 2026, 14 of 18; Continuing Airworthiness Records Review, In Progress, Lucy Grant; Records Entered, Maintenance Programme, Bridging Check and Exposition Scope of Work, Open.
- 12 tracked positions, 8 recorded. Engine: Engine, Lycoming O-235 (chapter 72); Left Magneto and Right Magneto (74); Carburettor (73). Propeller: Propeller, Fixed Pitch (61). Airframe: Vacuum Pump (37); Emergency Locator Transmitter, its Battery and Fire Extinguisher (25); Mode S Transponder (34); Very High Frequency Radio, 8.33 Kilohertz (23); Landing Light (33). Not recorded: Right Magneto, Vacuum Pump, Emergency Locator Transmitter Battery, Fire Extinguisher.
- The board's template has 41 positions, 29 of them required equipment. Only the 12 tracked are named on the canvas, so only they are in the sample, and which are required equipment is not recorded.
- Major items: the engine, Lycoming O-235-L2C, with no limit recorded; the propeller, 2,000 Hours or 72 Months, Manufacturer Recommendation, with no overhaul date, so its calendar limit cannot be worked out. Both are taken as fitted on 2 May 2019 at 2,150.0 airframe hours (Made Up). G-HKLM has no airframe hours entered.
- Changes embodied: Mode S Transponder, Standard Change, 8 June 2021 (Made Up), and 8.33 Kilohertz Radio, Standard Change, 3 September 2018 (Made Up), each with a mass effect of 0.0 Kilograms (Made Up). The light-emitting diode landing light is fitted with no change recorded, so the Landing Light position needs a recorded change.
- By hand: 6 items open, the 4 positions not recorded, the landing light, and the propeller. The baseline is not signed.

## Management System

- Hazards: 7 open (2026-0001 to 2026-0007); Lucy Grant owns 2026-0004 (from the G-CDEF review on 11 November) and 2026-0005.
- Safety reports: SR-2026-011 to SR-2026-015, 1 to assess.
- Internal audit cycle 1 December 2025 to 30 November 2026: 8 of 10 audits complete.
- Findings: F01 airworthiness directives (closed); F02 G-EJKL certificate of release to service entered after 30 days (closed); F03 contracted maintenance (open, due 23 December 2026); F04 maintenance programmes (awaiting verification, due 2 December 2026); F05 safety risk management (open). Each is due 3 months from when it was raised.
- Actions: 9 (7 from hazards, 3 from findings, F03 also closes hazard 2026-0006).
- Placeholders: [Contracted Maintenance Organisation], [Independent Auditor].

## People

| Name | Role | Licence | Notes |
|---|---|---|---|
| [Accountable Manager] | Accountable Manager | | |
| Lucy Grant | Airworthiness Review Staff, Continuing Airworthiness | | Accepted 9 June 2023; last review 11 November 2026, G-CDEF |
| Chris Moore | Certifying Staff | Part-66 B1.2 | Current |
| Sam Patel | Certifying Staff | Part-66 B1.2 | Recurrent training due 6 December 2026 |
| [Name] | Airworthiness Review Staff | | Recency lapses 2 December 2026 |
| [Name] | Certifying Staff | Part-66 L2 | Lapsed, under 6 months in 2 years; ELA1 Aeroplanes, Wooden Structure |

| [Name] | Nominated Person, Continuing Airworthiness Manager | | |
| [Name] | Nominated Person, Maintenance Manager | | |
| [Name] | Support Staff, Planning and Records | | Joined 1 September 2026; initial safety training due 1 March 2027 |
| [Name] | Former Airworthiness Review Staff | | Left 30 June 2025 |

Reporting lines: the three managers report to the Accountable Manager. Continuing Airworthiness Manager: Lucy Grant and the review [Name]. Maintenance Manager: Chris Moore, Sam Patel, the L2 [Name], [Contract Engineer] (contracted B1.2, authorisation not yet issued, cover from December 2026), Ellie Ward and the planning and records [Name]. Compliance Monitoring Manager: [Independent Auditor] (contracted). The three managers are written as role placeholders: [Continuing Airworthiness Manager], [Maintenance Manager], [Compliance Monitoring Manager].

Employment: the Part-66 L2 [Name], [Contract Engineer] and [Independent Auditor] are Contracted; everyone else is Employed. Corrected 27 November 2026: this line said only the L2 [Name] was Contracted, against the reporting lines above and the Phase 2 corrections.

Added on 18 November 2026 for the review pages, to be confirmed by Alex King: Lucy Grant's review of G-BXYZ is taken as 2 August 2026, the day its certificate runs from, so that she is recent when she reviews G-CDEF on 11 November 2026. The other review staff member's last review is taken as 2 December 2025, from the lapse date of 2 December 2026. Each certificate in the Fleet table other than G-CDEF's is recorded as issued one year before its valid-to date, with a placeholder reference. G-CDEF's is the first certificate issued in the system: UK.CAO.[Number]-ARC-0001, at 7,720.0 airframe hours.

The tests of the review itself, added on 18 November 2026, take G-EJKL to be reviewed on 18 November 2026 by the other review staff member, who is taken not to be qualified under Part-66 and to be assisted at the survey. By hand: 18 days before 6 December 2026, so the new certificate is valid to 6 December 2027; copy to the Civil Aviation Authority by 28 November 2026; reference UK.CAO.[Number]-ARC-0002 at 11,206.8 airframe hours. This is a test case and not part of the sample; the manufacturer, designation, serial number and organisation address are placeholders.

Added on 19 November 2026 for the seed, to be confirmed by Alex King: the release for the directive inspection of G-ABCD on 20 July 2026 is taken to have gone into the records that day. The right main tyre of G-ABCD is taken to have been replaced by the pilot-owner on 22 October 2026 at 6,390.0 airframe hours, with its release not yet in the records.

Added on 19 November 2026, to be confirmed by Alex King: the certificates of G-DGHI, G-ABCD, G-BXYZ and G-FMNO from before these records are recorded as Lucy Grant's own, from the recency figures below. The sample does not say who issued the earlier certificates of G-EJKL (6 December 2025) and G-CDEF (2 December 2025); they stay recorded from the aircraft records.

Recency figures: experience in the last 2 years is Chris Moore 214 days, Sam Patel 176 days, L2 [Name] 61 days (last maintenance 14 August 2025). Lucy Grant has 5 reviews in 12 months (G-DGHI, G-ABCD, G-BXYZ, G-FMNO, G-CDEF). The lapsing review [Name] has 4 months of continuing airworthiness work; the G-EJKL review by 6 December 2026 keeps them current. Sam Patel’s last completed maintenance in the canvas example is fitting the stabilator trim cable on WP-2026-046. Chris Moore is scheduled to inspect it and has no completed work on that package. The test site seeds WP-2026-048 as its editable planning example. This line is the Recency board's and contradicts the Phase 3 sample above, where Sam Patel installed the trim cable on WP-2026-046 and Chris Moore is only planned for its inspection. WP-2026-046 is not seeded; the seed has only draft WP-2026-048. To be confirmed by Alex King, 27 November 2026.

| Ellie Ward | Mechanic, Trainee | Working toward Part-66 B1.2 | Joined 6 January 2025; on the job training for Cessna/Reims-Cessna 172/F172 Series (Lycoming) on G-BXYZ, 31 of 40 tasks; mentor Sam Patel, assessor Chris Moore |

Training: Sam Patel completed Human Factors on 6 December 2024 and renewal is due 6 December 2026, as shown on the Recurrent Training board. The seed uses [Training Certificate] as the evidence reference; the review [Name] has Human Factors overdue. Placeholders: [Part-147 Organisation], [Training Provider], [Previous Employer], [Base], [Job Card].

Roles are written in full: Continuing Airworthiness Manager, Compliance Monitoring Manager, Safety Manager, Maintenance Manager.

Added on 24 November 2026 for the person records, from the Staff board:

| Name | Role | Staff Group | Reports To | Employment | Licence | Sign-In |
|---|---|---|---|---|---|---|
| [Accountable Manager] | Accountable Manager | Management | | Employed | | Administrator |
| [Continuing Airworthiness Manager] | Continuing Airworthiness Manager | Management | Accountable Manager | Employed | | None |
| [Maintenance Manager] | Maintenance Manager | Management | Accountable Manager | Employed | | None |
| [Compliance Monitoring Manager] | Compliance Monitoring Manager | Management | Accountable Manager | Employed | | None |
| Lucy Grant | Airworthiness Review Staff | Airworthiness Review Staff | Continuing Airworthiness Manager | Employed | | Airworthiness Review Staff, Continuing Airworthiness Manager |
| [Review Name] | Airworthiness Review Staff | Airworthiness Review Staff | Continuing Airworthiness Manager | Employed | | Airworthiness Review Staff |
| [Planning and Records Name] | Planning and Records | Other Staff | Maintenance Manager | Employed | | Planning and Records |
| Chris Moore | Certifying Staff | Certifying Staff | Maintenance Manager | Employed | Part-66 B1.2 | None |
| Sam Patel | Certifying Staff | Certifying Staff | Maintenance Manager | Employed | Part-66 B1.2 | None |
| [Certifying Staff Name] | Certifying Staff | Certifying Staff | Maintenance Manager | Contracted | Part-66 L2 | None |
| [Contract Engineer] | Certifying Staff | Certifying Staff | Maintenance Manager | Contracted | Part-66 B1.2 | None |
| Ellie Ward | Mechanic, Trainee | Other Staff | Maintenance Manager | Employed | Working Toward Part-66 B1.2 | None |
| [Independent Auditor] | Auditor | Other Staff | Compliance Monitoring Manager | Contracted | | None |
| [Read Only Name] | | Other Staff | | Employed | | Read Only |
| [Former Review Name] | Airworthiness Review Staff | Airworthiness Review Staff | | Employed | | None |

- The board writes Lucy Grant's sign-in as that of the Continuing Airworthiness Manager's staff; in the system she holds the roles Airworthiness Review Staff and Continuing Airworthiness Manager, as recorded on 18 November 2026. The [Continuing Airworthiness Manager] of the board is a person with no sign-in.
- [Read Only Name] is a sign-in of the sample for the Read Only role. It is not a person of the table above this one.
- [Planning and Records Name] joined 1 September 2026. Ellie Ward joined 6 January 2025. [Former Review Name] left 30 June 2025; the record is kept until 30 June 2027 (CAO.A.045(e), 2 years).
- [Contract Engineer] is written here as Contracted with a Part-66 B1.2 licence, as the Staff board gives. Phase 2 settled the authorisation: none at the sample date (Phase 3 sample, above). The Work Packages board's "Authorised 11 November 2026" is not taken.

## Commercial

- Customers, named apart on 24 November 2026 so that one can be told from another, with the day each became a customer taken as the first of the month the Customers board gives: [Flying Club Name] (Flying Club, G-DGHI, 1 March 2025); [Owner Name G-EJKL] (Pilot-Owner, 1 December 2025); [Owner Name G-ABCD] (Pilot-Owner, 1 March 2026); [Syndicate Name G-BXYZ] (Syndicate of 6, 1 January 2025); [Owner Name G-FMNO] (Pilot-Owner, 1 May 2024); [Syndicate Name G-CDEF] (Syndicate of 4, 1 April 2024); [Owner Name G-HKLM] (Pilot-Owner, 1 November 2026).
- Customers: 7, one per aircraft. Contracts for G-BXYZ, G-CDEF, G-DGHI, G-HKLM (continuing airworthiness management) and G-ABCD (maintenance programme review and airworthiness review); G-EJKL and G-FMNO have none, work orders only.
- Enquiries: E-2026-036 [Prospective Customer], Robin DR 400 annual, to answer by 19 November; E-2026-035 G-EJKL (quoted); E-2026-034 G-FMNO (accepted); closed E-2026-033 G-DGHI, E-2026-032 G-ABCD, E-2026-031 G-HKLM, E-2026-029 turbine engine overhaul (declined, outside scope).
- Quotes: Q-2026-023 G-EJKL £1,860.00 awaiting acceptance; Q-2026-022 G-FMNO £420.00; Q-2026-021 G-DGHI £980.00; Q-2026-020 G-ABCD £315.00; Q-2026-019 G-CDEF £2,140.00 (invoiced).
- Invoices: INV-2026-0141 G-CDEF £2,140.00 due 5 December; INV-2026-0140 G-BXYZ and INV-2026-0139 G-DGHI quarterly management fees £360.00 (paid); INV-2026-0137 G-FMNO £185.00, 14 days overdue.

## Suppliers

[Parts Distributor], [Engine Overhaul Organisation], [Propeller Organisation], [Calibration Laboratory], [Oil Supplier] (suspended). The Suppliers board shows the illustrative Part-CAO evaluations dated 18 November 2026. The propeller organisation has a next evaluation of 30 November 2026. The oil supplier retains the missing conformity evidence with its suspension and has no next evaluation date in the sample.


## Goods In

Five representative Receiving Inspection board entries are seeded. On 18 November the ELT battery has the supplier and release-document checks recorded and is Awaiting Inspection. The ineligible G-DGHI trim cable is returned on 15 November and its replacement is accepted into Stores on 16 November and creates a linked stock entry with its sample CAA Form 1 reference. The owner-supplied G-FMNO alternator is quarantined on 6 November and references a separate sample authority report dated 7 November. The oil without conformity evidence is inspected on 28 October and returned on 29 October. The delivery-line and receiving-inspector authorisation references are illustrative.

## Tools and Equipment

The marked Part-CAO sample uses fictitious Hangar delegations for Lucy Grant. Grease Gun 0201 has the board's 3 August 2026 service evidence and six-month interval, giving 3 February 2027. Jack 0210 is segregated with a leaking seal and a 12-month service control. Its service completion is missing. Jack Point Adapter 0301 shows inspection before each use.

0142 keeps the board's September despatch and use conflict, uncertain suitability of 0143 for the G-ABCD recheck, and the missing evidence for the G-FMNO no-effect claim. The historical certificate and acceptance still need verification. The propeller balancing kit shows occasional access through [Propeller Organisation] and **Control basis to verify**, with its interval and date blank. The synthetic due-date, calibration and affected-work scenarios are test-only evidence.
