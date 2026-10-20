# Product & Engineering Alignment Workshop

**Audience:** Product, Design, Development, and relevant customer/stakeholder representatives  
**Purpose:** Resolve the uncertainties that could cause significant rework across product scope, user experience, data model, API, and deployment.

## 1. Desired outputs

By the end of the session, the team should have:

- A named first customer/user and the primary problem to solve.
- An agreed first end-to-end workflow and MVP boundary.
- Initial role, organization, assessment, and result-visibility rules.
- A decision on whether formal assessment needs change the proposed baseline.
- A technical starting point and a list of explicitly deferred architecture choices.
- Owners and follow-up dates for any decision that remains open.

The session does not need to finalize every requirement or architecture decision. It needs to make the assumptions behind the first implementation visible and binding enough to build one vertical slice.

## 2. Suggested pre-read

1. [Product Strategy & Competitive Assessment](01-Product-Strategy-and-Competitive-Assessment.md)
2. [Product Requirements Document](02-Product-Requirements.md)
3. [Engineering Architecture Brief](03-Engineering-Architecture-Brief.md)

Ask participants to flag: (a) a requirement they consider mandatory for Release 1, (b) an assumption they disagree with, and (c) a risk that would block a first pilot.

## 3. Customer discovery questions

Use these questions to establish what needs to be built and why. Record evidence and decisions rather than treating unanswered questions as requirements.

### A. Customer and problem

- Who is the primary customer: an individual instructor, university, corporate training organization, independent learner, or another group?
- What problem with current quiz apps or LMS products are we solving?
- What does the customer use today, and what is frustrating or missing?
- What single outcome must the first release deliver?
- Is the product for internal use, commercial SaaS, or open source?

**Decision output:** First target user, problem statement, and value proposition.

### B. Assessment workflow

- Who creates a quiz, who takes it, and who reviews results?
- Do learners use public links, invitations, or assigned accounts?
- Are assessments for practice, formal exams, certification, or more than one of these?
- Are time limits, attempt limits, randomization, and scheduled availability required at launch?
- Must authors grade essay or short-answer responses at launch?
- When may learners see scores, answer keys, and feedback?

**Decision output:** End-to-end workflow and minimum assessment capabilities.

### C. Users and organizational boundaries

- Is the platform for one organization or multiple tenants?
- Are courses, classes, cohorts, teams, or only quizzes needed initially?
- Can instructors share question banks?
- Are guest users allowed?
- Who owns questions and assessment results?

**Decision output:** Roles, access boundaries, ownership, and organization model.

### D. Scale, performance, and reliability

- How many registered users and active learners are expected initially?
- How many learners may start or submit simultaneously?
- What is the typical question count per quiz?
- What should happen if a learner loses connectivity during an assessment?
- Are availability windows or high-stakes assessment requirements strict?
- What downtime or data loss is acceptable?

**Decision output:** Workload profile and measurable performance/recovery targets.

### E. Security, privacy, and compliance

- Will the platform store personally identifiable or sensitive assessment records?
- Are institutional identity providers or single sign-on required?
- Which institutional, contractual, accessibility, or regulatory obligations apply?
- Are audit trails, retention, export, or deletion required?
- Is proctoring required, or explicitly out of scope?

**Decision output:** Security baseline, identity approach, and privacy/compliance constraints.

### F. Delivery constraints

- When must the first working release be available?
- Is there a fixed budget or hosting environment?
- Is the product self-hosted or cloud-hosted?
- Are there existing systems, datasets, or identity services to reuse?
- What is an acceptable first demonstration?

**Decision output:** Deadline, budget, hosting constraints, and demo criteria.

## 4. Product-team alignment questions

| Topic | Questions to resolve | Expected output |
| --- | --- | --- |
| MVP boundary | What must work end-to-end in Release 1? What is explicitly deferred? | MVP scope and non-goals |
| User experience | Which three screens matter most? What should first use look like? | User flows and wireframes |
| Differentiation | Why use this instead of Canvas, Blackboard, or a simpler quiz app? | Confirmed value proposition |
| Question types | Which formats are mandatory at launch? | Question-type specification |
| Assessment rules | How do scores, attempts, deadlines, randomization, and feedback work? | Assessment rules |
| Reporting | Which metrics matter on day one? | Reporting requirements |
| Content migration | Are spreadsheet, CSV, QTI, or existing-system imports required? | Import/export requirements |
| Success measures | How will the team know the MVP is useful? | Product KPIs and acceptance criteria |
| Prioritization | Which features are P0, P1, and P2? | Ranked backlog |
| Release acceptance | Who approves the demo and release readiness? | Acceptance/sign-off process |

**Specific choice to settle:** Is the primary product for low-stakes practice or formal assessment? Formal use raises the importance of versioning, auditability, identity, timing, grading disputes, and reliability from the first release.

## 5. Engineering questions

| Topic | Question | Initial deliverable |
| --- | --- | --- |
| Application structure | Modular monolith or distributed services for the first release? | Component boundary sketch |
| Frontend | Which framework, UI library, and state/form approach fit the team and flows? | Frontend baseline |
| Backend | Which framework supports domain rules, validation, authentication, and API docs? | Backend baseline |
| Persistence | Which relational database approach fits assessment data and transactional guarantees? | Initial data model |
| Authentication | Local auth, identity provider, or both? | Identity integration decision |
| API contracts | How are questions, quizzes, assignments, attempts, and results exposed? | Initial API contract |
| Assessment execution | How do autosave, concurrent requests, timers, and retries work? | Attempt state machine |
| Testing | What is unit-, integration-, and end-to-end-tested? | Test strategy |
| Deployment | What is the shortest reproducible path from commit to running app? | CI/CD and deployment baseline |
| Observability | How will API, database, and failed-submission issues be diagnosed? | Logs and health checks |
| Configuration | How are secrets, environment settings, and migrations managed? | Configuration convention |
| Performance | What is the first representative load test? | Baseline benchmark |

**Current engineering recommendation:** Start with a modular monolith, relational database, documented API contract, automated migrations, and reproducible deployment. Keep service extraction and distributed infrastructure as evidence-driven choices.

## 6. Day-zero decision log

Use this as the exit checklist before implementation backlog is locked. Every decision should have an owner, status, rationale, and date. Current defaults below are proposals from the notes, not approvals.

| # | Decision | Proposed starting point | Status / owner |
| --- | --- | --- | --- |
| 1 | Target user | Instructor/assessment author and learner are the initial role hypothesis; name the first customer segment. | Open — assign in session |
| 2 | Primary workflow | Create/reuse question → create and publish quiz → learner completes → result is recorded and shown by policy. | Open — Product |
| 3 | MVP boundary | Use the PRD P0/P1/P2 list as a proposal; explicitly confirm Release 1 and non-goals. | Open — Product |
| 4 | Roles and access | Author, learner, and administrator; decide whether organization/group boundaries are needed at launch. | Open — Product + Engineering |
| 5 | Assessment rules | Single-answer MCQ and true/false first; settle scoring, deadlines, attempts, randomization, and result visibility. | Open — Product |
| 6 | Technical baseline | Modular monolith and relational persistence are proposed; select stack, hosting, and identity approach. | Open — Engineering |
| 7 | API and domain model | Start from Question/Version, Quiz/Version, Assignment, Attempt, Response, Grade, and AuditEvent. | Open — Engineering |
| 8 | Definition of done | Use PRD acceptance criteria plus agreed security, accessibility, concurrency, latency, and operational gates. | Open — Product + Engineering |

## 7. Open inconsistencies to resolve during the session

1. **Written grading:** The core “Review results” journey includes grading written responses, while manual grading is P1/Release 2. Confirm whether the journey is conditional or the feature moves into Release 1.
2. **API-ready:** The PRD overview describes the app as API-ready, while a documented API is P1. Define whether MVP needs an external API or only an API-capable internal architecture with stable identifiers and shared authorization.
3. **Performance gates:** The 100-active-learner and 99.5% availability targets are proposals. Confirm expected load, use case, environment, and recovery needs before making them acceptance criteria.
4. **Multi-tenancy:** Roles and organization concepts appear in the domain model, but organization boundaries are conditional/P1. Confirm launch ownership and isolation requirements.
5. **Practice vs. formal exams:** This is the most consequential product decision because it changes identity, audits, timing, grading, privacy, and reliability.

## 8. Suggested rapid-development workflow

For each slice:

1. Agree on the user story.
2. Define acceptance criteria and the API contract, including permissions, schemas, validation, and errors.
3. Implement the full path: migration → backend → UI → automated tests.
4. Deploy and validate it in a running environment.
5. Demonstrate to Product, record gaps, and reprioritize.

The first slice should exercise the central domain: create/reuse a question → create and publish a quiz → complete an attempt with autosave → submit safely → score → show permitted results. This will expose foundational product and architecture gaps early.

## 9. Implementation-readiness pack to produce

The alignment session should lead to these concise artifacts:

1. Product decisions and assumptions log.
2. Prioritized MVP backlog with testable acceptance criteria.
3. Initial user flows and wireframes.
4. Domain model and assessment state machine.
5. Initial API contract.
6. Technology and deployment decisions.
7. Definition of done and first vertical-slice plan.

Resolve product ambiguity before it becomes code. Defer architecture choices that do not affect the first working slice.
