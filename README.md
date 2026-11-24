# Airworthiness+

Continuing airworthiness web app for United Kingdom owners, operators, Part-CAO, Part-CAMO and Part-145 organisations and licensed engineers.

- `canvas/`: the design canvas pages, in the Claude Design format (`.dc.html`), and the canvas layout. They render in the Design editor, not as plain web pages.
- `design-system/`: the project record. Read `Decisions.md` and `SampleData.md` before any change. `Procedures.md` lists every exposition procedure by approval.
- `scripts/`: the generators that build the canvas pages and the Marketplace data.
- `data/`: the Marketplace data from the Civil Aviation Authority approved organisations lists, with Companies House matches.
- `research/`: reading notes on UK Regulation (EU) No 1321/2014, CAP 562 and document control systems.

Regulatory source documents are not stored here; fetch them from the Civil Aviation Authority.

## Private Beta

The project follows the UK Government Service Manual phases. Discovery and alpha are finished. Private beta is the current phase: the first real version is built and verified, and used internally only. No customer data enters the system in this phase.

Scope is one slice, the Part-CAO core loop for Part-ML aircraft: Organisation and Access, Aircraft, Maintenance Programme, Airworthiness Directives, Maintenance Data, Airworthiness Review, Records. Everything else in the canvas is backlog, to be built in the order of `prompts/canvas-build.md`.

| Folder | Holds |
|---|---|
| `prompts/private-beta.md` | The working brief for this phase |
| `prompts/private-beta-continuation.md` | Where the work stands and how to carry on, for a new session |
| `assurance/` | Assurance case, hazard log, NCSC Software Security Code of Practice self-assessment, readiness review |
| `requirements/` | Numbered requirements and the traceability matrix |
| `architecture/` | Architecture Decision Records and the threat model |
| `operations/` | Backup and restore, monitoring, incident response, data protection |

Rules for this phase:

- The regulation is the requirements specification. Every requirement cites its source.
- Every requirement traces to a test. A requirement with no test is a visible gap in `requirements/traceability.csv`.
- Changes reach `main` only by pull request with passing checks. See `CONTRIBUTING.md`.
- Vulnerabilities are reported as set out in `SECURITY.md`.
- The code is licensed under the GNU Affero General Public License version 3 only (AGPL-3.0-only), copyright Airworthiness Limited. See `LICENSE`. The sample data, design system and research notes are covered by the same licence unless a file says otherwise. The licence for the open data standard is not yet chosen.
- Public beta does not start until `assurance/readiness-review.md` is signed off by Alex King.
