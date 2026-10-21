import asyncio
from collections.abc import Iterator

import pytest

from db_helpers import IsolatedDatabase, isolated_database, run_migrations


@pytest.fixture(autouse=True)
def identity_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    # Configuration only, not a verifier substitute; liveness never fetches JWKS.
    monkeypatch.setenv("QUEZO_OIDC_ISSUER", "http://localhost:8080/realms/quezo-local")
    monkeypatch.setenv("QUEZO_API_AUDIENCE", "quezo-api")


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
