from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase, run_migrations
from identity_helpers import SigningPeer
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import assigned, headers
from test_responses import opened, command, path


@pytest.fixture
def database(empty_database: IsolatedDatabase) -> Iterator[IsolatedDatabase]:
    run_migrations(empty_database.migration_url, "0007_attempt_start")
    yield empty_database


def test_prior_head_backfills_real_frozen_attempt(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    assignment, _ = assigned(author, database)
    attempt_id = uuid4()
    # Persist the actual D01 schema before upgrading; no response schema exists yet.
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("""
            INSERT INTO quezo.attempts (id, assignment_id, learner_id, version_id, attempt_number,
                title, instructions, policy, started_at, deadline, possible_points)
            SELECT %s, a.id, a.learner_id, v.id, 1, v.title, v.instructions, v.policy,
                clock_timestamp(), NULL, v.possible_points
            FROM quezo.assignments a JOIN quezo.quiz_versions v ON v.id = a.version_id WHERE a.id = %s
        """, (attempt_id, assignment["id"]))
        connection.execute("""
            INSERT INTO quezo.attempt_questions (id, attempt_id, version_id, question_id,
                question_version_id, position, question, options, effective_points)
            SELECT gen_random_uuid(), %s, quiz_version_id, question_id, question_version_id, position,
                question, question->'options', effective_points FROM quezo.quiz_questions WHERE quiz_version_id = %s
        """, (attempt_id, assignment["versionId"]))
        connection.execute("""
            INSERT INTO quezo.attempt_start_commands (actor_id, assignment_id, operation, request_id, fingerprint, attempt_id)
            SELECT learner_id, id, 'start', %s, %s, %s FROM quezo.assignments WHERE id = %s
        """, (uuid4(), "a" * 64, attempt_id, assignment["id"]))
        snapshot = connection.execute("SELECT * FROM quezo.attempt_questions ORDER BY id").fetchall()
    run_migrations(database.migration_url)
    run_migrations(database.migration_url)
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0008_responses",)
        assert connection.execute("SELECT * FROM quezo.attempt_questions ORDER BY id").fetchall() == snapshot
        assert connection.execute("SELECT revision, selected_option_id, saved_at FROM quezo.attempt_responses").fetchall() == [(0, None, None)] * 2
    attempt = author.get(f"/api/v1/attempts/{attempt_id}", headers=headers(peer))
    assert attempt.status_code == 200
    assert author.put(path(attempt.json()), json=command(attempt.json()["questions"][0]), headers=headers(peer)).status_code == 200


def test_response_migration_rollback(database: IsolatedDatabase) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo.response_commands (probe integer)")
    with pytest.raises(RuntimeError, match="DuplicateTable"):
        run_migrations(database.migration_url)
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0007_attempt_start",)
        assert connection.execute("SELECT to_regclass('quezo.attempt_responses')").fetchone() == (None,)
        connection.execute("DROP TABLE quezo.response_commands")
    run_migrations(database.migration_url)


def test_response_constraints_and_retained_private_ledger(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    run_migrations(database.migration_url)
    attempt = opened(author, database, peer)
    question_id = attempt["questions"][0]["attemptQuestionId"]
    body = command(attempt["questions"][0])
    assert author.put(path(attempt), json=body, headers=headers(peer)).status_code == 200
    for table in ["attempt_responses", "response_commands"]:
        with psycopg.connect(database.web_url) as connection, pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(f"SELECT * FROM quezo.{table}")
        for url, error in [(database.runtime_url, psycopg.errors.InsufficientPrivilege),
                           (database.migration_url, psycopg.errors.CheckViolation)]:
            with psycopg.connect(url) as connection, pytest.raises(error):
                connection.execute(f"DELETE FROM quezo.{table}")
    with psycopg.connect(database.migration_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute("UPDATE quezo.response_commands SET fingerprint = %s", ("b" * 64,))
    for update in ["revision = revision + 2", "selected_option_id = gen_random_uuid(), revision = revision + 1"]:
        with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(f"UPDATE quezo.attempt_responses SET {update}, saved_at = clock_timestamp() WHERE question_id = %s", (question_id,))
    # A valid-looking mutation still cannot commit without its acknowledgement.
    with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.attempt_responses SET revision = revision + 1, saved_at = clock_timestamp() WHERE question_id = %s", (question_id,))
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.attempts SET state = 'finalized' WHERE id = %s", (attempt["id"],))
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute("UPDATE quezo.attempt_responses SET revision = revision + 1, saved_at = clock_timestamp() WHERE question_id = %s", (question_id,))
