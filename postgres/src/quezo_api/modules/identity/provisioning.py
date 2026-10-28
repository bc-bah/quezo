from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid5

from quezo_api.database import Database
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.schemas import Role


@dataclass(frozen=True)
class SyntheticAccount:
    username: str
    roles: tuple[Role, ...]

    def application_id(self, issuer: str) -> UUID:
        return uuid5(UUID("c8293778-d759-466c-b84b-a1d027ee45fb"), f"{issuer}\n{self.username}")


ACCOUNTS = {
    "administrator": SyntheticAccount("quezo-test-administrator", (Role.ADMINISTRATOR,)),
    "author": SyntheticAccount("quezo-test-author", (Role.AUTHOR,)),
    "learner": SyntheticAccount("quezo-test-learner", (Role.LEARNER,)),
    "combined": SyntheticAccount("quezo-test-combined", (Role.AUTHOR, Role.LEARNER)),
    "empty": SyntheticAccount("quezo-test-empty", ()),
}


class LocalIdentityProvider(Protocol):
    async def establish(self, account: SyntheticAccount) -> VerifiedIdentity: ...


async def provision_account(
    database: Database, provider: LocalIdentityProvider, issuer: str, name: str,
) -> UUID:
    """Explicit allowlisted local bootstrap, never a login or runtime route."""
    if name not in ACCOUNTS:
        raise ApiError(ErrorCode.VALIDATION_FAILED)
    account = ACCOUNTS[name]
    account_id = account.application_id(issuer)
    async with database.transaction() as connection:
        # Serialize local retries/first-admin creation, including the external operation.
        await connection.execute("SELECT pg_advisory_xact_lock(716269004)")
        cursor = await connection.execute(
            "SELECT 1 FROM quezo.accounts WHERE id = %s", (account_id,),
        )
        if await cursor.fetchone() is not None:
            raise ApiError(ErrorCode.INVALID_STATE)
        if Role.ADMINISTRATOR in account.roles:
            cursor = await connection.execute(
                "SELECT 1 FROM quezo.accounts a JOIN quezo.account_roles r "
                "ON r.account_id = a.id WHERE a.status = 'active' "
                "AND r.role = 'administrator'"
            )
            if await cursor.fetchone() is not None:
                raise ApiError(ErrorCode.INVALID_STATE)
        identity = await provider.establish(account)
        if (
            identity.issuer != issuer or not identity.subject.strip()
            or len(identity.subject) > 255
        ):
            raise ApiError(ErrorCode.UNAUTHENTICATED)
        await connection.execute(
            """
            INSERT INTO quezo.accounts
                (id, status, username, email, identity_desired_enabled)
            VALUES (%s, 'active', %s, %s, true)
            """,
            (account_id, account.username, f"{account.username}@example.invalid"),
        )
        await connection.execute(
            "INSERT INTO quezo.identity_mappings (issuer, subject, account_id, active) "
            "VALUES (%s, %s, %s, true)", (issuer, identity.subject, account_id),
        )
        for role in account.roles:
            await connection.execute(
                "INSERT INTO quezo.account_roles (account_id, role) VALUES (%s, %s)",
                (account_id, role.value),
            )
    return account_id
