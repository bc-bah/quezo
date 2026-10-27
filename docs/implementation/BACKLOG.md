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

**Current state (27 October 2026):** I02 is `done`; EX-I02-01 is closed after
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
and R01's execution gate is satisfied. B.C. directed R01 acceptance/tracking
to `done` and T01 execution on 23 October 2026. Live GitHub main and this checkout
contain R01 [PR #14](https://github.com/bc-bah/quezo/pull/14), merge
`8976371bdf00bb337a0db0df1818cf739df7b546`, implementation
`bb194681762e5e5e3563645f67303f9ca51f38cd`. All producer merges and implementation
commits above, I02 and approval `49eb37b` were verified as ancestors.
I02 was already `done`; its accepted record and closed exception are preserved.
T01 is `done`: B.C. requested milestone acceptance/tracking reconciliation on
23 October 2026. [PR #15](https://github.com/bc-bah/quezo/pull/15) is merged at
`df06ccc19af947cda05757c79938394763d6edb6`, including implementation `300bbc4`.
The recorded lifecycle evidence and passing hosted browser/matrix checks support
acceptance of the Phase 2 exit gate. All eight Phase 2 packages are now `done`.
C03 is now `done`: B.C. reviewed the updated local Docker app, requested commit
and merge to local `dev`, and directed acceptance reconciliation on 27 October.
Implementation/integration commit is `2eba9eb`; head is `0010_author_workspace`.
A01/D04/R02 are `ready` after B.C.'s explicit
[scoped approvals](../SOFTWARE-SPECIFICATION.md#c03-acceptance-and-phase-3-approvals-27-october-2026).
Prepare separate dispatches in order **A01, then D04, then R02**, under B.C.'s
integration/review ownership, with one shared-file/contract/migration writer at
a time. No remaining package is active or assigned an implementation owner by
this record. A01 verifies exact least-privilege permissions before privileged
implementation; D04 implements the approved timing adjustment/off interaction,
not the old hard-cap rule for opted-in adjusted attempts. Later release holds remain.
Prerequisites are logical AND. `-` means none; phase order is not an additional
dependency. Decision gates still apply as specified by the package.

Approval evidence: [G00](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026),
[second wave](../SOFTWARE-SPECIFICATION.md#second-wave-approval-f03-and-i01) and
[I02 assignment/exception](../SOFTWARE-SPECIFICATION.md#i02-assignment-and-completion-exception).
Current approval: [C03 acceptance and Phase 3 approvals](../SOFTWARE-SPECIFICATION.md#c03-acceptance-and-phase-3-approvals-27-october-2026);
the [Phase 2 assignment/defaults](../SOFTWARE-SPECIFICATION.md#phase-2-assignment-and-demo-defaults)
remain historical, except for the explicitly amended D04 timing boundary.
Completed assignments: [historical Phase 2 prompts](PHASE-2-HANDOFFS.md).
Prepared next-wave prompts: [Phase 3 handoffs](PHASE-3-HANDOFFS.md); no package
is assigned by that document.
Integrated foundation baseline: `553a2c8b77a770667f4cef6825f57c3b55f477ed`;
migration head `0004_identity`. Consumers must also include their later producer
commits, recorded on acceptance. Accepted C01 merge
`e66f459c5a6b225bd3d1b4bbce6b5b87de67974c` advances the migration head to
`0005_questions` and completes C01's initial shared-file window. Subsequent
accepted producers advance the current head to `0009_finalization`; R01/T01 add
no migration. C03 is integrated locally at `2eba9eb` (containing `354da49` and
T01 merge `df06ccc`), advancing head to `0010_author_workspace`. This is the
next-package baseline plus the current approval/tracking update; use a newer
B.C.-recorded integrated baseline after each sequential package merge.
Shared writes and migration ordering remain serialized by B.C.

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
| R01 | 2 | [Policy-filtered result](02-CORE-LIFECYCLE.md#r01-policy-filtered-result) | D03 | done | B.C. | Acceptance/tracking directed 23 October 2026; [PR #14](https://github.com/bc-bah/quezo/pull/14), merge `8976371`, implementation `bb19468`, verified on live main and in T01 ancestry. [Accepted handoff/evidence](../DEVELOPMENT.md#r01-policy-filtered-result): 648 Python / 283 database-suite / 30 browser cases; 27 independent policy combinations/boundaries. No migration; head `0009_finalization`. |
| T01 | 2 | [First lifecycle acceptance](02-CORE-LIFECYCLE.md#t01-first-lifecycle-acceptance) | R01, I02 | done | B.C. | Accepted 23 October 2026 following B.C.'s tracking direction; [PR #15](https://github.com/bc-bah/quezo/pull/15), merge `df06ccc`, implementation `300bbc4`; [accepted handoff](../DEVELOPMENT.md#t01-first-lifecycle-acceptance), [AT matrix/demo](../../tests/e2e/README.md#lifecycle-acceptance-matrix), [hosted browser/matrix CI](https://github.com/bc-bah/quezo/actions/runs/39949405839). Recorded unfiltered gate: 648 Python / 283 database-suite / 33 browser cases, zero skipped; reproducible six-case demo passed. No runtime contract/migration changes; head `0009_finalization`. Phase 2 milestone only, not full P0/pilot acceptance. |
| C03 | 3 | [Complete author workspace](03-COMPLETE-P0.md#c03-complete-author-workspace) | T01 | done | B.C. | Accepted/integrated 27 October 2026 after local app review; local dev fast-forward `2eba9eb`; head `0010_author_workspace`; [case-level evidence and check limitations](../DEVELOPMENT.md#c03-complete-author-workspace), [acceptance record below](#c03-acceptance-and-next-package-readiness-27-october-2026). No remote PR/push or hosted CI claimed. |
| A01 | 3 | [Account administration](03-COMPLETE-P0.md#a01-account-administration) | T01 | ready | Unassigned; B.C. integration/review | First separate dispatch. Scoped DEC-06 amendment approved 27 October; verify/record exact local-realm least privileges before privileged implementation. Baseline `2eba9eb`, head `0010_author_workspace`, plus this tracking update. |
| D04 | 3 | [Configurable delivery controls](03-COMPLETE-P0.md#d04-configurable-delivery-controls) | T01 | ready | Unassigned; B.C. integration/review | Second separate dispatch, after A01's serialized write window. DEC-09 and scoped DEC-02/05 timing amendments approved 27 October; implement pre-start adjust/off, immutable choice and start-cutoff/deadline distinction. Reverify integrated baseline/head after A01. |
| R02 | 3 | [History and author reporting](03-COMPLETE-P0.md#r02-history-and-author-reporting) | T01 | ready | Unassigned; B.C. integration/review | Third separate dispatch after D04's serialized write window; reverify actual head/contracts. Latest-completed-attempt link remains partial AT-13 only; full history/reporting not implemented or accepted. |
| Q01 | 4 | [Integrity and access failure suite](04-READINESS.md#q01-integrity-and-access-failure-suite) | C03, A01, D04, R02 | planned | B.C. | - |
| Q02 | 4 | [Accessibility and workflow acceptance](04-READINESS.md#q02-accessibility-and-workflow-acceptance) | C03, A01, D04, R02 | planned | B.C. | DEC-09 approved 27 October; D04 implementation and actual accessibility/workflow evidence still required |
| O01 | 4 | [Deployment observability and recovery](04-READINESS.md#o01-deployment-observability-and-recovery) | C03, A01, D04, R02 | planned | B.C. | DEC-08/DEC-10 operational targets required; synthetic local rehearsal allowed |
| Q03 | 4 | [Load and multi-process evidence](04-READINESS.md#q03-load-and-multi-process-evidence) | O01, Q01 | planned | B.C. | DEC-08 benchmark/gates required |
| G01 | 5 | [Prototype acceptance and pilot decision](04-READINESS.md#g01-prototype-acceptance-and-pilot-decision) | Q01, Q02, O01, Q03 | planned | B.C. | DEC-11 later approvers/release commitments and release evidence required; DEC-10 gates any pilot |

## Review findings and completion exceptions

### C03 acceptance and next-package readiness: 27 October 2026

**Accepted by B.C.** after reviewing the rebuilt local Docker app and requesting
commit/merge to `dev`, followed by explicit tracking reconciliation. C03 commit
`2eba9eb8f2986664687059f974ad4282b0b1dd49` is locally fast-forward integrated;
no remote merge/PR is invented. Head `0010_author_workspace` follows
`0009_finalization`; the local stack was rebuilt, migration applied and app
health/new routes verified without replacing existing database/Keycloak volumes.

Evidence: [C03 scenario map and outcomes](../DEVELOPMENT.md#c03-complete-author-workspace),
[19 focused persistence tests](../../postgres/tests/test_author_workspace.py),
[3 new real-provider browser journeys](../../tests/e2e/author-workspace.spec.ts).
All 36 browser cases passed, including inherited C01/C02/T01; type checks,
88 Python + 2 Node contract checks, production build/HTTP, generated-contract
checks and whitespace checks passed. The umbrella `--checks` invocation stopped
with 665 passes/two stale route-inventory failures; corrected inventories passed
the subsequent focused contract suite. No green umbrella rerun or hosted CI
result is claimed.

| Acceptance | Accepted package evidence | Still partial / outside this package |
| --- | --- | --- |
| AT-03 | Inherited C01/T01 both-type/content-bound/ownership evidence; C03 metadata bounds, combined text/category/tag search, pagination, owned moves/archives, direct/nested-ID and real foreign-author checks | Browser bounds are representative; exhaustive new bounds are HTTP/database evidence; no blanket catalogue/WCAG claim |
| AT-04 | Reuse in two quizzes, explicit revision update, immutable old publications, private attempt snapshots and finalized results/grade retention across edit/archive | No duplicate command, regrade or reset |
| AT-05 | Inherited stale-tab/CAS, replay, preview/no-side-effects tests; new history, close/archive, pending-draft freeze, stale/invalid transitions, active-attempt rejection and resume/finalize after close | Advanced delivery/timed preview/accessibility remains D04/Q02; not accepted as full advanced-policy coverage |
| AT-01/02 | Existing identity evidence retained | A01 administration not implemented/accepted |
| AT-06/09/12/13/14 | Existing T01/R01 evidence retained; latest-completed-attempt link is partial history | D04 settings/accessibility and R02 full history/reporting need new evidence; no new completion claims |

B.C.'s explicit DEC-06/09/02/05 approvals and serialized dispatch order are in the
[specification approval record](../SOFTWARE-SPECIFICATION.md#c03-acceptance-and-phase-3-approvals-27-october-2026).
A01/D04/R02 are ready for separate assignment, not active. The order is a
shared-write/integration schedule, not new domain prerequisite edges.
Exact Keycloak permissions must be verified before privileged A01 implementation.
No credentials, successor code, deployment, release or pilot is authorized by
this documentation task. DEC-08/10 and release/date/budget holds remain.

### Phase 3 checkout baseline and partial AT-13 evidence: 27 October 2026

The pre-C03 integrated checkout included `354da49`, which adds learner-workspace
links to view the most recent finalized attempt and its policy-filtered result.
The behavior and its browser scenario are documented in
[DEVELOPMENT.md](../DEVELOPMENT.md#host-run-application-processes) and
[lifecycle.spec.ts](../../tests/e2e/lifecycle.spec.ts); a result remains governed
by R01 release policy.
This is a useful return path, not paginated learner history, author reporting,
or full AT-13 acceptance. It does not change T01's accepted scope or complete
R02. That starting baseline/head `0009_finalization` is superseded by the C03
acceptance record above: next dispatch uses `2eba9eb` and `0010_author_workspace`
plus this tracking update, or a newer B.C.-recorded integrated baseline.
See the [prepared Phase 3 handoffs](PHASE-3-HANDOFFS.md); no package is assigned
by this record.

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

### T01 milestone acceptance: 23 October 2026

B.C.'s request to reconcile acceptance before Phase 3 is recorded against merged
PR #15 and its actual handoff, not an uncommitted implementation. The reviewed
records cover AT-01 and initial AT-03 through AT-12, both release presets,
controlled backend expiry, interrupted save/submit recovery, immutable snapshots,
one Grade and policy-filtered results. The retained local unfiltered gate reports
33 browser cases with no failures/skips and all producer checks passing; the
independent six-case demo also passed. Hosted browser, Node 22/24 and Python
3.12/3.14 jobs succeeded in the linked run.

This is acceptance/evidence reconciliation, not a new code review or application
test run. The [coverage matrix](../../tests/e2e/README.md#lifecycle-acceptance-matrix)
retains explicit C03/A01/D04/R02 and readiness gaps. No known assigned T01
criterion remains outstanding in the delivery record. T01 acceptance does not
approve runtime administration credentials, timed accessibility, Phase 3 dispatch,
full P0, deployment or pilot readiness. At that checkpoint DEC-08/09/10 and later
DEC-11 commitments remained held; the 27 October record above supersedes the
DEC-09/ownership holds, not release/pilot gates. EX-I02-01 remains closed.

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
