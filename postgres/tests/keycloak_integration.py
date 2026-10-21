"""Explicit real Keycloak HTTP/code+PKCE evidence, not a real-browser I02 test."""

import base64
import hashlib
import os
import secrets
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import httpx2 as httpx
import pytest
from pydantic import SecretStr

from db_helpers import IsolatedDatabase
from keycloak_helpers import KeycloakLocal, local_origin
from quezo_api.app import create_app
from quezo_api.database import Database, DatabaseSettings
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.provisioning import ACCOUNTS, SyntheticAccount, provision_account
from quezo_api.modules.identity.tokens import IdentitySettings, TokenVerifier


class LoginForm(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.action: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "form" and values.get("id") == "kc-form-login":
            self.action = values.get("action")


async def login(origin: str, account: SyntheticAccount) -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    redirect = "http://localhost:3000/auth/callback"
    async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as client:
        response = await client.get(
            f"{origin}/realms/quezo-local/protocol/openid-connect/auth",
            params={
                "client_id": "quezo-web", "redirect_uri": redirect, "response_type": "code",
                "scope": "openid quezo-api", "state": state, "nonce": nonce,
                "code_challenge": challenge, "code_challenge_method": "S256",
            },
        )
        assert response.status_code == 200
        form = LoginForm()
        form.feed(response.text)
        assert form.action is not None
        assert urlsplit(form.action).netloc == urlsplit(origin).netloc
        assert urlsplit(form.action).scheme == "http"
        # Keycloak treats localhost as a secure context, as browsers do. HTTPX's
        # cookie jar does not; replay only this server's login cookies to this origin.
        cookies = "; ".join(
            f"{cookie.name}={cookie.value}" for cookie in client.cookies.jar
            if cookie.path == "/realms/quezo-local/"
        )
        response = await client.post(
            form.action, headers={"Cookie": cookies}, data={
                "username": account.username, "password": os.environ["QUEZO_SYNTHETIC_PASSWORD"],
                "credentialId": "",
            },
        )
        assert response.status_code == 302, "Synthetic Keycloak login did not complete"
        callback = urlsplit(response.headers["location"])
        assert f"{callback.scheme}://{callback.netloc}{callback.path}" == redirect
        params = parse_qs(callback.query)
        assert params["state"] == [state]
        response = await client.post(
            f"{origin}/realms/quezo-local/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code", "client_id": "quezo-web",
                "client_secret": os.environ["QUEZO_OIDC_CLIENT_SECRET"],
                "redirect_uri": redirect, "code": params["code"][0], "code_verifier": verifier,
            },
        )
        assert response.status_code == 200
        tokens = response.json()
        assert isinstance(tokens["access_token"], str)
        assert isinstance(tokens["id_token"], str)
        return tokens["access_token"], tokens["id_token"]


@pytest.mark.anyio
async def test_real_keycloak_provisioning_tokens_and_current_access(
    database: IsolatedDatabase,
) -> None:
    origin = local_origin(os.environ["KEYCLOAK_LOCAL_ORIGIN"])
    # This explicit suite requires its own disposable test service, not default development.
    assert urlsplit(origin).port not in {None, 80, 443, 8080}
    issuer = f"{origin}/realms/quezo-local"
    settings = IdentitySettings(issuer=issuer, audience="quezo-api")
    async with httpx.AsyncClient(timeout=5, trust_env=False, follow_redirects=False) as transport:
        provider = KeycloakLocal(transport, origin)
        await provider.login()
        await provider.setup_realm()  # Refuses an existing realm; cleanup owns only this creation.
        try:
            discovery = await transport.get(issuer + "/.well-known/openid-configuration")
            assert discovery.status_code == 200
            assert discovery.json()["issuer"] == issuer
            async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
                app = create_app()
                app.state.database = db
                app.state.token_verifier = TokenVerifier(settings, transport)
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://api.test",
                ) as api:
                    for name, account in ACCOUNTS.items():
                        account_id = await provision_account(db, provider, issuer, name)
                        token, id_token = await login(origin, account)
                        headers = {"Authorization": f"Bearer {token}"}
                        response = await api.get("/api/v1/me", headers=headers)
                        assert response.status_code == 200
                        assert response.json() == {
                            "userId": str(account_id), "roles": sorted(account.roles), "status": "active",
                        }
                        assert token not in response.text and issuer not in response.text
                        response = await api.get("/api/v1/me", headers={"Authorization": f"Bearer {id_token}"})
                        assert response.status_code == 401
                        async with db.transaction() as connection:
                            await connection.execute("DELETE FROM quezo.account_roles WHERE account_id = %s", (account_id,))
                        assert (await api.get("/api/v1/me", headers=headers)).json()["roles"] == []
                        async with db.transaction() as connection:
                            await connection.execute("UPDATE quezo.accounts SET status = 'disabled' WHERE id = %s", (account_id,))
                        assert (await api.get("/api/v1/me", headers=headers)).json()["code"] == "ACCOUNT_DISABLED"
                        with pytest.raises(ApiError) as error:
                            await provision_account(db, provider, issuer, name)
                        assert error.value.code == ErrorCode.INVALID_STATE
                    # No password/direct grant bypass is enabled on the actual web client.
                    denied = await transport.post(
                        issuer + "/protocol/openid-connect/token", data={
                            "grant_type": "password", "client_id": "quezo-web",
                            "client_secret": os.environ["QUEZO_OIDC_CLIENT_SECRET"],
                            "username": ACCOUNTS["learner"].username,
                            "password": os.environ["QUEZO_SYNTHETIC_PASSWORD"],
                        },
                    )
                    assert denied.status_code == 400
        finally:
            await provider.request("DELETE", "/admin/realms/quezo-local", expected=204)
