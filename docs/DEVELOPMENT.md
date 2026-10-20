# Development scaffold

## What is and is not available

The scaffold contains a Next.js/TypeScript npm workspace and an independent
Python/FastAPI backend with a typed liveness endpoint, generated OpenAPI, pytest
checks and strict mypy configuration. Optional Docker dependencies and separate
frontend/backend CI jobs are included. It does not implement any PRD feature.

Authentication, database connectivity, schemas/migrations, business routes,
background expiration, grading, real readiness checks, application containers,
and deployment are intentionally absent. Starting Keycloak/PostgreSQL does not
wire either into the applications.

## Prerequisites and startup

Use Node.js 22+ and npm 10+ for the frontend, plus Python 3.12+ and
[uv](https://docs.astral.sh/uv/getting-started/installation/) 0.12.17 for the backend.
`.nvmrc` selects Node 22 and `postgres/.python-version` selects Python 3.12.
CI covers Node 22/24 and Python 3.12/3.14 in independent jobs. Docker with Compose
is only needed for optional dependencies. Commands work directly on Windows and
Linux; no Bash shell or manual virtual-environment activation is required.

From the repository root:

```powershell
npm ci
uv sync --directory postgres --locked
npm run dev:web
```

In a second terminal:

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
uv run --directory postgres --locked uvicorn --app-dir src quezo_api.app:create_app --factory --host 127.0.0.1 --port 4000 --no-server-header --reload
```

## Checks and starting without reload

```powershell
npm run typecheck
npm test
npm run build
```

`typecheck` runs Next.js route type generation/TypeScript checks and strict mypy
over Python application and test sources. `test` runs pytest through uv. FastAPI's
in-process test client checks the exact liveness response, absent product/readiness
routes, and generated OpenAPI. These checks do not establish assessment acceptance.
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

## Optional local dependencies

Copy the example at the repository root:

```powershell
Copy-Item .env.example .env
```

Use `cp .env.example .env` in Bash. Fill both password values with distinct
local-only credentials. Compose validates interpolations even for inactive
profiles, so both passwords are required even when only PostgreSQL is started.
There are no committed functional credentials.

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

| Variable | Purpose |
| --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER` | Local database/bootstrap owner (both default to `quezo`) |
| `POSTGRES_PASSWORD` | Required local database password |
| `POSTGRES_PORT` | Host port; default 5432 |
| `KEYCLOAK_ADMIN` | Local bootstrap administrator name |
| `KEYCLOAK_ADMIN_PASSWORD` | Required local bootstrap password |
| `KEYCLOAK_PORT` | Host port; default 8080 |

The root `.env` is for Compose only; neither application shell loads it.
Uvicorn receives its host/port/reload options from the startup command. Database
URLs and OIDC secrets are not declared until they have an actual consumer, and
must never use `NEXT_PUBLIC_` variables. Do not enable a fake login or
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

## Review stop and next implementation step

Review [scope](PROTOTYPE-SCOPE.md) and [architecture](PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md),
especially proposed assignment, timing, grading, disclosure and identity rules.
Use the [software specification](SOFTWARE-SPECIFICATION.md) for detailed behavior
and decision approvals, then select an explicitly assigned, dependency-ready item
from the [implementation backlog](implementation/BACKLOG.md). Follow its phase
package and [agent handoff](implementation/AGENT-HANDOFF.md), including required
real migrations, identity, contracts, UI and tests.
Do not confuse a green scaffold check with P0 delivery or pilot readiness.
