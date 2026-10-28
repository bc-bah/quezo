# Phase 3: Complete the P0 workflows

These packages share the T01 prerequisite. The approved execution order is now
separate sequential A01, D04, R02 dispatches under the shared-file rules in
the [plan](README.md#4-integration-and-ownership-rules). Each is a vertical slice.
Dependencies/status live in [BACKLOG.md](BACKLOG.md); exact requirements live in
the [software specification](../SOFTWARE-SPECIFICATION.md).

**Readiness checkpoint, 27 October 2026:** T01 is accepted at merge `df06ccc`
([milestone evidence](BACKLOG.md#t01-milestone-acceptance-23-october-2026));
the current integrated local `dev` baseline is C03 `2eba9eb` (migration head
`0010_author_workspace`). C03 is accepted/done after B.C.'s local app review
and requested commit/merge. A01 is explicitly dispatched; D04/R02 remain `ready`
under the [27 October scoped approvals](../SOFTWARE-SPECIFICATION.md#c03-acceptance-and-phase-3-approvals-27-october-2026).
B.C. owns integration/review/merge; prepare separate explicit dispatches in order
A01, D04, R02 with a single shared-file/contract/migration writer at a time.
Verify exact Keycloak least privileges before privileged A01 implementation.
DEC-09 now approves pre-start timing adjust/off with scoped DEC-02/05 amendments;
implementation/accessibility evidence remains required. Start from this baseline
plus the tracking update, or B.C.'s newer integrated baseline after each merge.
Copy-ready prompts are in
[PHASE-3-HANDOFFS.md](PHASE-3-HANDOFFS.md). No pilot or deployment approval is
implied. The learner return link for a most recent finalized attempt at `354da49`
is partial AT-13 evidence, not full learner-history acceptance.

## C03: Complete author workspace

**State:** accepted/done, 27 October 2026; local `dev` commit `2eba9eb`, head
`0010_author_workspace`. See [case-level acceptance](BACKLOG.md#c03-acceptance-and-next-package-readiness-27-october-2026).
The scope below is retained as the completed package contract, not a redispatch.

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

**Editor seam:** C03's exclusive window is complete. Its composition/lifecycle
files and quiz editor wrapper are integrated. D04 owns policy validation/settings
and may integrate the settings subview through that wrapper during its separate
exclusive window; retain C03 behavior. B.C. serializes migrations/shared edits.

**Excluded:** duplicate-quiz command, pool selection, imports, rich media.

## A01: Account administration

**Rules:** IAM-03 plus IAM-01/02; AT-01/02.
**Surfaces:** identity administration adapter/endpoints, admin routes, integrity
records and focused tests.

Build in-app account list, provision, role change and activation/deactivation.
Use a narrowly privileged Keycloak administration identity and expose partial
failure/retry without activating incomplete users. Enforce application-side
revocation promptly and protect the last active administrator.

**Approval/readiness:** dispatched as the first separate package under B.C.'s
27 October DEC-06 amendments. Dedicated local-realm identity only, for user
provisioning/status/profile and required role mapping. B.C.'s follow-up approval
permits the fine-grained Keycloak user `manage` capability, including the user
deletion/password-reset capabilities that Keycloak does not separate from it;
Quezo must not expose deletion or credential-reset operations. B.C. also approved
`view-users` for account search/profile access, including its transitive
read-only `query-groups` role; group mutation remains excluded. The effective
local Keycloak 26.4.7 mapping was verified before privileged implementation:
`query-users` and `view-users` roles on the dedicated client-credentials service
account, plus a client policy targeting only `quezo-account-admin` with `view`
and `manage` on the `Users` resource type. A client policy is required because a
user policy does not match this caller context. Disabled synthetic create, profile
read/update and exact username search all succeeded. Server-side ignored
secrets; no master/realm/client/group mutation administration, credential
storage, unrestricted proxy, or external provisioning.

**Done:** all three roles can be administered through the app; stale tokens do not
preserve revoked access; identity-service failures are visible and retries cannot
duplicate users or accidentally grant privileges; administrator alone still cannot
inspect assessment answers. Retain AT-02 and regression AT-01 evidence.

**Excluded:** credential storage, tenancy, group management, an unrestricted
Keycloak administration proxy or general audit browser.

## D04: Configurable delivery controls

**Decisions:** DEC-09 approved 27 October; DEC-01-05 apply with the explicit
DEC-02/05 accessible-timing amendments in the specification.
**Rules:** AUTH-02/04, ATT-01/03, RESULT-01; AT-05/06/09/12.
**Surfaces:** quiz policy validation/settings UI, attempt timing/order enforcement,
assignment eligibility display and their tests.

Expose duration/attempt limits (including explicit unlimited), IANA-zoned start/end
times, independent question/option order flags and all result-release modes.
Wire every setting to immutable publication and attempt snapshots. Resolve
ambiguous schedule input, explain eligibility/remaining attempts and implement the
approved accessible timing behavior.

**Approval/readiness:** ready for second separate dispatch, after A01's exclusive
window. Every learner can choose standard, adjusted (at least 10 times the authored
duration supported, ceiling 6048000 seconds), or off before start. Availability
end always gates new starts; it does not cap an explicitly adjusted attempt,
and off removes both deadline bounds. Pin the choice/deadline; preserve existing
attempts. Authored duration bounds remain unchanged. No post-start extension,
reset or reopening; result-release policy is unchanged. This approves a design,
not delivered controls or WCAG conformance.

**Done:** changed settings affect only explicitly new published assignments;
randomized order remains stable on refresh; limits survive concurrent starts;
availability boundaries use server time; close differs correctly from expiry;
release settings cannot leak fields. Verify both independent randomization flags,
including the disabled paths. Retain AT-06/09/12 and relevant preview cases.
Verify standard/adjusted/off choices, server-side bounds, near-availability-end
starts that outlive the schedule, cutoff in every mode, replay/resume preserving
the frozen choice and compatibility with existing attempts. Test unchanged
release filtering and accessible pre-start controls; do not claim AT-14 complete
from design approval or representative controls alone.

**Editor seam:** own policy files/settings subview and integrate through C03's
existing wrapper as the single dispatched writer under B.C. Do not redesign
C03's question bank/composition/lifecycle. Coordinate forward migrations from
the actual post-A01 head.

**Excluded:** random subset pools, late-answer grace, attempt reset/reopening,
per-learner accommodations not approved under DEC-09.

## R02: History and author reporting

**Dispatch baseline:** B.C. confirmed the separate post-D04 R02 window at
`d43d893` / `0012_delivery_controls`, superseding the original C03 baseline
`2eba9eb` / `0010_author_workspace`. This is integration scheduling, not a new
domain dependency. Implementation and focused evidence are recorded in
[DEVELOPMENT.md](../DEVELOPMENT.md#r02-history-and-author-reporting); full AT-13
tracker acceptance remains B.C.'s review decision.

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
