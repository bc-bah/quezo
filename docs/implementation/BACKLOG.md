# Implementation backlog

**Source of truth:** package status, prerequisites, assignment and completion
evidence live here. Behavior lives in the [software specification](../SOFTWARE-SPECIFICATION.md);
package descriptions live in the linked phase files.

Status values: `planned`, `ready`, `active`, `review`, `blocked`, `done`.
`ready` means prerequisites and decision gates are satisfied, not that an agent
has permission to start. `review` means work is available but not yet accepted.
`done` requires the plan's integration/evidence definition. Replace `-` with actual
owner, PR/commit and evidence links as work progresses. A blocked item records the
specific decision or predecessor, not a generic "waiting."

**Current state (20 October 2026):** F01/F02/F03/I01 are `done` following B.C.'s
completion confirmation and merged evidence review. F03 carries B.C.'s explicit
EX-I02-01 completion exception below; combined browser acceptance is not claimed.
I02 is `active` by B.C.'s explicit assignment, with B.C. as owner, integrator
and reviewer/merge approver. This records assignment, not an agent launch or
completion. Later release commitments remain held under DEC-11.
Prerequisites are logical AND. `-` means none; phase order is not an additional
dependency. Decision gates still apply as specified by the package.

Approval evidence: [G00](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026),
[second wave](../SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01) and
[I02 assignment/exception](../SOFTWARE-SPECIFICATION.md#i02-assignment-and-completion-exception).
Current assignment: [I02 copy-ready prompt](AGENT-HANDOFF.md#i02-dispatch-prompt).
Integrated producer baseline: `6ef734faefbb52c76b78abb7d676ec9305f0c557`;
migration head `0004_identity`. I02 has the exclusive shared-file window for its
focused integration changes. S01 is ready but not dispatched; C01 still awaits
I02 acceptance. No successor becomes active automatically.

| ID | Phase | Package | Prerequisites | Status | Owner | PR/commit and evidence / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| G00 | 0 | [Approve implementation baseline](01-FOUNDATIONS.md#g00-approve-implementation-baseline) | - | done | B.C. | [Original scoped approval](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026); DEC-06/07 holds superseded by [second-wave approval](../SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01) |
| F01 | 1 | [Database and integration-test foundation](01-FOUNDATIONS.md#f01-database-and-integration-test-foundation) | G00 | done | B.C. | Accepted 20 October 2026; [PR #3](https://github.com/bc-bah/quezo/pull/3), merge `8732328`; [local evidence](../DEVELOPMENT.md#f01-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39505683430); 51 tests at F01, original 41 database cases retained in F02 |
| F02 | 1 | [Contract and error foundation](01-FOUNDATIONS.md#f02-contract-and-error-foundation) | G00 | done | B.C. | Accepted 20 October 2026; [PR #4](https://github.com/bc-bah/quezo/pull/4), merge `5f31412`; [local evidence](../DEVELOPMENT.md#f02-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39509963069); 138 Python tests and 2 tooling/client tests; approved actor contract |
| F03 | 1 | [Web session and navigation foundation](01-FOUNDATIONS.md#f03-web-session-and-navigation-foundation) | F01, F02 | done | B.C. | Accepted 20 October 2026 with explicit [EX-I02-01](#ex-i02-01-native-loginlogout-origin); [PR #5](https://github.com/bc-bah/quezo/pull/5), merge `b1a2fe0`; [local evidence](../DEVELOPMENT.md#f03-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39519807448); 10 web tests, 154 Python cases; real-browser gate remains I02 |
| I01 | 1 | [Identity and authorization backend](01-FOUNDATIONS.md#i01-identity-and-authorization-backend) | F01, F02 | done | B.C. | Accepted 20 October 2026; [PR #6](https://github.com/bc-bah/quezo/pull/6), merge `6ef734f`; [local evidence](../DEVELOPMENT.md#i01-local-verification-20-october-2026), [hosted CI](https://github.com/bc-bah/quezo/actions/runs/39530379835); 262 Python cases, 10 web tests and actual-Keycloak HTTP integration; combined browser proof remains I02 |
| I02 | 1 | [Integrated login and access gate](01-FOUNDATIONS.md#i02-integrated-login-and-access-gate) | F03, I01 | active | B.C. | Explicit assignment 20 October 2026; integrated baseline `6ef734f`; exclusive integration window; [copy-ready prompt](AGENT-HANDOFF.md#i02-dispatch-prompt); first resolve EX-I02-01, then complete real-browser AT-01 evidence |
| C01 | 2 | [Versioned objective questions](02-CORE-LIFECYCLE.md#c01-versioned-objective-questions) | I02 | planned | B.C. | - |
| C02 | 2 | [Immutable quiz publication](02-CORE-LIFECYCLE.md#c02-immutable-quiz-publication) | C01 | planned | B.C. | - |
| D01 | 2 | [Assignment and attempt start](02-CORE-LIFECYCLE.md#d01-assignment-and-attempt-start) | C02 | planned | B.C. | - |
| D02 | 2 | [Durable response save and resume](02-CORE-LIFECYCLE.md#d02-durable-response-save-and-resume) | D01 | planned | B.C. | - |
| S01 | 2 | [Pure objective scoring](02-CORE-LIFECYCLE.md#s01-pure-objective-scoring) | F02 | ready | B.C. | F02 integrated and DEC-03 approved; not dispatched or authorized by the I02 assignment |
| D03 | 2 | [Finalization and expiration](02-CORE-LIFECYCLE.md#d03-finalization-and-expiration) | D02, S01 | planned | B.C. | - |
| R01 | 2 | [Policy-filtered result](02-CORE-LIFECYCLE.md#r01-policy-filtered-result) | D03 | planned | B.C. | - |
| T01 | 2 | [First lifecycle acceptance](02-CORE-LIFECYCLE.md#t01-first-lifecycle-acceptance) | R01, I02 | planned | B.C. | - |
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

**State:** open; I02 acceptance blocker, not a start/approval blocker.
**Owner:** B.C. **Authorized disposition, 20 October 2026:** B.C. explicitly
approved F03 completion with this exception and required I02 to reproduce/fix it.

The spec review found `Referrer-Policy: no-referrer` in
`frontend/quezo/next.config.ts:11`, native POST forms in
`frontend/quezo/src/app/auth-form.tsx:9`, and exact-origin rejection in
`frontend/quezo/src/lib/server/session.ts:15-18`. Browser policy can produce
`Origin: null` and a 403 for ordinary login/logout; the HTTP production test
supplies Origin manually. See the documented
[referrer-policy effect on Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy#effect_on_the_origin_header).
This is a source/protocol finding, **not a browser
reproduction**. It affects the F03 login/logout criterion and I02's AT-01 proof.

I02 must first exercise native forms in an actual browser without injected
Origin headers. If confirmed, apply a narrowly scoped compatible referrer policy
and regression test; never allow null/foreign origins or bypass CSRF checks.
If not reproduced, retain exact browser/version/header evidence resolving the
finding. Close EX-I02-01 only with accepted evidence; no AT-01 or I02 completion
while unresolved. No integrity or disclosure exception is authorized.

**Second-wave review checkpoint:** compared F02 merge `5f31412` with I01 merge
`6ef734f`. Standards: no significant findings. Spec: one high-severity functional
integration finding, EX-I02-01. Both merged PRs' hosted matrices passed; manual
Origin headers in the existing test do not exercise native browser behavior.
This documentation review did not rerun application tests or claim browser proof.

## Update protocol

**Foundation review checkpoint:** compared G00 merge `fd9baaa` with integrated
F02 merge `5f31412`. Standards and specification reviews found no significant
issues. Both PRs' hosted CI passed on Node 22/24 and Python 3.12/3.14; retained
local evidence is linked above. This documentation reconciliation did not rerun
application tests. B.C.'s completion confirmation and merged results establish
package acceptance, not full AT-01/AT-10/AT-15 or prototype readiness.

The coordinator assigns an owner and moves an eligible item to `active` before
dispatch. The assignee returns acceptance IDs, evidence, changed contracts and
handoff details; the coordinator moves it to `review`, then `done` after accepted
integration. Link an issue/PR only if one was actually created; local evidence and
commit references are valid while the project remains local.

When a prerequisite changes incompatibly, mark affected consumers blocked and
record the changed contract. After integration, reevaluate readiness from this
table; do not rely on an old agent prompt. If a package is split, update this table,
its phase description and the plan's dependency diagram in one documentation change.
