# Engineering Architecture Brief — Quiz Management Platform

**Audience:** Development, Architecture, Product  
**Status:** Architecture drivers and proposed defaults; not a final design or stack decision.

## 1. Purpose and boundary

This brief carries the PRD's architecture drivers into an engineering discussion. It identifies the concepts and correctness rules that should shape the high-level architecture, data model, and API contract. It intentionally leaves framework, hosting, and schema choices open for the alignment session.

The initial system is a standalone web assessment platform. Its boundary includes question authoring, quiz publication, assignment/access, attempt execution, grading, result visibility, and basic reporting. Full LMS functions and automated proctoring are outside the proposed MVP.

## 2. Architecture drivers

| Driver | Why it matters to the design |
| --- | --- |
| Correct historical results | Questions and published quizzes may change; a learner's existing attempt must retain the content and scoring rules they received. |
| Reliable attempts | Acknowledged answers must survive refresh and defined recoverable failures; finalization must be safe to retry. |
| Server-enforced policy | Eligibility, access, deadlines, attempt limits, grading visibility, and organization boundaries require server-side enforcement. |
| Simple first deployment | The product asks for low operational overhead and rapid iteration; avoid distributed infrastructure without demonstrated need. |
| Evolving assessment domain | Stable IDs, versioned questions/quizzes, assignments, attempts, responses, grades, and audit events should support future API and integration work. |
| Responsive and accessible workflows | Learner and author workflows have mobile, keyboard, and screen-reader requirements. |
| Measurable performance | Proposed targets require a representative workload and test environment before they can be release gates. |

## 3. Proposed technical baseline

The source material recommends beginning with a **modular monolith**, a **relational database**, a **documented API contract**, **automated migrations**, automated tests, and a reproducible deployment pipeline. Treat these as defaults for review rather than selected technologies.

Keep the initial deployment straightforward while maintaining clear boundaries for identity/access, question authoring, quiz configuration/publication, assessment execution, grading, reporting, and administration. Add background processing, caching, multiple application instances, or extracted services only when measured requirements justify them.

## 4. Domain model and key relationships

| Concept | Responsibility / relationship |
| --- | --- |
| User | Authenticated identity and account status. |
| Organization + Membership | Optional tenant boundary and a user's role/permissions within it. |
| Group | Cohort, class, or learner grouping. |
| Question + QuestionVersion | Reusable question identity with immutable content/scoring revisions. |
| QuestionBank | Collection of reusable questions. |
| Quiz + QuizVersion | Assessment identity plus immutable published configuration and question composition. |
| QuizQuestion | Connects a quiz version with selected question versions and any quiz-specific point values. |
| Assignment | Distributes a quiz to learners or groups and carries access/availability context. |
| Attempt | One learner's execution of an assessment; associated with an assignment where applicable. |
| AttemptQuestion | Snapshot of the wording, options, order, and grading definition presented in an attempt. |
| Response | Learner answer and save/submission status for an attempt question. |
| Grade | Objective score or manual grading state, with any correction/regrade history. |
| AuditEvent | Trace for publication changes, grade changes, and relevant admin actions. |

Keep **quiz**, **assignment**, and **attempt** distinct: one quiz can be assigned to several cohorts, and each assignment can produce many attempts. Exact cardinalities, constraints, indexes, and storage strategy belong in the high-level architecture and data model.

## 5. Assessment lifecycle and correctness rules

The precise state machine remains to be designed. The source proposes these lifecycle concepts:

- Quiz: draft → published → closed → archived (confirm whether reopening or revision creates a new version).
- Attempt: in progress → submitted, expired, and/or graded (define allowed transitions and when grading is final).
- Response: saved/unsaved and submitted state (define server acknowledgement semantics and conflict behavior).

The following invariants should shape the design and tests:

1. **Server-authoritative time:** The client can display a timer, but the server decides whether an attempt is within its deadline.
2. **Durable acknowledgement:** A successful save response means the answer is persisted according to an explicit durability contract.
3. **Idempotent finalization:** Retried or concurrent submits produce one finalized attempt and one consistent score.
4. **Attempt snapshot:** An attempt preserves the question version/content, option order, and scoring rules presented to that learner.
5. **Publication consistency:** Changes to a question or quiz do not silently mutate an attempt already in progress or an existing result.
6. **Policy-controlled disclosure:** Correct answers, explanations, and scores are returned only when the configured result policy permits them.
7. **Consistent authorization:** The API enforces the same permission model as the UI; learners cannot access another learner's answers or grades.
8. **Tenant isolation:** If multi-organization operation is enabled, all content and result access is scoped and tested at the organization boundary.
9. **Auditable grading changes:** Manual grade changes and regrades retain who changed what and when.

## 6. API design starting point

The initial API contract should cover the supported MVP domain and define authorization, request/response schemas, validation, error behavior, idempotency, and versioning. Candidate resource groups are:

- users, memberships, and organizations (if in scope)
- questions, question versions, and question banks
- quizzes, quiz versions, publication, and preview
- assignments and eligibility
- attempts, attempt questions, and responses/autosave
- submission and scoring
- grades and result visibility
- basic reporting and exports (when enabled)

The source sets documented API access at P1 while calling the MVP “API-ready” and requiring stable identifiers and equivalent authorization in P0. Product and Engineering should define whether P0 means API-capable internals or an externally supported API.

## 7. Proposed quality targets and validation

The PRD proposes p95 API read latency ≤300 ms at an agreed baseline, quiz UI usable in 2.5 seconds at p75, 100 concurrent active learners without correctness failures, 99.5% monthly availability, and WCAG 2.2 AA for core workflows. These are proposals, not established capabilities or contractual targets.

Before adopting them, agree on workload, device/network profile, deployment environment, availability exclusions, recovery objectives, and whether the product is used for formal examinations. The first load test should include autosave traffic and a burst of simultaneous submissions. Record p50/p95/p99, error rate, CPU, memory, and database connection utilization.

## 8. Engineering practices for the first release

- Use automated migrations and a reproducible environment/deployment process.
- Test critical state transitions, grading rules, access controls, question/version snapshots, and submission idempotency.
- Add structured logs, health checks, error reporting, and operational metrics; avoid unnecessary logging of sensitive answer content.
- Define backup and restore procedures with agreed recovery objectives.
- Implement short end-to-end vertical slices rather than independent frontend/backend/database tracks.
- Start with the assessment lifecycle slice: create/reuse a question → create and publish a quiz → start an eligible learner attempt → save answers → submit once → calculate and display permitted results.

## 9. Decisions required from Product and Engineering

| Decision | Architecture impact | Current status / candidate default |
| --- | --- | --- |
| First audience and use case | User roles, organization model, UX, and acceptance criteria | Open; instructor/learner is the current working assumption. |
| Practice vs. formal examination | Identity, audit, timer behavior, grading, availability, privacy, and reliability | Open; objective practice quizzes are the proposed starting point. |
| Single organization vs. multi-tenant | Ownership, membership, data isolation, and query constraints | Open; simple organization model can be enabled when needed. |
| Expected traffic and peak concurrency | Hosting, scaling, database tuning, and test targets | Open; 100 active learners is a proposed target, not confirmed demand. |
| Authentication and SSO | Identity integration, session model, account lifecycle | Open; secure auth and server-side role checks are baseline requirements. |
| Data/privacy/compliance obligations | Retention, deletion, audit, deployment, and access policy | Open; confirm jurisdiction, contracts, and institutional requirements. |
| Hosting and delivery constraints | Deployment design, cost, environments, and operations | Open; one reproducible deployment is the proposed default. |
| Public API scope | Auth, compatibility policy, documentation, support expectations | Open; documented external API proposed for a later release unless required sooner. |
| Question import/interoperability | Canonical data format, compatibility, migration scope | Open; investigate QTI/LTI only after validating need. |

## 10. High-Level Architecture Document outline

After the PRD decisions are confirmed, the HLA should document:

1. Architecture drivers: functional priorities, quality attributes, constraints, and workload.
2. System context: user roles, external systems, identity providers, and integration boundaries.
3. Container/component view: frontend, backend/domain modules, persistence, and background processing if needed.
4. Domain model: question/quiz versions, assignments, attempts, responses, grading, and audit events.
5. State machines: publication, attempt lifecycle, autosave, submission, timeout, grading, and result release.
6. API: auth, authorization, resource contracts, errors, idempotency, and versioning.
7. Security and privacy: threat model, data isolation, session security, retention, and auditability.
8. Performance and reliability: load profiles, persistence, caching decisions, recovery objectives, and failure handling.
9. Deployment: environments, configuration, migrations, backups, observability, and release process.
10. Architecture decision records: alternatives, rationale, trade-offs, and deferred choices.
