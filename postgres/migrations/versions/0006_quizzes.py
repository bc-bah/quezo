"""Draft composition, immutable publication and retained command acknowledgements."""

from alembic import op

revision = "0006_quizzes"
down_revision = "0005_questions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION quezo.quiz_policy_valid(p jsonb)
        RETURNS boolean LANGUAGE plpgsql STABLE STRICT AS $$
        DECLARE key text; value jsonb; start_at timestamptz; end_at timestamptz;
        BEGIN
            IF jsonb_typeof(p) <> 'object' OR NOT p ?& ARRAY[
                'durationSeconds','attemptLimit','availabilityStart','availabilityEnd','timeZone',
                'randomizeQuestions','randomizeOptions','scoreRelease','answerKeyRelease','explanationRelease']
                OR p - ARRAY['durationSeconds','attemptLimit','availabilityStart','availabilityEnd','timeZone',
                'randomizeQuestions','randomizeOptions','scoreRelease','answerKeyRelease','explanationRelease'] <> '{}'
            THEN RETURN false; END IF;
            FOREACH key IN ARRAY ARRAY['durationSeconds','attemptLimit'] LOOP
                value := p->key;
                IF value <> 'null'::jsonb AND
                    (jsonb_typeof(value) <> 'number' OR value::text !~ '^[0-9]+$')
                THEN RETURN false; END IF;
            END LOOP;
            IF (p->>'durationSeconds')::numeric NOT BETWEEN 60 AND 604800
                OR (p->>'attemptLimit')::numeric NOT BETWEEN 1 AND 100
                OR jsonb_typeof(p->'randomizeQuestions') <> 'boolean'
                OR jsonb_typeof(p->'randomizeOptions') <> 'boolean'
                OR jsonb_typeof(p->'timeZone') <> 'string'
                OR NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name = p->>'timeZone')
            THEN RETURN false; END IF;
            FOREACH key IN ARRAY ARRAY['availabilityStart','availabilityEnd'] LOOP
                value := p->key;
                IF value <> 'null'::jsonb AND (jsonb_typeof(value) <> 'string'
                    OR (p->>key) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?([Zz]|[+]00:00)$')
                THEN RETURN false; END IF;
            END LOOP;
            start_at := (p->>'availabilityStart')::timestamptz;
            end_at := (p->>'availabilityEnd')::timestamptz;
            IF start_at >= end_at THEN RETURN false; END IF;
            FOREACH key IN ARRAY ARRAY['scoreRelease','answerKeyRelease','explanationRelease'] LOOP
                IF jsonb_typeof(p->key) <> 'string' OR (p->>key) NOT IN
                    ('after_finalization','after_availability_end','never')
                    OR ((p->>key) = 'after_availability_end' AND end_at IS NULL)
                THEN RETURN false; END IF;
            END LOOP;
            RETURN true;
        END $$;
        GRANT EXECUTE ON FUNCTION quezo.quiz_policy_valid(jsonb) TO quezo_runtime;
        ALTER TABLE quezo.questions ADD CONSTRAINT questions_id_owner UNIQUE (id, owner_id);
        ALTER TABLE quezo.question_versions ADD CONSTRAINT question_versions_id_question UNIQUE (id, question_id);
        CREATE TABLE quezo.quizzes (
            id uuid PRIMARY KEY,
            owner_id uuid NOT NULL REFERENCES quezo.accounts(id),
            title text NOT NULL CHECK (quezo.question_text_valid(title, 200, true)),
            state text NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','published','closed','archived')),
            draft_revision integer NOT NULL DEFAULT 1 CHECK (draft_revision > 0),
            draft jsonb,
            published_version_id uuid,
            UNIQUE (id, owner_id),
            CHECK (draft IS NULL OR (
                jsonb_typeof(draft) = 'object' AND draft ?& ARRAY['title','instructions','questions','policy']
                AND draft - ARRAY['title','instructions','questions','policy'] = '{}'
                AND jsonb_typeof(draft->'title') = 'string'
                AND quezo.question_text_valid(draft->>'title', 200, true)
                AND jsonb_typeof(draft->'instructions') = 'string'
                AND quezo.question_text_valid(draft->>'instructions', 10000, false)
                AND jsonb_typeof(draft->'questions') = 'array'
                AND jsonb_array_length(draft->'questions') <= 200
                AND quezo.quiz_policy_valid(draft->'policy')
            )),
            CHECK (state <> 'draft' OR (draft IS NOT NULL AND published_version_id IS NULL)),
            CHECK (state <> 'published' OR published_version_id IS NOT NULL)
        );
        CREATE INDEX quizzes_owner ON quezo.quizzes(owner_id, id);
        CREATE TABLE quezo.quiz_versions (
            id uuid PRIMARY KEY,
            quiz_id uuid NOT NULL,
            owner_id uuid NOT NULL,
            draft_revision integer NOT NULL CHECK (draft_revision > 0),
            title text NOT NULL CHECK (quezo.question_text_valid(title, 200, true)),
            instructions text NOT NULL CHECK (quezo.question_text_valid(instructions, 10000, false)),
            policy jsonb NOT NULL CHECK (quezo.quiz_policy_valid(policy)),
            possible_points integer NOT NULL CHECK (possible_points BETWEEN 1 AND 2000000),
            published_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            UNIQUE (quiz_id, draft_revision),
            UNIQUE (id, quiz_id),
            UNIQUE (id, owner_id),
            FOREIGN KEY (quiz_id, owner_id) REFERENCES quezo.quizzes(id, owner_id)
        );
        ALTER TABLE quezo.quizzes ADD CONSTRAINT quizzes_publication
            FOREIGN KEY (published_version_id, id) REFERENCES quezo.quiz_versions(id, quiz_id);
        CREATE TABLE quezo.quiz_questions (
            quiz_version_id uuid NOT NULL,
            owner_id uuid NOT NULL,
            question_id uuid NOT NULL,
            question_version_id uuid NOT NULL,
            position integer NOT NULL CHECK (position BETWEEN 1 AND 200),
            question jsonb NOT NULL,
            point_override integer CHECK (point_override BETWEEN 0 AND 10000),
            effective_points integer NOT NULL CHECK (effective_points BETWEEN 0 AND 10000),
            PRIMARY KEY (quiz_version_id, position),
            UNIQUE (quiz_version_id, question_id),
            FOREIGN KEY (quiz_version_id, owner_id) REFERENCES quezo.quiz_versions(id, owner_id),
            FOREIGN KEY (question_id, owner_id) REFERENCES quezo.questions(id, owner_id),
            FOREIGN KEY (question_version_id, question_id) REFERENCES quezo.question_versions(id, question_id)
        );
        CREATE TABLE quezo.quiz_publication_commands (
            actor_id uuid NOT NULL,
            quiz_id uuid NOT NULL,
            operation text NOT NULL CHECK (operation = 'publish'),
            request_id uuid NOT NULL,
            version_id uuid NOT NULL,
            fingerprint text NOT NULL CHECK (fingerprint ~ '^[0-9a-f]{64}$'),
            acknowledgement jsonb NOT NULL,
            PRIMARY KEY (actor_id, quiz_id, operation, request_id),
            FOREIGN KEY (quiz_id, actor_id) REFERENCES quezo.quizzes(id, owner_id),
            FOREIGN KEY (version_id, quiz_id) REFERENCES quezo.quiz_versions(id, quiz_id),
            CHECK ((jsonb_typeof(acknowledgement) = 'object'
                AND acknowledgement ?& ARRAY['requestId','quizId','versionId','draftRevision','publishedAt']
                AND acknowledgement - ARRAY['requestId','quizId','versionId','draftRevision','publishedAt'] = '{}'
                AND acknowledgement->>'requestId' = request_id::text
                AND acknowledgement->>'quizId' = quiz_id::text
                AND acknowledgement->>'versionId' = version_id::text) IS TRUE)
        );
        CREATE TABLE quezo.quiz_publication_events (
            version_id uuid PRIMARY KEY,
            actor_id uuid NOT NULL,
            quiz_id uuid NOT NULL,
            request_id uuid NOT NULL,
            operation text NOT NULL DEFAULT 'publish' CHECK (operation = 'publish'),
            correlation_id uuid NOT NULL,
            occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
            FOREIGN KEY (version_id, quiz_id) REFERENCES quezo.quiz_versions(id, quiz_id),
            FOREIGN KEY (quiz_id, actor_id) REFERENCES quezo.quizzes(id, owner_id),
            FOREIGN KEY (actor_id, quiz_id, operation, request_id)
                REFERENCES quezo.quiz_publication_commands(actor_id, quiz_id, operation, request_id)
        );
    """)
    op.execute("""
        CREATE FUNCTION quezo.validate_quiz_question() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE expected jsonb; points integer;
        BEGIN
            IF EXISTS (SELECT 1 FROM quezo.quiz_publication_events WHERE version_id = NEW.quiz_version_id)
            THEN RAISE EXCEPTION 'Publication is sealed' USING ERRCODE = '23514'; END IF;
            SELECT jsonb_build_object(
                'questionId', q.id, 'bankId', q.bank_id, 'versionId', v.id, 'revision', v.revision,
                'questionType', v.question_type, 'prompt', v.prompt, 'options', v.options,
                'correctOptionId', v.correct_option_id, 'defaultPoints', v.default_points, 'feedback', v.feedback
            ), v.default_points INTO expected, points
            FROM quezo.questions q JOIN quezo.question_versions v ON v.question_id = q.id
            WHERE q.id = NEW.question_id AND v.id = NEW.question_version_id AND q.owner_id = NEW.owner_id;
            IF expected IS NULL OR NEW.question - 'createdAt' <> expected
                OR (NEW.question->>'createdAt')::timestamptz IS DISTINCT FROM
                    (SELECT created_at FROM quezo.question_versions WHERE id = NEW.question_version_id)
                OR NEW.effective_points <> coalesce(NEW.point_override, points)
            THEN RAISE EXCEPTION 'Invalid pinned question' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
        CREATE TRIGGER quiz_question_snapshot BEFORE INSERT ON quezo.quiz_questions
            FOR EACH ROW EXECUTE FUNCTION quezo.validate_quiz_question();
        CREATE FUNCTION quezo.validate_quiz_publication() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE version uuid; total integer; count_items integer; last_position integer; expected integer;
        BEGIN
            IF TG_TABLE_NAME = 'quiz_versions' THEN version := NEW.id;
            ELSE version := NEW.quiz_version_id; END IF;
            SELECT count(*), sum(effective_points), max(position) INTO count_items, total, last_position
                FROM quezo.quiz_questions WHERE quiz_version_id = version;
            SELECT possible_points INTO expected FROM quezo.quiz_versions WHERE id = version;
            IF count_items NOT BETWEEN 1 AND 200 OR last_position <> count_items OR total <> expected
                OR NOT EXISTS (SELECT 1 FROM quezo.quiz_publication_events WHERE version_id = version)
            THEN RAISE EXCEPTION 'Incomplete publication' USING ERRCODE = '23514'; END IF;
            RETURN NULL;
        END $$;
        CREATE CONSTRAINT TRIGGER complete_quiz_version AFTER INSERT ON quezo.quiz_versions
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.validate_quiz_publication();
        CREATE CONSTRAINT TRIGGER complete_quiz_questions AFTER INSERT ON quezo.quiz_questions
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.validate_quiz_publication();
        CREATE FUNCTION quezo.reject_quiz_publication_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Publication records are immutable' USING ERRCODE = '23514';
        END $$;
    """)
    for table in ("quiz_versions", "quiz_questions", "quiz_publication_commands", "quiz_publication_events"):
        op.execute(f"""
            REVOKE UPDATE, DELETE ON quezo.{table} FROM quezo_runtime;
            CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON quezo.{table}
                FOR EACH ROW EXECUTE FUNCTION quezo.reject_quiz_publication_mutation()
        """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
