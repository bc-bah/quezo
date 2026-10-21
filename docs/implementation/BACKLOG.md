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

**Current state (20 October 2026):** B.C. explicitly dispatched I02 and authorized
reconciliation of these coordination records in the I02 session. F03/I01 are done
and integrated through PR #5 (`b1a2fe0`) and PR #6 (`6ef734f`). B.C. accepts
EX-I02-01 below as a predecessor completion exception, not a starting blocker.
I02 is active under B.C. as owner, integrator and reviewer, with the exclusive
integration shared-file window. No I02 acceptance, successor dispatch or later
release approval is implied.
Prerequisites are logical AND. `-` means none; phase order is not an additional
dependency. Decision gates still apply as specified by the package.

Approval evidence: [G00 approval record](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026).
Prepared assignments: [first-wave prompts](AGENT-HANDOFF.md#4-approved-first-wave-prompts).
Dispatch F01 first, then F02 by default to serialize shared files; this is a
coordination order, not a new F02 prerequisite. B.C. may dispatch them concurrently
only after assigning non-overlapping shared-file write windows. Move each to
`active` when actually dispatched. B.C. records accepted integration evidence.

| ID | Phase | Package | Prerequisites | Status | Owner | PR/commit and evidence / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| G00 | 0 | [Approve implementation baseline](01-FOUNDATIONS.md#g00-approve-implementation-baseline) | - | done | B.C. | [Scoped approval, 20 October 2026](../SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026); DEC-01 through DEC-05 approved; DEC-06/07 holds explicit; F01/F02 assigned |
| F01 | 1 | [Database and integration-test foundation](01-FOUNDATIONS.md#f01-database-and-integration-test-foundation) | G00 | done | B.C. | Accepted/integrated PR #3, merge `8732328`; [local evidence](../DEVELOPMENT.md#f01-local-verification-20-october-2026); reconciliation authorized by B.C. 20 October 2026 |
| F02 | 1 | [Contract and error foundation](01-FOUNDATIONS.md#f02-contract-and-error-foundation) | G00 | done | B.C. | Accepted/integrated PR #4, merge `5f314125e13262139e1d3e28d190881d6fbd5f8b`; [local evidence](../DEVELOPMENT.md#f02-local-verification-20-october-2026); reconciliation authorized by B.C. 20 October 2026 |
| F03 | 1 | [Web session and navigation foundation](01-FOUNDATIONS.md#f03-web-session-and-navigation-foundation) | F01, F02 | done | B.C. | Accepted/integrated PR #5, merge `b1a2fe035d52cdddf4db3a0c832a690773fe5688`; completion confirmed by B.C. 20 October 2026 with EX-I02-01; hosted CI is not browser evidence |
| I01 | 1 | [Identity and authorization backend](01-FOUNDATIONS.md#i01-identity-and-authorization-backend) | F01, F02 | done | B.C. | Accepted/integrated PR #6, merge `6ef734faefbb52c76b78abb7d676ec9305f0c557`; completion confirmed by B.C. 20 October 2026; hosted CI is not browser evidence |
| I02 | 1 | [Integrated login and access gate](01-FOUNDATIONS.md#i02-integrated-login-and-access-gate) | F03, I01 | active | B.C. | Explicit dispatch 20 October 2026; exclusive integration write window; real browser AT-01 and EX-I02-01 resolution required; B.C. owns acceptance/exception closure |
| C01 | 2 | [Versioned objective questions](02-CORE-LIFECYCLE.md#c01-versioned-objective-questions) | I02 | planned | B.C. | - |
| C02 | 2 | [Immutable quiz publication](02-CORE-LIFECYCLE.md#c02-immutable-quiz-publication) | C01 | planned | B.C. | - |
| D01 | 2 | [Assignment and attempt start](02-CORE-LIFECYCLE.md#d01-assignment-and-attempt-start) | C02 | planned | B.C. | - |
| D02 | 2 | [Durable response save and resume](02-CORE-LIFECYCLE.md#d02-durable-response-save-and-resume) | D01 | planned | B.C. | - |
| S01 | 2 | [Pure objective scoring](02-CORE-LIFECYCLE.md#s01-pure-objective-scoring) | F02 | planned | B.C. | - |
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

## EX-I02-01: Native form origin evidence

B.C. accepts this predecessor completion exception on 20 October 2026.
At dispatch, source/protocol review predicted that F03's `Referrer-Policy: no-referrer`
could cause native login/logout POSTs to send `Origin: null` and receive 403.
It was not yet a confirmed browser failure. I02 must reproduce and fix it,
or resolve it with exact browser/version/request-header evidence before
I02/AT-01 acceptance. Never allow null/missing/foreign origins, remove CSRF,
or substitute manually supplied Origin headers for native browser actions.
B.C. owns review and exception closure; F03/I01 completion permits I02 to start.

## Update protocol

The coordinator assigns an owner and moves an eligible item to `active` before
dispatch. The assignee returns acceptance IDs, evidence, changed contracts and
handoff details; the coordinator moves it to `review`, then `done` after accepted
integration. Link an issue/PR only if one was actually created; local evidence and
commit references are valid while the project remains local.

When a prerequisite changes incompatibly, mark affected consumers blocked and
record the changed contract. After integration, reevaluate readiness from this
table; do not rely on an old agent prompt. If a package is split, update this table,
its phase description and the plan's dependency diagram in one documentation change.
