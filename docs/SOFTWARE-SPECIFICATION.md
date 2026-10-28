# Quezo software specification

**Version:** 0.1  
**Date:** 20 October 2026  
**Status:** Foundations, Phase 2 and C03 accepted; A01 explicitly dispatched under the 27 October scoped DEC-06 approvals; D04/R02 remain ready for separate sequential dispatch.

**Scope:** Single-organization, low-stakes, authenticated objective assessment.

## 1. Purpose and authority

This specification translates the [prototype scope](PROTOTYPE-SCOPE.md) and
[high-level architecture](PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md) into observable
software behavior. It covers every P0 requirement in the
[PRD](reference/02-Product-Requirements.md). Terms come from
[CONTEXT.md](../CONTEXT.md).

The approved scope and technology choices take precedence over the original
PRD's open alternatives. This document proposes detailed rules; writing "shall"
defines the intended acceptance condition, not evidence of approval or delivery.
Resolve section 2 before implementing affected behavior. After approval, this
document is the behavioral source of truth; the HLA owns architecture rationale,
and the [implementation bundle](implementation/README.md) owns delivery sequencing.
An agent encountering a conflict must identify the conflicting requirement and
obtain a decision rather than silently choosing a different behavior.

**Existing software:** F01 PostgreSQL infrastructure, F02 schemas/errors/generated
contracts, F03 server sessions/navigation/facade, and I01 token validation,
current-actor `/me` and controlled local provisioning. I02's combined real-browser
identity gate is accepted and EX-I02-01 closed. Phase 2 adds versioned questions,
immutable publication, assignment/start, durable saves, scoring/finalization and
policy-filtered results. T01 accepts the integrated initial lifecycle; this is
not full P0 or pilot approval.

**Excluded:** multiple tenants, cohorts, anonymous access, written/manual grading,
regrading, CSV/import/export, pool selection, external API support, LMS integration,
AI/proctoring and media/community features. Minimal integrity events are included;
a general audit-management product is not.

## 2. Decision register

Confirmed: P0 scope, one organization, low-stakes use, Next.js/React + Python/FastAPI,
PostgreSQL, Keycloak and Docker. Decision approval is scoped as recorded below.
Record approval date, approver and any amendments in the final column. An empty
approval means the decision is not approved.

| ID | Proposed baseline / unresolved choice | Required before | Owner | Approval |
| --- | --- | --- | --- | --- |
| DEC-01 | Named-learner assignments; one assignment per learner/version; no self-enrollment; one active attempt per assignment; starts and expirations consume allowance | Domain implementation | B.C. | Approved as written by B.C., 20 October 2026 |
| DEC-02 | Availability end caps standard duration; approved pre-start accessible timing may override the attempt deadline, never the start cutoff; no grace period or late offline answers; close preserves active deadlines; archive retains history | Domain implementation | B.C. | Approved 20 October 2026; scoped accessible-timing amendment approved 27 October 2026 in the Phase 3 approval record below |
| DEC-03 | Single-answer MCQ and true/false; nonnegative integer points, no penalties/partial credit, positive quiz total | Domain implementation | B.C. | Approved as written by B.C., 20 October 2026 |
| DEC-04 | Independent score/key/explanation release after finalization, after availability end, or never; per-item grading is gated with answer-key release | Result and publication implementation | B.C. | Approved as written by B.C., 20 October 2026 |
| DEC-05 | Input bounds in section 6, unlimited values, revision protocol and idempotency retention; retained request records have no automatic cleanup in the prototype | Contract implementation | B.C. | Approved 20 October 2026; adjusted learner duration ceiling of 6048000 seconds approved 27 October 2026; authored duration bounds unchanged |
| DEC-06 | Server-side web sessions; application roles/status authoritative on each request; Keycloak owns identity; local realm, confidential web client, exact redirects, code + PKCE, state/nonce and dedicated API audience; openid-client for web OIDC; PyJWT with cryptography and async HTTPX for backend validation; separately scoped least-privilege A01 administration adapter | Identity implementation | B.C. | F03/I01 approved 20 October 2026; local provisioning only in those packages. A01 local-realm boundary approved 27 October 2026. B.C. follow-up approval 27 October 2026 permits the local A01 service identity's fine-grained user `manage` capability, including Keycloak user deletion/password-reset capability that Keycloak does not separate from `manage`; Quezo must not expose deletion or credential-reset operations. Exact effective permissions must be verified and recorded before privileged implementation; no other realm/group/client administration is approved. |
| DEC-07 | Psycopg 3 async/pooling; Alembic with SQLAlchemy Core, no ORM; openapi-typescript + openapi-fetch; node-postgres (pg) for restricted PostgreSQL server sessions; PyJWT with cryptography and repository-convention HTTPX for I01 | Foundation implementation; session choice before F03 | B.C. | F01/F02 tools approved; F03 npm-locked dependencies and I01 uv-locked dependencies approved by B.C., 20 October 2026 |
| DEC-08 | Approve benchmark environment/profile, performance gates, logging/metric tooling, bounded retry and rate-limit settings | Hardening/load work | B.C. | Held; close before hardening/load gates and O01 operational targets; no approved numeric performance gates |
| DEC-09 | Pre-start learner timing adjustment/off choice, pinned per attempt, with explicit scheduled-availability interaction | Timed UX implementation | B.C. | Approved 27 October 2026 as specified in the Phase 3 record below; implementation and Q02 verification still required, no WCAG conformance claim |
| DEC-10 | Name first pilot audience; approve hosting, data retention/deletion, incident ownership, backup RPO/RTO and any availability commitment | Real-data/shared pilot | B.C. | Held; close before O01 operational targets and any real-data/shared pilot; synthetic local work only |
| DEC-11 | Name review/merge/release approvers and assign delivery dates/budget | Scheduling and release commitment | B.C. | B.C. owns foundation/Phase 2 and, confirmed 27 October 2026, C03/A01/D04/R02 integration/review/merge. Sequential separate dispatch A01 then D04 then R02; release approval, dates and budget remain held |

An authorized synthetic-data development wave can proceed once its relevant
decisions are approved; unresolved pilot commitments do not authorize real data.
The initial baseline work item identifies exactly which decisions each wave needs.

### G00 approval record: 20 October 2026

Historical first-wave authorization; its F03/I01 holds are superseded only by the
[second-wave approval](#second-wave-approval-f03-and-i01) below.

B.C. explicitly approved this scoped baseline and first-wave tool selection.
B.C. is the backlog and integration owner, accountable owner for every package,
and reviewer/merge approver for F01 and F02. Later package reviewers and release
commitments remain unassigned under DEC-11; ownership alone is not approval.

**Authorized wave:** F01 database/integration-test foundation and F02
contract/error foundation, using synthetic data only. Both are ready for dispatch,
not active or implemented. Use the [prepared prompts](implementation/AGENT-HANDOFF.md#4-approved-first-wave-prompts).
B.C. coordinates shared-file writes; separate sessions do not receive concurrent
permission to edit shared manifests, CI, application wiring or documentation.
Select compatible library versions and lock them during implementation; this
approval selects tools, not unverified package versions.

**Explicit holds:** DEC-06 and the session-storage portion of DEC-07 block F03/I01
as applicable. DEC-08 through DEC-11 remain open except for first-wave ownership
and review/merge authority above; B.C. owns obtaining the relevant reviews at the
listed gates. No successors, deployment, external resources, real learner data,
shared pilot, delivery date or budget are authorized by G00. Domain decisions
DEC-01 through DEC-05 are approved but do not dispatch their future packages.

### Second-wave approval record: 20 October 2026

Historical dispatch provenance: B.C. authorized F03's first shared-file window
and coordination-record reconciliation, then I01's window from integrated F03
PR #5 (`b1a2fe0`). The I01 extension selected repository-convention asynchronous
HTTPX and PyJWT/cryptography, with no runtime administration credentials.
The consolidated approval below preserves both assignments and their boundaries.
Current completion and I02 authorization are recorded separately below.

### Second-wave approval: F03 and I01

Historical second-wave authorization; current status is in the
[I02 assignment record](#i02-assignment-and-completion-exception).

On 20 October 2026, B.C. confirmed F01/F02 complete, requested F03/I01 be made
`active`, and explicitly approved the following identity/session baseline.
F01 is integrated by [PR #3](https://github.com/bc-bah/quezo/pull/3), merge
`873232814ab3de0baefeac2ebbcdc1351611a67d`; F02 by
[PR #4](https://github.com/bc-bah/quezo/pull/4), merge
`5f314125e13262139e1d3e28d190881d6fbd5f8b`. Both packages are accepted as foundation
work, not as AT-01, full AT-10/AT-15, or prototype acceptance.

**Approved choices:** openid-client for Next.js OIDC, node-postgres (`pg`) for
server-session persistence, and PyJWT with cryptography plus HTTPX for backend
JWT/JWKS verification. Use a dedicated local Keycloak realm, confidential web
client with exact redirect/logout URIs, authorization code + PKCE/state/nonce,
and a dedicated backend audience. No implicit/password grant, arbitrary login
role grants, or runtime Keycloak-admin credentials. Local provisioning is explicit
and fail-closed; application identity uses unique `(issuer, subject)` mapping.
Application roles/status are read authoritatively for every protected request.

Session and login-transaction records live in a separate PostgreSQL schema with
a restricted web runtime role, not the `quezo` schema with F01's default backend
grants. Only the web runtime may read session secrets; it cannot read assessment
tables, and `quezo_runtime` cannot read session records. Migration/bootstrap
credentials are never application credentials. Tokens remain server-side;
browser cookies hold opaque session identifiers, never access/refresh tokens.
F03/I01 reuse the approved F02 actor DTO and sanitized error contract.

Agents may select compatible library versions and bounded session/timeout
defaults, document the rationale and enforce/test expiry and limits for B.C.'s
review. This delegation is not permission to invent business behavior, change
the actor contract, relax security controls or establish DEC-08 performance gates.

**Assignment:** F03 and I01 are active under B.C.'s ownership, integration and
review/merge authority. This records B.C.'s explicit assignment, not an agent
launch or evidence of implementation. Default execution is F03 then I01 to
serialize migrations and shared files; the package dependency graph is unchanged.
Use the [second-wave handoffs](implementation/AGENT-HANDOFF.md#5-active-second-wave-prompts).
I02 still owns the combined real-browser identity acceptance after both merge.

**Remaining holds:** DEC-08/09/10 and the remainder of DEC-11 are unchanged.
No I02 or other successor dispatch, production configuration, external provisioning,
deployment, real data or shared pilot is authorized. Full account-administration
integration/privileges belong to A01 and require separate review.

### I02 assignment and completion exception

Historical assignment; the [I02 acceptance record](#i02-acceptance-and-exception-closure)
below now closes the exception and completes the gate.

On 20 October 2026, B.C. confirmed F03 and I01 complete and explicitly requested
their `done` status and I02's `active` assignment. F03 is merged via
[PR #5](https://github.com/bc-bah/quezo/pull/5), merge
`b1a2fe035d52cdddf4db3a0c832a690773fe5688`; I01 via
[PR #6](https://github.com/bc-bah/quezo/pull/6), merge
`6ef734faefbb52c76b78abb7d676ec9305f0c557`. Hosted CI passed for both on Node 22/24
and Python 3.12/3.14. Local evidence remains in the development runbook.

**EX-I02-01, explicit completion exception:** the review identified a likely
native-browser login/logout failure: F03's `Referrer-Policy: no-referrer` can
produce `Origin: null` for native form POSTs, which its strict CSRF origin guard
rejects. The existing HTTP test supplies Origin manually. This is a source/protocol
finding, not a browser reproduction. B.C. explicitly approved closing F03 with
this named exception and assigning browser reproduction/fix as I02's first
acceptance blocker. **Owner:** B.C. **Scope/impact:** F03 native authentication
forms may fail closed; no permission to weaken origin validation or accept null
origins. **Follow-up/closure:** actual-browser evidence must confirm and fix the
failure, or demonstrate with evidence that it does not occur; retain malicious
origin denial regression coverage. I02 and AT-01 cannot pass while it is unresolved.
No integrity or unauthorized-disclosure failure is accepted as an exception.

**Authorized work:** I02 integrated login/access proof and minimal F03/I01
integration fixes, synthetic local data only. B.C. owns the package, integration,
review/merge and its exclusive shared-file window. Select/add the browser test
runner as I02 already requires, keeping the current npm/uv toolchains and locked
dependencies. Existing identity/session choices and defaults remain the baseline;
changing login semantics, refresh behavior or global SSO logout requires a
separate decision, not an incidental test fix.

Use the [I02 prompt](implementation/AGENT-HANDOFF.md#i02-dispatch-prompt) from
`6ef734f` plus this approval/tracker update. `active` records explicit assignment;
this documentation does not launch an agent or establish combined acceptance.
The known exception is a completion blocker to resolve during I02, not a missing
approval preventing I02 from starting. DEC-08/09/10 and later DEC-11 holds remain.
C01/S01 or other successor dispatch, real data, deployment and shared pilot
remain unauthorized by this assignment.

### I02 assignment and completion exception: 20 October 2026

Historical in-session dispatch/reconciliation record, superseded for current
status by I02 acceptance and the Phase 2 assignment below.

B.C. confirms F03 PR #5 (merge `b1a2fe035d52cdddf4db3a0c832a690773fe5688`)
and I01 PR #6 (merge `6ef734faefbb52c76b78abb7d676ec9305f0c557`) done and
integrated, and explicitly dispatches I02. B.C. owns the package, integration,
review and exclusive shared-file write window. B.C. also explicitly authorizes
the I02 session to reconcile the approval/tracker documents to this assignment.

**EX-I02-01:** B.C. accepts the predicted `no-referrer`/native POST `Origin:null`
interaction as a predecessor completion exception. At dispatch it was not a
confirmed runtime failure and did not block starting I02. I02 must reproduce/fix or resolve
it with native browser login AND logout evidence before I02/AT-01 acceptance.
CSRF and foreign/null/missing Origin rejection must remain intact. B.C. owns
exception closure; passing HTTP tests/hosted CI do not substitute for this proof.

DEC-06/07 and the implemented session defaults remain unchanged. npm-locked
Playwright Test may be added for isolated real PostgreSQL/Keycloak/API/built-web
acceptance using synthetic data. No refresh tokens, global SSO logout, runtime
admin credentials, automatic grants, outage fallback, schema redesign, A01,
business routes, successors, external resources, deployment or real data are
authorized. Return evidence for review, without automatic commit or PR.

### I02 acceptance and exception closure

On 21 October 2026, B.C. confirmed I02 complete. The reviewed integrated result
is [PR #7](https://github.com/bc-bah/quezo/pull/7), merge
`553a2c8b77a770667f4cef6825f57c3b55f477ed`. Standards and specification review
found no significant issues. All 16 actual-browser scenarios and the retained
application checks passed in the recorded local run; hosted browser and
Node 22/24/Python 3.12/3.14 jobs also passed.

EX-I02-01 is closed: real Chromium native forms reproduced null-Origin/403 with
`no-referrer`; I02 changed document policy to `strict-origin`, preserving
`no-referrer` on auth routes. Normal login/logout work without injected Origin;
the retained negative control and malicious-origin checks still deny access.
See [browser evidence](DEVELOPMENT.md#i02-integrated-browser-gate) and
[hosted CI](https://github.com/bc-bah/quezo/actions/runs/39564745343).
This accepts the AT-01 working-foundations gate, not future assessment
authorization, full accessibility, operational readiness or pilot deployment.

### Phase 2 assignment and demo defaults

Historical assignment record; all eight packages are now accepted. The demo
defaults and later holds below remain in force.

On 21 October 2026, B.C. explicitly assigned **C01, C02, D01, D02, S01, D03,
R01 and T01** as `active`, retaining ownership, integration and review/merge.
B.C. explicitly approved that these are **assignments with execution gates**:
only C01 and S01 can implement immediately; downstream packages must wait for
all listed producers to be accepted and integrated in their own checkout.
The dependency graph is unchanged. No agent launch or product implementation
is implied by this record.

The starting foundation is I02 merge `553a2c8`, with migration head
`0004_identity`, plus this approval/tracker update. Use the
[Phase 2 prompts](implementation/PHASE-2-HANDOFFS.md). Later accepted producer
commits/contracts must be recorded in the backlog and included before a consumer
starts. No fabricated endpoints, parallel DTO copies or mock-only acceptance
may substitute for missing producers.

B.C. approved these **minimal demo defaults**:

| Setting | Phase 2 author/learner demo |
| --- | --- |
| Duration and availability | Untimed: duration, availability start and end all null |
| Attempt limit | One successful start per assignment; expiry consumes allowance |
| Question/option order | No randomization in the initial UI; preserve authored order |
| Points | Selected question-version default unless an explicit validated override is supplied |
| Score-only release preset | Score `after_finalization`; answer key and explanation each `never` |
| Fully withheld preset | Score, answer key and explanation each `never` |

Persist independent policy fields and evaluate them at the proper server seams;
the two UI presets do not collapse three release rules into one flag. Backend
fixtures/tests cover other approved policies, finite deadlines, ordering and
allowance boundaries. `after_availability_end` still requires a finite end.
Do not silently coerce unsupported writes into demo defaults. Advanced policy
controls remain D04 work; authors may choose either minimal release preset so
T01 can demonstrate released aggregate scores and fully withheld results.

At this historical Phase 2 checkpoint DEC-09 remained held: no user-facing timed learner workflow/countdown was accepted
in Phase 2. D03 must still implement and test authoritative backend expiry;
T01 uses an explicitly controlled backend expiry fixture to demonstrate an
expired result, not a timed-accessibility claim. DEC-08 remains held: no numeric
performance gate or automatic transient-database retry policy is approved.
Surface failures and support specified idempotent client retries without
inventing a server retry loop.

One writer owns shared scripts/CI/manifests, generated contracts and migration
ordering at a time. C01 has the initial shared-file window; S01 is independently
restricted to pure scoring and its tests. B.C. serializes later windows along
the lifecycle chain. Phase 3, real-data/shared pilot, external provisioning,
deployment, delivery dates and budget remain outside this assignment.

### T01 acceptance and Phase 3 readiness

On 23 October 2026, B.C. requested acceptance/tracking reconciliation before
moving to Phase 3. T01 is accepted at [PR #15](https://github.com/bc-bah/quezo/pull/15)
merge `df06ccc19af947cda05757c79938394763d6edb6`, implementation `300bbc4`,
following review of its recorded lifecycle evidence and successful hosted
browser/Node/Python jobs. All Phase 2 packages are `done`; the migration head
at that checkpoint was `0009_finalization`. See the
[acceptance record](implementation/BACKLOG.md#t01-milestone-acceptance-23-october-2026)
and [scoped AT matrix](../tests/e2e/README.md#lifecycle-acceptance-matrix).

The T01 predecessor gate is satisfied for all Phase 3 packages. The original
Phase 3 checkout was `354da49`, head `0009_finalization`; its latest-finalized
learner return link is only partial AT-13 evidence. The following dated record
supersedes the original unassigned/decision-held Phase 3 checkpoint.

### C03 acceptance and Phase 3 approvals: 27 October 2026

B.C. reviewed the updated local Docker author workspace, confirmed satisfaction,
requested its commit/merge into local `dev`, and then directed backlog/acceptance
reconciliation. C03 is accepted at `2eba9eb8f2986664687059f974ad4282b0b1dd49`,
fast-forward integrated into local `dev` from `354da49`. Current migration head
is `0010_author_workspace`, also verified applied in the local Docker stack.
No remote push, PR or hosted CI result is asserted. The
[C03 evidence map](DEVELOPMENT.md#c03-complete-author-workspace) distinguishes
inherited/new/partial/out-of-package AT-03/04/05 cases and records the umbrella
check limitation. Package acceptance does not declare full catalogue AT IDs,
full P0, accessibility conformance or pilot readiness.

B.C. explicitly approved these additional synthetic local-development decisions:

- **A01 / DEC-06:** a dedicated local-realm service identity limited to user
  provisioning/status/profile and required role mapping. No master-realm,
  client/realm administration, application credential storage or unrestricted
  administration proxy. Service secrets are server-side ignored configuration,
  never browser data, logs or source. Application authorization remains
  authoritative. Setup remains explicit/local, not external provisioning.
  B.C.'s 27 October follow-up approves the local service identity's fine-grained
  user `manage` capability, which Keycloak also uses for user deletion and
  password-reset operations; Quezo must not expose those operations. Before
  privileged implementation, verify and record the exact effective permissions.
  No master/realm/client or group administration, credential storage, or other
  broader capability is approved. A further 27 October approval permits the
  local service account's `view-users` role for account search/profile access,
  including its transitive read-only `query-groups` role; group mutation remains
  excluded.
- **D04 / DEC-09:** before starting an attempt, every eligible learner may keep
  the authored timing, choose an adjusted duration supporting at least ten times
  the authored duration, or turn off timing. Availability end remains a hard
  cutoff for **new starts**. For an explicitly adjusted attempt it does not
  shorten the chosen duration; turning timing off removes both duration and
  availability-end attempt deadlines. Standard attempts retain the earlier-bound
  rule. Freeze the choice/effective deadline on the attempt. This explicitly
  amends DEC-02 and DEC-05: authored duration remains 60-604800 seconds, adjusted
  duration supports up to 6048000 seconds. No post-start extension, reset,
  reopening, late answer grace or retroactive change to existing attempts.
  Snapshot/schema/start-command changes require a reviewed forward migration and
  regenerated contracts. Result-release policy remains pinned and unchanged:
  after-availability-end disclosure still requires finalization and the original
  published availability end; timing adjustment does not release active answers.
  Approval is not evidence that these controls exist or meet WCAG; D04 and Q02
  must test them.
- **Ownership / DEC-11:** B.C. remains integration/review/merge owner. Prepare
  A01, then D04, then R02 for **separate explicit dispatch**, one shared-file/
  generated-contract/migration writer at a time. No concurrent assignment or
  automatic successor execution. The next agent branches from the actual current
  local `dev` plus this approval/tracking update; reverify head after each merge.
  C03's exclusive editor window is complete; D04's separately dispatched owner
  may integrate its settings through the existing wrapper without redesigning
  C03 composition/lifecycle.

A01 is `active` for the explicitly dispatched session; D04/R02 remain `ready`
for separate dispatch after A01's integration window. The [handoff
packet](implementation/PHASE-3-HANDOFFS.md) carries these contracts. DEC-08/10
and release/date/budget commitments remain held.

**A01 effective Keycloak permissions verified 27 October 2026:** On local
Keycloak 26.4.7, the dedicated `quezo-account-admin` confidential client uses a
service account with only `realm-management/query-users` and `view-users`
assigned and scoped; the token contains those roles plus the `query-groups`
composite implied by `view-users`. Fine-grained access is granted by a `client`
policy targeting only `quezo-account-admin`, attached to the `Users` resource
type with only `view` and `manage` scopes. A user policy for the service-account
user does not authorize the client-credentials request context. The exact
client-bound policy evaluated `PERMIT`; through the service identity, disabled
synthetic-user creation returned 201, profile read returned 200, profile update
returned 204, and exact username search found the synthetic fixture. No
`manage-users`, role-mapping, group-mutation, client, or realm-administration
permission is granted. Keycloak `manage` still carries its approved delete and
password-reset effects; no Quezo endpoint exposes either operation.

## 3. Actors and authorization

### IAM-01: Identity and sessions

The web module shall use Keycloak authorization code + PKCE with state/nonce and
exact redirect validation. Tokens remain in server-side sessions; browser cookies
are HttpOnly, Secure in shared environments, SameSite, rotated and expiring.
State-changing browser calls require CSRF/origin validation. FastAPI independently
validates issuer, audience, signature and token lifetime.

Map identity by unique `(issuer, subject)`, not email. Application status and role
assignments are authoritative for authorization on every protected operation.
Token role claims must not restore a removed application privilege. Provisioning
is controlled; signing in does not auto-grant a role or reactivate an account.
Disabled users and sessions without an active mapped account receive no assessment
access, including with an otherwise valid old token.

### IAM-02: Permission matrix

Roles may be combined; each operation still requires its resource relationship.
Administrator privilege is not blanket access to assessment content.

| Operation | Administrator | Author | Learner |
| --- | --- | --- | --- |
| Provision users, change roles/status | Allowed | Denied | Denied |
| Manage banks/questions/quizzes | Only with author role and ownership | Own resources | Denied |
| Assign a quiz | Only with author role and ownership | Own published quiz; active learner recipient | Denied |
| Look up assignable learners | Same author condition | Minimum identity fields for active learners only | Denied |
| Preview unpublished content | Same author condition | Own content; preview does not start an attempt | Denied |
| Start/resume/save/finalize | Only with learner role and assignment | Only with learner role and assignment | Own assignment/attempt |
| Read learner result/history | Same learner condition | Same learner condition | Own, release-filtered |
| Read quiz report/finalized submission | Same author condition | Own quiz | Denied |

Checks apply to direct HTTP calls, lists/searches, nested IDs and generated links,
not only screens. Conceal another user's resource as 404 consistently; use 403
for an authenticated actor lacking the required operation role. A shared link
identifies an assignment, never grants eligibility.

### IAM-03: Account administration

The prototype shall provide an in-app user list, provisioning, role assignment
and activation/deactivation controls. Keycloak handles credentials and resets;
the application never stores a password. Record administrator, target, action
and outcome without credential material.

Keycloak and application updates are not one database transaction. Keep partially
provisioned users ineligible, expose failures and allow controlled retry.
For revocation, disable application access first; grant/activate only after
required identity operations succeed. Subsequent requests after committed
revocation are denied; do not promise to cancel a transaction already admitted.
Protect against removal of the last active administrator. A bootstrap/runbook
must establish the first administrator without a runtime authentication bypass.

## 4. Authoring and publication

### AUTH-01: Question bank and revisions

An author shall create, read, edit, archive and organize their questions in owned
banks, with text/category/tag filtering and bounded pagination. Each question
has a stable ID; edits create immutable versions. Archived questions remain
available to historical references but are excluded from new selection by default.
Moving a question between owned banks does not change its identity.

Supported content is plain text. A single-answer MCQ has stable option IDs and
exactly one correct option; true/false has exactly two semantic choices and one
correct answer. Authors set default points and explanatory feedback. Validation
rejects duplicate option IDs, missing correct options, empty required text,
unsupported question types and points outside the approved bounds.

A quiz draft selects explicit question-version IDs. When a newer revision exists,
updating the draft selection is explicit, not a silent change. Saving or archiving
a reusable question cannot mutate a published quiz or an attempt snapshot.

### AUTH-02: Quiz construction and preview

An author shall edit a draft's title, instructions, ordered selected questions,
optional quiz-specific point overrides, duration/attempt limits, availability
window/time zone, randomization flags and independent result policies.
The effective points use the override when present, otherwise the selected
question version's default. A published quiz must contain at least one question
and a positive possible-points total. A selected question identity occurs at most
once per quiz version in this prototype.

Preview shall use the learner presentation rules without creating an Assignment,
Attempt or Grade, consuming allowance, or writing reporting data. The preview is
author-authorized; ordinary learner endpoints cannot preview draft content.

### AUTH-03: Publication state and immutability

| Current condition | Command | Result / constraint |
| --- | --- | --- |
| Draft, no publication | Publish | Validate and atomically create first immutable QuizVersion; state becomes published |
| Published, with explicit revision draft | Publish revision | Create a new immutable version; existing assignments remain pinned to their old version |
| Published | Close | Block starts across versions; existing attempts continue under their fixed deadline |
| Closed, no in-progress attempts | Archive | Remove from active management; preserve versions, assignments and results |
| Draft, never published | Archive | Abandon draft without creating results |
| Archived, or closed without an approved transition | Edit/reopen/publish | Reject; reopening is not part of this prototype |

A quiz may remain published while a new draft revision is edited. A draft edit
does not demote or mutate the currently published quiz. Closing with a pending
revision freezes it; reopening/editing a closed quiz is outside this baseline.
Publication validates ownership of all selected versions and policy compatibility.
Use expected draft revision to prevent two author tabs silently overwriting edits.
Replay the same publication command without creating duplicate published versions.

### AUTH-04: Distribution

An author shall assign a specific published quiz version to an active learner.
Duplicate assignment requests return the existing assignment rather than reset
allowance. A new version requires an explicit new assignment and has its own
allowance; publishing alone never reassigns learners. Assignment deletion,
reassignment and revocation are deferred; access can be disabled at user level,
and closing a quiz stops new attempts.

The learner's assignment list shall distinguish not yet available, available,
in progress, completed/attempts remaining, exhausted and closed states without
exposing questions or keys before an authorized start.

## 5. Attempts, scoring and results

### ATT-01: Atomic start and stable presentation

Start shall validate active user/role, assignment ownership, quiz state,
availability and allowance in a transaction serialized on the assignment.
Require an idempotency key: a replay returns the original attempt even if it
has since finalized. A different start command resumes the one active attempt,
or creates a new attempt only if allowance remains.

Allocate the attempt number and fix all question content, option IDs/order,
points, policy, explicit pre-start timing choice (standard/adjusted/off), start
time and effective deadline atomically under the approved D04 timing amendment.
Resume/replay preserves the original choice/deadline; a new request cannot
extend an existing attempt. Preserve compatibility with pre-D04 snapshots.
Randomize the order of all
selected questions/options when configured; do not select a pool subset.
Refresh/resume returns exactly that presentation. Private scoring data is stored
server-side but excluded from the learner representation.

### ATT-02: Durable responses and conflicts

Each attempt question has one current response, initially unanswered at revision
zero. The save command carries a stable request ID, expected response revision,
and option ID or explicit null to clear. Lock the parent attempt before applying
response compare-and-swap. Validate the option belongs to that attempt question.

Commit response, incremented revision, timestamp and request acknowledgement
atomically; acknowledge only after commit. With the same request ID and normalized
payload, replay the original acknowledgement without incrementing the revision.
Reusing that ID with different content is a conflict. A new request with stale
expected revision returns a conflict plus the current authorized response.

Idempotency records are scoped to actor + command target + operation and contain
a payload fingerprint. Keep them throughout prototype record retention; automatic
cleanup requires a reviewed retry-window policy. Authenticate/authorize before
replaying them. Replaying a prior accepted save after expiry/finalization is
allowed as an acknowledgement only; return current attempt state separately and
never mutate the finalized data.

The client shall serialize saves per question, mark only the acknowledged local
edit as saved, and preserve a visibly unsaved newer edit. Show saving, saved,
offline/unsaved and conflict states. A failed or stale save cannot look successful.
On reconnect/resume, reconcile persisted state before retrying local edits; surface
cross-tab conflicts rather than silently choosing a winner. In-memory unsaved edits
are not guaranteed to survive refresh or browser closure; warn before discarding
them. Server-acknowledged answers must survive those events.

### ATT-03: Authoritative timing and expiration

Store UTC instants and the author's IANA scheduling zone. Start is allowed at or
after availability start and strictly before availability end. The deadline is the
earlier present bound of availability end and start plus duration for standard
timing; both absent means no deadline. Under the approved 27 October DEC-09
amendment, an explicit pre-start adjusted choice uses start plus the chosen
duration without the availability-end cap; timing off uses no attempt deadline.
Availability end still gates new starts in every mode. Persist the choice and
effective deadline atomically with the attempt; existing attempts never change.
Resolve ambiguous/nonexistent daylight-saving inputs explicitly.

Use authoritative database wall-clock time after acquiring the attempt lock,
not browser time or a transaction-start timestamp captured before waiting.
Admit a new save or voluntary finalization only strictly before the deadline.
A save admitted before the deadline may finish committing after it; requests
admitted at/after it cannot contribute answers. There is no offline grace period.

Expiry uses the same finalization logic as submit. A lifespan-managed periodic
task processes overdue attempts in bounded, lock-safe batches; relevant reads and
writes also reconcile overdue attempts. Process restart or multiple workers must
not extend an attempt or double-grade it. Closing a quiz does not change an
existing deadline. At a boundary, the browser may be wrong; the server response
must explain the authoritative state.

### ATT-04: Finalization

The editable state is `in_progress`; the only terminal state is `finalized`, with
reason `submitted` or `expired`. Before voluntary submission the browser waits
for pending saves and resolves failures/conflicts; finalization accepts no new
answer payload. Give a confirmation that warns about unanswered questions.

Lock the parent attempt; if already finalized, return its existing identity and
completion metadata. Otherwise determine reason/time, score persisted responses,
insert the unique Grade and update state/audit metadata in one transaction.
A failed transaction produces no partial grade or finalized state. A response
lost after commit is safe to retry. The returned confirmation must not bypass
result-release policy by including hidden scores or keys.

Use one lock order across commands; retry only transient database failures within
a bounded policy approved under DEC-08. Never retry a business conflict as if it
were a transient connection failure.

### SCORE-01: Objective grading

Grade only the delivered snapshot. A selected correct option earns its integer
points; incorrect or unanswered earns zero, with distinct outcome values.
No partial credit, penalties, pass/fail threshold, manual pending grade or regrade
is defined here. Grade stores earned/possible totals and per-question outcomes.
Display percentages to a consistent precision; never use rounded percentages to
calculate stored totals. Suggested display is one decimal place (DEC-03).

An expired attempt is graded from accepted saves, including all-unanswered work.
Scoring is a pure calculation; transaction/finalization ownership stays with the
attempt module. There is exactly one final grade per attempt.

### RESULT-01: Disclosure and history

Read results only after finalization and only for the permitted actor. For each
of score, correct answer and explanatory feedback, evaluate the pinned policy:
`after_finalization`, `after_availability_end`, or `never`.
The second mode requires a configured end time. Closing a quiz is not that time.

Before release, omit protected fields entirely from HTTP, HTML, client caches,
logs and generated learner fixtures. Do not send a full object and merely hide
it in the UI. Per-question correctness/awarded points are gated with answer-key
release because they can reveal the key. A released score can include aggregate
earned/possible points without item details. Explain to authors that released
explanatory text can itself reveal answers even when keys are hidden.

Learner history includes their attempts, presentation title/version, timestamps,
completion reason and policy-permitted result fields, with explicit withheld
status rather than a misleading zero. Current server time controls release on
every read; replaying a submit acknowledgement never replaces that check.

### RESULT-02: Author reporting

An author shall view their quiz's assigned learners, participation, in-progress
and finalized attempt counts, reasons and final scores, and inspect finalized
individual submissions. Identify quiz versions and multiple attempts explicitly;
do not merge a learner's attempts into an undocumented "best score."

Participation = distinct assigned learners with at least one started attempt;
completion = distinct assigned learners with at least one finalized attempt.
Show submitted versus expired counts separately. In-progress attempts have no
final score and do not enter score aggregates. Default score summaries are per
finalized attempt; label that denominator. Question response-distribution and
cohort analytics remain deferred. Unanswered and incorrect outcomes remain
distinct in authorized submission detail.

## 6. Data and input contracts

Stable public IDs are UUIDs. Wire fields use camelCase, timestamps are RFC 3339
UTC strings, duration is integer seconds, points and revisions are integers.
Python models may use snake_case internally with explicit aliases.

These bounds are approved under DEC-05; test both boundaries, not just typical
values. Trim required text for emptiness while preserving intentional content.

| Input | Proposed bound |
| --- | --- |
| Quiz title / bank name / category / tag | 1-200 / 1-100 / 1-100 / 1-50 characters when supplied |
| Question prompt / quiz instructions / feedback | 1-4,000 / 0-10,000 / 0-4,000 characters |
| Option text / options per MCQ | 1-1,000 characters / 2-10 options |
| Questions per published quiz / tags per question | 1-200 / 0-20 |
| Points per question including override | 0-10,000; quiz total must exceed zero |
| Duration / attempt limit | Null means unlimited; otherwise 60-604,800 seconds / 1-100 attempts |
| Learner pre-start accessible timing (DEC-09, 27 October amendment) | Standard, explicitly adjusted duration (60-6,048,000 seconds, supports at least 10 times the authored duration), or timing off; authored bounds unchanged; freeze choice/deadline per attempt |
| List page size | Default 25, maximum 100; stable ordering with a unique-ID tiebreaker |
| Request body | Maximum 256 KiB; return 413 above the limit; compose large quizzes using question-version references |

Do not silently coerce malformed IDs, fractional points, unknown enum values,
negative limits or invalid time zones into defaults. Missing optional limits
use documented defaults; explicit null has the meaning above. Reject extra
write fields that could inject owner IDs, scoring results or server timestamps.

The physical schema is delivered with migrations, not by this document. It shall
enforce the following independently of UI behavior:

| Record | Required identity/relationship and invariant |
| --- | --- |
| User | Unique issuer/subject; live application roles/status |
| QuestionBank, Question | Author ownership; version history; archive marker; references survive archive |
| QuestionVersion | Immutable content/options/key/default points/feedback; stable option IDs within revision |
| Quiz, QuizVersion, QuizQuestion | Draft revision separate from publication; immutable referenced question versions, order, effective points and rules |
| Assignment | Unique learner/version pair; pinned publication and allowance |
| Attempt | Unique assignment/attempt number; at most one in-progress attempt per assignment; frozen deadline/policy and explicit pre-start timing choice (D04 target; preserve existing snapshots) |
| AttemptQuestion, Response | Unique attempt position; fixed content/order/private scoring; one response per attempt question; monotonic response revision |
| Grade | Unique attempt reference; immutable totals/outcomes consistent with finalization |
| Command acknowledgement | Unique actor/target/operation/request key; fingerprint and stable acknowledgement |
| Integrity event | Actor/action/target/time/correlation; publication, access-change and finalization trace without answer/token content |

Use foreign keys and appropriate unique/check constraints. JSON snapshots do not
remove relational ownership and uniqueness checks. Web sessions use restricted
storage distinct from assessment access. Index owned lists, assignment eligibility,
attempt lookup/deadline and reporting paths. No tenant columns or empty tenant
abstractions are required for this single-organization baseline.

## 7. HTTP and frontend integration

The following is the proposed interface inventory. Paths are relative to
`/api/v1`; authentication/session redirects belong to the web module, not a
second business implementation. Resource schemas are implemented as Pydantic
models and exported as OpenAPI with each slice.

| Methods and paths | Contract responsibility |
| --- | --- |
| `GET /me`; `GET, POST /users`; `PATCH /users/{id}` | Current actor; administrator account management |
| `GET /eligible-learners` | Author-only minimal learner lookup for assignment |
| `GET, POST /question-banks`; `PATCH /question-banks/{id}` | Owned collections and organization |
| `GET, POST /questions`; `GET, PATCH /questions/{id}`; `POST /questions/{id}/archive` | Filtered question list, revision-producing edits, archive |
| `GET /questions/{id}/versions/{versionId}`; `POST /questions/{id}/preview` | Authorized exact revision and nonpersistent preview |
| `GET, POST /quizzes`; `GET, PATCH /quizzes/{id}` | Owned list, create and expected-revision draft edit |
| `POST /quizzes/{id}/preview`, `/publish`, `/close`, `/archive` | Explicit author commands; publish requires expected revision and idempotency key |
| `GET, POST /assignments`; `GET /assignments/{id}` | Role-filtered assignment views, create for named learner |
| `POST /assignments/{id}/attempts`; `GET /attempts/{id}` | Idempotent start/resume; full authorized learner presentation without keys |
| `PUT /attempts/{id}/responses/{attemptQuestionId}` | Response CAS and replay-safe acknowledgement |
| `POST /attempts/{id}/submission` | Finalize persisted answers; repeatable completion metadata |
| `GET /attempts/{id}/result`; `GET /me/attempts` | Release-filtered learner result/history |
| `GET /quizzes/{id}/results`; `GET /quizzes/{id}/submissions/{attemptId}` | Owning author's report and finalized submission |

Collection endpoints paginate and filter server-side; return `items` and
`nextCursor` (null when exhausted). Foreign/missing nested resource IDs return
404 without indicating ownership. Attempts use `attemptQuestionId`, never a
mutable question-bank ID, for response addressing.

### Save example

```json
{
  "requestId": "9e174008-8d7e-46e0-9bcd-dddf2da7ab05",
  "expectedRevision": 0,
  "selectedOptionId": "a1d150fb-435f-4ce1-9d6e-0c7277368ab1"
}
```

Successful response (including on exact retry):

```json
{
  "acknowledgement": {
    "requestId": "9e174008-8d7e-46e0-9bcd-dddf2da7ab05",
    "responseRevision": 1,
    "savedAt": "2026-10-20T14:00:00Z"
  },
  "attemptState": "in_progress",
  "serverTime": "2026-10-20T14:00:00Z"
}
```

Acknowledgement values are stable across retries; enclosing attempt state/time
are fresh. The request ID above is a command idempotency identifier, distinct from
the HTTP correlation ID in error/log envelopes. Start and publish use an
`Idempotency-Key` UUID header and the same fingerprint/replay rules.
Submission is idempotent by attempt identity, returning 200 for the existing
completion. Start returns 201 only for a new attempt, 200 for resume/replay.

### Error contract

```json
{
  "code": "RESPONSE_REVISION_CONFLICT",
  "message": "This answer changed in another session.",
  "requestId": "server-generated-correlation-id",
  "details": {
    "currentRevision": 2,
    "selectedOptionId": null
  }
}
```

| HTTP status | Cases / stable codes |
| --- | --- |
| 401 | Missing/expired/invalid identity: `UNAUTHENTICATED` |
| 403 | Denied role, disabled access or CSRF failure: `FORBIDDEN`, `ACCOUNT_DISABLED`, `CSRF_REJECTED` |
| 404 | Missing/concealed resource: `NOT_FOUND` |
| 409 | `RESPONSE_REVISION_CONFLICT`, `DRAFT_REVISION_CONFLICT`, `IDEMPOTENCY_CONFLICT`, `ATTEMPT_FINALIZED`, `DEADLINE_PASSED`, `ATTEMPT_LIMIT_REACHED`, `ASSESSMENT_UNAVAILABLE`, `INVALID_STATE` |
| 413 / 422 | `PAYLOAD_TOO_LARGE` / `VALIDATION_FAILED`; field paths and safe reasons, not raw submitted secrets/content |
| 429 | `RATE_LIMITED`; bounded client retry with `Retry-After` |
| 503 / 500 | `DEPENDENCY_UNAVAILABLE` / `INTERNAL_ERROR`; correlation ID, no implementation details |

Expired saves return authoritative status/deadline; they may trigger expiration
but never append their answer. Protected responses use private/no-store caching.
Internal error handling and all real routes must preserve the envelope; a schema
document alone does not implement it.

Generate the TypeScript client from OpenAPI once implemented contracts exist.
The server owns schemas; agents must not hand-edit generated clients or parallel
copies of Python DTOs. Frontend work can proceed with schema-validated fixtures
after its producer contract merges, but a fixture-only screen is not complete.
Default FastAPI `/docs` exposure is for local development; decide shared-environment
access with deployment policy. No compatibility/support promise for third parties
is made by `/api/v1`.

## 8. User-facing workflow requirements

| Surface | Required states and behavior |
| --- | --- |
| Login/navigation | Signed out, signing in, signed in, expired session, access disabled; role-appropriate navigation plus server checks |
| Administration | Loading/empty/error user list; provision/edit/status outcome; explicit partial-failure handling |
| Question bank/editor | Search/filter/pagination, no matches, validation, stale edit conflict, archive confirmation and retained-history explanation |
| Quiz editor/preview | Draft vs publication, explicit revision update, validation, schedule/time zone, policy preview, publish/close/archive confirmation |
| Assignment list | Eligibility/availability, attempts remaining, resume versus new attempt; disabled controls with explanations |
| Attempt | Stable ordered question navigation, current answer, visible per-question save state, authoritative timer, offline/conflict handling |
| Submission | Unanswered warning, pending-save guard, submitting, unknown outcome after disconnect, retry/resume confirmation |
| Learner history/result | Completion reason, withheld vs released fields, no fabricated zero for hidden scores |
| Author report/submission | Participation/completion definitions, version/attempt identity, empty/loading/error and final item outcomes |

All core flows require semantic labels, keyboard operation, visible focus,
screen-reader status announcements, responsive layout and non-color-only state.
Timer announcements must not flood assistive technology. Implement the pre-start
adjust/off controls and scheduled-availability interaction approved under DEC-09
on 27 October; a countdown alone is not an accessibility plan. Q02 must verify
the delivered behavior before any timed-accessibility conformance claim.

## 9. Quality and operational acceptance

| ID | Acceptance contract | PRD |
| --- | --- | --- |
| QUAL-01 | No loss of acknowledged saves after refresh, lost HTTP acknowledgement, app restart or agreed recoverable database restart; one grade under concurrent finalization; verify against real PostgreSQL | NFR-004, NFR-005 |
| QUAL-02 | Role/ownership/CSRF/token tests, strict input validation and secret/answer-log redaction; minimal identity data; approved retention before real records | NFR-007, NFR-008 |
| QUAL-03 | Core keyboard/screen-reader/responsive flows reviewed against WCAG 2.2 AA, including timing; record scope and remaining issues | NFR-009 |
| QUAL-04 | Critical transitions, grade calculations, disclosure, contracts and migrations have automated tests; existing type/build checks remain green | NFR-010 |
| QUAL-05 | Locked dependencies, environment-based configuration, separate web/backend images, single migration release step and documented health/readiness | NFR-011 |
| QUAL-06 | Correlated structured errors; save/finalization latency/failure metrics, expiry backlog and database pool pressure; no sensitive payload logging | NFR-012 |
| QUAL-07 | Documented backup and isolated restore exercise measures recovery time/data loss against approved RPO/RTO; cover assessment and identity/session dependencies | NFR-013 |
| QUAL-08 | Repeat concurrency tests with multiple backend processes; no in-memory authoritative state, duplicate grading or unbounded per-worker connection growth | NFR-014 |
| QUAL-09 | Benchmark candidate: 100 active learners, 20 questions, up to four options and 2 KB prompts, changed-answer save no more than every five seconds, 100 submissions within five seconds, 10,000 historical attempts | NFR-001, NFR-002, NFR-003 |
| QUAL-10 | Hosting/monitoring and incident ownership must be approved before any availability commitment; 99.5% monthly remains proposed, not a demo-measurable guarantee | NFR-006 |

For QUAL-09, record hardware, database size/pool limits, network/device profile,
ramp-up, p50/p95/p99, failures, CPU/memory and connection use. Candidate gates are
p95 reads <=300 ms and p75 usable quiz UI <=2.5 seconds, with zero correctness
failures. Define "usable" as controls rendered, initial authorized content loaded,
and a learner able to select/save an answer. Separate frontend measurement from
backend latency; exclude identity-provider latency only where explicitly agreed.
Numeric goals become release gates only after DEC-08 approval.

## 10. Acceptance catalogue and traceability

These are acceptance scenarios to implement, not results already obtained.
Work packages reference these IDs; expand them into automated/manual cases with
setup, action, expected result and retained evidence.

| Test ID | Scenario / required evidence | Software rules |
| --- | --- | --- |
| AT-01 | Login/logout/expiry, invalid issuer/audience, old token after account disable, denied direct calls | IAM-01, IAM-02 |
| AT-02 | In-app provisioning/role changes, last-admin protection, identity outage and safe retry; partial provisioning stays ineligible | IAM-03 |
| AT-03 | Both question types, input bounds, search/category/tags, owned-bank move/archive; another author cannot discover content | AUTH-01 |
| AT-04 | Same question reused in two quizzes; edit creates new revision; existing publications/attempts/grades remain unchanged | AUTH-01, AUTH-03 |
| AT-05 | Draft/preview/publish/close/archive, stale draft conflict, replayed publish, invalid state rejection, no preview side effects | AUTH-02, AUTH-03 |
| AT-06 | Assign named learner, duplicate assignment, unauthorized link, concurrent start/replay, attempt limit including expired attempts; both randomization flags on/off and stable refresh order | AUTH-04, ATT-01 |
| AT-07 | Saved answer refresh/restart, clear answer, duplicate save, stale revision, mismatched idempotency payload and cross-tab conflict | ATT-02 |
| AT-08 | Disconnect with unsaved edit, lost acknowledgement, reconnect/retry, pending-save submission guard and clear status announcements | ATT-02, ATT-04 |
| AT-09 | Exact schedule/deadline boundaries, daylight-saving ambiguity, delayed lock admission, quiz closure, expiry catch-up and worker races; standard/adjusted/off timing, schedule cutoff versus attempt deadline, immutable choice and server bounds | ATT-03 |
| AT-10 | Concurrent submit/save/expiry and response loss yield exactly one Grade and valid final snapshot; rollback yields no partial result | ATT-04, QUAL-01 |
| AT-11 | MCQ/true-false, point overrides, wrong/unanswered, zero-point items, invalid zero-total quiz, expired all-unanswered attempt | SCORE-01 |
| AT-12 | Every release mode at boundary times; inspect JSON/HTML/cache for hidden keys, explanations, item outcomes and grades | RESULT-01 |
| AT-13 | Learner history and author participation/completion/score/submission views agree on attempt/version identity and denominators | RESULT-01, RESULT-02 |
| AT-14 | Keyboard/screen-reader/responsive flows, usable pre-start timing adjustment/off controls and the approved schedule/deadline interaction; approval alone is not evidence | QUAL-03 |
| AT-15 | Reproducible deployment/migration, liveness vs readiness, structured errors/metrics and fail-closed dependency outages | QUAL-02, QUAL-05, QUAL-06 |
| AT-16 | Agreed workload/burst and multi-process runs meet approved thresholds without integrity/disclosure failures | QUAL-08, QUAL-09 |
| AT-17 | Isolated backup restore, recovered identity/access behavior, measured RPO/RTO and privacy/retention review | QUAL-02, QUAL-07, QUAL-10 |

| PRD requirements | Software rules | Primary evidence |
| --- | --- | --- |
| FR-001, FR-002, FR-003, FR-061 | IAM-01, IAM-02 | AT-01, AT-03, AT-06, AT-12 |
| FR-004 | IAM-03 | AT-02 |
| FR-010, FR-011, FR-012, FR-013 | AUTH-01 | AT-03, AT-11 |
| FR-014, FR-018 | AUTH-01, AUTH-03, ATT-01 | AT-04 |
| FR-015, FR-020, FR-021, FR-024, FR-025 | AUTH-02, AUTH-03 | AT-05, AT-11 |
| FR-022, FR-023 | AUTH-02, ATT-01, ATT-03 | AT-06, AT-09; randomization is also checked for stable resume |
| FR-026, FR-043 | AUTH-02, RESULT-01 | AT-12 |
| FR-030, FR-031 | AUTH-04, ATT-01 | AT-06 |
| FR-032, FR-033, FR-037, FR-038 | ATT-02, section 8 | AT-07, AT-08 |
| FR-034 | ATT-03 | AT-09 |
| FR-035, FR-036 | ATT-04 | AT-08, AT-10 |
| FR-040, FR-041, FR-042 | SCORE-01, ATT-04 | AT-10, AT-11 |
| FR-050, FR-051, FR-052, FR-056 | RESULT-01, RESULT-02 | AT-12, AT-13; no pending manual grade state while written grading is excluded |
| FR-062 | Section 6 | AT-04, AT-06, AT-13; organization IDs are not applicable to excluded tenancy |

Before calling the prototype complete, every P0 row and applicable quality rule
must have evidence or an explicitly approved release exception. A partial tracer
slice, a mock-only screen or passing scaffold checks do not satisfy that gate.
