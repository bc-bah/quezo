"""Pinned assignments and atomic, replayable attempt snapshots."""

from alembic import op

revision = "0007_attempt_start"
down_revision = "0006_quizzes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE quezo.assignments (
            id uuid PRIMARY KEY,
            quiz_id uuid NOT NULL,
            version_id uuid NOT NULL,
            learner_id uuid NOT NULL REFERENCES quezo.accounts(id),
            created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (learner_id, version_id),
            UNIQUE (id, learner_id, version_id),
            FOREIGN KEY (version_id, quiz_id) REFERENCES quezo.quiz_versions(id, quiz_id)
        );
        CREATE INDEX assignments_learner ON quezo.assignments(learner_id, id);
        CREATE INDEX assignments_quiz ON quezo.assignments(quiz_id, id);
        CREATE TABLE quezo.attempts (
            id uuid PRIMARY KEY,
            assignment_id uuid NOT NULL,
            learner_id uuid NOT NULL,
            version_id uuid NOT NULL,
            attempt_number integer NOT NULL CHECK (attempt_number > 0),
            state text NOT NULL DEFAULT 'in_progress' CHECK (state IN ('in_progress','finalized','expired')),
            title text NOT NULL,
            instructions text NOT NULL,
            policy jsonb NOT NULL CHECK (quezo.quiz_policy_valid(policy)),
            started_at timestamptz NOT NULL,
            deadline timestamptz CHECK (deadline > started_at),
            possible_points integer NOT NULL CHECK (possible_points BETWEEN 1 AND 2000000),
            UNIQUE (assignment_id, attempt_number),
            UNIQUE (id, version_id),
            UNIQUE (id, assignment_id, learner_id),
            FOREIGN KEY (assignment_id, learner_id, version_id)
                REFERENCES quezo.assignments(id, learner_id, version_id)
        );
        CREATE UNIQUE INDEX one_active_attempt ON quezo.attempts(assignment_id) WHERE state = 'in_progress';
        CREATE INDEX attempts_learner ON quezo.attempts(learner_id, id);
        CREATE INDEX attempts_deadline ON quezo.attempts(deadline, id)
            WHERE state = 'in_progress' AND deadline IS NOT NULL;
        CREATE TABLE quezo.attempt_questions (
            id uuid PRIMARY KEY,
            attempt_id uuid NOT NULL,
            version_id uuid NOT NULL,
            question_id uuid NOT NULL,
            question_version_id uuid NOT NULL,
            position integer NOT NULL CHECK (position BETWEEN 1 AND 200),
            question jsonb NOT NULL,
            options jsonb NOT NULL,
            effective_points integer NOT NULL CHECK (effective_points BETWEEN 0 AND 10000),
            UNIQUE (attempt_id, position),
            UNIQUE (attempt_id, question_id),
            UNIQUE (id, attempt_id),
            FOREIGN KEY (attempt_id, version_id) REFERENCES quezo.attempts(id, version_id),
            FOREIGN KEY (version_id, question_id) REFERENCES quezo.quiz_questions(quiz_version_id, question_id),
            FOREIGN KEY (question_version_id, question_id) REFERENCES quezo.question_versions(id, question_id)
        );
        CREATE TABLE quezo.attempt_start_commands (
            actor_id uuid NOT NULL,
            assignment_id uuid NOT NULL,
            operation text NOT NULL CHECK (operation = 'start'),
            request_id uuid NOT NULL,
            fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
            attempt_id uuid NOT NULL,
            PRIMARY KEY (actor_id, assignment_id, operation, request_id),
            FOREIGN KEY (attempt_id, assignment_id, actor_id)
                REFERENCES quezo.attempts(id, assignment_id, learner_id)
        );
        CREATE FUNCTION quezo.validate_attempt_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE v quezo.quiz_versions; n integer;
        BEGIN
            SELECT * INTO v FROM quezo.quiz_versions WHERE id = NEW.version_id;
            IF (NEW.title, NEW.instructions, NEW.policy, NEW.possible_points)
                IS DISTINCT FROM (v.title, v.instructions, v.policy, v.possible_points)
                OR NEW.deadline IS DISTINCT FROM least(
                    (v.policy->>'availabilityEnd')::timestamptz,
                    NEW.started_at + (v.policy->>'durationSeconds')::integer * interval '1 second')
                OR NEW.started_at < (v.policy->>'availabilityStart')::timestamptz
                OR NEW.started_at >= (v.policy->>'availabilityEnd')::timestamptz
                OR NEW.attempt_number > (v.policy->>'attemptLimit')::integer
            THEN RAISE EXCEPTION 'Invalid attempt snapshot' USING ERRCODE = '23514'; END IF;
            SELECT count(*) + 1 INTO n FROM quezo.attempts WHERE assignment_id = NEW.assignment_id;
            IF n <> NEW.attempt_number OR NEW.state <> 'in_progress'
            THEN RAISE EXCEPTION 'Invalid attempt allocation' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER attempt_snapshot BEFORE INSERT ON quezo.attempts
            FOR EACH ROW EXECUTE FUNCTION quezo.validate_attempt_snapshot();
        CREATE FUNCTION quezo.protect_attempt_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Attempts cannot be deleted' USING ERRCODE = '23514';
            END IF;
            IF (to_jsonb(NEW) - 'state') IS DISTINCT FROM (to_jsonb(OLD) - 'state')
                OR (OLD.state <> 'in_progress' AND NEW.state <> OLD.state)
            THEN RAISE EXCEPTION 'Attempt snapshot is immutable' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER frozen_attempt BEFORE UPDATE OR DELETE ON quezo.attempts
            FOR EACH ROW EXECUTE FUNCTION quezo.protect_attempt_snapshot();
        CREATE FUNCTION quezo.validate_attempt_question() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE q quezo.quiz_questions; p jsonb;
        BEGIN
            IF EXISTS (SELECT 1 FROM quezo.attempt_start_commands WHERE attempt_id = NEW.attempt_id)
            THEN RAISE EXCEPTION 'Attempt is sealed' USING ERRCODE = '23514'; END IF;
            SELECT * INTO q FROM quezo.quiz_questions
                WHERE quiz_version_id = NEW.version_id AND question_id = NEW.question_id;
            SELECT policy INTO p FROM quezo.attempts WHERE id = NEW.attempt_id;
            IF NEW.question IS DISTINCT FROM q.question OR NEW.effective_points IS DISTINCT FROM q.effective_points
                OR NEW.question_version_id IS DISTINCT FROM q.question_version_id
                OR jsonb_typeof(NEW.options) <> 'array'
                OR (SELECT jsonb_agg(value ORDER BY value->>'id') FROM jsonb_array_elements(NEW.options))
                   IS DISTINCT FROM
                   (SELECT jsonb_agg(value ORDER BY value->>'id') FROM jsonb_array_elements(q.question->'options'))
                OR (NOT (p->>'randomizeQuestions')::boolean AND NEW.position <> q.position)
                OR (NOT (p->>'randomizeOptions')::boolean AND NEW.options <> q.question->'options')
            THEN RAISE EXCEPTION 'Invalid attempt question' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER attempt_question_snapshot BEFORE INSERT ON quezo.attempt_questions
            FOR EACH ROW EXECUTE FUNCTION quezo.validate_attempt_question();
        CREATE FUNCTION quezo.complete_attempt_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE n integer; last_position integer; points integer; expected integer;
        BEGIN
            SELECT count(*), max(position), sum(effective_points) INTO n, last_position, points
                FROM quezo.attempt_questions WHERE attempt_id = NEW.id;
            SELECT count(*) INTO expected FROM quezo.quiz_questions WHERE quiz_version_id = NEW.version_id;
            IF n <> expected OR n <> last_position OR points <> NEW.possible_points
                OR NOT EXISTS (SELECT 1 FROM quezo.attempt_start_commands WHERE attempt_id = NEW.id)
            THEN RAISE EXCEPTION 'Incomplete attempt snapshot' USING ERRCODE = '23514'; END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER complete_attempt AFTER INSERT ON quezo.attempts
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.complete_attempt_snapshot();
        REVOKE DELETE ON quezo.attempts FROM quezo_runtime;
    """)
    for table in ("assignments", "attempt_questions", "attempt_start_commands"):
        op.execute(f"""
            REVOKE UPDATE, DELETE ON quezo.{table} FROM quezo_runtime;
            CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON quezo.{table}
                FOR EACH ROW EXECUTE FUNCTION quezo.reject_quiz_publication_mutation()
        """)
    # Row locking requires an UPDATE privilege; the trigger still rejects every mutation.
    op.execute("GRANT UPDATE (id) ON quezo.assignments TO quezo_runtime")


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
