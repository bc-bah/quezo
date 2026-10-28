from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase
from finalization_helpers import submit
from identity_helpers import SigningPeer
from quezo_api.errors import ApiError
from quezo_api.modules.attempts.schemas import StartCommand
from quezo_api.modules.attempts.service import admit
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import assigned, headers, wait_until_locked
from quezo_api.modules.quizzes.policies import QuizPolicy
from test_quizzes import publish
from test_responses import command, path
from quezo_api.modules.quizzes.service import learner_preview
from quezo_api.modules.quizzes.schemas import PublishedQuestion


CHOICES: list[dict[str, Any]] = [
    {}, {"timingChoice": "adjusted", "adjustedDurationSeconds": 6048000}, {"timingChoice": "off"},
]


def send(client: TestClient, assignment: dict[str, Any], peer: SigningPeer,
         body: dict[str, Any], key: str | None = None) -> Any:
    return client.post(f"/api/v1/assignments/{assignment['id']}/attempts", json=body,
                       headers={**headers(peer), "Idempotency-Key": key or str(uuid4())})


@pytest.mark.parametrize("body", CHOICES)
def test_exact_timing_and_start_cutoff(body: dict[str, Any]) -> None:
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    end = now + timedelta(seconds=1)
    policy = QuizPolicy.model_validate({
        "durationSeconds": 604800, "availabilityStart": now, "availabilityEnd": end,
    })
    choice = StartCommand.model_validate(body)
    expected = {"standard": end, "adjusted": now + timedelta(seconds=6048000), "off": None}
    assert admit(policy, now, choice) == expected[choice.timing_choice]
    with pytest.raises(ApiError):
        admit(policy, now - timedelta(microseconds=1), choice)
    admit(policy, end - timedelta(microseconds=1), choice)
    with pytest.raises(ApiError):
        admit(policy, end, choice)


@pytest.mark.parametrize("body", [
    {"timingChoice": "extension"}, {"timing_choice": "off"},
    {"timingChoice": "adjusted"}, {"timingChoice": "adjusted", "adjustedDurationSeconds": None},
    *[{"timingChoice": "adjusted", "adjustedDurationSeconds": value}
      for value in (59, 6048001, True, 60.0, "60")],
    {"timingChoice": "off", "adjustedDurationSeconds": 60},
    {"timingChoice": "standard", "adjustedDurationSeconds": 60},
    {"deadline": "2099-01-01T00:00:00Z"},
])
def test_invalid_server_choices(author: TestClient, database: IsolatedDatabase,
                                peer: SigningPeer, body: dict[str, Any]) -> None:
    assignment, _ = assigned(author, database)
    assert send(author, assignment, peer, body).status_code == 422
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (0,)


@pytest.mark.parametrize("body", CHOICES)
def test_near_end_and_close_are_not_adjusted_expiry(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, body: dict[str, Any],
) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=3)
    assignment, request = assigned(author, database, {
        "durationSeconds": 604800, "availabilityEnd": end.isoformat(), "attemptLimit": 1,
        "scoreRelease": "after_availability_end", "answerKeyRelease": "never",
        "explanationRelease": "after_availability_end",
    })
    result = send(author, assignment, peer, body)
    assert result.status_code == 201
    attempt = result.json()
    choice = body.get("timingChoice", "standard")
    assert attempt["timingChoice"] == choice
    assert attempt["policy"]["durationSeconds"] == 604800
    expected = end if choice == "standard" else (
        datetime.fromisoformat(attempt["startedAt"]) + timedelta(seconds=6048000) if choice == "adjusted" else None)
    assert (datetime.fromisoformat(attempt["deadline"]) if attempt["deadline"] else None) == expected
    # Closing neither expires an attempt nor releases an active attempt's answers.
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.quizzes SET state='closed' WHERE id=%s", (request["quizId"],))
    assert author.get(f"/api/v1/attempts/{attempt['id']}/result", headers=headers(peer)).status_code == 409
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp()))) + 0.02)", (end,))
    read = author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer))
    assert read.json()["state"] == ("finalized" if choice == "standard" else "in_progress")
    if choice != "standard":
        assert author.get(f"/api/v1/attempts/{attempt['id']}/result", headers=headers(peer)).status_code == 409
        assert author.put(path(attempt), json=command(attempt["questions"][0]), headers=headers(peer)).status_code == 200
    completion = submit(author, attempt, peer)
    assert completion.json()["completionReason"] == ("expired" if choice == "standard" else "submitted")
    released = author.get(f"/api/v1/attempts/{attempt['id']}/result", headers=headers(peer)).json()
    assert released["score"]["status"] == released["explanations"]["status"] == "released"
    assert released["answerKey"] == {"status": "withheld"}
    assert "correctOption" not in json.dumps(released)
    for ordinary in (read, send(author, assignment, peer, body)):
        assert not any(field in ordinary.text for field in ("feedback", "correctOption", "earnedPoints"))
    assert send(author, assignment, peer, body).json()["code"] == "ASSESSMENT_UNAVAILABLE"


@pytest.mark.parametrize("duration", [None, 60])
def test_off_without_availability_has_no_deadline(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, duration: int | None,
) -> None:
    assignment, _ = assigned(author, database, {"durationSeconds": duration})
    result = send(author, assignment, peer, {"timingChoice": "off"})
    assert result.status_code == 201 and result.json()["deadline"] is None
    assert result.json()["timingChoice"] == "off"


@pytest.mark.parametrize("body", CHOICES)
def test_queued_cutoff_every_mode(author: TestClient, database: IsolatedDatabase,
                                 peer: SigningPeer, body: dict[str, Any]) -> None:
    end = datetime.now(timezone.utc) + timedelta(seconds=3)
    assignment, _ = assigned(author, database, {"availabilityEnd": end.isoformat()})
    with ThreadPoolExecutor(max_workers=1) as pool:
        with psycopg.connect(database.runtime_url) as lock:
            lock.execute("SELECT id FROM quezo.assignments WHERE id=%s FOR UPDATE", (assignment["id"],))
            pending = pool.submit(send, author, assignment, peer, body)
            wait_until_locked(database)
            lock.execute("SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp()))) + 0.02)", (end,))
        assert pending.result().json()["code"] == "ASSESSMENT_UNAVAILABLE"


@pytest.mark.parametrize("body", CHOICES)
def test_concurrent_choices_resume_replay_and_limit(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, body: dict[str, Any],
) -> None:
    assignment, _ = assigned(author, database, {"durationSeconds": 60, "attemptLimit": 1})
    keys = [str(uuid4()), str(uuid4())]
    alternatives = [body, {"timingChoice": "adjusted", "adjustedDurationSeconds": 60}]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda i: send(author, assignment, peer, alternatives[i], keys[i]), range(2)))
    assert sorted(result.status_code for result in results) == [200, 201]
    frozen = results[0].json()
    assert results[1].json() == frozen
    for i in range(2):
        assert send(author, assignment, peer, alternatives[i], keys[i]).json() == frozen
    assert send(author, assignment, peer, {"timingChoice": "off"}).json() == frozen
    changed = {"timingChoice": "off"} if body != {"timingChoice": "off"} else {}
    assert send(author, assignment, peer, changed, keys[0]).json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert submit(author, frozen, peer).status_code == 200
    with ThreadPoolExecutor(max_workers=2) as pool:
        denied = list(pool.map(lambda b: send(author, assignment, peer, b), alternatives))
    assert all(result.json()["code"] == "ATTEMPT_LIMIT_REACHED" for result in denied)
    replay = send(author, assignment, peer, body, keys[0]).json()
    assert replay["timingChoice"] == frozen["timingChoice"] and replay["deadline"] == frozen["deadline"]
    for update in ("timing_choice='off'", "adjusted_duration_seconds=120", "deadline=NULL"):
        # A no-op is legal; use a guaranteed change for nullable deadlines.
        if update == "deadline=NULL" and frozen["deadline"] is None:
            update = "deadline=started_at + interval '1 minute'"
        if update == "timing_choice='off'" and frozen["timingChoice"] == "off":
            update = "timing_choice='standard'"
        with psycopg.connect(database.runtime_url) as connection, pytest.raises(psycopg.errors.CheckViolation):
            connection.execute("UPDATE quezo.attempts SET " + update)


def test_policy_revision_only_explicit_new_assignment_and_preview(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    assignment, request = assigned(author, database, {"durationSeconds": 60})
    before = send(author, assignment, peer, {}).json()
    base = "/api/v1/quizzes/" + request["quizId"]
    draft = author.post(base + "/drafts", json={"expectedRevision": 1}).json()
    body = draft["draft"]
    body["policy"] = {
        "durationSeconds": 604800, "attemptLimit": None, "timeZone": "America/New_York",
        "availabilityStart": "2026-11-01T05:30:00Z", "availabilityEnd": "2026-11-01T06:30:00Z",
        "randomizeQuestions": True, "randomizeOptions": True,
        "scoreRelease": "never", "answerKeyRelease": "after_finalization",
        "explanationRelease": "after_availability_end",
    }
    assert author.patch(base, json={**body, "expectedRevision": 2}).status_code == 200
    preview = author.post(base + "/preview", json={"expectedRevision": 3})
    assert preview.status_code == 200
    assert not any(field in preview.text for field in ("correctOption", "feedback", "defaultPoints"))
    version = publish(author, {"id": request["quizId"]}, revision=3).json()["versionId"]
    assert author.get("/api/v1/assignments/" + assignment["id"], headers=headers(peer)).json()["versionId"] == request["versionId"]
    assert send(author, assignment, peer, {"timingChoice": "off"}).json() == before
    new = author.post("/api/v1/assignments", json={**request, "versionId": version}).json()
    assert new["id"] != assignment["id"]
    assert new["attemptsRemaining"] is None and new["durationSeconds"] == 604800
    assert new["timeZone"] == "America/New_York"
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM quezo.grades").fetchone() == (0,)


@pytest.mark.parametrize("questions", [False, True])
@pytest.mark.parametrize("options", [False, True])
def test_preview_independent_order_flags(
    author: TestClient, database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch,
    questions: bool, options: bool,
) -> None:
    assignment, request = assigned(author, database)
    publication = author.get(
        f"/api/v1/quizzes/{request['quizId']}/versions/{request['versionId']}",
    ).json()
    monkeypatch.setattr("quezo_api.modules.quizzes.service.SystemRandom.sample",
                        lambda self, population, k: list(reversed(population)))
    items = [PublishedQuestion.model_validate(item) for item in publication["questions"]]
    preview = learner_preview("Preview", "", items, QuizPolicy.model_validate({
        "randomizeQuestions": questions, "randomizeOptions": options,
    }))
    expected = list(reversed(items)) if questions else items
    for actual, source in zip(preview.questions, expected, strict=True):
        assert actual.prompt == source.question.prompt
        assert actual.options == (list(reversed(source.question.options)) if options else source.question.options)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.attempts").fetchone() == (0,)


@pytest.mark.parametrize(("choice", "seconds", "deadline"), [
    ("unknown", None, "NULL"), ("off", 60, "NULL"),
    ("adjusted", None, "NULL"), ("adjusted", 59, "started_at + interval '59 seconds'"),
    ("adjusted", 6048001, "started_at + interval '6048001 seconds'"),
    ("off", None, "started_at + interval '60 seconds'"),
    ("adjusted", 60, "NULL"),
])
def test_database_rejects_invalid_timing_snapshots(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
    choice: str, seconds: int | None, deadline: str,
) -> None:
    assignment, _ = assigned(author, database, {"attemptLimit": None})
    attempt = send(author, assignment, peer, {}).json()
    assert submit(author, attempt, peer).status_code == 200
    with psycopg.connect(database.runtime_url) as connection:
        with pytest.raises(psycopg.errors.CheckViolation):
            connection.execute(
                "INSERT INTO quezo.attempts (id, assignment_id, learner_id, version_id, attempt_number, "
                "title, instructions, policy, started_at, deadline, possible_points, timing_choice, adjusted_duration_seconds) "
                "SELECT gen_random_uuid(), assignment_id, learner_id, version_id, 2, title, instructions, policy, "
                f"started_at, {deadline}, possible_points, %s, %s FROM quezo.attempts WHERE id=%s",
                (choice, seconds, attempt["id"]),
            )
