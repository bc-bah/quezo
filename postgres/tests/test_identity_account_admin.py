import json
from urllib.parse import parse_qs
from uuid import uuid4

import httpx2 as httpx
import pytest
from pydantic import SecretStr, ValidationError

from identity_helpers import SETTINGS
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.account_admin import AccountAdminSettings, KeycloakAccountAdmin

pytestmark = pytest.mark.anyio

CLIENT_SECRET = "synthetic-account-administration-test-secret"


def settings() -> AccountAdminSettings:
    return AccountAdminSettings(
        issuer=SETTINGS.issuer, client_id="quezo-account-admin",
        client_secret=SecretStr(CLIENT_SECRET),
    )


def test_account_admin_config_is_local_and_hides_secret() -> None:
    configured = settings()
    assert CLIENT_SECRET not in repr(configured)
    with pytest.raises(ValidationError):
        AccountAdminSettings(
            issuer="https://accounts.example.invalid/realms/customer",
            client_id="quezo-account-admin", client_secret=SecretStr(CLIENT_SECRET),
        )


async def test_keycloak_create_profile_retry_and_status_use_only_owned_disabled_user() -> None:
    account_id = str(uuid4())
    username = "synthetic-account-admin-probe"
    user_id = str(uuid4())
    user: dict[str, object] | None = None
    creates = 0
    enabled_updates: list[bool] = []

    def serve(request: httpx.Request) -> httpx.Response:
        nonlocal user, creates
        path = request.url.path
        if path.endswith("/protocol/openid-connect/token"):
            assert parse_qs(request.content.decode()) == {
                "grant_type": ["client_credentials"],
                "client_id": ["quezo-account-admin"],
                "client_secret": [CLIENT_SECRET],
            }
            return httpx.Response(200, json={"access_token": "synthetic-admin-token"})
        assert request.headers["authorization"] == "Bearer synthetic-admin-token"
        if path.endswith("/users") and request.method == "GET":
            return httpx.Response(200, json=[user] if user else [])
        if path.endswith("/users") and request.method == "POST":
            payload = json.loads(request.content)
            assert payload["enabled"] is False
            assert payload["attributes"] == {"quezoAccountId": [account_id]}
            user = {"id": user_id, **payload}
            creates += 1
            return httpx.Response(201)
        if path.endswith(f"/users/{user_id}") and request.method == "GET":
            return httpx.Response(200, json=user)
        if path.endswith(f"/users/{user_id}") and request.method == "PUT":
            payload = json.loads(request.content)
            user = {**(user or {}), **payload}
            enabled_updates.append(payload["enabled"])
            return httpx.Response(204)
        raise AssertionError(f"Unexpected Keycloak request: {request.method} {path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
        provider = KeycloakAccountAdmin(settings(), client)
        issuer, subject = await provider.ensure_disabled_user(account_id, username, None)
        retry_issuer, retry_subject = await provider.ensure_disabled_user(account_id, username, None)
        await provider.set_enabled(account_id, subject, True)
        await provider.set_enabled(account_id, subject, False)

    assert (issuer, retry_issuer) == (SETTINGS.issuer, SETTINGS.issuer)
    assert retry_subject == subject == user_id
    assert creates == 1
    assert enabled_updates == [False, False, True, False]


async def test_keycloak_refuses_a_preexisting_foreign_user() -> None:
    account_id = str(uuid4())
    requests: list[str] = []

    def serve(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/protocol/openid-connect/token"):
            return httpx.Response(200, json={"access_token": "synthetic-admin-token"})
        requests.append(request.method)
        return httpx.Response(200, json=[{
            "id": str(uuid4()), "username": "synthetic-foreign",
            "attributes": {"quezoAccountId": ["another-account"]}, "enabled": False,
        }])

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
        provider = KeycloakAccountAdmin(settings(), client)
        with pytest.raises(ApiError) as error:
            await provider.ensure_disabled_user(account_id, "synthetic-foreign", None)
    assert error.value.code == ErrorCode.INVALID_STATE
    assert requests == ["GET"]


async def test_mapped_legacy_synthetic_user_can_be_disabled_safely() -> None:
    account_id = str(uuid4())
    subject = str(uuid4())
    user: dict[str, object] = {
        "id": subject, "username": "quezo-test-learner", "enabled": True,
        "attributes": {"quezo-local-fixture": ["I01"]},
    }

    def serve(request: httpx.Request) -> httpx.Response:
        nonlocal user
        path = request.url.path
        if path.endswith("/protocol/openid-connect/token"):
            return httpx.Response(200, json={"access_token": "synthetic-admin-token"})
        if request.method == "GET":
            return httpx.Response(200, json=user)
        if request.method == "PUT":
            user = {**user, **json.loads(request.content)}
            return httpx.Response(204)
        raise AssertionError(f"Unexpected Keycloak request: {request.method} {path}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
        provider = KeycloakAccountAdmin(settings(), client)
        await provider.set_enabled(account_id, subject, False)
    assert user["enabled"] is False
