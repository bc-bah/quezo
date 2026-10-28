from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase, run_migrations
from finalization_helpers import legacy_opened, prior_schema_lifespan, submit
from identity_helpers import SigningPeer
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import headers
from test_delivery_controls import send
from test_responses import command, path


@pytest.fixture
def database(empty_database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch) -> Iterator[IsolatedDatabase]:
    monkeypatch.setattr("quezo_api.app.expiration_lifespan", prior_schema_lifespan)
    run_migrations(empty_database.migration_url, "0011_account_administration")
    yield empty_database


@pytest.mark.parametrize("finalized", [False, True])
@pytest.mark.parametrize("duration", [None, 604800])
def test_post_a01_upgrade_preserves_history_and_old_fingerprint(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, finalized: bool, duration: int | None,
) -> None:
    attempt = legacy_opened(author, database, peer, {"durationSeconds": duration})
    assert author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer)).status_code == 200
    if finalized:
        assert submit(author, attempt, peer).status_code == 200
    with psycopg.connect(database.runtime_url) as connection:
        original = connection.execute("SELECT to_jsonb(t) FROM quezo.attempts t").fetchone()
        responses = connection.execute("SELECT * FROM quezo.attempt_responses ORDER BY question_id").fetchall()
        ledger = connection.execute("SELECT * FROM quezo.attempt_start_commands").fetchall()
    run_migrations(database.migration_url)
    run_migrations(database.migration_url)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute(
            "SELECT to_jsonb(t) - ARRAY['timing_choice','adjusted_duration_seconds'] FROM quezo.attempts t",
        ).fetchone() == original
        assert connection.execute("SELECT * FROM quezo.attempt_responses ORDER BY question_id").fetchall() == responses
        assert connection.execute("SELECT * FROM quezo.attempt_start_commands").fetchall() == ledger
    read = author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer))
    assert read.status_code == 200 and read.json()["timingChoice"] == "standard"
    assert (read.json()["deadline"] is None) == (duration is None)
    assert send(author, {"id": attempt["assignmentId"]}, peer, {}, attempt["startKey"]).json() == read.json()
    if not finalized:
        assert send(author, {"id": attempt["assignmentId"]}, peer, {"timingChoice": "off"}).json() == read.json()


def test_failed_upgrade_is_atomic(database: IsolatedDatabase) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("ALTER TABLE quezo.attempts ADD COLUMN adjusted_duration_seconds integer")
    with pytest.raises(RuntimeError, match="DuplicateColumn"):
        run_migrations(database.migration_url)
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0011_account_administration",)
        assert connection.execute(
            "SELECT count(*) FROM information_schema.columns WHERE table_schema='quezo' "
            "AND table_name='attempts' AND column_name='timing_choice'",
        ).fetchone() == (0,)
        connection.execute("ALTER TABLE quezo.attempts DROP COLUMN adjusted_duration_seconds")
    run_migrations(database.migration_url)
