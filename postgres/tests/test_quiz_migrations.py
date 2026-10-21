from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from db_helpers import IsolatedDatabase, run_migrations
from question_helpers import content
from test_identity_access import identity_client, peer
from test_question_migrations import insert_question, seed_bank
from test_questions import author
from test_quizzes import composition, create, publish


def test_actual_question_head_upgrade_preserves_content(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0005_questions")
    owner, bank = seed_bank(empty_database)
    with psycopg.connect(empty_database.runtime_url) as connection:
        question, version = insert_question(connection, owner, bank, content())
        before = connection.execute("SELECT row_to_json(v) FROM quezo.question_versions v").fetchone()
    run_migrations(empty_database.migration_url)
    run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0006_quizzes",)
        assert connection.execute("SELECT row_to_json(v) FROM quezo.question_versions v").fetchone() == before
        assert connection.execute("SELECT id FROM quezo.questions").fetchone() == (question,)
        assert connection.execute("SELECT id FROM quezo.question_versions").fetchone() == (version,)


def test_failed_quiz_upgrade_is_atomic(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0005_questions")
    with psycopg.connect(empty_database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo.quizzes (probe integer)")
    with pytest.raises(RuntimeError, match="DuplicateTable"):
        run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0005_questions",)
        assert connection.execute("SELECT to_regprocedure('quezo.quiz_policy_valid(jsonb)')").fetchone() == (None,)
        assert connection.execute("SELECT to_regclass('quezo.quiz_versions')").fetchone() == (None,)
        connection.execute("DROP TABLE quezo.quizzes")
    run_migrations(empty_database.migration_url)


def test_published_rows_commands_and_events_are_immutable(author: TestClient, database: IsolatedDatabase) -> None:
    quiz = create(author, composition(author))
    assert publish(author, quiz).status_code == 201
    for table in ["quiz_versions", "quiz_questions", "quiz_publication_commands", "quiz_publication_events"]:
        for url, error in [(database.runtime_url, psycopg.errors.InsufficientPrivilege),
                           (database.migration_url, psycopg.errors.CheckViolation)]:
            for statement in [f"DELETE FROM quezo.{table}", f"UPDATE quezo.{table} SET owner_id = owner_id"
                              if table in ("quiz_versions", "quiz_questions")
                              else f"UPDATE quezo.{table} SET actor_id = actor_id"]:
                with psycopg.connect(url) as connection, pytest.raises(error):
                    connection.execute(statement)
        with psycopg.connect(database.web_url) as connection, pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(f"SELECT * FROM quezo.{table}")
    with pytest.raises(psycopg.IntegrityError), psycopg.connect(database.runtime_url) as connection:
        connection.execute("DELETE FROM quezo.quizzes WHERE id = %s", (quiz["id"],))
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute(
            "INSERT INTO quezo.quiz_questions SELECT quiz_version_id, owner_id, question_id, "
            "question_version_id, 3, question, point_override, effective_points FROM quezo.quiz_questions LIMIT 1")


@pytest.mark.parametrize("change", [
    {"durationSeconds": 59}, {"durationSeconds": 604801}, {"durationSeconds": True},
    {"durationSeconds": 60.5}, {"durationSeconds": "60"},
    {"attemptLimit": 0}, {"attemptLimit": 101}, {"randomizeQuestions": "false"},
    {"scoreRelease": "after_availability_end"}, {"explanationRelease": None}, {"timeZone": "Not/AZone"},
    {"availabilityStart": "2026-10-22T00:00:00Z", "availabilityEnd": "2026-10-21T00:00:00Z"},
])
def test_database_rejects_policy_independently(
    author: TestClient, database: IsolatedDatabase, change: dict[str, Any],
) -> None:
    quiz = create(author, {"title": "Policy"})
    draft = quiz["draft"]
    draft["policy"].update(change)
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute("UPDATE quezo.quizzes SET draft = %s WHERE id = %s", (Jsonb(draft), quiz["id"]))


def test_incomplete_publication_cannot_commit(author: TestClient, database: IsolatedDatabase) -> None:
    quiz = create(author, {"title": "Incomplete"})
    with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(database.runtime_url) as connection:
        connection.execute(
            "INSERT INTO quezo.quiz_versions (id, quiz_id, owner_id, draft_revision, title, instructions, policy, possible_points) "
            "SELECT %s, id, owner_id, 1, title, '', draft->'policy', 1 FROM quezo.quizzes WHERE id = %s",
            (uuid4(), quiz["id"]),
        )
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.quiz_versions").fetchone() == (0,)
