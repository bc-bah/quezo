import asyncio
import json
import os
from typing import Self
from urllib.parse import quote
from uuid import UUID

import httpx2 as httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.tokens import IdentitySettings

MAX_RESPONSE_BYTES = 65536


class AccountAdminSettings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    issuer: str = Field(min_length=1, max_length=2048)
    client_id: str = Field(min_length=1, max_length=200)
    client_secret: SecretStr = Field(min_length=32, repr=False)
    timeout: float = Field(default=5, gt=0, le=10, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_issuer(self) -> Self:
        identity = IdentitySettings(issuer=self.issuer, audience="quezo-api")
        if (
            not identity.issuer.endswith("/realms/quezo-local")
            or self.client_id != "quezo-account-admin"
        ):
            raise ValueError("Account administration is restricted to the local realm")
        return self

    @classmethod
    def from_env(cls) -> Self | None:
        client_id = os.environ.get("QUEZO_ACCOUNT_ADMIN_CLIENT_ID")
        client_secret = os.environ.get("QUEZO_ACCOUNT_ADMIN_CLIENT_SECRET")
        if not client_id and not client_secret:
            return None
        if not client_id or not client_secret:
            raise ValueError("Both account-administration client settings are required")
        return cls.model_validate({
            "issuer": os.environ.get("QUEZO_OIDC_ISSUER"),
            "client_id": client_id,
            "client_secret": client_secret,
        })


class KeycloakAccountAdmin:
    def __init__(self, settings: AccountAdminSettings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client
        issuer = settings.issuer
        self.realm_url = issuer[:issuer.rfind("/realms/")] + "/admin" + issuer[issuer.rfind("/realms/"):]

    async def _read(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, object] | None = None,
        form: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        expected: tuple[int, ...],
    ) -> tuple[int, bytes, httpx.Headers]:
        try:
            async with asyncio.timeout(self.settings.timeout):
                async with self.client.stream(
                    method, url, headers=headers, json=json_body, data=form,
                    params=params, follow_redirects=False,
                ) as response:
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
                    if response.status_code not in expected:
                        raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
                    return response.status_code, bytes(body), response.headers
        except ApiError:
            raise
        except (httpx.HTTPError, TimeoutError):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None

    async def _token(self) -> str:
        _, body, _ = await self._read(
            "POST",
            f"{self.settings.issuer}/protocol/openid-connect/token",
            form={
                "grant_type": "client_credentials",
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret.get_secret_value(),
            },
            expected=(200,),
        )
        try:
            value = json.loads(body)
            token = value["access_token"]
            if not isinstance(token, str) or not token or len(token) > 32768:
                raise ValueError
            return token
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None

    def _user_url(self, user_id: str | None = None) -> str:
        base = f"{self.realm_url}/users"
        return base if user_id is None else f"{base}/{quote(user_id, safe='')}"

    async def _user(self, user_id: str, token: str) -> dict[str, object]:
        _, body, _ = await self._read(
            "GET", self._user_url(user_id), headers={"Authorization": f"Bearer {token}"},
            expected=(200,),
        )
        try:
            user = json.loads(body)
            if not isinstance(user, dict):
                raise ValueError
            return user
        except (json.JSONDecodeError, ValueError):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None

    async def _find(self, username: str, token: str) -> dict[str, object] | None:
        _, body, _ = await self._read(
            "GET", self._user_url(), headers={"Authorization": f"Bearer {token}"},
            params={"username": username, "exact": "true", "max": "2"},
            expected=(200,),
        )
        try:
            users = json.loads(body)
            if not isinstance(users, list) or len(users) > 1:
                raise ValueError
            if not users:
                return None
            user = users[0]
            if not isinstance(user, dict) or user.get("username") != username:
                raise ValueError
            return user
        except (json.JSONDecodeError, ValueError):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None

    @staticmethod
    def _verify_owner(user: dict[str, object], account_id: str) -> str:
        user_id = user.get("id")
        attributes = user.get("attributes")
        marker = attributes.get("quezoAccountId") if isinstance(attributes, dict) else None
        if (
            not isinstance(user_id, str) or not user_id
            or marker != [account_id]
        ):
            raise ApiError(ErrorCode.INVALID_STATE)
        try:
            UUID(user_id)
        except ValueError:
            raise ApiError(ErrorCode.INVALID_STATE) from None
        return user_id

    async def ensure_disabled_user(
        self, account_id: str, username: str, email: str | None,
    ) -> tuple[str, str]:
        token = await self._token()
        user = await self._find(username, token)
        if user is None:
            payload: dict[str, object] = {
                "username": username,
                "enabled": False,
                "attributes": {"quezoAccountId": [account_id]},
            }
            if email is not None:
                payload["email"] = email
            status, _, _ = await self._read(
                "POST", self._user_url(), headers={"Authorization": f"Bearer {token}"},
                json_body=payload, expected=(201, 409),
            )
            user = await self._find(username, token)
            if user is None or (status == 409 and user.get("enabled") is True):
                raise ApiError(ErrorCode.INVALID_STATE)
        user_id = self._verify_owner(user, account_id)
        if user.get("enabled") is True:
            raise ApiError(ErrorCode.INVALID_STATE)
        current = await self._user(user_id, token)
        self._verify_owner(current, account_id)
        if current.get("enabled") is True:
            raise ApiError(ErrorCode.INVALID_STATE)
        payload = {
            **current,
            "username": username,
            "enabled": False,
            "attributes": {"quezoAccountId": [account_id]},
        }
        if email is None:
            payload.pop("email", None)
        else:
            payload["email"] = email
        await self._read(
            "PUT", self._user_url(user_id), headers={"Authorization": f"Bearer {token}"},
            json_body=payload, expected=(204,),
        )
        verified = await self._user(user_id, token)
        self._verify_owner(verified, account_id)
        if (
            verified.get("enabled") is not False
            or verified.get("username") != username
            or verified.get("email") != email
        ):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        return self.settings.issuer, user_id

    async def set_enabled(self, account_id: str, subject: str, enabled: bool) -> None:
        try:
            UUID(subject)
        except ValueError:
            raise ApiError(ErrorCode.INVALID_STATE) from None
        token = await self._token()
        current = await self._user(subject, token)
        attributes = current.get("attributes")
        managed_id = (
            attributes.get("quezoAccountId")
            if isinstance(attributes, dict) else None
        )
        legacy_fixture = (
            attributes.get("quezo-local-fixture")
            if isinstance(attributes, dict) else None
        )
        if managed_id not in ([account_id], None) or (
            managed_id is None and legacy_fixture != ["I01"]
        ):
            raise ApiError(ErrorCode.INVALID_STATE)
        if current.get("id") != subject:
            raise ApiError(ErrorCode.INVALID_STATE)
        current["enabled"] = enabled
        await self._read(
            "PUT", self._user_url(subject), headers={"Authorization": f"Bearer {token}"},
            json_body=current, expected=(204,),
        )
        verified = await self._user(subject, token)
        verified_attributes = verified.get("attributes")
        verified_managed_id = (
            verified_attributes.get("quezoAccountId")
            if isinstance(verified_attributes, dict) else None
        )
        verified_legacy_fixture = (
            verified_attributes.get("quezo-local-fixture")
            if isinstance(verified_attributes, dict) else None
        )
        if (
            verified.get("id") != subject
            or verified_managed_id not in ([account_id], None)
            or (
                verified_managed_id is None
                and verified_legacy_fixture != ["I01"]
            )
            or verified.get("enabled") is not enabled
        ):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
