# Phase 2: First complete assessment lifecycle

Use [BACKLOG.md](BACKLOG.md) for dependencies and the
[software specification](../SOFTWARE-SPECIFICATION.md) for exact behavior.
Each package delivers a small working slice, including its migrations, contract,
minimal UI and relevant tests unless explicitly pure calculation.

**Assignment, 21 October 2026:** C01 and C02 are accepted and `done`; the other six
packages below remain `active` under B.C., with explicit producer execution
gates. C02's accepted delivery is integrated by PR #9 at `03797bc`, verified
in D01's checkout on 22 October 2026 alongside its producer ancestors and wave
approval. S01 remains independently executable. Each later consumer must first include
its accepted producer commits. Use the
[copy-ready package prompts](PHASE-2-HANDOFFS.md) and
[approved demo defaults](../SOFTWARE-SPECIFICATION.md#phase-2-assignment-and-demo-defaults).
The first UI is untimed, unscheduled, one-attempt and nonrandomized, with score-only
or fully withheld release presets. Backend boundary fixtures still cover the
full applicable rules. Advanced controls and timed-accessibility approval are
not silently pulled into this wave.

The first demonstration may expose only approved fixed defaults for advanced
settings; unsupported controls remain absent and unsupported writes fail
explicitly. Immutable snapshots, authorization, durable saves, server timing,
idempotent finalization and result filtering are never deferred demo shortcuts.
Phase 3 completes all P0 configuration and management surfaces.

## C01: Versioned objective questions

**Rules:** AUTH-01, IAM-02; AT-03/04 (initial cases).  
**Surfaces:** question module/migrations/tests; minimal author question forms.

Create an owned bank and reusable question identity, immutable revision storage,
both objective question types, points/options/key/feedback validation and safe
author-only representations. Provide minimal create/read/edit selection UI and
exact-version retrieval. Search/tag/archive polish is completed by C03.

**Done:** both types round-trip through browser/backend/PostgreSQL; edits preserve
old revisions; author B cannot access author A's questions by list or direct ID.
Handoff version/option IDs and validated content shape for quiz composition.

## C02: Immutable quiz publication

**Rules:** AUTH-02/03; AT-04/05 (construction, preview, publication).  
**Surfaces:** quiz module/migrations/tests and minimal author composition/preview.

Compose a quiz from exact question versions with point overrides, validate positive
total/ownership, preview without attempts, and publish an immutable version with
expected draft revision and command replay protection. Support the same question
identity in multiple quizzes. Establish separate composition and policy-setting
files so C03/D04 can later extend them without competing edits.

**Done:** two quizzes reuse a question; preview has no persistence side effects;
replayed publish creates one version; stale edits conflict; subsequent question or
draft edits leave the published content unchanged. Handoff published version and
effective scoring/policy snapshot shapes. Advanced configuration UI waits for D04.

## D01: Assignment and attempt start

**Rules:** AUTH-04, ATT-01, timing admission from ATT-03; AT-06.  
**Surfaces:** distribution and attempt modules/migrations; author assignment action,
learner assignment list and start/resume route.

Provide minimal active-learner lookup and named assignment. Atomically enforce
eligibility/schedule/allowance, start request replay and one active attempt.
Persist fixed question/option order and private scoring definition; return only
the learner projection. Initialize deadline from approved policy, even if the
first UI exposes a limited default configuration.

**Done:** parallel starts consume one allowance, duplicate assignment cannot reset
it, old start request replay returns its original finalized or active attempt,
foreign IDs fail, and refresh returns stable content/order without keys. Handoff
the attempt identity, authorized snapshot and command-lock conventions.

## D02: Durable response save and resume

**Rules:** ATT-02, admission from ATT-03, section 7 save protocol; AT-07/08.
**Surfaces:** attempt response persistence/endpoints/tests and learner answer UI.

Implement response CAS, explicit clear, request fingerprint/acknowledgement ledger
and commit-before-success. Build question navigation, save-state announcements,
retry/reconnect reconciliation and cross-tab conflict handling. Persisted answers
must be distinguishable from local unsaved edits.

**Done:** exact retry does not increment revision; changed payload with reused key
conflicts; stale writes do not overwrite; acknowledged answers survive refresh
and application restart; lost acknowledgements reconcile; keys remain absent.
Handoff saved-response projection and pending-save/failure behavior for submission.

## S01: Pure objective scoring

**Rules:** SCORE-01, section 6 points bounds; AT-11.
**Surfaces:** scoring module and isolated calculation tests only.

Define a small typed calculation interface over immutable attempt questions and
responses. Calculate per-item outcome and earned/possible totals for both types,
including unanswered, cleared, incorrect and zero-point items. Accept already
validated scoring snapshots; reject impossible inputs at the appropriate seam.

**Done:** deterministic examples and boundary cases prove no partial credit or
float-based totals; changing external question-bank data cannot affect the inputs
or result. Handoff input/output types and scoring invariants to D03.

This is independent of the question/attempt persistence implementation once shared
contract conventions are established. It creates no Grade records or HTTP routes.

## D03: Finalization and expiration

**Decision:** user-facing timed interaction requires DEC-09 approval; backend
expiry fixtures can proceed while the first learner demonstration stays untimed.
**Rules:** ATT-03/04, SCORE-01; AT-09/10/11 initial cases.
**Surfaces:** attempt/grade migrations and finalizer; lifespan task; submit/expiry UI.

Use one transaction/lock path for voluntary submit, request-triggered expiry and
periodic expiry. Call S01, enforce unique grade, record completion reason and
integrity event, and return replay-safe metadata without hidden results.
Manage the bounded periodic task with startup/shutdown and multi-worker locking.
The browser waits for saves and handles unknown submit outcome with safe retry.

**Done:** concurrent save/submit/expiry yields one consistent grade; failed
transaction leaves no partial finalization; restart catches overdue attempts;
an exactly-at-deadline answer is rejected; response loss after commit is safe.
Handoff finalized-state projection and immutable grade access for R01.

## R01: Policy-filtered result

**Rules:** RESULT-01, IAM-02; AT-12.
**Surfaces:** result module/projection/tests and minimal learner result page.

Implement score/key/explanation policies over fixed attempt configuration,
including item-outcome redaction. Provide a result view that distinguishes
withheld from zero and submitted from expired. No web cache or submit payload
may bypass the same policy.

**Done:** all release modes have backend boundary tests; browser and serialized
payload inspection show no pre-release fields; foreign learners are denied;
withheld scores are not fabricated as zero. Handoff projections for R02 history.

## T01: First lifecycle acceptance

**Rules:** first lifecycle across AT-01 and AT-03 through AT-12.
**Surfaces:** `tests/e2e/`, synthetic fixtures and narrow integration fixes.

Run the real browser workflow: author creates both types, reuses a question in two
quizzes, previews/publishes, assigns learner, learner saves/refreshes/submits and
sees permitted results. Repeat with hidden results and an expired attempt.
Until DEC-09 is approved, demonstrate the expired result using a controlled
backend expiry fixture rather than treating timed learner UX as accepted.
Record which parts of the full acceptance catalogue remain for later packages.

**Done:** the integrated path uses real Keycloak, PostgreSQL and FastAPI rather
than mocked success; saves and repeated submit work after interruption; the demo
is reproducible from documented setup. Reviewers accept the lifecycle milestone.

This package closes integration gaps, not missing major implementations in its
predecessors. Those packages stay/revert to blocked or review until corrected.
Passing T01 is not the complete P0 or pilot-readiness gate.
