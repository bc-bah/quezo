import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Self

from fastapi import Request
from psycopg import AsyncConnection, ProgrammingError
from psycopg.conninfo import conninfo_to_dict
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


def database_loop_factory() -> asyncio.AbstractEventLoop:
    # Psycopg async connections cannot run on Windows' default Proactor loop.
    return asyncio.SelectorEventLoop()


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)

    url: SecretStr = Field(repr=False)
    pool_min: int = Field(default=1, ge=1, le=20)
    pool_max: int = Field(default=5, ge=1, le=20)
    pool_timeout: float = Field(default=5, gt=0, le=60, allow_inf_nan=False)
    startup_timeout: float = Field(default=10, gt=0, le=60, allow_inf_nan=False)
    statement_timeout_ms: int = Field(default=30_000, ge=1, le=300_000)

    @model_validator(mode="after")
    def validate_connection(self) -> Self:
        url = self.url.get_secret_value()
        if not url.startswith(("postgresql://", "postgres://")):
            raise ValueError("QUEZO_DATABASE_URL must be an explicit PostgreSQL URL")
        try:
            params = conninfo_to_dict(url)
        except ProgrammingError:
            raise ValueError("Invalid QUEZO_DATABASE_URL") from None
        if (
            params.get("user") != "quezo_runtime"
            or not params.get("dbname")
            or not params.get("host")
            or "service" in params
        ):
            raise ValueError(
                "QUEZO_DATABASE_URL requires host, database and quezo_runtime identity"
            )
        if self.pool_min > self.pool_max:
            raise ValueError("Database pool_min must not exceed pool_max")
        return self

    @classmethod
    def from_env(cls) -> Self:
        url = os.environ.get("QUEZO_DATABASE_URL")
        if not url:
            raise ValueError("QUEZO_DATABASE_URL is required")
        values: dict[str, object] = {"url": url}
        for field in (
            "pool_min",
            "pool_max",
            "pool_timeout",
            "startup_timeout",
            "statement_timeout_ms",
        ):
            if (value := os.environ.get(f"QUEZO_DB_{field.upper()}")) is not None:
                values[field] = value
        return cls.model_validate(values)


class Database:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._startup_timeout = settings.startup_timeout
        self._pool: AsyncConnectionPool[AsyncConnection[tuple[object, ...]]] = (
            AsyncConnectionPool(
                settings.url.get_secret_value(),
                open=False,
                min_size=settings.pool_min,
                max_size=settings.pool_max,
                max_waiting=settings.pool_max * 2,
                timeout=settings.pool_timeout,
                reconnect_timeout=settings.startup_timeout,
                name="quezo-runtime",
                kwargs={
                    "autocommit": True,
                    "connect_timeout": 5,
                    "application_name": "quezo-api",
                    "options": (
                        "-c timezone=UTC -c search_path=quezo,pg_catalog "
                        f"-c statement_timeout={settings.statement_timeout_ms} "
                        "-c lock_timeout=5000 -c idle_in_transaction_session_timeout=30000"
                    ),
                },
                check=AsyncConnectionPool.check_connection,
            )
        )

    @property
    def closed(self) -> bool:
        return self._pool.closed

    async def __aenter__(self) -> Self:
        try:
            await self._pool.open(wait=True, timeout=self._startup_timeout)
        except BaseException:
            await self._pool.close(timeout=5)
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._pool.close(timeout=5)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncConnection[tuple[object, ...]]]:
        async with self._pool.connection() as connection:
            async with connection.transaction():
                yield connection


def get_database(request: Request) -> Database:
    database = getattr(request.app.state, "database", None)
    if not isinstance(database, Database) or database.closed:
        raise RuntimeError("Database lifespan is not running")
    return database
