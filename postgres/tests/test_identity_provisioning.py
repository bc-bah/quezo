import asyncio
from dataclasses import dataclass

import psycopg
import pytest
from pydantic import SecretStr

from db_helpers import IsolatedDatabase
from identity_helpers import SETTINGS, seed_account
from quezo_api.database import Database, DatabaseSettings
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.access import resolve_actor
from quezo_api.modules.identity.provisioning import ACCOUNTS, SyntheticAccount, provision_account
from quezo_api.modules.identity.tokens import VerifiedIdentity

pytestmark = pytest.mark.anyio


@dataclass
class ProvisioningPeer:
    failure: str = ""
    calls: int = 0

    async def establish(self, account: SyntheticAccount) -> VerifiedIdentity:
        self.calls += 1
        if self.failure == "outage":
            raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
        if self.failure == "cancel":
            raise asyncio.CancelledError()
        return VerifiedIdentity(
            "wrong-issuer" if self.failure == "mismatch" else SETTINGS.issuer,
            str(account.application_id(SETTINGS.issuer)),
        )


@pytest.mark.parametrize("failure", ["outage", "mismatch", "cancel"])
async def test_identity_failure_never_commits_a_grant(
    database: IsolatedDatabase, failure: str,
) -> None:
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        with pytest.raises((ApiError, asyncio.CancelledError)):
            await provision_account(db, ProvisioningPeer(failure), SETTINGS.issuer, "administrator")
        async with db.transaction() as connection:
            for table in ("accounts", "identity_mappings", "account_roles"):
                cursor = await connection.execute(
                    psycopg.sql.SQL("SELECT count(*) FROM quezo.{}").format(psycopg.sql.Identifier(table))
                )
                assert await cursor.fetchone() == (0,)
        # A controlled retry succeeds only after identity operations succeed.
        account_id = await provision_account(db, ProvisioningPeer(), SETTINGS.issuer, "administrator")
        async with db.transaction() as connection:
            actor = await resolve_actor(
                connection, VerifiedIdentity(SETTINGS.issuer, str(ACCOUNTS["administrator"].application_id(SETTINGS.issuer))),
            )
        assert actor.user_id == account_id
        assert actor.roles == ["administrator"]


async def test_provisioning_retries_never_restore_revoked_access(database: IsolatedDatabase) -> None:
    peer = ProvisioningPeer()
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        user_id = await provision_account(db, peer, SETTINGS.issuer, "author")
        async with db.transaction() as connection:
            await connection.execute("UPDATE quezo.accounts SET status = 'disabled' WHERE id = %s", (user_id,))
            await connection.execute("DELETE FROM quezo.account_roles WHERE account_id = %s", (user_id,))
        with pytest.raises(ApiError) as error:
            await provision_account(db, peer, SETTINGS.issuer, "author")
        assert error.value.code == ErrorCode.INVALID_STATE
        assert peer.calls == 1
        async with db.transaction() as connection:
            cursor = await connection.execute("SELECT status FROM quezo.accounts WHERE id = %s", (user_id,))
            assert await cursor.fetchone() == ("disabled",)
            cursor = await connection.execute("SELECT count(*) FROM quezo.account_roles")
            assert await cursor.fetchone() == (0,)
        with pytest.raises(ApiError):
            await provision_account(db, peer, SETTINGS.issuer, "arbitrary-login")
        assert peer.calls == 1


async def test_concurrent_first_admin_provisioning_creates_exactly_one(database: IsolatedDatabase) -> None:
    peer = ProvisioningPeer()
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        results = await asyncio.gather(
            *(provision_account(db, peer, SETTINGS.issuer, "administrator") for _ in range(2)),
            return_exceptions=True,
        )
        assert sum(isinstance(result, ApiError) for result in results) == 1
        assert peer.calls == 1
        async with db.transaction() as connection:
            cursor = await connection.execute("SELECT count(*) FROM quezo.accounts")
            assert await cursor.fetchone() == (1,)


async def test_post_identity_database_failure_rolls_back_grants(database: IsolatedDatabase) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("ALTER TABLE quezo.account_roles ADD CONSTRAINT synthetic_failure CHECK (false)")
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        peer = ProvisioningPeer()
        with pytest.raises(psycopg.errors.CheckViolation):
            await provision_account(db, peer, SETTINGS.issuer, "administrator")
        assert peer.calls == 1
        async with db.transaction() as connection:
            cursor = await connection.execute("SELECT count(*) FROM quezo.accounts")
            assert await cursor.fetchone() == (0,)
            cursor = await connection.execute("SELECT count(*) FROM quezo.identity_mappings")
            assert await cursor.fetchone() == (0,)


async def test_first_admin_bootstrap_refuses_existing_active_admin(database: IsolatedDatabase) -> None:
    seed_account(database, roles=("administrator",))
    peer = ProvisioningPeer()
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        with pytest.raises(ApiError) as error:
            await provision_account(db, peer, SETTINGS.issuer, "administrator")
        assert error.value.code == ErrorCode.INVALID_STATE
        assert peer.calls == 0
