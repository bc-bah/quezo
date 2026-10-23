# Implementation backlog

**Source of truth:** package status, prerequisites, assignment and completion
evidence live here. Behavior lives in the [software specification](../SOFTWARE-SPECIFICATION.md);
package descriptions live in the linked phase files.

Status values: `planned`, `ready`, `active`, `review`, `blocked`, `done`.
`ready` means prerequisites and decision gates are satisfied, not that an agent
has permission to start. `active` records an explicit assignment; for a
preassigned wave it does not waive the separate execution gate. `review` means
work is available but not yet accepted.
`done` requires the plan's integration/evidence definition. Replace `-` with actual
owner, PR/commit and evidence links as work progresses. A blocked item records the
specific decision or predecessor, not a generic "waiting."

**Current state (23 October 2026):** I02 is `done`; EX-I02-01 is closed after
B.C.'s completion confirmation and review of merged browser/CI evidence.
C01 is `done` following B.C.'s explicit acceptance/integration confirmation.
C02 is also `done` at B.C.'s explicit direction, accepting the verified local
delivery and handoff. Integration verified on 22 October 2026: C02
[PR #9](https://github.com/bc-bah/quezo/pull/9) merged at
`03797bcbb545ec188da941ff6bb02e380f5b9f1b`, including implementation `67ce98a`.
D01's checkout contains this merge, C01 `e66f459`, I02 `553a2c8` and
wave approval `49eb37b`; its producer checkout gate is satisfied.
D01 is `done`: B.C. confirmed review, acceptance and integration on 22 October
2026 at merge `b5751a94ce2ab36be8add8070bbbd99573175d0a` (implementation
`cbb74f5`, [PR #10](https://github.com/bc-bah/quezo/pull/10)). Its frozen snapshot
and command lock contract are accepted; D02's producer gate is satisfied.
D02 and S01 are `done`: B.C. confirmed completion, acceptance and integration
on 22 October 2026 and directed this tracking reconciliation and D03 execution.
D02 merge `c7d6f7e0d9785e220530536078241725b3588547` includes implementation
`fbe93da` and browser follow-up `a82bc36`; S01 merge
`c9448f78cd6aee397763d37e8d33f8004a441862` includes implementation `00195df`.
Both merges, D01/C02/C01 ancestors, I02 `553a2c8` and Phase 2 approval
`49eb37b` are present in D03's checkout. Its execution gate is satisfied.
D03 is `done`: B.C. confirmed review and remote-main integration on 23 October
2026 and directed acceptance reconciliation and R01 execution.
[PR #13](https://github.com/bc-bah/quezo/pull/13) merged at
`0cfbff7bb65c9bbad2be049df729459c516516b0`, including implementation `9ff05f8`.
R01's checkout includes this merge, all producers above, I02 `553a2c8` and
Phase 2 approval `49eb37b`. The immutable Grade/finalized-state handoff is accepted
and R01's execution gate is satisfied. R01 and T01 remain `active`; T01 still
waits for accepted/integrated R01.
No successor dispatch is implied. B.C. owns integration,
review/merge and shared-file coordination for this wave; later release holds remain.
Prerequisites are logical AND. `-` means none; phase order is not an additional
dependency. Decision gates still apply as specified by the package.

Approval evidence: [G00](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026),
[second wave](../SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01) and
[I02 assignment/exception](../SOFTWARE-SPECIFICATION.md#i02-assignment-and-completion-exception).
Current approval: [Phase 2 assignment/defaults](../SOFTWARE-SPECIFICATION.md#phase-2-assignment-and-demo-defaults).
Current assignments: [eight copy-ready prompts](PHASE-2-HANDOFFS.md).
Integrated foundation baseline: `553a2c8b77a770667f4cef6825f57c3b55f477ed`;
migration head `0004_identity`. Consumers must also include their later producer
commits, recorded on acceptance. Accepted C01 merge
`e66f459c5a6b225bd3d1b4bbce6b5b87de67974c` advances the migration head to
`0005_questions` and completes C01's initial shared-file window. S01 may run
independently on its pure scoring/test surfaces. C02 and later shared writes
and migrations remain serialized along the lifecycle chain by B.C.

| ID | Phase | Package | Prerequisites | Status | Owner | PR/commit and evidence / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| G00 | 0 | [Approve implementation baseline](01-FOUNDATIONS.md#g00-approve-implementation-baseline) | - | done | B.C. | [Original scoped approval](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026); DEC-06/07 holds superseded by [second-wave approval](../SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01) |
| F01 | 1 | [Database and integration-test foundation](01-FOUNDATIONS.md#f01-database-and-integration-test-foundation) | G00 | done | B.C. | Accepted 20 October 2026; [PR #3](https://github.com/bc-bah/quezo/pull/3), merge `8732328`; [local evidence](../DEVELOPMENT.md#f01-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39505683430); 51 tests at F01, original 41 database cases retained in F02 |
| F02 | 1 | [Contract and error foundation](01-FOUNDATIONS.md#f02-contract-and-error-foundation) | G00 | done | B.C. | Accepted 20 October 2026; [PR #4](https://github.com/bc-bah/quezo/pull/4), merge `5f31412`; [local evidence](../DEVELOPMENT.md#f02-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39509963069); 138 Python tests and 2 tooling/client tests; approved actor contract |
| F03 | 1 | [Web session and navigation foundation](01-FOUNDATIONS.md#f03-web-session-and-navigation-foundation) | F01, F02 | done | B.C. | Accepted 20 October 2026 with [EX-I02-01](#ex-i02-01-native-loginlogout-origin), now closed in I02; [PR #5](https://github.com/bc-bah/quezo/pull/5), merge `b1a2fe0`; [local evidence](../DEVELOPMENT.md#f03-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39519807448); 10 web tests, 154 Python cases |
| I01 | 1 | [Identity and authorization backend](01-FOUNDATIONS.md#i01-identity-and-authorization-backend) | F01, F02 | done | B.C. | Accepted 20 October 2026; [PR #6](https://github.com/bc-bah/quezo/pull/6), merge `6ef734f`; [local evidence](../DEVELOPMENT.md#i01-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39530379835); 262 Python cases, 10 web tests and actual-Keycloak HTTP integration; combined browser proof accepted in I02 |
| I02 | 1 | [Integrated login and access gate](01-FOUNDATIONS.md#i02-integrated-login-and-access-gate) | F03, I01 | done | B.C. | Accepted 21 October 2026; [PR #7](https://github.com/bc-bah/quezo/pull/7), merge `553a2c8`; [16-browser-case evidence](../DEVELOPMENT.md#i02-integrated-browser-gate), [hosted browser and matrix CI](https://github.com/bc-bah/quezo/actions/runs/39564745343); EX-I02-01 closed; AT-01 foundation gate accepted |
| C01 | 2 | [Versioned objective questions](02-CORE-LIFECYCLE.md#c01-versioned-objective-questions) | I02 | done | B.C. | Accepted/integration confirmed by B.C. 21 October 2026; [PR #8](https://github.com/bc-bah/quezo/pull/8), merge `e66f459`; [handoff, evidence and exact-version contract](../DEVELOPMENT.md#c01-versioned-objective-questions), [hosted browser and matrix CI](https://github.com/bc-bah/quezo/actions/runs/39596126267); migration `0005_questions`; initial AT-03/04 question scope accepted |
| C02 | 2 | [Immutable quiz publication](02-CORE-LIFECYCLE.md#c02-immutable-quiz-publication) | C01 | done | B.C. | Accepted 21 October 2026; [PR #9](https://github.com/bc-bah/quezo/pull/9), merge `03797bc`; [accepted local handoff/evidence](../DEVELOPMENT.md#c02-immutable-quiz-publication): 449 Python, 166 database and 24 browser cases passed; migration `0006_quizzes`; [prompt](PHASE-2-HANDOFFS.md#c02-dispatch-prompt) |
| D01 | 2 | [Assignment and attempt start](02-CORE-LIFECYCLE.md#d01-assignment-and-attempt-start) | C02 | done | B.C. | Review/acceptance/integration confirmed by B.C. 22 October 2026; [PR #10](https://github.com/bc-bah/quezo/pull/10), merge `b5751a9`, implementation `cbb74f5`; [accepted snapshot/locking handoff and evidence](../DEVELOPMENT.md#d01-assignment-and-attempt-start): 475 Python, 192 database-suite and 25 browser cases passed; migration `0007_attempt_start` |
| D02 | 2 | [Durable response save and resume](02-CORE-LIFECYCLE.md#d02-durable-response-save-and-resume) | D01 | done | B.C. | Acceptance/integration confirmed 22 October 2026; [PR #11](https://github.com/bc-bah/quezo/pull/11), merge `c7d6f7e`, implementation `fbe93da`, browser follow-up `a82bc36`; [accepted save/admission/CAS/UI handoff and evidence](../DEVELOPMENT.md#d02-durable-response-save-and-resume): 500 Python, 217 database-suite and final 26 browser cases passed; migration `0008_responses` |
| S01 | 2 | [Pure objective scoring](02-CORE-LIFECYCLE.md#s01-pure-objective-scoring) | F02 | done | B.C. | Acceptance/integration confirmed 22 October 2026; [PR #12](https://github.com/bc-bah/quezo/pull/12), merge `c9448f7`, implementation `00195df`; [accepted pure scoring contract](../DEVELOPMENT.md#s01-pure-objective-scoring); executable evidence in `postgres/tests/test_scoring.py`; no migration |
| D03 | 2 | [Finalization and expiration](02-CORE-LIFECYCLE.md#d03-finalization-and-expiration) | D02, S01 | done | B.C. | Review/acceptance/integration confirmed 23 October 2026; [PR #13](https://github.com/bc-bah/quezo/pull/13), merge `0cfbff7`, implementation `9ff05f8`; [accepted Grade/state handoff and evidence](../DEVELOPMENT.md#d03-finalization-and-expiration): 611 Python / 246 database-suite / 27 browser cases; migration `0009_finalization`; untimed learner UI while DEC-09 held |
| R01 | 2 | [Policy-filtered result](02-CORE-LIFECYCLE.md#r01-policy-filtered-result) | D03 | active | B.C. | Assigned 21 October; execution directed 23 October after D03 acceptance; merge `0cfbff7`, all ancestors, I02 `553a2c8` and approval `49eb37b` verified. [Review-ready local handoff/evidence](../DEVELOPMENT.md#r01-policy-filtered-result): full common gate passed, 648 Python / 283 database-suite / 30 browser cases; all 27 independent policy combinations and boundary omissions covered. No migration (head `0009_finalization`); uncommitted, acceptance/integration pending; [prompt](PHASE-2-HANDOFFS.md#r01-dispatch-prompt) |
| T01 | 2 | [First lifecycle acceptance](02-CORE-LIFECYCLE.md#t01-first-lifecycle-acceptance) | R01, I02 | active | B.C. | Assigned 21 October 2026; I02 done; execution waits for R01 and transitive lifecycle producers accepted/integrated; [prompt](PHASE-2-HANDOFFS.md#t01-dispatch-prompt); no Phase 3/pilot authorization |
| C03 | 3 | [Complete author workspace](03-COMPLETE-P0.md#c03-complete-author-workspace) | T01 | planned | B.C. | - |
| A01 | 3 | [Account administration](03-COMPLETE-P0.md#a01-account-administration) | T01 | planned | B.C. | - |
| D04 | 3 | [Configurable delivery controls](03-COMPLETE-P0.md#d04-configurable-delivery-controls) | T01 | planned | B.C. | DEC-09 required for timed UX |
| R02 | 3 | [History and author reporting](03-COMPLETE-P0.md#r02-history-and-author-reporting) | T01 | planned | B.C. | - |
| Q01 | 4 | [Integrity and access failure suite](04-READINESS.md#q01-integrity-and-access-failure-suite) | C03, A01, D04, R02 | planned | B.C. | - |
| Q02 | 4 | [Accessibility and workflow acceptance](04-READINESS.md#q02-accessibility-and-workflow-acceptance) | C03, A01, D04, R02 | planned | B.C. | DEC-09 timed-accessibility approval required |
| O01 | 4 | [Deployment observability and recovery](04-READINESS.md#o01-deployment-observability-and-recovery) | C03, A01, D04, R02 | planned | B.C. | DEC-08/DEC-10 operational targets required; synthetic local rehearsal allowed |
| Q03 | 4 | [Load and multi-process evidence](04-READINESS.md#q03-load-and-multi-process-evidence) | O01, Q01 | planned | B.C. | DEC-08 benchmark/gates required |
| G01 | 5 | [Prototype acceptance and pilot decision](04-READINESS.md#g01-prototype-acceptance-and-pilot-decision) | Q01, Q02, O01, Q03 | planned | B.C. | DEC-11 later approvers/release commitments and release evidence required; DEC-10 gates any pilot |

## Review findings and completion exceptions

### EX-I02-01: Native login/logout Origin

**State:** closed, 21 October 2026, as part of B.C.'s I02 acceptance.
**Owner:** B.C. **Original disposition, 20 October 2026:** F03 completion with
the named exception, requiring browser reproduction/fix in I02.

The spec review found `Referrer-Policy: no-referrer` in
`frontend/quezo/next.config.ts:11`, native POST forms in
`frontend/quezo/src/app/auth-form.tsx:9`, and exact-origin rejection in
`frontend/quezo/src/lib/server/session.ts:15-18` in the pre-I02 baseline.
The source review predicted null-Origin native forms missed by manually supplied
HTTP test headers. See the documented
[referrer-policy effect on Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy#effect_on_the_origin_header).
I02 then reproduced the failure in Chromium 156.0.8078.4 without injected Origin
headers and fixed document policy to `strict-origin`, retaining `no-referrer`
on auth routes. Both native forms now succeed; a retained `no-referrer` negative
control and null/missing/foreign-origin tests still reject. See the
[red/green observations](../DEVELOPMENT.md#ex-i02-01-reproduction-and-proposed-resolution)
and [scenario results](../DEVELOPMENT.md#at-01-scenario-results).
The merged browser CI passed. No CSRF, integrity or disclosure exception remains.

**Second-wave review checkpoint:** compared F02 merge `5f31412` with I01 merge
`6ef734f`. Standards: no significant findings. Spec: one high-severity functional
integration finding, EX-I02-01. Both merged PRs' hosted matrices passed; manual
Origin headers in the existing test do not exercise native browser behavior.
That earlier review did not reproduce the failure; I02's subsequent evidence
above resolves it.

**I02 completion review:** compared I01 merge `6ef734f` with I02 merge `553a2c8`.
Standards and specification reviews found no significant issues. Reviewed
evidence includes all 16 real-browser cases, 12 web checks, 264 Python cases and
passing hosted browser/Node 22/24/Python 3.12/3.14 jobs. No new application test
run is claimed by this documentation update. Acceptance is for the working
identity foundation, not assessment workflows, full WCAG, P0 or pilot readiness.

## Update protocol

**Foundation review checkpoint:** compared G00 merge `fd9baaa` with integrated
F02 merge `5f31412`. Standards and specification reviews found no significant
issues. Both PRs' hosted CI passed on Node 22/24 and Python 3.12/3.14; retained
local evidence is linked above. This documentation reconciliation did not rerun
application tests. B.C.'s completion confirmation and merged results establish
package acceptance, not full AT-01/AT-10/AT-15 or prototype readiness.

The coordinator assigns an owner and records `active` before dispatch. B.C. may
preassign a whole wave with named execution gates; such consumers may read/plan
but cannot implement until their required producer rows are `done`, evidence is
recorded, and the exact producer commits are integrated in their checkout.
Approval of the wave removes a repeat assignment decision, not the dependency.
The assignee returns acceptance IDs, evidence, changed contracts and
handoff details; the coordinator moves it to `review`, then `done` after accepted
integration. Link an issue/PR only if one was actually created; local evidence and
commit references are valid while the project remains local.

When a prerequisite changes incompatibly, mark affected consumers blocked and
record the changed contract. After integration, reevaluate readiness from this
table; do not rely on an old agent prompt. If a package is split, update this table,
its phase description and the plan's dependency diagram in one documentation change.
