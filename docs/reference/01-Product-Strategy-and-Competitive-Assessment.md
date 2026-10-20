# Product Strategy & Competitive Assessment

**Audience:** Product, Design, Development leads  
**Status:** Proposed direction; competitive evidence needs validation.

## Executive recommendation

Build a focused assessment workspace that pairs the quick, uncomplicated experience of a standalone quiz app with a small set of assessment-management capabilities associated with higher-education LMS products. Keep the product assessment-first and avoid taking on the scope of a full LMS.

The product opportunity is a fast, self-contained way to create, deliver, grade, and analyze quizzes. The initial release should prove the complete assessment lifecycle: author a quiz, publish it, let an eligible learner complete it, preserve the attempt, score it, and show only the results the author has allowed.

## Problem and product position

Lightweight quiz apps often make it easy to take a quiz but provide limited instructor workflow, question reuse, controlled delivery, grading, or cohort reporting. Full LMS products offer mature assessment controls but bring course delivery, content management, communications, and other capabilities that may be unnecessary for teams whose primary need is assessment.

**Proposed position:** A fast, self-contained assessment workspace for creating, delivering, grading, and analyzing quizzes without requiring a full learning management system.

Potential users include individual instructors, training teams, certification programs, and self-assessment users. The initial customer and whether the first use case is low-stakes practice or formal assessment are still open decisions.

## Competitive landscape

| Reference category | Examples in the notes | Lesson to borrow | Boundary to preserve |
| --- | --- | --- | --- |
| Lightweight quiz and trivia apps | Sheet Best-powered quiz app; Quiz Master — web | Fast start, simple navigation, category/difficulty selection, clear results | Trivia interactions do not supply recurring assessment administration, cohort workflows, or grading operations. |
| Standalone assessment-management platforms | BrainCheck; Smart Quiz System; TestingPlatform | Authoring and administration, controlled attempts, roles, scheduling, randomization, and reporting | Advertised features need code review; reproducing every enterprise or proctoring feature would expand scope. |
| Learning and academic assessment platforms | Mindigo; HEIG-Quiz | Learner progress and academic evaluation workflows | Broader learning scope may add complexity beyond the product's assessment focus. |
| Mature LMS benchmarks | Canvas LMS / New Quizzes; Blackboard Learn | Question banks, assessment settings, grading, accommodations, and reporting | Use as capability benchmarks, not as architecture or feature-completeness targets. |

## Seven GitHub reference projects

The notes describe these repositories using their public-facing documentation and feature claims. Treat each row as a research lead, not a verified product assessment.

| Project | Contribution described in the notes | Potential learning | Validation needed |
| --- | --- | --- | --- |
| BrainCheck | MCQ assessment, admin CRUD, timers, score history | Minimal assessment lifecycle, modular routes, containerized deployment | Inspect license, data model, auth, scoring, tests, and deployment. Its documented four-option MCQ model is narrow. |
| Quiz Master — web | React, Vite, TypeScript trivia experience | Fast onboarding, categories, difficulty selection, result sharing, modern client | Review as a participant UX reference; it does not cover full instructor administration. |
| Face and Sound Detection Quiz | Online testing with automated monitoring | Possible future exam-integrity extension | Review separately. Browser detection is not proof of cheating; privacy, consent, false positives, and accessibility need dedicated policy and validation. |
| TestingPlatform | General testing platform | Possible assessment workflow and test organization patterns | Exact strengths and implementation quality are not established in the notes. Inspect repository and tests. |
| Mindigo | Learning and exam-preparation platform | Progress, mock exams, learning journeys, analytics | Identify which elements are assessment-specific and avoid importing all-in-one learning scope. |
| HEIG-Quiz | Academic evaluation platform | Academic assessment workflows and instructor/learner needs | Verify question types, grading, integrations, operational maturity, and license. |
| Smart Quiz System | Django REST + React assessment management | Multi-tenant roles, scheduling, randomization, manual grading, reporting | Verify claims in code. Proctoring, subscription, and enterprise capabilities may carry substantial product and maintenance cost. |

### Evidence quality and next validation

The material does not include stable repository URLs, review dates, license findings, or code-inspection results for every project. Before using the analysis to justify implementation or copying code, record the canonical repository URL, license and reuse restrictions, project activity, framework/dependency health, data model, access-control model, test coverage, deployment needs, and any relevant defects. The proposed high-value code-review targets are BrainCheck, Smart Quiz System, and HEIG-Quiz; the trivia app is primarily a UX reference, and the proctoring project is a separate future-research lead.

Canvas and Blackboard notes cite their capabilities generally but do not preserve detailed source links in the supplied text. Verify current product documentation before making capability comparisons outside this internal draft.

## Capability choices

| Adopt for the first release | Consider after core workflow is reliable | Defer until demand and constraints justify it |
| --- | --- | --- |
| Reusable questions; quiz authoring; timed attempts; automatic scoring; result visibility controls; user roles; straightforward administration; reliable save, submit, and result recording | Organization/group grouping; question banks and pools; random question selection; reusable templates; written-response grading; cohort reporting; imports/exports | AI proctoring; facial/sound analysis; complex subscription tiers; real-time collaborative authoring; full LMS features; microservices introduced only for anticipated scale |

Question reuse needs a robust domain model even if the product scope stays small: a question should be reusable, while an attempt must preserve the question content and scoring rules that the learner actually saw.

## Product principles

1. **Assessment-first:** Create and publish a quiz without first requiring courses, modules, a syllabus, or a gradebook.
2. **Reuse questions by default:** Keep question identity separate from each quiz's use of that question.
3. **Simple defaults, optional controls:** Make the basic workflow short; expose time limits, attempt limits, randomization, availability windows, and feedback policies as configuration.
4. **Reliable execution and grading:** Treat answer persistence, submission, scoring, and result recording as core product behavior, including recoverable interruptions.
5. **Actionable reporting:** Show participation, completion, scores, question response patterns, and learning gaps where the user is authorized to see them.
6. **Simple deployment, clear domain boundaries:** Start with a straightforward deployable application and separate domain responsibilities without assuming distributed services.

## Decisions for Product review

- Who is the first customer: an individual instructor, an educational institution, a corporate training organization, an independent learner, or another group?
- Is the primary use case low-stakes practice or formal examination? This changes identity, audit, grading, timing, reliability, and privacy requirements.
- Is this an internal tool, commercial SaaS product, or open-source project?
- Is multi-organization operation required at launch, or should the product start with an individual/single-organization ownership model?
- Which single user journey is the first release meant to prove?

Resolve these questions before treating the feature list or the architecture recommendation as binding.
