from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase
from identity_helpers import SigningPeer, seed_account
from quezo_api.errors import ApiError
from quezo_api.modules.attempts.responses import admit_save
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import assigned, headers, start, wait_until_locked


def opened(author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
           policy: dict[str, Any] | None = None) -> dict[str, Any]:
    assignment, _ = assigned(author, database, policy)
    result = start(author, assignment, peer)
    assert result.status_code == 201
    return dict(result.json())


def command(question: dict[str, Any], revision: int = 0) -> dict[str, Any]:
    return {"requestId": str(uuid4()), "expectedRevision": revision, "selectedOptionId": question["options"][0]["id"]}


def path(attempt: dict[str, Any], index: int = 0) -> str:
    return f"/api/v1/attempts/{attempt['id']}/responses/{attempt['questions'][index]['attemptQuestionId']}"


def test_save_clear_replay_stale_and_lost_ack(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    attempt = opened(author, database, peer)
    assert all(q["response"] == {"selectedOptionId": None, "revision": 0, "savedAt": None} for q in attempt["questions"])
    body = command(attempt["questions"][0])
    first = author.put(path(attempt), json=body, headers=headers(peer))
    assert first.status_code == 200
    assert first.headers["cache-control"] == "private, no-store"
    ack = first.json()["acknowledgement"]
    assert set(ack) == {"requestId", "responseRevision", "savedAt"} and ack["responseRevision"] == 1
    # Discarding the acknowledgement and reading/replaying uses persisted state, not process memory.
    snapshot = author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer))
    assert snapshot.json()["questions"][0]["response"] == {
        "selectedOptionId": body["selectedOptionId"], "revision": 1, "savedAt": ack["savedAt"],
    }
    assert not any(key in snapshot.text + first.text for key in ["correctOptionId", "feedback", "defaultPoints", "fingerprint"])
    replay = author.put(path(attempt), json=body, headers=headers(peer)).json()
    assert replay["acknowledgement"] == ack
    assert replay["serverTime"] >= first.json()["serverTime"]
    clear = {**command(attempt["questions"][0], 1), "selectedOptionId": None}
    assert author.put(path(attempt), json=clear, headers=headers(peer)).json()["acknowledgement"]["responseRevision"] == 2
    stale = author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
    assert stale.status_code == 409 and stale.json()["code"] == "RESPONSE_REVISION_CONFLICT"
    assert stale.json()["details"]["currentRevision"] == 2 and stale.json()["details"]["selectedOptionId"] is None
    assert author.put(path(attempt), json=body, headers=headers(peer)).json()["acknowledgement"] == ack
    for changed in [{**body, "selectedOptionId": None}, {**body, "expectedRevision": 2}]:
        assert author.put(path(attempt), json=changed, headers=headers(peer)).json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert author.put(path(attempt, 1), json=body, headers=headers(peer)).json()["code"] == "IDEMPOTENCY_CONFLICT"
    # UUID spelling normalizes before fingerprinting.
    normalized = {**body, "requestId": body["requestId"].upper(), "selectedOptionId": body["selectedOptionId"].upper()}
    assert author.put(path(attempt), json=normalized, headers=headers(peer)).json()["acknowledgement"] == ack
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.response_commands").fetchone() == (2,)


@pytest.mark.parametrize("same_key", [False, True])
def test_concurrent_response_cas(author: TestClient, database: IsolatedDatabase, peer: SigningPeer, same_key: bool) -> None:
    attempt = opened(author, database, peer)
    body = command(attempt["questions"][0])
    other = body if same_key else {**body, "requestId": str(uuid4()), "selectedOptionId": None}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda b: author.put(path(attempt), json=b, headers=headers(peer)), [body, other]))
    assert sorted(r.status_code for r in results) == ([200, 200] if same_key else [200, 409])
    if same_key:
        assert results[0].json()["acknowledgement"] == results[1].json()["acknowledgement"]
    else:
        conflict = next(r for r in results if r.status_code == 409).json()
        assert conflict["code"] == "RESPONSE_REVISION_CONFLICT" and conflict["details"]["currentRevision"] == 1
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.response_commands").fetchone() == (1,)
        assert connection.execute("SELECT max(revision) FROM quezo.attempt_responses").fetchone() == (1,)


def test_rollback_including_deferred_commit_failure(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    attempt = opened(author, database, peer)
    body = command(attempt["questions"][0])
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("REVOKE INSERT ON quezo.response_commands FROM quezo_runtime")
    assert author.put(path(attempt), json=body, headers=headers(peer)).status_code == 500
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT max(revision) FROM quezo.attempt_responses").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM quezo.response_commands").fetchone() == (0,)
        connection.execute("GRANT INSERT ON quezo.response_commands TO quezo_runtime")
        connection.execute("""
            CREATE FUNCTION quezo.fail_save_commit() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'Synthetic commit failure' USING ERRCODE = '23514'; END $$;
            CREATE CONSTRAINT TRIGGER fail_save_commit AFTER INSERT ON quezo.response_commands
                DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION quezo.fail_save_commit()
        """)
    assert author.put(path(attempt), json=body, headers=headers(peer)).status_code == 500
    with psycopg.connect(database.migration_url) as connection:
        assert connection.execute("SELECT max(revision) FROM quezo.attempt_responses").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM quezo.response_commands").fetchone() == (0,)
        connection.execute("DROP TRIGGER fail_save_commit ON quezo.response_commands")
    assert author.put(path(attempt), json=body, headers=headers(peer)).json()["acknowledgement"]["responseRevision"] == 1


@pytest.mark.parametrize("terminal", ["finalized", "expired"])
def test_terminal_replay_is_ack_only_and_live_authorized(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, terminal: str,
) -> None:
    attempt = opened(author, database, peer)
    body = command(attempt["questions"][0])
    ack = author.put(path(attempt), json=body, headers=headers(peer)).json()["acknowledgement"]
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.attempts SET state = %s WHERE id = %s", (terminal, attempt["id"]))
    replay = author.put(path(attempt), json=body, headers=headers(peer)).json()
    assert replay["acknowledgement"] == ack and replay["attemptState"] == terminal
    rejected = author.put(path(attempt), json=command(attempt["questions"][0], 1), headers=headers(peer))
    assert rejected.json()["code"] == "ATTEMPT_FINALIZED"
    assert rejected.json()["details"]["attemptState"] == terminal
    seed_account(database, subject="other")
    seed_account(database, subject="admin", roles=("administrator",))
    assert author.put(path(attempt), json=body, headers=headers(peer, "other")).status_code == 404
    assert author.put(path(attempt), json=body, headers=headers(peer, "admin")).status_code == 403
    assert author.put(path(attempt), json=body, headers={"Authorization": "Bearer invalid"}).status_code == 401
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("DELETE FROM quezo.account_roles WHERE account_id = (SELECT learner_id FROM quezo.attempts WHERE id = %s)", (attempt["id"],))
    assert author.put(path(attempt), json=body, headers=headers(peer)).status_code == 403
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.accounts SET status = 'disabled' WHERE id = (SELECT learner_id FROM quezo.attempts WHERE id = %s)", (attempt["id"],))
    assert author.put(path(attempt), json=body, headers=headers(peer)).json()["code"] == "ACCOUNT_DISABLED"


@pytest.mark.parametrize("change", [
    {"expectedRevision": True}, {"expectedRevision": "0"}, {"expectedRevision": -1},
    {"expectedRevision": 1.5}, {"expectedRevision": 9007199254740992},
    {"selectedOptionId": ""}, {"selectedOptionId": 42}, {"selectedOptionId": False},
    {"requestId": "invalid"}, {"unknown": "private-input"},
])
def test_strict_save_input(author: TestClient, database: IsolatedDatabase, peer: SigningPeer, change: dict[str, Any]) -> None:
    attempt = opened(author, database, peer)
    response = author.put(path(attempt), json={**command(attempt["questions"][0]), **change}, headers=headers(peer))
    assert response.status_code == 422 and "private-input" not in response.text


def test_missing_clear_foreign_option_and_question(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    attempt = opened(author, database, peer)
    body = command(attempt["questions"][0])
    for field in body:
        incomplete = {k: v for k, v in body.items() if k != field}
        assert author.put(path(attempt), json=incomplete, headers=headers(peer)).status_code == 422
    for option in [str(uuid4()), attempt["questions"][1]["options"][0]["id"]]:
        assert author.put(path(attempt), json={**body, "selectedOptionId": option}, headers=headers(peer)).status_code == 422
    assert author.put(f"/api/v1/attempts/{attempt['id']}/responses/{uuid4()}", json=body, headers=headers(peer)).status_code == 404
    assert author.put(f"/api/v1/attempts/{uuid4()}/responses/{attempt['questions'][0]['attemptQuestionId']}", json=body, headers=headers(peer)).status_code == 404
    assert author.put(path(attempt, 1), json=command(attempt["questions"][1]), headers=headers(peer)).status_code == 200


def test_post_lock_deadline_and_ack_after_expiry(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=4)
    attempt = opened(author, database, peer, {"availabilityEnd": end.isoformat()})
    body = command(attempt["questions"][0])
    ack = author.put(path(attempt), json=body, headers=headers(peer)).json()["acknowledgement"]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.attempts WHERE id = %s FOR UPDATE", (attempt["id"],))
            pending = pool.submit(author.put, path(attempt), json=command(attempt["questions"][0], 1), headers=headers(peer))
            wait_until_locked(database)
            lock.execute("SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp()))) + 0.02)", (end,))
        rejection = pending.result().json()
    assert rejection["code"] == "DEADLINE_PASSED" and rejection["details"]["deadline"] == attempt["deadline"]
    assert datetime.fromisoformat(rejection["details"]["serverTime"]) >= end
    replay = author.put(path(attempt), json=body, headers=headers(peer)).json()
    assert replay["acknowledgement"] == ack and replay["attemptState"] == "in_progress"
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.response_commands").fetchone() == (1,)


def test_predeadline_admission_can_commit_after_deadline(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=4)
    attempt = opened(author, database, peer, {"availabilityEnd": end.isoformat()})
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("""
            CREATE FUNCTION quezo.delay_save() RETURNS trigger LANGUAGE plpgsql AS $$
            DECLARE d timestamptz;
            BEGIN
                SELECT deadline INTO d FROM quezo.attempts WHERE id = NEW.attempt_id;
                PERFORM pg_sleep(greatest(0, extract(epoch FROM (d - clock_timestamp()))) + 0.02);
                RETURN NEW;
            END $$;
            CREATE TRIGGER delay_save BEFORE INSERT ON quezo.response_commands
                FOR EACH ROW EXECUTE FUNCTION quezo.delay_save()
        """)
    result = author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
    assert result.status_code == 200
    assert datetime.fromisoformat(result.json()["acknowledgement"]["savedAt"]) < end
    assert datetime.now(timezone.utc) >= end


@pytest.mark.parametrize("revoke", [True, False])
def test_queued_save_rechecks_authority_and_state(author: TestClient, database: IsolatedDatabase, peer: SigningPeer, revoke: bool) -> None:
    attempt = opened(author, database, peer)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.attempts WHERE id = %s FOR UPDATE", (attempt["id"],))
            pending = pool.submit(author.put, path(attempt), json=command(attempt["questions"][0]), headers=headers(peer))
            wait_until_locked(database)
            if revoke:
                lock.execute("DELETE FROM quezo.account_roles WHERE account_id = (SELECT learner_id FROM quezo.attempts WHERE id = %s)", (attempt["id"],))
            else:
                lock.execute("UPDATE quezo.attempts SET state = 'finalized' WHERE id = %s", (attempt["id"],))
        assert pending.result().json()["code"] == ("FORBIDDEN" if revoke else "ATTEMPT_FINALIZED")
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT max(revision) FROM quezo.attempt_responses").fetchone() == (0,)


def test_exact_save_boundary() -> None:
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    admit_save("in_progress", None, now)
    admit_save("in_progress", now, now - timedelta(microseconds=1))
    for instant in [now, now + timedelta(microseconds=1)]:
        with pytest.raises(ApiError) as error:
            admit_save("in_progress", now, instant)
        assert error.value.code == "DEADLINE_PASSED"
