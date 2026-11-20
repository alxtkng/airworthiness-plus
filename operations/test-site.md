# The Test Site

Date: 20 November 2026. Decision: `architecture/decisions/ADR-0003-test-site.md` (Issues 96 and 98).

## Status

Made on Render by Alex King on 20 November 2026, from the Blueprint, at commit `9c33a95`. It answers at `https://airworthiness-plus-test.onrender.com`. The first sign-in is still to be done. What was seen of it is under First Deploy.

## What It Is

The service as the image builds it, on Render's free plan, with the sample organisation of `design-system/SampleData.md` and no other record. It is for trying the service before the server exists. **No real record is ever entered on it.**

It is not the server. `deployment.md` describes the server and is unchanged.

## What Runs

| Part | What It Is | Notes |
|---|---|---|
| The service | The image built from `Dockerfile`, unchanged | Free plan, Frankfurt. Sleeps after 15 minutes without a request; the next request waits about a minute |
| The database | PostgreSQL 18, free plan | Closed to every address outside Render's own network. Deleted 30 days after it is made |
| The proxy | Render's | Ends HTTPS and sends plain HTTP to port 8000 of the service |
| The set-up | `render.yaml` at the root of the repository | The whole of it. Checked against Render's published schema on 20 November 2026 |

## How It Starts

Render gives a free service no way to run a command before it starts and no terminal. So each time the container starts, `airworthiness_plus.sample.test_site` does the owner's work and then becomes the service:

1. `manage.py prepare_test_site` runs as the owner of the tables:
   - It refuses any database it did not find empty and mark as the test site's own.
   - It brings the tables up to date.
   - It makes the role the service signs in as, a member of `airworthiness_application` and nothing more, or sets that role's password again. An existing role that is anything else is refused.
   - It sets up the sample organisation, if it is not there.
2. The service is started by the `Dockerfile`'s own command, in place of the program, with every `AIRWORTHINESS_TEST_SITE_` value removed from its environment. The running service holds its own role's credentials and no others (ADR-0002).

If step 1 fails, the service is not started and Render shows the deploy as failed.

## Secrets

None is in the repository, none is typed by anyone, and none is given to an assistant. Render generates each when the test site is made.

| Value | What It Is For | Made By | Who Can Read It |
|---|---|---|---|
| `AIRWORTHINESS_SECRET_KEY` | The application's signing key | Render: 256 random bits, 44 characters. The server's rule of 50 characters stands for the server | Whoever can sign in to the Render account |
| `AIRWORTHINESS_DATABASE_PASSWORD` | The service's role | Render | As above |
| `AIRWORTHINESS_TEST_SITE_OWNER_PASSWORD` | The owner of the tables | Render, with the database | As above. Never in the running service |
| `AIRWORTHINESS_TEST_SITE_ADMINISTRATOR_PASSWORD` | The sample Administrator's first password | Render | As above. Never in the running service. It is the password at the first sign-in only: changing it in Render afterwards changes nothing |

## Making It

Done once by Alex King. Nothing is installed on his computer.

1. Merge the pull request, so that `render.yaml` is on `main`.
2. At render.com, sign up with the GitHub account. Choose the free plan.
3. Choose New, then Blueprint. Give Render access to the `airworthiness-plus` repository and choose it.
4. Render lists one web service and one database, both free. Apply.
5. Wait for the service to show as live. The first build takes several minutes.
6. Open the service's address, which ends `.onrender.com`. The sign-in page appears.

## Signing In

1. In Render, open the service `airworthiness-plus-test`, then Environment. Show the value of `AIRWORTHINESS_TEST_SITE_ADMINISTRATOR_PASSWORD`.
2. Sign in as `accountable.manager@your-organisation.example` with that value.
3. Set up an authenticator application when asked. Every user has two factors, here as on the server.
4. The other sample users have no password. The Administrator gives each a first password on the Users page (`user-administration.md`).

Five failed sign-ins lock a user name for 15 minutes. The address is public, so anyone can cause that. It passes on its own.

## When Something Changes

- A change merged to `main` reaches the test site after the pipeline has passed, and not before.
- A change to `render.yaml` is applied by Render when it is merged.
- A migration is applied at the next start, by step 1 above.

## When the Database Is Deleted

Render deletes a free database 30 days after it is made, after warning by email. The sample is lost; nothing else was ever there.

1. In Render, delete the database `airworthiness-plus-test-database` if it is still listed.
2. Open the Blueprint and sync it. Render makes a new, empty database.
3. Deploy the service again. The start makes the tables, the role and the sample afresh.
4. Sign in as under Signing In. Authenticators are set up again.

## Removing It

In Render, delete the service, then the database, then the Blueprint. Nothing is left, and nothing on the server or in the repository depends on it.

## What It Shows, and What It Does Not

| Shown | Not Shown |
|---|---|
| The image runs outside the build environment | Any of the 17 checks of the server and its proxy (`deployment.md`) |
| The two database roles work on a hosted database whose owner is not a superuser | Backup and restore (REQ-150 to REQ-153): the free database has none |
| Sign-in, the second factor and the pages over real HTTPS | Rate limiting, request size limits and forwarded-address handling by our own proxy |
| The sample as a user sees it | Any exit item of `assurance/readiness-review.md` |

The address logged for a request is the last one in `X-Forwarded-For`. Behind Render's proxy that may be one of Render's own addresses, not the visitor's. It is to be looked at on the first sign-in and recorded here.

## Rehearsal, 20 November 2026

Run in the build environment, not on Render. PostgreSQL 16 with password sign-in (SCRAM-SHA-256) over the network, a database owned by a role that is not a superuser and may create roles, as a hosted database's is. The environment was the one `render.yaml` describes, and the start command was read from `render.yaml`.

| Step | Result |
|---|---|
| `render.yaml` against Render's published schema | No error. A wrong plan name was refused, so the check can fail |
| First start, empty database | Database marked; migrations applied; Service Role Made; Sample Organisation Set Up |
| Second and third starts | Service Role Password Set Again; Sample Organisation Already Set Up |
| A start with a different password for the service's role | The role's password set to it. The database then accepted the new password and refused the old |
| The service's role, read from the catalogue | May sign in; no power of its own; member of `airworthiness_application` only; password stored as SCRAM-SHA-256 |
| The running Gunicorn processes, read from the operating system | Database user `airworthiness_service`; no `AIRWORTHINESS_TEST_SITE_` value and no owner-work flag in any of the three |
| `/health/` over plain HTTP, as the host's check asks it | 200, OK |
| A page over plain HTTP | 301 to HTTPS at the host name |
| A request for another host name | 400 |
| Sign-in as the Administrator with the generated first password | Accepted; the authenticator set-up page followed |
| Sign-in with a wrong password | Refused |
| Memory, Gunicorn and two workers | About 140 megabytes, of 512 allowed |
| The tests | 680 pass: the 657 from before and 23 new, in `tests/test_test_site.py` |
| The new tests against deliberate faults | Eight faults put into the code one at a time; each was caught |

One thing the rehearsal found: the owner of the tables, when not a superuser, is shown no organisation's rows, because row-level security is forced on the owner too (ADR-0002). So the check in `seed_sample_organisation` that the sample is already set up finds nothing on such a database, and a second run is stopped only by the user name being taken. `prepare_test_site` asks as the sign-in page does, by user name. The command for the server is left as it is and the point is recorded for the server's first deployment.

## First Deploy, 20 November 2026

Alex King signed up to Render and applied the Blueprint. Render made the database and the web service from `render.yaml` at commit `9c33a95`. The health page answered within about 6 minutes of the Blueprint being applied.

Seen from the build session, from outside, with no sign-in:

| Asked | Answer |
|---|---|
| `/health/` | 200, OK. The service reaches its database as its own role |
| The home page | 302 to `/sign-in/?next=/` at the same host, over HTTPS |
| The sign-in page | 200, titled Sign In, with the user name and password fields |
| The stylesheet and the script | 200, from the service itself. The page asks for nothing from any other site |
| Response headers | Content Security Policy with `default-src 'none'`; Strict Transport Security for a year with subdomains; no-store; nosniff; frame options DENY; referrer policy same-origin; opener policy same-origin |
| The forgery-protection cookie | `__Host-csrftoken`, Secure, HttpOnly, SameSite Lax |
| What answers behind the proxy | Gunicorn, by Render's own header |
| A path that does not exist, `/admin/` | 404 |

Not done from the build session: no sign-in was tried, with a right password or a wrong one. The certificate and the TLS versions were not read, because the build session's own proxy stands between it and the site.

## Expected of Render, and What Was Seen

| Expected | Seen on 20 November 2026 |
|---|---|
| The free plan builds and runs a `Dockerfile` service | Yes. The service is live and Gunicorn answers |
| Render sends requests to port 8000, set by `PORT` | Yes. The sign-in page appears at the `.onrender.com` address |
| The database's user may create a role and owns its database | Yes, by what followed: the service starts only after the owner's work has finished, and it signs in to the database as the role that work makes. The deploy's own log was not read from the build session |
| Render sets `X-Forwarded-Proto`, so the service knows a request came over HTTPS | Yes. The home page redirects once, to sign-in, and not without end |
| The service's host name is the one in `RENDER_EXTERNAL_HOSTNAME` | Yes. The host name is `airworthiness-plus-test.onrender.com` and no request was refused with 400 |
| A free database may be closed to all outside addresses | The Blueprint applied without error. That the database refuses an outside connection was not tried |
| The free plan asks for no payment card | To be confirmed by Alex King |

## Still to Be Seen

| What | When |
|---|---|
| The first sign-in as the sample Administrator, and the authenticator set-up | By Alex King |
| The address the access log records for that sign-in: the visitor's, or one of Render's | At the first sign-in |
| Two-factor sign-in on the Render account | To be confirmed by Alex King |
