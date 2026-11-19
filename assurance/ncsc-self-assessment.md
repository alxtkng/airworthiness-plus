# NCSC Software Security Code of Practice: Self-Assessment

Source: Software Security Code of Practice, Department for Science, Innovation and Technology and the National Cyber Security Centre, published May 2025, GOV.UK page last updated 15 January 2026. 14 principles in 4 themes. The principles below are summarised; the Code has the authoritative wording.

https://www.gov.uk/government/publications/software-security-code-of-practice/software-security-code-of-practice

Senior Responsible Owner: Alex King, founder, Airworthiness Limited.

Assessed: 18 November 2026, start of private beta, before any product code. Assessed again: 19 November 2026, for the readiness review, with the private beta slice built and not yet deployed.

State is one of: Not Started, In Progress, Met. A principle is Met only when its evidence exists and can be opened.

## Theme 1. Secure Design and Development

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 1.1 | Follow an established secure development framework | Met. NIST SP 800-218 adopted. Every change goes through a pull request with tests, type checks, lint, a dependency scan, a secret scan and an image build; `main` is protected, administrators included | `CONTRIBUTING.md`; `.github/workflows/checks.yml`; branch protection rule on `main`, read 19 November 2026 |
| 1.2 | Know what the software is made of and assess the risk of third-party components | Met. Four runtime dependencies, pinned with hashes; the base image pinned by digest; the font files recorded with checksums and licence; a scan and a bill of materials on every build and each Monday | `pyproject.toml`; `uv.lock`; `Dockerfile`; `architecture/decisions/ADR-0001-stack.md`; pipeline artefact software-bill-of-materials |
| 1.3 | Have a clear process for testing software and updates before distribution | Met. 657 tests on every change, ten of them in a real browser; an independent review of the code of 19 November 2026, with every finding fixed (`assurance/independent-verification/code-review-2026-11-19.md`); golden cases worked by hand; property tests; independent recompute of each calculation; tests over every address | `tests/`; `assurance/independent-verification/`; `assurance/dogfooding.md`; `assurance/assurance-case.md` C1 |
| 1.4 | Secure by design and secure by default through the lifecycle | In Progress. The design rules are built and tested: history that cannot be altered, separation of organisations in the database, serials from the server. The threat model is written and reviewed. OWASP ASVS 5.0 Level 2 is assessed and not yet met in full | `architecture/threat-model.md`; `assurance/asvs.md`; `assurance/hazard-log.md`; `architecture/decisions/ADR-0002-data-layer.md` |

## Theme 2. Build Environment Security

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 2.1 | Protect the build environment against unauthorised access | In Progress. The repository is public and can be changed only through a protected `main`. Two-factor sign-in on the GitHub account, and who can reach the server, are not confirmed in the record: both are for Alex King to state | `operations/keys-and-secrets.md`. To come: Alex King's confirmation |
| 2.2 | Control and log changes to the build environment | Met. Pipeline configuration is in the repository and changes only by pull request; actions pinned to commits. `main` protected since 18 November 2026: pull request required, checks must pass, no force push, no deletion, administrators included | `.github/workflows/checks.yml`; branch protection rule on `main`. Who can change the repository's settings: Alex King alone |

## Theme 3. Secure Deployment and Maintenance

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 3.1 | Distribute software securely to customers | In Progress. The service is built as an image from the lock file by the pipeline, and its deployment over HTTPS is written and rehearsed. It is not yet deployed | `Dockerfile`; `operations/deployment.md` |
| 3.2 | Implement and publish an effective vulnerability disclosure process | Met. Process and contact published; the repository is public; GitHub private vulnerability reporting is on, read 19 November 2026 | `SECURITY.md`; `operations/vulnerability-management.md` |
| 3.3 | Have processes for proactively detecting, prioritising and managing vulnerabilities in components | In Progress. A scan on every change and each Monday; severities and times to fix are written. GitHub's dependency alerts, secret scanning and push protection are off: for Alex King to switch on. Updates to the server's operating system have no owner written down | `.github/workflows/checks.yml`; `operations/vulnerability-management.md` |
| 3.4 | Report vulnerabilities to relevant parties where appropriate | In Progress. Written: who is told and when. Not yet used | `operations/vulnerability-management.md`, Telling People |
| 3.5 | Provide timely security updates, patches and notifications to customers | In Progress. Times to fix are written. No customers in private beta | `operations/vulnerability-management.md`; `operations/contracts/service-level-draft.md` |

## Theme 4. Communication with Customers

| Principle | Summary | Current State | Evidence Location |
|---|---|---|---|
| 4.1 | Tell the customer the level of support and maintenance provided | In Progress. Drafted for a solicitor; no customers in private beta | `operations/contracts/service-level-draft.md` |
| 4.2 | Give at least 1 year's notice before support or maintenance ends | In Progress. In the draft service level; what a customer takes with it is written | `operations/contracts/service-level-draft.md`; `operations/contracts/data-export-on-exit.md` |
| 4.3 | Tell customers about notable incidents that may significantly affect them | In Progress. Written; not yet walked through | `operations/incident-response.md` |

## Summary

| State | Count |
|---|---|
| Met | 5 |
| In Progress | 9 |
| Not Started | 0 |

Updated in every pull request that adds evidence. Completion is an exit condition for private beta (`assurance/readiness-review.md`). It is not complete: nine principles are In Progress, most of them because nothing is deployed and there are no customers yet.
