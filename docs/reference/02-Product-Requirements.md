# Product Requirements Document — Quiz Management Platform

**Document type:** Product Requirements Document  
**Version:** 0.1  
**Status:** Proposed baseline for internal review  
**Audience:** Product, Design, Development, QA

## 1. Product overview

### Purpose

Build a lightweight, maintainable web application for authoring, administering, delivering, grading, and analyzing quizzes and assessments. The product combines the usability of standalone quiz apps with selected assessment capabilities found in higher-education LMS platforms. It does not aim to replace a complete LMS.

### Problem

Lightweight quiz applications tend to prioritize quiz-taking, trivia, or basic question management. Comprehensive LMS products provide more advanced assessment controls but also include broader course and content functions that can be unnecessary for users whose main need is quizzes. The proposed product fills that gap with a standalone assessment workflow, reusable questions, configurable delivery, reliable results, and practical analytics.

### Objectives

- Minimize the time required to create and publish a quiz.
- Make quiz-taking straightforward on desktop, tablet, and mobile browsers.
- Provide reliable assessment execution, answer persistence, submission, and scoring.
- Support question reuse across assessments.
- Provide sufficient administration, grading, and analytics for small-to-medium assessment workflows.
- Keep operational complexity and resource use low.
- Establish a clean foundation for future integrations and advanced capabilities.

### Non-goals for the initial release

- A complete LMS with learning modules, content authoring, discussion forums, or attendance management.
- AI-based remote proctoring or biometric identity verification.
- Native iOS or Android applications.
- Adaptive testing or computerized adaptive testing.
- Complex institutional gradebook synchronization.
- Microservices, event streaming, or distributed orchestration without demonstrated need.

## 2. Target users and success

| User | Main tasks | Proposed success measure |
| --- | --- | --- |
| Instructor / assessment author | Create and organize questions, configure and publish quizzes, grade submissions, review performance | Less time spent preparing and administering assessments |
| Learner / test taker | Open an assigned or shared quiz, answer, see save/submission status, receive permitted results | Successful, understandable completion without lost answers |
| Platform administrator | Manage accounts, roles, organization membership, configuration, and access | Secure administration with low operational overhead |
| Training manager / assessment coordinator | Organize cohorts, assign assessments, track completion, compare results | Timely visibility into completion and learning gaps |

Instructor, learner, and administrator roles are required for the initial design. More advanced organization roles depend on the multi-tenant decision.

## 3. Core user journeys

1. **Create and publish:** Sign in → create quiz → add questions → preview → publish.
2. **Complete an assessment:** Open an authorized quiz → answer and save → submit → view permitted results.
3. **Review results:** Open results → inspect scores and submissions → grade written responses if supported → export or analyze.

**Alignment issue:** The third journey currently includes written-response grading, while FR-044 and the release plan put manual grading in P1 / Release 2. Decide whether written grading is required in the MVP, or revise the journey to make that step conditional.

## 4. Priorities

- **P0 — MVP:** Required for a usable initial release.
- **P1 — Next release:** Important after the core workflows are reliable.
- **P2 — Future:** Optional expansion requiring additional validation.

## 5. Functional requirements

### A. Identity, access, and administration

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-001 | Users can authenticate securely. | P0 |
| FR-002 | The platform enforces role-based access for administrators, authors, and learners. | P0 |
| FR-003 | Authors can manage only quizzes and question banks they are authorized to access. | P0 |
| FR-004 | Administrators can manage user accounts, role assignments, and access status. | P0 |
| FR-005 | The platform supports organization and group boundaries when multi-tenant operation is enabled. | P1 |
| FR-006 | Important administrative and assessment-management actions are recorded in an audit trail. | P1 |

### B. Question bank and authoring

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-010 | Authors can create, read, update, archive, and organize questions. | P0 |
| FR-011 | The system supports single-answer multiple choice and true/false questions. | P0 |
| FR-012 | Authors can configure answer options, correct answers, points, and explanatory feedback. | P0 |
| FR-013 | Authors can categorize and search questions by text, category, and tags. | P0 |
| FR-014 | A question is reusable across quizzes without duplicating its identity. | P0 |
| FR-015 | Authors can preview questions and quizzes before publishing. | P0 |
| FR-016 | The system supports multiple-answer selection, short-answer questions, and manual grading for written responses. | P1 |
| FR-017 | The system supports bulk question import/export through a documented format. | P1 |
| FR-018 | The system preserves the question content and scoring rules applicable to an existing attempt, even if the original question changes. | P0 |

**Design constraint:** Question editing must not silently alter completed results. Published quiz configuration and submitted attempts need explicit versioning or immutable snapshots.

### C. Quiz construction and publication

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-020 | Authors can create a quiz with a title, instructions, questions, and scoring rules. | P0 |
| FR-021 | Authors can add questions from the question bank and configure quiz-specific point values where permitted. | P0 |
| FR-022 | Authors can configure time limits, attempt limits, and question/option randomization. | P0 |
| FR-023 | Authors can configure start and end times, including the relevant time zone. | P0 |
| FR-024 | The system distinguishes draft, published, closed, and archived assessments. | P0 |
| FR-025 | Authors can preview an assessment as a learner would experience it. | P0 |
| FR-026 | Authors can configure when learners see scores, correct answers, and feedback. | P0 |
| FR-027 | Authors can copy a quiz to create a new assessment. | P1 |
| FR-028 | The system can select a configured number of random questions from a defined bank or pool. | P1 |

### D. Assessment delivery

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-030 | Learners can access an assessment through an authorized assignment, link, or invitation. | P0 |
| FR-031 | The system validates eligibility, availability, and attempt limits before an attempt starts. | P0 |
| FR-032 | The system records each learner's answers and preserves them across navigation and recoverable interruptions. | P0 |
| FR-033 | Learners can navigate questions and revise answers before submission, subject to quiz settings. | P0 |
| FR-034 | The server enforces assessment deadlines using server-side time and state validation. | P0 |
| FR-035 | Retried submission requests do not cause duplicate scoring or finalization. | P0 |
| FR-036 | Learners receive clear submission confirmation and attempt status. | P0 |
| FR-037 | Browser refreshes and temporary network loss do not silently discard answers already saved by the server. | P0 |
| FR-038 | The platform shows autosave status and distinguishes saved from unsaved answers. | P0 |
| FR-039 | Anonymous or guest participation is supported when explicitly enabled by an authorized author. | P1 |

### E. Scoring and grading

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-040 | The system automatically grades supported objective question types. | P0 |
| FR-041 | The system calculates scores using configured points and grading rules. | P0 |
| FR-042 | Each attempt retains answers, score, timestamps, and completion state. | P0 |
| FR-043 | Learners see only results and feedback permitted by assessment configuration. | P0 |
| FR-044 | Authorized authors can review submissions and manually grade supported written responses. | P1 |
| FR-045 | Authorized authors can correct grading errors with an auditable record of the change. | P1 |
| FR-046 | The system supports score recalculation under controlled rules when an assessment is regraded. | P1 |

### F. Reporting and analytics

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-050 | Learners can view their permitted attempt history and results. | P0 |
| FR-051 | Authors can view participation, completion status, and scores for each quiz. | P0 |
| FR-052 | Authors can inspect an individual submission. | P0 |
| FR-053 | Authorized users can export assessment results in CSV format. | P1 |
| FR-054 | The system reports question-level response distributions and observed correctness rates. | P1 |
| FR-055 | The system supports authorized comparisons across groups or cohorts. | P1 |
| FR-056 | The platform distinguishes unanswered questions, incorrect answers, pending manual grades, and finalized scores. | P0 |

### G. Integrations and extensibility

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-060 | The platform exposes a documented API for supported assessment-management operations. | P1 |
| FR-061 | API access enforces the same authorization rules as the user interface. | P0 |
| FR-062 | Quizzes, questions, attempts, and organizations use stable identifiers. | P0 |
| FR-063 | The platform provides a future path to LMS interoperability, including investigation of QTI import/export and LTI launch/integration requirements. | P2 |
| FR-064 | AI-assisted question generation may be added as an optional authoring feature with human review before publication. | P2 |

**Alignment issue:** The overview calls the MVP “API-ready,” but FR-060 places a documented API in P1. Clarify whether “API-ready” means internal architecture and stable identifiers in P0, or a supported external API in the MVP.

## 6. Non-functional requirements

These are proposed targets, not measured product claims. Confirm the workload, test environment, and contractual expectations before making them release gates.

| ID | Attribute | Proposed criterion |
| --- | --- | --- |
| NFR-001 | Performance | At agreed baseline load, API read operations achieve p95 latency ≤300 ms, excluding external services and large exports. |
| NFR-002 | Interactive response | Initial quiz interface is usable within 2.5 seconds at p75 on the agreed device/network profile. |
| NFR-003 | Concurrency | MVP sustains 100 concurrent active assessment takers in a documented load test without correctness failures. |
| NFR-004 | Reliability | No answers acknowledged as saved are lost under defined failure scenarios. |
| NFR-005 | Submission integrity | Repeated or concurrent submission requests for one attempt produce one finalized result. |
| NFR-006 | Availability | Target 99.5% monthly availability for initial hosted deployment, excluding planned maintenance if contractually defined. |
| NFR-007 | Security | Enforce server-side authorization, secure sessions, input validation, protection against common web vulnerabilities, and secure password handling. |
| NFR-008 | Privacy | Collect necessary personal information only, apply retention rules, and restrict assessment-data access. |
| NFR-009 | Accessibility | Target WCAG 2.2 AA for core learner and author workflows, including keyboard and screen-reader use. |
| NFR-010 | Maintainability | Automated tests cover critical assessment state transitions, grading rules, access controls, and submission idempotency. |
| NFR-011 | Portability | Support documented, reproducible deployment with environment-based configuration. |
| NFR-012 | Observability | Provide structured logs, health checks, error reporting, and operational metrics without unnecessary logging of sensitive answers. |
| NFR-013 | Data protection | Support backups and a documented restore procedure with agreed recovery objectives. |
| NFR-014 | Scalability | Support additional application instances and database optimization without redesigning core domain concepts. |

Load tests should state concurrent users, question count and payload size, autosave frequency, simultaneous submissions, database/history size, device/network profile, error rate, p50/p95/p99 latency, CPU, memory, and database connection use. Include submission bursts and autosave traffic.

## 7. Business rules and assessment integrity

1. **Attempt lifecycle:** Attempts move through defined states such as in progress, submitted, expired, and graded. Reject invalid transitions.
2. **Server-authoritative timing:** The browser displays the timer; the server decides whether a deadline has passed.
3. **Answer persistence:** A save acknowledgement means the answer has been durably recorded according to the persistence contract.
4. **Idempotent finalization:** Retries must not create multiple finalized attempts or apply grading more than once.
5. **Published assessment consistency:** Define whether quiz/question changes apply to future attempts only; do not silently change an attempt already underway.
6. **Scoring transparency:** Define points, grading method, and treatment of unanswered responses before scoring.
7. **Feedback access control:** Release correct answers, explanations, and scores only according to the configured result policy.
8. **Tenant isolation:** If multiple organizations are supported, block access to other organizations' content and results unless explicitly authorized.
9. **Auditability:** Grade changes, quiz publication changes, and relevant administration must be traceable.

## 8. Conceptual domain entities

This is product vocabulary, not a physical database schema.

| Entity | Purpose |
| --- | --- |
| User | Authenticated identity and account status |
| Organization | Optional tenant or administrative boundary |
| Membership | User's role and permissions within an organization |
| Group | Cohort, class, or assigned learner group |
| Question / QuestionVersion | Reusable identity plus immutable content/scoring revisions |
| QuestionBank | Collection of reusable questions |
| Quiz / QuizVersion | Assessment identity and immutable published configuration/composition |
| QuizQuestion | Relationship between a quiz version and selected questions |
| Assignment | Distribution of a quiz to learners or groups |
| Attempt | One learner's execution of an assessment |
| AttemptQuestion | Snapshot of question content, options, order, and scoring used in an attempt |
| Response | Learner answer and save/submission state |
| Grade | Score, grading state, and manual grading information where applicable |
| AuditEvent | Trace of relevant administrative or assessment-management actions |

Keep quiz, assignment, and attempt separate: one quiz may be assigned to several groups, and each assignment may produce many attempts.

## 9. Proposed release scope

| Release | Candidate scope |
| --- | --- |
| Release 1 — Core assessment platform | Authentication and roles; question bank and basic authoring; quiz creation, preview, publication, and scheduling; timed attempts, navigation, autosave, and submission; automatic grading and result visibility; learner history and instructor summaries; basic administration, automated tests, logging, and deployment documentation. |
| Release 2 — Assessment management | Short-answer/essay grading; question import/export; cohorts and group assignments; expanded reporting and question analysis; quiz duplication and random pools; broader API access and audit reporting. |
| Release 3 — Optional extensions | LMS interoperability; AI-assisted authoring; advanced analytics; additional identity/enterprise integrations; proctoring integrations only if validated by user demand and privacy requirements. |

Release boundaries are provisional. If formal academic assessment is the primary use case, manual grading, auditability, identity controls, and some currently deferred capabilities may need to move into Release 1.

## 10. MVP acceptance criteria

### Authoring

- An authorized author creates a question and reuses it in two quizzes.
- A draft quiz can be previewed, published, closed, and archived.
- Publishing or editing does not silently change an assessment already being attempted.

### Assessment delivery

- An eligible learner starts an assessment and navigates its questions.
- Saved answers survive refresh and agreed network interruption scenarios.
- The server enforces time limits, availability windows, and attempt limits.
- Repeated submissions produce one finalized attempt and one consistent score.

### Grading and results

- Objective questions are graded according to configured rules.
- Learners cannot view results or answer keys before release is authorized.
- An instructor can inspect attempts and export results when export is enabled.

### Security and operations

- Cross-role and cross-organization authorization tests pass where applicable.
- The application passes agreed concurrency and latency tests.
- Backup restoration, health checks, error reporting, and deployment procedures are verified.

## 11. Key risks and mitigations

| Risk | Consequence | Mitigation |
| --- | --- | --- |
| Scope grows toward a full LMS | Slower delivery and higher maintenance | Enforce MVP boundaries and prioritize assessment workflows. |
| Lost answers or duplicate submissions | Invalid results and loss of trust | Durable autosave, explicit state transitions, idempotency, and failure testing. |
| Question edits alter historical results | Grading disputes and unreliable results | Immutable question versions and attempt snapshots. |
| Submission bursts degrade performance | Failed or delayed assessments | Load testing, bounded transactions, database tuning, and controlled retries. |
| Answer keys or grades are exposed | Assessment compromise and privacy breach | Server-side access control and negative authorization tests. |
| Proctoring false positives and privacy concerns | Unfair outcomes and compliance risk | Exclude automated proctoring from MVP; require separate validation and policy review. |
| Premature architecture complexity | Higher costs and slower iteration | Start with a modular application; extract services only when justified. |
| Import semantics are unclear | Lost formatting or inconsistent scoring | Define a canonical format and verify import/export round trips. |

## 12. Decisions needed before baseline approval

| Decision | Why it matters | Current proposed default |
| --- | --- | --- |
| First customer and primary use case | Changes workflow, language, roles, and what counts as success | Standalone web app for instructors and learners; validate the actual first segment. |
| Practice vs. formal assessment | Changes identity, audit, timing, grading, reliability, privacy, and acceptance criteria | Objective quizzes first unless formal exams are confirmed as primary. |
| Organization model | Changes ownership, authorization, data boundaries, and reporting | Simple organization model, enabled when needed. |
| Expected scale and hosting | Sets measurable performance and operational targets | One straightforward deployable application and explicit load-test target. |
| Identity and compliance | Drives login, data retention, access controls, and deployment constraints | Secure role-based access; confirm SSO and applicable obligations before implementation. |
| Delivery constraints | Sets scope and release acceptance | Unresolved: deadline, budget, environment, and demo criteria. |
| Written grading in Release 1 | Resolves the journey/priority mismatch | P1 unless formal assessment is the primary case. |
| Meaning of “API-ready” | Resolves the API priority mismatch | Stable domain IDs and authorization in P0; supported documented API can remain P1. |

## Appendix: competitor validation

Before this PRD becomes the basis for detailed architecture or code reuse, inspect the reference repositories for license/reuse restrictions, framework versions, dependency health, data models/migrations, authentication and tenant isolation, assessment state and grading correctness, automated tests/CI, API boundaries, defects, performance bottlenecks, and deployment requirements. Publicly visible README claims are not independent verification.
