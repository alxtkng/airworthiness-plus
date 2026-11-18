# Document control and "read and sign": EMOS (Jet2) and comparable systems

Research date: 18 Nov 2026. Labels used below:
- [CONFIRMED]: stated by the cited source.
- [INFERENCE]: my own reasoning, not stated by a source.
- [UNVERIFIED]: from background knowledge; I did not fetch a source for it.

---

## 1. "EMOS" at Jet2

**Result: not confirmed.** I found no public source that links a system called "EMOS" to Jet2.com or Jet2 plc. That covers searches for EMOS, eMOS, Jet2 manuals, read-and-sign and engineering.

The names that do have public evidence are below.

| Candidate | Evidence | Relevance |
|---|---|---|
| **EFOS** (Evoke Systems Ltd, UK) | [CONFIRMED] Jet2.com has used EFOS since 2006 "to support its Flight Operations, Engineering, and Ground Operations teams". Contract renewed 19 Nov 2024. https://aircraftit.com/news/evoke-celebrates-long-term-partnership-and-renewal-with-jet2-com | Most likely source of the name. "EFOS" and "EMOS" differ by one letter. |
| EFOS modules at Jet2 | [CONFIRMED] Jet2 uses EFOS Training Records (which helped it reach ATQP status) and the EFOS "Flight Management Journey Log" (2019). https://www.aircraftit.com/news/following-over-10-years-using-efos-jet2-signs-another-5-year-contract . Jet2 crew run "EFOS" and "EFOS WEB" on company iPads (EFB). https://support.crewlounge.aero/support/solutions/articles/24000071596-jet2-com-how-to-import-efos | Confirms that EFOS is Jet2's EFB and back-office platform. |
| **EFOS Documents** module | [CONFIRMED] Evoke sells "EFOS Documents" with "Read & Sign", "Version Control", "Distribution Groups", "Expiration Management", "overdue tasks" and "EFB Ready". https://www.evoke-systems.aero/products/efos-documents/ . A 2007 article describes EFOS managing operational, training and aircraft manuals with version control. It was meant to replace the paper forms pilots sign to confirm they have read documents. https://www.theregister.com/2007/07/17/evoke_electronic_flight_bag | Matches the brief's description of "EMOS" (manual library, read and sign, EFB). [INFERENCE] No source says Jet2 uses the EFOS Documents module itself. |
| **DocuNet** (Vistair, now Comply365) | [CONFIRMED] In 2014 Jet2 selected DocuNet "to control, manage, and distribute operation manuals" for its Boeing fleet. It delivers revisions to "crew and EFB platforms" and supports offline revision notes. https://comply365.com/2014-09-jet2-signs-new-docunet-contract/ | Jet2's flight-ops manual authoring and publishing tool, at least from 2014. Whether it is still in use is not known. |
| EMOS Information Systems Ltd | [CONFIRMED] A UK ID-card and print-management firm with no aviation link. https://www.emos.com/ | Rule out. |

**Conclusion [INFERENCE].** "EMOS" is most likely one of two things:
- a misremembering of **EFOS** (Evoke Systems, a vendor product, not in-house); or
- an internal Jet2 label, for example "Engineering Manuals / Maintenance Organisation System", that is not published anywhere.

If it is an internal name, it may sit on top of a vendor product such as EFOS Documents or DocuNet. Ask a Jet2 contact to confirm the name before you cite "EMOS" in product material.

---

## 2 and 3. How comparable systems name and structure the feature

| Product | Module / section name | Read-and-sign term | What it tracks | Exposition and read-and-sign under one heading? | Source |
|---|---|---|---|---|---|
| **Centrik** (TrustFlight) | "Documents Module". Tabs include "My Documents to Read". SmartDocs for authoring. | "Mark as Read". "read-and-sign" is used for distribution from SmartDocs. | Distribution to "Roles", Organisations and Departments. "Read On" date, due/overdue users, "Send Reminder to All", "Postpone all" with a new deadline and reason. SmartDocs produces "Records of Revision", "Summaries of Change" and "List of Effective Pages". | Yes. Authoring and approval (SmartDocs) publish into the Documents module, which handles distribution and read tracking. | https://helpdesk.trustflight.com/hc/en-gb/articles/16958857078941-Centrik-5-User-Guide-Documents-Module-Document-Tracking ; https://helpdesk.trustflight.com/hc/en-gb/articles/16772859925661-Centrik-5-User-Guide-Documents-Module-Overview-Mark-as-Read ; https://www.trustflight.com/smartdocs/ |
| **EFOS Documents** (Evoke) | "EFOS Documents" | "Read & Sign" | "Version Control", "Distribution Groups", "Expiration Management", overdue tasks, acknowledgement tracking | Yes, within one Documents module | https://www.evoke-systems.aero/products/efos-documents/ |
| **Web Manuals** (Web Manuals AB) | Platform modules: "Write and edit", "Reader and reviewer", "EFB App", "Compliance monitoring" | No "read and sign" label. Uses "Track who's read what", "Send Smart Reminders" and "Get the Full Picture" (reader reports). | "Role-Based Distribution", "Revision Tracking" and "Track Every Change" (revision bars), "Approval Workflow" (draft, review, final), offline via EFB | Manuals are grouped under "WEB MANUALS PLATFORM". Compliance monitoring sits under "AUTOMATE COMPLIANCE" in the top navigation, but both share one platform heading in the footer. | https://webmanuals.aero/product ; https://webmanuals.aero/product-tour/distribution ; https://webmanuals.aero/read-and-review |
| **Comply365** (includes ex-Vistair DocuNet) | "ContentManager365" (filed under "Operational Content Management"), "SafetyManager365", "TrainingManager365" | "read & sign" | "distribute updates", "Document distribution", "permission-controlled libraries", audit trails, "Offline-ready" | Yes. Content management includes read & sign. | https://comply365.com/mro/ |
| **Vistair CrewNet** (now Comply365) | "CrewNet – Crew Notices and Bulletins" | "digitally acknowledge receipt"; "Read & Receipt Compliance" | Mandatory notices and bulletins, real-time reports and dashboards | No. Notices are a separate product from manuals (DocuNet). | https://www.aircraftit.com/vendors/vistair-systems/crewnet |
| **Ideagen Q-Pulse** | Document module, "Workload / My Actions" | "acknowledge", with the instruction "make sure that you have read and understood" first | Document owner, "copyholders", "active documents" | Yes, under the Document module. Acknowledgement is part of document control. | https://eaudit.gcaa.ae/QPulseWeb/UI/Help/Content/Document/docs_ack.htm |
| **Ideagen Coruson / Aviation Safety (Cora)** | Document details view, "Viewer tab", "Distribution" section | "Acknowledge" | Copyholders in "Distribution", distributed date, "acknowledged date" | Yes, under document control | https://coruson.help.ideagen.com/hc/en-gb/articles/360005738700-Acknowledging-Documents |
| **Converge ETL** | "Document management" module | "Track required reading"; "required-reading groups"; "request confirmation" | Revisions retained, "revision visibility", assignment at aircraft or fleet level, "Reports and reminders" | Yes | https://www.converge.aero/document-management |
| **Galiot DOC** (MER Systems) | Galiot DOC (document management) | "Read & Sign Confirmation" | Version control, rollback, permissions, metadata | Yes | https://www.aeroexpo.online/prod/mer-systems-ltd/product-172191-41179.html |
| **Swiss-AS AMOS** | Core modules: Material Management, Engineering, Planning, Production, Maintenance Control, Component Maintenance, Human Resources, Quality Assurance, Financial Management, and others | None found | Quality Assurance covers audits, compliance and corrective actions | No document or read-and-sign module is named publicly. [INFERENCE] AMOS focuses on maintenance and engineering. Operators usually pair it with a separate DMS. | https://swiss-as.com/core-optional-modules |
| **ELMS Aviation** | "ELMS Workforce: Competence & Compliance" (People & Role Records, Competence Management, Authorisations, Training Oversight, Compliance Evidence, Dashboards & Reporting); "ELMS Governance: SMS" | None found | Competence and authorisation records | No. This is a competence-management product, not a DMS. | https://www.elms-aviation.com/ |
| **Veryon Publications** | "Content Library" | None listed (has "Engagement Tracking") | OEM and regulatory publications, offline access | Not applicable. Covers OEM publications, not company manuals. | https://www.getapp.ca/software/2045339/veryon-publications |
| **Ramco Aviation** | Content management capability | None found | OEM document revisions with "approval workflows"; "content repository" | Not applicable. Covers OEM technical documentation. | https://www.ramco.com/blog/aviation/manage-your-oem-digital-technical-documentation |
| **MROPro** | Not found | Not found | Not found | Cannot confirm. Several extended searches found no aviation product of this name. A similarly named "MRO Pro" iOS app exists. | Searches only |
| IFS Maintenix, Rusada ENVISION, CAMP, Traxxall, Flydocs, Gen-X, AeroDocs | Not verified | Not verified | Not verified | Searches returned no specific public pages on read-and-sign. [INFERENCE] These are mainly MRO/M&E, records or tracking tools that cover OEM data rather than company-manual acknowledgement. | Searches only |

**Patterns across these vendors**

1. Every dedicated document-management system puts read-and-sign inside its Documents or document-management area, as a distribution and tracking step. None gives it a separate top-level section. Examples: Centrik Documents, EFOS Documents, Q-Pulse, Coruson, Comply365 ContentManager365, Converge.
2. The labels vary:
   - "Read & Sign": EFOS, Comply365, Galiot, Centrik SmartDocs
   - "Mark as Read" / "My Documents to Read": Centrik
   - "Acknowledge": Q-Pulse, Coruson
   - "Required reading": Converge
   - "Read & Receipt": CrewNet
3. The common entities across vendors are:
   - document or manual
   - revision, with Record of Revision, Summary of Change and List of Effective Pages
   - distribution by role, department or organisation (copyholders)
   - read or acknowledged date
   - deadline or due date, overdue status, reminders and postponement with a reason
   - notices or bulletins, sometimes a separate product
4. Large MRO/M&E suites (AMOS, Ramco, Veryon) do not offer company-manual read-and-sign publicly. Their "documentation" features mean OEM technical publications.

---

## 4. Regulatory and industry wording

- **UK CAA SRG1773 (Part-CAMO CAME compliance checklist)** [CONFIRMED]:
  - The CAME introduction should list "Holders of the copies", "Location of copies", "List of issues/amendments or record of revision" and "Revision highlights / Summary of changes".
  - §2.9: "All staff should be able to demonstrate knowledge of, and compliance with, the CAMO procedures".
  - §5.1 lists a sample "Revision acknowledge" form.
  - https://caa.co.uk/publication/download/18137
- **ORO.MLR.100 (UK and EU Air Ops)** [CONFIRMED]:
  - (d) "All operations personnel shall have easy access to the portions of the OM that are relevant to their duties."
  - (e) "All personnel shall be made aware of the changes that are relevant to their duties."
  - https://legislation.gov.uk/eur/2012/965/annex/III/division/subpart+mlr/2016-08-25/data.xht
- **Part-145, 145.A.35 AMC** [CONFIRMED]: staff need an adequate understanding of "associated organisation procedures". https://www.easa.europa.eu/en/print/pdf/node/19100
- **FAA AC 120-78A, "Electronic Signatures, Electronic Recordkeeping, and Electronic Manuals" (22 Jun 2016)** [CONFIRMED]:
  - §4-2b "Access, Availability, and Distribution": a system should provide "distribution and/or access to manual(s) by the appropriate personnel".
  - It does not define a read-acknowledgement function. "Acknowledged by" appears only as an example of a signature statement.
  - https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_120-78A.pdf
- **IATA (document control systems, IOSA)** [CONFIRMED]: "Any document changes need to be incorporated, distributed, and understood by those concerned". IATA also calls for "Stringent version management to prevent obsolete documents being used". IATA names the function "Document Control System". https://www.iata.org/en/publications/newsletters/iata-knowledge-hub/document-control-systems/
- **ISO 9001:2015 §7.5 "Documented information"** [UNVERIFIED]: §7.5.3 requires control of "distribution, access, retrieval and use" and "control of changes (e.g. version control)".
- **ICAO Doc 9859 (SMM)** [UNVERIFIED]: the SMS component "Safety promotion" has the element "Safety communication". That is the natural regulatory home for safety notices that need acknowledgement.

**Summary [INFERENCE].** Regulators describe the outcome ("made aware of the changes", "demonstrate knowledge", "Revision acknowledge" form). They do not give the feature a name. "Read and sign" is an industry and vendor term, and "acknowledge" is the term closest to the regulators' wording.

---

## 5. Recommendation for Airworthiness+ [INFERENCE, based on the evidence above]

**Section name: "Documentation", or better "Document Control".**
- "Documentation" is acceptable and plain English.
- "Document Control" matches IATA and ISO usage and signals controlled revisions rather than a file store.
- Avoid "Library" as the section name. Veryon and Comply365 use "library" for a reference collection, so it suggests OEM publications.
- Centrik and EFOS both use "Documents". That works if you want a short label.

**Suggested sub-items**

1. **Manuals & Procedures** (or "Library"): the exposition (MOE/CAME/CAE/MOM), procedures and forms. Each record carries:
   - issue/revision
   - Record of Revision and Summary of Change
   - List of Effective Pages
   - temporary revisions
   - copyholders/distribution
2. **Changes / Revisions**: drafting, review and approval workflow. Flag items that need CAA prior approval (CAME §0.5) versus those that do not (CAME §0.6).
3. **Required Reading**: the staff-facing view.
   - "Required Reading" works well as the module name. It describes the obligation and covers notices as well as manuals.
   - Use **"Acknowledge"** as the button or action. It matches CAA's "Revision acknowledge" wording and Q-Pulse/Coruson.
   - "Read and Sign" is also widely understood (EFOS, Comply365), but "sign" may wrongly suggest a certifying or regulatory signature under AC 120-78A.
   - Track:
     - assignee by role or department
     - revision acknowledged
     - due date, overdue status and reminders
     - postponement with a reason
     - a mandatory "I have read and understood" statement
4. **Notices** (Technical/Quality/Safety Notices, bulletins): short documents that go through the same Required Reading flow. This follows CrewNet's notices and bulletins model and the ICAO "Safety communication" element.

**Where the current "Organisation" items belong**

- **Exposition**: belongs under Documentation. It is the main controlled document.
- **Changes**: split it.
  - Document revisions belong under Documentation.
  - Changes to the approval itself (CAA forms such as Form 2 changes, nominated persons, scope changes) belong with Approval.
- **Approval and Scope**: does not belong under Documentation. It is regulatory status (certificate, ratings, nominated persons, locations).
  - Keep it in an "Organisation", "Approval" or "Compliance" section, or rename it "Approval".
  - The current section name "Organisation" fits it better than "Documentation" does.
- **Oversight**: does not belong under Documentation. It covers CAA oversight and audit findings and internal compliance monitoring. It sits naturally under "Compliance" or "Quality".
  - AMOS puts audits under "Quality Assurance".
  - Web Manuals separates "Compliance monitoring" from manuals in its top navigation.

**Suggested structure**
- **Approval** (or **Organisation**): Approval and Scope, Approval Changes, Oversight
- **Document Control** (or **Documentation**): Manuals & Procedures (including Exposition), Revisions, Required Reading, Notices
