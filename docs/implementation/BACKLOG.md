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

**Initial state:** only G00 is ready for document review. All engineering packages
are planned; no product implementation or issue/PR creation is implied.
Prerequisites are logical AND. `-` means none; phase order is not an additional
dependency. Decision gates still apply as specified by the package.

| ID | Phase | Package | Prerequisites | Status | Owner | PR/commit and evidence / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| G00 | 0 | [Approve implementation baseline](01-FOUNDATIONS.md#g00-approve-implementation-baseline) | - | ready | - | DEC-01 through DEC-07 pending; reviewers/assignment needed |
| F01 | 1 | [Database and integration-test foundation](01-FOUNDATIONS.md#f01-database-and-integration-test-foundation) | G00 | planned | - | - |
| F02 | 1 | [Contract and error foundation](01-FOUNDATIONS.md#f02-contract-and-error-foundation) | G00 | planned | - | - |
| F03 | 1 | [Web session and navigation foundation](01-FOUNDATIONS.md#f03-web-session-and-navigation-foundation) | F01, F02 | planned | - | - |
| I01 | 1 | [Identity and authorization backend](01-FOUNDATIONS.md#i01-identity-and-authorization-backend) | F01, F02 | planned | - | - |
| I02 | 1 | [Integrated login and access gate](01-FOUNDATIONS.md#i02-integrated-login-and-access-gate) | F03, I01 | planned | - | - |
| C01 | 2 | [Versioned objective questions](02-CORE-LIFECYCLE.md#c01-versioned-objective-questions) | I02 | planned | - | - |
| C02 | 2 | [Immutable quiz publication](02-CORE-LIFECYCLE.md#c02-immutable-quiz-publication) | C01 | planned | - | - |
| D01 | 2 | [Assignment and attempt start](02-CORE-LIFECYCLE.md#d01-assignment-and-attempt-start) | C02 | planned | - | - |
| D02 | 2 | [Durable response save and resume](02-CORE-LIFECYCLE.md#d02-durable-response-save-and-resume) | D01 | planned | - | - |
| S01 | 2 | [Pure objective scoring](02-CORE-LIFECYCLE.md#s01-pure-objective-scoring) | F02 | planned | - | - |
| D03 | 2 | [Finalization and expiration](02-CORE-LIFECYCLE.md#d03-finalization-and-expiration) | D02, S01 | planned | - | - |
| R01 | 2 | [Policy-filtered result](02-CORE-LIFECYCLE.md#r01-policy-filtered-result) | D03 | planned | - | - |
| T01 | 2 | [First lifecycle acceptance](02-CORE-LIFECYCLE.md#t01-first-lifecycle-acceptance) | R01, I02 | planned | - | - |
| C03 | 3 | [Complete author workspace](03-COMPLETE-P0.md#c03-complete-author-workspace) | T01 | planned | - | - |
| A01 | 3 | [Account administration](03-COMPLETE-P0.md#a01-account-administration) | T01 | planned | - | - |
| D04 | 3 | [Configurable delivery controls](03-COMPLETE-P0.md#d04-configurable-delivery-controls) | T01 | planned | - | DEC-09 required for timed UX |
| R02 | 3 | [History and author reporting](03-COMPLETE-P0.md#r02-history-and-author-reporting) | T01 | planned | - | - |
| Q01 | 4 | [Integrity and access failure suite](04-READINESS.md#q01-integrity-and-access-failure-suite) | C03, A01, D04, R02 | planned | - | - |
| Q02 | 4 | [Accessibility and workflow acceptance](04-READINESS.md#q02-accessibility-and-workflow-acceptance) | C03, A01, D04, R02 | planned | - | - |
| O01 | 4 | [Deployment observability and recovery](04-READINESS.md#o01-deployment-observability-and-recovery) | C03, A01, D04, R02 | planned | - | DEC-08/DEC-10 operational targets required; synthetic local rehearsal allowed |
| Q03 | 4 | [Load and multi-process evidence](04-READINESS.md#q03-load-and-multi-process-evidence) | O01, Q01 | planned | - | DEC-08 benchmark/gates required |
| G01 | 5 | [Prototype acceptance and pilot decision](04-READINESS.md#g01-prototype-acceptance-and-pilot-decision) | Q01, Q02, O01, Q03 | planned | - | Named approvers and release evidence required |

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
