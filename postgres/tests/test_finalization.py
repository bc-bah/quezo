import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
import subprocess
import sys
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from db_helpers import BACKEND, IsolatedDatabase
from finalization_helpers import submit
from identity_helpers import SigningPeer, seed_account
from quezo_api.database import Database, DatabaseSettings
from quezo_api.modules.attempts import expiration, finalization
from quezo_api.modules.questions.service import Connection
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import assigned, headers, start, wait_until_locked
from test_responses import command, opened, path
from test_quizzes import composition, create, publish


@pytest.fixture(autouse=True)
def controlled_worker_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 3600)


def wait_deadline(database: IsolatedDatabase, end: datetime) -> None:
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp()))) + 0.01)", (end,))


def counts(database: IsolatedDatabase) -> tuple[Any, ...]:
    with psycopg.connect(database.runtime_url) as connection:
        row = connection.execute(
            "SELECT (SELECT count(*) FROM quezo.grades), (SELECT count(*) FROM quezo.grade_items), "
            "(SELECT count(*) FROM quezo.attempt_completion_events), "
            "(SELECT count(*) FROM quezo.attempts WHERE state = 'finalized')",
        ).fetchone()
        assert row is not None
        return row


@pytest.mark.parametrize("release", ["never", "after_finalization"])
def test_submit_persisted_only_replay_and_nondisclosure(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, release: str,
) -> None:
    attempt = opened(author, database, peer, {"scoreRelease": release})
    assert author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer)).status_code == 200
    result = submit(author, attempt, peer)
    assert result.status_code == 200 and result.headers["cache-control"] == "private, no-store"
    assert set(result.json()) == {"attemptId", "state", "completionReason", "finalizedAt"}
    assert result.json()["completionReason"] == "submitted"
    assert counts(database) == (1, 2, 1, 1)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT earned_points, possible_points FROM quezo.grades").fetchone() == (7, 10)
        assert connection.execute(
            "SELECT outcome FROM quezo.grade_items i JOIN quezo.attempt_questions q ON q.id = i.question_id ORDER BY q.position",
        ).fetchall() == [("correct",), ("unanswered",)]
    for _ in range(3):
        assert submit(author, attempt, peer).json() == result.json()
    snapshot = author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer))
    assert snapshot.json()["completion"] == result.json()
    assert not any(field in snapshot.text + result.text for field in
                   ["earnedPoints", "correctOptionId", "feedback", "outcome", "gradeId"])
    url = f"/api/v1/attempts/{attempt['id']}/submission"
    for body in [{"responses": []}, {"selectedOptionId": command(attempt["questions"][0])["selectedOptionId"]},
                 {"completionReason": "submitted"}, {"finalizedAt": "2026-01-01T00:00:00Z"}]:
        assert author.post(url, json=body, headers=headers(peer)).status_code == 422
    assert author.post(url, headers=headers(peer)).status_code == 422


@pytest.mark.parametrize("fault", ["insert", "commit", "scoring"])
def test_finalization_rollback(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
    monkeypatch: pytest.MonkeyPatch, fault: str,
) -> None:
    attempt = opened(author, database, peer)
    if fault == "scoring":
        def failed_score(snapshot: object) -> Any:
            raise ValueError("Synthetic invalid snapshot")
        monkeypatch.setattr(finalization, "score", failed_score)
    else:
        with psycopg.connect(database.migration_url) as connection:
            if fault == "insert":
                connection.execute("REVOKE INSERT ON quezo.attempt_completion_events FROM quezo_runtime")
            else:
                connection.execute("""
                    CREATE FUNCTION quezo.fail_completion() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN RAISE EXCEPTION 'Synthetic commit failure' USING ERRCODE = '23514'; END $$;
                    CREATE CONSTRAINT TRIGGER fail_completion AFTER INSERT ON quezo.attempt_completion_events
                        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.fail_completion()
                """)
    result = submit(author, attempt, peer)
    assert result.status_code == 500 and result.json()["code"] == "INTERNAL_ERROR"
    assert counts(database) == (0, 0, 0, 0)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT state, completion_reason, finalized_at FROM quezo.attempts").fetchone() == ("in_progress", None, None)
    if fault == "scoring":
        from quezo_api.modules.scoring import score
        monkeypatch.setattr(finalization, "score", score)
    if fault != "scoring":
        with psycopg.connect(database.migration_url) as connection:
            connection.execute("GRANT INSERT ON quezo.attempt_completion_events TO quezo_runtime")
            if fault == "commit":
                connection.execute("DROP TRIGGER fail_completion ON quezo.attempt_completion_events")
    assert submit(author, attempt, peer).status_code == 200
    assert counts(database) == (1, 2, 1, 1)


@pytest.mark.parametrize("iteration", range(3))
def test_save_submit_race_and_duplicate_submit(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, iteration: int,
) -> None:
    attempt = opened(author, database, peer)
    with ThreadPoolExecutor(max_workers=4) as pool:
        saves = pool.submit(author.put, path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
        submits = [pool.submit(submit, author, attempt, peer) for _ in range(3)]
        saved = saves.result()
        results = [task.result() for task in submits]
    assert saved.status_code in (200, 409)
    assert all(result.status_code == 200 and result.json() == results[0].json() for result in results)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT earned_points FROM quezo.grades").fetchone() == ((7 if saved.status_code == 200 else 0),)
    assert counts(database) == (1, 2, 1, 1)


@pytest.mark.parametrize("revoke", ["role", "disabled", "mapping", "none"])
def test_submit_authority_after_lock(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, revoke: str,
) -> None:
    attempt = opened(author, database, peer)
    seed_account(database, subject="other")
    seed_account(database, subject="admin", roles=("administrator",))
    url = f"/api/v1/attempts/{attempt['id']}/submission"
    assert author.post(url, json={}, headers=headers(peer, "other")).status_code == 404
    assert author.post(url, json={}, headers=headers(peer, "admin")).status_code == 403
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.attempts WHERE id = %s FOR UPDATE", (attempt["id"],))
            pending = pool.submit(submit, author, attempt, peer)
            wait_until_locked(database)
            owner = "(SELECT learner_id FROM quezo.attempts WHERE id = %s)"
            if revoke == "role":
                lock.execute("DELETE FROM quezo.account_roles WHERE account_id = " + owner, (attempt["id"],))
            elif revoke == "disabled":
                lock.execute("UPDATE quezo.accounts SET status = 'disabled' WHERE id = " + owner, (attempt["id"],))
            elif revoke == "mapping":
                lock.execute("UPDATE quezo.identity_mappings SET active = false WHERE account_id = " + owner, (attempt["id"],))
        assert pending.result().status_code == {"role": 403, "disabled": 403, "mapping": 401, "none": 200}[revoke]
    assert counts(database) == ((1, 2, 1, 1) if revoke == "none" else (0, 0, 0, 0))


@pytest.mark.parametrize("trigger", ["read", "save", "submit"])
def test_request_expiry_and_late_answer_rejection(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, trigger: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 3600)
    end = datetime.now(timezone.utc) + timedelta(seconds=3)
    attempt = opened(author, database, peer, {"availabilityEnd": end.isoformat()})
    wait_deadline(database, end)
    if trigger == "save":
        result = author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
        assert result.status_code == 409 and result.json()["details"]["attemptState"] == "finalized"
    elif trigger == "read":
        assert author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer)).json()["completion"]["completionReason"] == "expired"
    else:
        assert submit(author, attempt, peer).json()["completionReason"] == "expired"
    assert counts(database) == (1, 2, 1, 1)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT earned_points, possible_points FROM quezo.grades").fetchone() == (0, 10)
        assert connection.execute("SELECT count(*) FROM quezo.grade_items WHERE outcome = 'unanswered'").fetchone() == (2,)
        assert connection.execute("SELECT max(revision) FROM quezo.attempt_responses").fetchone() == (0,)


def test_exact_database_deadline_admission(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempt = opened(author, database, peer, {"durationSeconds": 60})
    async def exact_clock(connection: Connection) -> datetime:
        row = await (await connection.execute("SELECT deadline FROM quezo.attempts WHERE id = %s", (attempt["id"],))).fetchone()
        assert row is not None and isinstance(row[0], datetime)
        return row[0]
    # Control only the sampled DB wall-clock value to hit equality deterministically.
    monkeypatch.setattr("quezo_api.modules.attempts.responses.database_time", exact_clock)
    result = author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
    assert result.status_code == 409 and result.json()["code"] == "DEADLINE_PASSED"
    completed = submit(author, attempt, peer).json()
    assert completed["completionReason"] == "expired" and completed["finalizedAt"] == attempt["deadline"]
    assert counts(database) == (1, 2, 1, 1)


def test_submit_waits_past_deadline_and_accepted_save_survives(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=4)
    attempt = opened(author, database, peer, {"availabilityEnd": end.isoformat()})
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("""
            CREATE FUNCTION quezo.delay_accepted_save() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                PERFORM pg_sleep(greatest(0, extract(epoch FROM (
                    (SELECT deadline FROM quezo.attempts WHERE id = NEW.attempt_id) - clock_timestamp()))) + 0.02);
                RETURN NEW;
            END $$;
            CREATE TRIGGER delay_accepted_save BEFORE INSERT ON quezo.response_commands
                FOR EACH ROW EXECUTE FUNCTION quezo.delay_accepted_save()
        """)
    with ThreadPoolExecutor(max_workers=2) as pool:
        saved = pool.submit(author.put, path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
        # Observe that save holds the parent before allowing submission to race it.
        with psycopg.connect(database.runtime_url, autocommit=True) as probe:
            import time
            for _ in range(200):
                if probe.execute("SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname=current_database() AND wait_event='PgSleep')").fetchone() == (True,):
                    break
                time.sleep(0.01)
            else:
                pytest.fail("Save did not reach its admitted precommit barrier")
        pending = pool.submit(submit, author, attempt, peer)
        result = saved.result()
        assert result.status_code == 200
        assert datetime.fromisoformat(result.json()["acknowledgement"]["savedAt"]) < end
        assert pending.result().json()["completionReason"] == "expired"
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT earned_points FROM quezo.grades").fetchone() == (7,)


def worker_process(database: IsolatedDatabase) -> subprocess.Popen[str]:
    code = """
import asyncio
from quezo_api.database import Database, DatabaseSettings, database_loop_factory
from quezo_api.modules.attempts.expiration import expire_batch
async def main():
    async with Database(DatabaseSettings.from_env()) as db:
        print(await expire_batch(db))
with asyncio.Runner(loop_factory=database_loop_factory) as runner:
    runner.run(main())
"""
    return subprocess.Popen([sys.executable, "-c", code], env={
        **os.environ, "QUEZO_DATABASE_URL": database.runtime_url, "PYTHONPATH": str(BACKEND / "src"),
    },
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


@pytest.mark.parametrize("iteration", range(3))
def test_multiple_process_workers_submit_save_and_restart(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, monkeypatch: pytest.MonkeyPatch,
    iteration: int,
) -> None:
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 3600)
    end = datetime.now(timezone.utc) + timedelta(seconds=3)
    attempt = opened(author, database, peer, {"availabilityEnd": end.isoformat()})
    wait_deadline(database, end)
    workers = [worker_process(database) for _ in range(2)]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            done = pool.submit(submit, author, attempt, peer)
            late = pool.submit(author.put, path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
            assert done.result().json()["completionReason"] == "expired"
            assert late.result().status_code == 409
        for process in workers:
            stdout, stderr = process.communicate(timeout=20)
            assert process.returncode == 0, stderr
            assert stdout.strip() in ("0", "1")
    finally:
        for process in workers:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
    assert counts(database) == (1, 2, 1, 1)
    assert submit(author, attempt, peer).status_code == 200


@pytest.mark.anyio
async def test_worker_bounded_skip_locked_startup_and_cancellation(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 3600)
    end = datetime.now(timezone.utc) + timedelta(seconds=4)
    assignment, request = assigned(author, database, {"availabilityEnd": end.isoformat()})
    attempts = [start(author, assignment, peer).json()]
    for subject in ("worker-learner-2", "worker-learner-3"):
        learner_id = seed_account(database, subject=subject)
        other = author.post("/api/v1/assignments", json={**request, "learnerId": str(learner_id)}).json()
        result = author.post(f"/api/v1/assignments/{other['id']}/attempts", json={},
                            headers={**headers(peer, subject), "Idempotency-Key": str(uuid4())})
        assert result.status_code == 201
        attempts.append(result.json())
    wait_deadline(database, end)
    monkeypatch.setattr(expiration, "BATCH_SIZE", 1)
    settings = DatabaseSettings(url=SecretStr(database.runtime_url), pool_max=1)
    with psycopg.connect(database.runtime_url) as held:
        held.execute("SELECT id FROM quezo.attempts WHERE id = %s FOR UPDATE", (attempts[0]["id"],))
        async with Database(settings) as db:
            assert await expiration.expire_batch(db) == 1
            assert await expiration.expire_batch(db) == 1
            assert await expiration.expire_batch(db) == 0
    # A fresh lifecycle immediately catches the remaining overdue attempt.
    async with Database(settings) as db:
        async with expiration.expiration_lifespan(db):
            assert counts(database) == (3, 6, 3, 3)
        assert not any(t.get_name() == "quezo-expiration" and not t.done() for t in asyncio.all_tasks())


@pytest.mark.anyio
async def test_worker_failure_is_explicit_and_cancel_rolls_back(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 3600)
    end = datetime.now(timezone.utc) + timedelta(seconds=3)
    attempt = opened(author, database, peer, {"availabilityEnd": end.isoformat()})
    wait_deadline(database, end)
    entered = asyncio.Event()
    original = finalization.finalize_locked
    async def pause(connection: Connection, locked: dict[str, Any], now: datetime) -> Any:
        result = await original(connection, locked, now)
        entered.set()
        await asyncio.Event().wait()
        return result
    monkeypatch.setattr(expiration, "finalize_locked", pause)
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        task = asyncio.create_task(expiration.expire_batch(db))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert counts(database) == (0, 0, 0, 0)
        monkeypatch.setattr(expiration, "finalize_locked", original)
        with psycopg.connect(database.migration_url) as connection:
            connection.execute("REVOKE SELECT ON quezo.attempts FROM quezo_runtime")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            async with expiration.expiration_lifespan(db):
                pytest.fail("Unavailable schema must fail startup")
        with psycopg.connect(database.migration_url) as connection:
            connection.execute("GRANT SELECT ON quezo.attempts TO quezo_runtime")
        assert await expiration.expire_batch(db) == 1
    assert submit(author, attempt, peer).json()["completionReason"] == "expired"


@pytest.mark.anyio
async def test_periodic_worker_logs_dependency_failure_and_recovers_on_next_tick(
    database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 0.01)
    tick = asyncio.Event()
    calls = 0
    original = expiration.expire_batch
    async def unavailable_once(db: Database) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise psycopg.OperationalError("private connection details")
        count = await original(db)
        tick.set()
        return count
    monkeypatch.setattr(expiration, "expire_batch", unavailable_once)
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        task = asyncio.create_task(expiration.run_worker(db))
        try:
            await asyncio.wait_for(tick.wait(), 5)
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    assert "DEPENDENCY_UNAVAILABLE" in caplog.text and "private connection details" not in caplog.text


def test_scoring_adapter_wrong_and_zero_point_correct_items(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    learner = seed_account(database, subject="learner")
    body = composition(author, points=0)
    body["questions"][0]["pointOverride"] = 7
    quiz = create(author, body)
    version = publish(author, quiz).json()["versionId"]
    assignment = author.post("/api/v1/assignments", json={
        "quizId": quiz["id"], "versionId": version, "learnerId": str(learner),
    }).json()
    attempt = start(author, assignment, peer).json()
    wrong = {**command(attempt["questions"][0]), "selectedOptionId": attempt["questions"][0]["options"][1]["id"]}
    assert author.put(path(attempt), json=wrong, headers=headers(peer)).status_code == 200
    assert author.put(path(attempt, 1), json=command(attempt["questions"][1]), headers=headers(peer)).status_code == 200
    assert submit(author, attempt, peer).status_code == 200
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT earned_points, possible_points FROM quezo.grades").fetchone() == (0, 7)
        assert connection.execute(
            "SELECT i.outcome, i.earned_points, i.possible_points FROM quezo.grade_items i "
            "JOIN quezo.attempt_questions q ON q.id=i.question_id ORDER BY q.position",
        ).fetchall() == [("incorrect", 0, 7), ("correct", 0, 0)]


def test_predeadline_submission_can_commit_after_deadline(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=3)
    attempt = opened(author, database, peer, {"availabilityEnd": end.isoformat()})
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("""
            CREATE FUNCTION quezo.delay_grade() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                PERFORM pg_sleep(greatest(0, extract(epoch FROM (
                    (SELECT deadline FROM quezo.attempts WHERE id = NEW.attempt_id) - clock_timestamp()))) + 0.02);
                RETURN NEW;
            END $$;
            CREATE TRIGGER delay_grade BEFORE INSERT ON quezo.grades
                FOR EACH ROW EXECUTE FUNCTION quezo.delay_grade()
        """)
    result = submit(author, attempt, peer)
    assert result.status_code == 200 and result.json()["completionReason"] == "submitted"
    assert datetime.fromisoformat(result.json()["finalizedAt"]) < end
    assert datetime.now(timezone.utc) >= end
    assert submit(author, attempt, peer).json() == result.json()
