# G-EJKL long-term evidence renewal trial

28 November 2026. This rehearsal renews both timestamped G-EJKL signatures and verifies the evidence in the separate SQLite receiver. The receiver and native OpenSSL 3.5.9 process ran with operating-system network access denied. The sender's record archive, original and corrected Ed25519 signatures, and reading trust file stayed byte-identical in both arms.

## Why G-EJKL

G-EJKL already appears in the Airworthiness+ sample fleet with its 11,206.8-hour baseline and deferred headset defect. The integrated AMOS trial asks for one synthetic aircraft carrying an unresolved deferred defect, a recurring inspection and a corrected record. The earlier unsigned handover regression used this fixture and added the inspection and corrected reading. Keeping the same aircraft, records and identifiers across the unsigned, signed, timestamped and renewed runs makes it possible to compare the receiver's conclusions directly. REQ-134 traces the retained aircraft records and superseded entries. REQ-290 traces the independently recomputed inspection forecast. This is the project's regression specimen selection. [Sample fleet](../design-system/SampleData.md) · [Integrated AMOS brief](../prompts/amos-workflow-completion.md#required-integrated-trial) · [Unsigned trial](amos-workflow-trial.md)

The renewal method follows the RFC 3161 re-timestamping guidance and the renewal lifecycle in RFC 4998 §§5.2–5.3. Renew while predecessor evidence is valid, check predecessor validity and status at the successor's time, and check the latest timestamp at the final evaluation. This is a synthetic JSON profile informed by Evidence Record Syntax. ASN.1 ERS and XMLERS encoding conformance, hash-tree renewal for algorithm migration, and qualified operational custody remain outside the exercise. [RFC 3161 §4](https://www.rfc-editor.org/rfc/rfc3161.html#section-4) · [RFC 4998 §5](https://www.rfc-editor.org/rfc/rfc4998.html#section-5) · [RFC 6283](https://www.rfc-editor.org/rfc/rfc6283.html)

## Renewal and verification method

1. Verify the source archive, the two linked reading signatures, their original scoped authority and each predecessor timestamp. Use trust roots pinned independently from the sender inputs.
2. Use a distinct renewal TSA root. For each reading, its new RFC 3161 message imprint covers a canonical JSON record with separate SHA-256 commitments to the raw Ed25519 signature, the archive manifest, the reading trust file, the pinned predecessor root, the exact predecessor DER response and the predecessor CRL when available.
3. In the receiver, recompute both payloads. Check each predecessor at its own `genTime`, check its certificate and recorded revocation status at the successor's `genTime`, and require renewal before the predecessor leaf and root expiry. Check the renewal certificate and applicable signed revocation evidence at the final evaluation. Keep the two reading signatures, the original timestamp evidence, the new responses and their verification findings together in the receiver snapshot. Keep the independently supplied roots and signed CRLs with the public evidence.

The canonical JSON is UTF-8 with sorted keys, compact separators, unescaped non-ASCII characters and no non-finite numbers. The purpose value is `airworthiness-plus:synthetic-rfc3161-renewal:v1`. Renewal response rows use `record_id` and a standard padded Base64 DER `response`. The exact payload keys are `purpose`, `record_id`, `signature_sha256`, `archive_manifest_sha256`, `reading_trust_sha256`, `previous_tsa_root_sha256`, `previous_response_sha256` and `previous_crl_sha256`. An absent predecessor CRL is encoded as JSON null and keeps the chain's status indeterminate.

## Recorded results

| Arm | Original TSA time | Renewal TSA time | Predecessor expiry and evaluation | Result |
| --- | --- | --- | --- | --- |
| Exact retained timestamps | 28 November 2026 at 10:49:58 UTC | 28 November 2026 at 11:06:33 UTC | Expires 26 February 2027 at 10:49:58 UTC. Simulated verification one second later. | Both renewal links verified. Full chain status **Indeterminate** because the original issuer's CRL is unavailable. |
| Complete synthetic chain | 28 November 2026 at 11:06:33 UTC | 28 November 2026 at 11:06:34 UTC | The short-lived predecessor leaf actually expired at 11:06:45 UTC. The receiver ran offline after expiry and evaluated the evidence at 11:06:46 UTC. | Both full chains **Verified** using the frozen predecessor CRL and a separate renewal TSA CRL. Native current-time verification of either old timestamp failed with `certificate has expired`. |

Both times in each timestamp generation are whole-second values. Renewal timing is checked per reading. The sender's correction still binds one signed reading to its predecessor. Each receiver replay left one snapshot, including the unchanged open defect and inspection due date. The complete arm used a 12-second predecessor leaf and 180-day renewal leaf. The system clock was unchanged. The retained arm used a simulated future evaluation and simulated renewal-issuer status for that date.

The offline receiver refused a different authentic predecessor CRL, the removal of a bound CRL, a substituted predecessor with conflicting chronology, an authentic renewal issued after expiry and a correctly bound renewal over a revoked predecessor. The regression also targets payload binding using a different valid predecessor response for the same signature. Refusals preserve the accepted SQLite evidence.

## Reproduce

Use OpenSSL 3 on the path, the locked Python environment and disposable PostgreSQL.

```sh
PYTHONPATH=src uv run pytest -q tests/test_offline_tsa_renewal.py \
  tests/test_offline_tsa_status.py tests/test_exports.py tests/test_security.py
```

For the public artifacts, use a fresh SQLite path with the [timestamped receiver command](../architecture/decisions/ADR-0010-aircraft-transfer-pilot.md#trusted-timestamp-evidence). Add the final evaluation instant and the renewal envelope, independent root, root pin and CRL. In the complete arm also supply the frozen predecessor CRL as `--tsa-crl`.

```sh
--tsa-evaluated-at "$evaluation_utc" --renewals sender/04-renewals.json \
  --renewal-tsa-root custodian/renewal-tsa-root.pem \
  --renewal-tsa-root-sha256 "$renewal_root_pin" \
  --renewal-tsa-crl custodian/renewal-crl.pem
```

The local `gejkl-renewal-trial-2026-11-28` folder retains the original and successor timestamp envelopes, independent trust inputs, receiver verdicts and refusal evidence. Private keys remained ephemeral. Renewal of the newest token at a later deadline, hash-algorithm migration and third-party operational validation remain separate evidence.

At code revision `e241fac`, all **43 export, security, status and renewal checks** passed with OpenSSL 3.5.9 selected. Ruff, mypy and requirements traceability passed.
