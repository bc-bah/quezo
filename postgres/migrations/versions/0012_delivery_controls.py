"""Freeze explicit pre-start timing; preserve all existing snapshots and deadlines."""

from alembic import op

revision = "0012_delivery_controls"
down_revision = "0011_account_administration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE quezo.attempts
            ADD COLUMN timing_choice text NOT NULL DEFAULT 'standard',
            ADD COLUMN adjusted_duration_seconds integer,
            ADD CONSTRAINT attempt_timing_choice CHECK (
                (timing_choice IN ('standard', 'off') AND adjusted_duration_seconds IS NULL)
                OR (timing_choice = 'adjusted' AND adjusted_duration_seconds IS NOT NULL
                    AND adjusted_duration_seconds BETWEEN 60 AND 6048000));
        CREATE OR REPLACE FUNCTION quezo.validate_attempt_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE v quezo.quiz_versions; n integer; expected_deadline timestamptz;
        BEGIN
            SELECT * INTO v FROM quezo.quiz_versions WHERE id = NEW.version_id;
            expected_deadline := CASE NEW.timing_choice
                WHEN 'off' THEN NULL
                WHEN 'adjusted' THEN NEW.started_at + NEW.adjusted_duration_seconds * interval '1 second'
                ELSE least((v.policy->>'availabilityEnd')::timestamptz,
                    NEW.started_at + (v.policy->>'durationSeconds')::integer * interval '1 second')
                END;
            IF (NEW.title, NEW.instructions, NEW.policy, NEW.possible_points)
                IS DISTINCT FROM (v.title, v.instructions, v.policy, v.possible_points)
                OR NEW.deadline IS DISTINCT FROM expected_deadline
                OR NEW.started_at < (v.policy->>'availabilityStart')::timestamptz
                OR NEW.started_at >= (v.policy->>'availabilityEnd')::timestamptz
                OR NEW.attempt_number > (v.policy->>'attemptLimit')::integer
            THEN RAISE EXCEPTION 'Invalid attempt snapshot' USING ERRCODE = '23514'; END IF;
            SELECT count(*) + 1 INTO n FROM quezo.attempts WHERE assignment_id = NEW.assignment_id;
            IF n <> NEW.attempt_number OR NEW.state <> 'in_progress'
            THEN RAISE EXCEPTION 'Invalid attempt allocation' USING ERRCODE = '23514'; END IF;
            RETURN NEW;
        END $$;
    """)


def downgrade() -> None:
    raise RuntimeError("Forward migrations only; use reviewed recovery procedures")
