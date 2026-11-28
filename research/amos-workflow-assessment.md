# AMOS workflow assessment and Airworthiness+ validation plan

28 November 2026. This plan translates the 18 supplied screenshots in their original order. The demonstrations are historical product evidence. UK rules and applicable AMC inform UK implementation. EASA and FAA material, industry specifications, and analogies inform design. Proposed controls and test criteria are project decisions. The screenshots establish neither regulatory acceptance of Airworthiness+ nor comparative safety performance.

## Source experts and intended reviewers

Luigi Careddu of Swiss-AS presented the AMOS signing and implementation examples. Dragos Munteanu of IATA presented the adjacent industry perspective on recognition, data exchange and security. The ATA e-Business Aircraft Transfer Records Working Group maintains the aircraft-transfer specification. The roles named under each screenshot are proposed reviewers, with no participation or endorsement implied. [EASA webinar summary naming the presenters](https://www.easa.europa.eu/en/downloads/132518/en) · [ATA Aircraft Transfer Records Working Group](https://ataebiz.org/wg-aircraft-transfer/)

## Screenshot-by-screenshot design and test cases

### 1. Faceted work-order retrieval and ATA system classification

**Observation.** The AMOS work-order enquiry at 0:17 scopes by aircraft and accepts ATA chapter 25. Date, state, record type, deferral class, originating description and corrective action are separate dimensions. The results still show multiple chapters while the filter is being entered.

**Framework and reviewer.** ATA iSpec 2200 Standard Numbering System, UK Part-ML defect control and the Part-CAO written work-order process. Review with a continuing airworthiness planner. [ATA standards](https://ataebiz.org/standards/) · [ML.A.403](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05b%20ML/2%20Regs/03890_ML.A.403.htm) · [CAO.A.055](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/05860_CAOA055_Maintenance_data_and_work_orders.htm)

**Plan and test.** Extend maintenance history across existing defect, order and package records. Seed a chapter 25 section and a different chapter on the same aircraft, plus chapter 25 on another aircraft. Search for chapter 25 and a term that appears separately in the report and action. Check the chapter-to-section match, cross-aircraft exclusion, source links and legible status. Existing record validation is baseline evidence. The combined search awaits implementation.

### 2. Structural damage and repair register

**Observation.** The structural damage screen at 0:24 links a front-view lightning-strike marker for AAO to work order 2252475 and a frame reference. The chart selector offers aircraft and subassembly views. The screenshot shows a prompt to open a context menu.

**Framework and reviewer.** Airframe Structural Repair Manual (SRM), aircraft-specific drawings, documented repair data and ATA Spec 2500 Repair Damage Status. Review with a structures engineer and technical records lead. [Project research on structural repair evidence](1321-2014/02.md#3-records-and-documents) · [ATA standards](https://ataebiz.org/standards/) · [CAO.A.090](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/06070_CAOA090_Record-keeping.htm)

**Plan and test.** Model finding, physical location, repair, references and follow-up inspection as linked records. Store aircraft identity, drawing revision, frame or zone and dimensions. Seed a finding, a repair and a repeat inspection, change the drawing revision, then confirm the original physical reference and links survive a transfer. The repair records exist. The mapped register and revised drawing test await implementation.

### 3. Electronic technical log provenance and part-linked defect retrieval

**Observation.** The 0:37 exercise combines a maintenance defect and a pilot report for YAA, ATA 80, associated with part 3291556-1. The screenshot shows filter setup.

**Framework and reviewer.** ATA Spec 2000 Chapter 17 Electronic Logbook, ML.A.403 and Airworthiness+ Technical Log issue #7. NASA Ames researcher Barbara Kanki and colleagues studied how pilots and mechanics write and interpret discrepancy entries. Use that research to test whether the next reader can act on the report. Review with a flight crew representative and maintenance control. [NASA logbook communication research](https://ntrs.nasa.gov/citations/20090020413) · [ATA standards](https://ataebiz.org/standards/) · [ML.A.403](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05b%20ML/2%20Regs/03890_ML.A.403.htm) · [Issue #7](https://github.com/alxtkng/airworthiness-plus/issues/7)

**Plan and test.** Model original author, recording actor, source record and component linkage in the technical-log design. Enter two reports for the same aircraft and ATA chapter with different origins and one unrelated part. Retrieve both relevant records without losing original attribution or letting text mentions masquerade as structured links. The technical-log workflow is deferred.

### 4. Stock visibility by location and issue eligibility

**Observation.** The 1:17 quiz asks for ZRH Main Store. The picture shows seven there, one at ZRH Line, eight at the station, and ten across the network. GVA is zero. The screen offers alternates, shelf-life-related search, quarantine, transfers and a dangerous-goods marker.

**Framework and reviewer.** UK CAO.A.050(c), 145.A.42 and applicable component classification, segregation and eligibility controls. ATA Spec 2000 Chapter 9 supports traceability. ATA Spec 2400 is a candidate for allowable configuration data, subject to the applicable source and intended use. Review with a Stores inspector and maintenance engineer. [CAO.A.050](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/05830_CAOA050_Components_equipment_and_tools.htm) · [145.A.42](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/02%20145/2%20Regs/01648%20145.A.42%20Components.htm) · [ATA standards](https://ataebiz.org/standards/)

**Plan and test.** Add this stock snapshot to the Stores handoff criteria. Check that users can retrieve each geographic total. In a separate iteration reserve one eligible unit and quarantine or expire another. Check that physical custody persists and available quantity falls correctly, and that issue eligibility is evaluated for the intended package. Use the same scenario as a product-training exercise with Stores staff. Receiving and the first custody link exist. The location ledger and guided exercise await implementation.

### 5. Intraday production planning, fatigue and shift handover

**Observation.** The SWISS timeline overlays work, breaks, a time marker, completion and possible conflicts. The image gives limited visibility into individual assignments.

**Framework and reviewer.** UK 145.A.47 production planning and fatigue, human factors and task turnover. Bonny Parke and Barbara Kanki studied how briefings and recordings supplement written shift turnover. Review with a line maintenance planner and a human factors specialist. [NASA shift-handover study](https://ntrs.nasa.gov/citations/20110008267) · [CAA 145.A.47](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/02%20145/2%20Regs/01650%20145.A.47%20Production%20planning.htm) · [FAA maintenance human factors research](https://www.faa.gov/about/initiatives/maintenance_hf) · [SWISS demonstration](https://www.youtube.com/watch?v=9xaPj6gDIno)

**Plan and test.** Retain the existing roster, fatigue and acknowledged handover workflow. In a future dispatch trial, give a planner a turnaround task overlapping a break and an outstanding inspection that crosses shifts. Confirm the conflict is understandable and that the incoming person can see and acknowledge the outstanding work.

### 6. Maintenance, repair and overhaul interoperability

**Observation.** The architecture slide groups engineering, material management, production and planning around AMOS and shows interfaces to electronic technical logs, airline operations, records and analytics.

**Framework and reviewer.** ATA Spec 2000 Chapters 16 to 18 address distinct exchange domains. ATA Spec 2500 addresses aircraft transfer, including repair/damage and maintenance status. Review with the ATA working group, operator systems architect and technical records lead. [ATA standards](https://ataebiz.org/standards/) · [ATA working group](https://ataebiz.org/wg-aircraft-transfer/)

**Plan and test.** Start with records handover and document which system owns each item. Use stable identifiers, versioned mappings, and source references. Test duplicates, missing mandatory data, unsupported records and unresolved differences at receiving. Align with existing standards where they fit and confirm rights before redistributing specification material. An application archive and selected import layouts exist. Full receiving-side round-trip and ATA conformance are future tests.

### 7. Electronic attestation and operational control

**Observation.** At 4:06 Swiss-AS describes paperless operation, attribution and timing, qualification checks, clock-in and location examples, pending/signed status and mobility.

**Framework and reviewer.** UK CAO.A.060 and applicable maintenance procedures. EASA paperless maintenance guidance provides context. Review with the maintenance approval holder and certifying staff. [CAA CAO.A.060](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/05890_CAOA060_Maintenance_standards.htm) · [EASA paperless maintenance guidance](https://www.easa.europa.eu/en/faq/137907) · [Presentation 4:06](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=246s)

**Plan and test.** Specify the evidence for completion, inspection and release separately. For a proposed in-app action, confirm a signer sees the exact version, an out-of-scope authorisation is refused, and an outstanding inspection remains visible before handover. Treat clock-in, location and mobile connectivity as use-case decisions.

### 8. Electronic, advanced and qualified signatures

**Observation.** The slide distinguishes ordinary electronic signing, advanced signatures with identifiable signers and detectable changes, and qualified signatures with a qualified certificate and device.

**Framework and reviewer.** UK eIDAS trust-service terminology and the applicable aviation approval and procedure. Review with a UK trust-services specialist and the approval holder. [ICO qualified trust services](https://ico.org.uk/for-organisations/guide-to-eidas/qualified-trust-services/) · [EASA paperless maintenance guidance](https://www.easa.europa.eu/en/faq/137907)

**Plan and test.** Record the required evidence level and validation method for each action before choosing technology. Include the intent to sign, exact content, identity, authorisation and time. Contrast a sign-in event with a signing event in test data and ensure the verifier reports each accurately. No signature level is assigned by this plan.

### 9. Step-up authentication and source attribution

**Observation.** At 6:41 AMOS illustrates a signed-in user sign, optional repeat authentication and a back-office user entering a pilot report on behalf of its source.

**Framework and reviewer.** Digital identity, role-based access and separation of the reporting, recording and signing roles. Review with flight operations and an identity engineer. [Airworthiness+ passkey decision](../architecture/decisions/ADR-0005-passkeys-and-verification.md) · [Presentation 6:41](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=401s)

**Plan and test.** Reuse existing recent verification where appropriate. Record the original reporter, transcriber, and any certifying actor as distinct identities. Confirm fresh verification does not confer extra maintenance privileges. The passkey controls can be exercised today. Delegated report entry and record-bound signing await design and implementation.

### 10. Security management and independent assurance

**Observation.** At 7:51 Swiss-AS describes ISO 27001 certification, recurring external certification audits, third-party testing of main releases, and vulnerability management across software and services.

**Framework and reviewer.** ISO/IEC 27001 information security management system, OWASP ASVS application verification and the existing independent test scope. Review with the information security lead and an independent assessor. [ISO/IEC 27001](https://www.iso.org/standard/27001) · [OWASP ASVS](https://asvs.owasp.org/downloads/) · [Issue #40](https://github.com/alxtkng/airworthiness-plus/issues/40) · [Presentation 7:51](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=471s)

**Plan and test.** Reuse the current assurance and vulnerability-management records. Exercise the existing authentication, authorisation and archive tests as baseline evidence. Document ownership of vulnerability intake, maintained releases and operator communication. Independent testing and any certification remain separate assurance activities.

### 11. Structured electronic work cards and independent inspection

**Observation.** At 9:06 AMOS renders an electronic task card from structured SGML maintenance data. Individual blocks can be stamped, timestamped and checked for qualifications and missing sign-offs. The closed card can be signed and archived.

**Framework and reviewer.** UK CAO.A.055 and CAO.A.060, Part-145 maintenance data and performance of maintenance, and ATA Spec 2000 Chapter 18. ATA iSpec 2200 and S1000D are source-format references. The AAIB investigation into G-EUOE provides a case for testing how the interface makes incomplete critical work visible. Review with certifying staff and a technical publications specialist. [AAIB report 1/2015](https://www.gov.uk/aaib-reports/aircraft-accident-report-1-2015-airbus-a319-131-g-euoe-24-may-2013) · [CAA CAO.A.055](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/05860_CAOA055_Maintenance_data_and_work_orders.htm) · [ATA standards](https://ataebiz.org/standards/) · [Presentation 9:06](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=546s)

**Plan and test.** Preserve the issued revision and keep source rendering separate from the sign-off workflow. Exercise the existing draft-to-release path with a missing or non-independent inspection. For the next slice, require one attestation for a defined card step, verify the recorded version outside the app and ensure a corrected version receives its own evidence.

### 12. Internal public-key infrastructure and trust anchors

**Observation.** At 9:26 Swiss-AS describes an internal root or a certificate signed by a certification authority, with user certificates chained to it and a trust anchor shared for external verification.

**Framework and reviewer.** Certificate path validation, issuer governance and revocation, informed by ETSI signature validation material. Review with a PKI engineer and a receiving technical records team. [ETSI PAdES specification publication](https://portal.etsi.org/Portal_Pub/APNProcPub.asp?ACTION_TYPE_NB=AP&FROM_DD=17&FROM_MM=Aug&FROM_YYYY=2026&REAL_FROM_DD=17&REAL_FROM_MM=Aug&REAL_FROM_YYYY=2026&TO_DD=17&TO_MM=Aug&TO_YYYY=2026) · [Presentation 9:26](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=566s)

**Plan and test.** Derive trust, expiry, revocation and historical validation requirements before selecting a provider or operating a certificate authority. Test trusted, unknown and revoked or indeterminate cases with a verifier that gets trust material through a separate route.

### 13. Signing workflow, archival confirmation and audit history

**Observation.** At 10:56 the signing event generates a PDF/A and a queue entry. The signer previews, authenticates and signs. Archiving precedes clearing the pending entry, and the signature is recorded in history.

**Framework and reviewer.** CAO.A.090 and 145.A.55 recordkeeping, archival PDF/A and PAdES as a candidate digital signature format. Review with a records archivist and a workflow engineer. [CAA CAO.A.090](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/05d%20CAO/2%20Regs/06070_CAOA090_Record-keeping.htm) · [CAA 145.A.55](https://regulatorylibrary.caa.co.uk/1321-2014/Content/Document%20Structure/02%20145/2%20Regs/01653%20145.A.55%20Maintenance%20and%20airworthiness%20review%20records.htm) · [Presentation 10:56](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=656s)

**Plan and test.** Design explicit pending, signed and archived states. Simulate a revision change before signing, duplicate completion and an archive failure after signing. Require a fresh review for the new revision and a recoverable archive retry without duplicate evidence. The full workflow awaits implementation.

### 14. Portable signed evidence and offline verification

**Observation.** At 11:41 a signed demo PDF/A has a named certificate. AMOS describes distributing the root and verifying offline after acquiring it.

**Framework and reviewer.** Long-term signature validation, independently distributed trust anchors, archival readability, and the existing records exit workflow. Review with an archivist and a recipient who has no issuing-system account. [Airworthiness+ data export on exit](../operations/contracts/data-export-on-exit.md) · [Presentation 11:41](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=701s)

**Plan and test.** Exercise present-day checks for archive integrity and retained history. Add issuer verification when external evidence exists. Give the recipient an intact file, a modified copy and a file with an untrusted issuer. Check that the verifier distinguishes integrity, issuer trust and maintenance authorisation. Document which claims remain indeterminate offline.

### 15. Federated trust and the electronic passport analogy

**Observation.** At 14:06 the example shows state signing authorities, document signers and distribution of verification material through the ICAO Public Key Directory, master lists or bilateral exchange.

**Framework and reviewer.** ICAO Doc 9303 trust distribution is an analogy. Review with a trust specialist, a releasing organisation and an independent recipient. [ICAO ePassport validation](https://www.icao.int/icao-pkd/epassport-validation) · [Presentation 14:06](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=846s)

**Plan and test.** Start with two organisations and separately obtained trust material. Reconcile issuer identity and signing authority at the time of the action. Publish a test example and a second implementation should be able to interpret it. The trial requires no central directory.

### 16. External trust service provider integration

**Observation.** At 15:41 AMOS submits the PDF/A to a provider. The provider authenticates the signer and signs using a key held in a hardware security module or on a token, depending on the service. The signed result is retained.

**Framework and reviewer.** Trust service provider integration, document binding and verification of externally produced evidence. Review with the provider's technical specialist and the operator's records and compliance leads. [ICO qualified trust services](https://ico.org.uk/for-organisations/guide-to-eidas/qualified-trust-services/) · [Presentation 15:41](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=941s)

**Plan and test.** Preserve the submitted revision and intended signer. Trial a provider sandbox only after requirements are known. Test delay, refusal, mismatched response, duplicate notification and archival failure. Check the result is bound to the exact document and signer before recording completion.

### 17. Management of change and parallel operational validation

**Observation.** At 16:26 the project flow covers scoping, process and IT design, a limited parallel run, gap analysis and training. It includes early authority engagement, fallback, operational participants and final approval.

**Framework and reviewer.** Management of change, problem logging and CAP 562 Leaflet C-90 guidance where applicable to the proposed use. Review with both organisations' accountable leads, working users and the competent authority where required. [CAA CAP 562](https://www.caa.co.uk/data-and-publications/publications/documents/content/cap-562/) · [Presentation 16:26](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=986s)

**Plan and test.** Run the existing acceptance checks for problem entries and parallel-run records. For an operational trial, agree the authoritative system and fallback, involve staff outside the build team, and record and resolve differences before cutover. Confirm the applicable process with each organisation.

### 18. Readiness, cutover and stabilisation

**Observation.** The 2021 example at 17:06 overlaps design, implementation, training, authority work and parallel operation. It shows a late-November cutover and December stabilisation.

**Framework and reviewer.** Implementation readiness, cutover, fallback, operational training and post-implementation review. Review with the project sponsor, operational lead, training lead and receiving organisation. [Presentation 17:06](https://www.youtube.com/watch?v=Jvz4BJJHwaM&t=1026s) · [Airworthiness+ readiness review](../assurance/readiness-review.md)

**Plan and test.** Set entry and exit criteria using the trial organisation’s operating context. Rehearse stop, escalation and fallback with synthetic evidence. For a real trial record the owner and closure of every difference, training completion and stabilisation responsibilities.

## Sequence for the working plan

1. **Phase 4 Stores.** Use the stock-by-location case from screenshot 4 as an acceptance criterion for the location ledger and availability view.
2. **Planning and work packages.** Establish a baseline for work order, defect, roster, inspection, and release evidence. Specify one step-level signing action and an external verification result before expanding to other sign-off actions. Test dispatch visibility only when an intraday workflow is available.
3. **Aircraft records and exchange.** Use a single synthetic aircraft with one unresolved defect and a limit, one recurring inspection with completion inputs, and one correction that preserves its original. The first exercise uses the existing archive. The next exercise covers a corrected *signed* record and receiving-side reconciliation once those capabilities exist. Use ATA Spec 2500 as the transfer mapping reference.
4. **Adoption and assurance.** For a future parallel handover with two organisations, document who owns the live record, what causes the trial to stop, and how differences are resolved. Measure time to reconcile, entries rekeyed, defects or due items lost, and evidence that could not be verified. Review preservation of all three seeded items with the receiver before expanding the trial. Publish original synthetic fixtures and conformance cases once the exchange format and publication rights are settled.

The [local execution record](../assurance/amos-workflow-trial.md) records what was exercised against the current implementation.
