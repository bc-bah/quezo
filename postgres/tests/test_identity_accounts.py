import asyncio
from collections.abc import Iterator
from uuid import UUID, uuid4

import httpx2 as httpx
import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from db_helpers import IsolatedDatabase
from identity_helpers import SETTINGS, SUBJECT, SigningPeer, seed_account
from quezo_api.app import create_app
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.account_admin import AccountAdminSettings, KeycloakAccountAdmin
from quezo_api.modules.identity.tokens import TokenVerifier

pytestmark = pytest.mark.anyio

ADMIN_SECRET = "synthetic-account-administration-test-secret"


class FakeAccountAdmin(KeycloakAccountAdmin):
    def __init__(self) -> None:
        super().__init__(
            AccountAdminSettings(
                issuer=SETTINGS.issuer, client_id="quezo-account-admin",
                client_secret=SecretStr(ADMIN_SECRET),
            ),
            httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))),
        )
        self.users: dict[str, tuple[str, str, str | None, bool]] = {}
        self.fail_provision = False
        self.fail_status = False
        self.create_count = 0

    async def close(self) -> None:
        await self.client.aclose()

    async def ensure_disabled_user(
        self, account_id: str, username: str, email: str | None,
    ) -> tuple[str, str]:
        existing = self.users.get(account_id)
        if existing is None:
            subject = f"synthetic-{account_id}"
            self.users[account_id] = (subject, username, email, False)
            self.create_count += 1
        else:
            subject = existing[0]
        if self.fail_provision:
            self.fail_provision = False
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        return SETTINGS.issuer, subject

    async def set_enabled(self, account_id: str, subject: str, enabled: bool) -> None:
        if self.fail_status:
            self.fail_status = False
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        existing = self.users[account_id]
        assert existing[0] == subject
        self.users[account_id] = (subject, existing[1], existing[2], enabled)


@pytest.fixture
def admin_client(
    database: IsolatedDatabase,
    monkeypatch: pytest.MonkeyPatch,
    peer: SigningPeer,
) -> Iterator[tuple[TestClient, FakeAccountAdmin]]:
    monkeypatch.setenv("QUEZO_DATABASE_URL", database.runtime_url)
    app = create_app()

    with TestClient(app, backend_options={"loop_factory": asyncio.SelectorEventLoop}) as client:
        provider = FakeAccountAdmin()

        async def install() -> httpx.AsyncClient:
            identity_client = httpx.AsyncClient(transport=httpx.MockTransport(peer.serve))
            app.state.token_verifier = TokenVerifier(SETTINGS, identity_client)
            app.state.account_admin = provider
            return identity_client

        assert client.portal is not None
        identity_client = client.portal.call(install)
        try:
            yield client, provider
        finally:
            client.portal.call(identity_client.aclose)
            client.portal.call(provider.close)


@pytest.fixture
def peer() -> SigningPeer:
    return SigningPeer()


def headers(peer: SigningPeer, subject: str = SUBJECT) -> dict[str, str]:
    claims = peer.claims()
    claims["sub"] = subject
    return {"Authorization": f"Bearer {peer.token(claims)}"}


@pytest.mark.parametrize("roles", [
    ["administrator"], ["author"], ["learner"],
])
def test_admin_provisions_each_application_role_in_disabled_state(
    database: IsolatedDatabase,
    admin_client: tuple[TestClient, FakeAccountAdmin],
    peer: SigningPeer,
    roles: list[str],
) -> None:
    seed_account(database, roles=("administrator",))
    client, provider = admin_client
    response = client.post(
        "/api/v1/admin/accounts",
        json={"username": f"synthetic-{roles[0]}", "email": None, "roles": roles},
        headers=headers(peer),
    )
    assert response.status_code == 201
    account = response.json()
    assert account["roles"] == roles
    assert account["status"] == "disabled"
    assert account["provisioningState"] == "complete"
    assert account["identitySyncState"] == "in_sync"
    assert provider.create_count == 1
    assert client.post(
        "/api/v1/admin/accounts",
        json={"username": f"synthetic-{roles[0]}", "email": None, "roles": roles},
        headers=headers(peer),
    ).status_code == 409
    assert provider.create_count == 1


def test_partial_provisioning_is_ineligible_and_retry_is_idempotent(
    database: IsolatedDatabase,
    admin_client: tuple[TestClient, FakeAccountAdmin],
    peer: SigningPeer,
) -> None:
    seed_account(database, roles=("administrator",))
    client, provider = admin_client
    provider.fail_provision = True
    body = {"username": "synthetic-retry", "email": "retry@example.invalid", "roles": ["learner"]}

    failed = client.post("/api/v1/admin/accounts", json=body, headers=headers(peer))
    assert failed.status_code == 503
    listed = client.get("/api/v1/admin/accounts", headers=headers(peer)).json()["items"]
    partial = next(item for item in listed if item["username"] == body["username"])
    assert partial["status"] == "disabled"
    assert partial["provisioningState"] == "failed"
    assert partial["identityErrorCode"] == "DEPENDENCY_UNAVAILABLE"
    account_id = partial["userId"]
    subject = provider.users[str(UUID(account_id))][0]
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute(
            "SELECT count(*) FROM quezo.identity_mappings WHERE account_id = %s AND active",
            (account_id,),
        ).fetchone() == (0,)
    assert client.get("/api/v1/me", headers=headers(peer, subject)).status_code == 401

    retried = client.post("/api/v1/admin/accounts", json=body, headers=headers(peer))
    assert retried.status_code == 201
    assert retried.json()["userId"] == account_id
    assert provider.create_count == 1
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute(
            "SELECT count(*) FROM quezo.accounts WHERE id = %s", (account_id,),
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT action, outcome, error_code FROM quezo.account_admin_events "
            "WHERE target_id = %s ORDER BY id", (account_id,),
        ).fetchall() == [
            ("provision", "failure", "DEPENDENCY_UNAVAILABLE"),
            ("provision", "success", None),
        ]


def test_roles_status_last_admin_and_stale_token_revocation(
    database: IsolatedDatabase,
    admin_client: tuple[TestClient, FakeAccountAdmin],
    peer: SigningPeer,
) -> None:
    first_admin = seed_account(database, roles=("administrator",))
    client, _provider = admin_client
    authorization = headers(peer)
    assert client.post(
        f"/api/v1/admin/accounts/{first_admin}/deactivate", headers=authorization,
    ).status_code == 409
    assert client.put(
        f"/api/v1/admin/accounts/{first_admin}/roles",
        json={"roles": ["author"]}, headers=authorization,
    ).status_code == 409

    created = client.post(
        "/api/v1/admin/accounts",
        json={"username": "synthetic-second-admin", "roles": ["administrator"]},
        headers=authorization,
    )
    second_admin = created.json()["userId"]
    assert client.post(
        f"/api/v1/admin/accounts/{second_admin}/activate", headers=authorization,
    ).status_code == 200
    assert client.put(
        f"/api/v1/admin/accounts/{first_admin}/roles",
        json={"roles": ["author", "learner"]}, headers=authorization,
    ).status_code == 200
    assert client.get("/api/v1/admin/accounts", headers=authorization).status_code == 403
    second_subject = next(
        subject for subject, _username, _email, enabled in _provider_users(admin_client[1])
        if enabled
    )
    assert client.get(
        f"/api/v1/attempts/{uuid4()}/result", headers=headers(peer, second_subject),
    ).status_code == 403


def _provider_users(provider: FakeAccountAdmin) -> list[tuple[str, str, str | None, bool]]:
    return list(provider.users.values())


def test_deactivation_revokes_application_access_before_identity_sync(
    database: IsolatedDatabase,
    admin_client: tuple[TestClient, FakeAccountAdmin],
    peer: SigningPeer,
) -> None:
    seed_account(database, roles=("administrator",))
    client, provider = admin_client
    created = client.post(
        "/api/v1/admin/accounts",
        json={"username": "synthetic-author", "roles": ["author"]},
        headers=headers(peer),
    )
    account_id = created.json()["userId"]
    assert client.post(
        f"/api/v1/admin/accounts/{account_id}/activate", headers=headers(peer),
    ).status_code == 200
    provider.fail_status = True
    response = client.post(
        f"/api/v1/admin/accounts/{account_id}/deactivate", headers=headers(peer),
    )
    assert response.status_code == 503
    updated = next(
        item for item in client.get("/api/v1/admin/accounts", headers=headers(peer)).json()["items"]
        if item["userId"] == account_id
    )
    assert updated["status"] == "disabled"
    assert updated["identitySyncState"] == "failed"
    subject = provider.users[str(UUID(account_id))][0]
    assert client.get("/api/v1/me", headers=headers(peer, subject)).status_code == 401
    assert client.post(
        f"/api/v1/admin/accounts/{account_id}/deactivate", headers=headers(peer),
    ).status_code == 200
    assert provider.users[str(UUID(account_id))][3] is False


def test_administration_is_not_available_to_non_admin_roles(
    database: IsolatedDatabase,
    admin_client: tuple[TestClient, FakeAccountAdmin],
    peer: SigningPeer,
) -> None:
    client, _provider = admin_client
    author_id = seed_account(database, roles=("author",))
    learner_id = seed_account(database, roles=("learner",), subject="synthetic-learner")
    for subject in (SUBJECT, "synthetic-learner"):
        assert client.get("/api/v1/admin/accounts", headers=headers(peer, subject)).status_code == 403
    assert author_id != learner_id
