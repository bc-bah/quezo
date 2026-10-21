# Quezo

A standalone assessment workspace for creating, delivering, and reviewing quizzes.

**Status: working foundations through I02 complete; Phase 2 assigned.** The agreed prototype scope is
single-organization, low-stakes assessment covering the PRD's P0 requirements.
PostgreSQL infrastructure, shared contracts, web sessions and backend identity
are integrated and the real-browser identity gate is accepted. EX-I02-01 is closed.
All eight Phase 2 packages are active assignments; only C01/S01 can implement
immediately. C01 adds author-owned banks and versioned objective questions for
review; quiz delivery and later gates remain outside this slice.

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
for requirement IDs. The [Phase 2 assignment/defaults](docs/SOFTWARE-SPECIFICATION.md#phase-2-assignment-and-demo-defaults)
defines current decisions and remaining holds. B.C. owns integration and the
backlog. Use the [eight copy-ready prompts](docs/implementation/PHASE-2-HANDOFFS.md);
active assignment does not waive a consumer's integrated-producer gate.

The supplied product ideation documents are preserved in [docs/reference](docs/reference/00-Start-Here.md)
as unmodified source material, not approved specifications or executable agent
instructions. [CONTEXT.md](CONTEXT.md) defines assessment terminology.

## Development scaffold

```text
frontend/quezo/          Next.js sessions, OIDC facade, navigation and author forms
postgres/               Python + FastAPI + Uvicorn; identity and question authoring
postgres/src/quezo_api/  Application, identity and question modules
postgres/tests/         Database, identity, question and HTTP contract checks
postgres/migrations/    Ordered foundation, session, identity and question migrations
tests/e2e/              Real-browser identity and versioned-question journeys
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

Open `http://localhost:3000`, sign in as a provisioned author and choose
**Manage question banks** to create, edit and select exact MCQ/true-false revisions.
`http://localhost:4000/health/live` remains process-only liveness. FastAPI's local
`/docs` and `/openapi.json` describe implemented identity/question contracts.
Quiz composition, delivery and grading are not implemented by C01.

```powershell
npm run typecheck
npm test
npm run build
```

The root scripts are convenience wrappers: `typecheck` checks both languages,
`test` runs web checks and pytest, and `build` builds only Next.js. Python runs directly through
Uvicorn; there is no backend JavaScript build.

See [development setup](docs/DEVELOPMENT.md) for optional local infrastructure,
configuration, checks, and the Phase 2 assignments.
