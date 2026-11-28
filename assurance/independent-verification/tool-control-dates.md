# Independent verification of tool control dates

28 November 2026. A separate reviewer recomputed these cases from the five canvas boards, the reviewed design handoff and the CAA sources, without seeing the implementation or its tests. These checks establish expected results for REQ-362.

| Source evidence | Worked result |
| --- | --- |
| Grease Gun 0201, service 3 August 2026, six months | February is six months after August. The third exists, so due 3 February 2027. |
| Torque Wrench 0142, 14 September 2026, six months | Due 14 March 2027 in the supported test case. Acceptance on 16 September and the two passing interim checks on 14 October and 13 November leave the anchor unchanged. |
| Jack 0210, 12-month service control and leaking seal | The board supplies no service completion. Leave the date blank. 25 November is the seal-kit ETA. |
| Jack Point Adapter 0301 | Inspection before each use. There is no calendar deadline. |
| January and February boundaries | 31 January 2027 +1 month gives 28 February. +2 months directly gives 31 March. A fresh 28 February completion +1 month gives 28 March. 31 January 2028 +1 month gives 29 February. 29 February 2028 +12 months gives 28 February 2029. |
| UK due-day boundary | For 12 September 2026, 22:59:59 UTC falls on the due day and 23:00 UTC falls on 13 September, when the control is overdue. |

The calendar and inclusive due-day convention is local. The AMC describes labels and following manufacturer intervals or substantiating an alternative. [CAO.A.050](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/05830_CAOA050_Components_equipment_and_tools.htm) · [AMC 145.A.40(b)](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/02%20145/3%20AMC/AMC%20145%20A%2040%20b%20Equipment%20and%20tools.htm)

## 0142 case carried into the later workflows

The preceding known-good date was 12 September 2025. Twelve months gives 12 September 2026 inclusive, subject to actual label evidence. Include the start boundary and any issue overlapping the search bounds. C05 records despatch on 1 September 2026. G-ABCD's claimed use on the due day conflicts with physical custody if that despatch date is accurate. Search through the 14 September discovery while reconciling actual removal, historical label and missing evidence. The +5.2% as-found reading exceeds the sample +4% limit by 1.2 percentage points. The within-2% as-left result leaves historical impact open. PR 2 records the case and hold when it records the out-of-limits result. PR 4 investigates and can close the case with authorised evidence.

Verify whether 0143's 4–20 Nm range fits the G-ABCD recheck, confirm the applicable method and obtain signed work evidence. G-BXYZ's claimed 20 September re-torque needs the linked propeller logbook and any required follow-up. G-FMNO's no-effect claim still needs applicable independent evidence. In the synthetic test only, 30.0 ±0.2 Nm gives 29.8–30.2 Nm within 29–31 Nm. This calculation supplies no historical finding. [CAP 2375 Issue 04 §§2.4–2.6](https://www.caa.co.uk/publication/download/22229#page=59)
