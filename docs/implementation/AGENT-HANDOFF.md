# Coding-agent handoff

Use this document when assigning or completing a package from
[BACKLOG.md](BACKLOG.md). It is an on-demand execution guide, not an instruction
to launch agents or implement the entire backlog.

## 1. Coordinator preparation

Select a dependency-ready package; verify its decisions and integrated input
contracts, then assign its owner and permitted file surfaces. Use a separate
worktree/session for each concurrent package. Agree shared-file edits with the
integration owner before dispatch, particularly quiz settings/composition,
migrations, generated contracts, lockfiles and root application wiring.

Provide the agent with:

```text
Implement Quezo work item <ID>: <title>.

Read:
- docs/implementation/BACKLOG.md: this row and all listed prerequisites.
- docs/implementation/<phase-file>.md: this package only.
- docs/SOFTWARE-SPECIFICATION.md: <named rules and acceptance IDs>.
- docs/PROTOTYPE-HIGH-LEVEL-ARCHITECTURE.md: <relevant sections>.
- docs/DEVELOPMENT.md and the current manifest scripts for setup/checks.

Approved decisions: <DEC IDs, approval references and any amendments>.
Integrated prerequisites: <commit/PR references>.
Permitted surfaces: <paths>; shared-file owner: <name/contact>.
Required input contracts: <schema/model/endpoint references>.

Deliver the package's complete acceptance criteria and relevant tests.
Use real auth/persistence/browser integration wherever its criteria require it.
Preserve all excluded scope and the agreed synthetic-data boundary.
Escalate incompatible contracts, unapproved behavior, or out-of-scope file needs.

Stop after this package and return the handoff format below.
Do not start successors, create external resources, or deploy without a separate
explicit assignment. PR/commit instructions, if any: <coordinator supplies>.
```

Replace every placeholder before dispatch. An unavailable approval or prerequisite
is a blocker to resolve, not something to ask the agent to invent. A consumer may
use schema-validated fixtures for development, but its final acceptance still
requires the actual producer integration.

## 2. Assignee execution

1. Confirm the live tracker, approved decisions, workspace state and input
   contracts match the assignment. Report any mismatch before changing behavior.
2. Implement only the assigned vertical slice. Keep domain rules inside the
   owning module; update the server schema and regenerate clients when interfaces
   change. Coordinate shared files and migration ordering.
3. Run the existing relevant checks plus the acceptance tests the package adds.
   Record commands, environment and outcomes; distinguish automated results,
   manual observations and unverified requirements.
4. Review every assigned acceptance ID. A failed/unverified item remains open.
   Return implementation and evidence to the coordinator for integration.

Use the repository's current scripts rather than installing a second toolchain
or inventing test commands that do not exist. Add missing feature tests/tooling
only as the assigned package calls for them. Treat authentication or database
substitutes as test fixtures, never silent runtime fallbacks.

## 3. Handoff format

```text
Work item: <ID>
State: ready for review | blocked
Changes: <behavior and relevant file paths>
Requirement coverage: <SRS rules and PRD IDs>
Acceptance: <each assigned AT ID, scenarios covered, result/evidence link>
Checks: <exact commands, environment and outcomes>
Contracts: <new/changed endpoints, schemas, generated-client updates>
Data: <migration IDs, clean/upgrade results, recovery implications>
Integration: <commit/PR, prerequisites used, shared-file coordination>
Known gaps: <unverified criteria, failures, decisions needed; "none" only if true>
Successor handoff: <what dependent packages can now rely on>
```

The agent reports readiness for review; it does not declare user acceptance or
pilot readiness. The coordinator records integration and updates the tracker.
Retain evidence in repository tests/runbooks or approved CI/PR artifacts; keep
raw logs, credentials and assessment payloads out of committed documents.
