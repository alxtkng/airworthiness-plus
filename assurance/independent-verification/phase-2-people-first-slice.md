# Independent review of the first Phase 2 People changes

27 November 2026. A separate reviewer inspected the Organisation Chart, maintenance authorisation records, Recency tab and work attribution against main at 1394296. This inspection covers the first slice. It leaves the phase-wide review and independent recompute open.

| Finding | Resolution |
|---|---|
| Work attribution could use a person’s employment dates from a stale form read | Reload and lock the performer during validation. The database checks the dates when it captures the performer’s name. |
| Concurrent staff edits could form a cycle, which the chart would omit | Serialise reporting-line edits on the organisation and start the validation from the current manager record. The chart lists unresolved reporting lines separately. |
| The new Recency tab labels the inclusive last eligible date as the lapse day | Use the existing Authorisations wording, After the displayed date. |
| Former certifying staff had no visible way to reach the historical authorisation form | Link the form from their Staff record. |
| The management table displayed a former manager as current | Apply the active-manager rule to the table as well as the tree. |
| The aircraft export’s people lookup omitted attributed performers | Include the people attributed to that aircraft’s work. The work retains the name at entry. |

Remaining Phase 2 scope includes training evidence on All Staff, review-staff authorisation scope and validity, maintenance experience assessment by qualifying scope and both duration routes, and checks that use those results at release and defect deferral.
