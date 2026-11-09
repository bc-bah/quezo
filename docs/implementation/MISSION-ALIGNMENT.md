# Mission gap audit and prioritized development approach

**Date:** 9 November 2026

**Audit baseline:** current checkout at `1f8b4d1`.

**Status:** planning direction recorded at the user's request; new features are
not implemented or dispatched by this update. Detailed product decisions remain
open in [DEC-12 through DEC-18](../SOFTWARE-SPECIFICATION.md#2-decision-register).

## 1. Purpose and evidence boundary

The customer notes supplied on 9 November describe the 526th IS DOT team's
recurring IQT/MQT assessment workflow: paper administration, hand grading,
manual outcome calculation and re-entry into a tracking process for classes
of approximately 80-100 students. The stated needs are timely results,
accessible metrics, reuse of prior training information and less personnel
workload. Pass/fail and flight-level results are existing metrics; duration,
section success and question difficulty are potential interests to validate.
The notes do not define the subsequent review/action process.

Sources supplied with the request: **Customer Impact (What are 526 IS Mission
Gaps/Challenges)**, **Background / Problem**, and **Simplified Workflow**.
This document records their assessment-management requirements, not approval
to use actual training content or personnel records.

The audit compared those notes with application code, schemas, UI and existing
evidence records. "Implemented" means code is present, not that package
acceptance, operational capacity or pilot approval has been established.
No new runtime, load or accessibility result is claimed by this documentation
update. The original product references and accepted lifecycle remain intact.

**Finding:** the digital author-to-result lifecycle already exists. The largest
mission gaps are class/flight/iteration context, explicit pass/fail rules and
usable leadership reporting. Build on existing delivery, immutable grading and
history rather than replacing them.

## 2. Workflow coverage

| Customer workflow / need | Present in the audited checkout | Missing or incomplete |
| --- | --- | --- |
| 1. Develop assessment content | Reusable banks, categories/tags, MCQ/true-false, immutable question versions, composition and preview/publication | No Word/PDF/Excel ingestion; no structured IQT/MQT or assessment-section model; written responses unsupported |
| 2. Administer assessments | Authenticated named assignments, schedule/attempt limits, timing controls and randomized ordering | No training iterations, class rosters, flight membership or batch assignment; learner selection is one application ID at a time |
| 3. Collect responses | Durable save/clear/resume, explicit conflict/retry states and submission | 80-100 concurrent learner capacity is not established by functional implementation |
| 4. Grade assessments | Automatic objective scoring from delivered snapshots; correct/incorrect/unanswered distinctions | No manual grading; only add it if actual assessment formats require it |
| 5. Calculate outcomes | Earned/possible points and report percentages | No passing threshold or explicit pass/fail outcome; completion is not passing |
| 6. Record results | Immutable persisted grades, learner history and author submission inspection | No results export or external tracker integration; retaining the current tracker may still require re-entry |
| 7. Produce metrics | Per-quiz participation/completion, submitted/expired counts and mean released score | No class/flight breakdown, iteration comparison, pass rate, section/item analytics, duration summaries or dedicated leadership reporting access |
| 8. Review and act | Individual submission inspection | No recorded remediation/follow-up workflow; customer action/ownership rules are undefined |

### Implementation evidence and interpretation

| Evidence | What it establishes |
| --- | --- |
| [Question schemas](../../postgres/src/quezo_api/modules/questions/schemas.py), [quiz schemas](../../postgres/src/quezo_api/modules/quizzes/schemas.py) | Objective types, reusable versions and publication composition; category/tag metadata is not a versioned section-scoring model |
| [Assignment UI](../../frontend/quezo/src/app/author/quizzes/assign.tsx), [distribution service](../../postgres/src/quezo_api/modules/distribution/service.py) | One learner/version per assignment; duplicate assignment preserves allowance; author selection exposes application IDs |
| [Delivery settings](../../frontend/quezo/src/app/author/quizzes/policy-settings.tsx), [quiz policy](../../postgres/src/quezo_api/modules/quizzes/policies.py) | Timing, availability, attempt limits, order flags and independent result release; no pass threshold |
| [Response service](../../postgres/src/quezo_api/modules/attempts/responses.py), [scorer](../../postgres/src/quezo_api/modules/scoring.py), [finalization](../../postgres/src/quezo_api/modules/attempts/finalization.py) | Durable response updates, snapshot-based objective scoring and persisted finalization/grade records |
| [Report contracts](../../postgres/src/quezo_api/modules/results/schemas.py), [result service](../../postgres/src/quezo_api/modules/results/service.py), [report UI](../../frontend/quezo/src/app/author/quizzes/%5BquizId%5D/results/page.tsx) | History, owner-only reports and submission review, not cohort or leadership reporting |
| [R02 evidence](../DEVELOPMENT.md#r02-history-and-author-reporting), [browser scenarios](../../tests/e2e/reporting.spec.ts) | Existing scoped reporting evidence, not 100-user capacity, full acceptance or a new execution result |

Current reporting counts distinct assigned learners for participation/completion
across a quiz's publications. Its mean weights each **released finalized
attempt percentage** equally; it does not select a learner's first, latest or
best attempt. Withheld scores are excluded from author aggregates too.
Leadership reporting must explicitly resolve access and aggregation rules,
not silently bypass learner release policy or relabel this mean as a pass rate.

Immutable versions and grades support historical preservation, but do not
identify training iterations or make different assessments comparable.
Started/finalized timestamps support possible elapsed-duration reporting, not
active working time. Resumes, timing choices and delayed expiration processing
need explicit treatment before duration is reported.

## 3. Prioritized implementation packages

These are mission priorities, not a renumbering of the original PRD P0/P1/P2
requirements. Existing P0 and readiness obligations remain. The
[backlog](BACKLOG.md#mission-alignment-backlog) owns status, prerequisites and
dispatch; the specification owns decision approval. Every package is a vertical
slice covering persistence, API, authorization, UI and appropriate evidence.

### M01: Training iterations, rosters and bulk assignment - essential

Add lightweight IQT/MQT and class/iteration context, roster membership, flight
attribution and approved readable learner labels. Preserve historical membership
context so a later flight transfer does not silently rewrite old reports.
Support batch assignment to a published version with explicit per-recipient
outcomes and retry-safe behavior. Reuse existing named-learner authorization;
neither a roster nor an assessment link implicitly grants access.

**Acceptance:** assign one publication to a synthetic 100-person class without
100 individual actions; retries neither duplicate assignments nor reset
allowances; invalid/disabled recipients produce visible outcomes. Demonstrate
historical reporting context after a roster change. This is a batch workflow
criterion, not evidence of 100 simultaneous attempts.

**Decision gate:** DEC-12 must resolve iteration/roster/flight semantics, allowed
profile fields and assignment identity when the same learner/version recurs.
The current uniqueness rule is one assignment per learner/version; do not
silently reuse an exhausted assignment for a new training iteration.

### M02: Explicit pass/fail outcomes - essential

Version the passing rule with publication and preserve the rule used for each
attempt outcome. Define percentage/point comparison, rounding boundaries,
retake selection and unfinished/expired treatment before changing contracts.
Keep existing grades immutable; do not manufacture historical pass/fail outcomes
where no applicable rule was recorded.

**Acceptance:** below/at/above-threshold cases classify correctly; later policy
edits do not rewrite history; completion is distinct from passing, and unfinished
work is not silently counted as failure. Show explicit handling of historical
grades without a passing rule. **Decision gate:** DEC-13.

### M03: Instructor/leadership reporting and result handoff - essential

Add class/flight/iteration filters, completion and pass rates, learner outcomes
and scoped read-only reporting access. Resolve the relationship between staff
reporting permissions and learner release rules. If the existing tracker remains
required, agree a CSV handoff format first; do not assume an external API exists.
Avoid granting authorship or unrestricted assessment access just to view reports.

**Acceptance:** known synthetic outcomes reconcile across grade records, report
totals and the agreed export; show denominators, reporting scope, publication,
attempt-selection rule and withheld/unfinished states. Authorized staff can
produce the report without score re-entry; unauthorized scopes and protected
fields remain inaccessible. **Decision gate:** DEC-14.

### M04: Repeatability and cross-iteration comparison - next

Reuse definitions for a subsequent training iteration and compare retained
class/flight outcomes. Identify question/quiz versions, passing rules and retake
policies so changed assessments are not presented as equivalent. Reusing the
existing publication may suffice; a duplicate-quiz command is not assumed.

**Acceptance:** demonstrate two iterations without mixing their membership or
allowances; unchanged and changed assessment versions are distinguishable;
comparability limitations are visible. **Decision gate:** DEC-15.

### M05: Diagnostic metrics - validate customer value first

Add agreed elapsed-duration summaries, versioned section/objective mappings and
per-question correct/incorrect/unanswered rates. Preserve mappings used by a
publication rather than aggregating historical grades against mutable tags.
Define which attempts contribute, sample size, zero denominators and
standard/adjusted/off timing treatment. A percent-correct measure is not a claim
of calibrated question difficulty.

**Acceptance:** synthetic data with known outcomes reproduces the agreed
calculations; each metric shows its population, sample size, version and relevant
limitations. Elapsed duration is not labelled active time; expiry-worker delay
must not silently inflate the chosen duration measure. **Decision gate:** DEC-16.

### M06: Structured content onboarding - conditional

If existing-content migration is a significant burden, start with a validated
spreadsheet/CSV template, preview and explicit review before publication.
Handle invalid rows and duplicate/retry behavior explicitly. Arbitrary
Word/PDF extraction, OCR and AI authoring remain deferred.

**Acceptance:** import a representative synthetic content set, report rejected
rows without silent loss, and require review before publication.
**Decision gate:** DEC-17, including supported format and content types.

### M07: Review and follow-up - conditional

Define who acts on results, what action is recorded and what closes it before
building remediation tracking. Prefer a small assigned follow-up/status workflow
over an LMS. Manual grading, regrading and automated personnel/readiness
decisions are not implicitly included.

**Acceptance:** an authorized reviewer records an action against an outcome,
assigns its owner and records closure without modifying the original grade.
**Decision gate:** DEC-18.

## 4. Readiness and proposed demonstration

Readiness proceeds alongside assigned feature work; it is not postponed until
all optional analytics are built. Preserve Q01 integrity/access, Q02
accessibility/workflow, O01 operational/recovery and Q03 load gates. Extend their
coverage to new mission surfaces as those surfaces are implemented. Q03 still
requires O01's reproducible environment, Q01's correctness baseline and DEC-08's
approved workload/thresholds. A class size in the notes is not a throughput or
latency commitment.

**First mission demonstration:** one synthetic 100-person class divided into
flights, batch assignment of an objective assessment, durable response
collection, automatic grading and pass/fail, and a reconciled class/flight report
with the agreed tracker handoff. Then repeat for a second iteration to
demonstrate reuse and comparison (M04). Measure instructor assignment,
grading/calculation, report preparation and re-entry effort against an agreed
manual baseline; no saved-hours claim is established by the audit.

Before real-class use, demonstrate realistic concurrent saves/submission bursts,
no lost acknowledged answers or duplicate grades, accessible workflows and
recovery. Approve hosting, data handling/retention, identity operations and
incident ownership under DEC-08/10/11. G01 acceptance of the original lifecycle
does not automatically accept these new mission packages or permit real data.

## 5. Implementation versus acceptance reconciliation

A01 administration, D04 delivery controls and R02 history/reporting are present
in the audited checkout, with implementation/evidence sections in the
[development guide](../DEVELOPMENT.md). Older statements that they await their
first implementation are historical, not current capability descriptions.
They are tracked as `review`, not `done`: this update does not invent full
acceptance, new hosted results or pilot approval. Original dated approvals and
execution records remain available for provenance.
