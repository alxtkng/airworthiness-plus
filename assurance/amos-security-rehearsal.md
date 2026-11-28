# Synthetic security escalation rehearsal

28 November 2026. This local tabletop uses the [vulnerability management procedure](../operations/vulnerability-management.md), the [threat model](../architecture/threat-model.md) and the [ASVS record](asvs.md). OWASP ASVS supplies application verification requirements. ISO/IEC 27001 describes an organisational information security management system. The local exercise does not establish assessment or certification status. [OWASP ASVS](https://asvs.owasp.org/) · [ISO/IEC 27001](https://www.iso.org/standard/27001)

| Role | Scenario action | Recorded outcome |
| --- | --- | --- |
| Reporter | Supplies a synthetic report that an authenticated receiver may have seen someone else's aircraft export. | Rehearsal reference AMOS-SYNTHETIC-010. Scope is the code and the two sample organisations. |
| Security owner | Classifies the report against TH-020, REQ-003 and REQ-132 and sets the release decision for the exercise. | Cross-organisation record access would rate High. Release remains held pending verification. Plan reporter acknowledgement and first assessment using the times in SECURITY.md. |
| Release owner | Requests existing isolation, export and authority checks on the candidate. | All 18 checks in `tests/test_security.py` passed on integrated revision `6e2f78b`. The same selection passed the database record rules and the maintenance history browser check that refuses a foreign aircraft route. See the validation record for the full candidate results. |
| Security owner | Drafts a decision after retest. | Existing checks provide scoped evidence. Preserve the report and drill result. A real subscriber communication would describe impact and correction after confirmation. This exercise creates no real disclosure or confirmed vulnerability. |

The independent assessment, scope and deployment evidence remain with Airworthiness Limited and the commissioned assessor. [Independent assessment issue 40](https://github.com/alxtkng/airworthiness-plus/issues/40)
