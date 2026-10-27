import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

from db_helpers import IsolatedDatabase, run_migrations
from identity_helpers import SigningPeer, seed_account
from question_helpers import content
from quezo_api.database import Database, DatabaseSettings, database_loop_factory
from quezo_api.errors import ApiError
from quezo_api.modules.identity.access import resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions import service as questions
from quezo_api.modules.questions.schemas import QuestionListParams, QuestionMove
from quezo_api.modules.quizzes import service as quizzes
from quezo_api.modules.quizzes.schemas import DraftCommand
from quezo_api.schemas import PaginationParams
from test_identity_access import identity_client, peer
from test_questions import author, create_bank
from test_quizzes import composition, create, publish
from test_attempts import assigned, headers, start


def question(client: TestClient, bank: str, **fields: Any) -> dict[str, Any]:
    result = client.post("/api/v1/questions", json={**content(), "bankId": bank, **fields})
    assert result.status_code == 201
    return dict(result.json())


def test_search_move_archive_and_retained_selections(author: TestClient) -> None:
    bank, target = create_bank(author), create_bank(author)
    items = [question(author, bank, prompt=f"Needle %_{i}", category="Science", tags=["shared", "exact"])
             for i in range(3)]
    question(author, bank, prompt="Needle unrelated", category="Other", tags=["shared"])
    query: dict[str, str | int] = {"text": "NEEDLE %_", "category": "Science", "tag": "exact", "pageSize": 1}
    found: list[str] = []
    while True:
        page = author.get("/api/v1/questions", params=query)
        assert page.status_code == 200
        found.extend(item["questionId"] for item in page.json()["items"])
        if page.json()["nextCursor"] is None:
            break
        query["cursor"] = page.json()["nextCursor"]
    assert found == sorted(item["questionId"] for item in items)
    item = items[0]
    path = "/api/v1/questions/" + item["questionId"]
    body = {"title": "Pinned before archive", "questions": [
        {"questionId": item["questionId"], "versionId": item["versionId"]},
    ]}
    quiz = create(author, body)
    moved = author.post(path + "/move", json={"bankId": target, "expectedRevision": 1})
    assert moved.status_code == 200 and moved.json()["bankId"] == target
    assert author.get(path).json()["versionId"] == item["versionId"]
    assert author.get("/api/v1/questions", params={"bankId": bank, "tag": "exact"}).json()["items"]
    assert author.post(path + "/archive").status_code == 200
    assert author.get("/api/v1/questions", params={"bankId": target}).json()["items"] == []
    archived = author.get("/api/v1/questions", params={"bankId": target, "includeArchived": "true"}).json()["items"]
    assert archived[0]["questionId"] == item["questionId"] and archived[0]["archived"]
    assert author.get(path + "/versions/" + item["versionId"]).status_code == 200
    assert author.patch(path, json={**content(), "expectedRevision": 1}).json()["code"] == "INVALID_STATE"
    assert author.post(path + "/move", json={"bankId": bank, "expectedRevision": 1}).status_code == 409
    assert author.post("/api/v1/quizzes", json=body).json()["code"] == "INVALID_STATE"
    # Existing exact pins remain valid; archiving must not silently update or erase a draft.
    assert author.patch("/api/v1/quizzes/" + quiz["id"], json={**body, "expectedRevision": 1}).status_code == 200
    assert publish(author, quiz, revision=2).status_code == 201
    assert author.post(f"/api/v1/question-banks/{bank}/archive").json()["archived"] is True
    assert bank not in [b["id"] for b in author.get("/api/v1/question-banks").json()["items"]]
    assert bank in [b["id"] for b in author.get("/api/v1/question-banks?includeArchived=true").json()["items"]]
    assert author.get("/api/v1/questions", params={"bankId": bank}).json()["items"] == []
    assert author.post("/api/v1/questions", json={**content(), "bankId": bank}).status_code == 409
    assert author.patch(f"/api/v1/question-banks/{bank}", json={"name": "Denied"}).status_code == 409
    assert author.patch("/api/v1/questions/" + items[1]["questionId"],
                        json={**content(), "expectedRevision": 1}).status_code == 409
    # Moving an unarchived question out of an archived bank restores its discoverability.
    assert author.post("/api/v1/questions/" + items[1]["questionId"] + "/move",
                       json={"bankId": target, "expectedRevision": 1}).status_code == 200


def test_explicit_revision_update_and_publication_history(author: TestClient) -> None:
    body = composition(author)
    quiz = create(author, body)
    other = create(author, body)
    first = publish(author, quiz).json()
    assert publish(author, other).status_code == 201
    path = "/api/v1/quizzes/" + quiz["id"]
    original = author.get(path + "/versions/" + first["versionId"]).json()
    selected = original["questions"][0]["question"]
    changed = author.patch("/api/v1/questions/" + selected["questionId"], json={
        **{key: selected[key] for key in content()}, "category": "Revised", "tags": ["new"],
        "prompt": "Explicit new version", "expectedRevision": 1,
    }).json()
    draft = author.post(path + "/drafts", json={"expectedRevision": 1}).json()
    assert draft["draft"]["questions"][0]["versionId"] == selected["versionId"]
    body["questions"][0]["versionId"] = changed["versionId"]
    assert author.patch(path, json={**body, "expectedRevision": 2}).status_code == 200
    second = publish(author, quiz, revision=3).json()
    assert author.get(path + "/versions/" + first["versionId"]).json() == original
    latest = author.get(path + "/versions/" + second["versionId"]).json()
    assert latest["questions"][0]["question"]["versionId"] == changed["versionId"]
    first_page = author.get(path + "/versions?pageSize=1").json()
    assert [item["id"] for item in first_page["items"]] == [first["versionId"]]
    assert first_page["nextCursor"] == first["versionId"]
    rest = author.get(path + "/versions", params={"cursor": first_page["nextCursor"]}).json()
    assert [item["id"] for item in rest["items"]] == [second["versionId"]]
    assert rest["nextCursor"] is None
    assert author.get(f"/api/v1/quizzes/{other['id']}/versions", params={
        "cursor": second["versionId"],
    }).status_code == 404


def test_close_freezes_draft_preserves_attempts_and_archive_retains_history(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    assignment, request = assigned(author, database, {"attemptLimit": 2})
    attempt = start(author, assignment, peer).json()
    quiz_path = "/api/v1/quizzes/" + request["quizId"]
    version_path = quiz_path + "/versions/" + request["versionId"]
    publication = author.get(version_path).json()
    with psycopg.connect(database.runtime_url) as connection:
        frozen_questions = connection.execute(
            "SELECT row_to_json(t) FROM quezo.attempt_questions t WHERE attempt_id = %s ORDER BY position",
            (attempt["id"],),
        ).fetchall()
    assert author.post(quiz_path + "/drafts", json={"expectedRevision": 1}).status_code == 201
    assert author.post(quiz_path + "/close", json={"expectedRevision": 1}).json()["code"] == "DRAFT_REVISION_CONFLICT"
    closed = author.post(quiz_path + "/close", json={"expectedRevision": 2})
    assert closed.status_code == 200 and closed.json()["hasDraft"]
    for command in ["close", "drafts", "preview", "archive"]:
        assert author.post(quiz_path + "/" + command, json={"expectedRevision": 2}).status_code == 409
    assert publish(author, {"id": request["quizId"]}, revision=2).status_code == 409
    assert author.patch(quiz_path, json={"title": "Denied", "expectedRevision": 2}).status_code == 409
    resumed = start(author, assignment, peer)
    assert resumed.status_code == 200 and resumed.json()["deadline"] == attempt["deadline"]
    for item in publication["questions"]:
        q = item["question"]
        assert author.patch(f"/api/v1/questions/{q['questionId']}", json={
            **{key: q[key] for key in content()}, "prompt": "Edited after attempt start",
            "expectedRevision": 1, "correctOptionId": q["options"][1]["id"],
            "defaultPoints": 100, "feedback": "Changed after attempt start",
        }).status_code == 200
        assert author.post(f"/api/v1/questions/{q['questionId']}/archive").status_code == 200
    for bank_id in {item["question"]["bankId"] for item in publication["questions"]}:
        assert author.post(f"/api/v1/question-banks/{bank_id}/archive").status_code == 200
    assert author.get(version_path).json() == publication
    assert author.get("/api/v1/attempts/" + attempt["id"], headers=headers(peer)).json() == attempt
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute(
            "SELECT row_to_json(t) FROM quezo.attempt_questions t WHERE attempt_id = %s ORDER BY position",
            (attempt["id"],),
        ).fetchall() == frozen_questions
    assert author.post(f"/api/v1/attempts/{attempt['id']}/submission", json={}, headers=headers(peer)).status_code == 200
    before_result = author.get(f"/api/v1/attempts/{attempt['id']}/result", headers=headers(peer)).json()
    before_result.pop("serverTime")
    assert start(author, assignment, peer).json()["code"] == "ASSESSMENT_UNAVAILABLE"
    with psycopg.connect(database.runtime_url) as connection:
        before = {table: connection.execute(f"SELECT row_to_json(t) FROM quezo.{table} t ORDER BY 1::text").fetchall()
                  for table in ["attempts", "attempt_questions", "grades", "grade_items", "quiz_versions", "quiz_questions"]}
    assert author.post(quiz_path + "/archive", json={"expectedRevision": 2}).status_code == 200
    assert author.get(version_path).json() == publication
    after_result = author.get(f"/api/v1/attempts/{attempt['id']}/result", headers=headers(peer)).json()
    after_result.pop("serverTime")
    assert after_result == before_result
    with psycopg.connect(database.runtime_url) as connection:
        for table, rows in before.items():
            assert connection.execute(f"SELECT row_to_json(t) FROM quezo.{table} t ORDER BY 1::text").fetchall() == rows
    assert request["quizId"] not in [q["id"] for q in author.get("/api/v1/quizzes").json()["items"]]
    assert request["quizId"] in [q["id"] for q in author.get("/api/v1/quizzes?includeArchived=true").json()["items"]]
    assert author.get(quiz_path + "/versions").json()["items"][0]["id"] == request["versionId"]


def test_unpublished_archive_and_close_race(author: TestClient) -> None:
    quiz = create(author, {"title": "Abandoned"})
    path = "/api/v1/quizzes/" + quiz["id"]
    assert author.post(path + "/close", json={"expectedRevision": 1}).status_code == 409
    assert author.post(path + "/archive", json={"expectedRevision": 1}).status_code == 200
    assert author.get(path + "/versions").json()["items"] == []
    assert author.patch(path, json={"title": "Denied", "expectedRevision": 1}).status_code == 409
    quiz = create(author, composition(author))
    assert publish(author, quiz).status_code == 201
    path = "/api/v1/quizzes/" + quiz["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        close = pool.submit(author.post, path + "/close", json={"expectedRevision": 1})
        draft = pool.submit(author.post, path + "/drafts", json={"expectedRevision": 1})
        results = [close.result(), draft.result()]
    assert sum(result.status_code < 300 for result in results) == 1
    assert sum(result.status_code == 409 for result in results) == 1


def test_new_surfaces_hide_foreign_author_and_direct_calls(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    body = composition(author)
    quiz = create(author, body)
    version = publish(author, quiz).json()["versionId"]
    qid = body["questions"][0]["questionId"]
    bank = author.get("/api/v1/questions/" + qid).json()["bankId"]
    seed_account(database, roles=("author",), subject="foreign")
    author.headers.update(headers(peer, "foreign"))
    own_bank = create_bank(author)
    own = question(author, own_bank)
    for path in [f"/questions/{qid}/organization", f"/quizzes/{quiz['id']}/versions",
                 f"/questions?text=Synthetic&category=hidden&tag=hidden", "/question-banks?includeArchived=true",
                 "/quizzes?includeArchived=true"]:
        response = author.get("/api/v1" + path)
        assert response.status_code == (404 if "/organization" in path or "/versions" in path else 200)
        assert qid not in response.text and version not in response.text and bank not in response.text
    for path, payload in [
        (f"/question-banks/{bank}/archive", None), (f"/questions/{qid}/archive", None),
        (f"/questions/{qid}/move", {"bankId": own_bank, "expectedRevision": 1}),
        (f"/questions/{own['questionId']}/move", {"bankId": bank, "expectedRevision": 1}),
        (f"/quizzes/{quiz['id']}/close", {"expectedRevision": 1}),
        (f"/quizzes/{quiz['id']}/archive", {"expectedRevision": 1}),
    ]:
        assert author.post("/api/v1" + path, json=payload).status_code == 404

    async def direct_calls() -> None:
        async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
            async with db.transaction() as connection:
                actor = await resolve_actor(connection, VerifiedIdentity(
                    issuer="http://localhost:8080/realms/quezo-local", subject="foreign",
                ))
                for operation in [
                    questions.list_questions(connection, actor, QuestionListParams.model_validate({"bankId": bank})),
                    questions.archive_bank(connection, actor, UUID(bank)),
                    questions.organize_question(connection, actor, UUID(qid), QuestionMove.model_validate({
                        "bankId": own_bank, "expectedRevision": 1,
                    })),
                    quizzes.list_publications(connection, actor, UUID(quiz["id"]), PaginationParams()),
                    quizzes.transition(connection, actor, UUID(quiz["id"]), DraftCommand.model_validate({"expectedRevision": 1}), "closed"),
                ]:
                    with pytest.raises(ApiError) as error:
                        await operation
                    assert error.value.code.value == "NOT_FOUND"
    with asyncio.Runner(loop_factory=database_loop_factory) as runner:
        runner.run(direct_calls())


@pytest.mark.parametrize(("field", "value"), [
    ("category", ""), ("category", " "), ("category", "c" * 101),
    ("tags", [""]), ("tags", ["t" * 51]), ("tags", ["t"] * 21), ("tags", [None]),
])
def test_metadata_bounds_http(author: TestClient, field: str, value: object) -> None:
    bank = create_bank(author)
    assert author.post("/api/v1/questions", json={
        **content(), "bankId": bank, field: value,
    }).status_code == 422


@pytest.mark.parametrize(("category", "tags"), [(None, []), ("c", ["t"]), ("c" * 100, ["t" * 50] * 20)])
def test_metadata_valid_boundaries_http(author: TestClient, category: str | None, tags: list[str]) -> None:
    item = question(author, create_bank(author), category=category, tags=tags)
    metadata = author.get(f"/api/v1/questions/{item['questionId']}/organization").json()
    assert metadata["category"] == category and metadata["tags"] == tags
    assert author.patch(f"/api/v1/questions/{item['questionId']}", json={
        **content(), "expectedRevision": 1,
    }).status_code == 200
    retained = author.get(f"/api/v1/questions/{item['questionId']}/organization").json()
    assert retained["category"] == category and retained["tags"] == tags
    assert author.patch(f"/api/v1/questions/{item['questionId']}", json={
        **content(), "expectedRevision": 2, "category": None, "tags": [],
    }).status_code == 200
    cleared = author.get(f"/api/v1/questions/{item['questionId']}/organization").json()
    assert cleared["category"] is None and cleared["tags"] == []


def test_metadata_boundaries_and_upgrade_from_actual_head(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0009_finalization")
    owner = seed_account(empty_database, roles=("author",))
    from test_question_migrations import insert_question
    bank = uuid4()
    with psycopg.connect(empty_database.runtime_url) as connection:
        connection.execute("INSERT INTO quezo.question_banks (id, owner_id, name) VALUES (%s, %s, 'Retained')", (bank, owner))
        qid, vid = insert_question(connection, owner, bank, content())
        before = connection.execute("SELECT prompt, options, feedback FROM quezo.question_versions WHERE id = %s", (vid,)).fetchone()
    run_migrations(empty_database.migration_url)
    run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.runtime_url) as connection:
        assert connection.execute("SELECT prompt, options, feedback FROM quezo.question_versions WHERE id = %s", (vid,)).fetchone() == before
        assert connection.execute("SELECT category, tags FROM quezo.questions WHERE id = %s", (qid,)).fetchone() == (None, [])
        assert connection.execute("SELECT revision FROM quezo.questions WHERE id = %s", (qid,)).fetchone() == (1,)
    for category, tags in [("c", ["t"]), ("c" * 100, ["t" * 50] * 20)]:
        with psycopg.connect(empty_database.runtime_url) as connection:
            connection.execute("UPDATE quezo.questions SET category = %s, tags = %s WHERE id = %s",
                               (category, tags, qid))
            assert connection.execute("SELECT prompt, options, feedback FROM quezo.question_versions WHERE id = %s", (vid,)).fetchone() == before
    invalid: list[tuple[str | None, list[str | None]]] = [
        ("", []), ("c" * 101, []), (None, ["t" * 51]), (None, ["t"] * 21), (None, [None]),
    ]
    for bad_category, bad_tags in invalid:
        with pytest.raises(psycopg.errors.CheckViolation), psycopg.connect(empty_database.runtime_url) as connection:
            connection.execute("UPDATE quezo.questions SET category = %s, tags = %s WHERE id = %s",
                               (bad_category, bad_tags, qid))


@pytest.mark.parametrize("role", ["learner", "administrator"])
def test_new_surfaces_require_live_author_role(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, role: str,
) -> None:
    bank = create_bank(author)
    item = question(author, bank)
    quiz = create(author, {"title": "Protected"})
    seed_account(database, roles=(role,), subject=role)
    author.headers.update(headers(peer, role))
    for path in ["/questions?text=Synthetic&includeArchived=true", "/question-banks?includeArchived=true",
                 f"/questions/{item['questionId']}/organization", f"/quizzes/{quiz['id']}/versions"]:
        assert author.get("/api/v1" + path).status_code == 403
    for path, body in [
        (f"/question-banks/{bank}/archive", None), (f"/questions/{item['questionId']}/archive", None),
        (f"/questions/{item['questionId']}/move", {"bankId": bank, "expectedRevision": 1}),
        (f"/quizzes/{quiz['id']}/close", {"expectedRevision": 1}),
        (f"/quizzes/{quiz['id']}/archive", {"expectedRevision": 1}),
    ]:
        assert author.post("/api/v1" + path, json=body).status_code == 403


def test_author_workspace_migration_failure_is_atomic(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0009_finalization")
    with psycopg.connect(empty_database.migration_url) as connection:
        connection.execute("ALTER TABLE quezo.questions ADD COLUMN category integer")
    with pytest.raises(RuntimeError, match="DuplicateColumn"):
        run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0009_finalization",)
        assert connection.execute("SELECT to_regprocedure('quezo.question_tags_valid(text[])')").fetchone() == (None,)
        connection.execute("ALTER TABLE quezo.questions DROP COLUMN category")
    run_migrations(empty_database.migration_url)
