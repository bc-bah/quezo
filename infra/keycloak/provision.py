"""Explicit loopback-only synthetic provisioning; never imported by the API."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import httpx2 as httpx
import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg_pool import PoolTimeout
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "postgres" / "src"))

from quezo_api.database import Database, DatabaseSettings, database_loop_factory
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.provisioning import ACCOUNTS, SyntheticAccount, provision_account
from quezo_api.modules.identity.tokens import VerifiedIdentity


def local_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None or parsed.password is not None
        or parsed.path or parsed.query or parsed.fragment
    ):
        raise ValueError("KEYCLOAK_LOCAL_ORIGIN must be an exact loopback HTTP origin")
    return value


def secret(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) < 16:
        raise ValueError(f"{name} requires at least 16 characters")
    return value


class KeycloakLocal:
    def __init__(self, client: httpx.AsyncClient, origin: str) -> None:
        self.client = client
        self.origin = origin
        self.issuer = f"{origin}/realms/quezo-local"
        self.authorization: dict[str, str] = {}

    async def request(
        self, method: str, path: str, *, data: dict[str, str] | None = None,
        payload: object = None, expected: int = 200,
    ) -> object:
        try:
            async with asyncio.timeout(5):
                async with self.client.stream(
                    method, self.origin + path, headers=self.authorization,
                    data=data, json=payload, follow_redirects=False,
                ) as response:
                    if response.status_code != expected:
                        if response.status_code == 409:
                            raise ApiError(ErrorCode.INVALID_STATE)
                        raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 65536:
                            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
                    if not body:
                        return None
                    return json.loads(body)
        except (httpx.HTTPError, TimeoutError, ValueError):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None

    async def login(self) -> None:
        result = await self.request(
            "POST", "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password", "client_id": "admin-cli",
                "username": os.environ.get("KEYCLOAK_ADMIN", "quezo-admin"),
                "password": secret("KEYCLOAK_ADMIN_PASSWORD"),
            },
        )
        if not isinstance(result, dict) or not isinstance(result.get("access_token"), str):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        self.authorization = {"Authorization": f"Bearer {result['access_token']}"}

    async def setup_realm(self) -> None:
        config = json.loads(Path(__file__).with_name("realm.json").read_text())
        config["clients"][0]["secret"] = secret("QUEZO_OIDC_CLIENT_SECRET")
        await self.request("POST", "/admin/realms", payload=config, expected=201)
        profile = await self.request("GET", "/admin/realms/quezo-local/users/profile")
        if not isinstance(profile, dict):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        # Only administrators may maintain the synthetic-provisioning marker.
        profile["unmanagedAttributePolicy"] = "ADMIN_EDIT"
        await self.request("PUT", "/admin/realms/quezo-local/users/profile", payload=profile)

    async def establish(self, account: SyntheticAccount) -> VerifiedIdentity:
        password = secret("QUEZO_SYNTHETIC_PASSWORD")
        users = await self.request(
            "GET", f"/admin/realms/quezo-local/users?username={account.username}&exact=true",
        )
        if not isinstance(users, list):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        marker = {"quezo-local-fixture": ["I01"]}
        if not users:
            await self.request(
                "POST", "/admin/realms/quezo-local/users", expected=201,
                payload={
                    "username": account.username, "enabled": False,
                    "firstName": "Quezo", "lastName": "Synthetic",
                    "email": f"{account.username}@example.invalid",
                    "attributes": marker,
                },
            )
            users = await self.request(
                "GET", f"/admin/realms/quezo-local/users?username={account.username}&exact=true",
            )
        if (
            not isinstance(users, list)
            or len(users) != 1 or not isinstance(users[0], dict)
            or users[0].get("username") != account.username
            or users[0].get("attributes") != marker
        ):
            raise ApiError(ErrorCode.INVALID_STATE)
        subject = users[0].get("id")
        if not isinstance(subject, str):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        try:
            UUID(subject)
        except ValueError:
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE) from None
        path = f"/admin/realms/quezo-local/users/{subject}"
        await self.request(
            "PUT", path + "/reset-password", expected=204,
            payload={"type": "password", "value": password, "temporary": False},
        )
        await self.request(
            "PUT", path, expected=204,
            payload={
                "enabled": True, "firstName": "Quezo", "lastName": "Synthetic",
                "email": f"{account.username}@example.invalid",
            },
        )
        user = await self.request("GET", path)
        if (
            not isinstance(user, dict) or user.get("id") != subject
            or user.get("username") != account.username or user.get("enabled") is not True
            or user.get("attributes") != marker or user.get("requiredActions")
        ):
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        return VerifiedIdentity(self.issuer, subject)


async def run(setup: bool, account: str | None) -> None:
    origin = local_origin(os.environ.get("KEYCLOAK_LOCAL_ORIGIN", "http://localhost:8080"))
    async with httpx.AsyncClient(
        timeout=5, trust_env=False, follow_redirects=False,
        limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
    ) as client:
        provider = KeycloakLocal(client, origin)
        await provider.login()
        if setup:
            await provider.setup_realm()
            print("Local synthetic realm created; no application grants.")
        else:
            settings = DatabaseSettings.from_env()
            params = conninfo_to_dict(settings.url.get_secret_value())
            if (
                params.get("host") not in {"localhost", "127.0.0.1", "::1"}
                or set(params) - {"host", "port", "dbname", "user", "password"}
                or any(os.environ.get(key) for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"))
                or os.environ.get("QUEZO_OIDC_ISSUER") != provider.issuer
            ):
                raise ValueError("Local database and matching issuer are required")
            if account is None:
                raise ValueError("An allowlisted synthetic account is required")
            async with Database(settings) as database:
                account_id = await provision_account(database, provider, provider.issuer, account)
            print(f"Local provisioning succeeded: application account {account_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-local-synthetic", required=True, action="store_true")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup-realm", action="store_true")
    group.add_argument("--account", choices=ACCOUNTS)
    args = parser.parse_args()
    try:
        with asyncio.Runner(loop_factory=database_loop_factory) as runner:
            runner.run(run(args.setup_realm, args.account))
    except ApiError as error:
        print(f"Local provisioning failed: {error.code.value}; no new application grant committed.", file=sys.stderr)
        return 1
    except (ValueError, ValidationError, psycopg.Error, PoolTimeout):
        print("Local provisioning failed: configuration/database failure; no new grant committed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
