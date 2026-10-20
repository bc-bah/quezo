import asyncio
from collections.abc import Iterator

import pytest

from db_helpers import IsolatedDatabase, isolated_database, run_migrations


@pytest.fixture
def anyio_backend() -> tuple[str, dict[str, object]]:
    return "asyncio", {"loop_factory": asyncio.SelectorEventLoop}


@pytest.fixture
def empty_database() -> Iterator[IsolatedDatabase]:
    with isolated_database() as database:
        yield database


@pytest.fixture
def database(empty_database: IsolatedDatabase) -> IsolatedDatabase:
    run_migrations(empty_database.migration_url)
    return empty_database
