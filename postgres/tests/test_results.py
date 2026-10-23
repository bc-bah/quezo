from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from itertools import product
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from db_helpers import IsolatedDatabase
from finalization_helpers import submit
from identity_helpers import SigningPeer, seed_account
from quezo_api.modules.questions.service import Connection
from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.modules.results import service
from quezo_api.modules.results.schemas import WithheldResult
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import headers, wait_until_locked
from test_responses import command, opened, path


MODES = ("after_finalization", "after_availability_end", "never")


def result_path(attempt: dict[str, Any]) -> str:
    return f"/api/v1/attempts/{attempt['id']}/result"


@pytest.mark.parametrize(("score", "key", "explanation"), list(product(MODES, repeat=3)))
def test_independent_policies_every_combination_and_boundary(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
    monkeypatch: pytest.MonkeyPatch, score: str, key: str, explanation: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    end = datetime.now(timezone.utc) + timedelta(hours=1)
    attempt = opened(author, database, peer, {
        "availabilityEnd": end.isoformat(), "scoreRelease": score,
        "answerKeyRelease": key, "explanationRelease": explanation,
    })
    assert author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer)).status_code == 200
    completion = submit(author, attempt, peer)
    assert completion.status_code == 200
    assert set(completion.json()) == {"attemptId", "state", "completionReason", "finalizedAt"}
    with psycopg.connect(database.runtime_url) as connection:
        # Closing is not release. No closing UI/endpoint is introduced for this fixture.
        connection.execute("UPDATE quezo.quizzes SET state = 'closed'")
        command_row = connection.execute(
            "SELECT request_id FROM quezo.attempt_start_commands WHERE attempt_id = %s", (attempt["id"],),
        ).fetchone()
        assert command_row is not None
        start_key = str(command_row[0])
    for delta in (-1, 0, 1):
        async def clock(connection: Connection) -> datetime:
            row = await (await connection.execute(
                "SELECT (policy->>'availabilityEnd')::timestamptz FROM quezo.attempts WHERE id = %s",
                (attempt["id"],),
            )).fetchone()
            assert row is not None and isinstance(row[0], datetime)
            return row[0] + timedelta(microseconds=delta)
        # Only the clock sample is controlled; actual DB, authorization, Grade and HTTP serialization.
        monkeypatch.setattr(service, "database_time", clock)
        response = author.get(result_path(attempt), headers=headers(peer))
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        data = response.json()
        assert data["completion"] == completion.json()
        assert datetime.fromisoformat(data["serverTime"]) == end + timedelta(microseconds=delta)
        assert data["versionId"] == attempt["versionId"] and data["attemptNumber"] == 1
        for field, mode in (("score", score), ("answerKey", key), ("explanations", explanation)):
            visible = mode == "after_finalization" or (mode == "after_availability_end" and delta >= 0)
            if not visible:
                assert data[field] == {"status": "withheld"}
            else:
                assert data[field]["status"] == "released"
                if field == "score":
                    assert data[field] == {"status": "released", "earnedPoints": 7, "possiblePoints": 10}
                elif field == "answerKey":
                    items = data[field]["items"]
                    assert [item["outcome"] for item in items] == ["correct", "unanswered"]
                    assert [item["earnedPoints"] for item in items] == [7, 0]
                    assert [item["possiblePoints"] for item in items] == [7, 3]
                    for actual, frozen in zip(items, attempt["questions"], strict=True):
                        assert set(actual) == {
                            "attemptQuestionId", "position", "prompt", "correctOption",
                            "outcome", "earnedPoints", "possiblePoints",
                        }
                        assert actual["attemptQuestionId"] == frozen["attemptQuestionId"]
                        assert actual["correctOption"] == frozen["options"][0]
                else:
                    assert all(item["feedback"] == "Synthetic feedback" for item in data[field]["items"])
                    assert all(set(item) == {"attemptQuestionId", "position", "prompt", "feedback"}
                               for item in data[field]["items"])
        assert not any(field in response.text for field in ("gradeId", "correctOptionId", "defaultPoints", "fingerprint"))
        assert ("feedback" in response.text) == (data["explanations"]["status"] == "released")
        assert ("outcome" in response.text) == (data["answerKey"]["status"] == "released")
        # Confirmation, resume, and start replay are never alternative result channels.
        assert submit(author, attempt, peer).json() == completion.json()
        resume = author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer))
        replay = author.post(f"/api/v1/assignments/{attempt['assignmentId']}/attempts", json={},
                             headers={**headers(peer), "Idempotency-Key": start_key})
        for ordinary in (resume, replay):
            assert ordinary.status_code == 200
            assert not any(field in ordinary.text for field in ("earnedPoints", "correctOption", "feedback", "outcome"))
    assert "Synthetic feedback" not in caplog.text and "Synthetic question" not in caplog.text


@pytest.mark.parametrize("field", ["scoreRelease", "answerKeyRelease", "explanationRelease"])
def test_finite_end_required_and_withheld_rejects_protected_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        QuizPolicy.model_validate({field: "after_availability_end"})
    with pytest.raises(ValueError, match="finite end"):
        service.released("after_availability_end", None, datetime.now(timezone.utc))
    for protected in ("earnedPoints", "possiblePoints", "items", "feedback", "outcome", "correctOption"):
        with pytest.raises(ValidationError):
            WithheldResult.model_validate({"status": "withheld", protected: None})


def test_pre_finalization_ownership_roles_and_zero(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    attempt = opened(author, database, peer)
    seed_account(database, subject="other")
    seed_account(database, subject="admin", roles=("administrator",))
    seed_account(database, subject="author", roles=("author",))
    seed_account(database, subject="author-learner", roles=("author", "learner"))
    url = result_path(attempt)
    for finalized in (False, True):
        own = author.get(url, headers=headers(peer))
        assert own.status_code == (200 if finalized else 409)
        if not finalized:
            assert own.json()["code"] == "INVALID_STATE"
            assert not any(field in own.text for field in ("earnedPoints", "correctOption", "feedback", "outcome"))
        else:
            assert own.json()["score"] == {"status": "released", "earnedPoints": 0, "possiblePoints": 10}
        for subject, status in (("other", 404), ("author-learner", 404), ("admin", 403), ("author", 403)):
            foreign = author.get(url, headers=headers(peer, subject))
            missing = author.get(f"/api/v1/attempts/{uuid4()}/result", headers=headers(peer, subject))
            assert foreign.status_code == missing.status_code == status
            assert {k: v for k, v in foreign.json().items() if k != "requestId"} == {
                k: v for k, v in missing.json().items() if k != "requestId"
            }
            assert foreign.headers["cache-control"] == "private, no-store"
        assert author.get(url, headers={"Authorization": ""}).status_code == 401
        assert submit(author, attempt, peer).status_code == 200


@pytest.mark.parametrize("revocation", ["role", "disabled", "mapping"])
def test_result_rechecks_live_access_after_lock(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, revocation: str,
) -> None:
    attempt = opened(author, database, peer)
    assert submit(author, attempt, peer).status_code == 200
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.attempts WHERE id = %s FOR UPDATE", (attempt["id"],))
            pending = pool.submit(author.get, result_path(attempt), headers=headers(peer))
            wait_until_locked(database)
            owner = "(SELECT learner_id FROM quezo.attempts WHERE id = %s)"
            sql = {
                "role": "DELETE FROM quezo.account_roles WHERE account_id = ",
                "disabled": "UPDATE quezo.accounts SET status = 'disabled' WHERE id = ",
                "mapping": "UPDATE quezo.identity_mappings SET active = false WHERE account_id = ",
            }[revocation]
            lock.execute(sql + owner, (attempt["id"],))
        response = pending.result()
    assert response.status_code == (401 if revocation == "mapping" else 403)
    assert not any(field in response.text for field in ("earnedPoints", "correctOption", "feedback", "outcome"))


@pytest.mark.parametrize("finalize_early", [False, True])
def test_real_clock_release_on_each_read_and_expiry_reconciliation(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, monkeypatch: pytest.MonkeyPatch,
    finalize_early: bool,
) -> None:
    from quezo_api.modules.attempts import expiration
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 3600)
    end = datetime.now(timezone.utc) + timedelta(seconds=4)
    attempt = opened(author, database, peer, {
        "availabilityEnd": end.isoformat(), "scoreRelease": "after_availability_end",
    })
    if finalize_early:
        assert submit(author, attempt, peer).status_code == 200
    before = author.get(result_path(attempt), headers=headers(peer))
    assert before.status_code == (200 if finalize_early else 409)
    if finalize_early:
        assert before.json()["score"] == {"status": "withheld"}
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.attempts WHERE id = %s FOR UPDATE", (attempt["id"],))
            pending = pool.submit(author.get, result_path(attempt), headers=headers(peer))
            wait_until_locked(database)
            lock.execute("SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp()))) + 0.01)", (end,))
        response = pending.result()
    assert response.status_code == 200
    data = response.json()
    assert data["completion"]["completionReason"] == ("submitted" if finalize_early else "expired")
    assert data["score"] == {"status": "released", "earnedPoints": 0, "possiblePoints": 10}
    assert datetime.fromisoformat(data["serverTime"]) >= end
    assert data["answerKey"] == data["explanations"] == {"status": "withheld"}
    again = author.get(result_path(attempt), headers=headers(peer)).json()
    assert again["completion"] == data["completion"]
    assert again["serverTime"] > data["serverTime"]
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.grades").fetchone() == (1,)


def test_result_uses_frozen_questions_policy_and_grade(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    attempt = opened(author, database, peer, {
        "answerKeyRelease": "after_finalization", "explanationRelease": "after_finalization",
    })
    wrong = command(attempt["questions"][0])
    wrong["selectedOptionId"] = attempt["questions"][0]["options"][1]["id"]
    assert author.put(path(attempt), json=wrong, headers=headers(peer)).status_code == 200
    assert submit(author, attempt, peer).status_code == 200
    before = author.get(result_path(attempt), headers=headers(peer)).json()
    question = attempt["questions"][0]
    original = author.get(f"/api/v1/questions/{question['questionId']}/versions/{question['versionId']}").json()
    body = {k: original[k] for k in ("questionType", "prompt", "options", "correctOptionId", "defaultPoints", "feedback")}
    body.update(prompt="Changed bank prompt", feedback="Changed bank feedback", defaultPoints=100,
                correctOptionId=original["options"][1]["id"], expectedRevision=1)
    assert author.patch("/api/v1/questions/" + question["questionId"], json=body).status_code == 200
    with psycopg.connect(database.runtime_url) as connection:
        row = connection.execute(
            "SELECT a.quiz_id FROM quezo.assignments a WHERE a.id = %s", (attempt["assignmentId"],),
        ).fetchone()
        assert row is not None
        quiz_id = str(row[0])
    quiz = author.get("/api/v1/quizzes/" + quiz_id).json()
    assert author.post(f"/api/v1/quizzes/{quiz_id}/drafts", json={"expectedRevision": quiz["draftRevision"]}).status_code == 201
    assert author.patch("/api/v1/quizzes/" + quiz_id, json={
        "expectedRevision": quiz["draftRevision"] + 1, "title": "New title", "instructions": "",
        "questions": [{"questionId": question["questionId"], "versionId": question["versionId"]}],
        "policy": {"scoreRelease": "never", "answerKeyRelease": "never", "explanationRelease": "never"},
    }).status_code == 200
    assert author.post(f"/api/v1/quizzes/{quiz_id}/publish", json={"expectedRevision": quiz["draftRevision"] + 2},
                       headers={"Idempotency-Key": str(uuid4())}).status_code == 201
    after = author.get(result_path(attempt), headers=headers(peer)).json()
    assert {k: v for k, v in before.items() if k != "serverTime"} == {k: v for k, v in after.items() if k != "serverTime"}
    assert [item["outcome"] for item in after["answerKey"]["items"]] == ["incorrect", "unanswered"]
