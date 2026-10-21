import asyncio
import os
from collections.abc import Iterator
from typing import Annotated
from uuid import UUID, uuid4

import httpx2 as httpx
import psycopg
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from psycopg.conninfo import make_conninfo

from db_helpers import IsolatedDatabase, validate_test_admin_url
from identity_helpers import SETTINGS, SUBJECT, SigningPeer, seed_account
from quezo_api.app import create_app
from quezo_api.modules.identity.access import get_actor, require_owner, require_role
from quezo_api.modules.identity.tokens import TokenVerifier
from quezo_api.schemas import AccessStatus, Actor, Role


@pytest.fixture
def peer() -> SigningPeer:
    return SigningPeer()


@pytest.fixture
def identity_client(
    database: IsolatedDatabase, monkeypatch: pytest.MonkeyPatch, peer: SigningPeer,
) -> Iterator[TestClient]:
    monkeypatch.setenv("QUEZO_DATABASE_URL", database.runtime_url)
    monkeypatch.setenv("QUEZO_DB_POOL_TIMEOUT", "0.5")
    app = create_app()

    @app.get("/test-only/role/{role}")
    async def role_route(role: Role, actor: Annotated[Actor, Depends(get_actor)]) -> Actor:
        require_role(actor, role)
        return actor

    @app.get("/test-only/owner/{owner}")
    async def owner_route(owner: UUID, actor: Annotated[Actor, Depends(get_actor)]) -> Actor:
        require_owner(actor, owner, Role.AUTHOR)
        return actor

    with TestClient(app, backend_options={"loop_factory": asyncio.SelectorEventLoop}) as client:
        # Only the transport is synthetic: JWT verification and database lookup are real.
        async def install() -> httpx.AsyncClient:
            transport_client = httpx.AsyncClient(transport=httpx.MockTransport(peer.serve))
            app.state.token_verifier = TokenVerifier(SETTINGS, transport_client)
            return transport_client

        assert client.portal is not None
        transport_client = client.portal.call(install)
        try:
            yield client
        finally:
            client.portal.call(transport_client.aclose)
    assert transport_client.is_closed


@pytest.mark.parametrize("roles", [
    (), ("administrator",), ("author",), ("learner",), ("author", "learner"),
])
def test_me_returns_only_live_actor(
    database: IsolatedDatabase, peer: SigningPeer, identity_client: TestClient, roles: tuple[str, ...],
) -> None:
    account_id = seed_account(database, roles=roles)
    response = identity_client.get("/api/v1/me", headers={"Authorization": f"Bearer {peer.token()}"})
    assert response.status_code == 200
    assert response.json() == {"userId": str(account_id), "roles": sorted(roles), "status": "active"}
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-request-id"]
    assert SUBJECT not in response.text


@pytest.mark.parametrize(("state", "status", "code"), [
    ("missing", 401, "UNAUTHENTICATED"), ("inactive", 401, "UNAUTHENTICATED"),
    ("disabled", 403, "ACCOUNT_DISABLED"),
])
def test_missing_inactive_disabled_denied(
    database: IsolatedDatabase, peer: SigningPeer, identity_client: TestClient,
    state: str, status: int, code: str,
) -> None:
    if state != "missing":
        seed_account(database, active=state != "inactive", status="disabled" if state == "disabled" else "active")
    response = identity_client.get("/api/v1/me", headers={"Authorization": f"Bearer {peer.token()}"})
    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.json()["requestId"] == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "private, no-store"


def test_revocation_with_old_token_and_direct_role_ownership_checks(
    database: IsolatedDatabase, peer: SigningPeer, identity_client: TestClient,
) -> None:
    account_id = seed_account(database, roles=("author", "learner"))
    headers = {"Authorization": f"Bearer {peer.token()}"}
    assert identity_client.get(f"/test-only/owner/{account_id}", headers=headers).status_code == 200
    assert identity_client.get(f"/test-only/owner/{uuid4()}", headers=headers).status_code == 404
    assert identity_client.get("/test-only/role/administrator", headers=headers).status_code == 403
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("DELETE FROM quezo.account_roles WHERE account_id = %s", (account_id,))
        connection.execute(
            "INSERT INTO quezo.account_roles VALUES (%s, 'administrator')", (account_id,),
        )
    assert identity_client.get("/test-only/role/author", headers=headers).status_code == 403
    assert identity_client.get("/test-only/role/learner", headers=headers).status_code == 403
    assert identity_client.get(f"/test-only/owner/{account_id}", headers=headers).status_code == 403
    assert identity_client.get("/api/v1/me", headers=headers).json()["roles"] == ["administrator"]
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("UPDATE quezo.accounts SET status = 'disabled' WHERE id = %s", (account_id,))
    assert identity_client.get("/api/v1/me", headers=headers).json()["code"] == "ACCOUNT_DISABLED"
    assert peer.requests == 1


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Basic synthetic-secret"}, {"Authorization": "Bearer"},
    {"Authorization": "Bearer not-a-token"},
])
def test_missing_malformed_identity_denied(identity_client: TestClient, headers: dict[str, str]) -> None:
    response = identity_client.get("/api/v1/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_outages_never_authenticate_or_leak_tokens(
    identity_client: TestClient, peer: SigningPeer, caplog: pytest.LogCaptureFixture,
) -> None:
    peer.status = 503
    token = peer.token()
    response = identity_client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"
    assert token not in response.text + caplog.text
    assert SUBJECT not in response.text + caplog.text


def test_database_outage_does_not_reuse_previous_actor(
    database: IsolatedDatabase, identity_client: TestClient, peer: SigningPeer,
) -> None:
    seed_account(database)
    headers = {"Authorization": f"Bearer {peer.token()}"}
    assert identity_client.get("/api/v1/me", headers=headers).status_code == 200
    with psycopg.connect(database.migration_url, autocommit=True) as connection:
        connection.execute(
            psycopg.sql.SQL("REVOKE CONNECT ON DATABASE {} FROM quezo_runtime").format(
                psycopg.sql.Identifier(database.name),
            ),
        )
    params = validate_test_admin_url(os.environ["QUEZO_TEST_ADMIN_URL"])
    with psycopg.connect(make_conninfo(**params), autocommit=True) as admin:
        admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND usename = 'quezo_runtime'", (database.name,),
        )
    response = identity_client.get("/api/v1/me", headers=headers)
    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"
    assert peer.requests == 1


def test_duplicate_bearers_and_invalid_signature_are_unauthenticated(
    identity_client: TestClient, peer: SigningPeer,
) -> None:
    headers = [("Authorization", f"Bearer {peer.token()}")] * 2
    assert identity_client.get("/api/v1/me", headers=headers).status_code == 401
    headers = [("Authorization", f"Bearer {SigningPeer().token()}")]
    assert identity_client.get("/api/v1/me", headers=headers).status_code == 401


@pytest.mark.anyio
async def test_helpers_reject_disabled_and_missing_owner() -> None:
    from quezo_api.errors import ApiError, ErrorCode

    actor = Actor.model_validate({"userId": uuid4(), "roles": ["author"], "status": "active"})
    with pytest.raises(ApiError) as error:
        require_owner(actor, None, Role.AUTHOR)
    assert error.value.code == ErrorCode.NOT_FOUND
    actor.status = AccessStatus.DISABLED
    with pytest.raises(ApiError) as error:
        require_role(actor, Role.AUTHOR)
    assert error.value.code == ErrorCode.ACCOUNT_DISABLED
