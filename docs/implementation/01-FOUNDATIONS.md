# Phase 0-1: Baseline and working foundations

Dependencies/status are authoritative in [BACKLOG.md](BACKLOG.md). Each engineering
package also requires the [definition of done](README.md#5-definition-of-ready-and-done).
Paths below are ownership proposals; create only the files needed by the package.

## G00: Approve implementation baseline

**Owner/approver:** B.C. **Type:** review, not feature code.

**Recorded outcome, 20 October 2026:** [G00 accepted with scoped approval](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026).
DEC-01 through DEC-05 and F01/F02 tools under DEC-07 are approved. DEC-06 and
session storage implementation remain held, blocking F03/I01 as applicable.
B.C. owns integration and F01/F02 review/merge. Only F01/F02 are authorized,
using synthetic data; DEC-08 through DEC-11 later commitments remain held.

Read the scope, HLA and [software specification](../SOFTWARE-SPECIFICATION.md),
especially DEC-01 through DEC-11. Resolve DEC-01 through DEC-07 sufficiently to
start foundation and core work, including identity authority, bounds, timing,
release behavior, transaction/idempotency rules and library choices. Record actual
approvers/dates/amendments in the specification, not merely "reviewed."

Name the integration owner, package reviewers and the first authorized work wave.
For DEC-08 through DEC-11, record owners and the later gate where each must close;
identify any early prototype limitation while decisions remain pending.

**Done:** applicable baseline approvals recorded, contradictions resolved, first
wave explicitly assigned, and all remaining decision blockers visible in the
tracker. No product requirement is marked implemented by this review.

## F01: Database and integration-test foundation

**Rules:** specification section 6, QUAL-01/04/05.  
**Primary surfaces:** `postgres/` persistence setup and test fixtures,
`postgres/migrations/`, database Compose/CI wiring via the integration owner.

Install the approved driver/migration runner, implement environment-based
configuration and bounded connection lifecycle, and provide an isolated real
PostgreSQL test database. Establish migration execution/ordering and restricted
application versus migration identities. Create only foundational records needed
by the next slices; feature schemas arrive with their packages.

Define reusable transaction/test helpers without a generic repository framework.
Document clean setup, migration upgrade and test isolation. Test failures must
surface database unavailability rather than replacing PostgreSQL with memory.

**Done:** a clean database migrates; a previous baseline upgrades; rollback of
a failing transaction is demonstrated; integration tests cannot target a production
database accidentally; pool connections close on shutdown; CI can run the isolated
database tests. Handoff the connection/transaction interface and migration rules.

**Excluded:** full domain schema, caches, tenant abstractions, deployment hosting.

## F02: Contract and error foundation

**Rules:** specification sections 6-7, IAM-02, QUAL-02/04.  
**Primary surfaces:** backend HTTP schema/error helpers, contract export tooling,
frontend generated-client location and package/CI wiring by agreement.

Establish IDs/enums, camelCase serialization, safe validation/error envelope,
correlation IDs, pagination conventions and shared actor shape. Implement consistent
exception/validation handling with no raw submitted values in errors or logs.
Set up OpenAPI export and the approved TypeScript client-generation/check workflow,
initially against implemented endpoints. Agree the identity/session DTO shape
before F03 and I01 diverge; do not invent working business routes.

**Done:** invalid payload/unknown-field and dependency/internal error fixtures
produce the specified sanitized envelope; OpenAPI/client generation is reproducible
and CI detects stale generated output. The health contract still works. Handoff
the common actor/error/schema conventions and exact generation/check commands.

**Excluded:** full supported public API, unimplemented endpoints returning fake
success, domain authorization decisions inside generic middleware.

## F03: Web session and navigation foundation

**Rules:** IAM-01, section 8, QUAL-02/03.  
**Primary surfaces:** frontend session/facade code, root layout/navigation,
restricted web-session storage; coordinate session migration with F01's owner.

Implement the approved server-side session mechanism, login callback/logout,
PKCE/state/nonce, cookie/CSRF/origin protections and server-only token handling.
Build role-aware navigation and signed-out/expired/disabled/error states.
Backend business calls go through the server facade, not browser token storage.

Can progress alongside I01 using the agreed actor contract and controlled test
identities; I02 owns the final combined proof. A dependency outage must not become
a fake authenticated session.

**Done:** session expiry/logout/CSRF and token-nondisclosure tests pass; navigation
is keyboard usable; the session store is not process-local authoritative state;
facade errors preserve actionable backend errors. Handoff route conventions,
session interface and authorized-fetch/client integration.

**Excluded:** assessment screens or a parallel backend inside Next.js.

## I01: Identity and authorization backend

**Rules:** IAM-01/02, identity portion of IAM-03, AT-01.  
**Primary surfaces:** `infra/keycloak/`, `postgres/src/quezo_api/modules/identity/`,
identity migrations and backend authorization tests.

Configure a synthetic-data realm/client/roles without committed secrets, implement
issuer/audience/signature/lifetime validation and stable application identity
mapping, and expose `/api/v1/me`. Enforce current application roles and access
status; reusable authorization accepts the actor and owning resource.
Provide explicit first-admin/test-account provisioning with no auth bypass.

**Done:** invalid token variants and missing/inactive mappings are denied; old
tokens cannot restore revoked status/roles; cross-role calls fail consistently;
provisioning is reproducible and fail-closed. Handoff actor dependency, ownership
check conventions, identity configuration and test account setup.

**Excluded:** full administrator UI (A01), embedding Keycloak admin credentials
in frontend code, automatic role grants on arbitrary login.

## I02: Integrated login and access gate

**Rules:** IAM-01/02, AT-01, QUAL-02.  
**Primary surfaces:** integration/browser tests, minimal F03/I01 integration fixes.

Connect real Keycloak login to the web session facade and backend `/me` using the
shared DTO. Demonstrate all three roles, expiry/logout, disabled access, CSRF denial
and backend validation independent of web navigation. Select/add the browser test
runner here if not yet present, and establish reusable synthetic login fixtures.

**Done:** the real browser -> web facade -> FastAPI -> identity/account path works
without bypasses; token/cookie content is absent from browser storage and logs;
identity outages show explicit failure. Record AT-01 evidence and the foundation
milestone demonstration. Subsequent features inherit a working actor/session path.

**Excluded:** claiming full P0 administration or readiness from a successful login.
