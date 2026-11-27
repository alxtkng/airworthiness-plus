# ADR-0005 Passkeys and Recent Verification

Use a passkey with user verification as the first sign-in option. The account name identifies the user and the device asks for a fingerprint, PIN or security key verification. Require user verification during enrolment and at each use. The password and authenticator app remain the account setup and recovery path.

The server validates the passkey signature, challenge, origin, site and account. Each challenge expires after three minutes, belongs to the browser session and is consumed once. Credential identifiers and public keys stay out of history and exports. Enrolment, removal, sign-in and repeat verification are visible in the access log.

Browser sessions last up to 12 hours. The idle limit is 30 minutes, or 60 minutes for a deployment restricted to managed, single-user devices. Normal activity in multiple tabs uses the same session. Sign-out, account deactivation and credential resets still end sessions on the server. Removing a passkey ends the account's other sessions.

Use verification from the last five minutes for passkey changes, account recovery, user privilege changes and airworthiness review certificate issue or extension. When the session is older, use a passkey or the current password and a fresh authenticator code. Verification rotates the session key and leaves the original sign-in time in place.

Sources [NIST SP 800-63B-4, AAL2](https://pages.nist.gov/800-63-4/sp800-63b/aal/#aal2), [OWASP ASVS 5.0, V7](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x16-V7-Session-Management.md), [NCSC guidance on passkeys](https://www.ncsc.gov.uk/passkeys).
