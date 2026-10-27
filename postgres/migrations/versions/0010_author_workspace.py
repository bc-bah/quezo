"""C03 question organization; preserve all immutable content and snapshots."""

from alembic import op

revision = "0010_author_workspace"
down_revision = "0009_finalization"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION quezo.question_tags_valid(tags text[])
        RETURNS boolean LANGUAGE sql IMMUTABLE STRICT AS $$
            SELECT cardinality(tags) <= 20 AND NOT EXISTS (
                SELECT 1 FROM unnest(tags) tag
                WHERE tag IS NULL OR NOT quezo.question_text_valid(tag, 50, true)
            )
        $$;
        GRANT EXECUTE ON FUNCTION quezo.question_tags_valid(text[]) TO quezo_runtime;
        ALTER TABLE quezo.questions
            ADD COLUMN category text CHECK (quezo.question_text_valid(category, 100, true)),
            ADD COLUMN tags text[] NOT NULL DEFAULT '{}' CHECK (quezo.question_tags_valid(tags));
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
