"""Account administration profiles, provisioning state and integrity events."""

from alembic import op

revision = "0011_account_administration"
down_revision = "0010_author_workspace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE quezo.accounts
            ADD COLUMN username text,
            ADD COLUMN email text,
            ADD COLUMN provisioning_state text NOT NULL DEFAULT 'complete'
                CHECK (provisioning_state IN ('pending', 'complete', 'failed')),
            ADD COLUMN provisioning_error_code text,
            ADD COLUMN identity_sync_state text NOT NULL DEFAULT 'in_sync'
                CHECK (identity_sync_state IN ('in_sync', 'pending', 'failed')),
            ADD COLUMN identity_error_code text,
            ADD COLUMN identity_desired_enabled boolean NOT NULL DEFAULT false,
            ADD CONSTRAINT account_username_valid
                CHECK (username IS NULL OR (
                    length(username) BETWEEN 3 AND 128
                    AND username ~ '^[A-Za-z0-9._@+-]+$'
                )),
            ADD CONSTRAINT account_email_valid
                CHECK (email IS NULL OR (
                    length(email) BETWEEN 3 AND 254
                    AND email ~ '^[^[:space:]@]+@[^[:space:]@]+$'
                ))
    """)
    op.execute("""
        CREATE UNIQUE INDEX accounts_username_unique
        ON quezo.accounts (lower(username)) WHERE username IS NOT NULL
    """)
    op.execute("""
        CREATE TABLE quezo.account_admin_events (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            actor_id uuid NOT NULL REFERENCES quezo.accounts(id),
            target_id uuid NOT NULL REFERENCES quezo.accounts(id),
            action text NOT NULL CHECK (action IN (
                'provision', 'profile_update', 'roles_update', 'activate', 'deactivate'
            )),
            outcome text NOT NULL CHECK (outcome IN ('success', 'failure')),
            error_code text,
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            CHECK ((outcome = 'failure') = (error_code IS NOT NULL))
        )
    """)
    op.execute("""
        CREATE INDEX account_admin_events_target_time
        ON quezo.account_admin_events (target_id, occurred_at DESC)
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
