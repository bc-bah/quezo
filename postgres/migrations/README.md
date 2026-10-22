# Database migrations

F01 uses Alembic 1.20.0, SQLAlchemy Core 2.1.5 (no ORM), Psycopg 3.3.6 and
psycopg-pool 3.3.3, locked by uv. See [development setup](../../docs/DEVELOPMENT.md)
for credentials, bootstrap and isolated tests. B.C. owns migration ordering and
review under the approved G00/DEC-07 baseline.

## Baseline and revision chain

The pre-F01 scaffold had **no migrations, schema or migration version record**.
Its Alembic baseline is `base`, not a fictional deployed revision.

| Revision | Parent | Change |
| --- | --- | --- |
| `0001_application_schema` | `base` | Revoke public schema access; create migration-owned `quezo` namespace |
| `0002_runtime_grants` | `0001_application_schema` | Restrict database access, grant runtime schema usage and future table/sequence DML privileges; remove default public function execution |
| `0003_web_sessions` | `0002_runtime_grants` | Create isolated `quezo_session` tables and explicit DML grants to `quezo_web` only |
| `0004_identity` | `0003_web_sessions` | Create backend accounts, unique issuer/subject mappings and current role assignments; no seeded grants |
| `0005_questions` | `0004_identity` | Owned banks/questions, immutable objective revisions, content checks and restricted version privileges |
| `0006_quizzes` | `0005_questions` | Revisioned quiz drafts, immutable publications/ordered question snapshots, retained command acknowledgements and publication events |
| `0007_attempt_start` | `0006_quizzes` | Unique pinned assignments, numbered attempts, frozen private/presentation snapshots and retained start command mappings |

Only `public.alembic_version` records migration state. C01 adds question tables;
C02 adds quiz publication, acknowledgement and publication-event tables, but no
assignment, attempt, grade or seed tables in that revision. D01 adds assignment
and attempt tables only, with no response, grade or submission implementation. F03 adds sessions
and single-use login transactions in `quezo_session`. Upcoming packages
provide their own reviewed schema and section 6 constraints. Default runtime
grants apply only to tables/sequences created **by `quezo_migrator` in `quezo`**;
session storage must not use that schema or those grants.

The real prior-revision upgrade is `base -> 0001_application_schema`, disconnect,
then `0001_application_schema -> head`. Tests verify runtime schema
access is absent before the second revision and present afterwards, as well as
a separate clean `base -> head` path and repeat `head` execution.
F03 also tests the actual integrated prior head `0002_runtime_grants -> 0003_web_sessions`.
Applied F01 revisions are unchanged.
I01 additionally tests `0003_web_sessions -> 0004_identity`, preserving a stored
F03 session, repeat-head execution, constraint/privilege enforcement and failure
rollback to the actual prior revision. Applied F01/F03 migrations are unchanged.

### D01 assignment and attempt storage

`0007_attempt_start` is the single head, following actual integrated C02
`0006_quizzes`. No applied revision changes. `assignments` uniquely pins
`(learner_id, version_id)` and has an immutable quiz/version relationship.
No allowance counter is resettable: successful committed attempt rows consume
allowance; finalized and expired rows count too. `attempts` has a unique
assignment/number and a partial unique index permitting one `in_progress` row.
Composite foreign keys carry assignment/learner/version ownership through
attempts, question snapshots and the command ledger.

Attempt metadata (publication, title, instructions, points, policy, start and
deadline) is frozen. `attempt_questions` stores an exact private C02 question
JSON plus separately persisted presented options/position and its own UUID.
Triggers validate the snapshot against its publication, all options as a complete
permutation, nonrandomized order, effective points, exact deadline and dense
complete question coverage. Deferred completeness requires a retained start
command before commit. Sealed snapshots cannot gain questions. Immutable
assignments/questions/commands reject UPDATE/DELETE; attempts reject deletion,
metadata mutation and reopening a finalized state. Runtime receives only
column-level `UPDATE(id)` on assignments so PostgreSQL permits `FOR UPDATE`;
the immutable trigger still rejects even a no-op update. `quezo_web` has no
access to any D01 table.

Starts lock the owned assignment, re-resolve live identity, authorize and check
the scoped ledger. New commands lock an existing active attempt or take a quiz
share lock before new admission; the database wall clock is read after waits.
Future close operations must retain the quiz-row lock convention. Future
save/finalization operations lock the parent attempt and must not acquire an
assignment/quiz lock after that lock (avoid reversing start's order).
The command primary key is actor/assignment/operation/request UUID; its SHA-256
fingerprint includes those fields and the normalized empty payload. The stored
attempt ID is the acknowledgement, retained indefinitely. No automatic retry.

`test_attempt_migrations.py` covers actual `0006_quizzes -> head` preserving
published history, repeat head, failed-upgrade rollback, private table
privileges and snapshot/relationship constraints. F01's retained migration
tests cover clean `base -> head`. A failed upgrade rolls back DDL and ledger;
after application use a reviewed forward correction. Preserve assignments,
attempts, questions and command relationships together during recovery.
Response storage is D02; finalization timestamps/grade/expiry reconciliation
and the required forward extension of the metadata trigger are D03.
Reserved `finalized`/`expired` states are exercised only by controlled database
fixtures in D01; no runtime finalization or fake grade is provided.

### C02 quiz publication storage

`0006_quizzes` has parent `0005_questions` (D01 now follows it). `quizzes` stores the
owned mutable draft, separate monotonic revision, state and last published UUID.
Composition/policy JSON retains independent validated fields, not a preset flag.
`quiz_versions` freezes title, instructions, policy, positive possible total and
publication time. `quiz_questions` stores ordered exact C01 snapshots, overrides
and effective points. Composite foreign keys enforce author ownership and exact
question/version nesting; unique constraints reject duplicate identities/positions.
An insert trigger verifies copied content against the owned immutable C01 version.
Deferred checks require 1-200 densely ordered items, matching total and a
publication event before commit. Sealed versions cannot receive additional items.

`quiz_publication_commands` is unique by actor, quiz, operation and request UUID.
It stores the canonical fingerprint and stable acknowledgement indefinitely;
there is no automatic retention cleanup. `quiz_publication_events` records
publication metadata only, including distinct command and HTTP correlation UUIDs
and a foreign key to the retained command. Runtime UPDATE/DELETE grants are revoked on all four
publication tables and triggers also forbid owner-level mutation.
`quezo_web` has no access to any of these tables.

All draft mutations and publish lock the owning quiz first. Authority is resolved
inside the bounded transaction; ownership precedes ledger replay, which precedes
fresh-command revision/state validation. Publication rows, command acknowledgement,
event and quiz pointer commit together before HTTP success. A rollback leaves
no partial publication or acknowledgement.

`test_quiz_migrations.py` covers the actual `0005_questions -> head` upgrade,
preserved question rows, repeat head, failed-upgrade rollback, SQL policy bounds,
immutable publication rows and incomplete-publication rejection. Retained F01
tests cover clean `base -> head`. An unapplied failure rolls back DDL and ledger.
After application, use a reviewed forward migration; recovery must preserve
publication/acknowledgement/question relationships. This is not backup acceptance.

### C01 question storage

`0005_questions` has parent `0004_identity` (C02 now follows it). Applied foundation
revisions are unchanged. `question_banks` references its owning account.
`questions` has a stable UUID, bank/owner composite foreign key, current revision
and reserved archive marker. Bank/question archive commands and movement remain
C03 work; new selections exclude archived banks/questions.

`question_versions` stores its UUID, question UUID, unique positive revision,
type, literal prompt, ordered JSONB options (`id`, `text` only), correct option
UUID, integer default points, feedback and UTC creation time. A deferred composite
foreign key from `(questions.id, questions.revision)` requires the current
revision to exist at commit. Creation and revision insertion occur in one
transaction; edits lock the question, compare the expected revision, insert
the new version and advance the pointer before committing.

Immutable SQL validation functions/check constraints enforce text bounds,
nonblank required text, option shape/count/unique UUIDs/key membership, exact
`True`/`False` semantic choices and 0-10,000 points. The version UPDATE/DELETE
grants are revoked from `quezo_runtime`; a trigger also rejects mutation by the
migration owner. JSONB options are part of that immutable row, not mutable shared
option records. `quezo_web` has no privileges on any question table/function.
Owner/bank indexes support bounded stable lists.

`test_question_migrations.py` proves the actual `0004_identity -> head` upgrade
preserves an existing account, roles and web session; repeat-head is safe.
It exercises failed DDL rollback to `0004_identity`, SQL constraint violations,
immutable versions, relationship integrity and web-role denial. The retained
foundation suite independently covers clean `base -> head`.

An unapplied failure rolls back DDL and the ledger together. No destructive
downgrade or runtime version correction is provided. After integration, correct
content by appending a revision; correct schema with a reviewed forward migration.
Deleting/restoring versions can invalidate later pinned references, so recovery
must preserve the whole relational chain. This is not backup/restore acceptance.

### I01 identity storage

All three new tables are in `quezo`, owned by `quezo_migrator` and covered by the
existing restricted backend DML grants. No bootstrap role or default-grant change
is needed. `quezo_web` cannot read or write identity tables; `quezo_runtime` still
cannot access F03 session secrets.

`accounts` has the application UUID and active/disabled status (default disabled).
`identity_mappings` has a unique `(issuer, subject)` primary key, a unique
account foreign key and an active flag (default false). `account_roles` has one
row per account/administrator-author-learner pair, constrained by foreign key,
role check and composite primary key. There are no passwords, token role
snapshots, emails or session fields. Empty/combined roles are valid.

Migration does not grant anyone access. Use the explicit synthetic identity
provisioner only after a successful upgrade. An unapplied failure rolls back all
identity DDL and the revision record; an applied revision is forward-only.
Restoring an old database can restore revoked roles/status/mappings, so recovery
must review and reapply revocations before exposing traffic. This is not a
backup/recovery acceptance claim. See the [identity runbook](../../infra/keycloak/README.md).

## Execution and identities

Bootstrap is an explicit local administrator action (`postgres/bootstrap/roles.sql`).
It creates three distinct restricted login roles, makes `quezo_migrator` the database
owner and revokes public database/schema access. None is a superuser,
role creator, database creator, replication user or RLS bypass user. The bootstrap
identity is never supplied to FastAPI or Alembic.

Set `QUEZO_MIGRATION_URL` with user `quezo_migrator`, explicit host and database.
From the repository root:

```powershell
uv run --directory postgres --locked alembic heads
uv run --directory postgres --locked alembic history
uv run --directory postgres --locked alembic upgrade head
uv run --directory postgres --locked alembic current
```

`npm run db:upgrade` wraps the upgrade command. Migration credentials must be
available only in this command's environment, not the application environment.
There is no URL in `alembic.ini`, no offline SQL mode and no automatic migration
at application startup. Each run verifies the migration role has no cluster
administration privileges and takes a transaction-scoped PostgreSQL advisory
lock. A competing migration fails explicitly rather than racing the version
table. Connection, lock and statement waits are bounded (5s, 5s and 60s).

Every pending revision and its version record commit in one PostgreSQL transaction.
An error rolls back DDL and the version record. No autocommit blocks, concurrent
index creation or transaction-breaking commands may be added without a reviewed
change to this contract. `quezo_runtime` can connect and perform DML in `quezo`,
but cannot create schemas/tables/temp tables, truncate tables, assume the migration
role, create roles or read/write `public.alembic_version`.

### F03 session role and existing-baseline upgrade

Fresh bootstrap additionally requires distinct `QUEZO_WEB_PASSWORD` (Compose test
service: `QUEZO_TEST_WEB_PASSWORD`). `quezo_web` has CONNECT, USAGE on
`quezo_session` and SELECT/INSERT/UPDATE/DELETE on its two named tables only.
It has no assessment/public schema access, CREATE, TEMP, TRUNCATE, migration
ledger access or role memberships. `quezo_runtime` cannot access session secrets.
There are **no default web grants**; future session objects require explicit
review. Existing default backend grants remain scoped to `quezo`, never sessions.

An already bootstrapped F01 database needs a narrow, explicit administrator step
before upgrading. Do not rerun the full fresh bootstrap or reset volumes.
In a local administrator `psql` session, with the new distinct
`QUEZO_WEB_PASSWORD` exported to that process:

```sql
\set ON_ERROR_STOP on
\getenv web_password QUEZO_WEB_PASSWORD
CREATE ROLE quezo_web LOGIN PASSWORD :'web_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

Verify the password is nonempty and distinct from the existing role credentials
before running; existing roles are not silently reused or altered. Then leave
the administrator session and run `npm run db:upgrade` with only the migration
URL. The migration owns schema/tables; application startup only verifies access.
Web processes receive only `QUEZO_WEB_DATABASE_URL` with `quezo_web`.

`sessions` stores SHA-256 opaque-ID hashes, originating login hash, server-only
access token, token/absolute/idle expiry and creation time. `login_transactions`
stores hashed browser binding, state, nonce, PKCE verifier, expiry and a consumed
flag. Consuming is atomic; session insertion deletes the consumed transaction
atomically and refuses expired/deleted transactions. Logout deletes both pending
login and session rows, including sessions completed from that login. No refresh
or ID token, provider subject, email, application actor or role snapshot is stored.
Token/PKCE values are plaintext within this restricted schema: protect database
transport, dumps, backups and administrator access as secrets; encryption at rest
and real-data retention remain operational gates, not claims of this package.

Unapplied failure rolls back the whole upgrade. Existing sessions survive web
process restarts. A deliberate recovery that loses/deletes session rows signs
users out rather than restoring authorization from a cache. Restoring old session
backups could resurrect locally invalidated sessions; a reviewed recovery must
invalidate restored sessions/login transactions before reopening traffic.
No destructive downgrade is supplied.

## Adding and recovering revisions

Generate a revision with `uv run --directory postgres --locked alembic revision -m "description"`.
There is no ORM metadata/autogeneration contract. Write explicit SQL or SQLAlchemy
Core operations, parameterize data access, inspect `down_revision`, and keep one
linear head. B.C. serializes ordering before integration. Applied revisions are
immutable; do not stamp a database to hide unapplied work.

Run migration tests on a clean database and from the actual previous integrated
revision before review. Tests use disposable synthetic tables only; they never
add feature schemas to these migrations.

Downgrades deliberately fail: there is no unreviewed destructive rollback command.
For an unapplied failure, fix the cause and rerun; the transaction leaves the
previous baseline intact. After a committed change, use a reviewed forward
correction or a separately approved backup/restore procedure. Destructive changes
require B.C.'s reviewed backup/recovery plan. This foundation is not backup,
deployment or recovery acceptance.
