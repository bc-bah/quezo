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


def create_bank(client: TestClient) -> str:
    response = client.post("/api/v1/question-banks", json={"name": "Synthetic bank"})
    assert response.status_code == 201
    return str(response.json()["id"])


@pytest.fixture
def author(database: IsolatedDatabase, identity_client: TestClient, peer: SigningPeer) -> TestClient:
    seed_account(database, roles=("author",))
    identity_client.headers["Authorization"] = f"Bearer {peer.token()}"
    return identity_client


@pytest.mark.parametrize("kind", ["mcq", "true_false"])
def test_roundtrip_versions_and_stale_edit(author: TestClient, kind: str) -> None:
    bank = create_bank(author)
    body = content(kind)
    created = author.post("/api/v1/questions", json={**body, "bankId": bank})
    assert created.status_code == 201
    initial = created.json()
    question = f"/api/v1/questions/{initial['questionId']}"
    assert initial["revision"] == 1
    assert initial["bankId"] == bank
    for field, value in body.items():
        assert initial[field] == value
    options = [
        {**option, "text": "Changed choice" if index == 0 else option["text"]}
        for index, option in enumerate(body["options"])
    ] if kind == "mcq" else list(reversed(body["options"]))
    changed = {**body, "prompt": "Changed prompt", "feedback": "Changed feedback", "options": options,
               "defaultPoints": 0, "correctOptionId": body["options"][1]["id"], "expectedRevision": 1}
    edited = author.patch(question, json=changed)
    assert edited.status_code == 200
    latest = edited.json()
    assert latest["revision"] == 2
    assert latest["questionId"] == initial["questionId"]
    assert latest["versionId"] != initial["versionId"]
    assert latest["options"] == options
    assert {option["id"] for option in latest["options"]} == {option["id"] for option in initial["options"]}
    exact = author.get(f"{question}/versions/{initial['versionId']}")
    assert exact.json() == initial
    assert author.get(question).json() == latest
    assert exact.headers["cache-control"] == "private, no-store"
    conflict = author.patch(question, json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "DRAFT_REVISION_CONFLICT"
    assert author.get(question).json() == latest
    history = author.get(question + "/versions?pageSize=1").json()
    assert history["items"][0]["versionId"] == initial["versionId"]
    assert history["nextCursor"] == initial["versionId"]
    rest = author.get(question + "/versions", params={"cursor": history["nextCursor"]}).json()
    assert [item["versionId"] for item in rest["items"]] == [latest["versionId"]]
    assert rest["nextCursor"] is None


def test_owner_scoped_lists_direct_and_nested_ids(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    bank = create_bank(author)
    original = author.post("/api/v1/questions", json={**content(), "bankId": bank}).json()
    qid, vid = original["questionId"], original["versionId"]
    seed_account(database, roles=("author",), subject="author-b")
    author.headers["Authorization"] = f"Bearer {peer.token({**peer.claims(), 'sub': 'author-b'})}"
    own_bank = create_bank(author)
    own = author.post("/api/v1/questions", json={**content(), "bankId": own_bank}).json()
    assert [item["id"] for item in author.get("/api/v1/question-banks").json()["items"]] == [own_bank]
    assert [item["questionId"] for item in author.get("/api/v1/questions").json()["items"]] == [own["questionId"]]
    for path in [
        f"/question-banks/{bank}", f"/question-banks?cursor={bank}",
        f"/questions?bankId={bank}", f"/questions?cursor={qid}", f"/questions/{qid}",
        f"/questions/{qid}/versions", f"/questions/{qid}/versions/{vid}",
        f"/questions/{own['questionId']}/versions/{vid}",
        f"/questions/{own['questionId']}/versions?cursor={vid}",
    ]:
        response = author.get("/api/v1" + path)
        assert response.status_code == 404
        assert original["prompt"] not in response.text
    assert author.patch(f"/api/v1/question-banks/{bank}", json={"name": "Denied"}).status_code == 404
    assert author.post("/api/v1/questions", json={**content(), "bankId": bank}).status_code == 404
    assert author.patch(f"/api/v1/questions/{qid}", json={**content(), "expectedRevision": 1}).status_code == 404


@pytest.mark.parametrize("role", ["administrator", "learner"])
def test_non_author_denied_without_key_exposure(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, role: str,
) -> None:
    bank = create_bank(author)
    question = author.post("/api/v1/questions", json={**content(), "bankId": bank}).json()
    seed_account(database, roles=(role,), subject=role)
    author.headers["Authorization"] = f"Bearer {peer.token({**peer.claims(), 'sub': role})}"
    for path in ["/question-banks", f"/question-banks/{bank}", "/questions",
                 f"/questions/{question['questionId']}",
                 f"/questions/{question['questionId']}/versions",
                 f"/questions/{question['questionId']}/versions/{question['versionId']}"]:
        response = author.get("/api/v1" + path)
        assert response.status_code == 403
        assert "correctOptionId" not in response.text
    assert author.post("/api/v1/question-banks", json={"name": "Denied"}).status_code == 403
    assert author.post("/api/v1/questions", json={**content(), "bankId": bank}).status_code == 403
    assert author.patch(f"/api/v1/questions/{question['questionId']}",
                        json={**content(), "expectedRevision": 1}).status_code == 403


def test_live_revocation_and_transaction_rollback(author: TestClient, database: IsolatedDatabase) -> None:
    bank = create_bank(author)
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("DELETE FROM quezo.account_roles WHERE role = 'author'")
    assert author.post("/api/v1/questions", json={**content(), "bankId": bank}).status_code == 403
    assert author.get("/api/v1/question-banks").status_code == 403
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.questions").fetchone() == (0,)
        connection.execute("UPDATE quezo.accounts SET status = 'disabled'")
    assert author.post("/api/v1/question-banks", json={"name": "Denied"}).json()["code"] == "ACCOUNT_DISABLED"


def test_concurrent_edits_create_one_revision(author: TestClient) -> None:
    body = content()
    initial = author.post("/api/v1/questions", json={**body, "bankId": create_bank(author)}).json()
    path = f"/api/v1/questions/{initial['questionId']}"
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda _: author.patch(path, json={**body, "expectedRevision": 1}), range(2),
        ))
    assert sorted(result.status_code for result in results) == [200, 409]
    assert len(author.get(path + "/versions").json()["items"]) == 2


@pytest.mark.parametrize("kind", ["mcq", "true_false"])
@pytest.mark.parametrize("maximum", [False, True])
def test_http_database_content_boundaries(author: TestClient, kind: str, maximum: bool) -> None:
    body = content(kind)
    body.update(prompt="\U0001f642" * (4000 if maximum else 1),
                feedback="f" * (4000 if maximum else 0), defaultPoints=10000 if maximum else 0)
    if kind == "mcq":
        body["options"] = [
            {"id": str(uuid4()), "text": "o" * (1000 if maximum else 1)}
            for _ in range(10 if maximum else 2)
        ]
        body["correctOptionId"] = body["options"][-1]["id"]
    response = author.post("/api/v1/questions", json={**body, "bankId": create_bank(author)})
    assert response.status_code == 201
    for key, value in body.items():
        assert response.json()[key] == value


@pytest.mark.parametrize("change", [
    {"defaultPoints": True}, {"defaultPoints": 10001}, {"defaultPoints": 1.1},
    {"prompt": "p" * 4001}, {"feedback": "f" * 4001}, {"prompt": " \n\t"},
    {"questionType": "essay"}, {"options": []}, {"correctOptionId": str(uuid4())},
    {"createdAt": "2026-10-21T00:00:00Z"}, {"ownerId": str(uuid4())},
])
def test_invalid_http_writes_leave_no_rows(
    author: TestClient, database: IsolatedDatabase, change: dict[str, Any],
) -> None:
    response = author.post("/api/v1/questions", json={**content(), "bankId": create_bank(author), **change})
    assert response.status_code == 422
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.questions").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM quezo.question_versions").fetchone() == (0,)


def test_failed_version_insert_rolls_back_identity_before_response(
    author: TestClient, database: IsolatedDatabase,
) -> None:
    bank = create_bank(author)
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("REVOKE INSERT ON quezo.question_versions FROM quezo_runtime")
    response = author.post("/api/v1/questions", json={**content(), "bankId": bank})
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.questions").fetchone() == (0,)


def test_pagination_bank_edit_and_strict_http(author: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    banks = sorted(create_bank(author) for _ in range(3))
    page = author.get("/api/v1/question-banks?pageSize=2").json()
    assert [item["id"] for item in page["items"]] == banks[:2]
    assert page["nextCursor"] == banks[1]
    assert author.get("/api/v1/question-banks", params={"cursor": banks[1]}).json() == {
        "items": [{"id": banks[2], "name": "Synthetic bank"}], "nextCursor": None,
    }
    assert author.patch(f"/api/v1/question-banks/{banks[0]}", json={"name": "Renamed"}).status_code == 200
    assert author.get(f"/api/v1/question-banks/{banks[0]}").json()["name"] == "Renamed"
    ids = []
    for _ in range(3):
        response = author.post("/api/v1/questions", json={**content(), "bankId": banks[0]})
        ids.append(response.json()["questionId"])
    ids.sort()
    page = author.get("/api/v1/questions", params={"bankId": banks[0], "pageSize": 2}).json()
    assert [item["questionId"] for item in page["items"]] == ids[:2]
    rest = author.get("/api/v1/questions", params={"bankId": banks[0], "cursor": page["nextCursor"]}).json()
    assert [item["questionId"] for item in rest["items"]] == ids[2:]
    assert rest["nextCursor"] is None
    for query in ["pageSize=0", "pageSize=101", "pageSize=1.5", "cursor=bad", "ownerId=secret", "bankId=bad"]:
        assert author.get("/api/v1/questions?" + query).status_code == 422
    sentinel = "c01-sensitive-content"
    invalid: dict[str, Any] = {**content(), "bankId": banks[0], "prompt": sentinel, sentinel: sentinel}
    response = author.post("/api/v1/questions", json=invalid)
    assert response.status_code == 422
    assert sentinel not in response.text + caplog.text
    assert author.post("/api/v1/questions", json={**content(), "bankId": str(uuid4())}).status_code == 404
    assert author.post(f"/api/v1/questions/{ids[0]}/archive").status_code == 404
