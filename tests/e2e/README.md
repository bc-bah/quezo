# Real-browser foundation and lifecycle gates

This suite uses npm-locked Playwright Test 1.64.1 and its Chromium browser.
Every successful journey uses native Quezo forms, the actual Keycloak login UI,
the built Next server/session facade, a separate Uvicorn/FastAPI process, real
JWT/JWKS validation and migrated PostgreSQL. No injected browser cookies/tokens,
password grants, request interception, mocked actors or runtime bypasses.
Master-realm administration is confined to the existing explicit setup helper.

**Accepted baseline:** B.C. accepted I02 and closed EX-I02-01 on 21 October 2026
after reviewing merged PR #7 and its passing browser/CI evidence. T01 and the
Phase 2 lifecycle milestone were accepted on 23 October at PR #15 merge
`df06ccc`; see the [acceptance record](../../docs/implementation/BACKLOG.md#t01-milestone-acceptance-23-october-2026).
C03 was accepted on 27 October after B.C.'s local app review and requested
commit/merge at local dev `2eba9eb`, head `0010_author_workspace`; see the
[C03 acceptance record](../../docs/implementation/BACKLOG.md#c03-acceptance-and-next-package-readiness-27-october-2026).
All 36 real-provider browser cases passed, including 3 new C03 cases. The
umbrella `--checks` run was not rerun to a green exit after correcting two stale
route inventories; exact separate successful checks and limitations are in the
[C03 handoff](../../docs/DEVELOPMENT.md#c03-complete-author-workspace).
Future assigned packages extend these accepted lifecycle fixtures.
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
Remote Docker contexts are refused. Allow roughly 10 minutes for the browser
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
npm run test:e2e -- --grep C03
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
Next, migrates a fresh database to `0010_author_workspace`, and calls I01's allowlisted
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

## C03 author workspace evidence

`author-workspace.spec.ts` adds native bank/question organization, category/tag/text
search and pagination, owned-bank movement and explicit archive/history views.
Its composition journey reuses a revision in two quizzes, explicitly updates only
one draft pin, previews/publishes it, inspects publication history, closes a quiz,
observes rejection of archive while an actual attempt is active, finalizes and
archives without changing frozen private questions, publications or results.
Another real author is denied discovery and direct organization/lifecycle writes,
including protected HTML/RSC routes. Tokens come only from the actual signed-in
server session, not a password grant or injected browser identity.

These extend, not replace, C01/C02 and T01 cases for both question types, bounds,
stale editor/replay, safe preview/no side effects and historical finalization.
See the [C03 evidence map](../../docs/DEVELOPMENT.md#c03-complete-author-workspace)
for inherited/new/partial/out-of-package catalogue scenarios. A filtered C03 run
alone is not full AT-03/04/05 acceptance or D04/Q02 readiness.
The package is accepted, not a blanket full-catalogue or WCAG claim.
A01/D04/R02 are ready for separate explicit dispatch in that order; B.C. owns
integration/review/merge with one shared writer. DEC-09 timing design is approved,
but D04 controls and Q02 accessibility evidence are still pending.

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
disclosure and empty localStorage/sessionStorage. Request inspection checks
provisional headers immediately and actual Chromium wire headers through the
read-only `Network.requestWillBeSentExtraInfo` event, including failed requests.
It does not await raw-request-header promises that can remain unresolved for
interrupted prefetches. Auth response/cookie checks remain awaited; no header
values or protocol events are written to artifacts.

This is the accepted working-foundations and initial lifecycle demonstration,
not A01 account management, full delivery configuration, Q02/WCAG, full P0,
hosting or pilot acceptance. D01 demonstrates assignment/start/resume; D02 adds
saving, D03 submission and R01 policy-filtered results. Keyboard
observations are automated Chromium focus checks, not a human screen-reader
audit. Later assigned packages should extend these same fixtures after their
producer gates, not introduce a second runner.

## T01 foundation-to-lifecycle demonstration

B.C. directed R01 acceptance/tracking to `done` and T01 execution on 23 October
2026. I02 was already accepted/done. R01 merge `8976371` and all transitive
producer merges were verified on live GitHub and as local ancestors; see the
[authoritative backlog](../../docs/implementation/BACKLOG.md).
T01 milestone acceptance is recorded on 23 October 2026 at PR #15 merge
`df06ccc`, following reconciliation of the local evidence below and passing
[hosted checks](https://github.com/bc-bah/quezo/actions/runs/39949405839).

From a fresh checkout containing those producers and the T01 changes, perform
the install steps above, then run the complete acceptance command:

```powershell
npm run test:e2e -- --checks
```

For a shorter, repeatable foundation-to-lifecycle demo with real owned services:

```powershell
npm run test:e2e -- --grep "native login|T01|D02|D03 AT-09/11"
```

That selector runs **six** cases: native login/logout, two complete T01 author
journeys, two controlled-expiry journeys and the D02/D03 interruption journey.
It is not the full acceptance command. Both commands build the current web
application, provision synthetic identities, migrate owned PostgreSQL, use actual
Keycloak login and remove only their owned resources. No credential export,
external service, hand-edited state or manual fixture setup is needed.
The full run includes the unchanged 300-second token-expiry wait and duplicated
producer checks; allow substantially longer than the focused demo.

`lifecycle.spec.ts` runs the **same native-form workflow for both presets**:
create both question types; compose with a point override; preview and compare
assignment/attempt/Grade/start/publication/completion counts; publish; reuse the
exact question version in a second publication; assign; start as a real learner;
navigate and save both answers; hold a real parent lock to observe pending-save
submission blocking; edit both bank questions; refresh/resume unchanged
content/order and persisted answers; submit and replay; edit again after grading;
verify both publications, attempt and the one Grade remain unchanged; read the
permitted result. It checks raw HTTP, HTML, RSC, DOM, empty browser CacheStorage
and web storage, foreign author/learner denial, and revoked learner-role denial
with the previously valid token and browser session.

`responses.spec.ts` retains actual interrupted/offline save, cross-tab conflict,
lost save acknowledgement and lost submit acknowledgement tests. Its T01 extension
restarts both application processes after completion, checks durable responses
and stable presentation, then opens the policy-filtered result and confirms one
Grade. Faults sever real byte-forwarding sockets after a real API command queues
on PostgreSQL; neither requests nor success responses are mocked.
`finalization.spec.ts` reuses D03's explicitly controlled historical backend
admission and restart fixture for **both** score-only and withheld expired results.
Those two cases are not native author-to-start journeys or timed UX acceptance:
only their login/result-display portions are browser evidence.

Fresh identities use `privateIdentity` in the changed scenarios. It creates a
new context and reuses the unchanged I02 privacy observer (wire headers, callback
referrers, auth cookies, DOM/storage and secrets). Local logout still preserves
Keycloak SSO; the tests do not redefine it. Fixture-only committed role revocation
is restored in `finally`, never by runtime provisioning.
The safe reporter prints discovered count, exact static titles and outcome counts,
including skipped/interrupted cases. It recognizes new lifecycle failure locations
without printing payloads or raw call logs. No trace, HAR, screenshot, video or
browser state is retained.

### Lifecycle acceptance matrix

These are **initial lifecycle scopes**, not completion of every catalogue row.
The table is the historical T01 checkpoint; C03 now supplies the search,
revision-management and close/archive evidence identified as remaining below.
Use the [current C03 case map](../../docs/DEVELOPMENT.md#c03-complete-author-workspace)
and [acceptance reconciliation](../../docs/implementation/BACKLOG.md#c03-acceptance-and-next-package-readiness-27-october-2026)
for current scope rather than treating those historical C03 gaps as blockers.
The 23 October 2026 unfiltered gate passed all 33 browser cases, with zero
skips/failures, and every required producer check. Exact execution results are in the
[T01 section 3 handoff](../../docs/DEVELOPMENT.md#t01-first-lifecycle-acceptance).
Backend tests use real PostgreSQL, but most authenticate via the accepted
controlled signing/JWKS peer, not Keycloak. They supplement the real-Keycloak
browser paths; no browser happy path is claimed to prove concurrent integrity.

| AT | Actual browser evidence | Separate producer evidence | Explicit remaining scope |
| --- | --- | --- | --- |
| AT-01 | [access.spec.ts](access.spec.ts), all 16 I02 cases retained: native login/logout, actual expiry, roles, callback/CSRF and dependency outages. T01 adds old-token result/submission denial after committed role revocation. | [Identity tests](../../postgres/tests/test_identity_access.py), actual-provider HTTP integration and web session checks | A01 in-app administration is AT-02, not accepted here; Q01/Q02 broader access/workflow acceptance remains. |
| AT-03 initial | [questions.spec.ts](questions.spec.ts), [lifecycle.spec.ts](lifecycle.spec.ts): both types, immutable edits, literal input, owner-only lists/direct IDs, visible failures. | [test_questions.py](../../postgres/tests/test_questions.py), question schemas/migrations: bounds, transaction rollback, concurrent edits and privileges | C03 search/category/tags, move/archive and full author workspace. |
| AT-04 initial | C02 two-quiz reuse; T01 edits both types after saves and again after grading; old revisions, both publications, delivered order/answers and Grade stay fixed. | [test_quizzes.py](../../postgres/tests/test_quizzes.py) snapshot tests; [test_attempts.py](../../postgres/tests/test_attempts.py) frozen/randomized order; [test_results.py](../../postgres/tests/test_results.py) frozen Grade/policy | C03 complete revision/archive management; R02 historical/report views. |
| AT-05 initial | [quizzes.spec.ts](quizzes.spec.ts) draft/preview/publish/revision, stale tabs and publication outage/replay; T01 checks preview causes no assignment/attempt/Grade/allowance-ledger/event writes. | `test_concurrent_publish_one_snapshot_and_ledger`, `test_draft_cas_and_edit_publish_race`, validation/rollback/closed-state fixtures in `test_quizzes.py` | C03 close/archive UI and full management transitions; no browser close/archive acceptance. |
| AT-06 initial | [attempts.spec.ts](attempts.spec.ts) named assignment, duplicate acknowledgement, foreign link denial, start/reload/resume; T01 pinned publication and stable content/order. | `test_parallel_start_duplicate_and_finalized_replay`, frozen/randomization, schedule/allowance/post-lock checks in `test_attempts.py` | D04 configurable limits, schedules and both randomization controls; Q01 broader adversarial suite. |
| AT-07 initial | [responses.spec.ts](responses.spec.ts): refresh/web+API restart, clear, cross-tab conflict, explicit reconciliation; T01 persists both answers and resumes exact snapshot. | [test_responses.py](../../postgres/tests/test_responses.py): CAS races, same-key retry, changed-payload rejection, rollback/deferred commit and stale writes | Q01 expanded integrity/failure suite; unsaved browser-memory edits are not durable promises. |
| AT-08 initial | D02/D03 actual disconnect, unsaved warning, newer edit, lost save acknowledgement, retry, pending/conflicted/failed-save submission guard; T01 checks guard in both presets. | Response acknowledgement ledger/commit-before-success and terminal replay tests | Q02 screen-reader/responsive/workflow acceptance; no full accessibility claim from status locators. |
| AT-09 initial | [finalization.spec.ts](finalization.spec.ts) controlled historical overdue backend fixture, real restart catch-up and browser expired views for both presets; no timer. | [test_finalization.py](../../postgres/tests/test_finalization.py): exact database-sampled equality, real delayed locks/late commits, bounded worker/cancellation/restart and independent processes; `test_attempts.py` schedule admission | D04 schedule/DST/configurable delivery and DEC-09 timed UX; Q01/Q02 full timing/accessibility suite. Controlled clock samples are not browser timing evidence. |
| AT-10 initial | D02/D03 drops actual submit acknowledgement after dispatch, observes committed Grade, freezes edits, retries, restarts and reads result; T01 repeated submission preserves one Grade/metadata. | `test_save_submit_race_and_duplicate_submit`, `test_multiple_process_workers_submit_save_and_restart`, scoring/write/deferred-commit rollback and [finalization migration constraints](../../postgres/tests/test_finalization_migrations.py) | Q01 expanded integrity/access failures; Q03 approved load/multiprocess performance thresholds. Browser retries are not a concurrency proof. |
| AT-11 initial | T01 MCQ correct with override plus incorrect true/false scores 5/7 from old keys despite bank edits; R01 zero; D02 cleared/unanswered; expiry all-unanswered zero or withheld. | [test_scoring.py](../../postgres/tests/test_scoring.py) pure deterministic integer scoring/bounds/zero-point/unanswered; D03 persisted-response adapter; C02 zero-total rejection | Q01/Q02 expanded combinations/workflows; no new scoring, regrading or pass/fail feature. |
| AT-12 initial | [results.spec.ts](results.spec.ts), T01 and expiry: score-only/zero/withheld, HTTP/HTML/RSC/DOM omission, no-store, empty browser caches/storage, outage/revocation/foreign denial. Submission remains metadata-only. | `test_independent_policies_every_combination_and_boundary`: all 27 combinations at before/equality/after finite end, actual DB/Grade/HTTP with controlled clock sample; additional actual-wall-clock reads and post-lock access checks | D04 configuration UI and R02 history/reporting; Q01 broader disclosure checks; no browser finite-end/timed policy configuration claim. |

At that T01 checkpoint, full search/archive (C03), administration (A01), delivery settings/timed UX (D04),
history/reporting (R02), broader integrity (Q01), accessibility (Q02), operational
recovery (O01) and load gates (Q03) remain their owners' work. AT-02/13-17, full P0,
deployment and pilot readiness are not accepted by T01. No successor is dispatched.

### Exact browser case inventory

The T01 checkpoint discovered **33 cases**, not just the original 16. C03 adds
3 cases, bringing the current unfiltered suite to **36**; its scenario inventory
and outcomes are recorded in the C03 section above.
Counts by file: access 16, questions 5, quizzes 3, attempts 1, responses 1,
finalization 2, results 3, lifecycle 2. Each title below is printed by the safe
reporter; the full-run outcome is recorded in the T01 handoff, not inferred from
discovery or the existence of this list.

| File | Exact case title |
| --- | --- |
| access | EX-I02-01 no-referrer negative control rejects native null origins |
| access | AT-01 native login and logout forms |
| access | AT-01 administrator navigation, current actor and private browser state |
| access | AT-01 author navigation, current actor and private browser state |
| access | AT-01 learner navigation, current actor and private browser state |
| access | AT-01 combined navigation, current actor and private browser state |
| access | AT-01 empty navigation, current actor and private browser state |
| access | AT-01 persisted session survives built-web restart and keyboard navigation |
| access | AT-01 old token cannot restore removed roles or disabled account |
| access | AT-01 inactive mapping denies the existing browser session and direct token |
| access | AT-01 direct API denies missing, malformed, tampered, wrong-audience and wrong-issuer credentials |
| access | AT-01 callback state, browser binding and replay fail closed |
| access | AT-01 real foreign-origin form and missing/null hostile requests are denied |
| access | AT-01 backend and both database transports fail explicitly without cached actors |
| access | AT-01 real identity outage respects warm, expired and cold JWKS caches |
| access | AT-01 actual access-token expiry caps the durable session without refresh |
| questions | C01 AT-03/04 mcq author creates edits and selects immutable revisions |
| questions | C01 AT-03/04 true_false author creates edits and selects immutable revisions |
| questions | C01 signed-in foreign author and non-author roles cannot discover keys |
| questions | C01 stale browser edit and live role revocation fail visibly |
| questions | C01 dependency outage retains unsaved form and never reports success |
| quizzes | C02 AT-04/05 author composes previews publishes and explicitly revises immutable quizzes |
| quizzes | C02 stale composition and publication outage fail visibly without losing edits |
| quizzes | C02 real login ownership and publish retry are enforced before disclosure |
| attempts | D01 AT-06 author assigns and learner lists starts reloads without private payloads |
| responses | D02 AT-07/08 durable answers and D03 pending-save submission and lost completion response |
| finalization | D03 AT-09/11 controlled overdue backend fixture catches up on restart and renders expired without timed UX |
| finalization | T01 AT-09/11/12 controlled overdue backend fixture renders fully withheld expired result |
| results | R01 AT-12 score-only result omits unreleased data in real HTTP and HTML |
| results | R01 AT-12 released zero result omits unreleased data in real HTTP and HTML |
| results | R01 AT-12 fully withheld result omits unreleased data in real HTTP and HTML |
| lifecycle | T01 AT-03 through AT-12 score-only author-to-result lifecycle preserves frozen history and live access |
| lifecycle | T01 AT-03 through AT-12 fully withheld author-to-result lifecycle preserves frozen history and live access |

## D02 AT-07/08 response cases

`responses.spec.ts` extends the actual author-publish-assign/learner-start path
with both question types and explicit per-question saves. Run focused iteration
with `npm run test:e2e -- --grep D02`; the review gate remains the full
`npm run test:e2e -- --checks`.

The journey checks unanswered revision zero, acknowledged refresh and web/API
process restart, explicit clear, question navigation, cross-tab conflicts with
retained local input and explicit resolution, offline announcements and discard
warnings, reconnect reconciliation, newer input during an outstanding save,
and lost acknowledgement without duplicate revision. The lost-ack case holds a
real PostgreSQL parent lock, waits for the real API save to queue, severs the
web-to-API byte-forwarding transport, releases the lock and verifies commit
before reconnect/replay. This drops an actual acknowledgement rather than
assuming Chromium's offline flag cancels an already-open HTTP request.
Actual API outage produces a visible unsaved error, followed by reconciliation
and explicit retry. Learner JSON/HTML/RSC are inspected in memory for scoring/key
nondisclosure. No request interception, mocked save endpoint, screenshots or
payload logs are added.

## D03 AT-09/10/11 initial cases

Run `npm run test:e2e -- --grep D03` for the two focused journeys; review still
requires `npm run test:e2e -- --checks`. The D02 response journey now also
asserts submission is disabled during pending saves, newer unsaved input,
offline state, uncertain saves and cross-tab conflicts. It clears an answer,
checks/cancels the unanswered confirmation, then voluntarily submits through
the real browser/server-only facade. Holding the real parent lock and severing
the backend transport drops the completion response after dispatch; the case
observes the committed Grade, checks unknown-outcome UI and frozen editing,
retries the same attempt, reloads and proves exactly one Grade.

`finalization.spec.ts` uses an actual authenticated author API for a timed
publication solely as a **controlled backend expiry fixture**. With the API
stopped, it inserts an internally consistent already-overdue attempt using the
frozen publication and normal response-initialization constraints. It never
rewrites a protected deadline. API restart catches it before readiness; the
real learner browser shows the expired projection with disabled answers, no
timer, no submission control and no disclosed score, key or feedback.

These cases do not claim timed accessibility acceptance, a countdown,
history/reporting or pilot readiness. R01 supplies result release; T01 repeats
the expired projection under both approved presets. The live
voluntary-submit demonstration remains untimed while DEC-09 is held.

## R01 AT-12 policy-filtered results

Run `npm run test:e2e -- --grep "R01|D03 AT-09/11"` for the three result journeys
and the controlled-expiry result extension. Review requires the full
`npm run test:e2e -- --checks`.

`results.spec.ts` creates both question types, selects an approved release preset,
publishes/assigns, saves and submits using actual native author/learner forms.
It distinguishes score-only (1/3, displayed as 33.3%), a released zero (0/3,
0.0%) and fully withheld (no fabricated zero). In-memory API, HTML/RSC and DOM
inspection verifies key/outcome/awarded-item-point/feedback omissions. Submission
acknowledgements stay metadata-only. Pre-finalization/foreign result routes deny
content, private/no-store headers prevent response caching, reload rechecks
access and an actual API outage cannot display a cached result. Existing privacy
fixtures still check empty web storage and secret/content-free logs; no traces,
screenshots, HAR or result payload artifacts are retained.

The D03 restart fixture now follows the completion link and verifies an expired
result with its permitted zero aggregate, without releasing key or feedback.
This remains a controlled backend expiry fixture, not approved timed learner UX.
All 27 policy combinations and finite-end before/equality/after cases are real
PostgreSQL/HTTP backend fixtures in `test_results.py`; the browser only selects
the two approved untimed/unscheduled presets. R02 history and author reporting
remain out of scope. Execution evidence is recorded in the
[R01 handoff](../../docs/DEVELOPMENT.md#r01-policy-filtered-result).

The 23 October 2026 complete local gate passed all **30 browser cases** on
Chromium 156.0.8078.4, alongside 648 Python cases and all common checks.
Owned resources were removed normally. This is review evidence, not R01
acceptance/integration or hosted CI. B.C. subsequently accepted R01 merge
`8976371` and directed T01; see the current T01 handoff above.

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
