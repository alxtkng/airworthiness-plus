# Service Level: Draft

**Draft for a solicitor. Not legal advice. Not to be offered as it stands.** Every figure is Proposed and is Alex King's to confirm.

## What Is Honest to Promise Today

The service runs on one server and is operated by one person. A promise sized for a large provider would not be kept. These are the levels that can be.

| | Level | Reasoning |
|---|---|---|
| Hours of Support | Working days, 09:00 to 17:00 United Kingdom time | One person |
| Availability | No percentage is promised in beta. The aim is that the service is up during working hours | There is no second server to fail over to |
| Planned Maintenance | Outside working hours, with [2] working days' notice | |
| Recovery Time | The next working day after a failure is found | `backup-and-restore.md` |
| Recovery Point | No more than 24 hours of entries lost | Daily backup; 145.A.45(e) |
| Backup | Daily, encrypted, kept away from the server; a restore tested every 3 months and the result available to the customer | REQ-150 to REQ-153 |
| Response to a Fault Report | Acknowledged within 1 working day | |
| A Fault That Makes a Calculated Figure Wrong | Treated as the highest priority. Every organisation that could be affected is told the same working day it is confirmed, with which figures and since when | Hazard H-001. A wrong due date is the most serious thing the system can do |
| A Security Vulnerability | High severity fixed within 14 days, and at once if being used | `vulnerability-management.md` |
| Notice of a Personal Data Breach | Within [24] hours of becoming aware | Data processing agreement, clause 8 |
| Export | The customer can export all its records itself at any time, with no request to us | REQ-134, REQ-135 |

## What the Customer Does

- Keeps its source documents, so that a day's entries can be made again after a restore.
- Works from its last export and its paper records while the service is down. The system does not replace the organisation's responsibility for its records (CAO.A.090).
- Manages its own users, and has two Administrators.
- Reports faults, and records them in its Problem Log.

## What Is Not Promised

- That the system's figures are right without the organisation's own check. Each figure shows how it was calculated so that it can be checked.
- Acceptance by the Civil Aviation Authority. Each organisation obtains its own.
- Any level for a service the customer has not paid for. [For the solicitor: beta terms.]

## If a Level Is Missed

[For the solicitor. In beta, no service credits are proposed; the remedy is the right to leave with a full export.]
