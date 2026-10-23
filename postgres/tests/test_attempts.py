from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import time
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase
from identity_helpers import SigningPeer, seed_account
from quezo_api.errors import ApiError
from quezo_api.modules.attempts.service import admit
from quezo_api.modules.quizzes.policies import QuizPolicy
from test_identity_access import identity_client, peer
from test_questions import author
from test_quizzes import composition, create, publish


def headers(peer: SigningPeer, subject: str = "learner") -> dict[str, str]:
    return {"Authorization": f"Bearer {peer.token({**peer.claims(), 'sub': subject})}"}


def assigned(
    author: TestClient, database: IsolatedDatabase, policy: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    learner = seed_account(database, subject="learner")
    body = composition(author)
    body["questions"][0]["pointOverride"] = 7
    if policy is not None:
        body["policy"] = policy
    quiz = create(author, body)
    version = publish(author, quiz).json()["versionId"]
    request = {"quizId": quiz["id"], "versionId": version, "learnerId": str(learner)}
    response = author.post("/api/v1/assignments", json=request)
    assert response.status_code == 201
    return dict(response.json()), request


def start(client: TestClient, assignment: dict[str, Any], peer: SigningPeer, key: str | None = None) -> Any:
    return client.post(f"/api/v1/assignments/{assignment['id']}/attempts", json={},
                       headers={**headers(peer), "Idempotency-Key": key or str(uuid4())})


@pytest.mark.parametrize("same_key", [True, False])
def test_parallel_start_duplicate_and_finalized_replay(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, same_key: bool,
) -> None:
    assignment, request = assigned(author, database, {"attemptLimit": 2})
    key = str(uuid4())
    keys = [key, key if same_key else str(uuid4())]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda command: start(author, assignment, peer, command), keys))
    assert sorted(result.status_code for result in results) == [200, 201]
    attempt = results[0].json()
    assert results[1].json() == attempt
    assert attempt["possiblePoints"] == 10 and attempt["deadline"] is None
    assert len({question["attemptQuestionId"] for question in attempt["questions"]}) == 2
    assert all(field not in results[0].text for field in ["correctOptionId", "feedback", "defaultPoints"])
    with ThreadPoolExecutor(max_workers=2) as pool:
        duplicates = list(pool.map(lambda _: author.post("/api/v1/assignments", json=request), range(2)))
    assert all(result.status_code == 200 for result in duplicates)
    assert all(result.json()["attemptsStarted"] == 1 for result in duplicates)
    assert all(result.json()["id"] == assignment["id"] for result in duplicates)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (1,)
    assert author.post(f"/api/v1/attempts/{attempt['id']}/submission", json={}, headers=headers(peer)).status_code == 200
    summary = author.get("/api/v1/assignments/" + assignment["id"], headers=headers(peer)).json()
    assert summary["state"] == "completed_remaining" and summary["attemptsRemaining"] == 1
    next_attempt = start(author, assignment, peer)
    assert next_attempt.status_code == 201 and next_attempt.json()["attemptNumber"] == 2
    for command in keys:
        replay = start(author, assignment, peer, command)
        assert replay.status_code == 200 and replay.json()["id"] == attempt["id"]
        assert replay.json()["state"] == "finalized"
    assert author.post(f"/api/v1/attempts/{next_attempt.json()['id']}/submission", json={}, headers=headers(peer)).status_code == 200
    assert start(author, assignment, peer).json()["code"] == "ATTEMPT_LIMIT_REACHED"
    summary = author.get("/api/v1/assignments/" + assignment["id"], headers=headers(peer)).json()
    assert summary["state"] == "exhausted" and summary["attemptsCompleted"] == 2
    assert author.post("/api/v1/assignments", json=request).json()["attemptsRemaining"] == 0


def test_lookup_disclosure_pagination_and_foreign_ids(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    assignment, request = assigned(author, database)
    other = seed_account(database, subject="other")
    seed_account(database, subject="disabled", status="disabled")
    seed_account(database, subject="inactive", active=False)
    seed_account(database, subject="admin", roles=("administrator",))
    lookup = author.get("/api/v1/eligible-learners?pageSize=1")
    assert lookup.status_code == 200
    assert set(lookup.json()["items"][0]) == {"userId"}
    second = author.get("/api/v1/eligible-learners", params={"cursor": lookup.json()["nextCursor"]}).json()
    assert len(second["items"]) == 1 and second["nextCursor"] is None
    assert {item["userId"] for item in lookup.json()["items"] + second["items"]} == {request["learnerId"], str(other)}
    assert author.get("/api/v1/eligible-learners", headers=headers(peer)).status_code == 403
    seed_account(database, subject="foreign-author", roles=("author",))
    assert author.post("/api/v1/assignments", json=request, headers=headers(peer, "foreign-author")).status_code == 404
    for subject in ["learner", "admin"]:
        assert author.post("/api/v1/assignments", json=request, headers=headers(peer, subject)).status_code == 403
    different_quiz = create(author, {"title": "Different owned quiz"})
    assert author.post("/api/v1/assignments", json={**request, "quizId": different_quiz["id"]}).status_code == 404
    attempt = start(author, assignment, peer).json()
    for subject, status in [("other", 404), ("admin", 403)]:
        for path in ["/api/v1/assignments/" + assignment["id"], "/api/v1/attempts/" + attempt["id"],
                     "/api/v1/assignments?cursor=" + assignment["id"]]:
            assert author.get(path, headers=headers(peer, subject)).status_code == status
        assert author.post(f"/api/v1/assignments/{assignment['id']}/attempts", json={},
                           headers={**headers(peer, subject), "Idempotency-Key": str(uuid4())}).status_code == status
    assert author.get("/api/v1/assignments", headers=headers(peer, "other")).json()["items"] == []
    assert author.post("/api/v1/assignments", json={**request, "learnerId": str(uuid4())}).status_code == 404
    assert author.post("/api/v1/assignments", json={**request, "quizId": str(uuid4())}).status_code == 404
    assert author.post("/api/v1/assignments", json={**request, "ownerId": str(other)}).status_code == 422
    for query in ["pageSize=101", "pageSize=0", "cursor=invalid", "ownerId=secret"]:
        assert author.get("/api/v1/assignments?" + query, headers=headers(peer)).status_code == 422
    listing = author.get("/api/v1/assignments", headers=headers(peer))
    assert listing.headers["cache-control"] == "private, no-store"
    assert all(field not in listing.text for field in ["questions", "options", "correctOptionId", "feedback", "prompt"])
    assert author.get("/api/v1/attempts/" + str(uuid4()), headers=headers(peer)).status_code == 404


def test_concurrent_new_assignment_and_ineligible_recipient(
    author: TestClient, database: IsolatedDatabase,
) -> None:
    learner = seed_account(database, subject="learner")
    quiz = create(author, composition(author))
    version = publish(author, quiz).json()["versionId"]
    request = {"quizId": quiz["id"], "versionId": version, "learnerId": str(learner)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: author.post("/api/v1/assignments", json=request), range(2)))
    assert sorted(result.status_code for result in results) == [200, 201]
    assert results[0].json() == results[1].json()
    disabled = seed_account(database, subject="disabled", status="disabled")
    inactive = seed_account(database, subject="inactive", active=False)
    nonlearner = seed_account(database, subject="admin", roles=("administrator",))
    for recipient in [disabled, inactive, nonlearner]:
        assert author.post("/api/v1/assignments", json={**request, "learnerId": str(recipient)}).status_code == 404


@pytest.mark.parametrize(("random_questions", "random_options"), [(False, False), (True, False), (False, True), (True, True)])
def test_frozen_order_points_policy_and_content(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
    monkeypatch: pytest.MonkeyPatch, random_questions: bool, random_options: bool,
) -> None:
    # Deterministic permutation proves each flag is exercised, not merely a lucky random draw.
    monkeypatch.setattr("quezo_api.modules.attempts.service.SystemRandom.shuffle", lambda self, items: items.reverse())
    assignment, request = assigned(author, database, {
        "randomizeQuestions": random_questions, "randomizeOptions": random_options,
        "durationSeconds": 60, "attemptLimit": None,
    })
    original = author.get(f"/api/v1/quizzes/{request['quizId']}/versions/{request['versionId']}").json()
    response = start(author, assignment, peer)
    assert response.status_code == 201
    attempt = response.json()
    assert datetime.fromisoformat(attempt["deadline"]) - datetime.fromisoformat(attempt["startedAt"]) == timedelta(seconds=60)
    expected = list(original["questions"])
    if random_questions:
        expected.reverse()
    for actual, pinned in zip(attempt["questions"], expected, strict=True):
        options = list(pinned["question"]["options"])
        if random_options:
            options.reverse()
        assert actual["options"] == options and actual["versionId"] == pinned["question"]["versionId"]
        assert actual["effectivePoints"] == pinned["effectivePoints"]
    assert attempt["policy"] == original["policy"]
    for _ in range(2):
        assert author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer)).json() == attempt
        assert start(author, assignment, peer).json() == attempt
    assert author.post(f"/api/v1/quizzes/{request['quizId']}/drafts", json={"expectedRevision": 1}).status_code == 201
    newer = publish(author, {"id": request["quizId"]}, revision=2).json()["versionId"]
    assert newer != request["versionId"]
    assert author.get("/api/v1/assignments", headers=headers(peer)).json()["items"][0]["versionId"] == request["versionId"]
    assert author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer)).json() == attempt
    explicit = author.post("/api/v1/assignments", json={**request, "versionId": newer})
    assert explicit.status_code == 201 and explicit.json()["attemptsStarted"] == 0
    with psycopg.connect(database.runtime_url) as connection:
        private = connection.execute("SELECT question FROM quezo.attempt_questions ORDER BY position").fetchall()
        assert all("correctOptionId" in row[0] and "feedback" in row[0] for row in private)


@pytest.mark.parametrize("offset", [-60, 60])
def test_schedule_and_closed_admission(author: TestClient, database: IsolatedDatabase, peer: SigningPeer, offset: int) -> None:
    bound = (datetime.now(timezone.utc) + timedelta(seconds=offset)).isoformat()
    assignment, request = assigned(author, database, {
        "availabilityEnd" if offset < 0 else "availabilityStart": bound,
    })
    summary = author.get("/api/v1/assignments/" + assignment["id"], headers=headers(peer)).json()
    assert summary["state"] == ("closed" if offset < 0 else "not_yet_available")
    assert start(author, assignment, peer).json()["code"] == "ASSESSMENT_UNAVAILABLE"
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.quizzes SET state = 'closed' WHERE id = %s", (request["quizId"],))
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (0,)
    assert start(author, assignment, peer).status_code == 409


def test_rollback_revoked_replay_and_closed_resume(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    assignment, request = assigned(author, database)
    key = str(uuid4())
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("REVOKE INSERT ON quezo.attempt_start_commands FROM quezo_runtime")
    assert start(author, assignment, peer, key).status_code == 500
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM quezo.attempt_questions").fetchone() == (0,)
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("GRANT INSERT ON quezo.attempt_start_commands TO quezo_runtime")
    attempt = start(author, assignment, peer, key).json()
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.quizzes SET state = 'closed' WHERE id = %s", (request["quizId"],))
    assert start(author, assignment, peer).json() == attempt
    assert start(author, assignment, peer, key).json() == attempt
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("DELETE FROM quezo.account_roles WHERE account_id = %s", (request["learnerId"],))
    assert start(author, assignment, peer, key).status_code == 403
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.accounts SET status = 'disabled' WHERE id = %s", (request["learnerId"],))
    assert start(author, assignment, peer, key).json()["code"] == "ACCOUNT_DISABLED"


def test_waiting_start_rechecks_live_role(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    assignment, request = assigned(author, database)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.assignments WHERE id = %s FOR UPDATE", (assignment["id"],))
            pending = pool.submit(start, author, assignment, peer)
            wait_until_locked(database)
            lock.execute("DELETE FROM quezo.account_roles WHERE account_id = %s", (request["learnerId"],))
        assert pending.result().status_code == 403


def test_waiting_start_uses_post_lock_database_time(author: TestClient, database: IsolatedDatabase, peer: SigningPeer) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=3)
    assignment, _ = assigned(author, database, {"availabilityEnd": end.isoformat()})
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.assignments WHERE id = %s FOR UPDATE", (assignment["id"],))
            pending = pool.submit(start, author, assignment, peer)
            wait_until_locked(database)
            lock.execute("SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp()))) + 0.02)", (end,))
        assert pending.result().json()["code"] == "ASSESSMENT_UNAVAILABLE"
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (0,)


@pytest.mark.parametrize(("duration", "end_seconds"), [(None, 120), (60, 120), (120, 60)])
def test_database_deadline_is_earlier_present_bound(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, duration: int | None, end_seconds: int,
) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=end_seconds)
    assignment, _ = assigned(author, database, {"durationSeconds": duration, "availabilityEnd": end.isoformat()})
    response = start(author, assignment, peer)
    assert response.status_code == 201
    attempt = response.json()
    started = datetime.fromisoformat(attempt["startedAt"])
    expected = end if duration is None else min(end, started + timedelta(seconds=duration))
    assert datetime.fromisoformat(attempt["deadline"]) == expected
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT deadline FROM quezo.attempts WHERE id = %s", (attempt["id"],)).fetchone() == (expected,)


def wait_until_locked(database: IsolatedDatabase) -> None:
    deadline = time.monotonic() + 4
    with psycopg.connect(database.runtime_url, autocommit=True) as connection:
        while time.monotonic() < deadline:
            if connection.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname = current_database() "
                "AND pid <> pg_backend_pid() AND wait_event_type = 'Lock')",
            ).fetchone() == (True,):
                return
            time.sleep(0.01)
    pytest.fail("Start did not wait for the held assignment lock")


def test_fingerprint_and_strict_command(author: TestClient, database: IsolatedDatabase, peer: SigningPeer, monkeypatch: pytest.MonkeyPatch) -> None:
    assignment, _ = assigned(author, database)
    key = str(uuid4())
    assert start(author, assignment, peer, key).status_code == 201
    path = f"/api/v1/assignments/{assignment['id']}/attempts"
    assert author.post(path, json={}, headers=headers(peer)).status_code == 422
    assert author.post(path, json={"allowance": 100}, headers={**headers(peer), "Idempotency-Key": key}).status_code == 422
    # An inconsistent fingerprint must never be accepted, even for an owned retained command.
    monkeypatch.setattr("quezo_api.modules.attempts.service.StartCommand.model_dump", lambda *a, **kw: {"different": True})
    assert start(author, assignment, peer, key).json()["code"] == "IDEMPOTENCY_CONFLICT"
    for suffix in ["/submission", "/result"]:
        assert author.post("/api/v1/attempts/" + str(uuid4()) + suffix, json={}, headers=headers(peer)).status_code == 404
    assert author.post("/api/v1/attempts/" + str(uuid4()) + "/responses/" + str(uuid4()),
                       json={}, headers=headers(peer)).status_code == 405


@pytest.mark.parametrize(("duration", "end_offset", "expected"), [
    (None, None, None), (60, None, 60), (None, 30, 30), (60, 30, 30), (60, 120, 60),
])
def test_exact_admission_and_deadline_bounds(duration: int | None, end_offset: int | None, expected: int | None) -> None:
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    end = now + timedelta(seconds=end_offset) if end_offset is not None else None
    policy = QuizPolicy.model_validate({"durationSeconds": duration, "availabilityStart": now, "availabilityEnd": end})
    assert admit(policy, now) == (None if expected is None else now + timedelta(seconds=expected))
    with pytest.raises(ApiError):
        admit(policy, now - timedelta(microseconds=1))
    if end is not None:
        admit(policy, end - timedelta(microseconds=1))
        with pytest.raises(ApiError):
            admit(policy, end)
