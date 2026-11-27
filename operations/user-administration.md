# User Administration

Step 8 of private beta. Date: 19 November 2026. REQ-005 to REQ-010; OWASP ASVS 5.0, 6.4.1, 6.4.3, 6.4.4, 7.5.1.

This is the procedure for an organisation's Administrator. The system enforces what it can; the steps marked By Hand are the Administrator's to do and cannot be enforced by software.

## A New User

1. The Administrator adds the user on the Users page: full name, user name (their email address) and roles. The system makes a first password and shows it once, on the page that follows. It is not shown again; if it is lost before it is passed on, give the user a new one.
2. **By Hand.** The first password reaches the person by a route that is not this system and not the same route as their user name: in person, or by telephone to a number already known.
3. At first sign-in the user sets up an authenticator application and must change the password before any other page answers.
4. After changing the password, open **Passkeys** to add a fingerprint, device PIN or personal security key. Use the passkey for routine sign-in and keep the authenticator app for recovery. On a shared terminal, use a personal security key or phone.
5. A first password works up to the seventh day after the day it is given. After that the Administrator gives a new one.
6. A role is given only for what the person does. Airworthiness Review Staff also need a review staff record with their authorisation (Authorisations page); the role alone does not let them review.

## A User Who Leaves, or Changes Job

1. Make the user Inactive the day they leave. Their sessions end at once. Nothing they did is removed and their name stays on it.
2. For review staff, record the day they left; their record is kept for 2 years after (CAO.A.045(e)).
3. A change of job is a change of roles, the same day.

## A Forgotten Password

1. **By Hand.** Make sure the request comes from the person: speak to them, in person or on a number already known. A request by email alone is not enough.
2. Give them a new first password on the Users page and pass it on as in A New User. Their sessions end, and they must change it at sign-in, within 7 days. The second factor is still asked for.

## A Lost Passkey

With another working passkey or the password and authenticator app, sign in and open **Passkeys**. Remove the lost key. Other sessions for the account end. Add the replacement from the same page. If no sign-in method remains, follow the reset procedure below.

## A Lost or Replaced Authenticator

This is the more serious request: with it and a password, someone can sign in as the user.

1. **By Hand.** Make sure of the person as carefully as when they were first given access: in person, or by a video call in which they are recognised. Never on a message alone.
2. Reset the second factor on the Users page. This revokes their passkeys and ends their sessions. At the next sign-in they set up an authenticator again, then enrol any replacement passkeys.
3. If the device was lost or stolen, not merely replaced, give a new first password as well.

Both acts are entered in the access log with the Administrator's name. Adding users, changing their roles or access and resetting sign-in methods require verification from the last five minutes. Use a passkey or enter the current password and an authenticator code. Requests to end a session also accept an authenticator code.

## A Lost Device, or Anything Suspicious

End the user's sessions on the Users page. Then reset the password or the second factor as above.

## The Administrator's Own Account

- An organisation always has at least one active Administrator; the system refuses to remove the last.
- **By Hand.** An organisation should have two, so that one can restore the other. With one, a lost authenticator means asking the service's operator, who will set a new one up only after the same proof of identity, by the owner of the tables on the server.
- An Administrator can reset another user's password and second factor, and so could sign in as them. Every such reset is in the access log, which the Administrator reads on the Access Log page and the organisation should read. The system does not prevent it; both resets require the Administrator's recent verification. Check their entries in the Access Log.

## Review

Every 6 months the Administrator reads the Users page against who works for the organisation, and makes Inactive anyone who should not be there. Proposed; to be confirmed.
