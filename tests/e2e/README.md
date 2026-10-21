# I02 real-browser login and access gate

This suite uses npm-locked Playwright Test 1.64.1 and its Chromium browser.
Every successful journey uses native Quezo forms, the actual Keycloak login UI,
the built Next server/session facade, a separate Uvicorn/FastAPI process, real
JWT/JWKS validation and migrated PostgreSQL. No injected browser cookies/tokens,
password grants, request interception, mocked actors or runtime bypasses.
Master-realm administration is confined to the existing explicit setup helper.

## Install and run

From the repository root, with Node 22+/npm 10+, uv 0.12.17, Python 3.12+ and
a running **local** Docker engine with Compose:

```powershell
npm ci
uv sync --directory postgres --locked
npx playwright install chromium
npm run test:e2e
```

On Linux/CI install Chromium's OS dependencies too:

```text
npx playwright install --with-deps chromium
```

No `.env` or manually supplied credentials are needed. Do not point this command
at an existing realm, development volume, external database or shared server.
Remote Docker contexts are refused. Allow roughly 7 minutes for the browser
command: the expiry scenario actually waits the unchanged 300-second token
lifetime. It does not edit clocks/session rows or configure refresh tokens.

Run **all assignment checks**, then the same complete browser suite, with one
owned isolated dependency lifecycle:

```powershell
npm run test:e2e -- --checks
```

This executes, fail-fast, the exact root scripts `npm run typecheck`, `npm test`,
`npm run build`, `npm run api:check`, `npm run test:contracts`, `npm run test:db`,
`npm run test:identity`, `npm run test:identity:integration` and
`npm run test:web:production`. The actual-provider HTTP test removes its owned
realm before browser provisioning. Root `npm test` still does not run browsers.
`npm run typecheck` now also type-checks these TypeScript fixtures.

For a focused regression or the repeatable working-foundations demonstration:

```powershell
npm run test:e2e -- --grep "native login|negative control"
npm run test:e2e -- --grep "native login|navigation|persisted session"
```

Filtered runs are not complete AT-01 evidence. The `browser` CI job runs the
unfiltered command on Ubuntu/Node 22/Python 3.12 without duplicating the existing
Node/Python check matrices. A configured job is not a claimed hosted result.

## Fixture ownership, startup and cleanup

`postgres/tests/run_browser.py` generates a unique `quezo-i02-<12 hex>` Compose
project, four distinct loopback ports and distinct random synthetic secrets.
It ignores `.env` and inherited Compose/connection configuration. Only
`postgres-test` and `keycloak-test` start, with tmpfs storage and no development
volumes. PostgreSQL uses the existing role/bootstrap/control-marker scripts.
Keycloak discovery must return 200 before provisioning. `db_helpers` supplies
its guarded UUID-named database, migrations and non-FORCE ownership-checked drop.

The launcher uses the equivalent of these commands (the project and ports are
printed; secret values remain only in setup-process environments):

```text
docker compose --env-file <OS-null-device> -f <checkout-compose.yaml> -p <owned-project> --profile test --profile identity-test up -d --wait postgres-test keycloak-test
docker compose --env-file <OS-null-device> -f <checkout-compose.yaml> -p <owned-project> --profile test --profile identity-test rm -s -f postgres-test keycloak-test
docker network rm <owned-project>_default
```

`<OS-null-device>` is `NUL` on Windows, `/dev/null` on Linux. The command builds
Next, migrates a fresh database to `0004_identity`, and calls I01's allowlisted
synthetic provisioner for administrator, author, learner, combined and empty
roles, each with a separate generated password. Only the newly created realm's
`quezo-web` client is configured with the exact chosen web origin and callback.
Issuer remains the exact chosen Keycloak origin plus `/realms/quezo-local`;
scope/audience remain `openid quezo-api` / `quezo-api`. No wildcard redirects,
existing-realm overwrite or applied-migration edit.

`fixtures.ts` starts only its own built Next and Python/Uvicorn child processes.
It verifies provider discovery, API liveness after startup and the signed-out
web/session-store response before browser navigation. The web gets only its
restricted `quezo_web` connection and confidential-client configuration; the API
gets only `quezo_runtime` and issuer/audience settings. Admin/migration/synthetic
password variables are not inherited by either application.

The runner's `finally` stops/removes its two containers and network, including
on assertion/setup failure. Workers close contexts, child processes and pools
before the guarded database drop. Timed-out/interrupted commands kill only their
own process tree (Windows PID tree; POSIX process group). An uncatchable host
termination cannot execute `finally`: inspect the printed exact project first,
then remove only its two named containers and network. For example, substituting
the **actual printed owned project**, not a development project:

```text
docker ps -a --filter label=com.docker.compose.project=<owned-project>
docker rm -f <owned-project>-postgres-test-1 <owned-project>-keycloak-test-1
docker network rm <owned-project>_default
```

Never use volume deletion, broad process-name termination, or drop a caller-supplied
database. The normally completed command leaves no services running.

## Acceptance scenarios

`access.spec.ts` contains 16 cases; final execution evidence and EX-I02-01's
original red/green observations are recorded in
[DEVELOPMENT.md](../../docs/DEVELOPMENT.md#i02-integrated-browser-gate).

| Scenario | Evidence |
| --- | --- |
| EX-I02-01 negative control | Browser-only `no-referrer` meta-policy reproduces null Origin and 403 for both native forms; this is not used for successful journeys |
| Native login/logout | Normal configured pages send exact Origin, complete callback, invalidate the durable session, rotate on re-login; provider SSO and the old access token remain valid after **local** logout |
| Five role cases | Administrator, author, learner, combined and empty roles match real `/me`, do not inherit other navigation, survive reload, and expose no credentials in DOM/storage |
| Durable/keyboard path | Built-web restart preserves session; actual Tab/Enter login, skip link, provider password focus, workspace anchor and logout work |
| Role revocation/account disable | Old session/token loses removed author role immediately; disabled account gets 403, local session is deleted and provider SSO cannot reactivate it |
| Inactive mapping | Old token receives 401 and existing browser session expires |
| Direct API validation | No token, malformed and tampered tokens fail; real signed Keycloak tokens fail under a wrong expected audience or issuer (same actual provider keys through loopback alias) |
| Callback protections | Wrong state, missing browser binding and replay of a real completed callback fail with 401 and an actionable error |
| CSRF | Actual different-origin browser form is rejected without logout; supplemental missing/null/foreign Origin HTTP probes cover both routes |
| API/database outages | Stop actual API; sever each application's byte-forwarding PostgreSQL transport separately; explicit errors, no authenticated navigation/cache, real recovery |
| Identity outage | Pause owned Keycloak: warm keys work within TTL, expired/cold caches give 503, cold web discovery gives an actionable error, recovery revalidates |
| Actual expiry | Wait full provider lifetime; retained opaque cookie cannot restore session; old token receives 401; no refresh or injected expiry |

The database fault transport forwards bytes unchanged to actual PostgreSQL.
It is not a database substitute or an HTTP peer. Closing listeners and live
sockets creates real connection failures without destroying the tmpfs cluster.
The identity test uses approved bounded API settings: key TTL 10s, refresh
cooldown 1s, identity timeout 1s; API pool wait is 1s. Session defaults and
provider token lifetime remain unchanged. Fixture-only SQL revocations are
explicitly restored in `finally`; runtime provisioning never restores access.

There are no product role-protected routes yet. I01's retained lower-level
`test_identity_access.py` directly tests role/ownership denial independently of
navigation, including administrator non-inheritance. Those controlled-peer
checks **supplement**, not replace, the real browser/API journeys above.
F03's existing PKCE/nonce/replay/host/cookie tests remain required too.

## Evidence privacy and limits

Trace, video and screenshots are off. No HAR or storage-state export is used.
`safe-reporter.ts` prints static case names, status/duration, failure location
and non-sensitive classifications, never Playwright's raw error/call logs.
Automatic failure-context attachments are discarded; `preserveOutput: never`
and a temporary results directory removed in `finally` prevent retention.
CI uploads no browser artifacts. Do not enable debug HTTP logging or add a
standard HTML/blob reporter without a separate credential-redaction review.

Tokens, passwords, opaque login/session values and callback values are compared
in memory against rendered DOM/storage and captured application logs. Cookies
are intentionally stored by the browser: local cookies must be HttpOnly,
SameSite=Lax, host-scoped, path `/`, and unreadable through `document.cookie`.
The shared `Secure`/`__Host-` policy remains covered by configuration/cookie unit
tests; this loopback HTTP suite does not claim shared TLS deployment proof.
The suite also checks no direct browser API/token calls, no callback referrer
disclosure and empty localStorage/sessionStorage.

This is the working-foundations demonstration, not A01 account management,
assessment workflows, Q02/WCAG, full P0, hosting or pilot acceptance. Keyboard
observations are automated Chromium focus checks, not a human screen-reader
audit. C01/T01 should reuse the login/session fixtures and add their own real
business routes, authorization and lifecycle scenarios after separate dispatch.
