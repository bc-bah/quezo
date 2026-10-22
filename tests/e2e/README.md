# Real-browser identity, authoring and attempt-start gates

This suite uses npm-locked Playwright Test 1.64.1 and its Chromium browser.
Every successful journey uses native Quezo forms, the actual Keycloak login UI,
the built Next server/session facade, a separate Uvicorn/FastAPI process, real
JWT/JWKS validation and migrated PostgreSQL. No injected browser cookies/tokens,
password grants, request interception, mocked actors or runtime bypasses.
Master-realm administration is confined to the existing explicit setup helper.

**Accepted baseline:** B.C. accepted I02 and closed EX-I02-01 on 21 October 2026
after reviewing merged PR #7 and its passing browser/CI evidence. Phase 2 now
extends these fixtures with package-specific lifecycle journeys; use the
[Phase 2 handoffs](../../docs/implementation/PHASE-2-HANDOFFS.md).
An active package assignment does not remove its integrated-producer gate.
Keep the existing identity regressions and secret-safe reporting intact.

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
The expanded Python/database checks have a bounded 20-minute launcher timeout;
other check commands retain 10 minutes. This is a runner safety limit, not an
approved product performance target.

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
Next, migrates a fresh database to `0007_attempt_start`, and calls I01's allowlisted
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

C01 adds author-only product routes. I01's retained lower-level
`test_identity_access.py` and C01's `test_questions.py` test role/ownership denial
independently of navigation, including administrator non-inheritance.
Those controlled-peer checks **supplement**, not replace, the real browser/API journeys.
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

This is the working-foundations, C01 and C02 demonstration, not A01 account management,
full quiz delivery, Q02/WCAG, full P0, hosting or pilot acceptance. D01 additionally
demonstrates assignment/start/resume, not saving or submission. Keyboard
observations are automated Chromium focus checks, not a human screen-reader
audit. Later assigned packages should extend these same fixtures after their
producer gates, not introduce a second runner.

## C01 AT-03/04 initial cases

`questions.spec.ts` adds five real signed-in journeys to the existing discovery
configuration. Run a focused iteration with `npm run test:e2e -- --grep C01`;
the complete review gate remains `npm run test:e2e -- --checks`.

- Both MCQ and true/false: create/rename a bank, create/select/read a question,
  reload the exact revision, edit prompt/feedback/key/points, and select the old
  revision again. Actual API reads prove stable question/option IDs, distinct
  version IDs and byte-equivalent old content. Literal HTML-like input is not markup.
- A second author (the existing combined-role account), learner and
  administrator cannot obtain another author's prompt/key via lists, direct
  or nested API IDs, or rendered HTML/RSC. No second account provisioner is added.
- Two real tabs demonstrate stale-edit conflict with retained unsaved input;
  committed application-role revocation blocks a subsequent form save/read.
- Stopping the actual API leaves the form unsaved with a visible safe error;
  recovery permits an explicit save, never a fabricated success.

Existing identity scenarios are retained. The fixtures additionally check
assessment-content sentinels never appear in captured application logs. Traces,
screenshots, video, HAR and storage-state exports remain disabled. No raw
question/key payload is persisted as an artifact. Full search/category/tag,
move/archive management belongs to C03; two-quiz reuse and publication/attempt
preservation belong to C02 and later lifecycle acceptance, not these initial cases.

## C02 AT-04/05 publication cases

`quizzes.spec.ts` extends the same fixture/discovery path with three real-login
journeys. Focus with `npm run test:e2e -- --grep C02`; acceptance still requires
the complete `npm run test:e2e -- --checks`.

- Author creates both types, composes/reorders exact revisions with a point
  override, selects withheld policy, previews without private fields/writes,
  publishes and reloads. Two quizzes reuse a question; later question edits and
  an explicit new draft/publication leave the original published snapshot intact.
- Two tabs expose stale draft conflict while preserving unsaved edits. An actual
  API outage during publication displays failure; recovery retries the same
  command without claiming success prematurely.
- Actual signed-in API publication retries return identical acknowledgement;
  changed payload conflicts. A foreign author, learner and administrator cannot
  replay/read the quiz or disclose its content through HTML/RSC or preview.

Backend tests provide the real-database concurrency, rollback, independent policy
bounds, clean/prior-head migrations and immutable snapshot/ledger constraints.
No assignment, attempt, grade or timed learner UI is introduced here. Existing
privacy settings, content sentinels, disabled artifacts and owned-service cleanup
remain in force.

The 21 October 2026 local complete gate passed all 24 browser cases (16 I02,
5 C01, 3 C02) on Chromium 156.0.8078.4. Exact commands, environment, iteration
corrections and full database/web results are in the
[C02 review handoff](../../docs/DEVELOPMENT.md#c02-immutable-quiz-publication).
B.C.'s subsequent local-delivery acceptance is recorded in that handoff;
this browser run does not claim hosted CI or default-branch integration.

## D01 AT-06 assignment and start

`attempts.spec.ts` uses the same real-login fixtures and secret-safe reporter.
Focus with `npm run test:e2e -- --grep D01`; the required review gate remains
`npm run test:e2e -- --checks`.

The author creates and publishes an untimed quiz, selects an active learner by
application UUID, assigns and repeats the assignment. The actual learner lists,
starts, reloads and resumes that attempt. The case inspects application JSON and
HTML/RSC in memory for pre-start question disclosure and private key/feedback
leakage, verifies stored option IDs/order and one consumed allowance, and checks
foreign learner/author links and API IDs. Content sentinels remain excluded from
application logs and all browser artifacts remain disabled.

Database fixtures, not the demo, cover configured randomization, finite deadlines,
allowance exhaustion including expired attempts, concurrent starts and initial
assignments, finalized-command replay and post-lock live-role/time checks.
Fixture-only finalization is explicitly not D03 acceptance. Execution evidence
and exact D02/D03 contracts live in the D01 section of `docs/DEVELOPMENT.md`.

The 22 October 2026 complete local gate passed all 25 cases (16 I02, 5 C01,
3 C02 and 1 D01) on Chromium 156.0.8078.4, with owned-resource cleanup.
This is local review evidence, not B.C.'s acceptance or hosted CI.
