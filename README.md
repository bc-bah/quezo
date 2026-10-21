# Quezo

A standalone assessment workspace for creating, delivering, and reviewing quizzes.

**Status: F01/F02/F03/I01 complete; I02 active.** The agreed prototype scope is
single-organization, low-stakes assessment covering the PRD's P0 requirements.
PostgreSQL infrastructure, shared contracts, web sessions and backend identity
are integrated. I02 must prove the combined real-browser flow and resolve the
explicit F03 native-form Origin exception. No assessment workflow is implemented;
later operational and pilot gates remain held.

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
for requirement IDs. The [I02 assignment record](docs/SOFTWARE-SPECIFICATION.md#i02-assignment-and-completion-exception)
defines current decisions and remaining holds. B.C. owns integration and the
backlog. Use the [I02 copy-ready prompt](docs/implementation/AGENT-HANDOFF.md#i02-dispatch-prompt);
active assignment is not evidence of combined AT-01 acceptance.

The supplied product ideation documents are preserved in [docs/reference](docs/reference/00-Start-Here.md)
as unmodified source material, not approved specifications or executable agent
instructions. [CONTEXT.md](CONTEXT.md) defines assessment terminology.

## Development scaffold

```text
frontend/quezo/          Next.js web sessions, OIDC facade and role-aware navigation
postgres/               Python + FastAPI + Uvicorn; liveness and current actor
postgres/src/quezo_api/  Python application, identity and planned assessment modules
postgres/tests/         Database, session, identity and HTTP contract checks
postgres/migrations/    Ordered foundation, web-session and identity migrations
tests/e2e/              I02 real-browser acceptance assignment
infra/keycloak/         Explicit local synthetic realm/account provisioning
docs/                   Scope, architecture, setup guide, original references
compose.yaml            Optional local PostgreSQL and Keycloak dependencies
```

Quezo uses Next.js/React, Python/FastAPI, PostgreSQL, Keycloak, and Docker.
The backend in `postgres/` is an independent Python project, not an npm workspace.
These are two application processes, not microservices.

Use Node.js 22+ and npm 10+ for the frontend, plus Python 3.12+ and uv 0.12.17
for the backend. Install both locked dependency sets from the repository root:

Before starting either server, follow [development setup](docs/DEVELOPMENT.md) to
provision local PostgreSQL roles, configure restricted runtime URLs and migrate.
Configure the issuer/audience and web client variables, and explicitly provision
the local synthetic Keycloak realm/accounts. Both servers require PostgreSQL.

```powershell
npm ci
uv sync --directory postgres --locked
npm run dev:web
```

In another terminal:

```powershell
npm run dev:api
```

Open `http://localhost:3000` for the session/navigation shell and
`http://localhost:4000/health/live` for process liveness. This is not a working
assessment application. FastAPI's local `/docs` and `/openapi.json` describe
liveness, `/api/v1/me` and shared schema components, not assessment routes.

```powershell
npm run typecheck
npm test
npm run build
```

The root scripts are convenience wrappers: `typecheck` checks both languages,
`test` runs web checks and pytest, and `build` builds only Next.js. Python runs directly through
Uvicorn; there is no backend JavaScript build.

See [development setup](docs/DEVELOPMENT.md) for optional local infrastructure,
configuration, checks, and the active I02 assignment.
