"""Application-owned identity mappings and current access."""

from alembic import op

revision = "0004_identity"
down_revision = "0003_web_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE quezo.accounts (
            id uuid PRIMARY KEY,
            status text NOT NULL DEFAULT 'disabled' CHECK (status IN ('active', 'disabled')),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("""
        CREATE TABLE quezo.identity_mappings (
            issuer text NOT NULL CHECK (length(issuer) BETWEEN 1 AND 2048),
            subject text NOT NULL CHECK (length(btrim(subject)) BETWEEN 1 AND 255),
            account_id uuid NOT NULL UNIQUE REFERENCES quezo.accounts(id),
            active boolean NOT NULL DEFAULT false,
            PRIMARY KEY (issuer, subject)
        )
    """)
    op.execute("""
        CREATE TABLE quezo.account_roles (
            account_id uuid NOT NULL REFERENCES quezo.accounts(id),
            role text NOT NULL CHECK (role IN ('administrator', 'author', 'learner')),
            PRIMARY KEY (account_id, role)
        )
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
