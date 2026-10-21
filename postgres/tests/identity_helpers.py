import json
import time
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import httpx2 as httpx
import jwt
import psycopg
from cryptography.hazmat.primitives.asymmetric import rsa

from db_helpers import IsolatedDatabase
from quezo_api.modules.identity.tokens import IdentitySettings

SETTINGS = IdentitySettings(issuer="http://localhost:8080/realms/quezo-local", audience="quezo-api")
SUBJECT = "synthetic-identity"


@dataclass
class SigningPeer:
    private: rsa.RSAPrivateKey = field(
        default_factory=lambda: rsa.generate_private_key(public_exponent=65537, key_size=2048),
        repr=False,
    )
    kid: str = "synthetic-signing-key"
    requests: int = 0
    status: int = 200

    def jwk(self) -> dict[str, object]:
        value: dict[str, object] = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.private.public_key()))
        return {**value, "kid": self.kid, "alg": "RS256", "use": "sig"}

    def claims(self) -> dict[str, object]:
        now = int(time.time())
        return {
            "iss": SETTINGS.issuer, "aud": SETTINGS.audience, "sub": SUBJECT,
            "iat": now, "exp": now + 300, "typ": "Bearer",
            "realm_access": {"roles": ["administrator", "author", "learner"]},
        }

    def token(self, claims: dict[str, object] | None = None, **headers: object) -> str:
        return jwt.encode(
            self.claims() if claims is None else claims, self.private,
            algorithm="RS256", headers={"kid": self.kid, **headers},
        )

    def serve(self, request: httpx.Request) -> httpx.Response:
        assert str(request.url) == SETTINGS.issuer + "/protocol/openid-connect/certs"
        assert "authorization" not in request.headers
        self.requests += 1
        return httpx.Response(self.status, json={"keys": [self.jwk()]})


def seed_account(
    database: IsolatedDatabase, *, roles: tuple[str, ...] = ("learner",),
    status: str = "active", active: bool = True, subject: str = SUBJECT,
) -> UUID:
    account_id = uuid4()
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute(
            "INSERT INTO quezo.accounts (id, status) VALUES (%s, %s)", (account_id, status),
        )
        connection.execute(
            "INSERT INTO quezo.identity_mappings (issuer, subject, account_id, active) "
            "VALUES (%s, %s, %s, %s)", (SETTINGS.issuer, subject, account_id, active),
        )
        for role in roles:
            connection.execute(
                "INSERT INTO quezo.account_roles (account_id, role) VALUES (%s, %s)",
                (account_id, role),
            )
    return account_id
