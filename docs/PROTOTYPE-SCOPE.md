# Prototype scope

**Date:** 20 October 2026  
**Updated:** 9 November 2026

**Status:** Foundations, Phase 2 lifecycle through T01, and C03 accepted;
A01/D04/R02 implemented with scoped evidence and tracked for acceptance review.
The [mission audit and roadmap](implementation/MISSION-ALIGNMENT.md) adds planned
customer-alignment work; no new feature dispatch or acceptance is implied.
Pilot, deployment, and other held decisions remain tracked in the specification.
This is not a production-readiness claim.

## 1. Source and decision precedence

The [PRD v0.1](reference/02-Product-Requirements.md) supplies requirement IDs and
acceptance criteria. The [strategy](reference/01-Product-Strategy-and-Competitive-Assessment.md),
[engineering brief](reference/03-Engineering-Architecture-Brief.md), and
[workshop](reference/04-Product-Engineering-Alignment-Workshop.md) provide rationale
and open questions.
On 20 October 2026, the user approved **Python/FastAPI** for the backend:
its maintainers are comfortable with Python and accept a two-language stack.
Quezo uses Next.js/React for the frontend, PostgreSQL for persistence, Keycloak
for identity, and Docker for containerization. The product source documents are
preserved unchanged.

The user confirmed **single-organization, low-stakes P0 prototype** on
20 October 2026. All P0 requirements remain in the target prototype; the first
vertical slice is a delivery sequence, not a reduction of that scope. The
9 November mission roadmap selectively brings previously deferred cohort,
comparison, export and analytics capabilities into planning, subject to the
decision gates below. It does not generally promote all PRD P1/P2 requirements.
Proposed rules require review before implementation.

## 2. Outcome and audience

Prove this complete workflow for an author, learner, and administrator in one
organization:

> Create and reuse objective questions -> configure and publish a quiz ->
> authorize a learner -> save and resume an attempt -> finalize exactly once ->
> score against the delivered version -> show only permitted results.

The product is assessment-first, not a learning management system. The prototype
uses synthetic questions and test identities. It does not establish suitability
for formal exams, certification, sensitive institutional records, or public SaaS.
The 526th IS DOT notes now supply the planning context for IQT/MQT assessments,
recurring 80-100-person classes and flight-level reporting. A real-data pilot
audience and approval remain unconfirmed under DEC-10.

## 3. P0 coverage

These rows define the original P0 target, not its completion status. Consult the
[backlog](implementation/BACKLOG.md) for acceptance and the
[audit coverage matrix](implementation/MISSION-ALIGNMENT.md#2-workflow-coverage)
for implemented behavior versus mission gaps.

| PRD requirements | Prototype scope | Evidence expected at review/demo |
| --- | --- | --- |
| FR-001-004 | Keycloak sign-in; administrator/author/learner roles; account/access administration; ownership checks | Sign in as each role; prevent cross-author access; disable an account and deny further assessment operations |
| FR-010-015, FR-018 | Author-owned question bank; create/edit/archive; text/category/tag search; single-answer MCQ and true/false; points and feedback; reuse and preview; immutable revisions | Reuse a question in two quizzes; edit its draft without altering an existing attempt or published revision |
| FR-020-026 | Quiz authoring; bank selection and point overrides; time/attempt limits; question/option ordering randomization; zoned availability; draft/published/closed/archived; learner preview; disclosure policy | Publish and preview; enforce schedule and limits; keep ordering stable on refresh; close/archive safely |
| FR-030-038 | Named-learner assignment and authenticated links; eligibility; answer navigation and revision; durable autosave and resume; server deadlines; retry-safe submission and explicit status | Refresh after a save, disconnect/reconnect, retry/conflict saves, race submissions, and verify one final result |
| FR-040-043 | Objective auto-grading, configured points, retained answers/timestamps/state, authorized result release | Verify both supported question types, unanswered items, points, and restricted results |
| FR-050-052, FR-056 | Learner history; author participation/completion/score summary; individual submission review; explicit unanswered/incorrect/finalized distinctions | Inspect two learners' attempts without leaking one learner's work to another; no manual-grade state is needed while written answers are excluded |
| FR-061-062 | Server authorization for every application interface and stable identifiers | Negative authorization coverage for the same operations invoked outside the UI |

Assignment is separate from Quiz and Attempt even without cohorts. Proposed
prototype distribution is an author assigning named active learners, with a link
that locates the quiz but never grants access by itself. Self-enrollment and
public/guest links are not implicitly included.

FR-004 has an A01 in-app administration implementation using a narrowly
privileged local Keycloak adapter and application-owned access records.
Implementation and scoped evidence do not yet establish full package acceptance.

## 4. Explicit deferrals and reconciled inconsistencies

The original baseline exclusions below distinguish delivered scope from planned
mission extensions. M01-M07 are defined in the
[mission roadmap](implementation/MISSION-ALIGNMENT.md#3-prioritized-implementation-packages);
their detailed rules remain open under DEC-12 through DEC-18.

| Baseline deferral / mission planning change | PRD references / interpretation |
| --- | --- |
| Multiple organizations | Remains deferred; one deployment serves one organization; no tenant isolation claim |
| Group/cohort management and comparisons | FR-005, FR-055; planned lightweight class/flight/iteration scope in M01/M03/M04, not a general group-management or LMS capability |
| General audit browser, audit export, grade correction and regrading | FR-006, FR-045-046; retain minimal publication, access-change and finalization records for integrity, without promising full audit reporting |
| Multiple-answer, short-answer and essay questions; manual grading | FR-016, FR-044; PRD journey 3's written-grading step is conditional and excluded here |
| Question import/export and results CSV export | FR-017, FR-053; M03 plans a validated results handoff if the tracker remains required; M06 conditionally plans structured content import. General question export and arbitrary document extraction remain deferred |
| Quiz duplication, random selection from pools | FR-027-028; randomizing the order of all selected questions/options remains P0 |
| Guests and anonymous attempts | FR-039 |
| Question-level analytics | FR-054; M05 plans agreed diagnostic metrics only after customer validation |
| Supported public API, third-party credentials and compatibility commitment | FR-060; internal REST contracts are documented as developed, with FR-061 authorization from day one |
| QTI/LTI, AI authoring, proctoring, LMS features, native apps | FR-063-064 and PRD non-goals |
| Microservices, message brokers, Redis, WebSockets, media/CDN pipelines, subscriptions | Not required by the prototype's assessment workflow |

**Additional mission gaps:** M02 adds explicit pass/fail policy rather than
equating completion with passing. M03 adds scoped leadership reporting; current
owner reports exclude withheld scores and average all released finalized attempts.
M07 follow-up tracking depends on an agreed review/action process. These are
planned scope additions, not existing behavior or implicit changes to release
authorization.

## 5. Demonstration and acceptance

Use three test identities (administrator, author, learner), plus a second author
and learner for access-control checks. Prepare at least two quizzes sharing a
question, with both supported question types and different result policies.

1. Administrator provisions/assigns roles and disables access. Author organizes,
   searches, previews, reuses, publishes, closes, and archives content.
2. Learner accesses an assigned quiz in its availability window; repeat starts
   cannot bypass attempt limits. Randomized presentation survives refresh.
3. Acknowledged answers survive refresh, process restart, and a temporary network
   interruption within the agreed persistence contract. Unsaved edits stay
   visibly unsaved; stale saves cannot overwrite newer answers silently.
4. Submission retries and concurrent submission/expiry produce one finalized
   result. Deadline rejection is based on server time, not browser time.
5. Scores use fixed delivered questions and points. Hidden answers/feedback are
   absent from learner payloads. Learner history and author summaries agree.
6. PRD security, accessibility, concurrency, and recovery evidence is reviewed
   before any pilot; scaffolding alone satisfies none of those product gates.

The PRD's 100 active learners, p95 reads <=300 ms, p75 usable UI <=2.5 seconds,
99.5% availability, and WCAG 2.2 AA are proposed targets. Workload, environment,
measurement method, and operating commitments must be agreed before adoption.

The [mission demonstration](implementation/MISSION-ALIGNMENT.md#4-readiness-and-proposed-demonstration)
adds a synthetic 100-person class with flight attribution, batch assignment,
automatic pass/fail and reconciled report/handoff, followed by a second training
iteration. A batch assignment demonstration does not prove concurrent capacity.
Q01/Q02/O01/Q03 remain parallel readiness work and gates before real-class use.

## 6. Proposed delivery sequence after approval

The [software specification](SOFTWARE-SPECIFICATION.md) expands this scope into
testable rules and acceptance cases. The [implementation bundle](implementation/README.md)
is the delivery source of truth: baseline approval, working foundations, first
complete lifecycle, parallel P0 completion, hardening/operations and acceptance.
Its [backlog](implementation/BACKLOG.md) records actual package prerequisites,
ownership, status and evidence.

The mission sequence is M01 roster/iteration context, M02 pass/fail and M03
reporting/handoff first; M04 comparison next; M05 diagnostics after validation;
M06 content onboarding and M07 follow-up only where customer needs justify them.
Priority order does not add hidden prerequisite edges: use the mission backlog.

Each feature slice includes its migrations, interface contract, UI, authorization
and tests. Detailed product decisions remain proposed until recorded as approved
in the specification's decision register. No slice is authorized to start by the
creation of these documents.

## 7. Review gate

| Decision | Current position | Owner / gate |
| --- | --- | --- |
| Audience, organization scope, priority coverage | Single-organization, low-stakes, all P0; confirmed by user | Product; confirmed 20 October 2026 |
| Technology stack | Next.js/React, Python/FastAPI, PostgreSQL, Keycloak and Docker; two-language stack explicitly accepted | Confirmed 20 October 2026 |
| Exact versions, packages, module layout | Foundations through I02 integrated and locked, including Playwright browser evidence; Phase 2 reuses these tools | B.C.; Phase 2 assignment 21 October 2026; production suitability still requires review |
| Assignment, deadline/closure, attempt accounting, scoring, result-release semantics | DEC-01-05 baseline implemented through T01; C03 accepted; D04 controls and R02 reporting implemented, acceptance under review | B.C.; historical approvals retained; 9 November implementation reconciliation does not confer acceptance |
| Keycloak realm/provider, login claims, administration privileges | I02 local identity/session boundary accepted; scoped local-realm least-privilege A01 service identity approved; exact permissions must be verified/recorded before privileged implementation | B.C.; DEC-06 scoped amendment 27 October 2026; no production/external provisioning or broader administration approval |
| Timed learner accessibility | Pre-start standard/adjusted/off controls implemented with scoped evidence; D04 acceptance and Q02 evidence remain open | B.C.; DEC-09 approved 27 October 2026; no WCAG conformance claim |
| Mission-aligned scope and reporting rules | M01-M07 planned; roster/assignment identity, passing rules, reporting access, comparisons, metric definitions, import and follow-up decisions remain open | B.C.; DEC-12 through DEC-18 before affected implementation |
| First customer, pilot data policy, retention/deletion obligations | DEC-10 held; synthetic data only meanwhile | B.C. to obtain product/privacy review before pilot |
| Hosting, workload, recovery objectives, availability commitment | DEC-08/10 held; local Docker is not hosting approval | B.C. to obtain engineering/operations review before applicable operational gates |
| Delivery date, budget, release approver | DEC-11 later commitments held; B.C. owns foundation, Phase 2 and C03/A01/D04/R02 integration/review/merge | B.C. before scheduling/release commitment |

**Current gate:** T01 is accepted at merge `df06ccc`, completing Phase 2;
I02 and EX-I02-01 closure remain accepted. See the
[27 October readiness record](SOFTWARE-SPECIFICATION.md#c03-acceptance-and-phase-3-approvals-27-october-2026):
C03 is accepted at local dev `2eba9eb`, head `0010_author_workspace`.
A01/D04/R02 now have code and scoped evidence in this checkout; review acceptance
rather than redispatching their original implementation. B.C. serializes shared
writes/migrations. New mission packages remain planned behind their decision
and prerequisite gates. No automatic dispatch, deployment or pilot is authorized.
