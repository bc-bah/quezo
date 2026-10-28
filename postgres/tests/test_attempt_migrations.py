from collections.abc import Iterator
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase, run_migrations
from identity_helpers import SigningPeer
from test_identity_access import identity_client, peer
from test_questions import author
from test_quizzes import composition, create, publish
from test_attempts import assigned, start
from finalization_helpers import prior_schema_lifespan, submit


@pytest.fixture
def database(empty_database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch) -> Iterator[IsolatedDatabase]:
    monkeypatch.setattr("quezo_api.app.expiration_lifespan", prior_schema_lifespan)
    run_migrations(empty_database.migration_url, "0006_quizzes")
    yield empty_database


def test_actual_publication_head_upgrade_preserves_history(author: TestClient, database: IsolatedDatabase) -> None:
    quiz = create(author, composition(author))
    publication = publish(author, quiz).json()
    path = f"/api/v1/quizzes/{quiz['id']}/versions/{publication['versionId']}"
    original = author.get(path).json()
    run_migrations(database.migration_url)
    run_migrations(database.migration_url)
    assert author.get(path).json() == original
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0012_delivery_controls",)
        assert connection.execute("SELECT count(*) FROM quezo.assignments").fetchone() == (0,)


def test_failed_attempt_upgrade_is_atomic(database: IsolatedDatabase) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo.attempts (probe integer)")
    with pytest.raises(RuntimeError, match="DuplicateTable"):
        run_migrations(database.migration_url)
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0006_quizzes",)
        assert connection.execute("SELECT to_regclass('quezo.assignments')").fetchone() == (None,)
        connection.execute("DROP TABLE quezo.attempts")
    run_migrations(database.migration_url)


def test_snapshot_relationships_immutability_and_privileges(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    run_migrations(database.migration_url)
    assignment, request = assigned(author, database)
    attempt = start(author, assignment, peer).json()
    for table in ["assignments", "attempt_questions", "attempt_start_commands"]:
        for url, error in [(database.runtime_url, psycopg.errors.InsufficientPrivilege),
                           (database.migration_url, psycopg.errors.CheckViolation)]:
            with psycopg.connect(url) as connection, pytest.raises(error):
                connection.execute(f"DELETE FROM quezo.{table}")
    for table in ["assignments", "attempts", "attempt_questions", "attempt_start_commands"]:
        with psycopg.connect(database.web_url) as connection, pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(f"SELECT * FROM quezo.{table}")
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute("UPDATE quezo.attempts SET started_at = started_at + interval '1 second'")
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute("UPDATE quezo.assignments SET id = id")
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.UniqueViolation):
        connection.execute(
            "INSERT INTO quezo.assignments (id, quiz_id, version_id, learner_id) VALUES (%s,%s,%s,%s)",
            (uuid4(), request["quizId"], request["versionId"], request["learnerId"]),
        )
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.ForeignKeyViolation):
        connection.execute(
            "INSERT INTO quezo.assignments (id, quiz_id, version_id, learner_id) VALUES (%s,%s,%s,%s)",
            (uuid4(), uuid4(), uuid4(), request["learnerId"]),
        )
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(
            "INSERT INTO quezo.attempt_questions SELECT %s, attempt_id, version_id, question_id, "
            "question_version_id, 3, question, options, effective_points FROM quezo.attempt_questions LIMIT 1", (uuid4(),),
        )
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts WHERE id = %s", (attempt["id"],)).fetchone() == (1,)


def test_one_active_attempt_and_complete_snapshot_constraints(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    run_migrations(database.migration_url)
    assignment, _ = assigned(author, database, {"attemptLimit": 2})
    attempt = start(author, assignment, peer).json()
    copy = (
        "INSERT INTO quezo.attempts (id, assignment_id, learner_id, version_id, attempt_number, "
        "title, instructions, policy, started_at, deadline, possible_points) "
        "SELECT %s, assignment_id, learner_id, version_id, 2, title, instructions, policy, "
        "started_at, deadline, possible_points FROM quezo.attempts WHERE id = %s"
    )
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.UniqueViolation):
        connection.execute(copy, (uuid4(), attempt["id"]))
    assert submit(author, attempt, peer).status_code == 200
    with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(database.runtime_url) as connection:
        connection.execute(copy, (uuid4(), attempt["id"]))
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (1,)
