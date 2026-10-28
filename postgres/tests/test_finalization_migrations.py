from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase, run_migrations
from finalization_helpers import prior_schema_lifespan, submit, legacy_opened
from identity_helpers import SigningPeer
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import headers
from test_responses import command, path

opened = legacy_opened


@pytest.fixture
def database(empty_database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch) -> Iterator[IsolatedDatabase]:
    run_migrations(empty_database.migration_url, "0008_responses")
    monkeypatch.setattr("quezo_api.app.expiration_lifespan", prior_schema_lifespan)
    yield empty_database


def test_actual_response_head_upgrade_preserves_accepted_saves(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    attempt = opened(author, database, peer)
    body = command(attempt["questions"][0])
    first = author.put(path(attempt), json=body, headers=headers(peer))
    assert first.status_code == 200
    with psycopg.connect(database.runtime_url) as connection:
        responses = connection.execute("SELECT * FROM quezo.attempt_responses ORDER BY question_id").fetchall()
        ledger = connection.execute("SELECT * FROM quezo.response_commands").fetchall()
    run_migrations(database.migration_url)
    run_migrations(database.migration_url)
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0012_delivery_controls",)
        assert connection.execute("SELECT * FROM quezo.attempt_responses ORDER BY question_id").fetchall() == responses
        assert connection.execute("SELECT * FROM quezo.response_commands").fetchall() == ledger
        assert connection.execute("SELECT count(*) FROM quezo.grades").fetchone() == (0,)
    assert submit(author, attempt, peer).status_code == 200
    assert author.put(path(attempt), json=body, headers=headers(peer)).json()["acknowledgement"] == first.json()["acknowledgement"]


def test_failed_finalization_upgrade_is_atomic(database: IsolatedDatabase) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo.grades (probe integer)")
    with pytest.raises(RuntimeError, match="DuplicateTable"):
        run_migrations(database.migration_url)
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0008_responses",)
        assert connection.execute("SELECT count(*) FROM information_schema.columns WHERE table_schema='quezo' AND table_name='attempts' AND column_name='finalized_at'").fetchone() == (0,)
        connection.execute("DROP TABLE quezo.grades")
    run_migrations(database.migration_url)


def test_no_fabricated_grade_for_preexisting_terminal_fixture(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    attempt = opened(author, database, peer)
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.attempts SET state='expired' WHERE id=%s", (attempt["id"],))
    with pytest.raises(RuntimeError, match="Ungraded terminal fixtures"):
        run_migrations(database.migration_url)
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0008_responses",)


def test_grade_and_completion_are_unique_immutable_and_atomic(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    run_migrations(database.migration_url)
    attempt = opened(author, database, peer)
    with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.attempts SET state='finalized', completion_reason='submitted', finalized_at=clock_timestamp() WHERE id=%s", (attempt["id"],))
    with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(database.runtime_url) as connection:
        connection.execute("INSERT INTO quezo.grades VALUES (gen_random_uuid(), %s, 0, 10)", (attempt["id"],))
    assert submit(author, attempt, peer).status_code == 200
    for table in ("grades", "grade_items", "attempt_completion_events"):
        with psycopg.connect(database.web_url) as connection, pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(f"SELECT * FROM quezo.{table}")
        for statement in (f"DELETE FROM quezo.{table}", f"UPDATE quezo.{table} SET attempt_id=attempt_id"):
            for url, error in ((database.runtime_url, psycopg.errors.InsufficientPrivilege),
                               (database.migration_url, psycopg.errors.CheckViolation)):
                with psycopg.connect(url) as connection, pytest.raises(error):
                    connection.execute(statement)
    for update in ("state='in_progress', completion_reason=NULL, finalized_at=NULL",
                   "completion_reason='expired'", "finalized_at=clock_timestamp()"):
        with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
            connection.execute("UPDATE quezo.attempts SET " + update)
    with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
        connection.execute("INSERT INTO quezo.grades SELECT gen_random_uuid(), attempt_id, earned_points, possible_points FROM quezo.grades")
