# Phase 3 coding-agent handoffs

**State, 27 October 2026:** C03 accepted and locally integrated into `dev` at
`2eba9eb`, head `0010_author_workspace`. A01 is explicitly dispatched to the
current Copilot session; D04/R02 remain ready for **separate dispatch** in that
order. B.C. owns integration/review/merge and serializes shared-file/contract/
migration windows. The [approval record](../SOFTWARE-SPECIFICATION.md#c03-acceptance-and-phase-3-approvals-27-october-2026)
records scoped DEC-06 and DEC-09/02/05 amendments. Existing latest-finalized-attempt
navigation remains partial AT-13 evidence, not full history/reporting acceptance.

Use the common execution contract and then exactly one package prompt per
isolated session. The [backlog](BACKLOG.md) is authoritative for prerequisites
and status; this file does not assign work or approve decisions.

## Common execution contract

Before any prompt is dispatched, the coordinator must:

1. Assign an implementation owner; B.C. is integration/review/merge owner.
2. Record `active` in the backlog only after making that explicit assignment.
3. Confirm the execution checkout contains C03 `2eba9eb`, T01 `df06ccc` and this
   approval/tracking update; head is `0010_author_workspace` now. For D04/R02,
   record the actual newer integrated baseline/head after the previous package.
4. Assign one shared-file/contract/migration writer for the dispatched package.
   A01, D04 and R02 run sequentially, not automatically; the order is integration
   scheduling, not a new domain dependency. Verify exact A01 privileges before
   privileged implementation; broader rights require B.C.'s approval.

Each assignee must:

- Read [the package definition](03-COMPLETE-P0.md), its backlog row and
  prerequisites, the cited SRS rules/acceptance IDs, and the relevant current
  contracts/tests before editing.
- Confirm actual producer commits, live schemas and migration head in the
  checkout. Stop and report a mismatch; do not invent or duplicate contracts.
- Deliver a vertical slice with real authorization, persistence and browser
  behavior where required. Keep test fixtures from becoming runtime fallbacks.
- Use only synthetic local/test data. Do not provision credentials or external
  resources, deploy, or start a successor package automatically. Any local A01
  setup is explicit and bounded by the recorded approval, never implicit.
- Coordinate app/router registration, generated API contracts, shared fixtures,
  manifests/CI and migration revisions with B.C. C03's composition/lifecycle
  and wrapper are integrated; its exclusive window is finished. D04 owns policy
  validation/settings and wrapper integration during its separate window;
  preserve C03 behavior. Never branch migrations from the obsolete pre-C03 head.
- Return the format in [AGENT-HANDOFF.md](AGENT-HANDOFF.md#3-handoff-format),
  including a criterion-by-criterion result for every assigned acceptance ID.
  Distinguish implemented, tested, manually observed, partial and unverified.
  Include exact commands/environment, migration and clean/upgrade evidence,
  changed contracts, integration commit and remaining gaps. Do not self-accept
  the package or update its status to `done`.

An agent may do read-only preparation while waiting on a gate, but must stop
before implementation if the package is unassigned, a prerequisite is absent,
or a required decision is held. Do not create a partial subtask or claim the
whole package complete without a separate tracker entry and explicit approval.

## C03 historical dispatch prompt: Complete author workspace

**Dispatch state:** completed/accepted, not for redispatch. B.C. granted C03 the
sole shared editor/assembly/contract/migration window while D04 was unassigned.
Historical input baseline `354da49` / `0009_finalization` below is superseded by
output `2eba9eb` / `0010_author_workspace`; see the
[acceptance record](BACKLOG.md#c03-acceptance-and-next-package-readiness-27-october-2026).

```text
Implement Quezo work item C03: Complete author workspace.

Read:
- docs/implementation/BACKLOG.md: C03 row and this Phase 3 baseline record.
- docs/implementation/03-COMPLETE-P0.md: C03 scope, done criteria, seam and exclusions.
- docs/SOFTWARE-SPECIFICATION.md: AUTH-01/02/03 and AT-03/04/05.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: relevant authoring/module boundaries.
- docs/DEVELOPMENT.md and current package scripts for setup and validation.

Approved decisions: DEC-01 through DEC-07 as recorded in the specification.
Do not infer new authoring behavior or change the approved scope.
Integrated prerequisite: T01 merge df06ccc; required checkout baseline
354da49 (or a coordinator-recorded newer integrated baseline), migration head
0009_finalization. Verify these and the actual contracts before implementation.
Permitted surfaces: question/bank organization and search, quiz composition and
lifecycle, author routes and focused tests. C03 owns composition/lifecycle files
and the quiz editor route wrapper. Agree a single writer for shared editor/
assembly changes with D04's owner before editing those surfaces.
Shared-file owner: C03 implementation session; B.C. integration/review owner.
Historical exclusive window; D04 was unassigned.

Complete the C03 package: bank/question CRUD and category/tag/text search with
pagination; move/archive and reuse selection; draft revision UX and learner
preview; publication history, explicit question-version update, close/archive,
and stale-editor conflict behavior. Preserve history and prevent archived
content from silently entering new selection. Enforce ownership on lists,
search, nested IDs and direct authorized calls.

Acceptance: provide focused, real-auth/persistence/UI evidence for the C03
scope of AT-03/04/05. Identify which cases are inherited from T01, newly
covered, still partial, or outside this package; do not claim those full AT IDs
complete unless every catalogue scenario is evidenced. Verify another author's
content cannot be discovered and historical attempts/publications remain
unchanged by edits or archives.

Excluded: duplicate-quiz command, pool selection, imports, rich media, and
policy controls owned by D04. Coordinate any migration with the integration
owner; create it from the actual current head, never rewrite an applied revision.
Run focused tests during work and the existing relevant application/browser
checks before handoff. Regenerate/check generated contracts after API changes.
Stop after C03 and return AGENT-HANDOFF.md section 3; no automatic commit/PR,
successor dispatch or tracker acceptance.
```

## A01 dispatch prompt: Account administration

**Dispatch state:** A01 explicitly dispatched 27 October to the current Copilot
session; B.C. owns integration/review/merge. B.C.'s scoped DEC-06 approval and
follow-up amendment are recorded in the software specification and backlog.
Exact effective permission verification remains a mandatory entry step before
privileged implementation.

```text
Implement Quezo work item A01: Account administration.

Read:
- docs/implementation/BACKLOG.md: A01 row and Phase 3 baseline record.
- docs/implementation/03-COMPLETE-P0.md: A01 scope, done criteria and exclusions.
- docs/SOFTWARE-SPECIFICATION.md: IAM-01/02/03 and AT-01/02, including the
  27 October scoped DEC-06 approval.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: identity and authorization seams.
- docs/DEVELOPMENT.md and current package scripts for setup and validation.

Approved boundary: dedicated local-realm identity for user provisioning,
status/profile and required role mapping. B.C.'s 27 October follow-up approves
the fine-grained Keycloak user `manage` capability, including user deletion and
password-reset capability that Keycloak does not separate from `manage`; Quezo
must not expose deletion or credential-reset operations. B.C. further approved
`view-users` for account search/profile access, including its transitive
read-only `query-groups` role; group mutation remains excluded. Verified on
local Keycloak 26.4.7 before privileged implementation: `query-users` and
`view-users` are scoped to the dedicated `quezo-account-admin` service account,
and a client policy targeting only that client grants `view` and `manage` on the
`Users` resource type. Use a client policy, not a user policy, for this
client-credentials caller. No master/realm/client/group mutation administration,
credential storage, unrestricted proxy or external provisioning. Service
secrets stay server-side in ignored configuration, never browser/logs/source.
Application authorization remains authoritative. Local setup is explicit; do
not provision credentials outside it.
Integrated prerequisite: T01 merge df06ccc; required checkout baseline C03
2eba9eb, migration head 0010_author_workspace, plus this approval/tracking update
(or a B.C.-recorded newer integrated baseline). Verify all before edits.
Permitted surfaces: identity administration adapter/endpoints, admin routes,
integrity records and focused tests. B.C. owns integration/review/merge; the
explicitly dispatched A01 session is sole shared-file/contract/migration writer.

Build in-app account list, provision, role change and activation/deactivation.
Make partial identity-service failure visible and retryable without activating
incomplete users, duplicating accounts or accidentally granting privileges.
Enforce application-side revocation promptly and protect the last active
administrator. Keep assessment answers inaccessible to administrators.

Acceptance: provide AT-02 coverage for all three roles, safe retry/partial
failure, last-active-administrator protection and authorization; provide
regression evidence for the applicable AT-01 cases, including stale-token
revocation and denied direct calls. Do not claim full AT-01 or AT-02 from a
subset of scenarios.

Excluded: credential storage, tenancy, group management, an unrestricted
Keycloak administration proxy, and a general audit browser. Use synthetic
accounts only. Coordinate any migration and shared app/route changes. Run
focused tests plus relevant identity, contract and browser checks. Stop after
A01 and return AGENT-HANDOFF.md section 3; no automatic commit/PR, successor
dispatch or tracker acceptance.
```

## D04 dispatch prompt: Configurable delivery controls

**Dispatch state:** ready for second separate explicit dispatch after A01's
exclusive window/integration. DEC-09 and scoped DEC-02/05 timing amendments
approved 27 October; implementation and accessibility verification still pending.

```text
Implement Quezo work item D04: Configurable delivery controls.

Read:
- docs/implementation/BACKLOG.md: D04 row and Phase 3 baseline record.
- docs/implementation/03-COMPLETE-P0.md: D04 scope, done criteria and seam.
- docs/SOFTWARE-SPECIFICATION.md: AUTH-02/04, ATT-01/03, RESULT-01,
  AT-05/06/09/12 and the approved DEC-09 record.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: policy and attempt boundaries.
- docs/DEVELOPMENT.md and current package scripts for setup and validation.

Approved timing contract (27 October DEC-09/02/05): before start, learner chooses
standard, adjusted duration supporting at least 10 times the authored duration
(60-6048000 seconds), or timing off. Authored duration stays 60-604800 seconds.
Availability end always cuts off new starts. Standard deadlines retain the
earlier present bound; adjusted deadlines use start plus chosen duration without
the availability-end cap; off removes both deadline bounds. Freeze explicit
choice/effective deadline on the attempt. No active/history mutation or post-start
extension. Release rules remain pinned and require finalization; adjusted timing
does not change authored after-availability-end release schedules. Do not infer
additional behavior or claim WCAG conformance from design approval.
Integrated prerequisite: T01 merge df06ccc and C03 2eba9eb, plus current approval/
tracking update. Initial head is 0010_author_workspace; before D04, B.C. records
the actual post-A01 integrated baseline/migration head. Verify current publication,
assignment and attempt snapshots before editing; do not assume an old head.
Permitted surfaces: policy validation/settings UI, attempt timing/order
enforcement, assignment eligibility display and focused tests. D04 owns policy
validation/settings files and its settings subview; integrate through C03's
existing wrapper, preserving composition/lifecycle behavior.
Shared-file owner: explicitly dispatched D04 session; B.C. integration/review/
merge owner serializes the exclusive editor/assembly/contract/migration window.

Expose duration/attempt limits (including explicit unlimited), IANA-zoned
availability start/end, independent question/option order flags and each result
release mode. Wire validated settings to immutable publication and attempt
snapshots; resolve ambiguous schedules explicitly; explain eligibility and
remaining attempts; implement only the approved accessible timing behavior.
Keep authoritative boundary and expiry enforcement server-side.

Acceptance: provide case-level evidence for the D04 scope of AT-05/06/09/12:
settings change only explicitly new published assignments; both independent
randomization flags work, are independently disabled and remain stable on
refresh; limits survive concurrent starts; schedule/deadline boundaries use
server time; close differs from expiry; release policy does not leak protected
fields. Test default/adjusted/off, invalid server-side choices/bounds, near-end
starts that outlive availability, off without either deadline, start cutoff in
every mode, choice preservation on concurrent start/replay/resume, existing
snapshot compatibility and unchanged release filtering. Include keyboard/
assistive-technology timing controls and preview cases; distinguish prior
C03/R01/T01 evidence from new coverage. Do not claim AT-14 or a full catalogue
ID complete if its other scenarios are
not evidenced.

Excluded: random subset pools, late-answer grace, attempt reset/reopening and
unapproved per-learner accommodations. Coordinate migrations and shared route
assembly; never rewrite an applied revision. Run focused tests and relevant
browser, migration and contract checks. Stop after D04 and return
AGENT-HANDOFF.md section 3; no automatic commit/PR, successor dispatch or
tracker acceptance.
```

## R02 dispatch prompt: History and author reporting

**Dispatch state:** ready for third separate explicit dispatch after D04's
exclusive window/integration; implementation owner assigned on dispatch.
The existing learner link opens the most recent finalized attempt only; it is
not full paginated attempt history or author reporting.

```text
Implement Quezo work item R02: History and author reporting.

Read:
- docs/implementation/BACKLOG.md: R02 row and Phase 3 baseline/partial evidence.
- docs/implementation/03-COMPLETE-P0.md: R02 scope, done criteria and exclusions.
- docs/SOFTWARE-SPECIFICATION.md: RESULT-01/02, IAM-02 and AT-12/13.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: results/reporting boundaries.
- docs/DEVELOPMENT.md and current package scripts for setup and validation.

Approved decisions: DEC-01 through DEC-07 as recorded in the specification;
do not expand result disclosure or reporting scope.
Integrated prerequisite: T01 merge df06ccc and C03 2eba9eb plus this approval/
tracking update. Initial head is 0010_author_workspace; B.C. records the actual
post-D04 integrated baseline/head before separate R02 dispatch. Verify current
Grade, timing-adjusted attempt, publication and release-policy contracts before
implementation; do not assume a pre-D04 schema.
Permitted surfaces: result/history/report queries and projections; learner
history and author reporting/submission routes; narrowly justified indexes and
their focused tests. Coordinate router registration, generated contracts,
fixtures and any migration with the integration owner.
Shared-file owner: explicitly dispatched R02 session; B.C. integration/review/
merge owner serializes shared contract/router/migration edits.

Build paginated learner attempt history, author participation/completion/status/
score summaries and finalized submission inspection. Show publication-version
and attempt identity, submitted versus expired, unanswered versus incorrect,
and withheld versus released. Use the specification's denominators; do not
substitute a best-attempt score. Reuse the R01 disclosure rules and enforce
ownership/release checks on lists, nested IDs and direct calls.

Acceptance: cover the R02 scope of AT-12/13 with evidence that summary, detail
and history agree with persisted attempts and Grades; in-progress rows do not
count as finalized scores; release filtering applies to each projection; another
author cannot access these records; empty/loading/error states are usable.
Test direct-call and identifier-guessing paths as well as browser navigation.
The existing latest-completed-attempt return link is only prior partial evidence,
not acceptance of full AT-13.

Excluded: CSV export, cohort comparison, item response-distribution analytics,
manual grading and regrade controls. Coordinate query/index/migration changes
with the integration owner, and capture representative query-plan/index
observations. Run focused tests plus relevant contract and browser checks. Stop
after R02 and return AGENT-HANDOFF.md section 3; no automatic commit/PR,
successor dispatch or tracker acceptance.
```
