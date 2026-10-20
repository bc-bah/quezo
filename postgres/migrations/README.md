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

Only `public.alembic_version` records migration state. There are no domain,
identity, session, seed, audit or acknowledgement tables. Upcoming packages
provide their own reviewed schema and section 6 constraints. Default runtime
grants apply only to tables/sequences created **by `quezo_migrator` in `quezo`**;
session storage must not use that schema or those grants.

The real prior-revision upgrade is `base -> 0001_application_schema`, disconnect,
then `0001_application_schema -> 0002_runtime_grants`. Tests verify runtime schema
access is absent before the second revision and present afterwards, as well as
a separate clean `base -> head` path and repeat `head` execution.

## Execution and identities

Bootstrap is an explicit local administrator action (`postgres/bootstrap/roles.sql`).
It creates distinct restricted login roles, makes `quezo_migrator` the database
owner and revokes public database/schema access. Neither role is a superuser,
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
