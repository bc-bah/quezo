from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi.testclient import TestClient

from identity_helpers import SigningPeer
from quezo_api.database import Database
from test_attempts import headers


def submit(client: TestClient, attempt: dict[str, Any], peer: SigningPeer) -> Any:
    return client.post(f"/api/v1/attempts/{attempt['id']}/submission", json={}, headers=headers(peer))


@asynccontextmanager
async def prior_schema_lifespan(database: Database) -> AsyncIterator[None]:
    # Only prior-head migration tests use this: D03 cannot run on an old schema.
    yield
