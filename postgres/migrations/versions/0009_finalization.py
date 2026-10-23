"""Atomic immutable objective completion; no historical grading or regrade."""

from alembic import op

revision = "0009_finalization"
down_revision = "0008_responses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM quezo.attempts WHERE state <> 'in_progress')
            THEN RAISE EXCEPTION 'Ungraded terminal fixtures require reviewed recovery before D03';
            END IF;
        END $$;
        ALTER TABLE quezo.attempts DROP CONSTRAINT attempts_state_check;
        ALTER TABLE quezo.attempts ADD COLUMN completion_reason text, ADD COLUMN finalized_at timestamptz;
        ALTER TABLE quezo.attempts ADD CONSTRAINT attempt_completion_state CHECK (
            (state = 'in_progress' AND completion_reason IS NULL AND finalized_at IS NULL)
            OR (state = 'finalized' AND completion_reason IS NOT NULL AND finalized_at IS NOT NULL
                AND finalized_at >= started_at AND (
                    (completion_reason = 'submitted' AND (deadline IS NULL OR finalized_at < deadline))
                    OR (completion_reason = 'expired' AND deadline IS NOT NULL AND finalized_at >= deadline))));
        CREATE OR REPLACE FUNCTION quezo.protect_attempt_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Attempts cannot be deleted' USING ERRCODE = '23514';
            END IF;
            IF (to_jsonb(NEW) - ARRAY['state','completion_reason','finalized_at'])
                IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['state','completion_reason','finalized_at'])
                OR (OLD.state = 'finalized' AND NEW IS DISTINCT FROM OLD)
            THEN RAISE EXCEPTION 'Attempt snapshot is immutable' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TABLE quezo.grades (
            id uuid PRIMARY KEY,
            attempt_id uuid NOT NULL UNIQUE REFERENCES quezo.attempts(id),
            earned_points integer NOT NULL CHECK (earned_points >= 0),
            possible_points integer NOT NULL CHECK (possible_points BETWEEN 1 AND 2000000),
            CHECK (earned_points <= possible_points)
        );
        CREATE TABLE quezo.grade_items (
            attempt_id uuid NOT NULL REFERENCES quezo.grades(attempt_id),
            question_id uuid PRIMARY KEY,
            outcome text NOT NULL CHECK (outcome IN ('correct','incorrect','unanswered')),
            earned_points integer NOT NULL CHECK (earned_points >= 0),
            possible_points integer NOT NULL CHECK (possible_points BETWEEN 0 AND 10000),
            FOREIGN KEY (question_id, attempt_id) REFERENCES quezo.attempt_questions(id, attempt_id),
            CHECK ((outcome = 'correct' AND earned_points = possible_points)
                OR (outcome <> 'correct' AND earned_points = 0))
        );
        CREATE INDEX grade_items_attempt ON quezo.grade_items(attempt_id);
        CREATE TABLE quezo.attempt_completion_events (
            attempt_id uuid PRIMARY KEY REFERENCES quezo.grades(attempt_id),
            reason text NOT NULL CHECK (reason IN ('submitted','expired')),
            finalized_at timestamptz NOT NULL
        );
        CREATE FUNCTION quezo.complete_finalization() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE target uuid; a quezo.attempts; g quezo.grades;
            n integer; earned bigint; possible bigint;
        BEGIN
            IF TG_TABLE_NAME = 'attempts' THEN target := NEW.id; ELSE target := NEW.attempt_id; END IF;
            SELECT * INTO a FROM quezo.attempts WHERE id = target;
            SELECT * INTO g FROM quezo.grades WHERE attempt_id = target;
            IF a.state = 'in_progress' AND g.id IS NULL THEN RETURN NULL; END IF;
            SELECT count(*), sum(earned_points), sum(possible_points) INTO n, earned, possible
                FROM quezo.grade_items WHERE attempt_id = target;
            IF a.state <> 'finalized' OR g.id IS NULL OR g.possible_points <> a.possible_points
                OR n <> (SELECT count(*) FROM quezo.attempt_questions WHERE attempt_id = target)
                OR earned IS DISTINCT FROM g.earned_points::bigint
                OR possible IS DISTINCT FROM g.possible_points::bigint
                OR EXISTS (SELECT 1 FROM quezo.grade_items i JOIN quezo.attempt_questions q ON q.id = i.question_id
                    WHERE i.attempt_id = target AND i.possible_points <> q.effective_points)
                OR NOT EXISTS (SELECT 1 FROM quezo.attempt_completion_events e
                    WHERE e.attempt_id = target AND e.reason = a.completion_reason AND e.finalized_at = a.finalized_at)
            THEN RAISE EXCEPTION 'Incomplete finalization' USING ERRCODE = '23514'; END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER complete_finalization AFTER INSERT OR UPDATE ON quezo.attempts
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.complete_finalization();
        CREATE FUNCTION quezo.require_unfinalized_parent() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE current_state text;
        BEGIN
            SELECT state INTO current_state FROM quezo.attempts WHERE id = NEW.attempt_id FOR UPDATE;
            IF current_state <> 'in_progress'
            THEN RAISE EXCEPTION 'Grade is sealed' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER grade_parent BEFORE INSERT ON quezo.grades
            FOR EACH ROW EXECUTE FUNCTION quezo.require_unfinalized_parent();
        CREATE TRIGGER grade_item_parent BEFORE INSERT ON quezo.grade_items
            FOR EACH ROW EXECUTE FUNCTION quezo.require_unfinalized_parent();
    """)
    for table in ("grades", "grade_items", "attempt_completion_events"):
        op.execute(f"""
            REVOKE UPDATE, DELETE ON quezo.{table} FROM quezo_runtime;
            CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON quezo.{table}
                FOR EACH ROW EXECUTE FUNCTION quezo.reject_quiz_publication_mutation();
            CREATE CONSTRAINT TRIGGER complete_finalization AFTER INSERT ON quezo.{table}
                DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.complete_finalization();
        """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
