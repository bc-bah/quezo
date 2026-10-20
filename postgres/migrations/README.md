# Database migrations

Reserved for reviewed, ordered PostgreSQL migrations after architecture approval.
There is no schema, seed data, migration runner, or connection code yet.

Select and lock a migration runner with the first approved persistence slice.
SQLAlchemy/Alembic are Python ecosystem candidates, not installed or approved
requirements. The FastAPI switch does not change the PostgreSQL integrity rules.
Keep applied migrations immutable, record applied versions, and serialize migration
execution as a release step. Use database constraints for ownership relationships,
version references, response uniqueness and exactly one grade per attempt.

Schema changes and their real-database tests should accompany the feature they
enable. Destructive changes require a reviewed backup/recovery plan.
