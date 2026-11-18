# Airworthiness+

Continuing airworthiness web app for United Kingdom owners, operators, Part-CAO, Part-CAMO and Part-145 organisations and licensed engineers.

- `canvas/`: the design canvas pages, in the Claude Design format (`.dc.html`), and the canvas layout. They render in the Design editor, not as plain web pages.
- `design-system/`: the project record. Read `Decisions.md` and `SampleData.md` before any change. `Procedures.md` lists every exposition procedure by approval.
- `scripts/`: the generators that build the canvas pages and the Marketplace data.
- `data/`: the Marketplace data from the Civil Aviation Authority approved organisations lists, with Companies House matches.
- `research/`: reading notes on UK Regulation (EU) No 1321/2014, CAP 562 and document control systems.

Regulatory source documents are not stored here; fetch them from the Civil Aviation Authority.
