"""Establish the application namespace from the empty scaffold baseline."""

from alembic import op

revision = "0001_application_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
    op.execute("CREATE SCHEMA quezo AUTHORIZATION quezo_migrator")
    op.execute("REVOKE ALL ON SCHEMA quezo FROM PUBLIC")


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
