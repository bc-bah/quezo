import json

import httpx2 as httpx
import pytest

from keycloak_helpers import KeycloakLocal, local_origin
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.provisioning import ACCOUNTS


@pytest.mark.parametrize("origin", [
    "https://external.invalid", "http://external.invalid", "http://user:pass@localhost",
    "http://localhost/path", "http://localhost?next=external", "http://localhost/",
])
def test_provisioner_is_loopback_only(origin: str) -> None:
    with pytest.raises(ValueError):
        local_origin(origin)


@pytest.mark.anyio
@pytest.mark.parametrize("failure", ["create", "password", "enable", "readback", "foreign-user", "network"])
async def test_local_identity_operations_fail_closed(
    monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    monkeypatch.setenv("QUEZO_SYNTHETIC_PASSWORD", "synthetic-password-not-for-real-use")
    account = ACCOUNTS["administrator"]
    calls: list[str] = []
    created = False

    def serve(request: httpx.Request) -> httpx.Response:
        nonlocal created
        calls.append(f"{request.method} {request.url.path}")
        if failure == "network":
            raise httpx.ConnectError("secret", request=request)
        if request.method == "GET" and request.url.query:
            users: list[object] = []
            if failure == "foreign-user":
                users = [{"id": "foreign"}]
            elif created:
                users = [{
                    "id": "c8293778-d759-466c-b84b-a1d027ee45fb", "username": account.username,
                    "attributes": {"quezo-local-fixture": ["I01"]},
                }]
            return httpx.Response(200, json=users)
        if request.method == "POST":
            created = True
            assert json.loads(request.content)["enabled"] is False
            return httpx.Response(503 if failure == "create" else 201)
        if request.url.path.endswith("reset-password"):
            return httpx.Response(503 if failure == "password" else 204)
        if request.method == "PUT":
            return httpx.Response(503 if failure == "enable" else 204)
        return httpx.Response(200, json={
            "id": "c8293778-d759-466c-b84b-a1d027ee45fb", "username": account.username,
            "enabled": False, "attributes": {"quezo-local-fixture": ["I01"]},
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
        provider = KeycloakLocal(client, "http://localhost:58080")
        with pytest.raises(ApiError) as error:
            await provider.establish(account)
        assert error.value.code in {ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.INVALID_STATE}
    if failure == "foreign-user":
        assert len(calls) == 1


def test_realm_configuration_has_no_secrets_or_bypasses() -> None:
    from pathlib import Path

    config = json.loads((Path(__file__).resolve().parents[2] / "infra" / "keycloak" / "realm.json").read_text())
    assert "users" not in config
    assert config["registrationAllowed"] is False
    assert config["accessTokenLifespan"] == 300
    client = config["clients"][0]
    assert "secret" not in client
    assert client["publicClient"] is False
    for key in ("directAccessGrantsEnabled", "implicitFlowEnabled", "serviceAccountsEnabled", "fullScopeAllowed"):
        assert client[key] is False
    assert client["redirectUris"] == ["http://localhost:3000/auth/callback"]
    assert client["attributes"] == {
        "pkce.code.challenge.method": "S256",
        "post.logout.redirect.uris": "http://localhost:3000",
    }
    mapper = config["clientScopes"][0]["protocolMappers"][0]["config"]
    assert mapper["included.custom.audience"] == "quezo-api"
    assert mapper["id.token.claim"] == "false"
