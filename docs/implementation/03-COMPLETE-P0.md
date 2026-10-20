# Phase 3: Complete the P0 workflows

These packages can run in parallel after T01, subject to the shared-file rules in
the [plan](README.md#4-integration-and-ownership-rules). Each is a vertical slice.
Dependencies/status live in [BACKLOG.md](BACKLOG.md); exact requirements live in
the [software specification](../SOFTWARE-SPECIFICATION.md).

## C03: Complete author workspace

**Rules:** AUTH-01/02/03; AT-03/04/05.
**Surfaces:** question/bank organization and search, quiz composition/lifecycle,
author routes and their focused tests.

Complete bank/question CRUD, category/tag/text search with pagination, move/archive
and reuse selection. Complete draft revision UX, learner preview, publication
history, explicit question-version update, close/archive controls and stale-editor
conflicts. Explain retained history when archiving and reject invalid transitions.

**Done:** every authoring requirement can be exercised through UI and direct
authorized interfaces; archived content cannot silently enter new selection;
historical attempts survive edits/archives; owned lists/searches do not leak
another author's content. Retain AT-03/04/05 evidence.

**Parallel seam:** own composition/lifecycle files and the quiz editor route
wrapper. D04 owns policy validation/settings files. Agree the settings interface
before edits and integrate it through one route owner. Both packages supply
migrations in coordination with the migration integrator.

**Excluded:** duplicate-quiz command, pool selection, imports, rich media.

## A01: Account administration

**Rules:** IAM-03 plus IAM-01/02; AT-01/02.
**Surfaces:** identity administration adapter/endpoints, admin routes, integrity
records and focused tests.

Build in-app account list, provision, role change and activation/deactivation.
Use a narrowly privileged Keycloak administration identity and expose partial
failure/retry without activating incomplete users. Enforce application-side
revocation promptly and protect the last active administrator.

**Done:** all three roles can be administered through the app; stale tokens do not
preserve revoked access; identity-service failures are visible and retries cannot
duplicate users or accidentally grant privileges; administrator alone still cannot
inspect assessment answers. Retain AT-02 and regression AT-01 evidence.

**Excluded:** credential storage, tenancy, group management, an unrestricted
Keycloak administration proxy or general audit browser.

## D04: Configurable delivery controls

**Decisions:** DEC-09 approved before timed UX completion; existing DEC-01-05 apply.
**Rules:** AUTH-02/04, ATT-01/03, RESULT-01; AT-05/06/09/12.
**Surfaces:** quiz policy validation/settings UI, attempt timing/order enforcement,
assignment eligibility display and their tests.

Expose duration/attempt limits (including explicit unlimited), IANA-zoned start/end
times, independent question/option order flags and all result-release modes.
Wire every setting to immutable publication and attempt snapshots. Resolve
ambiguous schedule input, explain eligibility/remaining attempts and implement the
approved accessible timing behavior.

**Done:** changed settings affect only explicitly new published assignments;
randomized order remains stable on refresh; limits survive concurrent starts;
availability boundaries use server time; close differs correctly from expiry;
release settings cannot leak fields. Verify both independent randomization flags,
including the disabled paths. Retain AT-06/09/12 and relevant preview cases.

**Parallel seam:** own policy files and settings subview; request integration into
C03's quiz editor wrapper. Do not redesign C03's question bank or composition flow.

**Excluded:** random subset pools, late-answer grace, attempt reset/reopening,
per-learner accommodations not approved under DEC-09.

## R02: History and author reporting

**Rules:** RESULT-01/02, IAM-02; AT-12/13.
**Surfaces:** result/history/report queries and projections; learner history and
author reporting/submission routes; indexes required by those reads.

Build paginated learner attempt history, author participation/completion/status/
score summary and finalized submission inspection. Show version and attempt
identity, submitted versus expired, unanswered versus incorrect and withheld
versus released. Use the specification's denominators, not an assumed best attempt.

**Done:** summary/detail/history agree with persisted attempts and grades;
in-progress rows do not count as finalized scores; ownership and release checks
apply to lists, nested IDs and direct calls; empty/loading/error states are usable.
Retain AT-12/13 evidence and representative query-plan/index observations.

**Excluded:** CSV export, cohort comparison, item response-distribution analytics,
manual grading or regrade controls.

## Phase completion checkpoint

Map every P0 row in specification section 10 to implemented UI/interface behavior
and existing test evidence. Mark missing coverage as an explicit package blocker
before hardening begins. Shared test fixtures and generated contracts must match
the integrated result of all four tracks, not one agent's branch.
