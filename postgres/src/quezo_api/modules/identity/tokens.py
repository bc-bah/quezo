import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Self
from urllib.parse import urlsplit

import httpx2 as httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator

from quezo_api.errors import ApiError, ErrorCode

MAX_TOKEN_BYTES = 32768
MAX_JWKS_BYTES = 65536
MAX_JWKS_KEYS = 32


class IdentitySettings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    issuer: str = Field(min_length=1, max_length=2048)
    audience: str
    timeout: float = Field(default=5, gt=0, le=10, allow_inf_nan=False)
    cache_seconds: int = Field(default=300, ge=10, le=600)
    refresh_seconds: int = Field(default=10, ge=1, le=60)
    max_lifetime: int = Field(default=300, ge=60, le=900)

    @model_validator(mode="after")
    def validate_settings(self) -> Self:
        url = urlsplit(self.issuer)
        if (
            url.scheme not in {"https", "http"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or self.issuer.endswith("/")
            or not url.path.startswith("/realms/")
            or (url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"})
        ):
            raise ValueError("An exact HTTPS Keycloak issuer (HTTP loopback only) is required")
        if not self.audience or len(self.audience) > 200 or any(c.isspace() for c in self.audience):
            raise ValueError("An explicit API audience is required")
        if self.refresh_seconds > self.cache_seconds:
            raise ValueError("Refresh interval must not exceed cache lifetime")
        return self

    @classmethod
    def from_env(cls) -> Self:
        values: dict[str, object] = {
            "issuer": os.environ.get("QUEZO_OIDC_ISSUER"),
            "audience": os.environ.get("QUEZO_API_AUDIENCE"),
        }
        for field in ("timeout", "cache_seconds", "refresh_seconds", "max_lifetime"):
            if (value := os.environ.get(f"QUEZO_IDENTITY_{field.upper()}")) is not None:
                values[field] = value
        return cls.model_validate(values)


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str


class TokenVerifier:
    """One bounded JWKS cache per lifespan; no actor or role cache."""

    def __init__(self, settings: IdentitySettings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self._client = client
        self._keys: dict[str, jwt.PyJWK] = {}
        self._expires_at = 0.0
        self._refresh_after = 0.0
        self._failed = False
        self._lock = asyncio.Lock()

    async def _refresh(self) -> None:
        try:
            async with self._client.stream(
                "GET", f"{self.settings.issuer}/protocol/openid-connect/certs",
                follow_redirects=False,
            ) as response:
                if response.status_code != 200:
                    raise ValueError("JWKS unavailable")
                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    body.extend(chunk)
                    if len(body) > MAX_JWKS_BYTES:
                        raise ValueError("JWKS exceeds limit")
            document = json.loads(body)
            if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
                raise ValueError("Invalid JWKS")
            entries = document["keys"]
            if not 1 <= len(entries) <= MAX_JWKS_KEYS:
                raise ValueError("Invalid JWKS key count")
            keys: dict[str, jwt.PyJWK] = {}
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("Invalid JWK")
                if entry.get("use") != "sig" or entry.get("alg") != "RS256":
                    continue
                kid = entry.get("kid")
                if (
                    not isinstance(kid, str) or not 1 <= len(kid) <= 200
                    or kid in keys or entry.get("kty") != "RSA"
                    or "d" in entry
                    or ("key_ops" in entry and entry["key_ops"] != ["verify"])
                ):
                    raise ValueError("Invalid signing key")
                key = jwt.PyJWK(entry, algorithm="RS256")
                if not isinstance(key.key, RSAPublicKey) or not 2048 <= key.key.key_size <= 8192:
                    raise ValueError("Invalid RSA key size")
                keys[kid] = key
            if not keys:
                raise ValueError("No supported signing keys")
        except asyncio.CancelledError:
            self._failed = True
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError, jwt.PyJWTError):
            self._failed = True
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None
        self._keys = keys
        self._expires_at = time.monotonic() + self.settings.cache_seconds
        self._failed = False

    async def _key(self, kid: str) -> jwt.PyJWK:
        async with self._lock:
            now = time.monotonic()
            if now < self._expires_at and kid in self._keys:
                return self._keys[kid]
            if now >= self._refresh_after:
                self._refresh_after = now + self.settings.refresh_seconds
                try:
                    await self._refresh()
                except TimeoutError:
                    self._failed = True
                    raise
            if self._failed or time.monotonic() >= self._expires_at:
                raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
            if kid not in self._keys:
                raise ApiError(ErrorCode.UNAUTHENTICATED)
            return self._keys[kid]

    async def verify(self, token: str) -> VerifiedIdentity:
        try:
            if not token.isascii() or len(token) > MAX_TOKEN_BYTES:
                raise jwt.InvalidTokenError()
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if (
                header.get("alg") != "RS256"
                or not isinstance(kid, str) or not 1 <= len(kid) <= 200
                or any(name in header for name in ("jku", "x5u", "jwk", "crit", "b64"))
            ):
                raise jwt.InvalidTokenError()
            # Includes lock/queue wait and the complete streamed response, not just socket reads.
            async with asyncio.timeout(self.settings.timeout):
                key = await self._key(kid)
            claims = jwt.decode(
                token, key.key, algorithms=["RS256"],
                issuer=self.settings.issuer, audience=self.settings.audience,
                options={"require": ["iss", "aud", "sub", "exp", "iat", "typ"]},
                leeway=0,
            )
            subject = claims["sub"]
            if (
                not isinstance(subject, str) or not subject.strip()
                or len(subject) > 255 or any(ord(c) < 32 for c in subject)
                or claims["typ"] != "Bearer"
                or type(claims["exp"]) is not int or type(claims["iat"]) is not int
                or ("nbf" in claims and type(claims["nbf"]) is not int)
                or not 0 < claims["exp"] - claims["iat"] <= self.settings.max_lifetime
            ):
                raise jwt.InvalidTokenError()
            return VerifiedIdentity(self.settings.issuer, subject)
        except (jwt.PyJWTError, ValueError, TypeError, OverflowError):
            raise ApiError(ErrorCode.UNAUTHENTICATED) from None
        except TimeoutError:
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None
