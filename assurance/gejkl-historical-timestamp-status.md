# G-EJKL historical TSA certificate and revocation trial

28 November 2026. The receiver assessed expiry and revocation with the application and native OpenSSL process under an operating-system network denial. Future instants were supplied as explicit test inputs. The system clock was unchanged.

The TSA certificate is the certificate at issue. The G-EJKL readings themselves still use their original detached Ed25519 signatures and separately pinned synthetic authority. The timestamp proves existence of each signature by its recorded time. The exact signing instant remains signer-asserted. [RFC 3161](https://www.rfc-editor.org/rfc/rfc3161.html)

## Retained tokens at the expiry boundary

Both original responses still contain the TSA time **10:49:58 UTC on 28 November 2026**. The TSA leaf's validity ended at **10:49:58 UTC on 26 February 2027**. The explicit future evaluation instant was one second later, with the pinned root still within validity.

| Verification | Result for both retained G-EJKL responses |
| --- | --- |
| Native OpenSSL path at recorded TSA time | Verified both. |
| Native OpenSSL path evaluated one second after leaf expiry | Failed both with `certificate has expired`. |
| SQLite receiver using historical time for token validation and the future instant for certificate status | Accepted both historical proofs and reported both TSA certificate findings as `Expired` at evaluation. Replay retained one snapshot. |
| Revocation status of the original TSA leaf | `Indeterminate`. The original TSA private key was discarded, so this arm used the retained public evidence with no original issuer CRL. |

OpenSSL 3.5.9 was built locally from the publisher's SHA-256-checked release without changing the system installation. In this arm, the native verification control exercised `-attime` separately at the recorded and future times. The receiver uses the signed TSA time for the historical native path and keeps the explicit evaluation time in its result. LibreSSL can complete the in-date checks but its timestamp command lacks `-attime` for post-expiry native validation. [OpenSSL downloads](https://openssl-library.org/source/) · [OpenSSL timestamp verification](https://docs.openssl.org/3.5/man1/openssl-ts/) · [RFC 5280 certificate validity](https://www.rfc-editor.org/rfc/rfc5280.html#section-4.1.2.5)

## Revocation scenarios

A new local synthetic TSA timestamped the byte-identical G-EJKL signatures at **10:58:33 UTC on 28 November 2026**. The issuer signed complete counterfactual CRLs, supplied through the custody path with the separate TSA root and pin. The general evaluation was **10:58:33 UTC on 29 November 2026**. The post-expiry evaluation was **10:58:34 UTC on 26 February 2027**, one second after the replacement TSA leaf expired.

| Signed CRL evidence | Receiver result for the G-EJKL pair |
| --- | --- |
| Complete in-date list with no revocation entry | Accepted both under the synthetic profile while the leaf was within validity at evaluation. |
| Cessation of operation effective at 10:57:33 UTC or exactly at 10:58:33 UTC | Refused the transfer. The timestamp certificate was revoked at or before the trusted time. |
| Cessation of operation effective at 10:59:33 UTC | Accepted both proofs, with `Revoked After genTime` for each. The same outcome held at the post-expiry evaluation using a fresh signed CRL that still listed the leaf. |
| Earlier revocation on a fresh CRL at post-expiry evaluation | Refused. |
| Later recorded revocation with an invalidity date before the TSA time | Refused. The earlier effective date controls. |
| Later key compromise or later revocation with the reason absent | Refused. The recorded time alone is insufficient to retain the earlier proof under this profile. |
| Stale CRL, unrelated issuer signature, or late clear CRL after leaf expiry | Refused with indeterminate status. An empty late list may omit a previously revoked expired certificate. |

The receiver authenticates the direct complete CRL against the pinned root, checks issuer validity at the CRL's signed `thisUpdate` and checks that the list covers the explicit evaluation instant and was issued at or after the token time. Scope excludes delta, indirect and partitioned CRLs. The synthetic tokens use whole-second times with accuracy unspecified and the recorded before and after cases are one minute apart. All refusal cases preserved the previously accepted SQLite snapshot. The three successful imports on the revocation arm each replayed with one snapshot. [RFC 3161 revocation guidance](https://www.rfc-editor.org/rfc/rfc3161.html#section-4) · [RFC 5280 CRL and invalidity date](https://www.rfc-editor.org/rfc/rfc5280.html#section-5)

## Reproduction and evidence

Use the [signed timestamp receiver command](../architecture/decisions/ADR-0010-aircraft-transfer-pilot.md#signed-reading-rehearsal) and add either an explicit assessment time or that time plus its complete issuer CRL. Use a fresh SQLite path for a different scenario.

```sh
--tsa-evaluated-at "$evaluation_utc" --tsa-crl "$issuer_crl"
```

Leaving out the CRL keeps the revocation finding indeterminate when an evaluation instant is supplied. Run the regression with OpenSSL 3 on the path for historical native validation.

```sh
PYTHONPATH=src uv run pytest -q \
  tests/test_offline_tsa_status.py tests/test_exports.py tests/test_security.py
```

The retained evidence is in the local `gejkl-historical-timestamp-trial-2026-11-28` folder. Its `retained-expiry` arm has the byte-identical retained responses, the native boundary controls and the receiver verdict. Its `revocation` arm has the replacement responses, public trust inputs, signed scenario CRLs, receiver verdicts and refusal results. The TSA keys were ephemeral. Long-term evidence renewal, external TSA clock assurance and operational trust remain outside the exercise.

At code revision `05f5657`, all **42 export, security and historical-status checks** passed with OpenSSL 3.5.9 selected. The historical-status fixture also passed with LibreSSL 3.3.6 while the fixture certificate was within its actual validity period. Ruff, mypy and traceability passed. The first OpenSSL 3 regression run exposed a missing executable path in the subprocess environment. The passing run forwards the selected path while the receiver remains isolated from sender settings.

The subsequent [evidence renewal rehearsal](gejkl-evidence-renewal.md) adds a distinct renewal TSA and verifies timing and status after actual expiry of the predecessor in the complete fixture.
