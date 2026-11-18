# NCSC Software Security Code of Practice: Self-Assessment

Source: Software Security Code of Practice, Department for Science, Innovation and Technology and the National Cyber Security Centre, published May 2025, GOV.UK page last updated 15 January 2026. 14 principles in 4 themes. The principles below are summarised; the Code has the authoritative wording.

https://www.gov.uk/government/publications/software-security-code-of-practice/software-security-code-of-practice

Senior Responsible Owner: Alex King, founder, Airworthiness Limited.

Assessed: 18 November 2026, start of private beta. No product code exists yet.

State is one of: Not Started, In Progress, Met. A principle is Met only when its evidence exists and can be opened.

## Theme 1. Secure Design and Development

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 1.1 | Follow an established secure development framework | In Progress. NIST SP 800-218 adopted. Workflow written. Checks run on every pull request. `main` is protected | `CONTRIBUTING.md`; `.github/workflows/checks.yml`; branch protection rule on `main` |
| 1.2 | Know what the software is made of and assess the risk of third-party components | In Progress. Dependencies pinned with hashes in the lock file; vulnerability scan and software bill of materials on every build | `pyproject.toml`; `uv.lock`; `architecture/decisions/ADR-0001-stack.md`; pipeline artefact software-bill-of-materials |
| 1.3 | Have a clear process for testing software and updates before distribution | In Progress. Test-first approach, golden cases and independent recompute defined | `prompts/private-beta.md` Step 6; `assurance/assurance-case.md` C1. To come: test suite and results |
| 1.4 | Secure by design and secure by default through the lifecycle | In Progress. Non-negotiable design rules set: append-only history, data-layer organisation scoping, server-allocated serials | `prompts/private-beta.md` Step 4; `assurance/hazard-log.md`. To come: `architecture/threat-model.md`, `assurance/asvs.md` |

## Theme 2. Build Environment Security

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 2.1 | Protect the build environment against unauthorised access | Not Started. Repository is private. Two-factor authentication on the GitHub account and access to the Coolify server not yet confirmed | To come: record of account and server access controls in `operations/` |
| 2.2 | Control and log changes to the build environment | In Progress. Pipeline configuration is in the repository and changes only by pull request; actions pinned to commits. `main` protected since 18 November 2026: pull request required, checks must pass, no force push, no deletion, administrators included | `.github/workflows/checks.yml`; branch protection rule on `main`. To come: record of who can change repository settings |

## Theme 3. Secure Deployment and Maintenance

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 3.1 | Distribute software securely to customers | Not Started. Nothing is distributed in private beta. The service will be delivered over HTTPS from airworthiness.co | To come: deployment record in `operations/` |
| 3.2 | Implement and publish an effective vulnerability disclosure process | In Progress. Process and contact (contact@airworthiness.co) published; repository public since 18 November 2026 | `SECURITY.md`. To come: GitHub private vulnerability reporting switched on |
| 3.3 | Have processes for proactively detecting, prioritising and managing vulnerabilities in components | In Progress. Dependency vulnerability scan on every pull request and push to `main` | `.github/workflows/checks.yml`. To come: scheduled scan; `operations/vulnerability-management.md` |
| 3.4 | Report vulnerabilities to relevant parties where appropriate | Not Started | To come: `operations/vulnerability-management.md` |
| 3.5 | Provide timely security updates, patches and notifications to customers | Not Started. No customers in private beta | To come: `operations/vulnerability-management.md`; service level document |

## Theme 4. Communication with Customers

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 4.1 | Tell the customer the level of support and maintenance provided | Not Started. No customers in private beta | To come: service level document (readiness review, contract documents) |
| 4.2 | Give at least 1 year's notice before support or maintenance ends | Not Started | To come: service level document; data export on exit document |
| 4.3 | Tell customers about notable incidents that may significantly affect them | Not Started | To come: `operations/incident-response.md` |

## Summary

| State | Count |
|---|---|
| Met | 0 |
| In Progress | 7 |
| Not Started | 7 |

Updated in every pull request that adds evidence. Completion is an exit condition for private beta (`assurance/readiness-review.md`).
