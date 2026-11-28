# ADR-0010 Aircraft transfer pilot

Status: Proposed. Applies to synthetic trial data until the sending and receiving records leads agree the ownership and reconciliation rules.

## Ownership and references

| Information | Owner during the trial | Transfer representation |
| --- | --- | --- |
| Aircraft and registration history | Sending aircraft records lead until handover is accepted | Sender organisation and stable aircraft record identifier, with registration and serial as cross-checks |
| Defect report and deferral | Original reporting and recording organisation | Original stable record and source reference, with attributable decision, restriction and due limit |
| Inspection and forecast | Issuer owns recorded inspection evidence. Receiver recomputes the forecast from the agreed inputs | Stable inspection and completion identifiers, applicable source revision, interval and completion inputs |
| Corrections | Issuer of the original or authorised superseding record as evidenced by the records | Both stable versions, signed evidence where applicable, relationship, authority, reason and time |
| Import decision | Receiving records lead | Separate receiving identifier and dated reconciliation entry referring to the sender's version and identifier |

The current Airworthiness+ archive is a project format. Use the archive manifest to verify archive consistency and the source record IDs to compare the results. Reserve an explicit schema identifier and version for any separately published receiver contract. Validate schema, identities and references before applying an import. Use sending organisation, record identifier and version as a receiver identity. Repetition of the same version and contents should be idempotent. Conflicting contents for the same identity, unsupported versions, dangling references and missing required records must be recorded as reconciliation failures. A receiver mapping must retain unresolved or unmapped data and its source reference.

## Industry specifications

| Reference | Proposed application |
| --- | --- |
| ATA Spec 2500 | Map aircraft transfer status, including repair and damage, last done and next due, equipment status and related events. [ATA aircraft transfer working group](https://ataebiz.org/wg-aircraft-transfer/) |
| ATA Spec 2000 Chapter 16 | Assess exchange of authorised part release certificates. [Airlines for America Chapter 16 catalogue](https://publications.airlines.org/products/spec-2000-authorized-release-certificate-ch-16-revision-2019-1) |
| ATA Spec 2000 Chapters 17 and 18 | Assess electronic logbook and work-package exchange as separate adapters. [ATA maintenance execution working group](https://ataebiz.org/WG-maintenance-execution/) |

Airworthiness Limited owns confirming access to the applicable versions and public redistribution rights with Airlines for America. The publisher offers specifications to members and as publications. Public working-group summaries support the mapping scope above. Keep the initial examples original and synthetic. A conformance claim requires the applicable licensed version and executed conformance tests. [ATA standards catalogue](https://ataebiz.org/standards/)

## Verification

Run the archive handover regression and retain its results. The receiving records lead then tests valid transfer, replay, unsupported version, conflicting duplicate, missing required record and dangling reference in a separate implementation. Compare IDs, evidence history and operational status, and record transformations and differences. Independent import, issuer trust and standards conformance are open.
