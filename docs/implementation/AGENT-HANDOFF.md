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

**Historical assignments:** F01/F02 are now accepted and integrated. Do not
redispatch these prompts. Use [section 5](#5-active-second-wave-prompts) for the
current F03/I01 assignments; the original approval and execution instructions
below are retained as evidence of first-wave scope.

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

## 5. Active second-wave prompts

**Historical assignments:** F03 and I01 are now done; F03 has the explicit
[EX-I02-01 completion exception](BACKLOG.md#ex-i02-01-native-loginlogout-origin).
Do not redispatch these prompts. Use [I02](#i02-dispatch-prompt) below.
B.C. separately authorized coordination-record reconciliation during each
package's execution. Actual I01 execution followed integrated F03 PR #5
(`b1a2fe0`), retaining its schema/role boundaries and exclusive shared-file order.
The original prompts below preserve the approved scope, not current status.

B.C. explicitly assigned F03 and I01 on 20 October 2026 and approved the
[identity/session baseline](../SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01).
Both tracker rows are `active`; no further activation is required. No agent has
been launched by preparing these prompts. B.C. owns both packages and their
integration/review/merge. F01/F02 are done, with merged PRs and evidence in the
[backlog](BACKLOG.md).

The integrated producer baseline is `5f314125e13262139e1d3e28d190881d6fbd5f8b`.
Each execution checkout must also contain this second-wave approval/tracker update;
the producer commit alone predates it. Use one prompt per session.

**Default execution order:** F03 first, then I01 from the accepted F03 integration.
This serializes root scripts, CI, Compose, bootstrap, lockfiles, shared docs and
Alembic revisions; it does not add a logical dependency. F03 uses the approved
actor DTO and controlled test identities while I01 produces the real `/me` route.
I02 remains responsible for combined real-browser acceptance.

For parallel execution, B.C. must explicitly allocate non-overlapping shared-file
windows and migration ordering. Independent feature code can progress, but no
agent may guess revision IDs/parents or concurrently replace shared bootstrap,
fixtures or generated artifacts. Preserve applied revisions and test the single
integrated migration chain before acceptance.

### F03 dispatch prompt

```text
Implement Quezo work item F03: Web session and navigation foundation.

Read:
- docs/implementation/BACKLOG.md: F03 and its done prerequisites F01/F02.
- docs/implementation/01-FOUNDATIONS.md: F03 and the second-wave checkpoint.
- docs/implementation/README.md: shared-file rules and definition of done.
- docs/SOFTWARE-SPECIFICATION.md: second-wave approval, IAM-01/02, sections 6-8,
  QUAL-02/03 and AT-01 boundaries.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: sections 2-4 and 9.
- docs/DEVELOPMENT.md: F02 actor/error/client contract, F01 migration/test setup.
- postgres/migrations/README.md, infra/keycloak/README.md and current scripts.
- docs/implementation/AGENT-HANDOFF.md: section 3 return format and section 5.

Owner, integration owner and reviewer: B.C.
Assignment: F03 is active by B.C.'s explicit direction on 20 October 2026.
Approved decisions: DEC-06/07 second-wave approval selects openid-client for OIDC
and node-postgres (pg) for restricted PostgreSQL-backed server sessions.
Use a local Keycloak realm, confidential web client, exact redirects, code+PKCE,
state/nonce and a dedicated API audience. Keycloak owns identity; the backend
owns application role/status/ownership decisions on every protected request.
Choose compatible versions and lock via npm. B.C. authorizes documented,
bounded session/timeout defaults for review, not changes to business semantics.
No runtime Keycloak-admin credentials, auth bypass or automatic role grants.

Integrated prerequisites: F01 PR #3, merge 8732328; F02 PR #4, merge
5f314125e13262139e1d3e28d190881d6fbd5f8b. Verify these changes and the current
second-wave approval/tracker exist in this checkout. F01/F02 are done, not
blocked. The real /api/v1/me producer belongs to I01; do not implement it here.
Use controlled identities/schema-validated actor fixtures only in tests while
I01 is absent. Never enable a runtime fixture, fake session or outage fallback.

Permitted surfaces:
- frontend/quezo/ server-only OIDC/session/facade code, root layout/navigation,
  login/callback/logout and signed-out/expired/disabled/error presentation.
- Focused frontend session/navigation tests using repository conventions.
- Session-specific Alembic revision(s) and tests under postgres/migrations/
  and postgres/tests/, plus narrow bootstrap changes for the web runtime role.
- F03-only shared changes: frontend manifest, root package.json/package-lock.json,
  .env.example, compose.yaml, .github/workflows/ci.yml, shared test fixtures,
  postgres/bootstrap/roles.sql, test database bootstrap as needed,
  postgres/migrations/README.md and docs/DEVELOPMENT.md.
Shared-file owner: B.C. F03 has the first exclusive shared-file window.
Do not modify backend identity/business routes, F02 shared DTOs or existing
applied migrations. Escalate incompatible contracts or additional file needs.

Required input contracts:
- schemas.py Actor: userId UUID; roles array of administrator/author/learner
  (combined or empty); status active/disabled. No token, email or provider IDs.
- frontend/quezo/src/lib/api/client.ts and generated schema.d.ts; server models
  are authoritative. Consume the agreed actor shape until I01 exports /me;
  do not hand-edit generated output or invent an OpenAPI endpoint.
- Error envelope: code/message/requestId/details; preserve safe actionable
  backend errors. Transport/dependency failures are explicit, never signed-in.
- F01 migration head is 0002_runtime_grants. Use the actual integrated head
  when creating new revisions; one linear chain, migration-only credentials.
  quezo schema default grants belong to the backend and MUST NOT cover sessions.

Deliver all F03 acceptance criteria:
- Real server-side PostgreSQL session and login-transaction storage in a separate
  schema, with a restricted web runtime identity. Prove the web role cannot read
  assessment tables and quezo_runtime cannot access session secrets. Keep schema
  creation/privileged bootstrap out of application startup; do not use in-memory
  authoritative state. Bound and close the pg pool, including failed startup.
- Correct authorization-code callback, PKCE/state/nonce and replay rejection;
  exact redirect validation, session rotation/expiry and logout invalidation.
  Tokens remain server-only; opaque HttpOnly/SameSite cookies are Secure in shared
  environments. State-changing requests enforce CSRF/origin protection.
- A thin server-only backend facade, with no assessment rules in Next.js and no
  browser token storage. An actor snapshot in a session is not live authorization:
  consult backend /me/protected responses; never trust stale roles/status on outage.
- Keyboard-usable role-aware navigation and explicit signed-out, expired,
  disabled and error states; no assessment screens or administration UI.
- Tests for expiry/logout, callback replay, CSRF/origin denial, token redaction,
  durable sessions across process restart and database outages. Test storage and
  privilege boundaries against real PostgreSQL, not an in-memory substitute.
- Record clean migration and prior-baseline upgrade evidence and document exact
  session/configuration interfaces, timeout defaults, role provisioning and checks.
  If initial web tooling cannot exercise required behavior, add only focused
  test tooling needed for F03; combined Keycloak/browser acceptance stays in I02.

Run npm run typecheck, npm test, npm run build, npm run api:check,
npm run test:contracts and npm run test:db with required isolated dependencies,
plus the focused session/navigation/migration checks you add. Record exact
commands, environment and outcomes; missing prerequisites/skips are not passes.
Preserve F01 database lifecycle/isolation and F02 sanitized errors/client checks.
IAM-01 and QUAL-02/03 require package evidence; do not claim full AT-01 or WCAG
conformance from isolated F03 tests. I02 owns the real combined identity gate.

Use synthetic identities/data and local test dependencies only. Stop after F03
and return the complete section 3 handoff, including session/schema/role interface,
OIDC realm/client/audience/redirect requirements, defaults, tests and I01/I02 inputs.
Do not launch successors, create external resources, deploy, or use real data.
Do not create a commit or PR automatically; return changes for B.C.'s review.
Report ready for review or blocked with a specific reason, not done; B.C. owns
tracker updates and accepted integration.
```

### I01 dispatch prompt

```text
Implement Quezo work item I01: Identity and authorization backend.

Read:
- docs/implementation/BACKLOG.md: I01 and its done prerequisites F01/F02.
- docs/implementation/01-FOUNDATIONS.md: I01 and the second-wave checkpoint.
- docs/implementation/README.md: shared-file rules and definition of done.
- docs/SOFTWARE-SPECIFICATION.md: second-wave approval, IAM-01/02, identity
  portion of IAM-03, sections 6-7, QUAL-02/04 and AT-01.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: sections 2-5 and 9.
- docs/DEVELOPMENT.md: actor/error conventions and database/transaction interface.
- infra/keycloak/README.md, postgres/migrations/README.md and current scripts.
- docs/implementation/AGENT-HANDOFF.md: section 3 return format and section 5.

Owner, integration owner and reviewer: B.C.
Assignment: I01 is active by B.C.'s explicit direction on 20 October 2026.
Approved decisions: DEC-06/07 second-wave approval selects PyJWT with cryptography
and HTTPX for asynchronous JWT/JWKS integration. Follow the repository's existing
HTTPX package/import conventions when adding runtime dependencies; lock with uv.
Configure a dedicated local Keycloak realm, confidential web client using
code+PKCE/state/nonce, exact redirect/logout URIs and a dedicated API audience.
F03 uses openid-client and PostgreSQL sessions through pg. Application database
roles/status are authoritative on every protected request. Local provisioning
is explicit; no automatic grants and no runtime Keycloak-admin credentials.
B.C. authorizes bounded documented timeout/cache defaults for review, not
DEC-08 performance gates or weakened token validation.

Integrated prerequisites: F01 PR #3, merge 8732328; F02 PR #4, merge
5f314125e13262139e1d3e28d190881d6fbd5f8b. Verify these changes and the current
second-wave approval/tracker exist. The default shared-file sequence follows
accepted F03 integration: use that checkout baseline and its documented web
client/redirect/session requirements. F03 is not a logical package prerequisite;
parallel work requires B.C.'s explicit shared-file windows and migration order.
Do not overwrite F03 bootstrap, session grants or applied migrations.

Permitted surfaces:
- infra/keycloak/ synthetic realm/client configuration and local provisioning.
- postgres/src/quezo_api/modules/identity/ and package-specific authorization,
  token, provisioning and real-database tests under postgres/tests/.
- Identity Alembic revisions and minimal FastAPI router/lifespan wiring.
- I01-only shared changes: postgres/pyproject.toml and uv.lock, .env.example,
  compose.yaml, postgres/bootstrap/roles.sql, isolated test bootstrap/fixtures,
  root package.json and .github/workflows/ci.yml for required checks,
  postgres/migrations/README.md and docs/DEVELOPMENT.md.
- Regenerate postgres/openapi.json and frontend/quezo/src/lib/api/schema.d.ts
  using the existing scripts when /me is added; never hand-edit generated files.
Shared-file owner: B.C.; default exclusive I01 window follows F03 integration.
No frontend session/UI implementation, assessment modules or A01 admin UI.

Required input contracts:
- quezo_api.database.get_database and Database.transaction(): one bounded
  per-process pool; transaction commits only on successful context exit and
  rolls back on failure/cancellation. Pass the leased connection within atomic
  work; do not manually commit, retain it or open nested independent transactions.
- F02 Actor wire DTO: userId UUID, roles array of administrator/author/learner
  (combined or empty), status active/disabled. Resolve a current active actor,
  never authorize from a token role claim or a cached session actor alone.
- ApiModel aliases/validation and F02 error envelope code/message/requestId/details;
  reuse safe UNAUTHENTICATED, FORBIDDEN, ACCOUNT_DISABLED, NOT_FOUND and dependency
  errors as appropriate. Unknown/malformed identity must not become authenticated.
- F01 base head 0002_runtime_grants, or actual integrated head including F03.
  Keep a single migration chain and restricted migration/runtime identities.
  Identity tables belong in the backend quezo schema, not the web session schema.

Deliver all I01 acceptance criteria:
- Reproducible local realm/client/audience and synthetic test-account setup with
  no committed secrets, wildcards, auth bypass or bootstrap-admin application user.
  Keep Keycloak administration confined to explicit local provisioning; A01
  service privileges/account-management integration are not part of this package.
- Validate signature, configured issuer/audience, expiry and lifetime, with an
  explicit allowed-algorithm policy and bounded async JWKS retrieval/cache.
  Cover key rotation and unknown keys; never trust token-supplied key URLs or
  fall back to unverified claims. Dependency failures remain explicit/fail-closed.
- Unique stable (issuer, subject) to application UUID mapping, live application
  role/status lookup and reusable actor/role/ownership checks. Admin alone does
  not imply author/learner permissions; conceal foreign resources consistently.
- Implement GET /api/v1/me returning the existing Actor for active mapped users;
  deny missing/inactive mappings. Do not expose tokens or identity-provider data.
- Explicit first-admin/test-account provisioning: identity failures leave no
  eligible application grant; no arbitrary-login provisioning or privilege grants.
- Tests for invalid signatures/algorithms/issuer/audience/expired tokens,
  missing/inactive mappings, disabled accounts and role revocation with old tokens,
  cross-role/ownership denial, provisioning failure and identity outages.
  Use real PostgreSQL for account/mapping persistence and current-access checks.
- Clean and actual prior-revision upgrades; preserve F03 session isolation.
  Document actor dependency, authorization interfaces, realm/client setup,
  timeout/cache defaults and synthetic provisioning without leaking credentials.

Run npm run typecheck, npm test, npm run build, npm run api:generate,
npm run api:check, npm run test:contracts and npm run test:db, plus focused
identity/provisioning/migration tests. Verify generated /me types are reproducible
and preserve integrated F01/F02/F03 checks. Update intentional scaffold assertions
that required /api/v1/me to be absent; do not weaken unrelated route/error tests.
Record commands, environment and outcomes, distinguishing synthetic verifier
fixtures from actual Keycloak integration. Package evidence supports AT-01, but
I02 still owns the combined real-browser -> facade -> API identity acceptance.

Use synthetic data and local test dependencies only. Stop after I01 and return
the complete section 3 handoff with actor/auth helpers, migration chain, /me
contract, generated output, realm/client/audience settings, provisioning and tests.
Do not launch I02 or other successors, provision external resources, deploy or
use real data. Do not create a commit or PR automatically; return changes for
B.C.'s review. Report ready for review or blocked with a specific reason, not done;
B.C. owns tracker updates and accepted integration.
```

## 6. Active I02 integration handoff

**Historical assignment:** I02 is now done and EX-I02-01 closed following
B.C.'s 21 October 2026 completion confirmation and merged browser evidence review.
Do not redispatch this prompt. The current assignments are
[Phase 2](PHASE-2-HANDOFFS.md); the instructions below preserve I02's original scope.

B.C. confirmed F03/I01 completion and assigned I02 as `active` on 20 October
2026. B.C. owns integration/review/merge and explicitly accepted carrying the
native-form Origin finding as EX-I02-01 into I02, where it must be resolved
before acceptance. This is not a missing start approval. No agent is launched
by preparing this prompt.

F03 [PR #5](https://github.com/bc-bah/quezo/pull/5) and I01
[PR #6](https://github.com/bc-bah/quezo/pull/6) are integrated in
`6ef734faefbb52c76b78abb7d676ec9305f0c557`. Start from that result **plus this
approval/tracker update**. I02 owns the exclusive integration window; do not
reopen the historical F03/I01 prompts or dispatch assessment successors.

### I02 dispatch prompt

```text
Implement Quezo work item I02: Integrated login and access gate.

Read:
- docs/implementation/BACKLOG.md: active I02, done F03/I01 and EX-I02-01.
- docs/implementation/01-FOUNDATIONS.md: I02 acceptance and completion checkpoint.
- docs/implementation/README.md: integration ownership and definition of done.
- docs/SOFTWARE-SPECIFICATION.md: I02 assignment/completion exception,
  DEC-06/07, IAM-01/02, AT-01, QUAL-02 and relevant sections 6-8.
- docs/DEVELOPMENT.md: F03 configuration/session/facade, I01 actor/token interfaces,
  verification commands and distinctions between HTTP tests and browser proof.
- infra/keycloak/README.md: exact realm/client/audience and isolated provisioning.
- postgres/migrations/README.md and tests/e2e/README.md.
- Current root/frontend manifests and .github/workflows/ci.yml.
- docs/implementation/AGENT-HANDOFF.md: section 3 return format and section 6.

Owner, integration owner and reviewer/merge approver: B.C.
Assignment: I02 is active by B.C.'s explicit direction on 20 October 2026.
F03/I01 are done, not awaiting approval. B.C. explicitly accepts EX-I02-01 as
a predecessor completion exception and requires I02 to reproduce/fix or resolve
it with browser evidence before I02/AT-01 acceptance. It does not block starting.

Approved decisions: preserve DEC-06/07's implemented Keycloak code+PKCE/state/nonce,
confidential web client, dedicated API audience, PostgreSQL server sessions,
openid-client/pg web libraries and PyJWT/cryptography/async HTTPX backend validation.
Current database roles/status remain authoritative. No cached actor on outage,
runtime admin credentials, automatic grants or authentication bypass.
I02 may select/add a browser runner as its existing package requires: prefer
npm-locked Playwright Test, using the existing Node/uv toolchains. Document the
exact browser installation/run commands. Do not invent an already-existing
test:e2e command; add and document a focused script if needed.
No approval for refresh tokens, global SSO logout, different session defaults,
new business routes, A01 admin features, hosting, real data or pilot deployment.

Integrated prerequisites:
- F03 PR #5, merge b1a2fe035d52cdddf4db3a0c832a690773fe5688.
- I01 PR #6, merge 6ef734faefbb52c76b78abb7d676ec9305f0c557.
- Current migration head 0004_identity, following 0003_web_sessions.
Verify the producer code AND this I02 approval/tracker update exist in the
checkout. Do not implement from the old F02 baseline or overwrite either producer.
Both prior PRs passed hosted CI, but that is not real-browser AT-01 evidence.

Permitted surfaces:
- tests/e2e/ browser tests/configuration, reusable synthetic login fixtures and
  isolated orchestration; package-specific helper tests where already established.
- Narrow frontend session/facade/header/navigation fixes and focused regressions
  required to connect F03 to real I01, including EX-I02-01.
- Narrow backend identity/app or Keycloak test-provisioning fixes only where
  demonstrated necessary for I02 integration; no account-management expansion.
- I02-only shared edits: npm manifests/lock, root scripts, CI, Compose/env examples,
  existing isolated fixtures, docs/DEVELOPMENT.md and tests/e2e/README.md.
Shared-file owner: B.C.; I02 has the exclusive integration write window.
Preserve the single migration chain, database role isolation and all applied
revisions. No schema redesign is planned; escalate any demonstrated schema need.
Regenerate OpenAPI/TypeScript through F02 tools if a producer contract changes;
do not hand-edit artifacts or silently change the approved actor DTO.

Required interfaces and setup:
- Real browser -> Next auth routes/session facade -> FastAPI /api/v1/me -> real
  Keycloak JWT/JWKS and real PostgreSQL mappings/roles/status.
- Local realm quezo-local; confidential client quezo-web; scope openid quezo-api;
  API audience quezo-api; exact configured issuer and /auth/callback URI.
  If using isolated ports, explicitly register matching redirect/origin values;
  never fix a mismatch with wildcard redirects or disabled issuer/audience checks.
- Actor: userId UUID, roles array (administrator/author/learner, combined or empty),
  status active/disabled. /me denies inactive mappings/disabled accounts.
- Existing F03 SessionStore, BackendFacade and generated F02 client conventions;
  wire the existing actor adapter to I01's now-generated /me operation if needed,
  preserving schema checks, bounded requests, no-store and safe error propagation.
- Runtime roles quezo_web and quezo_runtime remain isolated from each other's
  storage; bootstrap/migration/provisioner credentials exist only in setup helpers.
- Current logout is local Quezo session invalidation, not Keycloak SSO logout.
  Session expiry is capped by access-token expiry; no automatic token refresh.

First acceptance blocker, EX-I02-01:
- Reproduce native browser clicks/submissions on the real login AND logout forms
  without setting Origin via the test API or globally injecting request headers.
- Inspect frontend/quezo/next.config.ts Referrer-Policy, src/app/auth-form.tsx
  native POSTs, src/lib/server/session.ts origin validation and the existing
  tests/production.test.ts manually supplied Origin header.
- The source/protocol review predicts no-referrer can yield Origin:null and 403.
  This has not yet been browser-reproduced; do not claim a confirmed runtime
  failure before observing it.
- If confirmed, choose the narrowest same-origin-form-compatible referrer policy
  (for example same-origin or strict-origin) and regression coverage while
  preserving token/query nondisclosure and foreign/null/missing Origin rejection.
  Never allow Origin:null, remove CSRF checks or replace native browser actions
  with manually authenticated HTTP calls merely to make the suite green.
- If not reproduced, record exact browser/version/request-header evidence that
  resolves the finding. Return EX-I02-01 closure evidence for B.C.'s review.

Deliver all I02 acceptance criteria:
- Start isolated real PostgreSQL, Keycloak, FastAPI and built Next.js instances;
  prove readiness before browser navigation. Reuse guarded test database and
  actual-provider helpers; do not target development volumes, production URLs
  or an existing realm. Cleanup only explicitly owned resources, also on failure.
- Through the actual provider login UI, demonstrate administrator, author and
  learner sessions/navigation, plus combined-role/non-inheritance behavior where
  relevant. Use explicit synthetic provisioning, not password-grant shortcuts,
  injected cookies/tokens, mocked /me, route interception or runtime auth bypass.
- Demonstrate callback, reload/session persistence, local logout and expiry with
  real server decisions. Use approved bounded configuration or actual waits;
  do not bypass validation or silently add refresh/global logout behavior.
- Disable/revoke an existing application's account/role and prove the next
  request with the old token/session cannot restore access. Cover invalid tokens
  and denied direct API calls independently of hidden navigation.
- Prove browser CSRF/origin denial and callback/state protections alongside
  valid native form success. Retain meaningful lower-level hostile-request tests;
  they supplement rather than replace the real user journey.
- Prove identity/backend/database outages fail explicitly without authenticated
  fallbacks. Respect I01's bounded JWKS cache: valid cached keys may work until
  TTL; cold/expired-cache failures must fail closed. Do not require per-request
  JWKS fetches or immediate failure of already validated cached keys.
- Assert tokens and usable session secrets are absent from page content,
  localStorage/sessionStorage and application logs. Opaque HttpOnly session
  cookies are intentional browser-cookie storage, not a failed assertion:
  verify document.cookie cannot read them and flags match local/shared policy.
- Keep Playwright traces/HAR/screenshots/storage-state files from persisting
  credentials, callback codes or authorization/cookie headers. Disable sensitive
  captures or sanitize them before retention; never commit raw browser state.
- Provide reusable synthetic login fixtures, automated AT-01 scenario evidence
  and the working-foundations demonstration. Note keyboard navigation/error-state
  observations without claiming full Q02/WCAG or P0 acceptance.

Preserve existing checks and run:
npm run typecheck
npm test
npm run build
npm run api:check
npm run test:contracts
npm run test:db
npm run test:identity
npm run test:identity:integration
npm run test:web:production
Run the newly documented real-browser command as well, with required isolated
services and actual browser dependencies. Add the focused browser check to CI
without duplicating every existing matrix unnecessarily. Record exact commands,
versions, environment and results; distinguish local/hosted/manual evidence.
Missing services, skipped cases, controlled HTTP peers and a passing existing
suite do not establish I02. Fix integration failures rather than weakening tests.

Stop after I02 and return the complete section 3 handoff, including each AT-01
scenario/result, EX-I02-01 disposition/evidence, browser fixture/startup/cleanup
commands, minimal producer fixes, generated changes if any and C01/T01 inputs.
Do not launch successors, provision external resources, deploy or use real data.
Do not create a commit or PR automatically; return changes for B.C.'s review.
Report ready for review or blocked with an exact unresolved criterion, not done;
B.C. owns acceptance, exception closure, integration and tracker updates.
```

## 7. Active Phase 2 assignments

B.C. assigned all eight lifecycle packages on 21 October 2026, with explicit
producer execution gates and approved untimed demo defaults. Use one copy-ready
prompt per session from [PHASE-2-HANDOFFS.md](PHASE-2-HANDOFFS.md).
`active` means assigned; it is not evidence that a predecessor has finished.
The current integrated foundation is I02 merge `553a2c8`, plus this planning
update. Consumers must also include their later accepted producer commits.

| Package | Copy-ready prompt | Implementation gate |
| --- | --- | --- |
| C01 | [Versioned objective questions](PHASE-2-HANDOFFS.md#c01-dispatch-prompt) | I02 done; executable now |
| C02 | [Immutable quiz publication](PHASE-2-HANDOFFS.md#c02-dispatch-prompt) | C01 accepted and integrated |
| D01 | [Assignment and attempt start](PHASE-2-HANDOFFS.md#d01-dispatch-prompt) | C02 accepted and integrated |
| D02 | [Durable response save and resume](PHASE-2-HANDOFFS.md#d02-dispatch-prompt) | D01 accepted and integrated |
| S01 | [Pure objective scoring](PHASE-2-HANDOFFS.md#s01-dispatch-prompt) | F02 done; executable now |
| D03 | [Finalization and expiration](PHASE-2-HANDOFFS.md#d03-dispatch-prompt) | D02 and S01 accepted and integrated |
| R01 | [Policy-filtered result](PHASE-2-HANDOFFS.md#r01-dispatch-prompt) | D03 accepted and integrated |
| T01 | [First lifecycle acceptance](PHASE-2-HANDOFFS.md#t01-dispatch-prompt) | R01 and I02 accepted and integrated |
