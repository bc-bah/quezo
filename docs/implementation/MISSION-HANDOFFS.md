# Mission and readiness agent handoffs

**Updated:** 9 November 2026

Copy one prompt below into a separate session whose checkout contains this
packet. Each prompt points back to the shared execution contract, so it can be
copied alone. Creating this packet launches no agents and changes no assignment,
approval or acceptance status.

## 1. Choose a stream

The [backlog](BACKLOG.md) is authoritative for prerequisites/status; the
[specification decision register](../SOFTWARE-SPECIFICATION.md#2-decision-register)
owns approvals. Recheck both at dispatch. At this checkpoint A01/D04/R02 are
under review, mission packages are planned, and DEC-12 through DEC-18 are open.
Start with gate preparation, not ungated implementation.

| Stream | Copy-ready prompt | When it can execute |
| --- | --- | --- |
| Gate preparation | [Read-only gate review](#gate-review) | Can be assigned now to identify acceptance/decision blockers; it grants no implementation permission |
| A: Class administration | [M01](#m01) | Accepted A01/D01, approved DEC-12 and explicit assignment |
| B: Assessment outcomes | [M02](#m02) | Accepted C02/S01/D03/R01, approved DEC-13 and explicit assignment; independent of M01 |
| C: Readiness | [Q01](#q01), [Q02](#q02), [O01](#o01) | Accepted C03/A01/D04/R02 and each package's applicable decisions; separate assignments can proceed concurrently |
| Reporting integration | [M03](#m03) | Accepted M01/M02/R02 and approved DEC-14 |
| Downstream mission work | [M04](#m04), [M05](#m05), [M07](#m07) | Accepted M03 plus each package's decisions; M05 also requires accepted D04 |
| Optional content onboarding | [M06](#m06) | Accepted C03 and validated need/approved DEC-17; independent of M01/M02 |
| Capacity evidence | [Q03](#q03) | Accepted O01/Q01, approved DEC-08 and the integrated workflows named in its workload |

These are logical parallel streams, not unrestricted simultaneous writes.
M01/M02 converge at M03. M04/M05/M07 can separate after that convergence, but
their report changes still need coordinated ownership. G01 remains a human
acceptance/pilot decision supported by evidence, not an agent self-approval task.

## 2. Shared execution contract

### Coordinator preparation

Before implementation dispatch, record the assignee, exact integrated baseline,
approved decisions, accepted prerequisites, permitted paths and shared-write
owner/window in the assignment or linked tracker entry. B.C. retains integration
and acceptance ownership. Use current integrated code, not an October handoff's
hard-coded commit or migration head.

Use the ownership boundaries below to allocate paths after inspecting the
current tree. New modules/routes require agreement on their location; these
boundaries do not preselect a new architecture.

| Package | Feature-local ownership candidate | Coordinate before writing |
| --- | --- | --- |
| M01 | Iteration/roster/batch-assignment slice; existing distribution module and assignment UI; focused tests | Identity/profile exposure, new schema/migrations and assignment uniqueness changes |
| M02 | Passing-policy/publication/scoring/finalization/result slice and focused tests | Quiz editor/policy, grade contracts and result projections shared with M01/M03 |
| M03 | Scoped reporting queries, report/handoff UI and export tests | M01 context, M02 outcome contracts, access policy and shared result renderer |
| M04/M05/M07 | Assigned comparison, diagnostic or follow-up slice and tests | Shared report routes, queries and version/membership mappings; one writer per overlapping surface |
| M06 | Structured import validation, preview/review and authoring tests | Question editor, publication behavior and agreed input format |
| Q01 | Failure/concurrency/access evidence and bounded integrity fixes | Feature-owned runtime fixes, shared fixtures and error contracts |
| Q02 | Accessibility/workflow evidence and bounded UI corrections | Feature-owned components and shared navigation/styles |
| O01 | Readiness, observability, deployment/recovery configuration and evidence | App lifespan/wiring, CI, Compose, images and operational settings |
| Q03 | Approved workload driver, measurement/correctness evidence and scoped tuning | Fixture generators, O01 environment, pool settings and feature-owned fixes |

Serialize migrations, generated OpenAPI/client updates, shared schemas, root
wiring, manifests/locks and shared documentation under a named writer. An
isolated worktree prevents working-copy collisions, not incompatible contracts.
Agree producer interfaces before parallel consumer development; integrate actual
producer code before claiming end-to-end acceptance.

### Assignee steps

1. Read the selected backlog row and prerequisites, its package definition,
   applicable specification decisions/rules, and this section. Inspect live
   workspace state, migration head and producer contracts. Completion: report
   the exact baseline, approvals, prerequisite evidence and write allocation.
   If any is missing, return `blocked` before runtime edits; identify the precise
   missing decision/evidence rather than choosing a policy yourself.
2. Deliver only the assigned slice or readiness package. Use the existing
   architecture and current development scripts. Update affected behavioral/
   contract documentation to reflect approved decisions. Completion: all
   assigned surfaces are integrated, including authorization, persistence, API,
   UI and migrations where the package requires them.
3. Execute package-specific acceptance and relevant regressions against isolated
   synthetic dependencies. Map every criterion to an observed result or explicit
   gap. Completion: record exact commands/environment/results; identify manual
   observations separately. A fixture-only consumer is not integrated delivery.
4. Return [the standard handoff](AGENT-HANDOFF.md#3-handoff-format), naming each
   M-package acceptance criterion from the roadmap or each readiness AT criterion.
   Use `ready for review` or `blocked`; include producer contracts successors can
   rely on, migration ordering and unverified criteria. Stop at this package.

If decisions or prerequisites remain unresolved, only separately assigned
read-only preparation is allowed. O01's explicitly assigned synthetic rehearsal
exception is described in its prompt; operational acceptance still requires its
approved targets. Any need to expand scope or write outside allocated paths
returns to the coordinator.

Retain synthetic-data, disclosure and immutable-history boundaries. No package
prompt authorizes deployment, real data, external provisioning, automatic
successor execution, commit/push or PR creation. Those require separate explicit
instructions. The coordinator, not the assignee, accepts delivery and updates
package status.

## 3. Gate preparation

### Gate review

```text
Prepare Quezo's next mission/readiness dispatch wave. This is read-only
preparation, not implementation or acceptance authority.

Read docs\implementation\MISSION-HANDOFFS.md sections 1-2, BACKLOG.md,
MISSION-ALIGNMENT.md, 03-COMPLETE-P0.md and 04-READINESS.md in that directory,
plus docs\SOFTWARE-SPECIFICATION.md's decision register. Inspect current
A01/D04/R02 implementation and the linked docs\DEVELOPMENT.md evidence.

Return a criterion-by-criterion A01/D04/R02 evidence/gap matrix for B.C.'s
acceptance review. Separate code presence, recorded execution and unverified
criteria; do not infer acceptance or rerun infrastructure without assignment.
For DEC-12/13/14, identify the concrete choices blocking the first mission wave,
alternatives and a recommendation, clearly labelled as a proposal. Identify
applicable DEC-08/10 blockers for readiness without inventing target values.

Propose exact non-overlapping file allocations and shared-write windows for
M01/M02 and Q01/Q02/O01, using the current tree. State which streams can be
assigned, which are blocked and why. Include the inspected commit/migration
head. Return the report in the conversation; do not change tracker statuses,
approve decisions, launch agents, edit runtime code or redispatch old packages.
Stop after the gate report.
```

## 4. Mission implementation prompts

Each prompt consumes only its package definition in
[MISSION-ALIGNMENT.md](MISSION-ALIGNMENT.md#3-prioritized-implementation-packages);
that document owns scope and acceptance targets. Prompts highlight important
integration hazards without replacing those criteria.

### M01

```text
Work only on Quezo M01: Training iterations, rosters and bulk assignment.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read M01 in docs\implementation\MISSION-ALIGNMENT.md and BACKLOG.md, and
DEC-12 plus DEC-01 in docs\SOFTWARE-SPECIFICATION.md.

Require accepted A01/D01, approved DEC-12 and the recorded assignment/write
allocation. Implement the full M01 vertical slice using existing distribution
and identity boundaries. Resolve the approved recurring learner/version identity
contract before changing assignment uniqueness; preserve historical membership
and existing allowances. Roster inclusion is not implicit application access.

Demonstrate the roadmap's 100-person synthetic batch, explicit recipient
failures, retry safety and historical flight attribution. Cover concurrent/
replayed batch requests, disabled recipients and a learner returning for a new
iteration. Report the context/membership/assignment contracts M03 can consume.
Return the standard handoff and stop; batch success is not a load benchmark.
```

### M02

```text
Work only on Quezo M02: Explicit pass/fail outcomes.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read M02 in docs\implementation\MISSION-ALIGNMENT.md and BACKLOG.md, and
DEC-13 plus existing scoring, finalization and result rules in
docs\SOFTWARE-SPECIFICATION.md.

Require accepted C02/S01/D03/R01, approved DEC-13 and the recorded assignment/
write allocation. Implement versioned passing rules and outcome presentation
without changing immutable historical grades or bypassing release policy.
Apply only approved threshold, rounding, retake and expired/unfinished rules.

Cover below/at/above-threshold boundaries, policy changes after publication,
historical grades without a passing rule and the approved retake cases.
Preserve exactly-once finalization and withheld-result behavior. Return the
outcome/policy contracts M03 can consume, full acceptance mapping and the
standard handoff. Stop after M02; roster work is a separate stream.
```

### M03

```text
Work only on Quezo M03: Instructor/leadership reporting and result handoff.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read M03 in docs\implementation\MISSION-ALIGNMENT.md and BACKLOG.md,
DEC-14 and RESULT-01/02 in docs\SOFTWARE-SPECIFICATION.md, and the R02
reporting implementation/evidence in docs\DEVELOPMENT.md.

Require accepted M01/M02/R02, approved DEC-14 and the recorded assignment/
write allocation. Use integrated membership/assignment/outcome contracts.
Deliver the approved class/flight/iteration reporting, staff access and tracker
handoff. Preserve existing disclosure rules unless DEC-14 explicitly amends them.
Implement CSV only if the approved handoff requires it; do not invent a tracker API.

Reconcile known synthetic grades to report counts, denominators, selected
attempts and any export. Cover unauthorized scopes, withheld/unfinished states,
repeat attempts and historical membership. Verify export validation and safe
spreadsheet handling when export is included. Report the M01-M03 demonstration
and standard handoff; stop before comparison or diagnostic analytics.
```

### M04

```text
Work only on Quezo M04: Repeatability and cross-iteration comparison.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read M04 in docs\implementation\MISSION-ALIGNMENT.md and BACKLOG.md,
DEC-15 in docs\SOFTWARE-SPECIFICATION.md and integrated M01-M03 contracts.

Require accepted M03, approved DEC-15 and the recorded assignment/write
allocation. Reuse existing publication/assignment mechanisms according to the
approved repeat-iteration rules; add duplication only if the agreed design needs it.
Keep assessment version, passing policy and retake differences visible.

Demonstrate two iterations with both unchanged and changed assessment versions.
Prove rosters/allowances remain separate and comparisons expose approved
limitations rather than implying equivalence. Return the standard handoff and
stop; diagnostics and follow-up are independent downstream packages.
```

### M05

```text
Work only on Quezo M05: Diagnostic metrics.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read M05 in docs\implementation\MISSION-ALIGNMENT.md and BACKLOG.md, and
DEC-16 in docs\SOFTWARE-SPECIFICATION.md.

Require accepted M03/D04, approved customer demand/formulas under DEC-16 and
the recorded assignment/write allocation. Deliver only the approved duration,
section/objective and question metrics. Preserve publication-time mappings;
current mutable tags are not historical section definitions.

Use known-data fixtures to verify populations, sample sizes, zero denominators,
version differences, unanswered items and approved retake selection. Exercise
resumes, standard/adjusted/off timing and delayed expiration processing.
Label elapsed time and percent-correct metrics accurately, preserve reporting
access/disclosure rules, return the standard handoff and stop.
```

### M06

```text
Work only on Quezo M06: Structured content onboarding.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read M06 in docs\implementation\MISSION-ALIGNMENT.md and BACKLOG.md, and
DEC-17 in docs\SOFTWARE-SPECIFICATION.md.

Require accepted C03, validated migration need/approved DEC-17 and the recorded
assignment/write allocation. Deliver the selected structured format, validation,
preview and review workflow using existing author-owned question/version rules.
Preserve supported question types and explicit publication review.

Cover a representative synthetic import, invalid rows, duplicates, replay/retry,
ownership and publication-review boundaries. Make failures visible and preserve
existing content/history. Arbitrary document extraction and AI authoring remain
outside this package. Return the standard handoff and stop.
```

### M07

```text
Work only on Quezo M07: Review and follow-up.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read M07 in docs\implementation\MISSION-ALIGNMENT.md and BACKLOG.md, and
DEC-18 in docs\SOFTWARE-SPECIFICATION.md.

Require accepted M03, approved DEC-18 and the recorded assignment/write
allocation. Deliver the agreed action/owner/status/closure workflow linked to
outcomes with scoped reviewer access. Keep the original grade immutable.

Demonstrate action creation, ownership, authorized closure and denial outside
the approved scope. Cover invalid transitions and historical traceability.
Manual grading/regrading, LMS expansion and automated personnel/readiness
decisions remain outside this package. Return the standard handoff and stop.
```

## 5. Readiness prompts

Use the corresponding definition in
[04-READINESS.md](04-READINESS.md) for all rules, AT criteria and exclusions.
Name the exact integrated feature set in the assignment; later mission merges
require updated evidence rather than inheriting an earlier readiness claim.

### Q01

```text
Work only on Quezo Q01: Integrity and access failure suite.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read Q01 in docs\implementation\04-READINESS.md, its BACKLOG.md prerequisites
and the referenced specification rules/AT criteria.

Require accepted C03/A01/D04/R02, applicable approved decisions and the recorded
assignment/write allocation. Exercise the full Q01 failure/concurrency/access
contract against isolated synthetic dependencies, including the integrated
mission surfaces named in the assignment.

Reuse existing failure tests and add missing cases. Coordinate bounded runtime
fixes with their feature owner; link each discovered failure to a regression.
Account for every Q01 criterion, preserve redaction and immutable grades, and
return the standard handoff with the correctness baseline Q03 can consume.
Stop after Q01; do not claim capacity or production readiness.
```

### Q02

```text
Work only on Quezo Q02: Accessibility and workflow acceptance.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read Q02 in docs\implementation\04-READINESS.md, its BACKLOG.md prerequisites,
DEC-09 and the referenced specification rules/AT criteria.

Require accepted C03/A01/D04/R02 and the recorded assignment/write allocation.
Exercise the specified author/learner/administrator flows and assigned integrated
mission surfaces using keyboard, responsive views and screen-reader review.
Include timing, focus, errors, save/conflict states and restricted results.

Fix blocking UI findings within the agreed ownership window. Separate automated
evidence from actual manual observations; if screen-reader review cannot be
performed, record that criterion as unverified, not passed. Return every
criterion's result, residual issues and the standard handoff. Stop after Q02.
```

### O01

```text
Work only on Quezo O01: Deployment observability and recovery.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read O01 in docs\implementation\04-READINESS.md, its BACKLOG.md prerequisites,
DEC-08/10 and the referenced specification rules/AT criteria.

Require accepted C03/A01/D04/R02 and the recorded assignment/write allocation.
For full execution/acceptance require approved operational targets. If DEC-08/10
remain held, proceed only when the assignment explicitly limits work to the
package's allowed isolated synthetic rehearsal; report operational acceptance
blocked and retain the unresolved decisions.

Build on existing local images/configuration. Deliver assigned readiness,
redacted observability, migration/release and backup/restore work across
assessment, identity and session dependencies. Rehearse only on owned isolated
resources, verify restored mapping/access/grades, and measure recovery against
approved targets when available. Supply the reproducible environment Q03 needs.
Return the standard handoff and stop; no external deployment is authorized.
```

### Q03

```text
Work only on Quezo Q03: Load and multi-process evidence.
First read and follow docs\implementation\MISSION-HANDOFFS.md section 2.
Read Q03 in docs\implementation\04-READINESS.md, its BACKLOG.md prerequisites,
DEC-08 and the referenced specification rules/AT criteria.

Require accepted O01/Q01, approved workload/environment/numeric gates and the
recorded assignment/write allocation. Verify all workflow producers in the
approved scenario are integrated. Benchmark only the owned isolated target.
Include the proposed 100-concurrent-learner scenario only once it is approved.

Exercise realistic saves/submission bursts and multiple backend processes.
Measure the package's latency, throughput, error and resource signals, separately
from frontend usable time. Assert no lost acknowledged answers or duplicate
grades. Investigate failures without weakening gates; coordinate scoped tuning
and rerun affected correctness cases. Return reproducible evidence, configuration,
limitations and the standard handoff. Stop; capacity evidence is not monthly
availability or pilot approval.
```
