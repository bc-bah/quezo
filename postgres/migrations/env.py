import os

from alembic import context
from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool


def run_migrations() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Migrations require a live PostgreSQL connection")
    url = os.environ.get("QUEZO_MIGRATION_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        raise ValueError("QUEZO_MIGRATION_URL must be an explicit PostgreSQL URL")
    try:
        params = conninfo_to_dict(url)
    except ProgrammingError:
        raise ValueError("Invalid QUEZO_MIGRATION_URL") from None
    if (
        params.get("user") != "quezo_migrator"
        or not params.get("host")
        or not params.get("dbname")
        or "service" in params
    ):
        raise ValueError("Migrations require host, database and quezo_migrator identity")
    params.update(
        connect_timeout="5",
        application_name="quezo-migrations",
        options="-c statement_timeout=60000 -c lock_timeout=5000",
    )
    engine = create_engine(
        "postgresql+psycopg://", connect_args=params, poolclass=NullPool
    )
    try:
        with engine.begin() as connection:
            privileged = connection.execute(text(
                "SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication "
                "OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
            )).scalar_one()
            if privileged:
                raise RuntimeError("Migration identity must not have cluster privileges")
            # One transaction-scoped lock serializes all revisions, including version writes.
            if not connection.execute(
                text("SELECT pg_try_advisory_xact_lock(716269001)")
            ).scalar_one():
                raise RuntimeError("Another Quezo migration is running")
            context.configure(
                connection=connection,
                target_metadata=None,
                version_table_schema="public",
                transactional_ddl=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


run_migrations()
