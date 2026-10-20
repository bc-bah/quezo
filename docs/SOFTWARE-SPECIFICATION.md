# Quezo software specification

**Version:** 0.1  
**Date:** 20 October 2026  
**Status:** Proposed implementation baseline; behavioral decisions await approval.  
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

**Existing software:** a Next.js placeholder, a FastAPI liveness endpoint and its
OpenAPI documentation, locked toolchains, optional database/identity containers,
and scaffold checks. None of the assessment requirements below is implemented.

**Excluded:** multiple tenants, cohorts, anonymous access, written/manual grading,
regrading, CSV/import/export, pool selection, external API support, LMS integration,
AI/proctoring and media/community features. Minimal integrity events are included;
a general audit-management product is not.

## 2. Decision register

Confirmed: P0 scope, one organization, low-stakes use, Next.js/React + Python/FastAPI,
PostgreSQL, Keycloak and Docker. All decisions below are **proposed/open**.
Record approval date, approver and any amendments in the final column. An empty
approval means the decision is not approved.

| ID | Proposed baseline / unresolved choice | Required before | Owner | Approval |
| --- | --- | --- | --- | --- |
| DEC-01 | Named-learner assignments; one assignment per learner/version; no self-enrollment; one active attempt per assignment; starts and expirations consume allowance | Domain implementation | Product | Pending |
| DEC-02 | Availability end caps duration; no grace period or late offline answers; close blocks new starts but preserves active deadlines; archived quizzes are read-only and retain history | Domain implementation | Product | Pending |
| DEC-03 | Single-answer MCQ and true/false; nonnegative integer points, no penalties/partial credit, positive quiz total | Domain implementation | Product | Pending |
| DEC-04 | Independent score/key/explanation release after finalization, after availability end, or never; per-item grading is gated with answer-key release | Result and publication implementation | Product | Pending |
| DEC-05 | Input bounds in section 6, unlimited values, revision protocol and idempotency retention; retained request records have no automatic cleanup in the prototype | Contract implementation | Product + Engineering | Pending |
| DEC-06 | Server-side web sessions; application roles/status authoritative on each request; Keycloak owns identity; review realm/client, session/JWT libraries and administration privileges | Identity implementation | Identity + Engineering | Pending |
| DEC-07 | Select PostgreSQL driver, migration runner, session storage implementation and TypeScript contract generator; no ORM is assumed | Foundation implementation | Engineering | Pending |
| DEC-08 | Approve benchmark environment/profile, performance gates, logging/metric tooling, bounded retry and rate-limit settings | Hardening/load work | Engineering + Operations | Pending |
| DEC-09 | Approve timed-assessment accessibility approach, including timing adjustment/extension or a justified applicable exception; unlimited quizzes alone do not establish WCAG conformance | Timed UX implementation | Product + Accessibility | Pending |
| DEC-10 | Name first pilot audience; approve hosting, data retention/deletion, incident ownership, backup RPO/RTO and any availability commitment | Real-data/shared pilot | Product + Privacy + Operations | Pending |
| DEC-11 | Name review/merge/release approvers and assign delivery dates/budget | Scheduling and release commitment | Product + Engineering | Pending |

An authorized synthetic-data development wave can proceed once its relevant
decisions are approved; unresolved pilot commitments do not authorize real data.
The initial baseline work item identifies exactly which decisions each wave needs.

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
points, policy, start time and deadline atomically. Randomize the order of all
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
earlier present bound of availability end and start plus duration; both absent
means no deadline. Resolve ambiguous/nonexistent daylight-saving inputs explicitly.

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

These bounds are proposed under DEC-05; test both boundaries, not just typical
values. Trim required text for emptiness while preserving intentional content.

| Input | Proposed bound |
| --- | --- |
| Quiz title / bank name / category / tag | 1-200 / 1-100 / 1-100 / 1-50 characters when supplied |
| Question prompt / quiz instructions / feedback | 1-4,000 / 0-10,000 / 0-4,000 characters |
| Option text / options per MCQ | 1-1,000 characters / 2-10 options |
| Questions per published quiz / tags per question | 1-200 / 0-20 |
| Points per question including override | 0-10,000; quiz total must exceed zero |
| Duration / attempt limit | Null means unlimited; otherwise 60-604,800 seconds / 1-100 attempts |
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
| Attempt | Unique assignment/attempt number; at most one in-progress attempt per assignment; frozen deadline/policy |
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
Timer announcements must not flood assistive technology. Final timing behavior
depends on DEC-09; a countdown alone is not an accessibility plan.

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
| AT-09 | Exact schedule/deadline boundaries, daylight-saving ambiguity, delayed lock admission, quiz closure, expiry catch-up and worker races | ATT-03 |
| AT-10 | Concurrent submit/save/expiry and response loss yield exactly one Grade and valid final snapshot; rollback yields no partial result | ATT-04, QUAL-01 |
| AT-11 | MCQ/true-false, point overrides, wrong/unanswered, zero-point items, invalid zero-total quiz, expired all-unanswered attempt | SCORE-01 |
| AT-12 | Every release mode at boundary times; inspect JSON/HTML/cache for hidden keys, explanations, item outcomes and grades | RESULT-01 |
| AT-13 | Learner history and author participation/completion/score/submission views agree on attempt/version identity and denominators | RESULT-01, RESULT-02 |
| AT-14 | Keyboard/screen-reader/responsive flows and approved timed-assessment accessibility behavior | QUAL-03 |
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
