# Contributing

How changes reach `main`. The same steps apply to code, requirements and assurance documents.

## The Workflow

1. **Issue.** Every change starts from a GitHub Issue. The Issue says what is needed and carries one label: `requirement`, `hazard`, `defect`, `security`, `decision` or `backlog`.
2. **Branch.** A branch is a private copy of the repository where work happens without touching `main`. Name it after the work: `step-2-assurance-plan`, `req-014-next-due`, `defect-31-day-count`.
3. **Commit.** A commit is one saved, described change. Keep each one small enough to review in a few minutes.
4. **Pull request.** A pull request asks for the branch to be merged into `main`. It shows every changed line and runs the automated checks.
5. **Review.** Alex reviews and approves. Calculation modules also need the independent recompute described in the working brief (Step 6).
6. **Merge.** Only when the checks pass and the review is approved. `main` is protected: nothing is pushed to it directly.

## Rules for Every Pull Request

- A change in behaviour updates `requirements/traceability.csv` in the same pull request.
- A new or changed regulatory claim carries its reference (for example ML.A.305, AMC1 CAO.A.025, CAP 562 C-90). A claim with no source is marked `To Be Checked`, never guessed.
- A new hazard, or a change to a mitigation, updates `assurance/hazard-log.md`.
- A product, interface or regulation decision is added to `design-system/Decisions.md`. An architecture decision gets a record in `architecture/decisions/`.
- Tests use the sample organisation and fleet in `design-system/SampleData.md`. Today in the sample world is 18 November 2026.
- Nothing is deleted from records, in the product or in this repository's record documents. Superseded entries stay and are marked superseded.

## Never Commit

- Secrets: passwords, tokens, keys, `.env` files. Secrets live in the environment of the server only.
- Regulatory source documents (PDF). Fetch them from the Civil Aviation Authority.
- Real aircraft, customer or personal records. Fixtures use the sample data only.

## Commit Messages

One line, imperative mood, 72 characters or fewer, saying what the change does:

```
Add next-due calculation for hours and calendar intervals

REQ-014, REQ-015. Whichever comes first governs (ML.A.302).
```

- First line: what changes. Start with a verb: Add, Fix, Change, Remove, Record.
- Body, when needed: why, with the requirement, hazard or Issue identifiers.
- One purpose per commit. A fix and an unrelated tidy-up are two commits.

## Writing

Documents and interface text follow `design-system/Writing.md`: British English, nothing abbreviated except regulatory identifiers, no marketing copy.
