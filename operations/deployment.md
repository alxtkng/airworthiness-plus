# Deployment

Step 8 of private beta. Date: 19 November 2026.

## Status

The service has not been deployed on a server of our own, because there is none. What is below describes how it is deployed when a server is rented. It was built and rehearsed in the build environment; the section What Is Checked on the Server lists what remains.

Corrected 20 November 2026: this document was written for an existing Coolify server, whose address and access were said to be held by Alex King. He searched for it on 20 November 2026 and there is none. There is no budget for a server now. Until one is rented the service runs only as the test site, with the sample organisation (`test-site.md`).

20 November 2026: the server was not reached. Its address and access were not to hand, and nothing answered over HTTPS at `airworthiness.co` or `www.airworthiness.co` when asked from the build session. Step 1 below is still to be done. Alex King asked for a test site first, at no cost: `test-site.md` (ADR-0003). It holds the sample organisation only, and nothing in this document is met or changed by it.

## What Runs

| Part | What It Is | Notes |
|---|---|---|
| The service | The image built from `Dockerfile`: the application and its static files, run by Gunicorn as a user that owns nothing | Base image pinned by digest; dependencies from `uv.lock` with hashes; no `.git`, tests or development tools inside. The pipeline builds it on every change |
| The database | PostgreSQL 16 or later, 18 preferred | Two roles: an owner, used only for migrations and setting up an organisation; and a login for the service, which is a member of `airworthiness_application` and nothing more (ADR-0002) |
| The reverse proxy | The server's own | Ends HTTPS and passes requests to port 8000 of the service |

The service makes no outbound connection except to its database.

## Settings

Every setting comes from the environment (`src/airworthiness_plus/environment.py`). A missing required value stops the service.

| Name | Required | Value |
|---|---|---|
| `AIRWORTHINESS_SECRET_KEY` | Yes | At least 50 random characters, made on the server and kept only there. Changing it ends every session |
| `AIRWORTHINESS_MANAGED_DEVICES_ONLY` | No | Set to `true` only if access is restricted to managed, single-user devices. This sets the deployment's idle limit to 60 minutes. Shared or mixed-device deployments use the 30-minute default |
| `AIRWORTHINESS_ALLOWED_HOSTS` | Yes | The service's host name, and nothing else |
| `AIRWORTHINESS_DATABASE_NAME`, `_USER`, `_PASSWORD`, `_HOST`, `_PORT` | Name and user | For the service: the login role. For migrations: the owner |
| `AIRWORTHINESS_DATABASE_OWNER_WORK` | No | `true` only for migrations and setting up an organisation. Never set for the running service |
| `AIRWORTHINESS_BEHIND_PROXY` | No | `true` in the image. The address logged is then the one the proxy saw |
| `AIRWORTHINESS_STATIC_ROOT` | No | Set in the image |
| `AIRWORTHINESS_DEBUG` | No | Never set on the server |

## First Deployment

Each step is run by Alex King, or by Claude with him present. Passwords are typed by him.

1. Look at the server without changing anything: free memory and disk, what else runs, which ports answer. Record the result here.
2. Create the database and the two roles. The owner needs the right to create a role, for the first migration only.
3. Run the migrations as the owner: `python -m django migrate`, with `AIRWORTHINESS_DATABASE_OWNER_WORK=true`.
4. Set up the organisation as the owner: `python -m django seed_sample_organisation` for the sample, or `set_up_organisation` for a real one.
5. Start the service with the login role's settings. Check `/health/` answers OK.
6. Point the reverse proxy at it and work through What Is Checked on the Server.
7. Set up backups (`backup-and-restore.md`) before anything is entered that matters.

## The Reverse Proxy

The application depends on the proxy for these. Each is checked on the server.

| Need | Why |
|---|---|
| HTTPS only, TLS 1.2 and 1.3, a publicly trusted certificate | OWASP ASVS 5.0, 12.1.1, 12.2.2 |
| `X-Forwarded-Proto` and `X-Forwarded-For` set by the proxy, replacing anything the client sent | The application trusts them (ASVS 4.1.3). A client must not be able to claim HTTPS or an address |
| The `Host` header passed through unchanged | The application refuses any host but its own |
| A limit on the size of a request, 2 megabytes | Threat TH-007. The application allows 1 megabyte for a form or a file |
| A limit on the rate of requests for each address | ASVS 2.4.1, 15.2.2. The application locks sign-in after 5 failures and limits the export of an organisation to 6 in an hour, but does not limit the rate of requests |
| The service reachable only through the proxy | Port 8000 is not published to the internet |
| A host name of its own for this service | ASVS 3.5.4. Cookies are for that host alone |

## What Is Checked on the Server

These are the rows of `assurance/asvs.md` marked To Be Verified at Deployment, with how each is shown.

| ASVS | Check |
|---|---|
| 2.4.1, 15.2.2 | Many requests from one address in a short time are slowed or refused by the proxy |
| 3.5.4 | The service has its own host name |
| 4.1.3, 15.3.4 | A request sent with a forged `X-Forwarded-For` is logged with the real address |
| 4.2.1 | The proxy and Gunicorn are current versions; a malformed request is refused by the proxy |
| 12.1.1, 12.1.2, 12.2.2 | A scan of the TLS versions, ciphers and certificate from outside |
| 12.3.1 to 12.3.4 | How the proxy reaches the service, the service its database, and the backup its storage; which of those cross a network that others share |
| 13.2.1, 13.2.3 | The database roles have their own long random passwords; no default credential anywhere |
| 13.2.4, 13.2.5 | The service cannot open a connection to the internet |
| 13.3.2 | Who can read the server's environment values |
| 13.4.1 | The running image has no `.git` folder. The pipeline checks this on every build |

## Rehearsal, 19 November 2026

Run in the build environment, not on the server. PostgreSQL 16, a database owned by a role that is not a superuser, the service as a login role that is a member of `airworthiness_application` only, Gunicorn with two workers, and a TLS-terminating proxy in front that overwrites the forwarded headers.

| Step | Result |
|---|---|
| Migrations as the owner | Applied |
| `seed_sample_organisation` as the owner | 7 aircraft, 4 directives, 4 sets of maintenance data, 7 certificates |
| `collectstatic` | 6 files |
| `/health/` over plain HTTP inside | 200, OK |
| A page over plain HTTP | 301 to HTTPS |
| A request for another host name | 400 |
| Response headers | Content Security Policy, Strict Transport Security for a year with subdomains, no-store, nosniff, frame options, as `tests/test_security.py` expects |
| Sign-in in Chromium: password, authenticator set-up, code | Reached the Fleet |
| Cookies | `__Host-sessionid` and `__Host-csrftoken`, Secure, HttpOnly, SameSite Lax |
| Fonts | Geist loaded from the service |
| Table rows | 6 rows, each one line; a row opened on click, with `aria-expanded` set |
| A script added to the page by hand | Refused by the Content Security Policy |
| Requests to any other site | None |
| Sign out, then the home page | Back to sign-in |
| Access log | Second Factor Set Up, Signed In, Signed Out, each with the address the proxy saw, not the one the client claimed |

One thing the rehearsal taught: with HTTPS only pretended by a header, Django refused the sign-in because the page's origin did not match. That is the forgery protection working, and it means the proxy must really end HTTPS.

The image itself could not be built in the build environment, which has no container service. The pipeline builds it.


### Passkeys

Publish one supported HTTPS sign-in hostname and keep it stable. Passkeys are bound to that hostname. If it changes, use the password and authenticator app to sign in and enrol new passkeys. Use the reverse proxy's verified HTTPS signal for the application as described above.
