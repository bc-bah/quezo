# Phase 2 coding-agent handoffs

**Approved and assigned:** B.C., 21 October 2026.
All eight packages are `active` assignments, **not simultaneously executable**.
I02 is done, EX-I02-01 is closed, and the integrated foundation is
`553a2c8b77a770667f4cef6825f57c3b55f477ed` ([PR #7](https://github.com/bc-bah/quezo/pull/7)).
Every checkout also needs this approval/tracker update. Later consumers need
their accepted producer commits, not just the foundation commit.

| Package | Prompt | Required producer acceptance/integration |
| --- | --- | --- |
| C01 | [Versioned objective questions](#c01-dispatch-prompt) | I02, already done |
| C02 | [Immutable quiz publication](#c02-dispatch-prompt) | C01 |
| D01 | [Assignment and attempt start](#d01-dispatch-prompt) | C02 |
| D02 | [Durable response save and resume](#d02-dispatch-prompt) | D01 |
| S01 | [Pure objective scoring](#s01-dispatch-prompt) | F02, already done |
| D03 | [Finalization and expiration](#d03-dispatch-prompt) | D02 and S01 |
| R01 | [Policy-filtered result](#r01-dispatch-prompt) | D03 |
| T01 | [First lifecycle acceptance](#t01-dispatch-prompt) | R01 and I02 |

C01 and S01 may run independently. The persistence/UI chain is
C01 -> C02 -> D01 -> D02 -> D03 -> R01 -> T01, with S01 joining at D03.
The [backlog](BACKLOG.md), not this diagram, is authoritative for current status.

## Common execution contract

Each copy-ready prompt below requires reading this section. These are assignments
for one package per isolated session, not permission to launch successor agents.

- **Owner/integrator/reviewer:** B.C. Active records assignment. Implementation
  starts only after every listed producer is `done`, its accepted commit/PR and
  contract evidence are recorded, and those commits are included in the checkout.
  If a gate is unmet, report the exact waiting prerequisite and stop implementation;
  do not invent contracts, ask for redundant wave approval, or change the tracker
  to imply execution readiness. Reading/planning may proceed while waiting.
- **Approved scope:** DEC-01 through DEC-07 and the
  [Phase 2 demo defaults](../SOFTWARE-SPECIFICATION.md#phase-2-assignment-and-demo-defaults).
  Untimed/unscheduled, one attempt, no initial UI randomization, question points
  unless overridden; choose score-only or fully withheld release preset.
  Store independent policy fields. Backend fixtures exercise other approved
  combinations and deadline/release boundaries. Reject unsupported writes
  explicitly; no silent defaults for invalid input.
- **Later gates:** DEC-09 still blocks timed learner UX. Backend expiry must work;
  T01's expired-result scenario uses a controlled backend fixture, not timed UX.
  DEC-08 does not authorize automatic database retry loops or performance targets.
  Specified replay-safe client commands are still required. No Phase 3, pilot,
  real data, external provisioning or deployment is authorized.
- **Reuse producers:** F01 bounded `Database.transaction()` and migration rules;
  I01 live actor resolution/role/ownership checks, including inside write
  transactions; F02 schemas, sanitized errors and generated TypeScript client;
  F03 server-only session/facade; I02 Playwright fixtures and secret-safe reporter.
  Do not add another database/session/auth framework or parallel web business API.
- **Shared writes:** C01 initially owns the integration window. S01 touches only
  pure scoring/tests unless B.C. grants a narrow expansion. B.C. serializes
  later app/lifespan/router wiring, root navigation, manifests/locks/scripts,
  CI/Compose, common fixtures, generated artifacts and documentation. Domain
  migrations accompany their package; create from the actual latest head
  (foundation head `0004_identity`), retain a single chain, never edit applied
  revisions, and prove clean plus actual prior-head upgrades.
- **Validation:** use existing scripts and isolated local dependencies. For
  database/web slices run `npm run test:e2e -- --checks` before review; it owns
  dependencies and runs the established checks plus the browser suite. Add
  feature tests to the appropriate existing discovery paths; run new focused
  selectors during iteration. Regenerate interfaces with `npm run api:generate`
  and verify `npm run api:check` when HTTP contracts change. Preserve current
  type/build, identity, contract, migration and browser checks. S01's narrower
  pure-test validation is specified in its prompt; T01 requires the full run.
- **Evidence:** use actual PostgreSQL and real authenticated browser paths where
  required, not runtime substitutes. Keep secret/answer data out of logs, traces,
  HAR, screenshots and browser state artifacts. Missing services, skipped cases,
  schema fixtures and an opened PR are not acceptance. Record exact commands,
  versions, environment and results; distinguish automated/manual/unverified work.
- **Return:** use [AGENT-HANDOFF.md section 3](AGENT-HANDOFF.md#3-handoff-format),
  with every assigned criterion, actual producer commits, migration/contract
  changes and successor inputs. Stop after the package. Do not automatically
  commit, create a PR, dispatch successors or mark anything done. B.C. accepts
  integration and updates status/evidence; a changed producer contract requires
  an updated consumer handoff before that consumer continues.

## C01 dispatch prompt

```text
Implement Quezo work item C01: Versioned objective questions.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common execution contract and C01.
- docs/implementation/BACKLOG.md: C01 and I02.
- docs/implementation/02-CORE-LIFECYCLE.md: C01 only.
- docs/SOFTWARE-SPECIFICATION.md: Phase 2 approval, AUTH-01, IAM-02,
  sections 6-8, AT-03/04 initial cases and QUAL-02/04.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: module/data/HTTP boundaries.
- docs/DEVELOPMENT.md, postgres/migrations/README.md, tests/e2e/README.md,
  current scripts and docs/implementation/AGENT-HANDOFF.md section 3.

Owner/integrator/reviewer: B.C. C01 is active as assigned 21 October 2026.
Execution gate: I02 is done; start from accepted foundation
553a2c8b77a770667f4cef6825f57c3b55f477ed plus this approval/tracker update.
Verify the live checkout/records; this is not the pre-I02 scaffold.
Approved decisions: DEC-01 through DEC-07 and the Phase 2 demo defaults.

Permitted surfaces: owning question module under postgres/src/quezo_api/modules/,
question/bank/version migrations and focused backend tests; minimal author
bank/question create/read/edit/selection routes/forms and browser tests.
C01 owns the initial shared-file window for necessary router/client/navigation,
fixture, script/CI and documentation changes. S01 independently owns scoring;
do not edit its surfaces or invent quiz/attempt/grading routes.

Required inputs: existing Actor, get_actor/get_identity/resolve_actor and
role/owner helpers; Database.transaction; F02 strict DTO/error/pagination
conventions; server-only BackendFacade.client; I02 login/test fixtures.

Deliver all C01 criteria:
- Author-owned banks, stable question identity and immutable versions for
  single-answer MCQ and true/false. Enforce plain-text/bounds, nonnegative
  integer points, valid stable option IDs and exactly one valid correct option.
  True/false has exactly two semantic choices; reject malformed/extra writes.
- Minimal real UI to create, read, edit and select both types, with point and
  feedback fields. Edits create a new revision without mutating historical
  content/options/key. Serve exact versions for future quiz composition.
- Resolve live authority on every operation, including within write transactions.
  Scope lists and direct/nested ID lookups; author B cannot read/write author A's
  material. Administrator-only is not author. No learner answer-key exposure.
- Real PostgreSQL constraints/migrations, deterministic server schemas/generated
  client updates, visible safe validation/errors and browser round trips.
- Tests proving both types, invalid/boundary content, revision preservation,
  list/direct foreign-owner denial and real signed-in author interaction.

C03 still owns complete search/tag/archive management polish; no fake-success
routes for omitted features. Do not start C02 or schema scaffolding for it.
Follow the common migration and full database/web validation contract; extend
the existing browser fixtures rather than adding a second runner.
Return section 3 with AT-03/04 initial coverage, exact version/option IDs and
validated content contracts, migration head and C02 consumer instructions.
Stop after C01; no automatic commit/PR or successor dispatch.
```

## C02 dispatch prompt

```text
Implement Quezo work item C02: Immutable quiz publication.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common contract and C02.
- docs/implementation/BACKLOG.md: C02 and C01's accepted handoff/evidence.
- docs/implementation/02-CORE-LIFECYCLE.md: C02 only.
- docs/SOFTWARE-SPECIFICATION.md: Phase 2 defaults, AUTH-02/03, IAM-02,
  section 6 bounds, section 7 revision/idempotency contracts and AT-04/05.
- docs/DEVELOPMENT.md, postgres/migrations/README.md, tests/e2e/README.md,
  architecture module/publication rules and AGENT-HANDOFF.md section 3.

Owner/integrator/reviewer: B.C.; C02 is an active assignment dated 21 October 2026.
Execution gate: C01 must be done, accepted and integrated. Resolve its actual
commit/PR and question-version contract from the live backlog, and verify this
checkout includes it plus I02 foundation 553a2c8 and the Phase 2 approval.
If C01 is not accepted/integrated, report the exact gate and stop implementation;
do not implement against a guessed version DTO or treat active as executable.

Permitted surfaces: quiz module/migrations/tests, minimal author composition
and preview/publication UI, package browser cases. After C01 acceptance B.C.
serializes needed shared registration, generated artifacts, fixtures and docs.
Keep composition and policy settings in distinct feature files for later C03/D04;
do not add speculative generic frameworks or full Phase 3 controls.

Required inputs: C01's owned immutable question/version/option contract,
existing identity/transaction helpers, F02 schema/error/client conventions and
I02 real login fixtures. Use accepted producers, not copied parallel DTOs.

Deliver all C02 criteria:
- Compose from exact owned question versions, ordered references and optional
  integer point overrides. A selected question identity occurs at most once.
  Require a positive total and all approved content/policy bounds at publication.
- Initial UI uses approved untimed/no-window/one-attempt/nonrandomized defaults
  and score-only or fully withheld presets. Persist independent policy fields;
  validate compatibility, including finite end for after_availability_end.
  Other approved combinations are backend fixtures/tests, not timed learner UX.
- Preview uses learner presentation rules without creating assignments,
  attempts, grades, allowance consumption or reporting writes.
- Draft CAS and publish idempotency: authenticate/authorize before replay,
  fingerprint actor/target/operation/key, reject changed-key payload/stale edits,
  atomically publish one immutable version and retain retry acknowledgements.
- Allow one question in two quizzes and explicit new draft/version creation;
  later question/draft edits cannot mutate published versions or pinned content.
- Browser author composition/preview/publication and real-database concurrency,
  replay, ownership, stale-edit and snapshot immutability evidence.

Do not implement assignments/start/scoring or C03/D04's complete lifecycle/settings
UI. Unsupported commands/writes fail explicitly, never success-shaped placeholders.
Run the common database/web checks, clean/prior-head migration evidence and
deterministic API generation/drift checks. Return section 3 with AT-04/05 evidence,
published/effective-points/policy snapshot contracts, lock/replay rules and D01
inputs. Stop after C02; no automatic commit/PR or successor dispatch.
```

## D01 dispatch prompt

```text
Implement Quezo work item D01: Assignment and attempt start.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common contract and D01.
- docs/implementation/BACKLOG.md: D01 and C02's accepted evidence/contracts.
- docs/implementation/02-CORE-LIFECYCLE.md: D01 only.
- docs/SOFTWARE-SPECIFICATION.md: Phase 2 defaults, AUTH-04, ATT-01,
  ATT-03 admission, IAM-02, sections 6-7 and AT-06.
- Architecture distribution/attempt boundaries; docs/DEVELOPMENT.md,
  postgres/migrations/README.md, tests/e2e/README.md and handoff section 3.

Owner/integrator/reviewer: B.C.; D01 is assigned active on 21 October 2026.
Execution gate: C02 done, accepted and integrated, including C01 transitively.
Resolve actual producer commits/contracts from the live backlog and verify
their presence alongside I02 foundation 553a2c8 and the current wave approval.
An unmet gate means report the missing producer and stop implementation,
not fabricate a publication API or begin ahead of its integration.

Permitted surfaces: distribution/attempt modules, migrations and focused tests,
minimal author assignment action/active-learner lookup, learner assignment list
and start/resume UI, package browser tests. Shared edits are B.C.-serialized
after C02; preserve applied migrations and regenerate HTTP contracts normally.

Required inputs: C02 immutable published versions/effective points/policies,
current live actor/ownership helpers, F01 transaction conventions and F02 command
idempotency/errors. Private scoring snapshots remain server-side.

Deliver all D01 criteria:
- Assign a named active learner to an owned published version. The unique pair
  returns its existing assignment on duplicate requests, never resets allowance;
  publication alone never assigns or moves existing learners to a new version.
- Minimal learner lookup discloses only authorized assignment fields.
  Assignment lists distinguish availability/in-progress/completed/remaining/
  exhausted/closed states without pre-start questions or private keys.
- Serialize atomic starts on the assignment; validate live actor/role/ownership,
  quiz state, schedule and allowance. A successful start consumes one allowance.
  Concurrent starts produce one active attempt, not multiple consumed allowances.
- Same start idempotency key returns its original attempt even once finalized;
  a different command resumes the active attempt or starts only if permitted.
  Enforce actor/target/operation/key fingerprints and authorized replay.
- Freeze content, option/question IDs and order, points, policy, start/deadline
  and attempt number atomically; learner projection omits scoring definitions.
  Refresh/resume returns the stored order. Exercise configured ordering and
  finite-time/allowance boundaries in backend fixtures; keep actual demo untimed.
- Deadline is the earlier present end/duration bound, or null if both absent.
  Honor inclusive start/exclusive end; no browser clock authority.
- Real-database race/replay/duplicate/foreign-ID tests and actual author assigns,
  learner lists/starts/reloads in the browser with payload nondisclosure checks.

No save/finalization/result UI yet and no fake Grade or submission endpoint.
Run common database/web checks and migration/contract evidence. Return section 3
with AT-06 results, attempt/learner/private snapshot shapes, stable IDs, ownership
and lock/replay conventions for D02/D03. Stop after D01; no automatic commit/PR
or successor dispatch.
```

## D02 dispatch prompt

```text
Implement Quezo work item D02: Durable response save and resume.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common contract and D02.
- docs/implementation/BACKLOG.md: D02 and D01's accepted snapshot/locking handoff.
- docs/implementation/02-CORE-LIFECYCLE.md: D02 only.
- docs/SOFTWARE-SPECIFICATION.md: ATT-02, ATT-03 admission, section 7 save
  protocol/errors, IAM-02, QUAL-01/04 and AT-07/08.
- docs/DEVELOPMENT.md, migration runbook, tests/e2e/README.md, architecture
  durable-save protocol and AGENT-HANDOFF.md section 3.

Owner/integrator/reviewer: B.C.; D02 is assigned active on 21 October 2026.
Execution gate: D01 done and accepted; include its actual integrated commit/
snapshot/locks, its ancestors, I02 553a2c8 and current Phase 2 approval.
Resolve producer references from the live backlog; if missing, report the exact
gate and stop implementation. No guessed attempt endpoints or fixture-only producer.

Permitted surfaces: attempt response persistence/endpoints and migrations/tests,
learner answer/navigation/save-state UI, package browser scenarios and narrow
shared wiring/generated artifacts under B.C.'s post-D01 shared-file window.
Use the existing server-only facade, live actor and transaction/error contracts.

Deliver all D02 criteria:
- Initially unanswered revision-zero responses; option ID must belong to the
  frozen attempt question. Explicit null clears; malformed input is rejected.
- Lock the parent attempt before response CAS, using the shared command lock
  order. Use database wall-clock time after locking for deadline admission.
  Only a new write admitted strictly before deadline may change answers.
- Atomically persist response/revision/timestamp plus normalized request
  fingerprint and stable acknowledgement; return success only after commit.
  Same-key/same-payload replay does not increment revision; changed payload
  conflicts; stale expected revision returns the current authorized response.
- Authenticate/authorize before replay. Previously accepted save replays after
  expiry/finalization return only the original acknowledgement plus current
  attempt state; they cannot mutate finalized data. Retain request records.
- Browser serializes saves per question and marks only the acknowledged edit
  saved. Preserve visibly unsaved newer input; announce saving/saved/offline/
  conflict. Reconcile persisted state on reconnect before retries; no silent
  cross-tab winner. Warn before discarding unsaved local edits.
- Real PostgreSQL tests cover rollback, concurrent CAS, key reuse, admission/
  boundary cases, explicit clear and lost acknowledgement. Real browser proves
  acknowledged answers survive refresh/restart, reconciliation and safe errors.
  Inspect learner payloads for absence of keys/private scoring fields.

D03 owns actual finalization/expiry reconciliation; do not fabricate final
grades here. Preserve admission semantics and hand off the boundary explicitly.
No timed learner UX, automatic database retry policy or success-shaped failures.
Run common database/web checks, migration upgrade and API drift checks.
Return section 3 with AT-07/08 evidence, saved-response/ack shapes and pending-
save/conflict/failure behavior for D03. Stop after D02; no automatic commit/PR
or successor dispatch.
```

## S01 dispatch prompt

```text
Implement Quezo work item S01: Pure objective scoring.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common contract and S01.
- docs/implementation/BACKLOG.md: S01 and done F02.
- docs/implementation/02-CORE-LIFECYCLE.md: S01 only.
- docs/SOFTWARE-SPECIFICATION.md: SCORE-01, section 6 point bounds,
  DEC-03 and AT-11; accepted Phase 2 scope.
- Architecture scoring boundary, docs/DEVELOPMENT.md F02 conventions,
  current Python manifest/checks and AGENT-HANDOFF.md section 3.

Owner/integrator/reviewer: B.C.; S01 is assigned active on 21 October 2026.
Execution gate: F02 is already accepted/integrated. Start on current accepted
foundation 553a2c8 plus the Phase 2 approval/tracker update. C01 and attempt
persistence are NOT new prerequisites; do not invent dependencies on them.
S01 can run alongside C01 without touching its shared surfaces.

Permitted surfaces: pure scoring module under postgres/src/quezo_api/modules/
and isolated scoring tests under postgres/tests/. No database, HTTP routes,
Grade persistence, web UI, migrations, root fixtures, manifests or CI changes
without B.C.'s explicit narrow shared-file assignment.

Required inputs: existing UUID/strict nonnegative integer conventions, not an
unimplemented attempt database model. Define a small typed pure interface over
already validated immutable question/response snapshots. D03 later adapts the
accepted persistence snapshot to it; do not duplicate another package's DTOs.

Deliver all S01 criteria:
- Deterministic scoring for single-answer MCQ and true/false using only delivered
  snapshot options/key/points and saved response, never current question-bank data.
- Correct answer receives integer points, incorrect/unanswered receive zero;
  cleared null is unanswered, not incorrect. Keep outcome distinctions explicit,
  including correct zero-point items and all-unanswered expired inputs.
- Exact integer earned/possible totals and per-item outcomes; no partial credit,
  penalties, floats in totals, pass/fail thresholds, manual pending grades,
  regrading, IO, database connections or global mutable state.
- Define responsibility for invalid/duplicate/inconsistent input at the typed
  validation seam; impossible input must not become a silently plausible score.
- Examples and boundary tests cover both types, maximum point bounds,
  unanswered/clear/wrong/correct/zero-point mixes, deterministic repeated calls
  and independence from external mutable question-bank data.

Validate with uv run --directory postgres --locked mypy and the exact new
scoring test file(s) via uv run --directory postgres --locked pytest.
Pure scoring tests must not require a database or identity service. Record the
actual selector and results; do not run or claim unrelated browser acceptance.
Return section 3 with AT-11 evidence, input/output types, validation assumptions
and invariants for D03. Stop after S01; no automatic commit/PR, no Grade writes
and no successor dispatch.
```

## D03 dispatch prompt

```text
Implement Quezo work item D03: Finalization and expiration.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common contract and D03.
- docs/implementation/BACKLOG.md: D03 and BOTH D02/S01 accepted handoffs.
- docs/implementation/02-CORE-LIFECYCLE.md: D03 only.
- docs/SOFTWARE-SPECIFICATION.md: ATT-03/04, SCORE-01, IAM-02, QUAL-01/04/08,
  section 7 submission/errors and AT-09/10/11 initial cases.
- Architecture finalization/time rules; docs/DEVELOPMENT.md, migration runbook,
  tests/e2e/README.md and AGENT-HANDOFF.md section 3.

Owner/integrator/reviewer: B.C.; D03 is assigned active on 21 October 2026.
Execution gate: BOTH D02 and S01 must be done, accepted and integrated. Resolve
their exact commits/contracts in the live backlog; include them and their
ancestors plus I02 553a2c8 and the Phase 2 approval. If either is absent, report
the missing producer and stop implementation. Do not fork the scoring rules.

Permitted surfaces: attempt/Grade persistence, finalization/expiry handlers,
bounded lifespan-managed expiry task, migrations and targeted concurrency tests;
minimal submit/confirmation/expired-state UI and real browser cases.
B.C. serializes shared lifespan/fixtures/generated contracts and migration head
after both producers integrate. Reuse their concrete transaction/lock conventions.

Required inputs: D02 persisted responses, admission/CAS/acknowledgements and
pending-save UI contract; S01 pure scoring interface; frozen D01 attempt policy.
Use live authority inside write transactions and one agreed command lock order.

Deliver all D03 criteria:
- One transaction/lock path for voluntary submit, request-triggered expiry and
  bounded periodic expiration. Lock the parent, then read database wall-clock
  time; at/after deadline finalize as expired and admit no new answer.
- Score ONLY persisted accepted responses through S01. Insert one unique
  immutable Grade, per-item results and minimal integrity event; update state
  and submitted/expired reason atomically. Failure leaves no partial result.
- Already-finalized calls return the existing completion metadata safely.
  Submission accepts no answer payload and leaks no withheld score/key/feedback.
  A lost response after commit is safely retryable without duplicate grading.
- Browser waits for pending saves, resolves failures/conflicts, confirms unanswered
  items and handles unknown submission outcome with safe retry. The live demo
  remains untimed; no countdown/timing adjustment UX while DEC-09 is held.
- Lifecycle-managed worker has bounded batches, safe startup/shutdown/cancellation
  and explicit dependency errors; multiple workers cannot double-grade. Restart
  catches overdue attempts. No external queue or unapproved DB retry loop.
- Real PostgreSQL races: save/submit/expiry, exact-deadline admission, transaction
  rollback, duplicate/replayed submit, response loss and restart catch-up.
  Keep before-deadline admitted writes valid even if commit crosses deadline.
- Real browser voluntary-submit proof; controlled backend expiry fixtures prove
  expired projections without claiming timed accessibility acceptance.

No history/reporting, result-release bypass or regrade/admin override. Follow
common full checks plus focused real-database concurrency/worker evidence.
Return section 3 with AT-09/10/11 initial results, finalized-state/immutable Grade
interfaces, locks/worker lifecycle and R01 inputs. Stop after D03; no automatic
commit/PR or successor dispatch.
```

## R01 dispatch prompt

```text
Implement Quezo work item R01: Policy-filtered result.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common contract and R01.
- docs/implementation/BACKLOG.md: R01 and D03's accepted Grade/state handoff.
- docs/implementation/02-CORE-LIFECYCLE.md: R01 only.
- docs/SOFTWARE-SPECIFICATION.md: RESULT-01, IAM-02, ATT-04 confirmation boundary,
  sections 6-8, QUAL-02 and AT-12.
- Architecture release/disclosure rules; docs/DEVELOPMENT.md, migration runbook,
  tests/e2e/README.md and AGENT-HANDOFF.md section 3.

Owner/integrator/reviewer: B.C.; R01 is assigned active on 21 October 2026.
Execution gate: D03 done, accepted and integrated, including D02/S01 ancestors.
Resolve actual producer commits/types from the backlog and verify this checkout
also includes I02 553a2c8 and current Phase 2 approval. If missing, report the
specific gate and stop implementation; never invent a Grade endpoint/shape.

Permitted surfaces: result module/projections/tests and minimal learner result
route/UI, generated contracts and browser scenarios. Narrow shared edits are
B.C.-serialized after D03. Reuse existing Grade/policy storage; no new result
database or speculative schema, history/reporting UI or A01 administration.

Required inputs: D03 immutable Grade, finalized reason/time and frozen attempt
policy; existing actor/ownership helpers, server clock, safe DTOs and web facade.

Deliver all R01 criteria:
- Authorized result reads only after finalization, scoped to the permitted
  learner. Foreign/missing resources do not disclose existence or content.
- Independently evaluate score/key/explanation after_finalization,
  after_availability_end or never on every read against frozen policy and
  authoritative server time. After-availability mode requires finite end;
  closing a quiz is not release time. Test immediately before/at/after the bound.
- Omit unreleased fields from serialized HTTP and HTML, not just UI visibility.
  Item correctness/awarded points require answer-key release; released aggregate
  score need not expose item results. Respect independent explanation policy.
- Browser distinguishes withheld from zero and submitted from expired; no
  fabricated zero score. Use consistent percentage display derived from exact
  integer totals, never alter grades using rounded values.
- Private/no-store result responses, safe caches/logs/fixtures, and no submission
  acknowledgement or web route bypass of the same disclosure policy.
- Real backend tests for every policy mode/combination/boundary, ownership,
  pre-finalization denial and payload omissions. Real browser proves approved
  score-only and fully withheld presets; inspect serialized payloads and DOM.
  Finite-end cases remain backend fixtures while timed learner UX is held.

R02 owns history and author reporting. Do not expand permissions or return full
server scoring objects to the client. Follow common database/web/contract checks.
Return section 3 with AT-12 results, safe result projections, omission semantics
and T01/R02 consumer instructions. Stop after R01; no automatic commit/PR or
successor dispatch.
```

## T01 dispatch prompt

```text
Implement Quezo work item T01: First lifecycle acceptance.

Read:
- docs/implementation/PHASE-2-HANDOFFS.md: common contract and T01.
- docs/implementation/BACKLOG.md: T01, R01, I02 and transitive lifecycle evidence.
- docs/implementation/02-CORE-LIFECYCLE.md: T01 and predecessor acceptance seams.
- docs/SOFTWARE-SPECIFICATION.md: Phase 2 defaults, IAM-01/02, AUTH-01 through
  AUTH-04, ATT-01 through ATT-04, SCORE-01, RESULT-01 and AT-01/03-12.
- docs/DEVELOPMENT.md, tests/e2e/README.md, migration runbook and
  AGENT-HANDOFF.md section 3.

Owner/integrator/reviewer: B.C.; T01 is assigned active on 21 October 2026.
Execution gate: R01 and I02 must be done and accepted/integrated; verify the
transitive C01/C02/D01/D02/S01/D03 producers and exact evidence/commit chain too.
I02 foundation 553a2c8 alone is insufficient. Resolve actual merged producers
from the live backlog; if missing or materially incomplete, report them and
stop. Active assignment does not permit building the missing packages inside T01.

Permitted surfaces: tests/e2e/ scenarios/fixtures/runbook, focused evidence and
narrow demonstrated integration fixes in owning producer modules. Shared
orchestration/scripts/CI/docs are B.C.-serialized after R01 integration.
No broad refactor, full Phase 3 features, new schema model or mock-success bridge.
Reopen a defective predecessor for B.C.'s review if a major implementation is
missing; do not mark its unverified criteria passed under an integration label.

Required inputs: all accepted real question/publication/assignment/attempt/
save/scoring/finalization/result interfaces; existing I02 Playwright login/
privatePage/application fixtures and secret-safe reporting. Use fresh contexts
for identity changes because local logout intentionally preserves provider SSO.

Deliver all T01 criteria with actual browser -> web -> FastAPI -> PostgreSQL
and real Keycloak identities:
- Author creates both objective types; edits preserve old versions; reuse a
  question in two quizzes, preview without attempts, publish and assign learner.
- Learner starts, navigates answers, saves, refreshes/resumes, confirms pending
  saves, submits exactly once and sees permitted score-only results.
- Repeat using the fully withheld preset; no hidden fields in HTTP/HTML/caches.
  Demonstrate expired outcome with an explicitly controlled backend expiry
  fixture, never a user-facing timed-assessment or accessibility acceptance claim.
- Exercise interrupted/lost save or submit acknowledgements, retry, durable
  persisted answers and one final grade. Preserve stable content/order.
- Cover foreign-author/learner denial and current identity checks without
  bypasses. Retain the accepted I02 login/logout/CSRF/outage regressions.
- Separate actual browser evidence from backend concurrency/boundary fixtures;
  reuse producer tests for race/clock/scoring guarantees rather than asserting
  that a happy path establishes integrity under concurrency.
- Produce a reproducible foundation-to-lifecycle demo and exact per-AT coverage,
  noting initial/partial cases and what C03/A01/D04/R02/Q01/Q02 still own.
  Full search/archive/admin/settings/history/reporting/accessibility/load/
  recovery acceptance is not silently declared complete.

Run npm run test:e2e -- --checks unfiltered with real owned dependencies;
ensure the new lifecycle scenarios are included rather than only the old 16
identity cases. Record exact case counts/names, commands, environment and outcome.
Run any additional focused producer checks needed by integration fixes, regenerate
and verify contracts if changed, and show clean/prior-head migrations for any
authorized migration. Skips/missing services/fixtures-only journeys are not passes.
Keep credentials, assessment keys and raw browser state out of retained artifacts.

Return the complete section 3 handoff plus a lifecycle acceptance matrix:
AT-01 and initial AT-03 through AT-12 scenarios, evidence links, explicit gaps,
producer commits and repeatable demo command. B.C. accepts the milestone after
review. Stop after T01; no automatic commit/PR, Phase 3 dispatch, deployment or
pilot-readiness claim.
```
