# Development setup

## What is and is not available

The scaffold contains a Next.js/TypeScript npm workspace and an independent
Python/FastAPI backend with a typed liveness endpoint, generated OpenAPI, pytest
checks and strict mypy configuration. F01 adds real PostgreSQL connectivity,
ordered migrations, restricted database roles and isolated database tests.
Separate frontend/backend CI jobs are included. No assessment feature is implemented.

Authentication, domain schemas, business routes,
background expiration, grading, real readiness checks, application containers,
and deployment are intentionally absent. Keycloak is not wired into either
application. Database configuration is required for backend lifespan startup.

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
export `QUEZO_DATABASE_URL` using the restricted runtime identity, then:

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
no `/health/ready` or `/api/v1` routes. FastAPI exposes local interactive docs at
`http://localhost:4000/docs` and the generated contract at
`http://localhost:4000/openapi.json`; only liveness is described. This is not the
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
uv run --directory postgres --locked uvicorn --app-dir src quezo_api.app:create_app --factory --loop quezo_api.database:database_loop_factory --host 127.0.0.1 --port 4000 --no-server-header --reload
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
over Python application and test sources. `test` runs pytest through uv. FastAPI's
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
These are local-only shells, not a production deployment. Build output, virtual
environments, Python bytecode and test/type-check caches are ignored by Git.
No linting tool or browser test runner is selected yet; add them deliberately
with the approved implementation conventions.

## Local database and optional identity dependency

Copy the example at the repository root:

```powershell
Copy-Item .env.example .env
```

Use `cp .env.example .env` in Bash. Fill `POSTGRES_PASSWORD`,
`QUEZO_MIGRATION_PASSWORD`, `QUEZO_RUNTIME_PASSWORD` and `KEYCLOAK_ADMIN_PASSWORD`
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
`quezo_migrator` and `quezo_runtime` and restricts database access. Initialization
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
data, separate credentials and no development volume. Populate the three
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

## Approved first wave and remaining review gates

B.C. approved the [scoped G00 baseline](SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026)
on 20 October 2026. F01 is active under B.C. for synthetic-data development;
F02 remains ready and undispatched.
Use their [prepared handoff prompts](implementation/AGENT-HANDOFF.md#4-approved-first-wave-prompts);
B.C. owns integration and review, and moves each item to `active` at dispatch.
F01 persistence tools are locked in the backend manifest; F02 contract tools
are not installed by this package.
Identity/session implementation and later gates remain held.

Read [scope](PROTOTYPE-SCOPE.md), [architecture](PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md)
and the [software specification](SOFTWARE-SPECIFICATION.md) for behavior and
decision approvals. Select only an explicitly assigned, dependency-ready item
from the [implementation backlog](implementation/BACKLOG.md). Follow its phase
package and [agent handoff](implementation/AGENT-HANDOFF.md), including required
real migrations, identity, contracts, UI and tests.
Do not confuse a green scaffold check with P0 delivery or pilot readiness.
