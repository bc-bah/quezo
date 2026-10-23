from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase
from identity_helpers import SigningPeer, seed_account
from question_helpers import content
from test_identity_access import identity_client, peer
from test_questions import author, create_bank


def composition(client: TestClient, *, points: int = 3) -> dict[str, Any]:
    bank = create_bank(client)
    items = []
    for kind in ["mcq", "true_false"]:
        response = client.post("/api/v1/questions", json={**content(kind), "bankId": bank, "defaultPoints": points})
        assert response.status_code == 201
        items.append({"questionId": response.json()["questionId"], "versionId": response.json()["versionId"]})
    return {"title": "Synthetic quiz", "instructions": "Choose one", "questions": items}


def create(client: TestClient, body: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/api/v1/quizzes", json=body)
    assert response.status_code == 201
    return dict(response.json())


def publish(client: TestClient, quiz: dict[str, Any], key: str | None = None, revision: int = 1) -> Any:
    return client.post(f"/api/v1/quizzes/{quiz['id']}/publish",
                       json={"expectedRevision": revision}, headers={"Idempotency-Key": key or str(uuid4())})


def test_reuse_preview_publication_and_immutable_revisions(author: TestClient, database: IsolatedDatabase) -> None:
    body = composition(author)
    body["questions"][0]["pointOverride"] = 7
    quiz = create(author, body)
    other = create(author, body)
    path = f"/api/v1/quizzes/{quiz['id']}"
    with psycopg.connect(database.runtime_url) as connection:
        before = connection.execute("SELECT row_to_json(q) FROM quezo.quizzes q ORDER BY id").fetchall()
    preview = author.post(path + "/preview", json={"expectedRevision": 1})
    assert preview.status_code == 200
    assert preview.json()["possiblePoints"] == 10
    assert preview.headers["cache-control"] == "private, no-store"
    assert all(field not in preview.text for field in ["correctOptionId", "feedback", "defaultPoints", "versionId"])
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT row_to_json(q) FROM quezo.quizzes q ORDER BY id").fetchall() == before
        for table in ["quiz_versions", "quiz_questions", "quiz_publication_commands", "quiz_publication_events"]:
            assert connection.execute(f"SELECT count(*) FROM quezo.{table}").fetchone() == (0,)
        for table in ["assignments", "attempts"]:
            assert connection.execute(f"SELECT count(*) FROM quezo.{table}").fetchone() == (0,)
        for table in ["grades"]:
            assert connection.execute(f"SELECT count(*) FROM quezo.{table}").fetchone() == (0,)
    key = str(uuid4())
    acknowledgement = publish(author, quiz, key)
    assert acknowledgement.status_code == 201
    with psycopg.connect(database.runtime_url) as connection:
        event = connection.execute(
            "SELECT correlation_id FROM quezo.quiz_publication_events WHERE quiz_id = %s", (quiz["id"],),
        ).fetchone()
        assert event is not None and str(event[0]) == acknowledgement.headers["x-request-id"]
    version_path = path + "/versions/" + acknowledgement.json()["versionId"]
    snapshot = author.get(version_path).json()
    assert snapshot["possiblePoints"] == 10
    assert [item["effectivePoints"] for item in snapshot["questions"]] == [7, 3]
    assert [item["question"]["versionId"] for item in snapshot["questions"]] == [item["versionId"] for item in body["questions"]]
    assert publish(author, other).status_code == 201
    assert author.patch(path, json={**body, "expectedRevision": 1}).json()["code"] == "INVALID_STATE"
    revised = author.post(path + "/drafts", json={"expectedRevision": 1})
    assert revised.status_code == 201
    assert revised.json()["state"] == "published" and revised.json()["draftRevision"] == 2
    assert author.post(path + "/drafts", json={"expectedRevision": 2}).status_code == 409
    original_question = snapshot["questions"][0]["question"]
    updated_content = {k: original_question[k] for k in content()}
    assert author.patch(f"/api/v1/questions/{original_question['questionId']}", json={
        **updated_content, "prompt": "New content", "defaultPoints": 100, "expectedRevision": 1,
    }).status_code == 200
    body.update(title="Next publication", policy={"scoreRelease": "never"})
    assert author.patch(path, json={**body, "expectedRevision": 2}).status_code == 200
    second = publish(author, quiz, revision=3)
    assert second.status_code == 201
    assert second.json()["versionId"] != acknowledgement.json()["versionId"]
    latest = author.get(path + "/versions/" + second.json()["versionId"]).json()
    assert latest["questions"] == snapshot["questions"]
    assert latest["policy"]["scoreRelease"] == "never"
    assert author.get(version_path).json() == snapshot
    replay = publish(author, quiz, key)
    assert replay.status_code == 200 and replay.json() == acknowledgement.json()
    assert publish(author, quiz, key, revision=3).json()["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_publish_one_snapshot_and_ledger(
    author: TestClient, database: IsolatedDatabase, same_key: bool,
) -> None:
    quiz = create(author, composition(author))
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: publish(author, quiz, key if same_key else None), range(2)))
    assert sorted(r.status_code for r in responses) == ([200, 201] if same_key else [201, 409])
    if same_key:
        assert responses[0].json() == responses[1].json()
    with psycopg.connect(database.runtime_url) as connection:
        for table in ["quiz_versions", "quiz_publication_commands", "quiz_publication_events"]:
            assert connection.execute(f"SELECT count(*) FROM quezo.{table}").fetchone() == (1,)


def test_draft_cas_and_edit_publish_race(author: TestClient) -> None:
    body = composition(author)
    quiz = create(author, body)
    path = f"/api/v1/quizzes/{quiz['id']}"
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(
            lambda _: author.patch(path, json={**body, "expectedRevision": 1}), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert publish(author, quiz).json()["code"] == "DRAFT_REVISION_CONFLICT"
    with ThreadPoolExecutor(max_workers=2) as executor:
        edit = executor.submit(author.patch, path, json={**body, "title": "Racing", "expectedRevision": 2})
        publication = executor.submit(publish, author, quiz, None, 2)
        results = [edit.result(), publication.result()]
    assert sum(r.status_code < 300 for r in results) == 1
    assert sum(r.status_code == 409 for r in results) == 1


def test_owner_nested_and_role_checks_before_replay(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    body = composition(author)
    quiz = create(author, body)
    path = f"/api/v1/quizzes/{quiz['id']}"
    key = str(uuid4())
    ack = publish(author, quiz, key).json()
    seed_account(database, roles=("author",), subject="other")
    author.headers["Authorization"] = f"Bearer {peer.token({**peer.claims(), 'sub': 'other'})}"
    own = create(author, {"title": "Own"})
    for url in [path, path + "/versions/" + ack["versionId"], "/api/v1/quizzes?cursor=" + quiz["id"],
                f"/api/v1/quizzes/{own['id']}/versions/{ack['versionId']}"]:
        assert author.get(url).status_code == 404
    assert author.post("/api/v1/quizzes", json=body).status_code == 404
    assert publish(author, quiz, key).status_code == 404
    assert author.patch(path, json={**body, "expectedRevision": 1}).status_code == 404
    assert author.post(path + "/preview", json={"expectedRevision": 1}).status_code == 404
    assert [q["id"] for q in author.get("/api/v1/quizzes").json()["items"]] == [own["id"]]
    for role in ["learner", "administrator"]:
        seed_account(database, roles=(role,), subject=role)
        author.headers["Authorization"] = f"Bearer {peer.token({**peer.claims(), 'sub': role})}"
        assert publish(author, quiz, key).status_code == 403
        assert author.get(path).status_code == 403
        assert author.post(path + "/preview", json={"expectedRevision": 1}).status_code == 403
    author.headers["Authorization"] = f"Bearer {peer.token()}"
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("DELETE FROM quezo.account_roles WHERE role = 'author'")
    assert publish(author, quiz, key).status_code == 403
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.accounts SET status = 'disabled'")
    assert publish(author, quiz, key).json()["code"] == "ACCOUNT_DISABLED"
    del author.headers["Authorization"]
    assert publish(author, quiz, key).status_code == 401


def test_validation_failure_rollback_and_unsupported_commands(author: TestClient, database: IsolatedDatabase) -> None:
    body = composition(author, points=0)
    quiz = create(author, body)
    assert publish(author, quiz).status_code == 422
    assert publish(author, create(author, {"title": "Empty"})).status_code == 422
    assert author.post("/api/v1/quizzes", json={**body, "questions": body["questions"] * 2}).status_code == 422
    wrong = {**body["questions"][0], "versionId": body["questions"][1]["versionId"]}
    assert author.post("/api/v1/quizzes", json={**body, "questions": [wrong]}).status_code == 404
    body["questions"][0]["pointOverride"] = 1
    valid = create(author, body)
    path = f"/api/v1/quizzes/{valid['id']}"
    for command in ["close", "archive", "reopen", "start", "submission"]:
        assert author.post(path + "/" + command, json={}).status_code == 404
    for header in [{}, {"Idempotency-Key": "invalid"}]:
        assert author.post(path + "/publish", json={"expectedRevision": 1}, headers=header).status_code == 422
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("REVOKE INSERT ON quezo.quiz_publication_events FROM quezo_runtime")
    key = str(uuid4())
    assert publish(author, valid, key).status_code == 500
    assert author.get(path).json()["state"] == "draft"
    with psycopg.connect(database.runtime_url) as connection:
        for table in ["quiz_versions", "quiz_questions", "quiz_publication_commands", "quiz_publication_events"]:
            assert connection.execute(f"SELECT count(*) FROM quezo.{table}").fetchone() == (0,)
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("GRANT INSERT ON quezo.quiz_publication_events TO quezo_runtime")
    assert publish(author, valid, key).status_code == 201


@pytest.mark.parametrize("policy", [
    {"durationSeconds": None, "attemptLimit": None, "scoreRelease": "never"},
    {"durationSeconds": 60, "attemptLimit": 1, "randomizeQuestions": True, "randomizeOptions": True},
    {"durationSeconds": 604800, "attemptLimit": 100, "availabilityStart": "2026-10-21T00:00:00Z",
     "availabilityEnd": "2026-10-22T00:00:00Z", "timeZone": "America/New_York",
     "scoreRelease": "after_availability_end", "answerKeyRelease": "after_finalization",
     "explanationRelease": "never"},
    {"availabilityEnd": "2026-10-22T00:00:00Z", "scoreRelease": "never",
     "answerKeyRelease": "after_availability_end", "explanationRelease": "after_availability_end"},
])
def test_backend_policy_snapshots(author: TestClient, policy: dict[str, Any]) -> None:
    quiz = create(author, {**composition(author), "policy": policy})
    preview = author.post(f"/api/v1/quizzes/{quiz['id']}/preview", json={"expectedRevision": 1})
    assert preview.status_code == 200
    assert sorted(item["questionType"] for item in preview.json()["questions"]) == ["mcq", "true_false"]
    assert [item["position"] for item in preview.json()["questions"]] == [1, 2]
    assert all(field not in preview.text for field in ["correctOptionId", "feedback"])
    ack = publish(author, quiz)
    assert ack.status_code == 201
    snapshot = author.get(f"/api/v1/quizzes/{quiz['id']}/versions/{ack.json()['versionId']}").json()
    for name, value in policy.items():
        assert snapshot["policy"][name] == value


def test_maximum_publication_and_bounded_pagination(author: TestClient) -> None:
    bank = create_bank(author)
    selections = []
    for _ in range(200):
        question = author.post("/api/v1/questions", json={**content(), "bankId": bank, "defaultPoints": 10000})
        assert question.status_code == 201
        selections.append({"questionId": question.json()["questionId"], "versionId": question.json()["versionId"]})
    quiz = create(author, {"title": "t" * 200, "instructions": "i" * 10000, "questions": selections})
    response = publish(author, quiz)
    assert response.status_code == 201
    snapshot = author.get(f"/api/v1/quizzes/{quiz['id']}/versions/{response.json()['versionId']}").json()
    assert snapshot["possiblePoints"] == 2000000 and len(snapshot["questions"]) == 200
    ids = sorted([quiz["id"]] + [create(author, {"title": "Small"})["id"] for _ in range(2)])
    first = author.get("/api/v1/quizzes?pageSize=2").json()
    assert [q["id"] for q in first["items"]] == ids[:2]
    last = author.get("/api/v1/quizzes", params={"cursor": first["nextCursor"]}).json()
    assert [q["id"] for q in last["items"]] == ids[2:] and last["nextCursor"] is None
    for query in ["pageSize=101", "pageSize=0", "cursor=invalid", "ownerId=secret"]:
        assert author.get("/api/v1/quizzes?" + query).status_code == 422


def test_closed_state_rejects_new_writes_but_retains_ack(author: TestClient, database: IsolatedDatabase) -> None:
    body = composition(author)
    quiz = create(author, body)
    key = str(uuid4())
    ack = publish(author, quiz, key).json()
    path = f"/api/v1/quizzes/{quiz['id']}"
    assert author.post(path + "/drafts", json={"expectedRevision": 1}).status_code == 201
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.quizzes SET state = 'closed' WHERE id = %s", (quiz["id"],))
    assert author.patch(path, json={**body, "expectedRevision": 2}).json()["code"] == "INVALID_STATE"
    assert publish(author, quiz, revision=2).json()["code"] == "INVALID_STATE"
    assert author.post(path + "/drafts", json={"expectedRevision": 2}).json()["code"] == "INVALID_STATE"
    assert publish(author, quiz, key).json() == ack
