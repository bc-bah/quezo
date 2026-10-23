import http.client
import json
import traceback
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import Depends, HTTPException, Query
from fastapi.testclient import TestClient
from psycopg import OperationalError
from psycopg_pool import PoolTimeout, TooManyRequests
from starlette.types import Message, Receive, Scope, Send

from quezo_api.app import create_app
from quezo_api.errors import (
    ERRORS, MAX_BODY_BYTES, ApiError, ErrorCode, ErrorEnvelope, HttpBoundary,
)
from quezo_api.schemas import Actor, ApiModel, NonNegativeInteger, PaginationParams

SECRET = "synthetic-secret-answer-do-not-reflect"
USER_ID = "b852a646-70ed-4ab9-aae4-d7fc2e0ca313"


class InputFixture(ApiModel):
    actor: Actor
    expected_revision: NonNegativeInteger


@pytest.fixture
def contract_client() -> Iterator[TestClient]:
    app = create_app()

    @app.post("/test-only/input", response_model=InputFixture)
    async def input_fixture(payload: InputFixture) -> InputFixture:
        return payload

    @app.get("/test-only/page")
    async def page_fixture(page: Annotated[PaginationParams, Query()]) -> PaginationParams:
        return page

    @app.get("/test-only/error/{kind}")
    async def error_fixture(kind: str) -> None:
        if kind == "dependency":
            raise OperationalError(SECRET)
        if kind == "pool":
            raise PoolTimeout(SECRET)
        if kind == "queue":
            raise TooManyRequests(SECRET)
        if kind == "rate":
            raise ApiError(ErrorCode.RATE_LIMITED, retry_after=7)
        if kind == "http":
            raise HTTPException(403, detail={"secret": SECRET}, headers={"X-Leak": SECRET})
        raise RuntimeError(SECRET)

    async def broken_dependency() -> None:
        raise OperationalError(SECRET)

    @app.get("/test-only/dependency", dependencies=[Depends(broken_dependency)])
    async def dependency_fixture() -> None:
        pytest.fail("A failing dependency must not execute the route")

    @app.get("/test-only/response", response_model=Actor)
    async def invalid_response_fixture() -> dict[str, str]:
        return {"userId": SECRET}

    # HTTP unit fixtures deliberately do not enter lifespan. F01's test_app.py
    # separately verifies the real database/startup path, with no substitution.
    yield TestClient(app)


@pytest.mark.parametrize(("payload", "path", "reason"), [
    ({"actor": {"userId": SECRET, "roles": ["learner"], "status": "active"},
      "expectedRevision": 0}, ["body", "actor", "userId"], "invalid_value"),
    ({"actor": {"userId": USER_ID, "roles": [SECRET], "status": "active"},
      "expectedRevision": 0}, ["body", "actor", "roles", 0], "invalid_value"),
    ({"actor": {"userId": USER_ID, "roles": ["learner"], "status": "active"},
      "expectedRevision": 0, SECRET: SECRET}, ["body", "[field]"], "unknown_field"),
    ({"actor": {"userId": USER_ID, "roles": ["learner"], "status": "active", SECRET: SECRET},
      "expectedRevision": 0}, ["body", "actor", "[field]"], "unknown_field"),
    ({"actor": {"userId": USER_ID, "roles": ["learner"], "status": "active"},
      "expectedRevision": 1.5}, ["body", "expectedRevision"], "invalid_value"),
    ({}, ["body", "actor"], "required"),
])
def test_invalid_payloads_are_sanitized(
    contract_client: TestClient, caplog: pytest.LogCaptureFixture,
    payload: dict[str, object], path: list[str | int], reason: str,
) -> None:
    response = contract_client.post("/test-only/input", json=payload)
    assert response.status_code == 422
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.code == ErrorCode.VALIDATION_FAILED
    assert envelope.details is not None
    assert {"path": path, "reason": reason} in response.json()["details"]["fields"]
    assert SECRET not in response.text + caplog.text
    assert "input" not in response.text and "ctx" not in response.text


def test_camel_case_request_and_response(contract_client: TestClient) -> None:
    payload = {
        "actor": {"userId": USER_ID, "roles": ["author", "learner"], "status": "active"},
        "expectedRevision": 0,
    }
    response = contract_client.post("/test-only/input", json=payload)
    assert response.status_code == 200
    assert response.json() == payload
    response = contract_client.post(
        "/test-only/input", json={**payload, "expected_revision": 0},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(("path", "status", "code"), [
    ("/test-only/error/dependency", 503, "DEPENDENCY_UNAVAILABLE"),
    ("/test-only/error/pool", 503, "DEPENDENCY_UNAVAILABLE"),
    ("/test-only/error/queue", 503, "DEPENDENCY_UNAVAILABLE"),
    ("/test-only/error/internal", 500, "INTERNAL_ERROR"),
    ("/test-only/error/http", 403, "FORBIDDEN"),
    ("/test-only/response", 500, "INTERNAL_ERROR"),
    ("/test-only/dependency", 503, "DEPENDENCY_UNAVAILABLE"),
    ("/test-only/error/rate", 429, "RATE_LIMITED"),
])
def test_safe_failures_and_correlation(
    contract_client: TestClient, caplog: pytest.LogCaptureFixture,
    path: str, status: int, code: str,
) -> None:
    caplog.set_level("INFO", logger="quezo_api.http")
    response = contract_client.get(path, headers={"X-Request-ID": SECRET})
    assert response.status_code == status
    assert response.json()["code"] == code
    request_id = response.headers["x-request-id"]
    assert UUID(request_id).version == 4
    assert response.json()["requestId"] == request_id
    assert response.headers["cache-control"] == "private, no-store"
    assert SECRET not in response.text + str(response.headers) + caplog.text
    record = [r for r in caplog.records if r.name == "quezo_api.http"][-1]
    assert json.loads(record.message) == {
        "requestId": request_id, "status": status, "code": code,
    }
    assert record.exc_info is None
    if status == 429:
        assert response.headers["retry-after"] == "7"


@pytest.mark.parametrize("body", [
    b'{"password":"synthetic-secret-answer-do-not-reflect",',
    b'{"password":"\xff"}',
])
def test_invalid_json_does_not_echo_body(
    contract_client: TestClient, caplog: pytest.LogCaptureFixture, body: bytes,
) -> None:
    response = contract_client.post(
        "/test-only/input", content=body, headers={"Content-Type": "application/json"},
    )
    assert response.status_code in {400, 422}
    assert response.json()["code"] == "VALIDATION_FAILED"
    assert SECRET not in response.text + caplog.text


def test_query_validation_and_defaults(contract_client: TestClient) -> None:
    assert contract_client.get("/test-only/page").json() == {"pageSize": 25, "cursor": None}
    for size in (1, 100):
        assert contract_client.get(f"/test-only/page?pageSize={size}").json()["pageSize"] == size
    for query in ("pageSize=0", "pageSize=101", "pageSize=1.5", f"{SECRET}={SECRET}"):
        response = contract_client.get(f"/test-only/page?{query}")
        assert response.status_code == 422
        assert SECRET not in response.text


def test_real_routes_have_consistent_envelopes_and_unchanged_health() -> None:
    client = TestClient(create_app())
    first = client.get("/health/live")
    second = client.get("/health/live")
    assert first.json() == {"status": "ok", "scope": "process-only"}
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    assert client.get("/api/v1/me").json()["code"] == "UNAUTHENTICATED"
    assert client.get("/api/v1/quizzes").json()["code"] == "UNAUTHENTICATED"
    for path in ("/api/v1/assignments", "/api/v1/eligible-learners", "/api/v1/attempts/" + USER_ID):
        assert client.get(path).json()["code"] == "UNAUTHENTICATED"
    for path in ("/api/v1/grades", "/health/ready", "/test-only/input"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"
    response = client.post("/health/live")
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["allow"] == "GET"


@pytest.mark.parametrize(("size", "status"), [(MAX_BODY_BYTES, 200), (MAX_BODY_BYTES + 1, 413)])
def test_body_limit_on_real_route(size: int, status: int) -> None:
    response = TestClient(create_app()).request("GET", "/health/live", content=b"x" * size)
    assert response.status_code == status
    if status == 413:
        assert response.json()["code"] == "PAYLOAD_TOO_LARGE"
        assert response.json()["requestId"] == response.headers["x-request-id"]


@pytest.mark.anyio
@pytest.mark.parametrize("declared_length", [None, b"1"])
async def test_chunked_limit_does_not_trust_content_length(declared_length: bytes | None) -> None:
    messages = iter([
        {"type": "http.request", "body": b"x" * MAX_BODY_BYTES, "more_body": True},
        {"type": "http.request", "body": b"x", "more_body": False},
    ])
    sent: list[Message] = []

    async def receive() -> Message:
        return next(messages)

    async def send(message: Message) -> None:
        sent.append(message)

    await create_app()({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/health/live",
        "query_string": b"", "root_path": "",
        "headers": [] if declared_length is None else [(b"content-length", declared_length)],
    }, receive, send)
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"])["code"] == "PAYLOAD_TOO_LARGE"


@pytest.mark.anyio
@pytest.mark.parametrize("started", [False, True])
async def test_failure_after_headers_never_reraises_original_secret(
    caplog: pytest.LogCaptureFixture, started: bool,
) -> None:
    async def failing_app(scope: Scope, receive: Receive, send: Send) -> None:
        if started:
            await send({"type": "http.response.start", "status": 200, "headers": []})
        raise RuntimeError(SECRET)

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        pass

    if started:
        with pytest.raises(RuntimeError, match="Response failed after headers") as error:
            await HttpBoundary(failing_app)({"type": "http"}, receive, send)
        assert SECRET not in "".join(traceback.format_exception(error.value))
    else:
        await HttpBoundary(failing_app)({"type": "http"}, receive, send)
    assert SECRET not in caplog.text


@pytest.mark.parametrize("validation_reason", ["Unprocessable Entity", "Unprocessable Content"])
def test_openapi_is_reproducible_and_contains_only_implemented_paths(
    monkeypatch: pytest.MonkeyPatch, validation_reason: str,
) -> None:
    monkeypatch.setitem(http.client.responses, 422, validation_reason)
    document = create_app().openapi()
    exported = Path(__file__).resolve().parents[1] / "openapi.json"
    assert json.loads(exported.read_text(encoding="utf-8")) == document
    assert document == create_app().openapi()
    assert set(document["paths"]) == {
        "/health/live", "/api/v1/me", "/api/v1/question-banks", "/api/v1/question-banks/{bank_id}",
        "/api/v1/questions", "/api/v1/questions/{question_id}",
        "/api/v1/questions/{question_id}/versions",
        "/api/v1/questions/{question_id}/versions/{version_id}",
        "/api/v1/quizzes", "/api/v1/quizzes/{quiz_id}", "/api/v1/quizzes/{quiz_id}/drafts",
        "/api/v1/quizzes/{quiz_id}/preview", "/api/v1/quizzes/{quiz_id}/publish",
        "/api/v1/quizzes/{quiz_id}/versions/{version_id}",
        "/api/v1/eligible-learners", "/api/v1/assignments", "/api/v1/assignments/{assignment_id}",
        "/api/v1/assignments/{assignment_id}/attempts", "/api/v1/attempts/{attempt_id}",
        "/api/v1/attempts/{attempt_id}/responses/{question_id}",
        "/api/v1/attempts/{attempt_id}/submission",
        "/api/v1/attempts/{attempt_id}/result",
    }
    schemas = document["components"]["schemas"]
    assert set(schemas["Actor"]["properties"]) == {"userId", "roles", "status"}
    assert schemas["Actor"]["additionalProperties"] is False
    assert schemas["Role"]["enum"] == ["administrator", "author", "learner"]
    assert schemas["PaginationParams"]["properties"]["pageSize"]["maximum"] == 100
    responses = document["paths"]["/health/live"]["get"]["responses"]
    assert responses["default"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorEnvelope")
    assert "X-Request-ID" in responses["200"]["headers"]
    for path, methods in document["paths"].items():
        if path.startswith(("/api/v1/questions", "/api/v1/question-banks", "/api/v1/quizzes")):
            for operation in methods.values():
                assert operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorEnvelope")


def test_every_error_code_has_safe_status_and_message() -> None:
    assert set(ERRORS) == set(ErrorCode)
    for code in ErrorCode:
        assert 400 <= ERRORS[code][0] <= 599


@pytest.mark.parametrize("code", list(ErrorCode))
def test_stable_codes_use_the_shared_handler(code: ErrorCode) -> None:
    app = create_app()

    @app.get("/test-only/known-error")
    async def known_error() -> None:
        raise ApiError(code)

    response = TestClient(app).get("/test-only/known-error")
    status, message = ERRORS[code]
    assert response.status_code == status
    assert response.json() == {
        "code": code.value, "message": message,
        "requestId": response.headers["x-request-id"],
    }


@pytest.mark.parametrize("retry_after", [0, -1, True])
def test_retry_after_must_be_positive_integer_seconds(retry_after: int) -> None:
    with pytest.raises(ValueError, match="positive seconds"):
        ApiError(ErrorCode.RATE_LIMITED, retry_after=retry_after)


def test_retry_after_is_not_a_generic_error_header() -> None:
    with pytest.raises(ValueError, match="Retry-After requires"):
        ApiError(ErrorCode.NOT_FOUND, retry_after=1)
