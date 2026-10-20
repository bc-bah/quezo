import os

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from db_helpers import (
    IsolatedDatabase,
    assert_test_cluster,
    drop_test_database,
    isolated_database,
    validate_test_admin_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "postgresql://quezo_test_admin:test@production.example:5432/quezo_test_control",
        "postgresql://quezo_test_admin:test@127.0.0.1:5432/quezo",
        "postgresql://postgres:test@127.0.0.1:5432/quezo_test_control",
        "postgresql://quezo_test_admin:test@127.0.0.1/quezo_test_control",
        "postgresql://quezo_test_admin:test@127.0.0.1:5432/quezo_test_control?hostaddr=192.0.2.1",
        "postgresql://quezo_test_admin:test@127.0.0.1:5432/quezo_test_control?service=production",
    ],
)
def test_test_database_guard_rejects_unsafe_targets_before_connecting(url: str) -> None:
    with pytest.raises(ValueError, match="isolated test"):
        validate_test_admin_url(url)


@pytest.mark.parametrize("name", ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE"])
def test_test_database_guard_rejects_ambient_connection_overrides(
    monkeypatch: pytest.MonkeyPatch, name: str,
) -> None:
    monkeypatch.setenv(name, "unexpected-connection-override")
    with pytest.raises(ValueError, match="isolated test"):
        validate_test_admin_url(
            "postgresql://quezo_test_admin:test@127.0.0.1:5432/quezo_test_control"
        )


def test_server_marker_is_required_even_with_a_safe_url() -> None:
    params = validate_test_admin_url(os.environ["QUEZO_TEST_ADMIN_URL"])
    with psycopg.connect(make_conninfo(**params)) as admin:
        with pytest.raises(RuntimeError, match="outside the isolated test cluster"):
            with admin.transaction():
                admin.execute("COMMENT ON DATABASE quezo_test_control IS 'not-a-test'")
                assert_test_cluster(admin)
        assert_test_cluster(admin)


def test_cleanup_refuses_unowned_names_and_markers(
    empty_database: IsolatedDatabase,
) -> None:
    params = validate_test_admin_url(os.environ["QUEZO_TEST_ADMIN_URL"])
    with psycopg.connect(make_conninfo(**params), autocommit=True) as admin:
        with pytest.raises(RuntimeError, match="non-test database"):
            drop_test_database(admin, "quezo_test_control", "anything")
        with pytest.raises(RuntimeError, match="unowned test database"):
            drop_test_database(admin, empty_database.name, "wrong-marker")
        assert admin.execute(
            "SELECT datname FROM pg_database WHERE datname = %s", (empty_database.name,)
        ).fetchone() == (empty_database.name,)


def test_test_databases_have_distinct_names_and_are_removed_after_use() -> None:
    with isolated_database() as first, isolated_database() as second:
        assert first.name != second.name
        with psycopg.connect(first.migration_url) as connection:
            connection.execute("CREATE TABLE public.f01_probe (value integer)")
        with psycopg.connect(second.migration_url) as connection:
            assert connection.execute(
                "SELECT to_regclass('public.f01_probe')"
            ).fetchone() == (None,)
    params = validate_test_admin_url(os.environ["QUEZO_TEST_ADMIN_URL"])
    with psycopg.connect(make_conninfo(**params)) as admin:
        assert admin.execute(
            "SELECT datname FROM pg_database WHERE datname IN (%s, %s)",
            (first.name, second.name),
        ).fetchall() == []
