# G-EJKL signed handover trial

28 November 2026. The trial uses the normal aircraft utilisation and export services in a disposable PostgreSQL database, the synthetic G-EJKL fixture and the separate SQLite receiver. It covers a signed original utilisation reading and correction alongside one deferred defect and one recurring inspection. The [unsigned G-EJKL regression](amos-workflow-trial.md) remains separate.

## Sender, trust custodian and receiver

1. The sender records 11,208.6 hours for G-EJKL, exports the original reading and signs the archived JSON record. The sender retains that archive and its detached signature. The fixture then records 11,206.8 hours as a new entry superseding the original. The corrected export retains both readings, with the original record identical to the first export.
2. The sender signs the corrected reading and its correction reason. The signed correction carries both the original record ID and the SHA-256 digest of the original signed claim. The sender supplies the final archive, detached signatures, record identifiers and source manifest digest.
3. The fixture's trust custodian separately supplies a file with the enrolled public key, the aircraft-specific synthetic grant, their validity and status, and an independently supplied SHA-256 pin for that file. The signed envelope carries no key or trust anchor. The roles and delivery paths are simulated with separate file inputs. The receiver takes its trust pin as an input and compares the exact trust file's bytes to it.
4. The receiver uses a separate Python process and SQLite database. It has no Django settings or sender database credentials. The trial subprocess rejects Python socket operations. It verifies the archive and both signatures before opening SQLite for import. A repeat of the same evidence leaves one snapshot. Refusals preserve the original snapshot.

The detached signature uses Ed25519. It covers the versioned purpose, issuer, aircraft and reading IDs, the reading digest, predecessor IDs and digest, reason, signer, key and grant IDs, and the asserted signing time. The reading digest also binds the counter identity present in the archived row. This pilot canonicalises a JSON value as UTF-8 with sorted keys, compact separators, unescaped non-ASCII characters and non-finite numbers refused. The SHA-256 digests use lowercase hexadecimal, and signatures use standard padded Base64. Each signed time has whole UTC seconds. [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032.html)

The signer-asserted time is authenticated as part of the claim. It is checked against the archived creation event and the pinned trust file's validity and status. The exercise cannot independently establish the time at which the key was used. The grant establishes scope within the synthetic trial. The defect and inspection are reconciled from the integrity-checked archive and remain outside the two reading signatures. Independent timestamping and operational authorisation require their own evidence. [RFC 3161](https://www.rfc-editor.org/rfc/rfc3161.html)

## Reproduce

Run using disposable PostgreSQL and the locked repository environment. The test retains both sender archives and signatures, the separate public trust file and pin, and the receiver verdict, case results and SQLite snapshot beneath pytest's temporary directory. The private key is generated in memory.

```sh
PYTHONPATH=src uv run pytest -q \
  tests/test_exports.py::test_signed_gejkl_trial_reconstructs_and_verifies_both_readings_offline
```

The detached signature and trust file format and receiver command are documented in the [transfer ADR](../architecture/decisions/ADR-0010-aircraft-transfer-pilot.md).

## Recorded result

The signed trial passed on code revision `9b46633`. The run used PostgreSQL 16.14 for sender fixtures and SQLite in the separate receiver. The full export and application security selection passed **41 checks**, with zero failures or skips. The earlier fixture attempt exposed that the base G-EJKL sample does not have a programme. The passing run creates the synthetic programme before adding the inspection.

| Check | Observed result |
| --- | --- |
| Original and correction | Both detached signatures verified. The original was signed at 10:43:36 UTC and the correction at 10:43:37 UTC, as asserted by the signer. The receiver retained 11,208.6 and 11,206.8 hours, the signed correction reason and the verified link. |
| Integrity and issuer | Both claims matched the archived reading contents. The key matched the receiver-pinned synthetic trust file. |
| Time and authority | The pinned synthetic grant matched the issuer, signer, aircraft and purpose and was valid at both asserted times. Independent sign-time evidence remains indeterminate. |
| Deferred defect | Right Headset Socket Crackle stayed open and deferred. The receiver retained the report, restriction note and 25 November 2026 limit. |
| Recurring inspection | The receiver calculated 8 December 2026 from completion on 8 November and a 30-day interval, matching the sender forecast on the fixture's 18 November business date. |
| Import and replay | One SQLite snapshot. The first verify and import took 0.065 seconds locally. No record fields were rekeyed. Replay reported `imported=false`. |
| Invalid evidence | A mismatched trust pin, a changed reading in a repacked and internally consistent archive, an altered signed reason and a validly signed correction linked to the wrong original claim all failed. |
| Unknown or inapplicable evidence | Unknown key, missing grant, expired key or grant, revoked key and a grant for the wrong aircraft were refused. |
| Indeterminate or absent evidence | Historical status that ended before the claimed time was indeterminate. Missing trust inputs failed before the receiver database was created. The other refusals left the accepted snapshot unchanged. |

Retained evidence is grouped into sender, custodian and receiver directories in the local `gejkl-signed-trial-2026-11-28` folder. The receiver verdict contains the verified claims and reconstructed records. Its case results file records each observed refusal. The sender bundle and the custodian bundle contain synthetic data and public verification material.

The retained files were also imported and replayed in a fresh SQLite database under the same network guard. Its verdict matched the retained verdict and it contained one snapshot.

The subsequent [trusted timestamp rehearsal](gejkl-trusted-timestamps.md) verifies RFC 3161 proof of existence for these same two signatures. The original asserted signing times and scope findings remain visible.
