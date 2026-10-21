"""Owned banks, stable questions and immutable versions."""

from alembic import op

revision = "0005_questions"
down_revision = "0004_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(r"""
        CREATE FUNCTION quezo.question_text_valid(value text, maximum integer, required boolean)
        RETURNS boolean LANGUAGE sql IMMUTABLE STRICT AS $$
            SELECT length(value) <= maximum
              AND (NOT required OR value ~ '[^[:space:]]')
              AND value !~ '[\x01-\x08\x0B\x0C\x0E-\x1F]'
        $$
    """)
    op.execute("""
        CREATE FUNCTION quezo.question_options_valid(options jsonb, kind text, correct uuid)
        RETURNS boolean LANGUAGE plpgsql IMMUTABLE STRICT AS $$
        DECLARE item jsonb; ids uuid[] := '{}'; option_id uuid; labels text[] := '{}';
        BEGIN
            IF jsonb_typeof(options) <> 'array' THEN RETURN false; END IF;
            IF jsonb_array_length(options) NOT BETWEEN 2 AND 10 THEN RETURN false; END IF;
            FOR item IN SELECT * FROM jsonb_array_elements(options) LOOP
                IF jsonb_typeof(item) <> 'object' THEN RETURN false; END IF;
                IF NOT (item ?& ARRAY['id','text']) OR item - ARRAY['id','text'] <> '{}'::jsonb
                   OR jsonb_typeof(item->'id') <> 'string'
                   OR jsonb_typeof(item->'text') <> 'string'
                   OR (item->>'id') !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                   OR NOT quezo.question_text_valid(item->>'text', 1000, true)
                THEN RETURN false; END IF;
                option_id := (item->>'id')::uuid;
                IF option_id = ANY(ids) THEN RETURN false; END IF;
                ids := array_append(ids, option_id);
                labels := array_append(labels, item->>'text');
            END LOOP;
            RETURN correct = ANY(ids) AND
                (kind = 'mcq' OR (kind = 'true_false' AND cardinality(ids) = 2
                 AND labels @> ARRAY['True','False']));
        END
        $$
    """)
    op.execute("""
        GRANT EXECUTE ON FUNCTION quezo.question_text_valid(text, integer, boolean),
            quezo.question_options_valid(jsonb, text, uuid) TO quezo_runtime
    """)
    op.execute("""
        CREATE TABLE quezo.question_banks (
            id uuid PRIMARY KEY,
            owner_id uuid NOT NULL REFERENCES quezo.accounts(id),
            name text NOT NULL CHECK (quezo.question_text_valid(name, 100, true)),
            archived boolean NOT NULL DEFAULT false,
            UNIQUE (id, owner_id)
        );
        CREATE INDEX question_banks_owner ON quezo.question_banks(owner_id, id);
        CREATE TABLE quezo.questions (
            id uuid PRIMARY KEY,
            bank_id uuid NOT NULL,
            owner_id uuid NOT NULL REFERENCES quezo.accounts(id),
            revision integer NOT NULL CHECK (revision > 0),
            archived boolean NOT NULL DEFAULT false,
            FOREIGN KEY (bank_id, owner_id) REFERENCES quezo.question_banks(id, owner_id)
        );
        CREATE INDEX questions_owner ON quezo.questions(owner_id, id);
        CREATE INDEX questions_bank ON quezo.questions(bank_id, owner_id, id);
        CREATE TABLE quezo.question_versions (
            id uuid PRIMARY KEY,
            question_id uuid NOT NULL REFERENCES quezo.questions(id),
            revision integer NOT NULL CHECK (revision > 0),
            question_type text NOT NULL CHECK (question_type IN ('mcq', 'true_false')),
            prompt text NOT NULL CHECK (quezo.question_text_valid(prompt, 4000, true)),
            options jsonb NOT NULL,
            correct_option_id uuid NOT NULL,
            default_points integer NOT NULL CHECK (default_points BETWEEN 0 AND 10000),
            feedback text NOT NULL CHECK (quezo.question_text_valid(feedback, 4000, false)),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (question_id, revision),
            CHECK (quezo.question_options_valid(options, question_type, correct_option_id))
        );
        ALTER TABLE quezo.questions ADD CONSTRAINT questions_current_version
            FOREIGN KEY (id, revision) REFERENCES quezo.question_versions(question_id, revision)
            DEFERRABLE INITIALLY DEFERRED;
        REVOKE UPDATE, DELETE ON quezo.question_versions FROM quezo_runtime
    """)
    op.execute("""
        CREATE FUNCTION quezo.reject_question_version_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Question versions are immutable' USING ERRCODE = '23514';
        END
        $$;
        CREATE TRIGGER immutable_question_version
            BEFORE UPDATE OR DELETE ON quezo.question_versions
            FOR EACH ROW EXECUTE FUNCTION quezo.reject_question_version_mutation()
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
