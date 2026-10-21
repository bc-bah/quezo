# Development setup

## What is and is not available

The scaffold contains a Next.js/TypeScript npm workspace and an independent
Python/FastAPI backend with a typed liveness endpoint, generated OpenAPI, pytest
checks and strict mypy configuration. F01 adds real PostgreSQL connectivity,
ordered migrations, restricted database roles and isolated database tests.
Separate frontend/backend CI jobs are included. No assessment feature is implemented.
F02 adds strict HTTP DTOs, sanitized errors, server-generated correlation IDs,
bounded request bodies and a generated TypeScript client for implemented routes.

F03 adds server-only OIDC and durable web sessions with navigation. I01 adds
independent JWT validation, live application authorization and `/api/v1/me`.
Explicit local synthetic provisioning is required; sign-in never grants access.

Domain schemas, business routes,
background expiration, grading, real readiness checks, application containers,
and deployment are intentionally absent. A configured local Keycloak can be
used by the web OIDC adapter; combined Keycloak/browser/backend acceptance is
I02, not established by F03 protocol tests. Database configuration is required
for both server lifecycles.

## Prerequisites and startup

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
no `/health/ready` or assessment routes. FastAPI exposes local interactive docs at
`http://localhost:4000/docs` and the generated contract at
`http://localhost:4000/openapi.json`; liveness and `GET /api/v1/me` are implemented.
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
dependency outage into an authenticated session. The second-wave DEC-06/07
approval selects openid-client + pg for F03. There is deliberately no
`/api/v1/me` route in F02.

**Pagination:** use `Annotated[PaginationParams, Query()]` for collection query
inputs: `pageSize` defaults to 25 and accepts 1-100, `cursor` defaults to null.
Only decimal integer query strings are parsed; fractions, booleans, negatives,
null sizes and extra fields fail validation. `Page[T]` responses contain
`items` and a required `nextCursor`, explicitly null when exhausted. A future
collection producer owns cursor encoding/validation and server-side filters;
it must use stable ordering with a unique-ID tiebreaker and apply authorization
before pagination. No list route, cursor algorithm or generic persistence layer
is implemented here. Concrete page schemas are generated when real routes use them.

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

F03 can rely on the integrated actor and generated types under B.C.'s second-wave
approval; I01 remains separately dispatched. S01 can reuse UUID and strict
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

**Review boundary:** F02 remains `active` in the backlog and is returned as ready
for B.C.'s review, not accepted/done. No commit, pull request, successor work,
external provisioning, deployment or real-data use was performed.

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
accepts integrated F01/F02 and dispatches F03, with B.C. owning integration,
review and the exclusive shared-file window. I01 is not dispatched by this work;
later approval gates remain held. The historic F01/F02 evidence above is unchanged.

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

F03 is returned **ready for B.C.'s review**, not done or integrated. No automatic
commit/PR, successor launch, external provisioning or deployment is performed.

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
addition to its restricted `QUEZO_DATABASE_URL`. Issuer must be an exact
Keycloak realm URL without trailing slash, credentials, query or fragment;
HTTPS is required except for loopback HTTP. The defaults used by the local
realm/F03 web configuration are `http://localhost:8080/realms/quezo-local`
and `quezo-api`. Neither the API nor web receives Keycloak admin credentials.
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

I01 is returned **ready for B.C.'s review**, not done. The tracker remains active;
B.C. owns review, accepted integration and final status updates.

## I02 integrated browser gate

### Review handoff: 20 October 2026

**Work item:** I02, Integrated login and access gate.

**State:** ready for B.C.'s review, not accepted/done. EX-I02-01 closure remains
B.C.'s decision. The final local combined command exited 0 with all 16 browser
cases passing, no skipped cases, and owned-resource cleanup completed.

**Changes:** `tests/e2e/` supplies locked Playwright configuration, reusable
synthetic login/application fixtures, real-browser scenarios and a
secret-safe reporter/runbook. `postgres/tests/run_browser.py` owns isolated
Compose/provisioning/migration/startup/cleanup, with focused launcher tests.
Root manifests/lock/scripts and one non-matrix CI browser job connect the suite.
The approval/checkpoint documents were reconciled only after B.C.'s explicit
permission in this session; I02 remains active for the human review boundary.

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

## Remaining review gates

Read [scope](PROTOTYPE-SCOPE.md), [architecture](PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md)
and the [software specification](SOFTWARE-SPECIFICATION.md) for behavior and
decision approvals. Select only an explicitly assigned, dependency-ready item
from the [implementation backlog](implementation/BACKLOG.md). Follow its phase
package and [agent handoff](implementation/AGENT-HANDOFF.md), including required
real migrations, identity, contracts, UI and tests.
Do not confuse a green scaffold check with P0 delivery or pilot readiness.
