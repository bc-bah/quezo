# Development setup

## What is and is not available

The scaffold contains a Next.js/TypeScript npm workspace and an independent
Python/FastAPI backend with a typed liveness endpoint, generated OpenAPI, pytest
checks and strict mypy configuration. F01 adds real PostgreSQL connectivity,
ordered migrations, restricted database roles and isolated database tests.
Separate frontend/backend CI jobs are included. C01 adds owned question banks,
immutable MCQ/true-false revisions and author forms. C02 adds draft composition,
nonpersistent learner-shaped preview and immutable quiz publication. D01 adds
named assignment and atomic start/resume with frozen learner/private snapshots.
F02 adds strict HTTP DTOs, sanitized errors, server-generated correlation IDs,
bounded request bodies and a generated TypeScript client for implemented routes.

F03 adds server-only OIDC and durable web sessions with navigation. I01 adds
independent JWT validation, live application authorization and `/api/v1/me`.
Explicit local synthetic provisioning is required; sign-in never grants access.
A01 adds administrator-only account listing, disabled-user provisioning,
application-role changes and activation/deactivation. The dedicated local
Keycloak service credential is server-only and separate from the web OIDC
credential; A01 never stores or provisions passwords.

D02 adds durable response saving, explicit clear, resume and conflict/retry UI.
D03 adds metadata-only submission, immutable grading through S01, request-triggered
expiry and a lifespan-managed bounded expiry worker. R01 adds independent
policy-filtered learner results and a minimal result page. History/reporting,
real readiness checks and production deployment remain absent. An opt-in
[full local Docker stack](#full-app-with-docker-desktop) runs the accepted app.
A configured local Keycloak can be
used by the web OIDC adapter; combined Keycloak/browser/backend acceptance is
I02, not established by F03 protocol tests. Database configuration is required
for both server lifecycles.

## Prerequisites and startup

### Full app with Docker Desktop

This is a local development/demo stack, not a production deployment or a Phase 3
readiness claim. Only Docker Desktop with Linux containers and Docker Compose
2.24.4+ is required to run the app; Node, Python and uv run inside the images.
The initialization helper uses PowerShell. Run these commands from the repository
root:

```powershell
.\infra\docker\Initialize-Local.ps1
docker compose --env-file .env.docker -f compose.local.yaml up -d --build --wait
docker compose --env-file .env.docker -f compose.local.yaml run --rm provision --setup-realm
docker compose --env-file .env.docker -f compose.local.yaml run --rm provision --account combined
```

Run the two provisioning commands **once**, explicitly, on a fresh stack.
They deliberately refuse an existing realm/application account; do not rerun
them during ordinary restarts. The combined synthetic account has author and
learner roles, not administrator privileges. See the
[identity runbook](../infra/keycloak/README.md) for additional allowlisted accounts
and partial-failure recovery. Choose a different synthetic password before
provisioning each additional account.

Open **http://localhost:3000** (use `localhost`, not `127.0.0.1`, for browser
sign-in), select **Sign in**, and use username **`quezo-test-combined`**.
Its password is the `QUEZO_SYNTHETIC_PASSWORD` value in the ignored local
`.env.docker` file. Keep this file private; it also contains the local Keycloak
administrator and database credentials. Do not paste it or resolved Compose
configuration into logs or commits. `.dockerignore` excludes all local env files
from image build contexts.

The API is at http://localhost:4000/docs; process-only liveness is at
http://localhost:4000/health/live. Keycloak is at http://localhost:8080.
All four published ports (3000, 4000, 5432 and 8080) bind only to host loopback
and must be free. The stack deliberately fixes these ports to match the exact
local realm redirect URIs. Stop any existing host-run app or dependency using
them first.

The standalone `compose.local.yaml` leaves the existing `compose.yaml` workflow
unchanged and uses the separate `quezo-local` project and persistent volumes.
Its containers share PostgreSQL's network namespace as a local-only pod. This
preserves the existing loopback-only web/database/provisioning safeguards and
gives the browser, web server and API the **same** `localhost` OIDC issuer without
loosening validation or requiring host DNS edits. Only PostgreSQL publishes
ports, including the web/API/Keycloak ports. Do not scale these services or
recreate PostgreSQL alone; bring the entire stack down and back up when changing
the network-owning container.

Migrations run as a one-shot restricted migrator before API startup. The API and
web receive only their own runtime database credentials; only the explicit
provisioning tool receives identity-administration credentials. Images run the
application processes as non-root. Health checks wait for PostgreSQL, Keycloak,
API liveness and an HTTP web response; these are startup checks, **not** a claim
of the deferred product readiness gate or a substitute for testing sign-in.

For later starts, logs and shutdown:

```powershell
docker compose --env-file .env.docker -f compose.local.yaml up -d --build --wait
docker compose --env-file .env.docker -f compose.local.yaml ps -a
docker compose --env-file .env.docker -f compose.local.yaml logs --tail 100 api web keycloak migrate
docker compose --env-file .env.docker -f compose.local.yaml down
```

Shutdown preserves the database, realm and assessments. Keep `.env.docker` with
those volumes: regenerating credentials does not rotate existing database or
Keycloak credentials. The helper refuses to overwrite an existing file.
Do not add `--volumes` to shutdown unless you intentionally want to delete this
local stack's assessments, identities and sessions. Test services remain in the
original Compose file and do not share these project volumes.

If your corporate HTTPS proxy causes npm's container build to fail with
`UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, export the trusted public Windows root
certificates and apply the optional build override:

```powershell
.\infra\docker\Export-WindowsCa.ps1
docker compose --env-file .env.docker -f compose.local.yaml -f infra\docker\compose.ca.yaml up -d --build --wait
```

Use the same override on subsequent rebuilds. The ignored `.env.docker.ca.pem`
bundle contains public certificates only, no private keys. BuildKit mounts it
as a build secret for npm; it is not copied into images or exposed to app
processes. TLS verification remains enabled. Do not work around this failure
with `strict-ssl=false` or `NODE_TLS_REJECT_UNAUTHORIZED=0`.

### Host-run application processes

In the learner workspace, **My assignments** includes **View completed attempt**
and **View result** links for the most recent finalized attempt on each assignment,
including submitted or expired attempts with no starts remaining. These links
remain available while another attempt is in progress; **Resume attempt** still
opens the active attempt. Results continue to honor the published release policy:
navigation does not release withheld scores, answer keys or explanations. This
is a return path for the latest completed attempt, not full history by itself.
R02 adds **Attempt history** and the author quiz's **Participation and results**
workspace; see [R02 contracts and evidence](#r02-history-and-author-reporting).

For the C01 author workflow, migration and consumer contract, see
[C01 versioned objective questions](#c01-versioned-objective-questions).
For quiz composition and publication, see [C02](#c02-immutable-quiz-publication).

Use Node.js 22+ and npm 10+ for the frontend, plus Python 3.12+ and
[uv](https://docs.astral.sh/uv/getting-started/installation/) 0.12.17 for the backend.
`.nvmrc` selects Node 22 and `postgres/.python-version` selects Python 3.12.
CI covers Node 22/24 and Python 3.12/3.14 in independent jobs. Docker with Compose
provides the local development and isolated test databases. Commands work on Windows and
Linux; no Bash shell or manual virtual-environment activation is required.

From the repository root:

```powershell
npm ci
uv sync --directory postgres --locked
npm run dev:web
```

Set up and migrate the local database as described below. In a second terminal,
export `QUEZO_DATABASE_URL` using the restricted runtime identity, plus
`QUEZO_OIDC_ISSUER` and `QUEZO_API_AUDIENCE` from the I01 configuration below, then:

```powershell
npm run dev:api
```

`npm ci` installs only the frontend toolchain; it does not install Python
dependencies. uv creates `postgres/.venv` from `postgres/uv.lock`. Install Python
3.12 first if needed; `uv python install 3.12` is an explicit option. uv can also
discover a suitable existing interpreter even when the shell's `python` command
points to an older version.

The web shell listens on `127.0.0.1:3000`; the backend on `127.0.0.1:4000`.
Visit `http://localhost:3000` and `http://localhost:4000/health/live`.
The backend returns `{"status":"ok","scope":"process-only"}`. It deliberately has
no `/health/ready` or raw grade routes. FastAPI exposes local interactive docs at
`http://localhost:4000/docs` and the generated contract at
`http://localhost:4000/openapi.json`; liveness, `GET /api/v1/me`, C01 question
authoring, C02 quiz publication, D01 assignment/start, D02 response saving,
D03 submission, R01 filtered results and R02 history/owner reporting are implemented.
Shared actor, error and pagination schemas are also exported. This is not the
deferred supported public API. Stop each foreground process with Ctrl+C.

To choose another backend port:

```powershell
npm run dev:api -- --port 4100
```

The backend now uses Uvicorn CLI options, not the former Express `PORT` variable.
For the web shell, use
`npm run dev --workspace @quezo/web -- --port 3100`.

Backend developers do not need npm to run the Python application. The equivalent
direct command from the repository root is:

```powershell
uv run --directory postgres --locked uvicorn --app-dir src quezo_api.app:create_app --factory --loop quezo_api.database:database_loop_factory --host 127.0.0.1 --port 4000 --no-server-header --no-access-log --reload
```

## Checks and starting without reload

```powershell
npm run typecheck
npm test
npm run build
```

Start the isolated test service and export its three test variables (below)
before `npm test`, `npm run test:db` or `pytest`. Missing database configuration
or an unavailable database is a failure, never a skip or an in-memory substitute.

`typecheck` runs Next.js route type generation/TypeScript checks and strict mypy
over Python application and test sources. `test` runs focused web tests and pytest
through uv. `test:db` includes the real web-session tests, using the same isolated
Python fixture to supply database URLs to Node. FastAPI's
in-process test client uses a real migrated database and checks exact liveness,
absent product/readiness routes, OpenAPI and lifespan cleanup. Database tests
also verify migrations, permissions, transaction commit/rollback, cancellation,
pool bounds and isolation safeguards. These do not establish assessment acceptance.
`build` builds only Next.js; Python runs directly and has no JavaScript compilation.

The backend checks can also be run without Node.js:

```powershell
uv run --directory postgres --locked mypy
uv run --directory postgres --locked pytest
```

Next.js generates `next-env.d.ts` and `.next/` types; do not hand-edit generated
declarations after initial setup. Python dependencies are pinned in
`postgres/pyproject.toml` and `postgres/uv.lock`; frontend dependencies remain in
npm manifests and `package-lock.json`. Update each lock through its package manager,
not by hand. `--locked` prevents unnoticed Python lockfile changes during normal use.

After building, the foreground commands below start the built shells in separate
terminals:

```powershell
npm run start --workspace @quezo/web
npm run start:api
```

The backend start command omits reload and suppresses Uvicorn's server banner.
Both launch scripts disable raw Uvicorn access logs, which otherwise include
untrusted paths/query strings. Retain `--no-access-log` in custom launchers;
do not enable request/body/token logging in HTTP clients, proxies or dependencies.
These are local-only shells, not a production deployment. Build output, virtual
environments, Python bytecode and test/type-check caches are ignored by Git.
No linting tool is selected. I02 adds npm-locked Playwright Test; see
[the real-browser runbook](../tests/e2e/README.md) for browser installation,
owned isolated dependencies and `npm run test:e2e`.

## T01 first lifecycle acceptance

**Work item:** T01, First lifecycle acceptance.
**Owner/integrator/reviewer:** B.C.; assigned active 21 October 2026, execution
directed 23 October after R01 acceptance reconciliation.
**State:** accepted and `done`, 23 October 2026, following B.C.'s request to
reconcile milestone acceptance before Phase 3. [PR #15](https://github.com/bc-bah/quezo/pull/15)
merged at `df06ccc19af947cda05757c79938394763d6edb6` (implementation `300bbc4`).
[Hosted browser and Node/Python matrix checks](https://github.com/bc-bah/quezo/actions/runs/39949405839)
passed. The local execution record below is retained unchanged; this tracking
update does not claim a new application run or code review. See the
[acceptance boundary](implementation/BACKLOG.md#t01-milestone-acceptance-23-october-2026).

**Changes:** `tests/e2e/lifecycle.spec.ts` adds complete real-native-form
author-to-result journeys for score-only and fully withheld presets.
`finalization.spec.ts` repeats the accepted controlled historical-expiry fixture
with withheld results. `responses.spec.ts` extends the accepted interruption
journey through post-completion process restart and the R01 result page.
`fixtures.ts` shares the existing privacy observer with fresh identity contexts;
`playwright.config.ts` includes the new file; `safe-reporter.ts` adds exact
discovery/outcome counts and safe failure locations. The browser runbook contains
the repeatable demo, all 33 exact case titles and the acceptance matrix.
Backlog/phase/handoff records reconcile R01 to done and preserve I02's existing
done acceptance and closed EX-I02-01. No producer implementation is replaced,
no mock-success bridge or broad refactor is introduced.

**Requirement coverage:** IAM-01/02; initial AUTH-01 through AUTH-04,
ATT-01 through ATT-04, SCORE-01 and RESULT-01; applicable section 6-8
immutability, command replay, strict projection, error and disclosure contracts.
PRD mapping follows SRS section 10: FR-001/002/003/061, initial
FR-010/011/012/013/014/018, FR-015/020/021/024/025/026,
FR-030/031/032/033/035/036/037/038/040/041/042/043 and the
learner-result portion of FR-050/051/052/056. FR-022/023/034 configurable
delivery/timing has separate backend evidence only, not full UI acceptance.

**Acceptance:** [the lifecycle matrix](../tests/e2e/README.md#lifecycle-acceptance-matrix)
maps **AT-01 and initial AT-03 through AT-12** to exact browser files, separate
producer concurrency/clock/scoring fixtures and remaining owners.
All assigned initial scopes passed in the unfiltered gate below; full catalogue
completion is not claimed.
Native browser paths use Keycloak -> built Next server-only facade -> separate
FastAPI -> actual PostgreSQL. Supplemental authenticated API probes obtain tokens
from real sessions only in fixture memory; browser requests never receive them.
Backend signing peers and controlled clock/expiry fixtures are explicitly separate.

| Assigned T01 criterion | Executable evidence |
| --- | --- |
| Both objective types, immutable edits, reuse, preview, publication, assignment | Both `lifecycle.spec.ts` presets create everything through real author forms; preview compares six persistence counts; both published snapshots and old question versions survive later edits. |
| Start, navigation, pending save, save/refresh/resume, exactly one final grade and result | Both lifecycle cases save both answers, observe pending-save submit blocking under a real parent lock, resume unchanged snapshots, submit/replay, and verify one 5/7 Grade from frozen keys/points. |
| Withheld and expired outcomes without disclosure | Full withheld lifecycle plus score-only/withheld `finalization.spec.ts` backend-expiry fixtures; HTTP/HTML/RSC/DOM omissions, no-store and empty browser caches/storage; R01 zero/outage regressions retained. |
| Interrupted saves/submission, durable responses and stable order | Existing D02/D03 actual transport-loss and retry journey, extended through web/API restart and policy-filtered result; both new normal journeys compare complete frozen presentations. |
| Foreign actor denial, live identity and unchanged I02 regressions | Foreign combined-role author/learner cannot read or replay; committed learner-role removal denies the old token's result/submission and clears rendered result. All 16 I02 cases remain in unfiltered discovery. |
| Distinct integrity evidence | Existing question/publication/attempt/response/finalization/result database suites and pure S01 tests; real races/rollback/processes are not inferred from browser happy paths. |
| Reproducible demo and exact scoped acceptance | Browser runbook commands, 33-title inventory and per-AT matrix; later-package gaps below remain explicit. |

**Checks / environment:** local Windows, Node 24.20.0, npm 11.19.0,
uv 0.12.17, Python 3.12.10, Docker Engine 29.9.2 / Compose 5.6.1,
PostgreSQL 17.11, Keycloak 26.4.7, Next.js 16.4.2,
Playwright 1.64.1 / Chromium 156.0.8078.4.
The local Docker engine was initially stopped and was started and readiness
verified. `npm run typecheck:e2e` initially failed because `tsc` was missing;
`npm ci --no-audit --no-fund` restored the locked dependencies and that check
passed. The existing uv launcher created its missing locked Python environment.
No dependency manifests/locks were changed and no missing-service run is a pass.

Focused iteration:
`npm run test:e2e -- --grep "T01|D02|D03 AT-09/11"` passed **5 cases** in owned
project `quezo-i02-a32e85749331`: D03 score-only expiry 13.731s, T01 withheld
expiry 8.705s, T01 score-only lifecycle 20.971s, T01 withheld lifecycle 21.048s,
D02/D03 interruption/result 34.544s. Its owned resources were removed.
This preceded the privacy-observer reuse and reporter count update; the complete
gate below validates those final changes as well.

The required unfiltered `npm run test:e2e -- --checks` **passed, exit 0**, with owned
project `quezo-i02-f8dfc7baf6e8`, loopback PostgreSQL/Keycloak/web/API ports
56853/56854/56855/56856 on 23 October 2026. Exact executed stages:

| Command / scope | Outcome |
| --- | --- |
| `npm run typecheck` | Web/browser TypeScript and strict mypy (85 source files) passed |
| `npm test` | 12 web checks and **648 Python cases passed**; Python 962.41s |
| `npm run build` | Passed built Next application |
| `npm run api:check` | OpenAPI and generated TypeScript current |
| `npm run test:contracts` | 88 Python (3.94s) and 2 tooling/client cases passed |
| `npm run test:db` | **283 cases passed**, 924.82s, including real clean/prior-head migrations |
| `npm run test:identity` | 108 cases passed, 95.48s |
| `npm run test:identity:integration` | 1 actual-Keycloak HTTP case passed, 9.38s |
| `npm run test:web:production` | 1 built-web/database/OIDC boundary case passed |
| Unfiltered real browser | **33 discovered, 33 passed; 0 failed, timed out, skipped or interrupted** |

These counts overlap across commands and are not additive unique-test totals.
All [33 exact browser titles](../tests/e2e/README.md#exact-browser-case-inventory)
passed, including all 16 I02 regressions and the real 300-second token expiry.
Full-run T01 score-only/withheld journeys took 21.041s/17.639s; controlled
score-only/withheld expiry 7.642s/7.280s; D02/D03 interruption/result 33.841s.
No producer code fixes were necessary; their focused suites were rerun by the
unfiltered gate rather than replaced with happy-path assertions.
The launcher closed application processes/pools and removed its guarded databases,
two containers and network normally. No development volumes were touched.
Only static case names, safe counts/durations, commands and environment are
retained here; no credentials, keys, raw browser state or assessment payloads.

The exact documented demo command
`npm run test:e2e -- --grep "native login|T01|D02|D03 AT-09/11"`
was then rerun independently with owned project `quezo-i02-9255c96f1c25`
(PostgreSQL/Keycloak/web/API ports 60249/60250/60251/60252):
**6 discovered, 6 passed, zero failures/skips/timeouts/interruptions, exit 0**.
Native login/logout took 4.707s; controlled score-only/withheld expiry
9.002s/8.314s; score-only/withheld lifecycle 21.387s/18.024s; interruption/result
35.446s. All resources were removed normally. This verifies reproducibility
from fresh owned dependencies, not a replacement for the full gate.

**Contracts:** no changed HTTP operations, schemas, generated client or runtime
interfaces; T01 uses the accepted `QuestionVersion`, `PublishedQuiz`, `Attempt`,
save acknowledgement, metadata-only `Completion` and filtered `LearnerResult`.
No API regeneration is needed for these test/documentation changes; the full
gate still verifies deterministic OpenAPI/client output with `npm run api:check`.
Fixture-only `privateIdentity` returns a new page and privacy-checking context
cleanup, sharing I02 observation rather than weakening it for identity switches.

**Data:** no migration, applied-revision edit, new schema, privilege or Grade
writer. Head remains `0009_finalization`. The complete gate includes existing
clean `base -> head`, all producer prior-head upgrades and repeat-head checks,
including `test_actual_response_head_upgrade_preserves_accepted_saves` for
`0008_responses -> 0009_finalization`. No new migration is authorized or needed.
Expiry uses the existing constrained historical fixture with API stopped,
then normal startup catch-up, never a mutated frozen deadline or user-facing timer.
Recovery must still preserve snapshots, responses/command ledgers, Grade/items
and completion events together; no backup/restore/RPO/RTO acceptance is claimed.

**Integration:** T01 implementation `300bbc4` is integrated by PR #15 merge
`df06ccc` on verified producer baseline
`8976371bdf00bb337a0db0df1818cf739df7b546`.
`gh api repos/bc-bah/quezo/branches/main`, merged PR records and
`git merge-base --is-ancestor <commit> HEAD` verified the following chain.
B.C.'s user-directed post-R01 serialized window covers common test fixtures,
discovery/reporting and documentation only; no shared scripts, CI, manifests,
application wiring or runtime implementation changes were needed.

| Producer / accepted evidence | Exact merged commit | Included implementation/follow-up commits |
| --- | --- | --- |
| [I02](#i02-integrated-browser-gate), [PR #7](https://github.com/bc-bah/quezo/pull/7) | `553a2c8b77a770667f4cef6825f57c3b55f477ed` | Accepted foundation; EX-I02-01 closed |
| Phase 2 assignment/defaults approval | `49eb37b133e737f61f30a97329940bd6281b2c5a` | Not a replacement for any later producer |
| [C01](#c01-versioned-objective-questions), [PR #8](https://github.com/bc-bah/quezo/pull/8) | `e66f459c5a6b225bd3d1b4bbce6b5b87de67974c` | `eb9d62d6222ef13c777786bd6969cbbfb11028cd`, `1f2cd53848804c6ea47cf8595ffb5907d4f98bd4` |
| [C02](#c02-immutable-quiz-publication), [PR #9](https://github.com/bc-bah/quezo/pull/9) | `03797bcbb545ec188da941ff6bb02e380f5b9f1b` | `67ce98a6d86fc1262ed431876f8e63a24c0d05eb`; diagnostic follow-ups `f07640857c922399c4fc4065fa766480415551bc`, `c3c7e40009804a6a47c246cc4a913bfb233d0940` |
| [D01](#d01-assignment-and-attempt-start), [PR #10](https://github.com/bc-bah/quezo/pull/10) | `b5751a94ce2ab36be8add8070bbbd99573175d0a` | `cbb74f553b7e2ce3df5cc6082c87d94ac19712ee` |
| [D02](#d02-durable-response-save-and-resume), [PR #11](https://github.com/bc-bah/quezo/pull/11) | `c7d6f7e0d9785e220530536078241725b3588547` | `fbe93dae1b702b909d8db7dc1d5ea9139e37cc49`, `a82bc36b0a8d4c762ec7a11229138c714e63a0de` |
| [S01](#s01-pure-objective-scoring), [PR #12](https://github.com/bc-bah/quezo/pull/12) | `c9448f78cd6aee397763d37e8d33f8004a441862` | `00195df0d0cd3f0e7fcc79eb241d2f0e944ef475` |
| [D03](#d03-finalization-and-expiration), [PR #13](https://github.com/bc-bah/quezo/pull/13) | `0cfbff7bb65c9bbad2be049df729459c516516b0` | `9ff05f87aae1cf8789e9b565508f75a5ef6fd275` |
| [R01](#r01-policy-filtered-result), [PR #14](https://github.com/bc-bah/quezo/pull/14) | `8976371bdf00bb337a0db0df1818cf739df7b546` | `bb194681762e5e5e3563645f67303f9ca51f38cd` |

**Known gaps:** no known failing or unverified assigned T01 criterion remains
in the delivery record; milestone acceptance is now recorded. Scope exclusions are
not failed criteria disguised as passes: C03 owns complete search/category/tag,
move/archive/close and author management; A01 owns in-app account administration;
D04 owns configurable delivery, schedule/DST/randomization and DEC-09-dependent
timed UX; R02 owns history/author reporting; Q01 owns expanded integrity/access
failures; Q02 owns accessibility/workflow acceptance. O01/Q03 own recovery/
operational/load evidence under their decision gates. This local Chromium run
is not hosted CI, another browser/OS matrix, a human screen-reader audit, full
AT-02/13-17, full P0, deployment or pilot readiness.

**Successor handoff:** T01 is accepted; future explicitly assigned
packages can reuse the integrated producer contracts, both preset journeys,
privacy-safe fresh-context helper and existing backend integrity fixtures.
Preserve fixed snapshots, live actor checks, no-store policy projections,
pending-save guards and replay-safe commands. No successor is dispatched here.
Repeatable demo:
`npm run test:e2e -- --grep "native login|T01|D02|D03 AT-09/11"`.
Full acceptance remains `npm run test:e2e -- --checks`, unfiltered.

## R01 policy-filtered result

**Acceptance/integration, 23 October 2026:** B.C. directed acceptance/tracking
to `done` and T01 execution. Live main and T01 ancestry contain
[PR #14](https://github.com/bc-bah/quezo/pull/14), merge
`8976371bdf00bb337a0db0df1818cf739df7b546`, implementation
`bb194681762e5e5e3563645f67303f9ca51f38cd`, and all producers listed below.
I02 was already accepted/done; no new acceptance exception is introduced.
The following is the historical R01 review handoff, not a current pending gate.

**Work item / owner:** R01, B.C.; assigned 21 October 2026, execution directed
23 October after D03 acceptance. **State: ready for review**; the full local
common gate passed. R01 acceptance and integration remain B.C.'s decision.

**Integration:** remote main and this checkout contain D03 merge
`0cfbff7bb65c9bbad2be049df729459c516516b0` (implementation `9ff05f8`,
[PR #13](https://github.com/bc-bah/quezo/pull/13)). B.C. confirmed review and
integration and directed the acceptance/tracking update. Ancestry also includes
D02 `c7d6f7e` (`fbe93da`, `a82bc36`), S01 `c9448f7` (`00195df`), D01 `b5751a9`,
C02 `03797bc`, C01 `e66f459`, I02 `553a2c8` and Phase 2 approval `49eb37b`.
R01 uses the serialized post-D03 shared-file window only for app routing,
generated contracts, discovery scripts, the completion link and documentation.
No commit, PR or successor dispatch is made.

**Changes / requirements:** RESULT-01, IAM-02, ATT-04's confirmation boundary,
SCORE-01 display precision, sections 6-8 and QUAL-02/04; FR-026/043 and the
learner-result portion of FR-050/051/052/056. `modules/results/service.py`
uses D03's ownership-scoped parent lock, post-wait live actor checks and
`clock_timestamp()`. A still-editable attempt returns 409 `INVALID_STATE`;
an overdue attempt first uses the existing atomic finalizer. Foreign/missing
attempts have the same 404 envelope; lacking the learner role is 403.
Administrator or author roles alone grant no result access.

**Contracts:** `GET /api/v1/attempts/{attempt_id}/result` returns the generated
`LearnerResult`, never the internal Grade/scorer object. Completion is D03's
unchanged metadata; `title`, `versionId`, `attemptNumber` and `serverTime`
identify the frozen attempt and time of release evaluation.

| Field | Withheld shape | Released shape |
| --- | --- | --- |
| `score` | Only `status: "withheld"` | `status: "released"`, integer `earnedPoints` / `possiblePoints` |
| `answerKey` | Only `status: "withheld"` | `status: "released"`, ordered items with frozen attempt-question ID, position, prompt, correct option, outcome and item earned/possible points |
| `explanations` | Only `status: "withheld"` | `status: "released"`, ordered items with frozen attempt-question ID, position, prompt and feedback |

These are discriminated unions, not nullable protected fields. Withheld
variants reject extra fields; no score zero, null placeholder, empty item list,
key, outcome, awarded points or feedback is serialized as a substitute.
Each field independently evaluates the frozen `QuizPolicy` on every read:
after finalization, at/after finite availability end, or never. A quiz's
current closed state is irrelevant to release. Missing required end times fail
validation rather than becoming automatic release. Explanation-only release
does not add key/outcome fields, although authored explanations can themselves
reveal answers; likewise key-released item totals can imply an aggregate.

**Web:** `/learner/attempts/{attemptId}/result` uses the existing server-only
facade and generated schema. The completion confirmation links to it but still
contains no score or key. Results are dynamic/private/no-store; the facade
does not cache backend responses. Only permitted projections reach HTML/RSC;
there is no full Grade in client state, browser storage or learner fixtures.
The page distinguishes submitted/expired and withheld/released-zero, displays
exact earned/possible integers and a display-only one-decimal percentage,
renders plain text and surfaces errors instead of cached/fabricated success.
Reload performs fresh authorization/time checks. No countdown or timed controls.

**AT-12 executable coverage:** `postgres/tests/test_results.py` exercises all
27 independent policy combinations immediately before, exactly at and immediately
after the finite end (microsecond offsets around a database-read frozen bound).
It uses actual PostgreSQL/Grades/HTTP and controls only that boundary clock sample.
Separate real wall-clock/lock-wait cases prove reread release and request-triggered
expiry. Other cases cover ownership/role denial, pre-finalization, post-lock
revocation, exact payload omissions, metadata-only submit/resume/start replay,
closed quiz, changed question/draft/publication, frozen grades and safe logs.
`tests/e2e/results.spec.ts` uses real native author/learner paths for score-only,
released zero and fully withheld presets, checking JSON, HTML/RSC, DOM, caches,
outages and foreign access. The existing D03 controlled expiry browser fixture
also opens its policy-filtered result; finite-end combinations remain backend
fixtures, not timed learner UX.

**Focused checks:** all **37 R01 backend cases passed in 136.41 seconds**.
An in-memory launcher wrapper, run with
`uv run --directory postgres --locked python -`, reused `run_browser.main`
and its disposable Compose/database lifecycle. Before its ordinary build it ran
`python -m pytest --tb=short -x postgres/tests/test_results.py` from the repository
root, with the existing application/test import paths. It then ran the ordinary
browser launcher with `--grep "R01|D03 AT-09/11"`: **4 passed** (controlled
expiry 10.102s, score-only 16.603s, released zero 16.907s, withheld 16.916s).
Owned project `quezo-i02-3e7ddd4d4620` and its network were removed normally.
`npm run api:generate`, `npm run typecheck` and `npm run test:contracts`
(88 Python / 2 tooling cases) also passed.

Initial setup restored missing npm dependencies using
`npm ci --no-audit --no-fund` and started the stopped local Docker Desktop.
Iteration corrected two typed projection-construction calls to use the existing
`model_validate` convention, and a scratch launcher's working-directory import.
The first `npm run test:e2e -- --checks` passed 647 Python cases but found one
old D01 test expecting 404 for POST to the formerly absent result path.
That assertion now expects 405 for the implemented GET-only route; submission
still expects 404 for a missing attempt. Its owned dependencies were cleaned up.
The subsequent complete common gate passed, including that corrected assertion.

Environment: Windows, Node 24.20.0, npm 11.19.0, uv 0.12.17, Python 3.12.10,
PostgreSQL 17.11, Keycloak 26.4.7, npm-locked Playwright 1.64.1,
Chromium 156.0.8078.4. These are local
automated observations, not hosted CI, a Node/Python matrix or manual accessibility
review. Secret-safe browser output is retained only as aggregate evidence here.

**Final common gate, 23 October 2026:** `npm run test:e2e -- --checks` passed
with owned project `quezo-i02-4244d02219da`. All commands below were actually
executed by that launcher; counts overlap and must not be summed as unique tests.

| Command / scope | Result |
| --- | --- |
| `npm run typecheck` | Passed web/browser TypeScript and strict mypy (85 sources) |
| `npm test` | 12 web checks and **648 Python cases passed** (934.20s Python) |
| `npm run build` | Passed built Next; result route is dynamic |
| `npm run api:check` | OpenAPI and generated TypeScript current |
| `npm run test:contracts` | 88 Python and 2 tooling/client cases passed |
| `npm run test:db` | **283 passed** (926.07s), including clean/prior-head migrations |
| `npm run test:identity` | 108 passed |
| `npm run test:identity:integration` | Actual Keycloak HTTP case passed |
| `npm run test:web:production` | Built web/database/OIDC boundary case passed |
| Full browser suite | **30 passed**; R01 score-only 16.448s, released zero 15.983s, withheld 15.639s; D03 controlled expired result 7.208s |

**Acceptance:** AT-12's assigned R01 scope passed, including all 27 policy
combinations/boundaries, live authorization, frozen-source behavior, omissions
and real-browser presets. The retained actual 300-second identity-expiry and
D02/D03 save/submit/lost-response regressions passed too. No skipped cases or
known failing R01 checks remain. The launcher removed its owned databases,
application processes, two containers and network; no development volumes were
touched. No acceptance/integration or successor execution is implied.

**Data:** no migration, schema, new storage, Grade writer or privilege changes.
Head remains `0009_finalization`; clean/prior-head upgrade and recovery rules
are unchanged. The result reader may invoke D03 finalization for an overdue
attempt and returns only after that transaction commits.

**Known scope limits / successor handoff:** T01 must first wait for B.C.'s R01
acceptance/integration, then use the completion link and generated
`LearnerResult` for both presets and the controlled expired fixture. Do not treat
a submission acknowledgement as a result read. R02 owns history and author
reporting: reuse this learner authorization/projection service in a bounded
transaction, re-evaluate time each read, preserve the status unions and stable
attempt/version/question IDs, and never reuse private Grade objects as learner
DTOs. Author reporting needs its separately authorized owner relationship;
this endpoint does not grant it. No A01, Phase 3, pilot, full WCAG or timed-UX
acceptance is implied.

## D03 finalization and expiration

**Acceptance/integration, 23 October 2026:** B.C. confirmed review and remote-main
integration and directed R01. Accepted [PR #13](https://github.com/bc-bah/quezo/pull/13)
merge `0cfbff7bb65c9bbad2be049df729459c516516b0` includes implementation `9ff05f8`.
R01 verified this commit and the full ancestor/approval chain below. The
Grade/state contract and recorded evidence are accepted. The following is the
historical review handoff, not a current integration-pending claim.

**Work item / owner:** D03, B.C.; assigned 21 October 2026, execution directed
22 October following explicit D02/S01 acceptance. **State: ready for review**;
local implementation and final checks complete, no acceptance or integration claim.

**Integration gate:** D02 merge `c7d6f7e0d9785e220530536078241725b3588547`
(implementation `fbe93da`, follow-up `a82bc36`) and S01 merge
`c9448f78cd6aee397763d37e8d33f8004a441862` (implementation `00195df`)
are ancestors of this checkout. So are D01 `b5751a9`, C02 `03797bc`,
C01 `e66f459`, I02 `553a2c8b77a770667f4cef6825f57c3b55f477ed` and
Phase 2 approval `49eb37b133e737f61f30a97329940bd6281b2c5a`.
B.C. confirmed both producers and directed the backlog reconciliation; this
is the serialized D03 lifespan/fixtures/generated-contract/migration window.

**Changes / requirements:** ATT-03/04, SCORE-01, IAM-02, QUAL-01/04/08 and
section 7 submission/errors; FR-034/035/036/040/041/042.
`attempts/finalization.py` owns the shared parent
lock, post-lock live authorization, database wall clock and atomic S01 adapter.
No new scoring rules: only private frozen question snapshots and persisted
accepted response selections enter `ScoringInput`. An adapter/scoring/write/
commit failure rolls back the entire completion. No request contains answers.

| Contract | Shape / behavior |
| --- | --- |
| `POST /api/v1/attempts/{attempt_id}/submission` | Strict empty JSON object `{}`; no answer, key, score or timestamp fields. HTTP 200 after commit, including repeats. Identity/ownership checked before replay and after the lock wait. |
| `Completion` | `{attemptId, state: "finalized", completionReason: "submitted" or "expired", finalizedAt}`. Stable completion metadata only; no Grade ID, earned score, outcomes, key or feedback, regardless of release preset. |
| `Attempt.completion` | Null while in progress; the same `Completion` after finalization. Only terminal state is `finalized`; `expired` is a reason, not another state. OpenAPI/TypeScript regenerated. |
| Late fresh save | Reconciles expiry in the transaction, commits it, then returns 409 with authoritative state/deadline/time. Never adds the late answer. Accepted save replay retains its original acknowledgement with fresh finalized state. |
| Internal Grade | `quezo.grades`: UUID `id`, unique `attempt_id`, exact `earned_points` and `possible_points`. `grade_items`: frozen `question_id`, `attempt_id`, outcome and integer item points. Private storage, never an ordinary learner DTO. |
| Minimal integrity event | `attempt_completion_events`: unique `attempt_id`, reason and finalization instant; committed with Grade, every item and attempt transition. |

**Locks / time:** start retains assignment -> existing attempt, or assignment ->
quiz share for a new snapshot. Read/save/submit lock only the owned attempt;
they never acquire assignment or quiz locks afterward. Live authority is read
inside the transaction and again after the wait. Only then is
`clock_timestamp()` sampled. At equality or later the reason is expired;
strictly earlier voluntary submission is submitted. Before-deadline admitted
saves remain valid even if commit crosses the deadline. Finalization never
re-reads the mutable bank or accepts pending browser answers.

**Worker lifecycle:** startup executes one bounded catch-up batch before serving.
Every five seconds, one transaction selects at most 20 overdue parents ordered
by deadline/ID with `FOR UPDATE SKIP LOCKED`, then uses the same finalizer with
a fresh database clock for each locked parent. Multiple processes cannot grade
the same attempt twice. The existing bounded pool is reused; no new pool,
external queue, HTTP background task or automatic transaction retry is added.
Dependency failures during scheduled sweeps produce a sanitized
`DEPENDENCY_UNAVAILABLE` log; the next ordinary scheduled sweep can recover.
Startup/schema errors fail startup, unexpected task errors propagate through the
lifespan TaskGroup, and shutdown cancels/awaits the worker before closing the
pool. Cancellation rolls back an unfinished batch. More than one startup batch
is caught by subsequent bounded ticks.

**UI:** submission stays in the D02 editor and is disabled while a save is busy
or an edit, conflict, failed/uncertain save or reconciliation remains unresolved.
All unanswered items are counted in a native confirmation. During submission
or an unknown outcome, answers are frozen; retry is explicit and addressed only
by attempt identity. Reconcile/reload can recover committed completion.
Submitted/expired confirmation never displays a fabricated zero or bypasses
release policy. No countdown or timing-adjustment controls; DEC-09 stays held.

**Data / R01 inputs:** migration `0009_finalization` follows `0008_responses`;
see the [migration runbook](../postgres/migrations/README.md#d03-finalization-storage).
R01 can read the immutable Grade/items, completion reason/time and D01 frozen
policy only after this package is accepted/integrated. It must apply independent
release fields on each result read, never expose the private scorer DTO or add
another Grade writer. No history, regrade, admin override or successor dispatch.

**Initial acceptance evidence:**

| Acceptance | Executable coverage |
| --- | --- |
| AT-09 initial | Real post-lock deadline rejection, deterministic equality using a controlled database-sampled deadline, valid before-deadline saves/submissions committing afterward, request-triggered expiry, bounded `SKIP LOCKED`, startup catch-up, cancellation, scheduled dependency-error reporting and recovery |
| AT-10 initial | Repeated save/submit races, duplicate/replayed submission, concurrent independent worker processes with HTTP save/submit, scoring/write/deferred-commit rollback, immutable/complete Grade constraints, and real browser transport loss after dispatch/commit followed by safe retry |
| AT-11 initial | S01 unchanged pure scoring suite plus D03 persisted-response adapter: MCQ/true-false, point override, correct/incorrect/unanswered, correct zero-point item, all-unanswered expiry; S01/publication retain zero-total rejection |
| AT-08 submission guard | Actual browser pending-save/newer-edit/offline/conflict/failed-save blocking, unanswered confirmation and unknown-outcome retry |

The focused real-PostgreSQL command, using the existing `run_browser` disposable
Compose lifecycle and guarded `db_helpers` databases, passed **97 cases in
435.12 seconds**:

```text
uv run --directory postgres --locked pytest --tb=short -x tests/test_finalization.py tests/test_finalization_migrations.py tests/test_responses.py tests/test_attempts.py tests/test_attempt_migrations.py tests/test_response_migrations.py tests/test_app.py tests/test_migrations.py
```

That run preceded the additional release-mode, repeated-process-race,
wrong/zero-point and delayed-submit cases; those are included in the final common
checks. `npm run test:e2e -- --grep D03` passed both real-browser journeys
(10.357s controlled expiry, 24.225s durable-save/submission journey), before the
additional focus-during-submit regression assertion. `npm run test:contracts`
passed 88 Python and 2 tooling/client tests; `npm run typecheck` passed web/API/
browser types. `npm run api:generate` regenerated, not manually edited, contracts.

Environment: Windows, Node 24.20.0, npm 11.19.0, uv 0.12.17, Python 3.12.10,
PostgreSQL 17.11, Keycloak 26.4.7, Playwright 1.64.1 and Chromium 156.0.8078.4.
Docker Desktop was initially stopped and was started for isolated validation.
Missing npm dependencies were restored with `npm ci --no-audit --no-fund`.
Initial iterations corrected test-only module search paths, duplicate synthetic
identity seeding and implemented-route/table allowlists; the targeted run above
then passed. One standalone mypy process exited abnormally; the subsequent full
typecheck passed without changing application code for that interruption.
No hosted CI, timed-accessibility, human screen-reader, load threshold, release
filtering or backup/recovery acceptance is claimed.

**Final common checks:** `npm run test:e2e -- --checks` completed successfully
in one invocation, using owned project `quezo-i02-c4b14d512362`:

| Command / stage | Result |
| --- | --- |
| `npm run typecheck` | Web, API (80 source files) and browser types passed |
| `npm test` | 12 web tests and **611 Python tests passed**, 859.72s for Python |
| `npm run build` | Production build passed, including the final submit/focus guard |
| `npm run api:check` | Exported OpenAPI and generated TypeScript current |
| `npm run test:contracts` | **88 Python + 2 tooling/client tests passed** |
| `npm run test:db` | **246 passed**, 827.97s; clean and actual prior-head migrations, concurrency, worker processes and cancellation |
| `npm run test:identity` | **108 passed**, 93.65s |
| `npm run test:identity:integration` | Actual Keycloak case passed, 9.13s |
| `npm run test:web:production` | Built-web HTTP/database/OIDC boundary passed |
| Full real-browser suite | **27 passed**, including the unchanged 300-second identity expiry, D03 controlled expiry (6.420s) and D02/D03 save/submit/response-loss journey (23.785s) |

The final browser run includes the focus-during-submit regression assertion and
all secret-safe teardown checks. `npm run typecheck:web` and
`npm run typecheck:e2e` also passed after the final guard/assertion changes.
The launcher removed its owned containers/network and fixture databases; no
development volumes were touched. `git diff --check` passed.

**Acceptance / known gaps:** AT-09/10/11 **initial D03 scope passed**, as did
AT-08's submission guard. The final suites cover every D03 criterion above;
no known failing D03 check remains. Equality is exercised with a controlled
database-sampled clock value, while actual lock waits and late commits use
real wall-clock deadlines. This is not full schedule/DST, timed-accessibility,
release-policy or P0 acceptance. B.C. still owns review and integration.
The backlog retains D03 as active with this review-ready handoff. No commit,
PR, regrade/admin override or R01/T01 dispatch was made.

## S01 pure objective scoring

B.C. confirmed acceptance and integration on 22 October 2026, at merge
`c9448f78cd6aee397763d37e8d33f8004a441862`, implementation `00195df`
([PR #12](https://github.com/bc-bah/quezo/pull/12)).
`modules/scoring.py` accepts immutable validated `ScoringInput` values:
ordered `QuestionSnapshot` tuples (attempt-question ID, type, delivered option
IDs, private key and effective integer points) and `SavedResponse` tuples.
`score()` returns immutable `Score`/`ItemScore` values with exact integer totals
and distinct correct/incorrect/unanswered outcomes; zero-point items retain their
outcome. Invalid membership, duplicates and zero possible total are rejected.
`tests/test_scoring.py` is the pure executable evidence. No database, HTTP,
Grade persistence or disclosure is owned by S01. D03 must adapt only frozen
questions and persisted accepted responses under the parent lock; it must not
duplicate scoring rules or replace invalid input with a zero grade.

## D02 durable response save and resume

**Work item:** D02. **Owner/integrator/reviewer:** B.C.; assigned 21 October 2026.
**State:** accepted and integrated by B.C. on 22 October 2026 at merge
`c7d6f7e0d9785e220530536078241725b3588547`, implementation `fbe93da`
and browser follow-up `a82bc36`
([PR #11](https://github.com/bc-bah/quezo/pull/11)).
The original local evidence and its execution limits below are retained.
B.C. confirmed D01 review/acceptance and directed its tracking reconciliation
before D02 implementation. This checkout includes D01 merge
`b5751a94ce2ab36be8add8070bbbd99573175d0a` / implementation `cbb74f5`
([PR #10](https://github.com/bc-bah/quezo/pull/10)), C02 `03797bc`,
C01 `e66f459`, I02 `553a2c8` and current Phase 2 approval `49eb37b`.
The accepted frozen snapshot and assignment -> attempt lock order are unchanged.
B.C.'s post-D01 shared-file window covers generated errors/client, test discovery,
migration-head expectations, learner navigation and these directly related docs.

**Changes / requirements:** `modules/attempts/responses.py` owns ATT-02 save
CAS/replay and ATT-03 admission. `0008_responses` owns response/ledger persistence.
The learner response editor provides explicit per-question Save/Clear, native
question links, saved/unsaved/saving/offline/conflict announcements and deliberate
conflict resolution. It preserves newer input while an earlier edit is saving.
Server-only learner actions reuse the live facade/Host/Origin/error contracts.
IAM-02 checks precede replay and are repeated after the parent lock wait.
QUAL-01/04 coverage uses real PostgreSQL and authenticated Chromium.

**Saved-response and command contracts:**

| Surface | Shape / behavior |
| --- | --- |
| `Attempt.questions[].response` | `{selectedOptionId: UUID or null, revision: integer, savedAt: UTC timestamp or null}`. Initial state is exactly null/0/null; explicit clears have a positive revision and timestamp. Frozen IDs/order/content are unchanged. |
| `PUT /api/v1/attempts/{attempt_id}/responses/{question_id}` | `question_id` is D01's **attemptQuestionId**, not original question/version ID. Strict body `{requestId, expectedRevision, selectedOptionId}`; all fields required, including explicit null. UUID/revision/extra-field and frozen-option validation reject malformed writes. |
| Success, HTTP 200 after commit | `{acknowledgement: {requestId, responseRevision, savedAt}, attemptState, serverTime}`. The acknowledgement is retained and stable; surrounding state/time are fresh. No grades, keys, feedback, fingerprint or private snapshot is returned. |
| Stale CAS, HTTP 409 | `RESPONSE_REVISION_CONFLICT` with `{currentRevision, selectedOptionId, savedAt}` in the authorized error details; null is preserved. |
| Changed key payload, HTTP 409 | `IDEMPOTENCY_CONFLICT`; fingerprints bind actor/attempt/operation/request, frozen question and normalized payload. Reusing a key on another question in that attempt conflicts too. |
| Fresh terminal/late write, HTTP 409 | `ATTEMPT_FINALIZED` / `DEADLINE_PASSED`, details `{attemptState, deadline, serverTime}`; no answer mutation. |

**Atomicity / admission:** lock only the owned parent attempt, re-resolve live
authority, read the frozen question and scoped ledger, then read PostgreSQL
`clock_timestamp()`. Authorized exact replay precedes fresh state/deadline/CAS
admission, so accepted commands remain replayable after expiry/finalization.
New writes require `in_progress` and database admission time strictly before the
deadline, if present. A predeadline admission can commit afterward. Response,
revision, admission timestamp and retained acknowledgement commit together;
commit-time failure cannot produce success. No database retry loop or ledger
cleanup is introduced. Do not acquire assignment/quiz locks after the parent.

**Browser / D03 input:** saves are explicit and single-flight per question, not
an autosave loop. An acknowledgement marks only its captured local edit saved;
newer input remains unsaved. Uncertain outcomes retain the exact command/key.
Reconnect, focus/resume and the Reconcile button fetch authorized persisted state
before retry; retry is explicit and reuses the uncertain command. A stale write
retains local input and requires **Use persisted answer** or **Keep my local
answer**, followed by an explicit save. No cross-tab winner is silently chosen.
Offline/transport/rejected saves never show Saved. Terminal admission errors
disable fresh edits but retained commands can resolve an already accepted save.
Unsaved edits are in memory only, with link and native unload warnings. Attempt
entry uses document navigation so browser Back also crosses the unload guard.

D03 must place submission alongside this editor's state: wait for all `busy`
saves, require no pending/dirty/conflicted/failed or unreconciled edits, and
confirm unanswered questions. Submit must never transmit an answer payload.
Read `attempt_responses` under the same parent lock and grade only persisted
selections against private frozen questions. D03 owns finalization, expiration
reconciliation/worker, final timestamps and grades. Until then a past-deadline
attempt can still report `in_progress`; `DEADLINE_PASSED` prevents writes without
pretending a grade or finalization exists. No submission/result control, timer
or fabricated grade is added here.

**Data:** single head `0008_responses` follows `0007_attempt_start`. Existing
frozen questions receive unanswered revision-zero rows; future snapshots initialize
them transactionally. Composite FKs, revision/option/state checks and deferred
acknowledgement completeness protect storage. Ledger rows cannot be changed or
deleted; response deletion is forbidden. Preserve responses and ledgers together
in recovery. See the [migration runbook](../postgres/migrations/README.md#d02-durable-response-storage).

**Acceptance / checks:** all common check stages and the final full browser
suite passed as recorded below. Focused `test_responses.py`, `test_response_migrations.py`,
`test_app.py` and `test_attempts.py` passed **56 cases** using a disposable real
PostgreSQL service. `npm run test:contracts` passed **88 Python + 2 tooling/client**
cases. AT-07 covers refresh/restart, clear, duplicate/key reuse and stale/cross-tab
writes. D02's AT-08 scope covers offline/newer input, lost acknowledgement,
reconciliation/retry and visible safe errors. The actual submission pending-save
guard remains D03, not a D02 acceptance claim.

The focused command
`uv run --directory postgres --locked pytest -x --tb=short tests/test_responses.py tests/test_response_migrations.py tests/test_app.py tests/test_attempts.py`
ran inside a unique disposable PostgreSQL Compose project using the existing
`run_browser` environment/lifecycle helpers and guarded `db_helpers` databases:
**56 passed in 226.59 seconds**. `npm run test:e2e -- --grep D02` then passed
the complete D02 browser journey, including privacy teardown, in **28.333 seconds**
of browser-test execution (service setup/build are additional).

The `npm run test:e2e -- --checks` run completed every non-browser stage:

| Command | Result |
| --- | --- |
| `npm run typecheck` | Web, API (72 source files) and browser types passed |
| `npm test` | 12 web tests; 500 Python tests passed in 769.03 seconds |
| `npm run build` | Production build passed |
| `npm run api:check` | OpenAPI and generated TypeScript current |
| `npm run test:contracts` | 88 Python and 2 tooling/client tests passed |
| `npm run test:db` | 217 passed in 842.37 seconds, including clean migration and actual prior-head response upgrade/backfill |
| `npm run test:identity` | 108 passed |
| `npm run test:identity:integration` | Real Keycloak integration passed |
| `npm run test:web:production` | Built-web HTTP/database/OIDC boundary passed |

That combined invocation exited nonzero on the browser privacy-fixture timeout
described below; it is not claimed as an uninterrupted green run.
After the final local-edit counter change, `npm run typecheck:web` and
`npm run build` passed again. After the privacy-observer correction,
`npm run typecheck:e2e` passed. The final `npm run test:e2e` rebuilt the current
web application and passed **all 26 browser cases**, including the unchanged
300-second identity expiry case and D02 in **23.905 seconds**. The launcher
removed its owned services/network; no development volumes were touched.

Environment: Windows, Node **24.20.0**, npm **11.19.0**, uv **0.12.17**,
Python **3.12.10**, PostgreSQL **17.11**, Keycloak **26.4.7**,
Playwright **1.64.1**, Chromium **156.0.8078.4**. All identities/data/services
are synthetic and local. No hosted CI, manual screen-reader audit, database
backup/recovery acceptance or timed-UX result is claimed.

| D02 criterion / acceptance | Executable evidence |
| --- | --- |
| Initial null/0/null, frozen-option membership, explicit clear, malformed rejection | `test_save_clear_replay_stale_and_lost_ack`, `test_strict_save_input`, `test_missing_clear_foreign_option_and_question` |
| Concurrent CAS, exact replay, changed key payload, retained original acknowledgement | `test_concurrent_response_cas`, `test_save_clear_replay_stale_and_lost_ack`; unique/immutable ledger constraints |
| Rollback and commit-before-success | `test_rollback_including_deferred_commit_failure` rejects both mid-command and deferred commit failures with no persisted response/ack |
| Post-lock authority/deadline, strict boundary, predeadline admission committing late | `test_queued_save_rechecks_authority_and_state`, `test_post_lock_deadline_and_ack_after_expiry`, `test_predeadline_admission_can_commit_after_deadline`, exact microsecond admission helper test |
| Authorized replay after expiry/finalization without mutation | `test_terminal_replay_is_ack_only_and_live_authorized`, post-lock deadline/replay test; terminal states are controlled fixtures, not D03 implementation |
| AT-07 acknowledged refresh/restart, clear and cross-tab handling | `responses.spec.ts`: both question types, web/API restart, deliberate stale conflict and explicit local replacement; database replay/key-reuse cases |
| AT-08 D02 scope | Same real browser journey: offline announcement/discard warning, reconnect reconciliation, newer edit during save, actual transport-lost acknowledgement and same-key retry, safe API-outage recovery |
| Learner nondisclosure and migration integrity | JSON/HTML/RSC checks in `responses.spec.ts`; response/migration constraint tests, web-role denial, actual prior-head backfill/repeat upgrade and clean-head suite |

Initial iterations exposed stale implemented-path/table allowlists and test
fixture issues (provider SSO between identities, a single observer connection
while holding a lock, and an unreliable in-flight browser-offline fault).
These were corrected without weakening checks. The lost-ack scenario now severs
real web-to-API sockets through a byte-forwarding fixture; it verifies the database
commit before reconciliation/replay. Intermediate runs timed out during privacy
teardown on unresolved Chromium raw-request-header promises for interrupted
requests. The fixture now inspects provisional headers synchronously and actual
wire headers through read-only Chromium network events; auth response/cookie,
DOM/storage and application-log checks remain enforced. The final full suite
completed every privacy check.

A later run had one existing C01 stale-edit locator timeout; that unchanged
case passed in isolation (8.418 seconds) and in the final full run. Another
run lost its PostgreSQL connection during identity expiry and subsequent
fixtures failed setup; Docker's reported engine version changed from 29.7.2
to 29.9.2 during that run. No application fix or timeout relaxation was made
for either interruption. The final full run above passed on the running engine.
No remaining D02 check failure is known. Hosted CI and broader acceptance
limits remain unverified as listed above.

PR browser CI on `fbe93da` subsequently reported an ambiguous page-wide alert
locator in D01 AT-06 (`attempts.spec.ts:109`). The assertion now scopes to the
main landmark and verifies the exact not-found message, rather than allowing
unrelated alerts such as the framework route announcer to match. The original
ambiguity did not reproduce locally, including after waiting for the announcer
to mount. With the scoped assertion, `npm run typecheck:e2e` and
`npm run test:e2e -- --grep "D01 AT-06"` passed (13.566 seconds for the browser
case). Hosted confirmation of this follow-up is pending.

## D01 assignment and attempt start

**Work item:** D01. **Owner/integrator/reviewer:** B.C.; assigned 21 October 2026.
**State:** accepted and integrated, confirmed by B.C. on 22 October 2026.
[PR #10](https://github.com/bc-bah/quezo/pull/10) merged at
`b5751a94ce2ab36be8add8070bbbd99573175d0a`, including implementation `cbb74f5`.
B.C. accepted the snapshot/locking contract below and directed D02 execution
after this tracking reconciliation; no later successor dispatch is implied.
The complete common gate passed, including all 25 real-browser cases.

**Integration:** the live C02 acceptance was already recorded. On 22 October
2026, `gh pr view 9 --json state,mergedAt,mergeCommit,url,headRefOid` verified
[PR #9](https://github.com/bc-bah/quezo/pull/9) merged on 21 October at
`03797bcbb545ec188da941ff6bb02e380f5b9f1b` (implementation `67ce98a`).
Git ancestry checks verified C01 `e66f459`, I02 `553a2c8` and Phase 2 approval
`49eb37b` in this checkout. The stale integration-pending text was corrected
before implementation. C02's accepted publication/policy contract is unchanged.
Shared edits use D01's post-C02 window: router registration, minimal navigation,
generated artifacts, test discovery/head expectations and directly related docs.

**Changes / requirement coverage:** `modules/distribution` owns minimal
active-learner lookup and unique pinned assignments (AUTH-04/IAM-02).
`modules/attempts` owns atomic start/resume, admission, allowance, ordering and
private-to-learner projection (ATT-01, ATT-03 admission, sections 6-7).
Author publication pages offer explicit assignment. `/learner` lists only the
current learner's assignments; `/learner/attempts/{id}` renders the authorized
stored snapshot with no answer controls or implied save/submit.
The demo remains untimed, unscheduled, one attempt and nonrandomized.

**HTTP contracts:** exported normally through `npm run api:generate`;
TypeScript uses that output, not handwritten parallel DTOs.

| Operation | Contract and authority |
| --- | --- |
| `GET /api/v1/eligible-learners` | Author role; paginated active accounts with learner role and active mapping. Items contain **only `userId`**. The existing identity producer has no name/email profile; selection uses the application UUID, not provider subject/email/roles. |
| `POST /api/v1/assignments` | `AssignmentCreate {quizId, versionId, learnerId}`; author must own the quiz and nested immutable publication; recipient must be active/eligible. 201 for new pair, 200 for its existing assignment, never a counter reset. |
| `GET /api/v1/assignments`, `/{assignment_id}` | Learner role and ownership; bounded UUID-ordered pagination. Summary contains IDs, title, state, started/completed/remaining counts, active attempt UUID and availability bounds, **no questions/options/private scoring**. |
| `POST /api/v1/assignments/{assignment_id}/attempts` | Learner ownership, UUID `Idempotency-Key`, strict empty `StartCommand {}`. 201 only for a new committed attempt; 200 for active resume or original-command replay. |
| `GET /api/v1/attempts/{attempt_id}` | Current active learner role and attempt ownership, including finalized fixture snapshots. Returns only the explicit `Attempt` learner projection. |

All assessment responses are private/no-store; missing/foreign IDs are concealed
as 404 after role checks. Missing role is 403, disabled account is denied even
with an old token, and removed mappings are unauthenticated. Errors use F02's
existing envelopes/codes. Browser writes reuse the server-only facade and
Host/Origin checks; tokens remain server-side. Assignment writes re-resolve the
author after the quiz lock; starts re-resolve the learner after lock waits.

Assignment states are `not_yet_available`, `available`, `in_progress`,
`completed_remaining`, `exhausted`, `closed`. Counts distinguish completed
history even when a schedule/closure takes precedence. An active attempt takes
precedence over closure/zero remaining allowance because closure does not revoke
an already-started attempt. No overdue attempt is silently replaced or given
another allowance; D03 must add the agreed reconciliation/finalization logic.
Publication alone never adds assignments or updates existing version pins.

**Frozen shapes / stable IDs:**

| Shape | Fields and use |
| --- | --- |
| `Attempt` | `id`, `assignmentId`, `versionId`, `attemptNumber`, current `state`, frozen `title`, `instructions`, independent `policy`, `startedAt`, nullable `deadline`, `possiblePoints`, ordered `questions`. |
| Learner `AttemptQuestion` | `attemptQuestionId`, original `questionId`/exact `versionId`, one-based `position`, `questionType`, literal `prompt`, ordered `{id,text}` options, `effectivePoints`. No correct option, feedback or default/scoring definition. |
| Private `attempt_questions` | Exact C02 `question` JSON (C01 `QuestionVersion`, including `correctOptionId`/feedback), frozen `effective_points`, original question/version FKs, stored `options` presentation and `position`, generated question UUID. Backend only; never passed through learner serialization. |
| Start acknowledgement | Retained `attempt_start_commands.attempt_id`, scoped to actor/assignment/`start`/request UUID, with canonical SHA-256 fingerprint. Replay reads that same attempt's current state and original snapshot, even after another attempt exists. |

D02 must address saves by **`attemptQuestionId`**, not bank/question identity.
C01 option UUIDs remain unchanged under shuffling. Each attempt gets new question
UUIDs; question/version IDs retain provenance. Question and option flags permute
the complete selected sets once; refresh never reshuffles. Policy includes all
independent release fields and unlimited nulls. No private scoring model is used
as an HTTP response model.

**Transactions / replay / time:** reuse F01's bounded `Database.transaction()`;
no manual commits, second pools, generic repositories or server retry loop.
Starts acquire the owned assignment `FOR UPDATE`, recheck current identity,
then consult the ledger. The canonical fingerprint includes actor, target,
operation, key and normalized empty payload. A mismatched fingerprint conflicts;
authorization always precedes replay. Each different command that resumes an
active attempt gets its own retained mapping to that attempt.
Active-attempt lookup uses `FOR UPDATE`; fresh admission takes a quiz `FOR SHARE`
lock and reads PostgreSQL `clock_timestamp()` **after** the waits. State,
inclusive start/exclusive end and remaining allowance are enforced there.
Deadline is `min(availabilityEnd, startedAt + duration)` over present bounds,
or null. All snapshots, numbering and the ledger commit before HTTP success.
The number of committed attempts is the consumed allowance, including expiry.

Lock order for successors: assignment -> existing attempt, or assignment ->
quiz share for new starts. D02/D03 lock the parent attempt for response CAS and
finalization; do not acquire assignment/quiz locks afterward. Close must serialize
on the quiz row without reversing this order. There is no ledger cleanup policy.
The UI retains its start command key while mounted for uncertain retries;
after reload it reconciles via the assignment's existing active attempt.

**Data / recovery:** `0007_attempt_start` follows actual prior head
`0006_quizzes`; existing revisions are untouched. Composite foreign keys,
unique learner/version and assignment/number pairs, one-active partial index,
immutable snapshot triggers, complete-publication-copy checks and deferred
attempt completeness back up application rules. Restricted column UPDATE on
assignment ID permits row locking but its trigger rejects every mutation.
No assignment deletion/reassignment/revocation is introduced. See the migration
README for privileges, clean/prior-head tests and forward-only recovery.

**AT-06 evidence:** `test_attempts.py`, `test_attempt_migrations.py` and
`tests/e2e/attempts.spec.ts` cover initial/duplicate assignment races, identical
and distinct concurrent start keys, one consumed allowance, finalized replay,
expired allowance, role/foreign/nested IDs, strict payloads, rollback, active
resume after closure, minimal lookup and pre-start nondisclosure.
All four ordering flag combinations use a deterministic reversal fixture to prove
both branches, complete sets and stored refresh order. Real-database finite
deadline fixtures cover each bound; exact microsecond admission is also tested
at the pure admission seam. Held assignment locks prove post-wait role revocation
and database-time schedule rejection. Actual browser work creates/publishes/
assigns and lists/starts/reloads/resumes, checking JSON and HTML/RSC in memory.
Fixture-only `finalized`/`expired` updates test D01 contracts, not grading or D03.

**Checks:** final `npm run test:e2e -- --checks` exited 0 with owned project
`quezo-i02-40267e4ad2f7`. The preceding focused D01 browser run also exited 0
with owned project `quezo-i02-7453f04875ed`. Both removed their disposable
PostgreSQL/Keycloak containers and networks; no development volumes were used.
Environment: Windows x64, Node 24.20.0, npm 11.19.0, uv 0.12.17,
Python 3.12.10, Docker Engine 29.7.2, PostgreSQL 17.11, configured Keycloak
26.4.7 and Chromium 156.0.8078.4 (Playwright 1.64.1).

| Final command / stage | Result |
| --- | --- |
| `npm run api:generate` | OpenAPI and TypeScript regenerated normally |
| `npm run typecheck` | Web/e2e TypeScript and strict mypy over 68 modules passed |
| `npm test` | 12 web tests and 475 Python tests passed; Python 754.60 seconds |
| `npm run build` | Production Next build passed, including author assignment and learner list/attempt routes |
| `npm run api:check` | OpenAPI and generated TypeScript current |
| `npm run test:contracts` | 88 Python and 2 Node tooling/client cases passed; missing start idempotency header rejected at compile time |
| `npm run test:db` | 192 cases passed in 712.14 seconds; includes real database race/rollback/constraint checks, clean/prior-head migrations and five pure exact-boundary cases |
| `npm run test:identity` | All 108 retained identity cases passed |
| `npm run test:identity:integration` | Actual Keycloak integration passed |
| `npm run test:web:production` | Built-web boundary/redaction case passed |
| `npm run test:e2e -- --grep D01` | Actual author/learner journey passed, 15.769 seconds |
| Unfiltered browser suite in `--checks` | All 25 passed: 16 I02, 5 C01, 3 C02, 1 D01; D01 11.648 seconds |
| `uv run --directory postgres --locked alembic heads` | Single head `0007_attempt_start` |

The D01 Python files contribute 26 passing cases (21 database-backed cases and
five pure boundary cases). All assigned AT-06 scenarios passed in the final
common gate. `test_actual_publication_head_upgrade_preserves_history` verifies
the actual `0006_quizzes -> 0007_attempt_start` path and repeat head against an
existing publication; retained clean migration checks verify `base -> head`.
Failed upgrade/transaction fixtures prove rollback without allowance consumption
or partial snapshots. No hosted CI, Node 22/Python 3.14 or manual accessibility
result is claimed.

Earlier focused iteration used the existing `run_browser` environment/Compose
and guarded `db_helpers` conventions in a temporary session-only launcher
(subsequently removed). The final common gate discovers all package tests
through committed test paths and root scripts; no custom runner is required.
Docker was initially stopped and was started with `docker desktop start`.
Missing npm dependencies were restored with `npm ci` after generation reported
the missing package; no dependencies or lockfiles were changed.

Initial
iteration caught the required PostgreSQL column UPDATE privilege for assignment
row locking, a browser assertion that observed the still-visible list heading
before navigation, a foreign-FK fixture masked by duplicate-pair uniqueness and
retained pre-D01 route-inventory expectations. These were corrected without
weakening ownership, private-table access or nondisclosure checks.
The first complete run had 471 passes, the two now-corrected inventory failures
and a migration subprocess timeout with a large elapsed-time jump; a concurrent
focused browser run also timed out in setup. Their exact host cause was not
established. The final sequential runs passed without relaxing timeouts, adding
runtime retries or bypassing services. No logs with raw assessment/credential
payloads, screenshots, trace, HAR or browser storage-state artifacts were retained.

**Known gaps:** no unresolved criterion within the assigned D01 slice.

**Successor handoff / excluded scope:** no saves/responses, submission, Grade,
result UI, worker expiry or timed accessibility UX. D02 adds response rows and
revision/acknowledgement behavior using the frozen question/option IDs above.
D03 adds actual expiry/finalization and grades, extends reserved state metadata
with a forward migration, and wires overdue-read/write reconciliation without
changing attempt deadlines or retained start mappings. These consumers still
require B.C.'s D01 acceptance and integration; no successor is authorized here.

## C03 complete author workspace

**Assignment:** B.C. confirmed integration/review ownership on 27 October 2026
and confirmed D04 is unassigned. C03 has the exclusive shared editor/assembly,
generated-contract and next-migration window. Branch
`feature/c03-author-workspace` starts at integrated dev `354da49`, which contains
T01 merge `df06ccc`; the input migration head was `0009_finalization`.
The original review handoff below is superseded by the acceptance record here;
it is not deployment approval or a claim that the entire catalogue is complete.

**Acceptance/integration, 27 October 2026:** B.C. reviewed the updated local
Docker application, confirmed satisfaction, requested staging/commit/merge to
local `dev`, then directed acceptance/backlog reconciliation. Commit
`2eba9eb8f2986664687059f974ad4282b0b1dd49` was fast-forward integrated into local
`dev`; no remote push/PR or hosted CI is claimed. C03's exclusive writer window
is complete. The [acceptance record](implementation/BACKLOG.md#c03-acceptance-and-next-package-readiness-27-october-2026)
retains case-level AT evidence and the umbrella-check limitation.

The existing local stack was rebuilt using
`docker compose --env-file .env.docker -f compose.local.yaml -f infra\docker\compose.ca.yaml up -d --build --wait`.
The public Windows CA build-secret override was used without disclosing secrets.
Database and Keycloak volumes/accounts were preserved; migration
`0010_author_workspace` applied successfully. All services were healthy, web
returned HTTP 200, API liveness and new C03 routes were checked.
Open `http://localhost:3000` (not `127.0.0.1`, because realm redirects are exact).
This is local synthetic validation, not hosted deployment/pilot approval.

### Organization and reuse

Use **Question banks** to create/rename banks and **Search questions** to search
all owned questions. Bank pages provide the same search within that bank.
Prompt text uses a case-insensitive literal substring, not wildcard or regular
expression matching. Category and tag filters are exact and can be combined with
text/bank filters. All filters survive bounded, stable UUID-cursor pagination.
Category is optional (1-100 characters when supplied); each of up to 20 tags is
1-50 characters. These are current question-organization metadata, not learner
content or retroactive additions to immutable question/publication/attempt
snapshots. Question content edits still create immutable revisions. Omitting
metadata in a direct edit preserves it; explicit null category/empty tags clear it.

The question page moves a question to another active owned bank without changing
question/version identity. Destination-bank choices are paginated. An unarchived
question may be moved out of an archived bank; an individually archived question
is read-only. Bank/question archive requires UI acknowledgement explaining retained
history. Default lists/search and the quiz selector exclude individually archived
questions and every question in an archived bank. Explicit **Include archived**
management views retain inspection links; they do not make that content selectable.
Archive is the approved removal operation; no destructive delete/restore command
is introduced.

The composition selector supports bank/text/category/tag filtering and pagination,
reuse in multiple quizzes, exact historical revision IDs and explicit **Use latest
revision** per selected question. That button changes only the local draft pin
until save; ordinary question edits never update pins silently. New selections
are rechecked under question/bank share locks by the authoring module, including
direct service calls. Archived content cannot be newly inserted through a forged
exact revision. An already-retained exact pin can still be saved, previewed and
published after its source is archived; changing its version or selecting it in a
new quiz is a new selection and is rejected. Existing publications are never
rewritten.

### Draft and publication lifecycle

The quiz route owns the editor wrapper and integrates the unchanged D04 policy
subview. It shows paginated immutable publication history with exact version links.
Revision-draft creation remains explicit while the current publication stays live.
Save, preview and publication use expected draft revision; stale tabs retain local
edits, show the conflict and offer an explicit reload/discard action. Publication
continues to use the retained idempotency command and immutable snapshots.

Close serializes on the same quiz row used by draft/publication commands and new
attempt admission. It blocks starts across all publications, freezes any pending
draft and preserves existing attempts' deadlines/resume/finalization. Archive
accepts a never-published draft or a closed quiz with no persisted in-progress
attempts. It rejects published-to-archive, reopening and all archived/closed edits
or publication. Both controls explain history retention; archived quizzes remain
available in an explicit management view and publication detail stays accessible.
The preview still uses the learner-safe projection and creates no assignment,
attempt, grade or reporting records. No D04 policy controls were added.

### Contracts, data and acceptance evidence

New routes: bank archive; question organization read/move/archive; publication
history; quiz close/archive. Existing bank/question/quiz lists gain archive
visibility parameters; question search adds `text`, `category` and `tag`.
The generated OpenAPI and TypeScript client remain authoritative. Author-role
and ownership checks apply before lists/search, cursor resolution, nested IDs
and direct service operations. Foreign resources are 404; non-author roles are
403, including administrator-only actors.

`0010_author_workspace` follows the actual `0009_finalization` head and adds
nullable category and bounded tag-array columns to stable questions, with
independent database checks. It changes no immutable-version schema, publication
trigger, attempt, response, grade or command ledger. Clean/upgrade/repeat-head and
failed-upgrade rollback checks use disposable PostgreSQL. Existing applied
revisions are unchanged. Recovery is forward-only and must preserve the existing
history/ledgers; do not delete development volumes or rewrite an applied revision.

| Catalogue scenarios | Inherited from accepted T01 inputs | New C03 evidence | Remaining boundary |
| --- | --- | --- | --- |
| AT-03: both question types, input bounds, ownership | C01 question schema/persistence tests and real-browser creation/edit/bounds/foreign-author cases | `postgres/tests/test_author_workspace.py`: metadata lower/upper/invalid bounds, combined literal/category/tag search, pagination, move/archive, role/nested-ID/direct-service checks; `tests/e2e/author-workspace.spec.ts`: native metadata/search/page/move/archive and real foreign-author denial | Browser metadata-bound combinations are representative, not every boundary permutation; exhaustive new bounds are HTTP/database tests |
| AT-04: reuse, new revisions, unchanged publications/attempts/grades | C02 reuse/immutable-publication tests and T01 frozen-attempt/finalization/result cases | C03 tests explicitly update one draft pin, retain the other quiz/publication, change prompt/key/points/feedback, archive sources/quiz, and compare stored private attempt snapshots, old publication and finalized result/grade records | No regrade, reset or duplicate-quiz command |
| AT-05: draft/preview/publish, stale conflict, publish replay, invalid states, no preview side effects | C02 CAS/concurrent publish/replay, learner-safe preview and zero assignment/attempt/grade side-effect assertions; C02 real stale-tab/outage UI tests | C03 persistence tests cover close/draft race, stale close, frozen pending revision, invalid transitions, active-attempt archive rejection, resume/finalize after close, unpublished abandonment and retained publication history; C03 browser journey covers explicit update/preview/history/close/rejected archive/final archive | Advanced delivery-policy editing and timed preview/accessibility remain D04/DEC-09; this package makes no blanket full-AT or Q02 accessibility acceptance claim |

Focused checks during implementation use the guarded isolated PostgreSQL helpers
and `npm run test:e2e -- --grep C03`. The common application/browser gate is
`npm run test:e2e -- --checks`; run outcomes are recorded at handoff. The browser
suite uses actual Keycloak sign-in, server sessions, JWT/JWKS validation, the
production Next build and restricted PostgreSQL, not injected actors or API
response substitutes. The Python HTTP tests use real JWT verification/persistence
with the existing controlled signing-peer transport; they are not independent
real-provider evidence.

**Executed checks, 27 October 2026:** Windows, Node 24.20.0, Python 3.12.10,
uv 0.12.17, PostgreSQL 17.11, Chromium 156.0.8078.4 and the locked Playwright
1.64.1. All database/browser services were newly owned disposable services;
the launchers removed them and their networks without touching development data.

| Command | Outcome |
| --- | --- |
| `npm run api:generate` / `npm run api:check` | Passed; OpenAPI and TypeScript client are current |
| `npm run typecheck` | Passed: Next/TypeScript, strict mypy (87 sources), browser TypeScript |
| `python -m pytest --tb=short tests\test_author_workspace.py` (from `postgres`, `PYTHONPATH=src`, owned isolated test database supplied by the existing helpers) | 19 passed in 103.87 seconds; includes current-head upgrade, repeat head, failed-upgrade rollback and independent database bounds |
| `npm run test:contracts` | 88 Python cases and 2 Node contract-tool cases passed |
| `npm run test:web:production` (owned isolated database) | 1 built-Next HTTP/database/OIDC-peer case passed |
| `npm run test:e2e` | Production build and all 36 real-provider browser cases passed; zero failures, skips or interruptions, including all 3 new C03 cases and inherited C01/C02/T01 cases |
| `uv run --directory postgres --locked alembic heads` | Single head `0010_author_workspace` |
| `git diff --check` | Passed |

The attempted umbrella `npm run test:e2e -- --checks` passed type checking and
12 web unit cases, then its full Python run reported **665 passed, 2 failed**
in 1081.88 seconds. Both failures were the HTTP contract test's old exact route
inventory, not application/persistence failures. The inventory was updated for
the delivered C03 routes; the subsequent 88-case contract run above passed both
variants. The focused C03 persistence checks and complete production/browser suite
were then rerun successfully. The umbrella launcher itself was **not rerun to a
green end-to-end exit**, and its later duplicate database/identity command stages
are not claimed as separately executed. Earlier focused runs also caught a stale
unsupported-command assertion and an ambiguous browser status locator; both were
corrected before the successful results above. No hosted CI or additional runtime
matrix result is claimed.

Excluded scope remains duplicate quiz, pool selection, imports, rich media,
D04 policy controls and unrelated reporting/account administration. B.C. must
serialize any later migration after `0010_author_workspace` and integrate D04's
settings through the single quiz-route owner. The original implementation handoff
performed no commit/PR or tracker acceptance; the later user-directed local
commit/merge and acceptance are recorded above. No successor dispatch occurred.

## C02 immutable quiz publication

### Acceptance record: 21 October 2026

B.C. explicitly accepted the verified C02 local delivery and directed the
backlog status change from `active` to `done` on 21 October 2026. The publication,
effective-points, independent-policy and lock/replay contracts below are accepted
unchanged, with the recorded passing database/web/browser evidence.

This acceptance is recorded against the uncommitted C02 worktree on C01 merge
`e66f459c5a6b225bd3d1b4bbce6b5b87de67974c`, with migration `0006_quizzes`.
Integration subsequently verified on 22 October 2026: [PR #9](https://github.com/bc-bah/quezo/pull/9)
merged at `03797bcbb545ec188da941ff6bb02e380f5b9f1b` (implementation `67ce98a`).
D01's checkout includes that merge, C01 `e66f459`, I02 `553a2c8` and wave
approval `49eb37b`. No new acceptance decision, test result or successor
dispatch is implied by recording this verified integration.

### Review handoff: 21 October 2026

**Work item:** C02, Immutable quiz publication.

**State at handoff:** ready for B.C.'s review; superseded by the acceptance
record above. The complete
`npm run test:e2e -- --checks` passed with all 24 browser cases and owned-resource
cleanup. B.C. retains acceptance/integration. No commit, PR or successor dispatch.

**Changes:** `postgres/src/quezo_api/modules/quizzes/` owns composition,
independent policy validation, draft CAS, preview projection and atomic
publication. `policies.py` is separate from composition schemas/service;
the author UI similarly separates `composition.tsx` from `policy-settings.tsx`.
`/author/quizzes` provides owned lists, explicit current or historical version
selection, ordering, point overrides, saved-draft preview, confirmed publication
and explicit new revision drafts. Unsaved edits survive safe errors; a stale
revision requires reload/reconciliation, not an automatic overwrite.

**Requirement coverage:** AUTH-02/03, IAM-02, section 6 bounds and section 7
revision/idempotency rules. This is the C02 construction/publication slice, not
the full close/archive/delivery lifecycle or advanced C03/D04 controls.

**Acceptance:** all assigned C02 scenarios below passed in the final unfiltered
real-database/web/browser gate. AT-04 attempt/grade preservation and AT-05
close/archive execution remain later-package cases, not C02 acceptance claims.

| Acceptance | Evidence |
| --- | --- |
| AT-04 | `test_quizzes.py` and `quizzes.spec.ts`: two quizzes reuse the same exact question version; later question edits, draft edits and a second explicit publication preserve the original content, order, option IDs, effective points and policy |
| AT-05 | Saved draft/preview/confirmed publish/new draft; concurrent CAS and publish; one version/event/acknowledgement on replay; changed-key payload, foreign owner, revoked role, stale revision and invalid state rejection; rollback on publication-event failure |
| Preview | Database row/count comparisons show no writes; JSON and browser HTML/RSC omit keys/feedback. Radio selections are local only, with no assignment/attempt/grade/reporting/allowance writes |
| Bounds/policy | Strict content and point limits, 200-question/2,000,000-point publication, duplicate identity rejection, positive-total gate, 27 independent release combinations, finite-end compatibility and backend timed/unlimited/randomized fixtures |
| Persistence | `test_quiz_migrations.py`: actual `0005_questions -> 0006_quizzes`, repeat head, preserved question history, failed-upgrade rollback, SQL policy enforcement, immutable publication/ledger/event rows and incomplete-publication rejection; retained F01 clean migration test |

**Checks:** local Windows x64, Node 24.20.0, npm 11.19.0, uv 0.12.17,
Python 3.12.10, Docker Engine 29.7.2, PostgreSQL 17.11 and Chromium 156.0.8078.4
(Playwright 1.64.1); actual Keycloak 26.4.7. Commands run from this worktree:

```powershell
npm run api:generate
npm run api:check
npm run typecheck
uv run --directory postgres --locked pytest tests\test_quiz_schemas.py tests\test_http_contract.py
node --test postgres\scripts\test_contract_tools.mjs
npm run test:e2e -- --grep C02
npm run test:e2e -- --grep "C02 stale"
npm run test:e2e -- --checks
```

Generation and drift checks passed. Type checks passed for web, e2e and all 57
Python source/test modules. The non-database schema/HTTP selectors passed 106
cases; both Node contract/tooling cases passed, including stale-output detection
and a compile-time rejection of publish without its idempotency header.
Focused real PostgreSQL runs use the existing `run_browser` environment/Compose
helpers with `--env-file NUL`, UUID-owned tmpfs projects and the existing guarded
`db_helpers` databases. The final focused API selector
`python -m pytest postgres\tests\test_quizzes.py --tb=short -x` passed all 12
cases; earlier focused schema/migration cases passed before a test-token failure.

Iteration found and fixed incomplete JWT claims in a new ownership-test fixture,
an ambiguous unscoped browser alert locator (now scoped to `main`), and the
retained clean-schema/client tests' pre-C02 inventory expectations. No runtime
authorization or privacy checks were relaxed. The first complete gate hit the
old 600-second launcher limit; the enlarged database suite took 613 seconds in
the next run. Only `npm test`/`test:db` now get a bounded 1,200-second allowance.
The subsequent full pytest run had 448 passes and the stale schema-inventory
assertion, since corrected. These iteration failures are superseded by the
final complete gate below, not counted as passing runs.

Final `npm run test:e2e -- --checks` exited 0 using owned project
`quezo-i02-b374d6649f9c`. PostgreSQL/Keycloak used disposable tmpfs storage and
guarded UUID-named databases; both containers and their network were removed.
No development volume, real account, trace, screenshot, HAR, storage-state or
assessment-payload artifact was created.

| Final command / stage | Result |
| --- | --- |
| `npm run typecheck` | Web/e2e TypeScript and strict mypy over 57 modules passed |
| `npm test` | 12 web tests and 449 Python tests passed; Python 569.52s |
| `npm run build` | Production Next build passed with all C02 author routes |
| `npm run api:check` | OpenAPI and generated TypeScript current |
| `npm run test:contracts` | 88 Python cases and 2 Node generation/client cases passed |
| `npm run test:db` | 166 real-database cases passed; 553.31s, including clean and actual prior-head migration paths |
| `npm run test:identity` | All 108 retained identity cases passed |
| `npm run test:identity:integration` | Actual Keycloak integration passed |
| `npm run test:web:production` | Built-web boundary/redaction case passed |
| Unfiltered Playwright suite | All 24 cases passed: 16 I02, 5 C01 and 3 C02, including genuine provider-token expiry |

Generation was separately repeated with `npm run api:generate` and checked with
`npm run api:check`; contract tests also verify that stale/missing output fails
without mutation and regeneration is deterministic. No hosted CI, Node 22 or
Python 3.14 execution result is claimed by this local C02 handoff.

**Contracts:** generated OpenAPI/TypeScript, not parallel handwritten DTOs:

| Operation | Input/output |
| --- | --- |
| `GET, POST /api/v1/quizzes` | Owned paginated `QuizSummary` list; create a `QuizComposition`, returning `Quiz` |
| `GET, PATCH /api/v1/quizzes/{quiz_id}` | Read own quiz; full composition replacement with `expectedRevision`, returning incremented `draftRevision` |
| `POST /api/v1/quizzes/{quiz_id}/drafts` | Explicit `DraftCommand` after publication, copying the last publication's exact selections and policies; advances draft revision without demoting published state |
| `POST /api/v1/quizzes/{quiz_id}/preview` | `DraftCommand` pins the expected saved draft; returns `QuizPreview` without keys, feedback, scoring definitions or persistence |
| `POST /api/v1/quizzes/{quiz_id}/publish` | `DraftCommand` plus UUID `Idempotency-Key`; 201 for new publication, 200 for exact replay, stable `PublishAcknowledgement` |
| `GET /api/v1/quizzes/{quiz_id}/versions/{version_id}` | Owning-author-only `PublishedQuiz`; foreign or mismatched nested IDs are concealed as 404 |

`QuizComposition` holds title, instructions, ordered `Selection` entries and
`QuizPolicy`. Each selection is an exact `(questionId, versionId)` plus nullable
integer `pointOverride`. Null means the selected revision's `defaultPoints`, not
the latest question default. Zero is an explicit override. Duplicate question
identities are rejected even with different version IDs. Empty/zero-total drafts
may be saved/previewed but cannot publish; publication requires 1-200 questions
and a positive total, at most 2,000,000.

`PublishedQuiz` contains its `id`, `quizId`, source `draftRevision`, title,
instructions, full independent `policy`, ordered `PublishedQuestion` entries,
`possiblePoints` and `publishedAt`. Each item contains a one-based `position`,
the actual C01 `QuestionVersion` (including stable option IDs/order and private
correct option/feedback), nullable override and frozen `effectivePoints`.
This is a **private author/scoring contract**, never a learner payload. The
learner-shaped preview uses an explicit allowlist: prompt, type, ordered options,
effective points, title/instructions and total. It never serializes the private
question model. Advanced randomization flags shuffle preview presentation only
in memory; default previews retain authored order.

Policy JSON stores independent duration, attempt limit, UTC availability start/end,
IANA time zone, question/option randomization flags and score/key/explanation
release fields, not a preset flag. Null duration/attempt limit means unlimited;
null availability means no corresponding bound. UI creation uses the approved
untimed/no-window/one-attempt/nonrandomized UTC defaults, with score-only or fully
withheld release. Advanced backend fixtures remain supported and validated.
The minimal editor refuses to rewrite a draft with advanced policies instead
of silently replacing them with demo defaults.

**Data:** `0006_quizzes` follows accepted `0005_questions`; applied revisions
are unchanged. Mutable `quizzes` owns a separately revisioned draft. Immutable
`quiz_versions` and ordered `quiz_questions` retain publication snapshots;
composite foreign keys enforce owner/question/version nesting and uniqueness.
Append-only publication command/event tables retain acknowledgements and trace
metadata without assessment content. Clean `base -> head`, actual
`0005_questions -> 0006_quizzes`, repeat-head, preserved content and
failed-upgrade rollback scenarios passed in the final common gate.
There is no cleanup/expiry of command acknowledgements.
Events retain both the command UUID and the separate server-generated HTTP
correlation UUID; exact replays do not create another event.

**Integration:** accepted C01 [PR #8](https://github.com/bc-bah/quezo/pull/8),
merge `e66f459c5a6b225bd3d1b4bbce6b5b87de67974c`, includes I02 `553a2c8` and
Phase 2 approval `49eb37b`; B.C.'s acceptance is recorded in this worktree.
C02 reuses `questions.service.get_question(connection, actor, question_id,
version_id)` inside its transaction and the original `QuestionVersion`/`Option`
schemas. Shared changes are limited to required router/navigation registration,
generated artifacts, test discovery/head assertions and documentation. I02's
real login fixtures and secret-safe reporter are retained.

All writes resolve live identity/roles inside `Database.transaction()`. Draft
edit, new-draft and publish lock the owned quiz row first. Publish authorizes
before checking the ledger, whose primary key is actor/quiz/operation/request ID;
SHA-256 fingerprints canonical actor/target/operation/key/payload. Exact replay
returns the original acknowledgement before current state/revision checks, even
after a later revision; a changed payload conflicts. A fresh command must match
the draft revision and allowed state. Publication, items, acknowledgement, trace
and pointer update commit atomically before success. No automatic database
retries are added; callers explicitly retry an uncertain publish with its same
key/payload. The UI retains that key for retries while the command panel remains
mounted; after reload, inspect persisted quiz/publication state.

**Known gaps:** no unresolved criterion within the assigned C02 slice.
Assignments/start/scoring/grades, complete
close/archive/settings management and timed learner UX are intentionally absent;
unsupported commands return explicit errors, not fabricated success.

**Successor handoff (D01):** C02 acceptance is recorded above; record/include
the actual integration commit and accepted handoff in the consumer checkout
before execution. Pin the
publication UUID, never the mutable quiz draft/current pointer. Use frozen
effective points, C01 option IDs/order and independent policy to build the
attempt's private scoring snapshot and separate learner projection. Keep
author-only `PublishedQuiz` out of learner HTML/JSON. Distribution must add
its own assignment/allowance/start admission and lock rules; C02 does not supply
placeholder implementations for them. No D01 execution is authorized by this
handoff alone.

## C01 versioned objective questions

### Acceptance and integration: 21 October 2026

B.C. explicitly confirmed C01 acceptance/integration on 21 October 2026.
[PR #8](https://github.com/bc-bah/quezo/pull/8) is merged as
`e66f459c5a6b225bd3d1b4bbce6b5b87de67974c`, including implementation `eb9d62d`
and deterministic OpenAPI correction `1f2cd53`. The accepted evidence is the
local handoff below and passing [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39596126267)
at `1f2cd53848804c6ea47cf8595ffb5907d4f98bd4`: browser, Python 3.12/3.14 and
Node 22/24 jobs. This documentation update does not claim a new application
test run or an independent code review.

The [backlog](implementation/BACKLOG.md) now records C01 as `done`. Acceptance
covers the assigned question slice and initial AT-03/04 evidence, not C02
publication or complete C03 management. C02's producer gate is satisfied when
its checkout includes this acceptance record and the merge above, with migration
`0005_questions`, I02 foundation `553a2c8` and Phase 2 approval `49eb37b`.
The exact-version consumer contract below is accepted unchanged; shared writes
remain B.C.-serialized. No successor dispatch or later lifecycle acceptance is
implied.

### Review handoff: 21 October 2026

**Work item:** C01, Versioned objective questions.

**State at handoff:** ready for B.C.'s review; superseded by the acceptance
record above. The final unfiltered
`npm run test:e2e -- --checks` exited 0, including all 21 browser cases and owned
service/network cleanup. B.C. retains acceptance and tracker updates.

**Changes:** `postgres/src/quezo_api/modules/questions/` owns strict DTOs,
authorization-scoped reads, bank writes and atomic revision-producing edits.
`0005_questions` introduces only bank/question/version storage. The `/author`
pages and server actions use the existing server-only `BackendFacade.client`;
they never query assessment storage or expose a bearer token to JavaScript.
The author home links to bank management. Generated OpenAPI/TypeScript, focused
Python tests, existing browser discovery/fixtures, database script and runbooks
are updated. No scoring, quiz, assignment, attempt or grading surfaces were added.

**Requirement coverage:** AUTH-01 and IAM-02; SRS sections 6-8; QUAL-02/04;
FR-003/011/012/061, the initial create/read/edit portion of FR-010, and immutable
identity/version foundations for FR-014/018;
NFR-007/008/010. This is not complete AUTH-01/AT-03 management or AT-04 publication
acceptance: the deferred cases are listed below.

**Acceptance:** `test_question_schemas.py`, `test_questions.py`,
`test_question_migrations.py` and `tests/e2e/questions.spec.ts` cover:

| Acceptance | Delivered initial scope |
| --- | --- |
| AT-03 | Both objective types through real signed-in browser, server facade, API and PostgreSQL; bank create/read/rename; required text and all content bounds; literal text rendering; strict/extra-field rejection; stable bounded pagination; foreign-owner list/direct/nested read and write denial; learner/administrator non-inheritance; live role revocation and visible outage errors |
| AT-04 | Stable question identity, distinct immutable version IDs, preserved option IDs/content/key/points/feedback after editing, explicit exact-version selection, old-version reread after refresh, stale/concurrent edit conflict, database mutation denial and atomic failure rollback |
| QUAL-02/04 | Existing identity/CSRF suite retained; safe field errors and log redaction; no key-bearing learner response; deterministic schemas/client; clean and actual prior-head migration/rollback; restricted web/runtime privileges |

Backend identity tests use the existing signed-token/JWKS controlled peer and
real database; the browser cases additionally use actual Keycloak/native login.
The existing combined-role synthetic account is the second author, not a new
provisioning/auth path. Browser artifacts remain disabled and application-log
sentinels cover assessment content as well as credentials.

**Checks:** final local execution on Windows x64, Node 24.20.0, npm 11.19.0,
uv 0.12.17, Python 3.12.10, Docker Engine 29.7.2, PostgreSQL 17.11 and Chromium
156.0.8078.4 (Playwright 1.64.1). Next.js is 16.4.2; identity uses the existing
local Keycloak fixture. No hosted or other-version matrix result is claimed.

The successful unfiltered `npm run test:e2e -- --checks` used owned project
`quezo-i02-eb9af10d8ef2`, with PostgreSQL/Keycloak/web/API loopback ports
53235/53236/53237/53238. The launcher generated distinct synthetic credentials,
guarded disposable databases and the realm; it removed its containers/network
and browser temporary results on completion, without touching development data.

| Exact command (repository root) | Final outcome |
| --- | --- |
| `npm run api:generate` | Regenerated authoritative OpenAPI and TypeScript client |
| `npm run typecheck` | Web, browser TypeScript and strict mypy passed (48 Python files) |
| `npm test` | 12 web tests and 365 Python cases passed, no skips |
| `npm run build` | Production Next build passed |
| `npm run api:check` | Both generated artifacts current |
| `npm run test:contracts` | 87 Python cases and 2 Node contract/tooling cases passed |
| `npm run test:db` | 138 cases passed, including clean/prior-head migrations, constraints, rollback, immutable versions and real-database authorization |
| `npm run test:identity` | 108 retained identity cases passed |
| `npm run test:identity:integration` | Actual Keycloak integration passed |
| `npm run test:web:production` | Built-web HTTP/session boundary passed |
| `npm run test:e2e -- --checks` | All above checks plus all 16 retained I02 and 5 C01 browser cases passed; exit 0 |
| `uv run --directory postgres --locked alembic heads` | Exactly `0005_questions` |
| `uv run --directory postgres --locked alembic history` | One linear chain; `0004_identity -> 0005_questions` |
| `git diff --check` | Passed |

Initial browser runs found that nested textarea labels included prefilled text
in label lookup, and browser form restoration retained stale text after a
conflict/reload. Explicit textarea labels and `autocomplete="off"` corrected
those paths; tests prove current persisted content appears on reload. Error
assertions now target the main region rather than also matching Next's route
announcer. The safe reporter recognizes C01 source locations without raw
error/call logs. Focused `npm run test:e2e -- --grep C01` and
`npm run test:e2e -- --grep "C01 stale"` drove these corrections.
One subsequent full run stopped at a native Windows/npm startup failure
(exit 3221226505) before `test:web:production`; its cleanup completed. The
unchanged complete command was rerun successfully as recorded above; no check,
assertion or runtime authority was bypassed.

**CI portability follow-up:** the hosted Python 3.14 contract check exposed a
standard-library HTTP 422 description change from `Unprocessable Entity` to
`Unprocessable Content`. Question routes now explicitly retain the committed
description. The reproducibility test exercises both standard-library phrases
on every Python version, comparing the complete schema with the committed
artifact. The failure was reproduced before the fix. Targeted local checks on
Python 3.12.10 and 3.14.7 each passed all 88 contract cases, strict mypy and
`npm run api:check`; both Node contract/tooling cases also passed. Regeneration
left OpenAPI and TypeScript artifacts unchanged. No runtime response, database
or browser behavior changed; the full browser/database gate was not rerun for
this metadata-only patch. Hosted CI must rerun after the patch is pushed.

**Contracts:** all paths below are relative to `/api/v1`. Every operation
requires a currently active mapped author. Administrator alone is denied (403);
another owner's resources are concealed as 404, including bank filters, cursors
and nested version IDs. Protected success/error responses are private/no-store.
`get_identity` verifies the token; the function-scoped transaction dependency
calls `resolve_actor` and `require_role` inside the same transaction as the
operation. Dependency teardown commits before sending success, including
deferred constraints. There is no authorization snapshot in a browser session.

| HTTP operation | Input / output |
| --- | --- |
| `GET /question-banks` | `pageSize`, `cursor`; `Page[Bank]` |
| `POST /question-banks` | `{name}`; 201 `Bank` |
| `GET /question-banks/{bank_id}` | Own bank; `Bank` |
| `PATCH /question-banks/{bank_id}` | `{name}`; updated `Bank` |
| `GET /questions` | `pageSize`, `cursor`, optional `bankId`; current `Page[QuestionSummary]` |
| `POST /questions` | `QuestionCreate`; 201 `QuestionVersion` |
| `GET /questions/{question_id}` | Current `QuestionVersion` |
| `PATCH /questions/{question_id}` | Full `QuestionEdit`, including `expectedRevision`; new `QuestionVersion` |
| `GET /questions/{question_id}/versions` | `pageSize`, `cursor`; retained `Page[QuestionSummary]` |
| `GET /questions/{question_id}/versions/{version_id}` | Exact owned `QuestionVersion`, never replaced by current |

`Bank` is `{id, name}`. `QuestionCreate` requires `bankId` plus every content
field below; `QuestionEdit` requires `expectedRevision` plus every content field
and does not accept bank/owner IDs. Despite PATCH, this is a complete new content
revision, not a partial field merge. Missing, extra and snake_case write fields
are rejected recursively. No server timestamp, version ID or owner is writable.

| Validated content field | Contract |
| --- | --- |
| `questionType` | Exactly `mcq` or `true_false` |
| `prompt` | 1-4,000 Unicode characters; not whitespace-only |
| `options` | Ordered list of 2-10 `{id, text}` objects for MCQ; exactly two for true/false |
| `options[].id` | UUID supplied by the author client; unique after UUID parsing within the revision; returned canonically |
| `options[].text` | 1-1,000 characters, not whitespace-only; true/false requires exactly `True` and `False`, case-sensitive, either order |
| `correctOptionId` | One UUID matching exactly one option ID; no additional per-option correct flags |
| `defaultPoints` | Strict integer 0-10,000, inclusive; no strings, booleans or fractional numbers |
| `feedback` | Required string of 0-4,000 characters; empty means no explanation supplied |

Bank names are 1-100 characters and not whitespace-only. Required text is
checked for trimmed emptiness but stored verbatim. All text must be valid Unicode;
C0 controls other than tab/CR/LF are rejected. Plain text means literal storage
and escaped text rendering, not an HTML/Markdown parser: angle brackets are
allowed as text, not interpreted. Bounds are checked independently of the UI.

`QuestionVersion` adds `questionId`, `bankId`, `versionId`, positive `revision`
and RFC 3339 UTC `createdAt` to the content fields. `questionId` is the stable
reusable question UUID. `versionId` is a new server UUID for every successful
save; revisions start at 1. Existing option IDs are retained when editing a
choice; added choices get new UUIDs, and changing type in the UI explicitly
replaces the choices. Old versions preserve their original option array/key.
`correctOptionId` references `options[].id` in that exact version, not a position,
question ID or boolean. No returned key-bearing DTO is a learner representation.

`QuestionSummary` contains `questionId`, `bankId`, `versionId`, `revision`,
`questionType`, `promptExcerpt` (first 120 characters) and `defaultPoints`.
Summaries omit key/options/feedback and keep maximum-sized pages below the
existing facade body limit. Lists default to 25, allow 1-100, and always return
`nextCursor` (null at end). Bank/question lists order by UUID ascending and use
the last bank/question UUID as cursor. History orders by revision and version
UUID and uses the last version UUID. Cursors must be canonical UUIDs and belong
to the authorized list scope; foreign/nested mismatches return 404, malformed
cursors 422. Authorization is applied before pagination.

Question edits lock the owned question row and compare `expectedRevision`
(strict integer 1-2,147,483,647). A stale edit returns 409
`DRAFT_REVISION_CONFLICT`; the UI retains unsaved input and asks for a reload.
No automatic retry, command acknowledgement ledger or C02 publication semantics
are added. A connection failure after a create/save is an unknown outcome:
the form tells the author to check persisted state before retrying.

**Data:** new single head `0005_questions`, parent `0004_identity`.
`question_banks`, `questions`, `question_versions` have relational ownership,
unique revisions, content checks, immutable version triggers/privileges and a
deferred current-version foreign key. Applied migrations are unchanged.
Unapplied upgrade failures roll back DDL and ledger; after an applied migration,
use reviewed forward corrections rather than a destructive downgrade.
See [migration details](../postgres/migrations/README.md#c01-question-storage).

**Integration:** accepted I02 foundation
`553a2c8b77a770667f4cef6825f57c3b55f477ed`, plus approval/tracker baseline
`4613fdc` (including `0514cfb` and `49eb37b`). C01 used its assigned initial
shared-file window. S01 surfaces are untouched. No commit, PR, successor
dispatch, tracker completion or acceptance is implied.

**Known gaps:** no unresolved criterion within the assigned C01 slice.
C03 owns full search/category/tag/move/archive controls; archive
markers are reserved storage only and unsupported commands remain absent.
C02 owns quiz reuse/composition/publication; no publication/attempt/grade
preservation claim is possible yet. No Q02/WCAG, Node 22/Python 3.14 local matrix,
hosted CI, deployment or real-data/pilot acceptance is claimed by this run.

**Successor handoff (C02):** acceptance/integration is recorded above; include
merge `e66f459`, this acceptance record and migration `0005_questions`.
Consume the generated schemas, not a copied
DTO. Persist explicit `(questionId, versionId)` selections; never resolve
"current" while publishing a prior selection. Within the caller's
`Database.transaction`, resolve the live actor, then call
`questions.service.get_question(connection, actor, question_id, version_id)`
to verify ownership/nesting and obtain the exact `QuestionVersion`. Supplying
no `version_id` deliberately requests current and is unsuitable for a pinned
selection. Recheck every selection inside publication's transaction.
Keep authored option order/UUIDs; use `defaultPoints` unless an explicit validated
quiz override exists. Do not confuse revision number with a version UUID, use
the bank ID as question identity, expose `correctOptionId`/feedback to learners,
or mutate a version. C02 adds its own FKs/duplicate-question checks, positive
total, snapshot/projection, draft CAS and publish replay semantics; none are
scaffolded here.

## F02 HTTP contracts and generated client

Server Pydantic models remain authoritative. `postgres/src/quezo_api/schemas.py`
defines `ApiModel`, `PublicId` (UUID), `NonNegativeInteger` (strict, no boolean,
string or fractional coercion), `UtcTimestamp`, `Actor`, `PaginationParams` and
`Page[T]`. Wire names are camelCase; Python attributes are snake_case. Use
`model_validate` with wire aliases when constructing DTOs. Unknown fields and
snake_case substitutes are rejected, including nested write fields. Timestamps
require an explicit UTC offset and serialize as RFC 3339 UTC strings; naive,
non-UTC and epoch inputs are rejected. Feature owners add their approved domain
fields/bounds/enums when implementing the corresponding routes, not here.

**Actor agreement:** B.C. explicitly approved the minimal F03/I01 DTO during
F02 dispatch on 20 October 2026:

```json
{
  "userId": "b852a646-70ed-4ab9-aae4-d7fc2e0ca313",
  "roles": ["author", "learner"],
  "status": "active"
}
```

`userId` is the application UUID, not an identity-provider subject.
`Role` contains `administrator`, `author`, `learner`; roles may be combined or
empty. `AccessStatus` contains `active`, `disabled`. No token, email, issuer,
subject, session secret, permission bitmap or storage field is included.
This is a descriptive DTO, **not** authentication or authorization. I01 must
resolve current application roles/status and enforce operation/ownership checks;
administrator alone never implies author or learner access. F03 must keep
session secrets separately on the server and must not turn an actor fixture or
dependency outage into an authenticated session. DEC-06/07 choices are now
approved in the [second-wave record](SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01).
F02 did not implement `/api/v1/me`; the integrated I01 package now provides it.

**Pagination:** use `Annotated[PaginationParams, Query()]` for collection query
inputs: `pageSize` defaults to 25 and accepts 1-100, `cursor` defaults to null.
Only decimal integer query strings are parsed; fractions, booleans, negatives,
null sizes and extra fields fail validation. `Page[T]` responses contain
`items` and a required `nextCursor`, explicitly null when exhausted. A collection producer owns cursor encoding/validation and server-side filters;
it must use stable ordering with a unique-ID tiebreaker and apply authorization
before pagination. C01 implements its own scoped UUID cursors and concrete
bank/question page schemas below; no generic persistence layer is introduced.

**Errors:** `postgres/src/quezo_api/errors.py` installs consistent handlers on the
application factory without changing F01 lifespan. Responses contain `code`,
fixed safe `message`, `requestId`, and optional typed `details`. Every HTTP
response has a newly generated UUID `X-Request-ID`; inbound IDs are never trusted
or reflected. The same ID appears in error bodies and structured error logs.
It is unrelated to a command `requestId` or `Idempotency-Key`.

Validation details are `{"fields":[{"path":["body","actor","userId"],"reason":"invalid_value"}]}`.
Reasons are `required`, `unknown_field` or `invalid_value`, never Pydantic's raw
message/input/context. Only schema-owned field names and array indexes may be
reflected; unknown keys and dynamic path segments become `[field]`. Neither
raw values nor validator/exception messages are logged. Errors use
`Cache-Control: private, no-store`. Future protected success responses must
also use private/no-store caching in their owning route/facade.

Use `ApiError(ErrorCode.<CODE>)` for the SRS's fixed error codes. For rate limits,
the owning feature may supply positive integer `retry_after` seconds; F02 does
not select a rate/retry policy or automatically retry requests. Framework 404
and 405 errors are sanitized too (`NOT_FOUND`, `METHOD_NOT_ALLOWED`); malformed
body decoding may return 400 with `VALIDATION_FAILED`. Arbitrary HTTP exception
details/headers are discarded; only validated Allow and numeric Retry-After
headers survive. Unsupported HTTP exception statuses fail as `INTERNAL_ERROR`.
Psycopg operational/pool failures become 503 `DEPENDENCY_UNAVAILABLE`, response
validation and unexpected failures become 500 `INTERNAL_ERROR`.
Future conflict details must be explicit, disclosure-reviewed Pydantic schemas,
not arbitrary dictionaries or exception text.

The HTTP boundary enforces **256 KiB of actual received body bytes**, including
chunked requests and misleading Content-Length. Exactly 256 KiB is allowed;
larger bodies receive 413 `PAYLOAD_TOO_LARGE` before route execution. It buffers
only up to this limit, does not contain authorization, and does not change
lifespan or websocket handling. Unexpected exceptions are consumed before the
server can log their raw text. A failure after response headers cannot replace
the already-started response: it logs only the correlated safe error and aborts
with a fixed, sanitized exception. No streaming business endpoint is introduced.

### Export, generation and drift checks

The approved tools are pinned to `openapi-typescript` 7.13.0 (root development
dependency) and `openapi-fetch` 0.17.0 (web runtime dependency). npm regenerates
the shared lock. No new Python dependency is needed.

From the repository root:

```powershell
npm run api:export
npm run api:generate
npm run api:check
npm run test:contracts
```

`api:export` runs
`uv run --directory postgres --locked python scripts/export_openapi.py` and
writes sorted, LF-terminated `postgres/openapi.json` directly from `create_app()`
without starting lifespan, reading database credentials or connecting to a
dependency. `api:generate` exports first, then runs
`node postgres/scripts/generate-client.mjs`, producing
`frontend/quezo/src/lib/api/schema.d.ts`. Do not hand-edit either generated file.
I01 adds `GET /api/v1/me` alongside `GET /health/live`; Actor is now that route's
response contract. PaginationParams remains an unattached schema contract, not
a promise of an implemented list endpoint.

`api:check` executes these read-only checks and fails for missing/stale output:

```powershell
npm run api:export -- --check
node postgres/scripts/generate-client.mjs --check
```

After a server contract change or producer merge, regenerate both artifacts,
review the diff, and run the checks before consumer work. Generated defaults
preserve optional request fields; the health response still guarantees exactly
`{"status":"ok","scope":"process-only"}`.

`frontend/quezo/src/lib/api/client.ts` exports `createApiClient(baseUrl, fetch?)`.
Consumers import `paths`/`components` from `./schema` rather than copy DTOs.
The client requires an explicit backend base URL, supports an injected fetch,
returns typed `data` or `error` with the original Response, and propagates
network failures. It adds no authentication, retry, default host or fake success.
F03 should use it inside the server-side facade and handle backend errors and
network failures separately, preserving the safe code/message/requestId.

`test:contracts` runs `test_contract_schemas.py`, `test_http_contract.py` and
Node's built-in runner for `postgres/scripts/test_contract_tools.mjs`.
HTTP fixtures add routes only to test-owned app instances and intentionally
omit lifespan; F01's real-database `test_app.py` remains the startup/liveness
evidence. Tooling tests create disposable copies, prove missing/stale checks
fail without overwriting output, regenerate identical artifacts, compile
positive/negative typed-client consumers, and exercise success/error/network
behavior with synthetic fetches. Web CI runs generation checks and these tests
on Node 22/24; the original Python 3.12/3.14 PostgreSQL jobs remain intact.

| Requirement | F02 evidence | Limit |
| --- | --- | --- |
| IAM-02 / FR-001,002,003,061 contract conventions | Approved minimal actor; role/status/UUID and extra-field fixtures; generated actor type | No token validation, current-role lookup or authorization enforcement; **AT-01 not established** |
| SRS sections 6-7; F02 schemas/errors/health criteria | CamelCase/strict integer/UUID/enum/UTC/pagination tests; invalid/unknown fields, safe dependency/internal/response errors; correlation, byte-limit boundaries and unchanged liveness | No business routes, scoring, cursor persistence or conflict implementation |
| QUAL-02 / NFR-007,008 | No raw payload/exception/unknown-key reflection; sanitized logs and disabled raw access logs | Role/ownership/CSRF/token, real-data privacy and retention acceptance remain later work |
| QUAL-04 / NFR-010; F02 generation criteria | Contract fixtures, deterministic export, negative drift tests, typed client checks, root type/build checks and preserved F01 suite | No assessment transitions, grading or disclosure acceptance |
| AT-15 partial support / QUAL-06 structured errors | Correlated 500/503 errors, explicit synthetic dependency failures and F01 process-only liveness | No deployment/readiness/metrics/recovery evidence; **full AT-15 not established** |

F03/I01 can rely on the agreed actor and generated types: B.C. has accepted
F01/F02 integration and approved their second-wave decisions. S01 can reuse UUID and strict
nonnegative integer conventions without implementing HTTP/authentication; its
domain inputs, scoring enums and AT-11 evidence remain S01's responsibility.

### F02 local verification: 20 October 2026

These are local results, not hosted CI or B.C.'s acceptance. Environment:
Windows x64, Node 24.20.0, npm 11.19.0, uv 0.12.17, Python 3.12.10 and 3.14.7,
Docker Engine 29.7.2, PostgreSQL 17.11 (Debian x86_64). Node 22 and hosted Linux
CI were not executed locally for F02; the configured CI matrices remain required
review evidence.

The isolated test dependency was started with:

```powershell
docker compose -p quezo-f02-9c413787 --profile test up -d --wait postgres-test
```

That shell set `QUEZO_TEST_PORT=55442` and distinct synthetic
`QUEZO_TEST_ADMIN_PASSWORD`, `QUEZO_TEST_MIGRATION_PASSWORD` and
`QUEZO_TEST_RUNTIME_PASSWORD` values. Unused `POSTGRES_PASSWORD` and
`KEYCLOAK_ADMIN_PASSWORD` placeholders satisfied Compose interpolation; neither
the development database nor identity service was started. Test shells exported
`QUEZO_TEST_ADMIN_URL` for `quezo_test_admin` at
`127.0.0.1:55442/quezo_test_control` and the matching migration/runtime passwords.
The Python 3.14 runs used a separate temporary session-artifact virtualenv via
`UV_PROJECT_ENVIRONMENT`; the default `postgres/.venv` stayed on Python 3.12.

| Exact command (repository root) | Final outcome |
| --- | --- |
| `npm install --ignore-scripts --no-audit --no-fund` | Installed pinned contract tools and regenerated `package-lock.json` through npm |
| `npm run api:export` (also run by generation) | Exported the implemented API without database startup |
| `npm run api:generate` | Regenerated OpenAPI and TypeScript reproducibly |
| `npm run api:check` | Both exported OpenAPI and generated TypeScript current |
| `npm run api:export -- --check` | Read-only server contract check passed |
| `node postgres/scripts/generate-client.mjs --check` | Read-only generated-type check passed |
| `npm run test:contracts` | 87 Python cases and 2 Node tooling/client tests passed, no skips |
| `uv run --directory postgres --locked pytest tests/test_contract_schemas.py tests/test_http_contract.py` | 87 passed (also invoked by `test:contracts`) |
| `npm run typecheck` | Web route/TypeScript checks and strict mypy passed; 19 Python source files |
| `npm test` | 138 passed, no skips, including all integrated F01 tests |
| `npm run test:db` | Original 41 database/migration/lifespan/isolation cases passed, no skips |
| `npm run build` | Next.js production build passed; product UI unchanged |
| `uv run --directory postgres --locked --python 3.14 mypy` | Passed, 19 source files |
| `uv run --directory postgres --locked --python 3.14 pytest tests/test_contract_schemas.py tests/test_http_contract.py` | 87 passed |
| `uv run --directory postgres --locked --python 3.14 python scripts/export_openapi.py --check` | Export identical across Python 3.12/3.14 |
| `uv run --directory postgres --locked --python 3.14 pytest` | Final full suite: 138 passed, no skips |

Initial checks caught alias-constructor typing, framework exception typing and
pagination schema-bound metadata issues; these were corrected before the final
results above. Negative drift tests deliberately use missing/modified artifacts
in temporary copies and assert exit status 1, then regenerate identical output.
They do not modify the checked-in generated artifacts. No check prerequisite
remained unavailable for the final local commands.

The original F01 migrations, rollback, role restrictions, shutdown/outage and
isolation tests remain unchanged. No new migration or data recovery procedure
is introduced. After testing, only the synthetic control database remained;
the F02 disposable test service and its dedicated network were removed:

```powershell
docker compose -p quezo-f02-9c413787 --profile test rm -s -f postgres-test
docker network rm quezo-f02-9c413787_default
```

**Original handoff boundary:** these local results were returned for B.C.'s
review, not declared acceptance by the implementing agent. F02 has since merged
via [PR #4](https://github.com/bc-bah/quezo/pull/4) and B.C. confirmed completion;
the backlog now records `done`. This does not authorize external provisioning,
deployment or real-data use.

## Local database and optional identity dependency

Copy the example at the repository root:

```powershell
Copy-Item .env.example .env
```

Use `cp .env.example .env` in Bash. Fill `POSTGRES_PASSWORD`,
`QUEZO_MIGRATION_PASSWORD`, `QUEZO_RUNTIME_PASSWORD`, `QUEZO_WEB_PASSWORD`
and `KEYCLOAK_ADMIN_PASSWORD`
with distinct local-only credentials. Compose validates interpolations even for
inactive profiles, so the bootstrap and Keycloak passwords are required even
when only PostgreSQL is started. Test role passwords may remain empty unless
starting the test service; its initialization rejects missing/equal role passwords.

```powershell
docker compose config --quiet
docker compose up -d postgres
docker compose --profile identity up -d
docker compose ps
```

`postgres` listens on loopback port 5432 by default. Optional `keycloak` listens
on loopback port 8080; its admin console is at `http://localhost:8080/admin`.
The database has a readiness check; wait for Keycloak's console to respond before
using it. The admin credentials bootstrap a fresh volume only; changing `.env`
does not rotate credentials already stored in either persisted volume.
On a fresh PostgreSQL volume, `postgres/bootstrap/roles.sql` creates
`quezo_migrator`, `quezo_runtime` and `quezo_web` and restricts database access. Initialization
failure must be resolved before using the service; `pg_isready` alone does not
prove roles or migrations are installed.

For an existing **local scaffold** volume with no F01 roles, review its contents
first, recreate the container to pick up the new password environment, then run
the explicit bootstrap once (substitute your configured bootstrap user/database):

```powershell
Get-Content postgres\bootstrap\roles.sql -Raw | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U quezo -d quezo
```

In Bash, use input redirection instead of `Get-Content`. The SQL is transactional
and fails rather than reusing/replacing existing roles. Do not delete an existing
volume to make setup pass. Existing roles or shared/non-scaffold databases need
B.C.'s coordination; this runbook does not authorize their modification.

| Variable | Purpose |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER` | Local database/bootstrap owner (both default to `quezo`) |
| `POSTGRES_PASSWORD` | Required local database password |
| `POSTGRES_PORT` | Host port; default 5432 |
| `QUEZO_MIGRATION_PASSWORD` | Bootstrap-only password for restricted schema owner `quezo_migrator` |
| `QUEZO_RUNTIME_PASSWORD` | Bootstrap-only password for restricted data identity `quezo_runtime` |
| `QUEZO_WEB_PASSWORD` | Bootstrap-only password for restricted session identity `quezo_web` |
| `KEYCLOAK_ADMIN` | Local bootstrap administrator name |
| `KEYCLOAK_ADMIN_PASSWORD` | Required local bootstrap password |
| `KEYCLOAK_PORT` | Host port; default 8080 |

The root `.env` is for Compose only; neither application shell loads it.
Export `QUEZO_MIGRATION_URL` to the migration shell and `QUEZO_DATABASE_URL` to
the application shell explicitly. Use PostgreSQL URLs with percent-encoded
passwords and explicit host, database and the appropriate fixed role name:

```text
QUEZO_MIGRATION_URL=postgresql://quezo_migrator:<encoded-password>@127.0.0.1:5432/quezo
QUEZO_DATABASE_URL=postgresql://quezo_runtime:<encoded-password>@127.0.0.1:5432/quezo
```

In PowerShell, assign `$env:QUEZO_MIGRATION_URL` / `$env:QUEZO_DATABASE_URL`;
in Bash use `export`. Do not place credentials in command arguments or Git.
In the migration shell, run:

```powershell
uv run --directory postgres --locked alembic upgrade head
```

Full revision rules and recovery implications are in
[the migration runbook](../postgres/migrations/README.md). FastAPI does not
run migrations. Runtime never receives the migration/bootstrap credential.
The launch scripts explicitly select a Selector event loop because Psycopg async
does not support Windows' Proactor loop; custom Uvicorn launchers must retain
`--loop quezo_api.database:database_loop_factory`, including without reload.
Database/OIDC secrets must never use `NEXT_PUBLIC_` variables. Do not enable a fake login or
`AUTH_DISABLED` mode.

Compose uses project-scoped named volumes and no fixed container names. Override
host ports for simultaneous worktrees. Stop optional containers without deleting
their data:

```powershell
docker compose --profile identity down
```

Do not remove volumes as routine cleanup; they persist database and identity data.
Never use these bootstrap database credentials or Keycloak `start-dev` settings
in a shared or production environment.

## Connection and transaction interface

`quezo_api.database.DatabaseSettings.from_env()` validates the runtime URL and
bounded pool settings; missing/invalid configuration fails explicitly without
printing the URL. Settings are read at lifespan startup, so importing the factory
or generating OpenAPI does not connect to PostgreSQL.

| Variable | Default | Accepted range |
| --- | --- | --- |
| `QUEZO_DATABASE_URL` | Required | PostgreSQL URL; explicit host/database; `quezo_runtime` |
| `QUEZO_DB_POOL_MIN` | 1 | 1-20, not above max |
| `QUEZO_DB_POOL_MAX` | 5 | 1-20 per process |
| `QUEZO_DB_POOL_TIMEOUT` | 5 seconds | Greater than 0, at most 60 |
| `QUEZO_DB_STARTUP_TIMEOUT` | 10 seconds | Greater than 0, at most 60 |
| `QUEZO_DB_STATEMENT_TIMEOUT_MS` | 30000 | 1-300000 |

Each process owns one `Database`, opened and closed by FastAPI lifespan.
Connection attempts have a 5-second timeout; shutdown waits at most 5 seconds
for pool workers. Failed startup also closes the pool (allow startup timeout
plus up to 5 seconds for cleanup). Waiting borrowers are capped at twice the
pool maximum. Multiply the pool maximum by worker/process count when budgeting
PostgreSQL connections; defaults are local limits, not approved performance gates.
Connections use UTC, a `quezo,pg_catalog` search path, a 5-second lock timeout
and a 30-second idle-in-transaction timeout.

Routes obtain the typed handle using `Depends(get_database)` from
`quezo_api.database`; it rejects calls outside the running lifespan. Modules
receive that handle directly:

```python
async with database.transaction() as connection:
    cursor = await connection.execute("SELECT %s::integer", (42,))
    row = await cursor.fetchone()
# Success/acknowledgement may be returned only after this block commits.
```

The yielded value is a Psycopg `AsyncConnection[tuple[object, ...]]`.
Successful exit commits; SQL errors, Python exceptions and cancellation roll
back before the connection returns to the pool. Do not manually commit/rollback,
retain a leased connection, change session settings or start untracked tasks
inside the block. Pass the same connection to collaborating functions in one
atomic operation; opening another `database.transaction()` leases a separate
connection, not a nested transaction. Domain SQL, locks, constraints and retry
policy belong to later packages; there is no generic repository or retry wrapper.

Database failures propagate; there is no memory fallback. Startup requires
connectivity, but `/health/live` remains exactly
`{"status":"ok","scope":"process-only"}` and makes no database query. It still
answers after a subsequent database outage. No `/health/ready` is introduced;
liveness does not assert schema, identity or deployment readiness.

## Isolated real PostgreSQL tests

Never point tests at the application database. Use the separate `postgres-test`
Compose service, a loopback-only PostgreSQL 17 instance with disposable tmpfs
data, separate credentials and no development volume. Populate the four
`QUEZO_TEST_*_PASSWORD` values in `.env`, using distinct synthetic credentials.
`QUEZO_TEST_PORT` defaults to 55432; choose a free port/project for each worktree.

```powershell
docker compose --profile test up -d --wait postgres-test
```

Export these variables to the test shell (the passwords must match the service):

```text
QUEZO_TEST_ADMIN_URL=postgresql://quezo_test_admin:<encoded-password>@127.0.0.1:55432/quezo_test_control
QUEZO_TEST_MIGRATION_PASSWORD=<test-migration-password>
QUEZO_TEST_RUNTIME_PASSWORD=<test-runtime-password>
QUEZO_TEST_WEB_PASSWORD=<test-web-password>
```

Run from the root:

```powershell
uv run --directory postgres --locked mypy
uv run --directory postgres --locked pytest
npm run test:db
```

`postgres/tests/db_helpers.py` and `conftest.py` provide `empty_database`
(unmigrated) and `database` (head) function-scoped fixtures. Every fixture creates
a fresh UUID-named `quezo_test_<32 hex digits>` database; synthetic test tables
are local to that database. The helpers reject non-loopback hosts, missing ports,
other database/user names, service/hostaddr overrides and extra URL parameters
**before connecting**. Ambient `PGHOSTADDR`, `PGSERVICE` and `PGSERVICEFILE`
overrides must also be unset, so libpq cannot redirect a safe-looking URL.
The helpers then require the server-side control database marker
installed only by `postgres/tests/bootstrap.sql`. Local hostname checks are an
accident guard, not protection from a malicious local database administrator.

Cleanup uses the same admin connection and checks the control marker, exact
generated name, expected owner and per-database ownership marker before dropping
that database only. It never drops the control database, a caller-supplied
application database or an unmarked database. It does not use `DROP ... FORCE`:
leaked connections fail cleanup. After an interrupted process, inspect orphaned
test databases or remove only the disposable test service:

```powershell
docker compose --profile test rm -s -f postgres-test
```

This discards that service's synthetic tmpfs contents, not development volumes.
Do not use broad volume deletion. CI uses a separate PostgreSQL 17 service for
each Python matrix job, runs the same bootstrap and tests, and discards the
service with the job. Hosted CI results are separate from local evidence.

Foundation evidence maps as follows:

| Requirement | Automated evidence | Limit |
| --- | --- | --- |
| QUAL-01 / NFR-004,005 | `test_database.py`: committed data survives pool recreation; failed/cancelled transactions roll back against real PostgreSQL | No response/grade lifecycle, lost HTTP acknowledgement or recovery guarantee |
| QUAL-04 / NFR-010 | `test_migrations.py`, `test_database_isolation.py`, existing HTTP checks and strict mypy | No domain transition, scoring or disclosure acceptance |
| QUAL-05 / NFR-011 | uv lock, environment validation, ordered/serialized migrations, CI database service and lifespan tests | No application images or deployment/readiness acceptance |
| AT-10, AT-15 | Foundation rollback, migration, outage and process-only liveness scenarios | **Partial support only**, not end-to-end acceptance |

### F01 local verification: 20 October 2026

These are local execution results, not hosted CI, B.C.'s acceptance or an
integration decision. Windows x64 used uv 0.12.17, Python 3.12.10 / 3.14.7,
Node 24.20.0, npm 11.19.0 and Docker Engine 29.7.2. PostgreSQL was 17.11
(Debian, x86_64), started only for synthetic tests. The test shell exported
`QUEZO_TEST_ADMIN_URL` for `quezo_test_admin` at
`127.0.0.1:55439/quezo_test_control`, plus distinct migration/runtime test
passwords. The Python 3.14 run used a separate session-artifact virtualenv
through `UV_PROJECT_ENVIRONMENT`; no development database was used.

| Exact command | Result |
| --- | --- |
| `uv run --directory postgres --locked mypy` | Passed, 13 source files including migrations |
| `uv run --directory postgres --locked pytest` (also invoked by `npm test`) | Final suite: 51 passed, no skips |
| `uv run --directory postgres --locked --python 3.14 mypy` | Passed, 13 source files |
| `uv run --directory postgres --locked --python 3.14 pytest` | 51 passed, no skips |
| `npm run test:db` | 41 passed, no skips |
| `npm run typecheck` | Passed, frontend types and backend mypy |
| `npm run build` | Next.js production build passed |
| `docker compose --profile identity --profile test config --quiet` | Passed with synthetic configuration values |
| `uv run --directory postgres --locked alembic heads` | One head: `0002_runtime_grants` |
| `uv run --directory postgres --locked alembic history` | Linear `base -> 0001_application_schema -> 0002_runtime_grants` |
| `uv run --directory postgres --locked alembic upgrade 0001_application_schema` | Passed on a fresh fixture-owned database |
| `npm run db:upgrade` | Upgraded that actual previous revision to head |
| `uv run --directory postgres --locked alembic current` | `0002_runtime_grants (head)` |

`npm ci --no-audit --no-fund` restored missing frontend dependencies after the
initial typecheck reported that `next` was unavailable. The initially attempted
uv-specific Linux image tag was unavailable; the successful CI replay instead
used official Python slim images with uv installed inside the disposable runner.
The real Uvicorn subprocess test caught and verified the correction of the custom
loop-factory signature; final results above include that subprocess check.

The CI-style bootstrap was also executed on a second fresh, disposable local
PostgreSQL instance, `quezo-f01-ci-550c86f7`. Its two role records had superuser,
database-creation and role-creation flags all false. The following PowerShell
commands exercised the same SQL inputs as CI:

```powershell
Get-Content postgres\bootstrap\roles.sql -Raw | docker exec -i quezo-f01-ci-550c86f7 psql -U quezo_test_admin -d quezo_test_control
Get-Content postgres\tests\bootstrap.sql -Raw | docker exec -i quezo-f01-ci-550c86f7 psql -U quezo_test_admin -d quezo_test_control
```

Linux replay used that instance's network namespace with the test admin URL
pointing to `127.0.0.1:5432/quezo_test_control` and the same synthetic test
password variables. For each of `3.12` and `3.14`, these commands were executed
(shown with a PowerShell variable to avoid duplicating the command):

```powershell
$python = "3.12" # Repeat with "3.14".
docker pull -q "python:$python-slim"
docker run --rm --network container:quezo-f01-ci-550c86f7 --mount "type=bind,source=$PWD,target=/work,readonly" -e UV_PROJECT_ENVIRONMENT=/tmp/quezo-venv -e QUEZO_TEST_ADMIN_URL -e QUEZO_TEST_MIGRATION_PASSWORD -e QUEZO_TEST_RUNTIME_PASSWORD "python:$python-slim" sh -c "python -m pip install --quiet uv==0.12.17 && uv run --directory /work/postgres --locked --python $python mypy --cache-dir /tmp/mypy-cache && uv run --directory /work/postgres --locked --python $python pytest -o cache_dir=/tmp/pytest-cache"
```

Both Linux runs passed mypy and all 51 tests without skips, on Python 3.12.15
and 3.14.8 respectively. This verifies the locked dependencies and database
suite on both CI Python versions, but does not claim a GitHub Actions run.
The installed package metadata requires Python >=3.10 for Psycopg/pool/Alembic
and >=3.11 for SQLAlchemy, compatible with the repository's >=3.12 baseline.
Only the synthetic control database remained after each suite; the disposable
local database services were removed after verification.

## F03 web session and navigation interface

B.C.'s [second-wave approval](SOFTWARE-SPECIFICATION.md#second-wave-approval-record-20-october-2026)
dispatched F03 from integrated F01/F02 with an exclusive shared-file window.
F03 and the subsequent I01 package are now done; the active I02 assignment and
explicit F03 completion exception are recorded below. Historical test results
remain unchanged.

### Configuration, lifecycle and OIDC requirements

Runtime packages are npm-locked: `openid-client` 6.8.8, `pg` 8.23.1,
`server-only` 0.0.1, `ajv` 8.20.0 and `ajv-formats` 3.0.1.
AJV validates the **existing exported server schemas**, not parallel web DTOs.
Focused test tooling adds `tsx` 4.23.15 and `@types/pg` 8.23.1; Node's built-in
test runner and React's server renderer suffice for package-level checks.
I02 still owns browser-runner selection and combined real identity acceptance.

Export these variables to the web server process, not `NEXT_PUBLIC_*` and not
the backend. The root `.env` is Compose input only.

| Variable | Exact contract |
| --- | --- |
| `QUEZO_WEB_ENV` | Required `local` or `shared`; local URLs must use loopback hosts |
| `QUEZO_WEB_ORIGIN` | Required exact public origin, e.g. `http://localhost:3000`; no credentials/path/query/fragment |
| `QUEZO_BACKEND_ORIGIN` | Required backend origin, locally `http://localhost:4000` |
| `QUEZO_OIDC_ISSUER` | Exact issuer, locally `http://localhost:8080/realms/quezo-local`; no query/fragment/credentials |
| `QUEZO_OIDC_CLIENT_ID` | Confidential web client ID, locally `quezo-web` |
| `QUEZO_OIDC_CLIENT_SECRET` | Required client secret, server environment only; never a Keycloak-admin credential |
| `QUEZO_API_AUDIENCE` | Dedicated API audience **and client-scope name**, locally `quezo-api`; 1-100 ASCII letters/digits/underscores/hyphens |
| `QUEZO_WEB_DATABASE_URL` | Explicit PostgreSQL URL with `quezo_web`, password, host and database; no query parameters; shared mode verifies database TLS certificates |

Shared mode requires HTTPS for all HTTP dependencies and sets Secure cookies.
For a private database CA use the process trust store / `NODE_EXTRA_CA_CERTS`;
never disable certificate verification. Local mode is exclusively loopback and
may use HTTP and non-TLS PostgreSQL. Runtime configuration rejects migration,
backend and bootstrap database identities. Privileged startup is forbidden.

After explicit bootstrap/migration, run `npm run dev:web` or, after
`npm run build`, `npm run start --workspace @quezo/web`.
The launcher defaults to `127.0.0.1` and sets `NEXT_MANUAL_SIG_HANDLE=1`.
Next instrumentation opens/verifies one shared pg pool per process and installs
SIGINT/SIGTERM cleanup; failed pool startup also closes all connections.
Use the launcher rather than bare `next start/dev`, whose competing default
signal handler can exit before application cleanup. Windows forced process
termination cannot run graceful handlers; connection teardown still invalidates
no persisted sessions. Build/type generation requires no database or OIDC secret.

For I01's local realm/client provisioning (no realm is auto-created by F03):

- Realm `quezo-local`; issuer exactly matches discovery, including scheme/host/port.
- Client `quezo-web`: confidential/client authentication enabled, standard code
  flow only; implicit flow, direct access grants and service accounts disabled;
  PKCE method S256. RS256 ID tokens are required and signature/JWKS checks enabled.
- Register only `${QUEZO_WEB_ORIGIN}/auth/callback` as a valid redirect URI
  (default `http://localhost:3000/auth/callback`); no wildcard/path/alternate-host
  entries. Login uses response type `code`, query callback, state, nonce and PKCE.
- Create client scope `quezo-api`, attach it to the web client, and configure
  its audience mapper to include `quezo-api` in **access tokens**. The web requests
  `openid quezo-api`; I01 must independently verify that dedicated API audience,
  issuer/signature/lifetime. ID tokens target the web client, not the API.
- Configure any web origins exactly, not `*`. The web server calls discovery,
  token/JWKS and backend endpoints; the browser receives only authorization
  redirects and opaque cookies, never tokens.

Synthetic identity creation and application `(issuer, subject)` mapping/role
provisioning are explicit I01 owner actions. Creating a Keycloak account or
signing in grants no application role. Empty/combined application roles are
valid; the backend's current status and operation/ownership decisions are final.
No admin credential is accepted by the web interface. I01's `infra/keycloak/README.md` documents the explicit local realm/provisioner.
It does not establish I02's combined browser acceptance.

### Routes, storage and defaults

| Surface | Behavior |
| --- | --- |
| `POST /auth/login` | Require exact Origin and Host; reject cross-site/same-site fetch metadata; discover issuer, persist a fresh binding/state/nonce/verifier and invalidate prior browser session/login |
| `GET /auth/callback` | Exact configured redirect; atomically consume matching browser binding once, verify state/nonce/PKCE and ID-token signature/issuer/audience/lifetime; call backend `/api/v1/me`; issue a new opaque session only for a valid active actor |
| `POST /auth/logout` | Same origin protection; durably invalidate session and pending login before clearing cookies and redirecting home |
| `GET /` | Server-only cookie lookup, expiry check and fresh backend `/me` for every authenticated render; native role-aware navigation, no assessment or administration screens |

`src/lib/server/http.ts` validates Host against the configured public origin,
then canonicalizes Next's internal bind URL. Never trust `X-Forwarded-*` to
choose a redirect or origin. A reverse proxy must preserve the exact configured
Host, strip untrusted forwarding headers, terminate HTTPS in shared mode and
disable access/query/body/header logs. Origin is mandatory on login/logout;
`null`, absent and nonmatching values fail. If `Sec-Fetch-Site` is present, only
`same-origin` is accepted. This is strict Origin-based CSRF protection, not an
unvalidated double-submit cookie; there are no GET logout/login mutations.
The callback is the protocol exception, protected by a browser-bound, single-use
state/nonce/PKCE transaction. There is no user-selected return URL.

Cookies are `quezo_session` and `quezo_login` locally, or
`__Host-quezo_session` and `__Host-quezo_login` in shared mode. Values are
32 random bytes encoded base64url (43 characters), HttpOnly, SameSite=Lax,
Path=/, no Domain; shared cookies are Secure. SHA-256 ID hashes, not usable
cookie values, are stored in PostgreSQL. Login rotates both binding and session;
logout also cancels a callback in flight through its originating login hash.
Invalidation uses separate READ COMMITTED statements in one transaction so a
callback holding the login-row lock cannot commit a session invisible to logout.
No process-local authoritative sessions, actor snapshots or refresh-token path.

| Fixed F03 default | Value / boundary |
| --- | --- |
| Login transaction/cookie lifetime | 5 minutes |
| Session absolute/cookie maximum | 8 hours; database session also capped by access-token expiry |
| Session idle timeout | 30 minutes; successful store lookup slides idle expiry, never absolute/token expiry |
| Access-token expiry | Fail closed and sign in again; no automatic refresh or offline scope |
| OIDC/backend request timeout | 5 seconds, no automatic retries |
| Backend actor/error body limit | 256 KiB |
| pg pool | Maximum 5 connections per process; at most 10 queued borrowers |
| pg connection / statement / lock / client query timeout | 5s / 5s / 2s / 6s |
| pg idle transaction / idle connection / connection maximum age | 5s / 10s / 300s |
| Expired-row cleanup | At login, delete at most 100 expired sessions and 100 expired login transactions |

These bounded defaults are authorized for B.C.'s review, not performance or
business-policy gates. Multiply connection bounds by the number of server
processes. No startup DDL or migration credential is used. Expired rows are
unusable immediately, but plaintext tokens/verifiers can remain until bounded
cleanup; a scheduled maintenance/retention policy remains required before real
data. Logout is **local Quezo logout**, not global Keycloak SSO termination or
access-token revocation. No provider logout URI is used; signing in again may
reuse the Keycloak SSO identity but always resolves a fresh backend actor.

`SessionStore.open/close`, `beginLogin/consumeLogin/createSession/session/logout`
and `prune` are server-only. The new Alembic revision is `0003_web_sessions`,
parent `0002_runtime_grants`; see the migration runbook for precise privileges,
existing-install role bootstrap and recovery implications. `quezo_runtime` cannot
read session secrets; `quezo_web` cannot read assessment tables or run DDL.

### Facade and I01/I02 handoff

`BackendFacade.actor(token)` now calls I01's generated `GET("/api/v1/me")`
operation with no-store and strict server-schema validation. I02 switches this
single adapter to the integrated operation without changing generated artifacts.
`BackendFacade.client(token)` supplies the existing `createApiClient`
with the same `authorizedFetch`: fixed backend origin, bearer token, stripped
Cookie, no redirects, bounded transport and no cache. Success and error bodies
are bounded to 256 KiB before generated-client parsing. Future route owners must
enforce the same origin boundary before state-changing facade calls. Every
backend protected operation must still enforce live roles/status/ownership.

The web never reads assessment tables and contains no assessment rules.
No actor cache is trusted on outage. Safe schema-valid backend errors preserve
code/message/requestId/details; network/invalid-response failures are explicit
503s. Unexpected errors become sanitized 500s. Only safe code/requestId events
are logged, never raw exceptions, tokens, callback queries or cookie values.
Next request logging is disabled. Instrumentation and route bundles preserve
branded errors across module copies. Route failures produce the envelope for API
requests or escaped actionable HTML for browser form submissions.

I01 supplies issuer/API-audience validation and real `/me`, including disabled
and revoked-role behavior, controlled provisioning and backend ownership checks.
I02 supplies real Keycloak/browser acceptance, provider-outage journeys and
manual keyboard/screen-reader/responsive review. F03's static-render checks
verify native links/buttons, skip target, nonpositive tab order, visible focus,
role-specific destinations and explicit status/error text; they are not full
WCAG conformance. The focused built-server HTTP test uses a controlled local OIDC
peer, never a runtime fixture/bypass, and is not the combined AT-01 gate.

### F03 verification commands

Export the four isolated test variables described above, start only the
worktree-specific `postgres-test` service, then run from the repository root:

```powershell
npm run typecheck
npm test
npm run build
npm run api:check
npm run test:contracts
npm run test:db
npm run test:web:production
```

`npm run test:web` runs configuration/origin/cookie/schema/facade/redaction and
semantic-navigation cases without a database. `test:db`/pytest create a fresh
UUID-named database per test and run the Node session suite with that fixture's
restricted web URL. No skip or memory substitute is used. The session suite
exercises real PostgreSQL expiry, rotation, replay, logout, privileges, durable
process restart, failed startup and a real broken TCP connection. A test-only
RS256 protocol peer exercises actual openid-client exchange/validation. Migration
tests prove clean head and `0002_runtime_grants -> head` upgrades and retain the
F01 transaction/isolation checks.

After building, `test:web:production` creates another isolated migrated database,
starts a bounded Next child process with synthetic OIDC/backend peers, checks the
real HTTP routes/rendered HTML/cache/error/log boundaries, stops it and drops
only its owned database. It uses no browser, real accounts or external service.
CI retains Node 22/24 and Python 3.12/3.14 checks; Python jobs install the locked
Node tools for real session tests and run the built-server check.

### F03 local verification: 20 October 2026

These are package review evidence, not hosted CI or accepted integration.
Environment: Windows x64, Node 24.20.0, npm 11.19.0, uv 0.12.17, Python 3.12.10,
Docker Engine 29.7.2, PostgreSQL 17.11 (Debian x86_64). Node 22, Python 3.14,
hosted CI, real Keycloak/browser login and assistive-technology review were not
executed locally for F03; configured CI and I01/I02 remain separate evidence.

Only the isolated synthetic test service was started:

```powershell
docker compose -p quezo-f03-37862b8f --profile test up -d --wait postgres-test
```

The shell set `QUEZO_TEST_PORT=55447`, distinct synthetic
`QUEZO_TEST_ADMIN_PASSWORD`, `QUEZO_TEST_MIGRATION_PASSWORD`,
`QUEZO_TEST_RUNTIME_PASSWORD`, `QUEZO_TEST_WEB_PASSWORD`, and unused development/
Keycloak password placeholders for Compose interpolation. Test commands exported
`QUEZO_TEST_ADMIN_URL` for `quezo_test_admin` at
`127.0.0.1:55447/quezo_test_control`, plus the matching migration/runtime/web
passwords. F01's control marker, generated database-name/owner guards and
non-FORCE teardown remained in use. No development volume or real identity data
was touched.

| Exact command, repository root | Outcome |
| --- | --- |
| `npm install --ignore-scripts --no-audit --no-fund` | Installed the approved dependencies and regenerated npm lock |
| `npm ls openid-client pg ajv ajv-formats server-only tsx @types/pg --depth=1` | Confirmed exact versions listed above |
| `npm run typecheck` | Passed web route/TypeScript checks and strict mypy, 22 Python files |
| `npm test` | 10 web tests and 154 Python cases passed, no skips; includes real Node/PostgreSQL session checks |
| `npm run build` | Passed production Next build, including all three auth routes and dynamic navigation |
| `npm run api:check` | OpenAPI and generated TypeScript unchanged/current |
| `npm run test:contracts` | 87 Python cases and 2 Node tooling/client tests passed |
| `npm run test:db` | 57 database/migration/lifespan/isolation cases passed, no skips |
| `uv run --directory postgres --locked pytest -s tests/test_web_sessions.py::test_web_sessions_against_real_postgres` | Final focused run: 13 Node checks passed inside the real isolated database fixture |
| `npm run test:web:production` | Built Next HTTP/HTML/cookie/cache/redaction test passed with local controlled protocol peers and real PostgreSQL |
| `uv run --directory postgres --locked alembic heads` | Exactly `0003_web_sessions` |
| `uv run --directory postgres --locked alembic history` | Linear `base -> 0001_application_schema -> 0002_runtime_grants -> 0003_web_sessions` |
| `docker compose --profile identity --profile test config --quiet` | Passed with synthetic required interpolation values |
| `git diff --check` | Passed |

Initial checks caught test-environment typing and worker module-format issues,
a loopback TCP test-proxy setup error, and two actual built-server integration
issues: module-copy error identity and internal bind-origin canonicalization.
They were corrected; the failed/hung runs are not counted as passes. Final
review also hardened callback/logout interleaving and tested pool/queue bounds;
subsequent runs caught and corrected a microsecond-sensitive expiry fixture and
OIDC nonconforming-HTTP/timeout error classification. Final full, database,
type/build and built-server commands passed after corrections; the unchanged
producer/client contracts also passed the separate checks above.
The interrupted test's disposable database is removed with the dedicated
test service, not by weakening F01's non-FORCE teardown.

After verification, no test application connections or scoped Node test
processes remained. Only the dedicated disposable service/network were removed,
including the interrupted run's synthetic database; no development volume was
deleted:

```powershell
docker compose -p quezo-f03-37862b8f --profile test rm -s -f postgres-test
docker network rm quezo-f03-37862b8f_default
```

| Requirement / acceptance boundary | F03 evidence |
| --- | --- |
| IAM-01; FR-001/002; partial AT-01 | Real openid-client code + PKCE, nonce/state/signature/issuer/client-audience/lifetime checks against a controlled peer; durable callback replay denial, rotation, expiry and logout; real Keycloak/API-audience gate remains I02 |
| IAM-02; FR-003/061; partial AT-01 | Fresh schema-validated `/me` per render, changed/empty roles and disabled/401 behavior, no cache on outage, no auto grants; independent backend ownership and token validation remain I01 |
| SRS sections 6-8; QUAL-02 / NFR-007,008 | Real database role isolation; strict Origin/Host/cookie checks; bounded store and dependency calls; token/secret absence from rendered HTML, responses and safe logs; no real-data privacy/retention acceptance |
| QUAL-03 / NFR-009; partial AT-14 | Native keyboard-operable navigation, labels, skip/focus targets, wrapping layout and explicit states; static-render evidence only, not full keyboard/screen-reader/WCAG acceptance |
| QUAL-04/05; partial AT-15 | Clean/prior-head migrations, process restart durability, failure/closure checks, locked dependencies, reproducible build and unchanged F02 contract checks; no deployment/readiness or recovery claim |

**Original handoff boundary:** F03 was returned ready for B.C.'s review, not
declared accepted by the implementing agent. It is now merged via PR #5 and
marked done by B.C. with EX-I02-01 explicitly carried into I02. I02 subsequently
reproduced/fixed the defect; B.C. accepted its evidence and closed the exception
on 21 October 2026.

## I01 identity and authorization

**Approval:** B.C.'s 20 October 2026 I01 DEC-06/07 extension and explicit
coordination-record reconciliation. Baseline: F01 PR #3 (`8732328`), F02 PR #4
(`5f314125e13262139e1d3e28d190881d6fbd5f8b`), integrated F03 PR #5 (`b1a2fe0`).
I01 does not claim acceptance or dispatch I02/A01.

Runtime dependencies are uv-locked PyJWT 2.15.1 with cryptography 50.0.2 and
the repository's existing HTTPX distribution, `httpx2==2.15.1`, imported as
`httpx2 as httpx`. The HTTPX dependency moved from dev to runtime; no second
HTTPX distribution was introduced.

### Configuration and validation

Export `QUEZO_OIDC_ISSUER` and `QUEZO_API_AUDIENCE` to the API process, in
addition to its restricted `QUEZO_DATABASE_URL`. A01 also requires
`QUEZO_ACCOUNT_ADMIN_CLIENT_ID` and `QUEZO_ACCOUNT_ADMIN_CLIENT_SECRET`; these
belong only in the API process and ignored local configuration. Issuer must be an exact
Keycloak realm URL without trailing slash, credentials, query or fragment;
HTTPS is required except for loopback HTTP. The defaults used by the local
realm/F03 web configuration are `http://localhost:8080/realms/quezo-local`
and `quezo-api`. Neither the API nor web receives bootstrap `master` admin
credentials; the web never receives the A01 service secret.
See [`infra/keycloak/README.md`](../infra/keycloak/README.md) for exact client,
redirect/logout, synthetic-account and explicit provisioning steps.

Lifespan creates one bounded database pool and one asynchronous HTTPX client
(two connections, proxy/environment trust and redirects disabled), and closes
both on shutdown. Import/OpenAPI generation reads no credentials and connects
to nothing. `/health/live` remains process-only and never fetches identity keys.
Missing/invalid identity configuration fails startup, not authentication-open.

| Setting | Default | Allowed bound |
| --- | --- | --- |
| `QUEZO_IDENTITY_TIMEOUT` | 5 seconds | Greater than 0, at most 10; total queue/lock/JWKS operation and HTTP timeout |
| `QUEZO_IDENTITY_CACHE_SECONDS` | 300 seconds | 10-600; monotonic in-process key cache, never an actor cache |
| `QUEZO_IDENTITY_REFRESH_SECONDS` | 10 seconds | 1-60, not above TTL; shared refresh/failure cooldown |
| `QUEZO_IDENTITY_MAX_LIFETIME` | 300 seconds | 60-900; maximum `exp - iat`, align with the realm |
| JWT / JWKS size | 32 KiB / 64 KiB | Fixed; streamed JWKS size enforcement |
| JWKS keys / RSA size | At most 32 / 2048-8192 bits | Fixed |

These are bounded local defaults authorized for review, **not DEC-08 performance
gates**. The allowed algorithm is explicitly RS256, never taken from an arbitrary
token choice. Signature, issuer, audience, subject, expiry, issued-at and access
token type (`Bearer`) are required. Numeric dates must be integers; future
issued-at/not-before, expired tokens, zero/overlong lifetimes and malformed
subjects fail closed, with no expiry leeway. ID tokens are not API credentials.

Only the configured issuer's `/protocol/openid-connect/certs` is fetched.
Token-supplied `jku`, `x5u`, `jwk`, unsupported critical headers and algorithm
changes are rejected; there is no unverified-claim fallback. A refresh replaces
the key set atomically. Concurrent refreshes are serialized; unknown key IDs
can trigger at most one fetch per cooldown across all IDs. A newly rotated key
inside the cooldown is temporarily rejected, then becomes usable after refresh.
Unknown keys after a successful refresh return 401, not a dependency error.

Cached keys remain usable until their bounded TTL, including during an outage;
this is signature verification, not a cached authorization decision. On expiry,
keys must refresh successfully; no stale-key fallback is allowed. Network,
timeout, redirect, malformed/oversized JWKS and unsupported key-set failures are
explicit 503 `DEPENDENCY_UNAVAILABLE`. Failed refreshes are also cooldown-bounded.
Cancellation propagates and releases the refresh lock. No retry loop is added.

### Actor and authorization interface

`quezo_api.modules.identity.access.get_actor` is the FastAPI dependency for
read operations. It validates one Bearer credential and then resolves the actor
from the database on **every** request. The token's role claims are never used.
Missing/inactive mappings return 401 `UNAUTHENTICATED`; mapped disabled accounts
return 403 `ACCOUNT_DISABLED`. Database outages preserve F02's safe 503 envelope.

For an atomic write, depend on `get_identity` to obtain a `VerifiedIdentity`,
open one `Database.transaction()`, and call
`resolve_actor(connection, identity)` **inside that same transaction**, before
operation/ownership checks and the write. Pass this leased connection onward;
do not open a second independent transaction or trust an earlier session actor.
Committed revocation denies subsequent admitted requests; a transaction already
admitted is not retroactively cancelled. No HTTP assessment/write route is
introduced by this package.

`require_role(actor, Role.AUTHOR)` requires the explicit operation role and active
status. `require_owner(actor, owner_id, Role.AUTHOR)` checks that role first
(403 if absent), then returns the same 404 `NOT_FOUND` for a missing/foreign owner.
Use the actual persisted owner, never a request-supplied assertion. Administrator
alone does not imply author/learner. Combined and empty roles remain valid.
Collections and nested resources must apply these same relationships before
serialization; future module owners own their queries, not generic middleware.

`GET /api/v1/me` returns only the existing F02 Actor (`userId`, `roles`, `status`)
for active mapped users. It exposes no tokens, email, issuer, subject or storage
fields. Success and errors use `Cache-Control: private, no-store`; F02 correlation
IDs and sanitized error envelopes remain unchanged. HTTPBearer security and
typed 401/403/503 responses are exported. OpenAPI and TypeScript were regenerated
using existing tooling, not edited by hand. F03's existing facade calls this
exact endpoint and validates its Actor; no frontend session/UI code changed.

The single migration chain now ends in `0004_identity`, parent
`0003_web_sessions`. The new backend tables contain no automatic seed grants.
F03 schema/role/bootstrap and all applied revisions are unchanged. Read the
[migration runbook](../postgres/migrations/README.md) for invariants and recovery.

### Checks and evidence boundaries

Use only the isolated synthetic database and, for the explicit actual-provider
check, the disposable `keycloak-test` service. Run from the repository root:

```powershell
npm run typecheck
npm test
npm run build
npm run api:generate
npm run api:check
npm run test:contracts
npm run test:db
npm run test:identity
npm run test:identity:integration
npm run test:web:production
```

`test:identity` covers signature/algorithm/claim/lifetime rejection, key rotation,
unknown IDs, cache/size/time limits, cancellation, safe dependency failures,
real database mapping/role/status lookup, role/ownership denial, revocation with
old tokens, database outage, controlled provisioning retry/concurrency/failure,
actual prior-head upgrade, rollback, constraints and F03 privilege isolation.
Verifier tests use generated RSA keys and a **synthetic HTTPX transport**; they
are not evidence that a live Keycloak service issued the token.

`test:identity:integration` is a separately invoked actual Keycloak 26.4.7 test,
using code+PKCE and real PostgreSQL. It creates/refuses-overwrite/cleans up its
own synthetic realm, provisions the five allowlisted account types, checks
real tokens/JWKS through `/me`, denies ID tokens and password grants, and proves
old-token role/status revocation. It uses HTTP clients rather than a browser
and does not pass through F03. CI adds this explicit local-service check to the
Python 3.12 job while retaining Node 22/24 and Python 3.12/3.14 checks and F03's
built-server test. Hosted CI is distinct from local execution.

| Requirement | I01 evidence / remaining boundary |
| --- | --- |
| IAM-01; FR-001/002; partial AT-01 | Independent signature/issuer/audience/lifetime validation; actual local Keycloak code+PKCE tokens; F03 owns session/nonce/state behavior, I02 owns combined browser acceptance |
| IAM-02; FR-003/061; partial AT-01 | Real current mapping/roles/status, old-token revocation, direct role/owner checks, administrator non-inheritance and 404 concealment |
| Identity portion of IAM-03; FR-004 | Explicit first-admin/synthetic provisioning; no new grant on identity/DB failure; safe retry and no revival of revoked accounts; no A01 UI/service privileges or mutation workflows |
| Sections 6-7; QUAL-02 / NFR-007/008 | UUID mapping, relational constraints, safe Actor/error output, token nondisclosure and backend/web database isolation; real-data privacy/retention remains held |
| QUAL-04 / NFR-010; partial AT-15 | Automated contracts, deterministic generation, clean/prior-head migrations and rollback/outage tests; not deployment/recovery acceptance |

### I01 local verification: 20 October 2026

Local review evidence, not hosted CI, accepted integration or full AT-01:
Windows x64, Node 24.20.0, npm 11.19.0, uv 0.12.17, Python 3.12.10 and 3.14.7,
Docker Engine 29.7.2, PostgreSQL 17.11 (Debian x86_64), Keycloak 26.4.7.
The primary virtualenv remained Python 3.12; the 3.14 compatibility run used
a separate session-artifact virtualenv through `UV_PROJECT_ENVIRONMENT`.

The isolated dependencies were started with:

```powershell
docker compose -p quezo-i01-e2f6cba3 --profile test --profile identity-test up -d --wait postgres-test keycloak-test
```

The provisioning/test shell used `QUEZO_TEST_PORT=55503`,
`KEYCLOAK_TEST_PORT=58083`, `KEYCLOAK_LOCAL_ORIGIN=http://localhost:58083`,
the four isolated PostgreSQL test credentials, and distinct synthetic
Keycloak/client/account credentials. The test admin URL targeted only
`quezo_test_admin` at `127.0.0.1:55503/quezo_test_control`. F01's database
marker/name/owner guards and non-FORCE teardown remained in use. No development
database, shared identity service or real identity data was used.

| Exact command, repository root | Final outcome |
| --- | --- |
| `uv add --directory postgres 'pyjwt[crypto]'`, then `uv lock --directory postgres` after pinning the selected version | Approved PyJWT/cryptography dependencies locked; HTTPX moved to runtime |
| `npm ci --no-audit --no-fund` | Restored missing web tools; npm lock unchanged |
| `npm run typecheck` | Web route/TypeScript checks and strict mypy passed, 37 Python source files |
| `npm test` | 10 web tests and 262 Python cases passed, no skips |
| `npm run build` | Production Next build passed; no frontend session/UI changes |
| `npm run api:generate` | Generated both OpenAPI and TypeScript `/me` output |
| `npm run api:check` | Both generated artifacts current |
| `npm run test:contracts` | 87 Python cases and 2 Node generation/client tests passed, including missing/stale output detection and identical regeneration |
| `npm run test:db` | 87 real database/migration/lifespan/isolation cases passed, including retained F03 session suite |
| `npm run test:identity` | 108 focused cases passed; synthetic RSA/JWKS transport plus real PostgreSQL |
| `npm run test:identity:integration` | Actual Keycloak test passed: all five account types, real code+PKCE exchange/JWKS/tokens, `/me`, old-token role/status revocation, ID-token/password-grant denial and provisioning replay refusal |
| `npm run test:web:production` | Preserved F03 built-Next HTTP/cookie/cache/redaction test passed against its controlled OIDC/backend peers and real PostgreSQL |
| `uv run --directory postgres --locked --python 3.14 mypy` | Passed, 37 files |
| `uv run --directory postgres --locked --python 3.14 pytest tests/test_identity_tokens.py tests/test_keycloak_provisioning.py` | 78 compatibility cases passed |
| `uv run --directory postgres --locked --python 3.14 python scripts/export_openapi.py --check` | Identical OpenAPI across Python 3.12/3.14 |
| `uv run --directory postgres --locked alembic heads` | Exactly `0004_identity` |
| `uv run --directory postgres --locked alembic history` | One linear chain from `base` through `0001_application_schema`, `0002_runtime_grants`, `0003_web_sessions`, `0004_identity` |
| `docker compose --profile identity --profile identity-test --profile test config --quiet` | Passed with synthetic interpolation values |
| `git diff --check` | Passed |

Initial checks exposed an incorrect HTTPX import, fixture typing/indentation
errors and actual Keycloak integration requirements: server-generated subjects,
admin-managed provisioning markers, required synthetic profile fields and an
explicit access-token subject mapper. These were corrected before the final
results above; no signature/issuer/audience/lifetime check was weakened.
The HTTP integration harness explicitly handles localhost Secure login cookies;
this is not a claim of browser or F03-facade execution.

Node 22, hosted Linux CI, the full Python 3.14 real-database suite and combined
real-browser login were not executed locally. The configured matrices remain
review evidence to obtain; I02 still owns the final browser/facade/API identity
gate. A01's administration UI/service privileges and later release/data gates
remain excluded. No automatic commit, PR, successor launch or deployment occurred.

After a second successful actual-Keycloak run, the following cleanup removed
only the two owned disposable services/network, leaving development volumes
untouched:

```powershell
docker compose -p quezo-i01-e2f6cba3 --profile test --profile identity-test rm -s -f postgres-test keycloak-test
docker network rm quezo-i01-e2f6cba3_default
```

**Original handoff boundary:** I01 was returned ready for B.C.'s review, not
declared done by the implementing agent. B.C. has since confirmed completion
and accepted the merged package; current status is in the backlog.

## I02 integrated browser gate

**Acceptance update, 21 October 2026:** B.C. confirmed I02 complete. PR #7
(`553a2c8`) is merged; its browser job and Node 22/24/Python 3.12/3.14 jobs passed.
Review found no significant standards/specification issues. EX-I02-01 is closed
with the native-browser red/green evidence below. The original handoff is retained
as historical evidence, not a statement of current tracker status.

### Review handoff: 20 October 2026

**Work item:** I02, Integrated login and access gate.

**State at the original handoff:** ready for B.C.'s review; superseded by the
accepted/done record above. The final local combined command exited 0 with all 16 browser
cases passing, no skipped cases, and owned-resource cleanup completed.

**Changes:** `tests/e2e/` supplies locked Playwright configuration, reusable
synthetic login/application fixtures, real-browser scenarios and a
secret-safe reporter/runbook. `postgres/tests/run_browser.py` owns isolated
Compose/provisioning/migration/startup/cleanup, with focused launcher tests.
Root manifests/lock/scripts and one non-matrix CI browser job connect the suite.
The approval/checkpoint documents were reconciled only after B.C.'s explicit
permission in that session; I02 was then active pending review. It is now done.

Only two producer changes were needed: `frontend/quezo/next.config.ts` uses
`strict-origin` on documents while explicitly retaining `no-referrer` on
`/auth/:path*`; `src/lib/server/facade.ts` uses I01's generated `/me` operation
and bounds success/error bodies before generated-client parsing. Native forms,
CSRF checks, cookie/session defaults, issuer/audience/signature checks and
account authority are unchanged. Focused frontend regressions cover the headers
and bounded generated-client error path.

**Requirement coverage:** IAM-01/02, AT-01, QUAL-02; FR-001/002/003/061 identity
and role behavior; NFR-007/008 nondisclosure/security evidence; sections 6-8
actor/error contracts and login states. Keyboard focus checks support only the
foundation portion of QUAL-03, not Q02/WCAG acceptance. Existing type, migration
and contract checks continue supporting QUAL-04/05; no full P0/AT-15/pilot claim.

### EX-I02-01 reproduction and proposed resolution

Browser: **Chromium 156.0.8078.4**, Playwright Test **1.64.1**, Windows x64.
All observations below used native clicks/submissions, no test-API Origin
injection or global request-header overrides.

| Observation | Exact evidence |
| --- | --- |
| Original login red | `npm run test:e2e -- --grep native`, project `quezo-i02-5b0f74463418`, web `http://127.0.0.1:52316`: native POST logged `Origin=null; status=403`; expected exact origin/303 failed |
| Original logout diagnosis | Temporary diagnostic case, `npm run test:e2e -- --grep diagnostic`, project `quezo-i02-18334a263d17`: changing **only that login document's** meta referrer policy to `strict-origin` yielded `Origin=http://127.0.0.1:50270; status=303`; actual provider UI completed login; the newly loaded original-policy page's native logout sent literal `Origin: null` and returned 403 |
| Final normal behavior | Final combined run, web `http://127.0.0.1:58572`: both native login and logout sent `Origin=http://127.0.0.1:58572`, returned 303 and completed the expected signed-in/signed-out UI |
| Retained negative control | Final `EX-I02-01 no-referrer negative control` case sets only a document meta policy to `no-referrer`: both forms again send literal `Origin: null` and receive 403 |
| Disclosure/CSRF safeguards | Normal login Referer contains origin only, never the query sentinel; auth-route responses explicitly remain `no-referrer`; callback URLs are not forwarded as referrers; foreign/null/missing Origin requests are still rejected |

The temporary diagnostic was replaced by the permanent negative control and
normal-path tests. An initial full run also caught Next's global header rule
overriding the intended route-level policy; the explicit `/auth/:path*` rule
fixes that precedence. The exception is **reproduced and fixed with closure
evidence returned**, not administratively closed by the agent.

### AT-01 scenario results

These are final **local automated browser** results from the unfiltered
`npm run test:e2e -- --checks` run, project `quezo-i02-85a400c9e613`.
See `tests/e2e/access.spec.ts` for executable assertions.

| Case | Result and observed behavior |
| --- | --- |
| EX-I02-01 negative control | PASS: native null-Origin login/logout both 403 |
| Native login/local logout | PASS: actual provider callback, exact-Origin forms, durable session deletion, new opaque session on re-login; Keycloak SSO/old API token remain valid after local logout |
| Administrator | PASS: administrator-only navigation; real `/me` actor; reload persistence; cookie/DOM/storage checks |
| Author | PASS: author-only navigation and same actor/privacy checks |
| Learner | PASS: learner-only navigation and same actor/privacy checks |
| Combined | PASS: author plus learner, no administrator inheritance |
| Empty | PASS: authenticated empty-role actor, no workspace links, explicit no-role message |
| Persistence/keyboard | PASS: same session survives built-web restart; Tab/Enter skip link, native login, provider password focus, workspace anchor and native logout |
| Old-token revocation/disable | PASS: removing author role removes navigation and changes `/me` immediately; disabled account returns 403, invalidates session and cannot reactivate through existing provider SSO |
| Inactive mapping | PASS: old token 401; existing browser session becomes expired |
| Independent direct API | PASS: missing/malformed/tampered token 401; actual signed provider token 401 with wrong expected audience or issuer; restored exact configuration returns 200 |
| Callback/state/binding/replay | PASS: wrong state, new-context missing binding and replay of a completed real callback return 401 with an actionable error |
| CSRF | PASS: real different-origin browser form 403 without invalidating the valid session; supplemental missing/null/foreign HTTP requests deny both auth actions |
| Backend/database outages | PASS: stopped actual API and severed real API/web PostgreSQL transports each produce explicit errors with no authenticated fallback; recovery revalidates the session |
| Identity outage | PASS: paused real Keycloak permits warm cached keys only within the configured 10s TTL; expired/cold caches return 503; cold web discovery returns an actionable 503; unpause restores validation |
| Actual expiry | PASS in 303087ms: unchanged 300s provider lifetime expires naturally; retained opaque cookie cannot authenticate; old API token returns 401; no refresh, time shift or row/token injection |

All cases also completed the fixture's application-log secret checks. Browser
checks confirm tokens/usable login and session secrets are absent from DOM,
localStorage/sessionStorage and readable cookies, and the browser does not
call the backend with a token. HttpOnly local session cookies are intentional.
Shared Secure/host-prefix policy remains unit-tested, not a shared-TLS browser
deployment claim. Traces/HAR/video/screenshots/storage-state are not retained.

The role/ownership enforcement helpers have no product routes to exercise yet.
Retained I01 `test_identity_access.py` supplies direct test-route role/ownership
denials (including administrator non-inheritance), while this suite supplies
actual provider/browser `/me`, invalid-token and revoked-account evidence.
These evidence types are complementary, not interchangeable.

### Exact commands, environment and cleanup

Final environment: Windows x64; Node **24.20.0**, npm **11.19.0**;
uv **0.12.17**, Python **3.12.10**; Docker Engine **29.7.2**, Compose **5.4.0**;
PostgreSQL **17.11** (Debian x86_64); Keycloak image **26.4.7**;
Next **16.4.2**; Playwright **1.64.1**, Chromium **156.0.8078.4**.
The final owned services used PostgreSQL port **58570**, Keycloak **58571**,
built web **58572**, API **58573**; application database transports used
additional ephemeral loopback listeners. Realm/client/scope/audience were
`quezo-local` / `quezo-web` / `openid quezo-api` / `quezo-api`, with exact
issuer `http://localhost:58571/realms/quezo-local` and registered callback
`http://127.0.0.1:58572/auth/callback`.

| Exact command, repository root | Final result |
| --- | --- |
| `npm install --ignore-scripts --no-audit --no-fund` | Installed approved browser dependency and regenerated npm lock |
| `npx playwright install chromium` | Installed the actual Chromium/headless-shell dependency |
| `npm run typecheck` | Web, strict mypy (39 Python files) and browser TypeScript passed |
| `npm test` | 12 web checks plus 264 Python cases passed, no skips |
| `npm run build` | Built actual Next production routes successfully |
| `npm run api:check` | OpenAPI and generated TypeScript current/unchanged |
| `npm run test:contracts` | 87 Python cases plus 2 Node tooling/client checks passed |
| `npm run test:db` | 87 cases passed, including clean/prior-revision migrations and restricted role/session checks |
| `npm run test:identity` | 108 cases passed |
| `npm run test:identity:integration` | 1 actual-Keycloak HTTP integration case passed; separately identified as HTTP, not browser proof |
| `npm run test:web:production` | 1 retained built-Next/controlled-peer HTTP test passed; not used as browser proof |
| `npm run test:e2e -- --checks` | Executed the nine checks above then all 16 real-browser cases; overall exit 0, cleanup completed |
| `npm ls @playwright/test openid-client openapi-fetch pg next --depth=1` | Confirmed locked versions; existing producer dependencies preserved |
| `git diff --check` | Passed |

Initial failures are not counted as passes: missing web dependencies were
restored after the initial typecheck failed; the runner needed Windows
ProgramFiles environment for Compose plugin discovery; the native-form
exception was reproduced before fixing; ambiguous global alert locators were
scoped to `main`; explicit auth header precedence was corrected. Two combined
attempts hit Windows nested-command exit `3221226505` with a newly created
console process group. The isolated command passed, and removing that unnecessary
Windows group flag allowed the complete final command to pass. PID-tree timeout
cleanup remains; no test or assertion was skipped to bypass these failures.

The full startup/installation/focused-demo/emergency-cleanup commands are in
[`tests/e2e/README.md`](../tests/e2e/README.md). Normal cleanup executed the exact
owned Compose service removal and network removal for
`quezo-i02-85a400c9e613`. A post-run inspection found no containers/network for
that project or its web/API/browser processes. Failed earlier runs also removed
their owned services. No development volume or existing realm was targeted.

**Contracts:** no new endpoint/DTO, generated artifact or schema change.
The existing generated `/me` operation is now the frontend adapter's typed call;
Actor stays `userId`, explicit `roles`, `status`. No runtime backend/Keycloak
producer code changes were necessary.

**Data:** migration head remains `0004_identity`, after `0003_web_sessions`.
The retained database suite passed clean and prior-head upgrades, durability,
constraints and role isolation. No applied revision, data retention or recovery
policy changed; existing recovery cautions about restoring revoked accounts or
locally invalidated sessions still apply.

**Integration:** verified ancestors F03 PR #5
(`b1a2fe035d52cdddf4db3a0c832a690773fe5688`) and I01 PR #6
(`6ef734faefbb52c76b78abb7d676ec9305f0c557`); checkout and remote main initially
matched the latter. Missing I02 coordination records were reconciled only after
B.C.'s explicit follow-up authorization. Work remains uncommitted on
`bc-bah-i02-login-access-gate`; no PR, successor, external resource or deployment.

**Known gaps:** no unresolved local I02 scenario; B.C.'s acceptance/exception
closure and hosted CI are outstanding. Node 22/Linux and Python 3.14 were not
rerun locally for I02. Keyboard observations are automated Chromium checks;
human screen-reader/full WCAG, assessment workflows, A01 and pilot gates remain
outside this work.

**Successor handoff (C01/T01):** after B.C.'s acceptance and separate dispatch,
reuse `test`, `login`, `beginLogin`, `privatePage` and the owned application fixture
in `tests/e2e/fixtures.ts`. Use fresh browser contexts when changing identities;
local logout intentionally preserves Keycloak SSO. Keep mutation scenarios serial
or provide independently owned accounts. Consume `BackendFacade.client/actor`
and the generated schema; backend writes must resolve live actor/roles inside
their transaction before operation/ownership checks. The repeatable navigation/
restart demonstration works, but no question, quiz or attempt route is supplied.

## A01 account administration

The administrator workspace at `/admin/accounts` is backed by the live
administrator-role check in the web facade and independently by each FastAPI
account endpoint. It lists application-linked account profiles and provides
disabled identity provisioning, PostgreSQL application-role changes, and
activation/deactivation. Administrators do not receive assessment-answer access.
The API never stores passwords or returns Keycloak subjects, tokens or secrets.

The local API uses only the `quezo-account-admin` confidential client-credentials
identity described in [`infra/keycloak/README.md`](../infra/keycloak/README.md).
The service secret remains server-side and is not passed to the web container.
Keycloak users are created disabled with an application ownership marker; exact
username lookup plus that marker makes an incomplete create safely retryable
without adopting a foreign account. Provisioning retries repeat the same
username/email. Roles are authoritative only in PostgreSQL. Activation enables
the identity first and grants application access only after success; deactivation
revokes the database mapping/status before attempting identity disable, so an
identity-service outage cannot preserve application access. The account list
exposes failed/in-sync state and a failed provision can be retried. No account
delete, credential-reset or password endpoint exists.

Migration `0011_account_administration` follows the verified C03 baseline
`0010_author_workspace`, adds profile/provisioning/sync state and a restricted
administrator integrity-event table. A transaction-scoped advisory lock
serializes last-active-administrator checks with role/status changes. Do not
rewrite any applied revision.

Focused A01 tests cover the three application roles, incomplete provisioning
and safe retry, duplicate refusal, last-admin protection, live role/status
revocation, provider-sync failure and administrator denial from learner results.
A temporary synthetic user was also created, profile-read/updated,
enabled/disabled, and removed using the verified local Keycloak service
identity. These cases are a subset of AT-02 and AT-01; they are not full
AT-01/AT-02 acceptance or the complete browser/authorization catalogue.

## D04 configurable delivery controls

Execution baseline: B.C. explicitly confirmed integrated `40d667d`, migration
head `0011_account_administration`, and the exclusive D04 settings/assembly/
contract/migration window. This is a consumer-baseline record, not tracker
acceptance. T01 `df06ccc` and C03 `2eba9eb` are ancestors. No commit/PR, R02
dispatch or acceptance update is automatic.

C03's composition/publication wrapper now embeds complete delivery settings:
explicit unlimited duration/attempts, bounded integer values, independent order
flags, IANA zone and optional availability bounds, plus independent score/key/
explanation release modes. The existing two release presets remain shortcuts.
Schedule entry is explicitly **UTC**, with an IANA-zoned confirmation of each
instant; it never guesses which repeated local hour the author intended or
normalizes a nonexistent local wall time. For a repeated local time choose its
distinct UTC instant. The zone is stored with UTC bounds; backend policy validation
still rejects invalid zones, schedules, limits and release-after-end without an
end. Saving/publishing does not reassign any learner.

Before a new start, every eligible learner can use labelled native keyboard
controls for standard, adjusted (60-6048000 seconds, initially ten times the
authored duration), or off. The same controls can be tried in author preview
without writing assignments, attempts or grades. Assignment cards explain state,
remaining starts, availability and authoritative server eligibility. Attempts show
their frozen timing and deadline, with no post-start extension controls.
After a dispatched start, retries retain the original body/key; a concurrent
start/resume cannot replace the winning snapshot's choice.
The new settings/timing fieldsets stay disabled until client handlers are ready,
so early native keyboard changes cannot be lost before hydration.

`StartCommand` adds optional `timingChoice` (standard by default) and
`adjustedDurationSeconds` (required only for adjusted). The server rejects coercion,
unknown modes, inappropriate durations and client-selected deadlines.
Attempt responses expose those frozen timing fields. Assignment responses add
authored duration and scheduling zone without questions or keys. OpenAPI and the
generated TypeScript contract are regenerated.

Forward migration `0012_delivery_controls` follows the actual A01 head. It
preserves old snapshots/deadlines and empty-payload replay fingerprints. Application
and database validation both retain the new-start cutoff in every mode; adjusted
deadlines are not capped by availability end, and off has neither bound.
Existing parent-lock/post-lock database-time admission, expiry reconciliation,
finalization and result filtering are reused, not replaced. Closing is not expiry
or release. Release after availability end still needs finalization and the
original pinned authored end.

### D04 case-level evidence map

| Catalogue scope | New D04 cases | Retained evidence, not new implementation |
| --- | --- | --- |
| AT-05 (settings/preview) | `test_policy_revision_only_explicit_new_assignment_and_preview`; `test_preview_independent_order_flags` (all four flag combinations); browser `D04 AT-05/06/09/12` covers saved/reloaded settings, explicit UTC repeated-hour choices, non-persisting preview and native labelled timing controls | C03 composition/lifecycle and C02 preview ownership/private-field allowlist remain their prior scope |
| AT-06 (distribution/order/start limits) | `test_concurrent_choices_resume_replay_and_limit` checks competing choices, same-key replay/conflict, active resume, finalized replay and concurrent limit denial; revision test checks old assignment/attempt unchanged and explicit new assignment; browser tests all three timing modes and refresh/resume | D01's four independent question/option flag combinations, disabled paths, refresh-stable snapshots and assignment races remain D01 coverage |
| AT-09 (timing) | `test_exact_timing_and_start_cutoff` checks exact lower/end boundaries in each mode; `test_queued_cutoff_every_mode` waits on the real assignment lock across end; `test_near_end_and_close_are_not_adjusted_expiry` checks standard expiry versus continuing adjusted/off, accepted post-end saves and completion; `test_off_without_availability_has_no_deadline`; invalid HTTP choices and direct database snapshot rejection | D02/D03 lock-safe save/submit expiry and periodic reconciliation remain prior evidence |
| AT-12 (release protection) | Near-end tests require finalization even after scheduled end for adjusted/off, then retain key withholding while releasing configured score/explanation; ordinary snapshots remain filtered | R01's 27 independent release-mode combinations and boundary filtering are rerun unchanged, not counted as new D04 coverage; T01's accepted lifecycle remains prior evidence |
| Migration compatibility | Actual post-A01 active/finalized and timed/untimed snapshots, accepted responses/ledger, legacy empty-body fingerprint, repeat head, failed-DDL rollback and immutable timing columns | Foundation clean-head/earlier-producer upgrades are retained checks |

These are scoped case-level claims, not full catalogue AT-05/06/09/12 completion.
Native keyboard interaction and accessible-name/role assertions are representative
assistive-technology semantics, not a manual screen-reader audit. No WCAG
conformance or AT-14 completion is claimed. Random subsets, grace, reset/reopening
and individualized accommodations remain excluded.

### D04 executed checks (27 October 2026)

Environment: Windows, Node 24.20.0, Python 3.12.10, PostgreSQL 17.11, locked
Playwright 1.64.1/Chromium. Database checks used newly owned disposable PostgreSQL
projects and the existing guarded isolated-database helpers, not development data.
A session-only wrapper supplied random test-role secrets and a loopback control
URL, invoked the following pytest commands from the repository root, and removed
only its named service/network in `finally`. No credentials or raw assessment
payload logs are retained.

```powershell
python -m pytest -c postgres\pyproject.toml postgres\tests\test_delivery_controls.py postgres\tests\test_delivery_migrations.py postgres\tests\test_attempts.py postgres\tests\test_attempt_migrations.py postgres\tests\test_finalization_migrations.py postgres\tests\test_results.py postgres\tests\test_migrations.py --tb=short
python -m pytest -c postgres\pyproject.toml postgres\tests\test_delivery_controls.py postgres\tests\test_delivery_migrations.py postgres\tests\test_finalization_migrations.py postgres\tests\test_response_migrations.py postgres\tests\test_identity_migrations.py postgres\tests\test_question_migrations.py postgres\tests\test_quiz_migrations.py postgres\tests\test_quizzes.py postgres\tests\test_contract_schemas.py postgres\tests\test_http_contract.py --tb=short
```

| Check | Result |
| --- | --- |
| First focused Python command | 108 passed in 534.68 seconds; this preceded expansion of the new preview/database-boundary/migration cases |
| Final expanded Python command | 200 passed in 638.57 seconds; includes all 43 new D04 cases, prior-head migration regressions, policy and HTTP/schema contracts |
| `npm run typecheck` | Passed Next/TypeScript, strict mypy (95 sources), browser TypeScript |
| `npm run test:web` | Existing 12 web unit checks passed |
| `npm run api:generate` / `npm run api:check` | Generated OpenAPI/client; freshness check passed |
| `node --test postgres\scripts\test_contract_tools.mjs` | Both contract tooling/client cases passed |
| `npm run test:e2e -- --grep "D04\|C03\|C02 AT-04/05\|D01 AT-06\|T01 AT-03"` | Final rerun passed production build and all 8 real-provider browser cases: 1 new D04 (18.812 seconds), 3 inherited C03, 1 C02, 1 D01 and 2 T01; zero failures/skips/interruptions |
| `uv run --directory postgres --locked alembic heads` | Single forward head `0012_delivery_controls` |
| `git diff --check` | Passed |

During browser iteration, the added timing fieldset exposed an old "first
fieldset" preview assertion; it now addresses the first question group explicitly.
Early keyboard interaction also reproduced a pre-hydration lost change, fixed
with readiness-disabled new fieldsets. Native datetime-local test inputs use
canonical browser values (zero seconds omitted), and the score selector uses
its full labelled-control semantics rather than an incorrect exact label-text
assumption. The runner's explicit test allowlist and safe failure-location
allowlist now include D04. These failed intermediate runs are not acceptance
evidence. The full unfiltered browser/umbrella check and hosted matrix were not
run for D04; only the recorded focused commands are claimed.
The preceding eight-case run passed D04 and six inherited cases but timed out
in the score-only T01 journey at its 180-second case limit; the safe report did
not establish the exact cause. No timeout or product threshold was relaxed.
The unchanged full eight-case selector then passed on fresh owned services,
including T01 score-only in 25.524 seconds. The earlier timeout remains recorded,
not relabelled as a diagnosed environment failure.

## R02 history and author reporting

### Baseline and boundaries

B.C. confirmed clean integrated commit
`d43d89351a1740c7c5143144ee78829240e26ead`, migration head
`0012_delivery_controls`, and the exclusive R02 router/generated-contract/index
or migration window before implementation. This checkout includes T01
`df06ccc`, C03 `2eba9eb`, A01 and D04. This is implementation/review evidence
only; no tracker acceptance, commit/PR, successor dispatch or pilot approval.

R02 extends the existing Results module, not scoring or finalization. Reads use
the persisted attempt state and immutable Grade, never a reconstructed score or
an inferred expiry. An overdue but not-yet-finalized attempt remains in progress
until the existing expiry worker or attempt finalization reconciles it. Timing
choice, adjusted duration and deadline are read from the D04 attempt snapshot;
availability end still independently controls each pinned disclosure policy.
Close/archive retain history and do not release restricted results.

### Contracts and navigation

| HTTP read | Projection |
| --- | --- |
| `GET /api/v1/me/attempts` | Own learner attempt history, pinned title/version, assignment/attempt identity and number, start/deadline/completion/timing, released/withheld/not-finalized score |
| `GET /api/v1/quizzes/{quiz_id}/results` | Owner-only summary plus paginated assigned learners, including those with no attempts |
| `GET /api/v1/quizzes/{quiz_id}/results/attempts` | Owner-only attempt rows across all retained publications, including in-progress rows with no final score |
| `GET /api/v1/quizzes/{quiz_id}/results/attempts/{attempt_id}` | Owner-only finalized saved responses and the shared R01 policy-filtered result projection; active attempts return `INVALID_STATE` |

All list operations use existing `pageSize` (1-100, default 25) and opaque UUID
`cursor` conventions. Rows are in stable UUID order, not a claimed chronological
or best-attempt ordering. Cursors must belong to the same learner/quiz scope;
foreign or absent IDs are concealed as 404, malformed cursors as 422. Nested
submission IDs must belong to the specified owned quiz. Administrator privilege
does not bypass author/learner roles or resource relationships. Current active
mapping, account status and roles are resolved on every public service call.
All result/report/history responses are private/no-store.

The learner assignment workspace links to `/learner/history`; history links to
the exact finalized result or active attempt. The quiz workspace links to
`/author/quizzes/{quizId}/results`, which links to finalized submission inspection.
These are server-only facade calls using regenerated OpenAPI/TypeScript
contracts, not direct browser/database access. Learner and author result views
share the same released-result renderer. Empty history/report pages, loading
status announcements, explicit errors and retry/back links are provided.

Participation/completion denominators are distinct assigned learners across the
quiz's publications: at least one started/finalized attempt respectively.
Submitted and expired are separate persisted completion reasons. Score summaries
are per finalized attempt, never a learner's best attempt. The UI labels the
mean as equally weighted attempt percentages among **released finalized
attempts**, and shows both the total finalized count and the withheld count.
An empty released-score denominator yields no mean, not zero. In-progress rows
never enter score aggregates, even after scheduled availability end.
Summary counters, score aggregates and the learner page share a repeatable-read
snapshot within the summary HTTP request.

Each attempt's pinned release policy is applied to history score, report score
rows, aggregate score membership and submission score/key/explanation projections
at current database time. The author submission view does not bypass release.
R01's result projector is shared rather than sending private question objects or
Grades to the web and hiding them. Saved selected answers/unanswered responses
are distinct from released correctness/points; item outcomes remain gated with
answer-key release. CSV/cohort/distribution analytics and manual grading/regrade
controls remain excluded.

### Evidence map and index observations

| Evidence | R02 coverage |
| --- | --- |
| `postgres/tests/test_reporting.py` | Summary/history/detail identity and Grade agreement; two publications/multiple starts; idle assigned learner; close/archive retention; cursor traversal; all 27 release combinations at end minus/at/plus one microsecond; expired/submitted and D04 snapshots; roles/owners/nested IDs/cursors/direct service calls; live revocation; no best or pooled-point mean |
| `postgres/tests/test_results.py` | Inherited R01 independent disclosure, zero score, exact release boundaries, finalization and frozen snapshot regression |
| `postgres/tests/test_app.py`, `test_http_contract.py`, `test_contract_schemas.py`, contract-tool consumer | Implemented route inventories, fresh generated contracts, strict error/schema and typed discriminated score contracts |
| `frontend/quezo/tests/navigation.test.tsx` | Loading announcements, explicit unfinished/withheld/released-zero states, shared independent R01 withheld rendering |
| `tests/e2e/reporting.spec.ts` | Three actual-provider browser cases: released/withheld multi-version reporting and learner navigation; persisted Grade cross-checks; finalized response outcomes; author guessed-ID denial; empty/error/retry and 26-attempt pagination |

`test_reporting_query_plans_reuse_existing_scoped_indexes` runs
`EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` against migrated PostgreSQL using
history, quiz/assignment-attempt join and finalized question/Grade-item reads.
Its tiny synthetic fixture is deliberately not a load benchmark. A separate
transaction-local `enable_seqscan=off` probe demonstrates eligibility of
`attempts_learner`, `assignments_quiz`, the assignment/attempt-number unique
index and `grade_items_attempt`; it is not an application setting or evidence
that a natural planner must always select them. Natural planner observations
and executed checks are recorded below. Existing primary/unique/relationship
indexes support these scoped reads; no new index, migration, backfill, privilege
change or Grade/timing/publication rewrite is introduced. Head remains
`0012_delivery_controls`; normal reviewed forward recovery procedures remain
unchanged.

### Executed checks

Executed 27 October 2026 on Windows, Node 24.20.0, Python 3.12.10,
PostgreSQL 17.11, locked Playwright 1.64.1/Chromium. Python checks used newly
owned disposable local PostgreSQL projects and the existing isolated-database
helpers. A session-only wrapper supplied random test-role secrets and a loopback
control URL, ran the commands below from the repository root using the locked
backend interpreter, and removed only its owned service/network in `finally`.
Browser checks used the existing guarded launcher, new isolated database/realm
and actual Keycloak 26.4.7. All owned services, contexts, pools and networks were
cleaned up. No development data/volumes or credentials were retained.

```powershell
python -m pytest -c postgres\pyproject.toml postgres\tests\test_reporting.py postgres\tests\test_results.py postgres\tests\test_app.py postgres\tests\test_contract_schemas.py postgres\tests\test_http_contract.py -s --tb=short
python -m pytest -c postgres\pyproject.toml postgres\tests\test_reporting.py -k query_plans -s --tb=short
npm run typecheck
npm run test:web
npm run api:generate
npm run api:check
node --test postgres\scripts\test_contract_tools.mjs
npm run test:e2e -- --grep "R02|R01 AT-12|D04"
uv run --directory postgres --locked alembic heads
git diff --check
```

| Check | Final result |
| --- | --- |
| Focused Python/API/contracts command | 171 passed in 389.58 seconds, including all 37 R02 cases |
| Sanitized query-plan observation rerun | 1 passed, 36 deselected in 7.58 seconds |
| `npm run typecheck` | Passed Next/TypeScript, strict mypy (96 sources), browser TypeScript |
| `npm run test:web` | 14 passed, including 2 new reporting/loading/render cases |
| Contract generation/freshness | OpenAPI and generated TypeScript current; no hand-edited generated schemas |
| Contract-tool/client checks | Both passed, including new reporting consumer, protected-score narrowing and nested-ID typing assertions |
| Focused browser command | Production build and all 7 cases passed: 3 R02, 3 R01, 1 D04; zero failures/timeouts/skips/interruptions |
| Alembic head | Unchanged single head `0012_delivery_controls` |
| Diff whitespace check | Passed |

Final browser R02 durations were 8.138 seconds (released), 7.622 seconds
(withheld), and 12.596 seconds (pagination/empty/error recovery), on owned project
`quezo-i02-5520f51a6795`. These are observed test times, not product thresholds.
In the tiny representative plan fixture (one assigned learner/attempt, two
questions), natural history used `attempts_learner`, the assignment identity
unique index and `grades_attempt_id_key` (Limit/Nested Loop; 0.117 ms).
The quiz join used `assignments_quiz` plus an attempts sequential scan/Hash Join
(0.044 ms). Finalized item inspection used `grade_items_attempt` and the
attempt-question relationship unique index followed by Sort (0.035 ms).
The separate index-eligibility probe also passed for the existing
assignment/attempt-number unique index. These are local planner observations,
not a load benchmark, numeric gate or proof of a larger-data plan.

Intermediate failures were corrected and are not acceptance evidence: the first
API fixture assumed unlimited attempts instead of the default single start; a
tiny-plan assertion incorrectly required a specific join index; route inventories
and an exported schema were stale during iteration. Browser iteration exposed an
ambiguous alert locator (now scoped to the main landmark), a strict optional-prop
type error in the shared renderer refactor (now explicitly nullable), and a
pagination test collecting DOM text before the destination rows arrived (now
awaiting the expected persisted IDs and row count). The final commands above
passed after those corrections; no product timeout or disclosure boundary was
relaxed.

The full unfiltered browser suite, `--checks` umbrella, hosted matrix, larger-data
performance/load checks and screen-reader/WCAG review were not run for R02.
Those are not claimed here. R02 scope is ready for B.C.'s integration/review,
not tracker acceptance or permission to dispatch a successor.

## Phase 2 completion and remaining review gates

C01 is accepted and integrated at `e66f459`; C02 is accepted and integrated
at `03797bc` (PR #9), verified in D01's checkout on 22 October 2026.
D01 is accepted and integrated at `b5751a9` (PR #10), as confirmed by B.C.
on 22 October 2026. B.C. also confirmed D02 at `c7d6f7e` (PR #11) and
S01 at `c9448f7` (PR #12) complete, accepted and integrated, and directed D03
execution after updating the tracking records. On 23 October, B.C. confirmed
D03 reviewed/integrated at `0cfbff7` (PR #13) and directed R01 execution after
recording D03 acceptance. R01 is now accepted/integrated at `8976371` (PR #14);
B.C. directed T01 execution after reconciliation on 23 October, then requested
milestone acceptance/tracking. T01 is accepted at `df06ccc` (PR #15), closing
Phase 2. C03 is subsequently accepted/integrated at local dev `2eba9eb`, head
`0010_author_workspace`, on 27 October. At A01's implementation checkpoint its
head was `0011_account_administration` and tracker acceptance remained pending
B.C.'s integration/review. B.C.'s subsequent D04 consumer-baseline and exclusive
window confirmation is recorded above without changing tracker acceptance;
R02 is not dispatched. The exact local Keycloak
permissions were recorded and verified before privileged implementation. B.C.
owns integration/review/merge and serializes shared-file/contract/migration
windows. Each later consumer must
first verify its own integrated producer
evidence in the backlog. The [Phase 2 prompts](implementation/PHASE-2-HANDOFFS.md)
are now historical; [Phase 3 packages](implementation/03-COMPLETE-P0.md) record
C03 complete and the remaining three prepared, not active.
Preserve `Database.transaction`, live actor checks, generated client/error
conventions, the I02 fixtures and secret-safe browser reporting.

The [approved demo defaults](SOFTWARE-SPECIFICATION.md#phase-2-assignment-and-demo-defaults)
originally kept learner interaction untimed pending D04. D04 now supplies the
[27 October approved timing approach](SOFTWARE-SPECIFICATION.md#c03-acceptance-and-phase-3-approvals-27-october-2026)
for explicit new starts, without changing old assignments or attempts.
Backend deadline/release
boundary tests and controlled expired-attempt fixtures are still required;
they do not establish timed UX acceptance. No automatic database retry policy
or performance gates are approved under DEC-08. Remaining Phase 3 work needs
separate explicit dispatch; real data/pilot/release approvals remain held.

Read [scope](PROTOTYPE-SCOPE.md), [architecture](PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md)
and the [software specification](SOFTWARE-SPECIFICATION.md) for behavior and
decision approvals. Select only an explicitly assigned, dependency-ready item
from the [implementation backlog](implementation/BACKLOG.md). Follow its phase
package and [agent handoff](implementation/AGENT-HANDOFF.md), including required
real migrations, identity, contracts, UI and tests.
Do not confuse a green scaffold check with P0 delivery or pilot readiness.
