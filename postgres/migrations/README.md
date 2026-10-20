# Database migrations

Reserved for reviewed, ordered PostgreSQL migrations in approved package F01.
There is no schema, seed data, migration runner, or connection code yet.

B.C. approved Alembic with SQLAlchemy Core (no ORM) and Psycopg 3 async/pooling
under [G00/DEC-07](../../docs/SOFTWARE-SPECIFICATION.md#g00-approval-record-20-october-2026).
Select compatible versions and lock them in F01; they are not installed yet.
The FastAPI switch does not change the PostgreSQL integrity rules.
Keep applied migrations immutable, record applied versions, and serialize migration
execution as a release step. Use database constraints for ownership relationships,
version references, response uniqueness and exactly one grade per attempt.

Schema changes and their real-database tests should accompany the feature they
enable. Destructive changes require a reviewed backup/recovery plan.
