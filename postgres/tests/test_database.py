import asyncio
import socket

import psycopg
import pytest
from pydantic import SecretStr
from psycopg_pool import PoolClosed, PoolTimeout

from db_helpers import IsolatedDatabase
from quezo_api.database import Database, DatabaseSettings


@pytest.mark.anyio
async def test_transactions_commit_success_and_roll_back_failure(
    database: IsolatedDatabase,
) -> None:
    async with await psycopg.AsyncConnection.connect(database.migration_url) as owner:
        await owner.execute(
            "CREATE TABLE quezo.f01_probe (value text NOT NULL UNIQUE)"
        )
    settings = DatabaseSettings(url=SecretStr(database.runtime_url))
    async with Database(settings) as db:
        async with db.transaction() as connection:
            await connection.execute(
                "INSERT INTO quezo.f01_probe VALUES (%s)", ("committed",)
            )
        with pytest.raises(psycopg.errors.UniqueViolation):
            async with db.transaction() as connection:
                await connection.execute(
                    "INSERT INTO quezo.f01_probe VALUES (%s)", ("rolled-back",)
                )
                await connection.execute(
                    "INSERT INTO quezo.f01_probe VALUES (%s)", ("committed",)
                )
        async with db.transaction() as connection:
            cursor = await connection.execute("SELECT value FROM quezo.f01_probe")
            assert await cursor.fetchall() == [("committed",)]
    assert db.closed
    async with Database(settings) as reopened:
        async with reopened.transaction() as connection:
            cursor = await connection.execute("SELECT value FROM quezo.f01_probe")
            assert await cursor.fetchall() == [("committed",)]


@pytest.mark.anyio
async def test_query_wait_does_not_block_the_event_loop(
    database: IsolatedDatabase,
) -> None:
    async with Database(DatabaseSettings(url=SecretStr(database.runtime_url))) as db:
        async with db.transaction() as connection:
            query = asyncio.create_task(connection.execute("SELECT pg_sleep(0.3)"))
            await asyncio.sleep(0.05)
            assert not query.done()
            await query


@pytest.mark.anyio
async def test_pool_capacity_waits_and_shutdown_are_bounded(
    database: IsolatedDatabase,
) -> None:
    settings = DatabaseSettings(
        url=SecretStr(database.runtime_url), pool_max=1, pool_timeout=0.1,
    )
    async with Database(settings) as db:
        async with db.transaction() as connection:
            with pytest.raises(PoolTimeout):
                async with db.transaction():
                    pytest.fail("A second lease exceeded the pool capacity")
            assert not connection.closed
            cursor = await connection.execute(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND application_name = 'quezo-api'"
            )
            assert await cursor.fetchone() == (1,)
    assert connection.closed
    with pytest.raises(PoolClosed):
        async with db.transaction():
            pytest.fail("Closed pools must reject work")
    async with await psycopg.AsyncConnection.connect(database.migration_url) as owner:
        cursor = await owner.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE datname = current_database() AND application_name = 'quezo-api'"
        )
        assert await cursor.fetchone() == (0,)


@pytest.mark.anyio
async def test_database_outage_fails_startup_and_closes_pool() -> None:
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        port = unavailable.getsockname()[1]
        db = Database(DatabaseSettings(
            url=SecretStr(f"postgresql://quezo_runtime:unused@127.0.0.1:{port}/unavailable"),
            startup_timeout=0.2,
        ))
        with pytest.raises(PoolTimeout):
            async with asyncio.timeout(8):
                async with db:
                    pytest.fail("An unavailable database must not become memory storage")
        assert db.closed


@pytest.mark.anyio
async def test_cancellation_rolls_back_and_returns_connection(
    database: IsolatedDatabase,
) -> None:
    async with await psycopg.AsyncConnection.connect(database.migration_url) as owner:
        await owner.execute("CREATE TABLE quezo.f01_probe (value text NOT NULL)")
    async with Database(DatabaseSettings(
        url=SecretStr(database.runtime_url), pool_max=1,
    )) as db:
        inserted = asyncio.Event()

        async def interrupted_write() -> None:
            async with db.transaction() as connection:
                await connection.execute("INSERT INTO quezo.f01_probe VALUES ('cancelled')")
                inserted.set()
                await asyncio.Event().wait()

        task = asyncio.create_task(interrupted_write())
        await asyncio.wait_for(inserted.wait(), timeout=3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        async with db.transaction() as connection:
            cursor = await connection.execute("SELECT value FROM quezo.f01_probe")
            assert await cursor.fetchall() == []


@pytest.mark.anyio
async def test_statement_timeout_rolls_back_and_connection_remains_usable(
    database: IsolatedDatabase,
) -> None:
    async with Database(DatabaseSettings(
        url=SecretStr(database.runtime_url), statement_timeout_ms=50,
    )) as db:
        with pytest.raises(psycopg.errors.QueryCanceled):
            async with db.transaction() as connection:
                await connection.execute("SELECT pg_sleep(1)")
        async with db.transaction() as connection:
            cursor = await connection.execute("SELECT 42")
            assert await cursor.fetchone() == (42,)
