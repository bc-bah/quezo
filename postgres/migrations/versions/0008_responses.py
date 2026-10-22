"""Durable response CAS and retained save acknowledgements."""

from alembic import op

revision = "0008_responses"
down_revision = "0007_attempt_start"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE quezo.attempts ADD UNIQUE (id, learner_id);
        CREATE TABLE quezo.attempt_responses (
            question_id uuid PRIMARY KEY,
            attempt_id uuid NOT NULL,
            selected_option_id uuid,
            revision bigint NOT NULL DEFAULT 0 CHECK (revision BETWEEN 0 AND 9007199254740991),
            saved_at timestamptz,
            FOREIGN KEY (question_id, attempt_id) REFERENCES quezo.attempt_questions(id, attempt_id),
            CHECK ((revision = 0 AND selected_option_id IS NULL AND saved_at IS NULL)
                OR (revision > 0 AND saved_at IS NOT NULL))
        );
        CREATE INDEX responses_attempt ON quezo.attempt_responses(attempt_id);
        INSERT INTO quezo.attempt_responses (question_id, attempt_id)
            SELECT id, attempt_id FROM quezo.attempt_questions;
        CREATE TABLE quezo.response_commands (
            actor_id uuid NOT NULL,
            attempt_id uuid NOT NULL,
            operation text NOT NULL CHECK (operation = 'save'),
            request_id uuid NOT NULL,
            question_id uuid NOT NULL,
            fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
            response_revision bigint NOT NULL CHECK (response_revision BETWEEN 1 AND 9007199254740991),
            selected_option_id uuid,
            saved_at timestamptz NOT NULL,
            PRIMARY KEY (actor_id, attempt_id, operation, request_id),
            UNIQUE (question_id, response_revision),
            FOREIGN KEY (attempt_id, actor_id) REFERENCES quezo.attempts(id, learner_id),
            FOREIGN KEY (question_id, attempt_id) REFERENCES quezo.attempt_questions(id, attempt_id)
        );
        CREATE FUNCTION quezo.initialize_response() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO quezo.attempt_responses (question_id, attempt_id) VALUES (NEW.id, NEW.attempt_id);
            RETURN NEW;
        END $$;
        CREATE TRIGGER initialize_response AFTER INSERT ON quezo.attempt_questions
            FOR EACH ROW EXECUTE FUNCTION quezo.initialize_response();
        CREATE FUNCTION quezo.validate_response() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE a quezo.attempts;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Responses are retained' USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'INSERT' THEN
                IF NEW.revision <> 0 OR NEW.selected_option_id IS NOT NULL OR NEW.saved_at IS NOT NULL
                THEN RAISE EXCEPTION 'Initial response must be unanswered' USING ERRCODE = '23514'; END IF;
                RETURN NEW;
            END IF;
            SELECT * INTO a FROM quezo.attempts WHERE id = OLD.attempt_id FOR UPDATE;
            IF (NEW.question_id, NEW.attempt_id) IS DISTINCT FROM (OLD.question_id, OLD.attempt_id)
                OR NEW.revision <> OLD.revision + 1 OR NEW.saved_at IS NULL
                OR a.state <> 'in_progress' OR NEW.saved_at >= a.deadline
                OR NEW.saved_at < a.started_at
                OR (NEW.selected_option_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM quezo.attempt_questions q, jsonb_array_elements(q.options) o
                    WHERE q.id = OLD.question_id AND (o->>'id')::uuid = NEW.selected_option_id))
            THEN RAISE EXCEPTION 'Invalid response transition' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER validate_response BEFORE INSERT OR UPDATE OR DELETE ON quezo.attempt_responses
            FOR EACH ROW EXECUTE FUNCTION quezo.validate_response();
        CREATE FUNCTION quezo.response_has_ack() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM quezo.response_commands c
                WHERE c.question_id = NEW.question_id AND c.response_revision = NEW.revision
                AND c.attempt_id = NEW.attempt_id AND c.saved_at = NEW.saved_at
                AND c.selected_option_id IS NOT DISTINCT FROM NEW.selected_option_id)
            THEN RAISE EXCEPTION 'Missing save acknowledgement' USING ERRCODE = '23514'; END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER response_has_ack AFTER UPDATE ON quezo.attempt_responses
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.response_has_ack();
        CREATE FUNCTION quezo.ack_has_response() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM quezo.attempt_responses r
                WHERE r.question_id = NEW.question_id AND r.attempt_id = NEW.attempt_id
                AND r.revision = NEW.response_revision AND r.saved_at = NEW.saved_at
                AND r.selected_option_id IS NOT DISTINCT FROM NEW.selected_option_id)
            THEN RAISE EXCEPTION 'Invalid save acknowledgement' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER ack_has_response BEFORE INSERT ON quezo.response_commands
            FOR EACH ROW EXECUTE FUNCTION quezo.ack_has_response();
        CREATE TRIGGER immutable_response_commands BEFORE UPDATE OR DELETE ON quezo.response_commands
            FOR EACH ROW EXECUTE FUNCTION quezo.reject_quiz_publication_mutation();
        REVOKE DELETE ON quezo.attempt_responses FROM quezo_runtime;
        REVOKE UPDATE, DELETE ON quezo.response_commands FROM quezo_runtime;
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
