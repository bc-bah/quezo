from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from quezo_api.app import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_liveness_is_process_only(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "scope": "process-only"}
    assert response.headers["content-type"] == "application/json"
    assert "x-powered-by" not in response.headers


@pytest.mark.parametrize("path", ["/health/ready", "/api/v1/quizzes"])
def test_product_and_readiness_routes_are_absent(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 404


def test_openapi_describes_only_the_liveness_contract(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    document = response.json()
    assert set(document["paths"]) == {"/health/live"}
    schema = document["paths"]["/health/live"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert schema["$ref"] == "#/components/schemas/LivenessResponse"
    properties = document["components"]["schemas"]["LivenessResponse"]["properties"]
    assert properties["status"]["const"] == "ok"
    assert properties["scope"]["const"] == "process-only"
    assert client.get("/docs").status_code == 200
