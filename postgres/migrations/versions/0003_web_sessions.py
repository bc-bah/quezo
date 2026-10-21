"""Restricted web sessions, independent of assessment default grants."""

from alembic import op

revision = "0003_web_sessions"
down_revision = "0002_runtime_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA quezo_session AUTHORIZATION quezo_migrator")
    op.execute("REVOKE ALL ON SCHEMA quezo_session FROM PUBLIC, quezo_runtime")
    op.execute("""
        CREATE TABLE quezo_session.sessions (
            id_hash text PRIMARY KEY CHECK (id_hash ~ '^[0-9a-f]{64}$'),
            login_hash text NOT NULL UNIQUE CHECK (login_hash ~ '^[0-9a-f]{64}$'),
            access_token text NOT NULL CHECK (length(access_token) BETWEEN 1 AND 32768),
            token_expires_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            expires_at timestamptz NOT NULL,
            idle_expires_at timestamptz NOT NULL,
            CHECK (expires_at > created_at AND expires_at <= token_expires_at),
            CHECK (idle_expires_at <= expires_at)
        )
    """)
    op.execute("""
        CREATE TABLE quezo_session.login_transactions (
            id_hash text PRIMARY KEY CHECK (id_hash ~ '^[0-9a-f]{64}$'),
            state text NOT NULL,
            nonce text NOT NULL,
            verifier text NOT NULL,
            consumed boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            expires_at timestamptz NOT NULL,
            CHECK (expires_at > created_at)
        )
    """)
    op.execute("CREATE INDEX session_expiry ON quezo_session.sessions (expires_at)")
    op.execute(
        "CREATE INDEX login_expiry ON quezo_session.login_transactions (expires_at)"
    )
    op.execute("""
        DO $$
        BEGIN
            EXECUTE format(
                'GRANT CONNECT ON DATABASE %I TO quezo_web', current_database()
            );
        END $$
    """)
    op.execute("GRANT USAGE ON SCHEMA quezo_session TO quezo_web")
    op.execute("""
        GRANT SELECT, INSERT, UPDATE, DELETE
        ON quezo_session.sessions, quezo_session.login_transactions TO quezo_web
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
