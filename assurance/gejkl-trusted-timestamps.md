# G-EJKL trusted timestamp rehearsal

28 November 2026. This extends the [signed G-EJKL handover trial](gejkl-signed-handover.md). The original and corrected archives and the two detached Ed25519 signatures were carried forward byte for byte. A local synthetic timestamp authority issued an RFC 3161 response for each already-existing signature. Each message imprint is SHA-256 over the decoded 64 bytes of the corresponding detached signature. The timestamp authority used its own key and certificate chain. The two reading signatures use their existing key and scoped grant. [RFC 3161](https://www.rfc-editor.org/rfc/rfc3161.html)

## Trust and verification

- The sender route supplies the archive, the detached signatures and the timestamp responses. The simulated custodian route supplies the existing reading trust file and pin, plus a separate TSA root PEM and SHA-256 pin. The receiver anchors TSA validation to that root. A token's embedded certificate provides the candidate signer.
- The issuer checks each response against its request, including the request nonce. The receiver independently checks the imprint against the exact detached signature bytes, the CMS and TSA certificate evidence, the permitted synthetic policy and the certificate validity at `genTime`. The archive, reading signatures and grants are checked before timestamp verification. All checks precede the SQLite import. [OpenSSL timestamp command](https://docs.openssl.org/3.5/man1/openssl-ts/)
- The token establishes that the exact signature existed by the timestamp authority's recorded time under this synthetic trust setup. The signing instant remains signer-asserted, and synthetic grant checks retain their original basis at the claimed signing times. The timestamp authority used the local UTC clock. External clock assessment, qualified TSA status, operational revocation evidence and independent proof of exact signing time remain open.
- The retained responses have the same second-resolution `genTime` and provide no independent ordering of the two signatures. The correction relationship is authenticated by the signed predecessor digest. LibreSSL also checks certificate validity at verification time. On this backend, replay of the public artifacts can be refused after certificate expiry. This rehearsal uses a 90-day TSA signing certificate and 365-day root. Long-term archival validation remains open.

## Reproduce

Run with the locked Python environment, disposable PostgreSQL and a local OpenSSL or LibreSSL executable on the path.

```sh
PYTHONPATH=src uv run pytest -q \
  tests/test_exports.py::test_signed_gejkl_trial_reconstructs_and_verifies_both_readings_offline
```

For retained artifacts, use a fresh SQLite path and add these receiver arguments to the [signed import command](../architecture/decisions/ADR-0010-aircraft-transfer-pilot.md#signed-reading-rehearsal). Supply the TSA root and its pin independently of the sender bundle.

```sh
--timestamps sender/03-timestamps.json --tsa-root custodian/tsa-root.pem \
  --tsa-root-sha256 "$tsa_root_pin"
```

When present, these three arguments and the signed evidence inputs form a complete set. The new result contains `trusted_timestamps`, `tsa_root_sha256` and `timestamp_assurance` alongside the original signature and authority results. Signed imports with no timestamp inputs retain their earlier signer-asserted result.

## Recorded result

The retained G-EJKL pair passed on code revision `81f18b8` using LibreSSL 3.3.6. The receiver and native verifier ran with operating-system network access denied. The subsequent [historical status trial](gejkl-historical-timestamp-status.md) exercises OpenSSL 3 with these retained responses.

| Check | Result |
| --- | --- |
| Original 11,208.6-hour signature | Verified RFC 3161 response at 10:49:58 UTC on 28 November 2026. TSA serial `D4A9B746F4415B3E33BAE019BAFF2830`. |
| Corrected 11,206.8-hour signature | Verified separate response at 10:49:58 UTC on 28 November 2026. TSA serial `49D52D72076C0E21AA7B780F2C5D3A74`. |
| Receiver reconciliation | The earlier archive, signature, defect and inspection findings match the previous verdict. Import took 0.130 seconds locally. Replay reported `imported=false` and the database retained one snapshot. |
| Refusals on retained evidence | A mismatched root pin, swapped responses and a missing response failed. The saved snapshot remained unchanged. |
| Fixture regression | Also refused a missing pin before opening SQLite, an unrelated pinned root, a malformed response and a valid response for the wrong signature imprint under the same TSA. **41 export and security checks passed** with zero skips or failures. Ruff, mypy and traceability passed. |

The public evidence is retained in the local `gejkl-timestamped-trial-2026-11-28` directory. The sender folder contains the unchanged archives and detached signatures plus the two individual DER responses and their transfer envelope. The custodian folder contains the original signer trust and the new TSA root and pin. The receiver folder contains the verdict, refusal and replay results, fixture refusal results and the SQLite snapshot.
