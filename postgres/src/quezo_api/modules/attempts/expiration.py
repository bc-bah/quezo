import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from uuid import UUID

from psycopg import OperationalError
from psycopg_pool import PoolTimeout, TooManyRequests

from quezo_api.database import Database
from quezo_api.modules.attempts.finalization import database_time, finalize_locked, lock_attempt

BATCH_SIZE = 20
INTERVAL_SECONDS = 5
logger = logging.getLogger("quezo_api.expiration")


async def expire_batch(database: Database) -> int:
    async with database.transaction() as connection:
        cursor = await connection.execute(
            "SELECT id FROM quezo.attempts WHERE state = 'in_progress' AND deadline <= clock_timestamp() "
            "ORDER BY deadline, id LIMIT %s FOR UPDATE SKIP LOCKED", (BATCH_SIZE,),
        )
        candidates = await cursor.fetchall()
        for (attempt_id,) in candidates:
            assert isinstance(attempt_id, UUID)
            attempt = await lock_attempt(connection, attempt_id, None)
            await finalize_locked(connection, attempt, await database_time(connection))
    return len(candidates)


async def run_worker(database: Database) -> None:
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        try:
            await expire_batch(database)
        except (OperationalError, PoolTimeout, TooManyRequests):
            # A later scheduled sweep is not a retry of a failed transaction.
            logger.error('{"operation":"expiration","code":"DEPENDENCY_UNAVAILABLE"}')


@asynccontextmanager
async def expiration_lifespan(database: Database) -> AsyncIterator[None]:
    # Startup fails explicitly if the schema/dependency is unavailable.
    await expire_batch(database)
    async with asyncio.TaskGroup() as group:
        worker = group.create_task(run_worker(database), name="quezo-expiration")
        try:
            yield
        finally:
            worker.cancel()
