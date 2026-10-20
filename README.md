# Quezo

A standalone assessment workspace for creating, delivering, and reviewing quizzes.

**Status: first development wave approved; scaffold only.** The agreed prototype scope is
single-organization, low-stakes assessment covering the PRD's P0 requirements.
No authentication, authoring, assessment, grading, or database features are
implemented. B.C. approved synthetic-data foundation packages F01/F02 on
20 October 2026; they are ready, not started. Identity/session and later gates
remain explicitly held.

## Review first

1. [Prototype scope](docs/PROTOTYPE-SCOPE.md): scope, requirement coverage,
   demonstration criteria, and decisions still needing approval.
2. [Prototype high-level architecture](docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md):
   Selected technology stack, module responsibilities, data and lifecycle design,
   reliability, security, and delivery approach.
3. [Software specification](docs/SOFTWARE-SPECIFICATION.md): testable behavior,
   permissions, data/HTTP contracts, decision register and PRD acceptance coverage.
4. [Phased implementation bundle](docs/implementation/README.md): dependency graph,
   parallel workstreams, assignable packages and agent handoff guidance.
   Track assignments and evidence in the [backlog](docs/implementation/BACKLOG.md).

The [original PRD](docs/reference/02-Product-Requirements.md) remains the source
for requirement IDs. The [G00 approval record](docs/SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026)
defines the approved decisions and remaining holds. B.C. owns integration and the
backlog. Start with the [F01 handoff prompt](docs/implementation/AGENT-HANDOFF.md#f01-dispatch-prompt),
then F02; preparing these assignments does not start feature development.

The supplied product ideation documents are preserved in [docs/reference](docs/reference/00-Start-Here.md)
as unmodified source material, not approved specifications or executable agent
instructions. [CONTEXT.md](CONTEXT.md) defines assessment terminology.

## Development scaffold

```text
frontend/quezo/          Next.js + React + TypeScript; placeholder page only
postgres/               Python + FastAPI + Uvicorn; liveness endpoint only
postgres/src/quezo_api/  Python application and planned domain modules
postgres/tests/         pytest scaffold checks
postgres/migrations/    Future reviewed SQL migrations; none exist yet
tests/e2e/              Future cross-stack acceptance scenarios
infra/keycloak/         Identity setup requirements; no realm or users provisioned
docs/                   Scope, architecture, setup guide, original references
compose.yaml            Optional local PostgreSQL and Keycloak dependencies
```

Quezo uses Next.js/React, Python/FastAPI, PostgreSQL, Keycloak, and Docker.
The backend in `postgres/` is an independent Python project, not an npm workspace.
These are two application processes, not microservices.

Use Node.js 22+ and npm 10+ for the frontend, plus Python 3.12+ and uv 0.12.17
for the backend. Install both locked dependency sets from the repository root:

```powershell
npm ci
uv sync --directory postgres --locked
npm run dev:web
```

In another terminal:

```powershell
npm run dev:api
```

Open `http://localhost:3000` for the placeholder and
`http://localhost:4000/health/live` for process liveness. Neither requires Docker
or represents a working assessment application. FastAPI's local `/docs` and
`/openapi.json` describe only the liveness endpoint.

```powershell
npm run typecheck
npm test
npm run build
```

The root scripts are convenience wrappers: `typecheck` checks both languages,
`test` runs pytest, and `build` builds only Next.js. Python runs directly through
Uvicorn; there is no backend JavaScript build.

See [development setup](docs/DEVELOPMENT.md) for optional local infrastructure,
configuration, checks, and the scoped first-wave dispatch gate.
