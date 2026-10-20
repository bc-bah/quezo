# Coding-agent handoff

Use this document when assigning or completing a package from
[BACKLOG.md](BACKLOG.md). It is an on-demand execution guide, not an instruction
to launch agents or implement the entire backlog.

## 1. Coordinator preparation

Select a dependency-ready package; verify its decisions and integrated input
contracts, then assign its owner and permitted file surfaces. Use a separate
worktree/session for each concurrent package. Agree shared-file edits with the
integration owner before dispatch, particularly quiz settings/composition,
migrations, generated contracts, lockfiles and root application wiring.

Provide the agent with:

```text
Implement Quezo work item <ID>: <title>.

Read:
- docs/implementation/BACKLOG.md: this row and all listed prerequisites.
- docs/implementation/<phase-file>.md: this package only.
- docs/SOFTWARE-SPECIFICATION.md: <named rules and acceptance IDs>.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: <relevant sections>.
- docs/DEVELOPMENT.md and the current manifest scripts for setup/checks.

Approved decisions: <DEC IDs, approval references and any amendments>.
Integrated prerequisites: <commit/PR references>.
Permitted surfaces: <paths>; shared-file owner: <name/contact>.
Required input contracts: <schema/model/endpoint references>.

Deliver the package's complete acceptance criteria and relevant tests.
Use real auth/persistence/browser integration wherever its criteria require it.
Preserve all excluded scope and the agreed synthetic-data boundary.
Escalate incompatible contracts, unapproved behavior, or out-of-scope file needs.

Stop after this package and return the handoff format below.
Do not start successors, create external resources, or deploy without a separate
explicit assignment. PR/commit instructions, if any: <coordinator supplies>.
```

Replace every placeholder before dispatch. An unavailable approval or prerequisite
is a blocker to resolve, not something to ask the agent to invent. A consumer may
use schema-validated fixtures for development, but its final acceptance still
requires the actual producer integration.

## 2. Assignee execution

1. Confirm the live tracker, approved decisions, workspace state and input
   contracts match the assignment. Report any mismatch before changing behavior.
2. Implement only the assigned vertical slice. Keep domain rules inside the
   owning module; update the server schema and regenerate clients when interfaces
   change. Coordinate shared files and migration ordering.
3. Run the existing relevant checks plus the acceptance tests the package adds.
   Record commands, environment and outcomes; distinguish automated results,
   manual observations and unverified requirements.
4. Review every assigned acceptance ID. A failed/unverified item remains open.
   Return implementation and evidence to the coordinator for integration.

Use the repository's current scripts rather than installing a second toolchain
or inventing test commands that do not exist. Add missing feature tests/tooling
only as the assigned package calls for them. Treat authentication or database
substitutes as test fixtures, never silent runtime fallbacks.

## 3. Handoff format

```text
Work item: <ID>
State: ready for review | blocked
Changes: <behavior and relevant file paths>
Requirement coverage: <SRS rules and PRD IDs>
Acceptance: <each assigned AT ID, scenarios covered, result/evidence link>
Checks: <exact commands, environment and outcomes>
Contracts: <new/changed endpoints, schemas, generated-client updates>
Data: <migration IDs, clean/upgrade results, recovery implications>
Integration: <commit/PR, prerequisites used, shared-file coordination>
Known gaps: <unverified criteria, failures, decisions needed; "none" only if true>
Successor handoff: <what dependent packages can now rely on>
```

The agent reports readiness for review; it does not declare user acceptance or
pilot readiness. The coordinator records integration and updates the tracker.
Retain evidence in repository tests/runbooks or approved CI/PR artifacts; keep
raw logs, credentials and assessment payloads out of committed documents.

## 4. Approved first-wave prompts

**Approval:** B.C., 20 October 2026; see the
[G00 approval record](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026).
These are prepared assignments, not evidence that agents have started. B.C. owns
both packages, integration and acceptance review. Use one prompt per session.
The execution checkout must contain this approval/tracker update before dispatch;
a session created from an older default branch must first receive that baseline.
Do not treat an unavailable approval record as an integrated prerequisite.

Default dispatch order is **F01, then F02**, integrating the accepted F01 result
before starting the second session so shared files have a single writer. F02
does not logically depend on F01: B.C. may instead authorize concurrent execution
with explicit, non-overlapping write windows for manifests/locks, CI, root scripts,
application wiring and shared docs. Neither prompt grants that concurrency.
B.C. moves the selected backlog row from `ready` to `active` before dispatch and
records the execution baseline commit/PR when available. Agents return the section 3
handoff; B.C. records `review`, then `done` only after accepted integration.

### F01 dispatch prompt

```text
Implement Quezo work item F01: Database and integration-test foundation.

Read:
- docs/implementation/BACKLOG.md: F01, prerequisite G00 and current dispatch state.
- docs/implementation/01-FOUNDATIONS.md: G00 approval outcome and F01 only.
- docs/implementation/README.md: integration rules and definition of ready/done.
- docs/SOFTWARE-SPECIFICATION.md: section 2 including the dated G00 approval,
  section 6, QUAL-01/04/05 and the acceptance catalogue for evidence mapping.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: sections 2-5, 7 and 10-11.
- docs/DEVELOPMENT.md, postgres/migrations/README.md and current manifest scripts.
- docs/implementation/AGENT-HANDOFF.md: execution rules and section 3 return format.

Owner, integration owner and reviewer: B.C.
Approved decisions: B.C.'s 20 October 2026 G00 record approves DEC-01 through
DEC-05 as written and the F01/F02 portion of DEC-07. Use Psycopg 3 async/pooling
and Alembic with SQLAlchemy Core, no ORM. Select compatible versions, verify them
against the repository's supported Python versions and lock them using uv.
DEC-06, DEC-07 session storage implementation and later DEC-08 through DEC-11
commitments remain held. Do not implement identity, sessions or later packages.
Integrated prerequisites: G00 is a document approval, recorded in the
specification and backlog; there is no engineering producer dependency.
Verify those records exist in this checkout and F01 is active under B.C.
If absent or stale, stop and report the mismatch rather than inferring approval.

Permitted surfaces:
- postgres/ persistence/configuration code, migration configuration,
  postgres/migrations/ and package-specific postgres/tests/ helpers/tests.
- Shared changes limited to F01 needs: postgres/src/quezo_api/app.py lifespan,
  postgres/pyproject.toml and postgres/uv.lock, compose.yaml, .env.example,
  .github/workflows/ci.yml, root package.json scripts and docs/DEVELOPMENT.md.
Shared-file owner: B.C.; use the exclusive F01 write window. If another package
is editing these files, stop shared-file edits and obtain B.C.'s coordination.
No frontend, identity/session or full assessment schema implementation.
Required input contracts: specification section 6 persistence invariants,
existing FastAPI application factory and process-only /health/live response.
There is no existing database/transaction interface; F01 produces it.

Deliver all F01 acceptance criteria:
- Environment-based real PostgreSQL configuration and a bounded connection
  lifecycle with shutdown cleanup; async requests must not block the event loop.
- Reviewed migration ordering/execution and restricted runtime versus migration
  identities; only foundational records needed by upcoming slices.
- Reusable transaction/test helpers, with no generic repository framework.
- An isolated real PostgreSQL test database with safeguards against accidentally
  targeting production or any non-test database, including destructive cleanup.
- Demonstrate clean migration, upgrade from the previous baseline, transaction
  rollback on failure, closed pools on shutdown and isolated database tests in CI.
  The initial scaffold has no migrations: document that baseline explicitly and
  demonstrate a real prior-revision upgrade path without inventing domain tables.
- Document setup, configuration, migration commands and test isolation.
  Database outages must fail explicitly; do not fall back to in-memory storage.

Run the current relevant checks, including
uv run --directory postgres --locked mypy
uv run --directory postgres --locked pytest
and the real migration/database checks introduced by F01. Run root/frontend
checks if shared changes affect them. Record exact commands and environment;
do not present skipped database checks as success. Preserve process-only
liveness and existing behavior outside the explicitly changed persistence setup.
Map evidence to QUAL-01/04/05 and F01's done criteria. AT-10/AT-15 remain only
partially supported by foundation evidence; do not claim end-to-end acceptance.

Use synthetic data and local/isolated test dependencies only. Preserve excluded
scope. Escalate incompatible contracts, unapproved behavior or out-of-scope files.
Stop after F01 and return the complete section 3 handoff format, including the
connection/transaction interface, migration rules and actual evidence.
Do not start successors, provision external resources, deploy or use real data.
Do not create a commit or PR automatically; return changes for B.C.'s review.
Report readiness for review, not done; B.C. owns tracker and integration updates.
```

### F02 dispatch prompt

```text
Implement Quezo work item F02: Contract and error foundation.

Read:
- docs/implementation/BACKLOG.md: F02, prerequisite G00 and current dispatch state.
- docs/implementation/01-FOUNDATIONS.md: G00 approval outcome and F02 only.
- docs/implementation/README.md: integration rules and definition of ready/done.
- docs/SOFTWARE-SPECIFICATION.md: section 2 including the dated G00 approval,
  sections 6-7, IAM-02, QUAL-02/04 and the acceptance catalogue for evidence mapping.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: sections 2-4, 8-9.
- docs/DEVELOPMENT.md and the current manifest scripts for setup/checks.
- docs/implementation/AGENT-HANDOFF.md: execution rules and section 3 return format.

Owner, integration owner and reviewer: B.C.
Approved decisions: B.C.'s 20 October 2026 G00 record approves DEC-01 through
DEC-05 as written and the F01/F02 portion of DEC-07. Use openapi-typescript for
generated TypeScript types and openapi-fetch for the typed client. Select
compatible versions and regenerate npm locks using the package manager.
Server Pydantic models/OpenAPI remain authoritative. Identity/session library
and storage implementation choices remain held under DEC-06/07; F02 may define
the shared actor DTO but must not implement authentication or fake business routes.
DEC-08 through DEC-11 later commitments remain held.
Integrated prerequisites: G00's approval record and backlog must exist in this
checkout; verify F02 is active under B.C. F01 is not a logical prerequisite.
Under the default sequential dispatch, use the integrated F01 baseline and
preserve its lifespan, persistence and CI changes. If approval, dispatch state
or the coordinated baseline is missing, stop and report the mismatch.

Permitted surfaces:
- postgres/src/quezo_api/ HTTP schema/error helpers, app handler wiring,
  package-specific postgres/tests/ and OpenAPI export tooling under postgres/.
- frontend/quezo/src/lib/api/ for generated types and typed-client integration.
- Shared changes limited to F02 needs: postgres/pyproject.toml and postgres/uv.lock,
  frontend/quezo/package.json, root package.json/package-lock.json,
  .github/workflows/ci.yml and docs/DEVELOPMENT.md.
Shared-file owner: B.C.; use the exclusive F02 write window. If another package
is editing shared files, stop those edits and obtain B.C.'s coordination.
Do not edit migrations, identity configuration or product UI.
Required input contracts: existing /health/live response, specification sections
6-7 wire/error/pagination conventions and IAM-02 actor roles/permissions.
No implemented /me or business endpoints exist; agree the actor/session DTO
shape with B.C. for later F03/I01 without fabricating endpoint implementations.

Deliver all F02 acceptance criteria:
- UUID/enums, camelCase serialization, safe validation/error envelopes,
  correlation IDs, pagination conventions and the shared actor shape.
- Consistent exception and validation handlers on real routes; no raw submitted
  secrets/content in errors or logs. Keep authorization out of generic middleware.
- Fixtures proving invalid payload/unknown-field rejection, safe dependency
  and internal errors, and the unchanged health contract. Test-only routes
  must not become fake-success production business endpoints.
- Reproducible OpenAPI export and typed-client generation/check commands
  against implemented endpoints; CI must detect stale generated output.
- Document the actor/error/schema conventions, exact generation/check commands
  and consumer handoff. Do not hand-edit generated types or duplicate server DTOs.

Run the current checks:
npm run typecheck
npm test
npm run build
plus the export/generation/drift checks and targeted error fixtures introduced
by F02. Record exact commands, environment and outcomes. Preserve any integrated
F01 database checks; if prerequisites for checks are unavailable, report that
explicitly rather than claiming success.
Map evidence to IAM-02 contract conventions, QUAL-02/04 and F02's done criteria.
Actor schemas/error tests alone do not establish AT-01 or full AT-15 acceptance.

Use synthetic data only and preserve all excluded scope. Escalate incompatible
contracts, unapproved behavior or out-of-scope file needs.
Stop after F02 and return the complete section 3 handoff format with schemas,
generated-client locations, commands, evidence and inputs for F03/I01/S01.
Do not start successors, provision external resources, deploy or use real data.
Do not create a commit or PR automatically; return changes for B.C.'s review.
Report readiness for review, not done; B.C. owns tracker and integration updates.
```
