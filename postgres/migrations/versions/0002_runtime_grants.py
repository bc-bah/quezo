"""Grant runtime data access without DDL or migration-ledger privileges."""

from alembic import op

revision = "0002_runtime_grants"
down_revision = "0001_application_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
            EXECUTE format(
                'GRANT CONNECT ON DATABASE %I TO quezo_runtime', current_database()
            );
        END $$
    """)
    op.execute("GRANT USAGE ON SCHEMA quezo TO quezo_runtime")
    op.execute("""
        ALTER DEFAULT PRIVILEGES FOR ROLE quezo_migrator IN SCHEMA quezo
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO quezo_runtime
    """)
    op.execute("""
        ALTER DEFAULT PRIVILEGES FOR ROLE quezo_migrator IN SCHEMA quezo
        GRANT USAGE, SELECT ON SEQUENCES TO quezo_runtime
    """)
    op.execute("""
        ALTER DEFAULT PRIVILEGES FOR ROLE quezo_migrator
        REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
