import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from typing import Annotated
from urllib.error import URLError
from urllib.request import urlopen

import psycopg
import pytest
from fastapi import Depends
from psycopg import sql
from psycopg.conninfo import make_conninfo
from fastapi.testclient import TestClient

from db_helpers import BACKEND, IsolatedDatabase, validate_test_admin_url
from quezo_api.app import create_app
from quezo_api.database import Database, database_loop_factory, get_database


@pytest.fixture
def client(
    database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    monkeypatch.setenv("QUEZO_DATABASE_URL", database.runtime_url)
    with TestClient(
        create_app(), backend_options={"loop_factory": asyncio.SelectorEventLoop}
    ) as test_client:
        yield test_client


def test_liveness_is_process_only(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "process-only"}
    assert response.headers["content-type"] == "application/json"
    assert "x-powered-by" not in response.headers


@pytest.mark.parametrize("path", ["/health/ready", "/api/v1/grades"])
def test_product_and_readiness_routes_are_absent(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404


def test_openapi_describes_only_implemented_contracts(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert set(document["paths"]) == {
        "/health/live", "/api/v1/me", "/api/v1/question-banks", "/api/v1/question-banks/{bank_id}",
        "/api/v1/questions", "/api/v1/questions/{question_id}",
        "/api/v1/questions/{question_id}/versions",
        "/api/v1/questions/{question_id}/versions/{version_id}",
        "/api/v1/questions/{question_id}/organization", "/api/v1/questions/{question_id}/move",
        "/api/v1/questions/{question_id}/archive", "/api/v1/question-banks/{bank_id}/archive",
        "/api/v1/quizzes", "/api/v1/quizzes/{quiz_id}", "/api/v1/quizzes/{quiz_id}/drafts",
        "/api/v1/quizzes/{quiz_id}/preview", "/api/v1/quizzes/{quiz_id}/publish",
        "/api/v1/quizzes/{quiz_id}/versions/{version_id}",
        "/api/v1/quizzes/{quiz_id}/versions", "/api/v1/quizzes/{quiz_id}/close",
        "/api/v1/quizzes/{quiz_id}/archive",
        "/api/v1/eligible-learners", "/api/v1/assignments", "/api/v1/assignments/{assignment_id}",
        "/api/v1/assignments/{assignment_id}/attempts", "/api/v1/attempts/{attempt_id}",
        "/api/v1/attempts/{attempt_id}/responses/{question_id}",
        "/api/v1/attempts/{attempt_id}/submission",
        "/api/v1/attempts/{attempt_id}/result",
    }
    schema = document["paths"]["/health/live"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"] == "#/components/schemas/LivenessResponse"
    properties = document["components"]["schemas"]["LivenessResponse"]["properties"]
    assert properties["status"]["const"] == "ok"
    assert properties["scope"]["const"] == "process-only"
    assert client.get("/docs").status_code == 200


def test_lifespan_opens_and_closes_database_pool(
    database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUEZO_DATABASE_URL", database.runtime_url)
    app = create_app()
    with TestClient(
        app, backend_options={"loop_factory": asyncio.SelectorEventLoop}
    ) as client:
        db = app.state.database
        assert isinstance(db, Database)
        assert not db.closed
        assert client.get("/health/live").json() == {
            "status": "ok", "scope": "process-only"
        }
    assert db.closed


def test_liveness_stays_process_only_after_database_connections_are_lost(
    database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUEZO_DATABASE_URL", database.runtime_url)
    with TestClient(
        create_app(), backend_options={"loop_factory": asyncio.SelectorEventLoop}
    ) as client:
        with psycopg.connect(database.migration_url, autocommit=True) as owner:
            owner.execute(
                sql.SQL("REVOKE CONNECT ON DATABASE {} FROM quezo_runtime").format(
                    sql.Identifier(database.name)
                )
            )
        # The owner cannot terminate another identity; only the isolated test admin can.
        params = validate_test_admin_url(os.environ["QUEZO_TEST_ADMIN_URL"])
        with psycopg.connect(make_conninfo(**params), autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND usename = 'quezo_runtime'", (database.name,)
            )
        assert client.get("/health/live").json() == {
            "status": "ok", "scope": "process-only"
        }


def test_uvicorn_loop_supports_psycopg_on_windows() -> None:
    loop = database_loop_factory()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()


def test_routes_can_use_the_lifespan_database_dependency(
    database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("QUEZO_DATABASE_URL", database.runtime_url)
    app = create_app()

    @app.get("/test-only/database")
    async def database_probe(db: Annotated[Database, Depends(get_database)]) -> str:
        async with db.transaction() as connection:
            cursor = await connection.execute("SELECT current_user")
            row = await cursor.fetchone()
            assert row is not None
            return str(row[0])

    with TestClient(
        app, backend_options={"loop_factory": asyncio.SelectorEventLoop}
    ) as client:
        assert client.get("/test-only/database").json() == "quezo_runtime"


def test_uvicorn_starts_with_the_documented_database_loop(
    database: IsolatedDatabase,
) -> None:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "--app-dir", str(BACKEND / "src"),
            "quezo_api.app:create_app", "--factory",
            "--loop", "quezo_api.database:database_loop_factory",
            "--host", "127.0.0.1", "--port", str(port), "--no-server-header",
        ],
        env={**os.environ, "QUEZO_DATABASE_URL": database.runtime_url},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                output, _ = process.communicate(timeout=5)
                pytest.fail(f"Uvicorn exited during startup:\n{output}")
            try:
                with urlopen(f"http://127.0.0.1:{port}/health/live", timeout=1) as response:
                    assert json.load(response) == {"status": "ok", "scope": "process-only"}
                    assert response.headers.get("server") is None
                    return
            except URLError:
                time.sleep(0.05)
        pytest.fail("Uvicorn did not become responsive within 15 seconds")
    finally:
        process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)
            pytest.fail("Uvicorn did not shut down within 10 seconds")
