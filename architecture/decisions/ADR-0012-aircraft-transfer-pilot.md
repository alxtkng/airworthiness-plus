# ADR-0012 Aircraft transfer pilot

Status: Proposed. Applies to synthetic trial data until the sending and receiving records leads agree the ownership and reconciliation rules.

## Ownership and references

| Information | Owner during the trial | Transfer representation |
| --- | --- | --- |
| Aircraft and registration history | Sending aircraft records lead until handover is accepted | Sender organisation and stable aircraft record identifier, with registration and serial as cross-checks |
| Defect report and deferral | Original reporting and recording organisation | Original stable record and source reference, with attributable decision, restriction and due limit |
| Inspection and forecast | Issuer owns recorded inspection evidence. Receiver recomputes the forecast from the agreed inputs | Stable inspection and completion identifiers, applicable source revision, interval and completion inputs |
| Corrections | Issuer of the original or authorised superseding record as evidenced by the records | Both stable versions, signed evidence where applicable, relationship, authority, reason and time |
| Import decision | Receiving records lead | Separate receiving identifier and dated reconciliation entry referring to the sender's version and identifier |

The Airworthiness+ Records Export version 1 archive is a project format. Its manifest digest identifies the snapshot. Within it, the sending organisation UUID, table and record UUID identify a source record. History sequence and its event hash identify a record version. Retain the original IDs and history in the receiver. Replay of an identical snapshot is idempotent. A different snapshot for the same aircraft is referred for reconciliation before use. The source archive remains the reference for records outside the receiver mapping.

The separate `Airworthiness+ Aircraft Handover Reconciliation` version 1 JSON compares the sender's observed state with the receiver's result. Its `records` object carries sender and aircraft UUIDs, defect UUID and limit, inspection UUID and source, completion UUID and issued instruction reference, revision and measurements, next due date, and both reading UUIDs and quantities. The signing envelope and archive manifest identify those readings by their exact version. The receiver recomputes next due and refuses absent dependencies, unexpected record identities or different compared values before writing. See the [synthetic example](../../data/amos/handover-comparison-v1.json).

## Industry specifications

| Reference | Proposed application |
| --- | --- |
| ATA Spec 2500 | Map aircraft transfer status, including repair and damage, last done and next due, equipment status and related events. [ATA aircraft transfer working group](https://ataebiz.org/wg-aircraft-transfer/) |
| ATA Spec 2000 Chapter 16 | Assess exchange of authorised part release certificates. [Airlines for America Chapter 16 catalogue](https://publications.airlines.org/products/spec-2000-authorized-release-certificate-ch-16-revision-2019-1) |
| ATA Spec 2000 Chapters 17 and 18 | Assess electronic logbook and work-package exchange as separate adapters. [ATA maintenance execution working group](https://ataebiz.org/WG-maintenance-execution/) |

Airworthiness Limited owns confirming access to the applicable versions and public redistribution rights with Airlines for America. The publisher lists Spec 2500 revision 2023.1 as a single-user or multi-user purchase with member access. The scope assessment uses its public descriptions. Written terms for redistribution of schemas, examples or extracts remain pending. Chapter 16 would map release-document identity and issuer evidence to Goods In. Chapter 17 would map flight, defect and reporter provenance. Chapter 18 would map issued card and work-package revisions, completed steps and checks. The next test uses accessible licensed versions, agreed publication terms and a participating operator to verify the applicable profiles. [A4A Spec 2500 publication](https://publications.airlines.org/products/spec-2500-aircraft-transfer-records-revision-2023-1) · [ATA Spec 2000](https://ataebiz.org/spec-2000/)

## Verification

Enable `AIRWORTHINESS_NODE24` with the absolute path of Node.js 24 when running the signed export regression. The independent JavaScript implementation uses Info-ZIP, native cryptography and SQLite. It checks the pinned archive digest, table ownership and record references, recomputes the calendar deadline and verifies the detached reading signatures and applicable synthetic grant with the recipient's separately pinned trust. It retains source history for the mapped tables and reports comparison time, rekeying and unresolved verification. The Python receiver also checks archive event chains, RFC 3161 tokens and renewal evidence. Operator-system import and standards conformance remain open.

## Human-readable evidence

Use `--compare comparison.json --report reconciliation.txt` with the Python receiver. Its report lists matched fields, elapsed time, rekeying and distinct integrity, issuer, signing time and maintenance authority findings. PDF/A-4 is a candidate for long-term rendered evidence under ISO 19005-4:2020. ETSI EN 319 142-1 V1.3.1 (2026-11) defines PAdES baseline signatures. The records owner and trust specialist decide their document profile and preservation period, then test independent PDF/A validation, PAdES validation against the applicable trust history and extraction of the referenced structured records. The pilot provides UTF-8 text and detached signatures. [ISO PDF/A-4](https://www.iso.org/standard/71832.html) · [ETSI PAdES specification](https://www.etsi.org/deliver/etsi_en/319100_319199/31914201/01.03.01_60/en_31914201v010301p.pdf)

## Local receiving rehearsal

The first receiver is a separate Python command and SQLite database. It receives a source aircraft archive, the separately supplied manifest digest, the expected aircraft identifier and the three trial record identifiers. It checks archive consistency and parent references, recalculates a day-based next due, and retains the selected records and their source history. Re-importing the same snapshot returns the same result without inserting again. A distinct snapshot for that aircraft is referred for reconciliation and the previous snapshot remains available. The exercise uses the project archive, synthetic inputs and the existing portable archive verifier.

From the project root, run the executable fixture with `uv run pytest -q tests/test_exports.py::test_independent_receiver_imports_the_unsigned_trial_and_rejects_invalid_transfers`. To run the receiver with that fixture's archive and identifiers:

```sh
PYTHONPATH=src uv run python tools/receive_handover.py transfer.zip receiver.sqlite \
  --manifest-digest "$manifest_digest" --aircraft-id "$aircraft_id" \
  --defect-id "$defect_id" --inspection-id "$inspection_id" --correction-id "$correction_id"
```

A successful result identifies the correction as unsigned and issuer trust as indeterminate. The pilot exercises independent storage and a calendar recomputation. Operational import, separately trusted signatures, authority at signing and Spec 2500 mapping are pending.

## Signed reading rehearsal

The same receiver also takes `--signatures`, `--trust` and `--trust-sha256` as a complete set. Verification precedes the SQLite transaction. Use a receiver database for the exercise whose incoming evidence is signed. A prior unsigned snapshot requires reconciliation before the receiver will accept a different snapshot for the same aircraft.

The signature envelope uses format `Airworthiness+ Synthetic Reading Signatures`, integer version 1, and the two detached claim/signature pairs. Both claims use purpose `airworthiness-plus:synthetic-utilisation-reading:v1`. The original has no predecessor and the correction binds the original claim hash. The supporting trust file uses format `Airworthiness+ Synthetic Reading Trust`, integer version 1, and lists of enrolled keys and separately scoped authorities. The receiver checks both lists against the claimed times with exclusive validity end dates and reported status coverage. The public key and signature use padded Base64. The synthetic custody channel is independent of the sender's archive inputs. [Trial and results](../../assurance/gejkl-signed-handover.md)

```sh
PYTHONPATH=src uv run python tools/receive_handover.py sender/02-corrected.zip receiver/receiver.sqlite \
  --manifest-digest "$manifest_digest" --aircraft-id "$aircraft_id" \
  --defect-id "$defect_id" --inspection-id "$inspection_id" --correction-id "$correction_id" \
  --signatures sender/02-signatures.json --trust custodian/trust.json \
  --trust-sha256 "$trust_pin"
```

The archive values and identifiers come from the sender route. Supply the trust pin from the separate custody route. Record versions and the scoped synthetic grant can be verified offline. Regulated issuance, operational status infrastructure and a trusted signature timestamp remain open.

## Trusted timestamp evidence

The synthetic receiver optionally verifies a timestamp envelope of format
`Airworthiness+ Synthetic Reading Timestamps`, integer version 1 and two
`record_id`/Base64 DER `response` entries. It uses three additional arguments,
`--timestamps`, `--tsa-root` and `--tsa-root-sha256`. Apply them together with
the signed reading flags. Each response must bind the raw detached signature
and chain to the separately pinned synthetic TSA root under the recorded
policy. Timestamp verification precedes the SQLite transaction. The receiver
keeps the TSA's proof-of-existence time separate from the asserted signing
instant and the authority check. See the [retained rehearsal](../../assurance/gejkl-trusted-timestamps.md).

Use `--tsa-evaluated-at` to report the TSA leaf's status at an explicit UTC
instant while native OpenSSL 3 validates the token path at `genTime`. Add
`--tsa-crl` for a complete issuer-authenticated PEM CRL for that instant.
The receiver evaluates the revocation date and reason separately, including
an earlier invalidity date. The [historical exercise](../../assurance/gejkl-historical-timestamp-status.md)
records both the retained-token expiry and the replacement-TSA CRL cases.

## Timestamp renewal

Add `--renewals`, `--renewal-tsa-root`, `--renewal-tsa-root-sha256` and
`--renewal-tsa-crl` to the signed timestamp transfer. The evaluation instant
applies to the renewal TSA. The receiver uses the renewal token time to check
the frozen predecessor CRL. Omitting the predecessor CRL is represented as
indeterminate, and omitting a CRL already bound into a renewal causes an
imprint mismatch. Both generations of timestamp evidence and the verification
findings are retained before the SQLite write. The [rehearsal record](../../assurance/gejkl-evidence-renewal.md)
gives the exact versioned wire format and results.
