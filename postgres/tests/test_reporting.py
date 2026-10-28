import asyncio
from datetime import datetime, timedelta, timezone
from itertools import product
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from db_helpers import IsolatedDatabase
from finalization_helpers import submit
from identity_helpers import SETTINGS, SUBJECT, SigningPeer, seed_account
from quezo_api.database import database_loop_factory
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection
from quezo_api.modules.results import service
from quezo_api.schemas import PaginationParams
from test_identity_access import identity_client, peer
from test_questions import author
from test_attempts import assigned, headers, start
from test_quizzes import composition, create, publish
from test_responses import command, path


def report_path(quiz_id: str) -> str:
    return f"/api/v1/quizzes/{quiz_id}/results"


def all_pages(client: TestClient, url: str, **kwargs: Any) -> list[dict[str, Any]]:
    items = []
    cursor = None
    while True:
        response = client.get(url, params={"pageSize": 1, **({"cursor": cursor} if cursor else {})}, **kwargs)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        page = response.json()
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


def test_summary_history_and_detail_agree_across_versions_and_attempts(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    assignment, request = assigned(author, database, {
        "attemptLimit": None,
        "answerKeyRelease": "after_finalization", "explanationRelease": "after_finalization",
    })
    base = report_path(request["quizId"])
    first = start(author, assignment, peer).json()
    wrong = {**command(first["questions"][0]), "selectedOptionId": first["questions"][0]["options"][1]["id"]}
    assert author.put(path(first), json=wrong, headers=headers(peer)).status_code == 200
    assert submit(author, first, peer).status_code == 200
    second = start(author, assignment, peer).json()
    assert author.put(path(second), json=command(second["questions"][0]), headers=headers(peer)).status_code == 200
    assert submit(author, second, peer).status_code == 200
    third = start(author, assignment, peer).json()
    idle = seed_account(database, subject="idle")
    assert author.post("/api/v1/assignments", json={**request, "learnerId": str(idle)}).status_code == 201

    quiz_url = "/api/v1/quizzes/" + request["quizId"]
    assert author.post(quiz_url + "/drafts", json={"expectedRevision": 1}).status_code == 201
    body = author.get(quiz_url).json()["draft"]
    body.update(title="Retained second publication", policy={"scoreRelease": "never"})
    assert author.patch(quiz_url, json={**body, "expectedRevision": 2}).status_code == 200
    version = publish(author, {"id": request["quizId"]}, revision=3).json()["versionId"]
    new_assignment = author.post("/api/v1/assignments", json={**request, "versionId": version}).json()
    fourth = start(author, new_assignment, peer).json()
    assert submit(author, fourth, peer).status_code == 200
    # Archive retains history, assignments and the original publication identities.
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.quizzes SET state='archived' WHERE id=%s", (request["quizId"],))

    report = author.get(base, params={"pageSize": 1}).json()
    assert report["summary"] == {
        "assignedLearners": 2, "participatingLearners": 1, "completedLearners": 1,
        "startedAttempts": 4, "inProgressAttempts": 1, "finalizedAttempts": 3,
        "submittedAttempts": 3, "expiredAttempts": 0, "scoreDenominator": "released_finalized_attempts",
        "releasedScoreAttempts": 2, "withheldScoreAttempts": 1, "meanScorePercent": 35.0,
    }
    learner_rows = report["learners"]["items"]
    next_cursor = report["learners"]["nextCursor"]
    assert next_cursor is not None
    learner_rows += author.get(base, params={"pageSize": 1, "cursor": next_cursor}).json()["learners"]["items"]
    assert {row["learnerId"] for row in learner_rows} == {request["learnerId"], str(idle)}
    assert next(row for row in learner_rows if row["learnerId"] == request["learnerId"]) == {
        "learnerId": request["learnerId"], "assignmentCount": 2, "startedAttempts": 4,
        "inProgressAttempts": 1, "finalizedAttempts": 3, "submittedAttempts": 3, "expiredAttempts": 0,
    }
    history = all_pages(author, "/api/v1/me/attempts", headers=headers(peer))
    attempts = all_pages(author, base + "/attempts")
    assert attempts == history
    assert {item["id"] for item in history} == {a["id"] for a in (first, second, third, fourth)}
    indexed = {item["id"]: item for item in history}
    assert indexed[third["id"]]["score"] == {"status": "not_finalized"}
    assert indexed[fourth["id"]]["score"] == {"status": "withheld"}
    assert indexed[fourth["id"]]["versionId"] == version
    for attempt in (first, second, fourth):
        response = author.get(base + "/attempts/" + attempt["id"])
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        detail = response.json()
        assert detail["attempt"] == indexed[attempt["id"]]
        result = author.get(f"/api/v1/attempts/{attempt['id']}/result", headers=headers(peer)).json()
        assert {k: v for k, v in detail["result"].items() if k != "serverTime"} == {
            k: v for k, v in result.items() if k != "serverTime"
        }
        assert detail["result"]["score"] == detail["attempt"]["score"]
        assert detail["attempt"]["versionId"] == attempt["versionId"]
        assert detail["attempt"]["attemptNumber"] == attempt["attemptNumber"]
    detail = author.get(base + "/attempts/" + first["id"]).json()
    assert [item["outcome"] for item in detail["result"]["answerKey"]["items"]] == ["incorrect", "unanswered"]
    assert [item["response"]["selectedOptionId"] for item in detail["responses"]] == [
        wrong["selectedOptionId"], None,
    ]
    assert author.get(base + "/attempts/" + third["id"]).status_code == 409
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*), sum(earned_points) FROM quezo.grades").fetchone() == (3, 7)
        assert connection.execute("SELECT count(*) FROM quezo.attempts WHERE state='in_progress'").fetchone() == (1,)


@pytest.mark.parametrize(("score", "key", "explanation"), list(product(
    ("after_finalization", "after_availability_end", "never"), repeat=3,
)))
def test_every_projection_uses_pinned_independent_release_at_boundary(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, monkeypatch: pytest.MonkeyPatch,
    score: str, key: str, explanation: str,
) -> None:
    end = datetime.now(timezone.utc) + timedelta(hours=1)
    assignment, request = assigned(author, database, {
        "availabilityEnd": end.isoformat(), "scoreRelease": score,
        "answerKeyRelease": key, "explanationRelease": explanation,
    })
    attempt = start(author, assignment, peer).json()
    assert submit(author, attempt, peer).status_code == 200
    base = report_path(request["quizId"])
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.quizzes SET state='closed' WHERE id=%s", (request["quizId"],))
    for delta in (-1, 0, 1):
        now = end + timedelta(microseconds=delta)

        async def clock(connection: Connection) -> datetime:
            return now
        monkeypatch.setattr(service, "database_time", clock)
        history = author.get("/api/v1/me/attempts", headers=headers(peer))
        attempts = author.get(base + "/attempts")
        report = author.get(base)
        detail = author.get(base + "/attempts/" + attempt["id"])
        result = author.get(f"/api/v1/attempts/{attempt['id']}/result", headers=headers(peer))
        for response in (history, attempts, report, detail, result):
            assert response.status_code == 200
            assert response.headers["cache-control"] == "private, no-store"
        assert history.json() == attempts.json()
        assert history.json()["items"][0] == detail.json()["attempt"]
        assert detail.json()["result"] == result.json()
        summary = report.json()["summary"]
        score_visible = score == "after_finalization" or (score == "after_availability_end" and delta >= 0)
        assert summary["releasedScoreAttempts"] == int(score_visible)
        assert summary["withheldScoreAttempts"] == int(not score_visible)
        assert summary["meanScorePercent"] == (0.0 if score_visible else None)
        assert detail.json()["attempt"]["score"] == result.json()["score"]
        for field, mode in (("score", score), ("answerKey", key), ("explanations", explanation)):
            visible = mode == "after_finalization" or (mode == "after_availability_end" and delta >= 0)
            if not visible:
                assert result.json()[field] == {"status": "withheld"}
            else:
                assert result.json()[field]["status"] == "released"
        serialized = detail.text
        assert ("correctOption" in serialized) == (result.json()["answerKey"]["status"] == "released")
        assert ('"outcome"' in serialized) == (result.json()["answerKey"]["status"] == "released")
        assert ("Synthetic feedback" in serialized) == (result.json()["explanations"]["status"] == "released")
        assert not any(field in serialized for field in ("correctOptionId", "fingerprint", "gradeId"))


@pytest.mark.parametrize("timing", [
    {}, {"timingChoice": "adjusted", "adjustedDurationSeconds": 60}, {"timingChoice": "off"},
])
def test_expired_vs_submitted_and_active_timing_are_persisted_not_inferred(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, timing: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quezo_api.modules.attempts import expiration
    monkeypatch.setattr(expiration, "INTERVAL_SECONDS", 3600)
    end = datetime.now(timezone.utc) + timedelta(seconds=2)
    assignment, request = assigned(author, database, {"availabilityEnd": end.isoformat()})
    attempt = author.post(f"/api/v1/assignments/{assignment['id']}/attempts", json=timing,
                          headers={**headers(peer), "Idempotency-Key": str(uuid4())}).json()
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("SELECT pg_sleep(greatest(0, extract(epoch FROM (%s - clock_timestamp()))) + 0.02)", (end,))
    # Reporting itself does not mutate or synthesize Grades for elapsed deadlines.
    before = author.get(report_path(request["quizId"])).json()["summary"]
    assert before["inProgressAttempts"] == 1 and before["finalizedAttempts"] == 0
    assert before["meanScorePercent"] is None
    completion = submit(author, attempt, peer).json()
    expected = "expired" if not timing else "submitted"
    assert completion["completionReason"] == expected
    summary = author.get(report_path(request["quizId"])).json()["summary"]
    assert summary["expiredAttempts"] == int(expected == "expired")
    assert summary["submittedAttempts"] == int(expected == "submitted")
    item = author.get("/api/v1/me/attempts", headers=headers(peer)).json()["items"][0]
    assert item["completion"] == completion and item["deadline"] == attempt["deadline"]
    assert item["timingChoice"] == attempt["timingChoice"]
    assert item["adjustedDurationSeconds"] == attempt["adjustedDurationSeconds"]


def test_empty_pages_and_access_controls_on_nested_ids_cursors_and_direct_calls(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    seed_account(database, subject="empty")
    assert author.get("/api/v1/me/attempts", headers=headers(peer, "empty")).json() == {
        "items": [], "nextCursor": None,
    }
    empty_quiz = create(author, composition(author))
    empty = author.get(report_path(empty_quiz["id"])).json()
    assert empty["learners"] == {"items": [], "nextCursor": None}
    assert empty["summary"]["assignedLearners"] == empty["summary"]["finalizedAttempts"] == 0
    assert empty["summary"]["meanScorePercent"] is None
    assignment, request = assigned(author, database)
    attempt = start(author, assignment, peer).json()
    assert submit(author, attempt, peer).status_code == 200
    base = report_path(request["quizId"])
    detail_url = base + "/attempts/" + attempt["id"]
    seed_account(database, subject="foreign", roles=("author", "learner"))
    seed_account(database, subject="admin", roles=("administrator",))
    for suffix in ("", "/attempts", "/attempts/" + attempt["id"]):
        for subject, status in (("foreign", 404), ("admin", 403), ("learner", 403)):
            response = author.get(base + suffix, headers=headers(peer, subject))
            assert response.status_code == status
            assert not any(field in response.text for field in ("Synthetic", "earnedPoints", "correctOption"))
        assert author.get(base + suffix, headers={"Authorization": ""}).status_code == 401
    assert author.get(report_path(empty_quiz["id"]) + "/attempts/" + attempt["id"]).status_code == 404
    assert author.get(base + "/attempts/" + str(uuid4())).status_code == 404
    for url, cursor in (
        ("/api/v1/me/attempts", attempt["id"]),
        ("/api/v1/me/attempts", str(uuid4())),
    ):
        assert author.get(url, params={"cursor": cursor}, headers=headers(peer, "foreign")).status_code == 404
    assert author.get(report_path(empty_quiz["id"]), params={"cursor": request["learnerId"]}).status_code == 404
    assert author.get(report_path(empty_quiz["id"]) + "/attempts", params={"cursor": attempt["id"]}).status_code == 404
    for url in (base, base + "/attempts", "/api/v1/me/attempts"):
        auth = headers(peer) if url == "/api/v1/me/attempts" else {}
        assert author.get(url, params={"cursor": "malformed"}, headers=auth).status_code == 422
        assert author.get(url, params={"pageSize": 101}, headers=auth).status_code == 422
    assert author.get("/api/v1/me/attempts").status_code == 403
    assert author.get("/api/v1/me/attempts", headers=headers(peer, "admin")).status_code == 403

    async def direct_calls() -> None:
        connection = await psycopg.AsyncConnection.connect(database.runtime_url)
        async with connection:
            for subject, code in (("foreign", ErrorCode.NOT_FOUND), ("admin", ErrorCode.FORBIDDEN)):
                identity = VerifiedIdentity(SETTINGS.issuer, subject)
                for operation in (
                    service.quiz_report(connection, identity, UUID(request["quizId"]), PaginationParams()),
                    service.author_attempts(connection, identity, UUID(request["quizId"]), PaginationParams()),
                    service.finalized_submission(connection, identity, UUID(request["quizId"]), UUID(attempt["id"])),
                ):
                    with pytest.raises(ApiError) as error:
                        await operation
                    assert error.value.code == code
            with pytest.raises(ApiError) as error:
                await service.learner_history(
                    connection, VerifiedIdentity(SETTINGS.issuer, SUBJECT), PaginationParams(),
                )
            assert error.value.code == ErrorCode.FORBIDDEN
    with asyncio.Runner(loop_factory=database_loop_factory) as runner:
        runner.run(direct_calls())
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.accounts SET status='disabled' WHERE id=%s", (request["learnerId"],))
    assert author.get("/api/v1/me/attempts", headers=headers(peer)).status_code == 403
    assert author.get(detail_url).status_code == 200


def test_reporting_query_plans_reuse_existing_scoped_indexes(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    assignment, request = assigned(author, database)
    attempt = start(author, assignment, peer).json()
    assert submit(author, attempt, peer).status_code == 200
    with psycopg.connect(database.runtime_url) as connection:
        # A tiny fixture naturally favors sequential scans; also prove scoped index eligibility.
        connection.execute("ANALYZE quezo.attempts")
        statements = [
            ("history", service.ATTEMPT_ROWS + " WHERE t.learner_id=%s ORDER BY t.id LIMIT 26",
             (datetime.now(timezone.utc), request["learnerId"])),
            ("report", "SELECT t.id FROM quezo.assignments a LEFT JOIN quezo.attempts t "
             "ON t.assignment_id=a.id WHERE a.quiz_id=%s", (request["quizId"],)),
            ("submission", "SELECT q.id FROM quezo.attempt_questions q JOIN quezo.grade_items i "
             "ON i.question_id=q.id AND i.attempt_id=q.attempt_id WHERE q.attempt_id=%s ORDER BY q.position",
             (attempt["id"],)),
        ]
        for name, sql, params in statements:
            natural = connection.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, params).fetchone()
            assert natural is not None and natural[0][0]["Execution Time"] >= 0
            nodes = []
            pending = [natural[0][0]["Plan"]]
            while pending:
                node = pending.pop()
                nodes.append(node["Node Type"] + (" via " + node["Index Name"] if "Index Name" in node else ""))
                pending.extend(node.get("Plans", []))
            print(f"R02 {name}: natural nodes={', '.join(nodes)}; "
                  f"execution_ms={natural[0][0]['Execution Time']}")
        connection.execute("SET LOCAL enable_seqscan=off")
        plans = {}
        for name, sql, params in statements:
            plans[name] = str(connection.execute("EXPLAIN (FORMAT JSON) " + sql, params).fetchone())
        assert "attempts_learner" in plans["history"]
        assert "assignments_quiz" in plans["report"]
        assert "grade_items_attempt" in plans["submission"]
        assignment_plan = str(connection.execute(
            "EXPLAIN (FORMAT JSON) SELECT id FROM quezo.attempts WHERE assignment_id=%s",
            (assignment["id"],),
        ).fetchone())
        assert "attempts_assignment_id_attempt_number_key" in assignment_plan


@pytest.mark.parametrize("revocation", ["role", "disabled", "mapping"])
def test_reporting_rechecks_live_author_and_learner_access(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer, revocation: str,
) -> None:
    assignment, request = assigned(author, database)
    attempt = start(author, assignment, peer).json()
    assert submit(author, attempt, peer).status_code == 200
    base = report_path(request["quizId"])
    for url in (base, base + "/attempts", base + "/attempts/" + attempt["id"]):
        assert author.get(url).status_code == 200
    with psycopg.connect(database.runtime_url) as connection:
        targets = "SELECT account_id FROM quezo.identity_mappings WHERE subject IN (%s, %s)"
        statement = {
            "role": "DELETE FROM quezo.account_roles WHERE account_id IN ",
            "disabled": "UPDATE quezo.accounts SET status='disabled' WHERE id IN ",
            "mapping": "UPDATE quezo.identity_mappings SET active=false WHERE account_id IN ",
        }[revocation]
        connection.execute(statement + "(" + targets + ")", (SUBJECT, "learner"))
    expected = 401 if revocation == "mapping" else 403
    for url, auth in (
        (base, {}), (base + "/attempts", {}), (base + "/attempts/" + attempt["id"], {}),
        ("/api/v1/me/attempts", headers(peer)),
    ):
        response = author.get(url, headers=auth)
        assert response.status_code == expected
        assert not any(field in response.text for field in ("earnedPoints", "Synthetic", "correctOption"))


def test_mean_is_equally_weighted_per_attempt_not_best_or_pooled_points(
    author: TestClient, database: IsolatedDatabase, peer: SigningPeer,
) -> None:
    assignment, request = assigned(author, database)
    first = start(author, assignment, peer).json()
    assert author.put(path(first), json=command(first["questions"][0]), headers=headers(peer)).status_code == 200
    assert submit(author, first, peer).status_code == 200  # 7/10 = 70%
    quiz_url = "/api/v1/quizzes/" + request["quizId"]
    assert author.post(quiz_url + "/drafts", json={"expectedRevision": 1}).status_code == 201
    body = author.get(quiz_url).json()["draft"]
    body["questions"] = [{**body["questions"][0], "pointOverride": 2}]
    assert author.patch(quiz_url, json={**body, "expectedRevision": 2}).status_code == 200
    version = publish(author, {"id": request["quizId"]}, revision=3).json()["versionId"]
    second_assignment = author.post("/api/v1/assignments", json={**request, "versionId": version}).json()
    second = start(author, second_assignment, peer).json()
    assert submit(author, second, peer).status_code == 200  # 0/2 = 0%
    summary = author.get(report_path(request["quizId"])).json()["summary"]
    assert summary["assignedLearners"] == summary["participatingLearners"] == summary["completedLearners"] == 1
    assert summary["releasedScoreAttempts"] == summary["finalizedAttempts"] == 2
    assert summary["meanScorePercent"] == 35.0  # Neither best (70%) nor pooled (7/12).
