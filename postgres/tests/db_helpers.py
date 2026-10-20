import os
import re
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import psycopg
from psycopg import ProgrammingError
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

BACKEND = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class IsolatedDatabase:
    name: str
    migration_url: str = field(repr=False)
    runtime_url: str = field(repr=False)


def validate_test_admin_url(url: str) -> dict[str, str]:
    message = "An explicit local isolated test admin URL is required"
    if any(os.environ.get(key) for key in ("PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE")):
        raise ValueError(
            "Unset PGHOSTADDR, PGSERVICE and PGSERVICEFILE for isolated test connections"
        )
    if not url.startswith(("postgresql://", "postgres://")):
        raise ValueError(message)
    try:
        parsed = conninfo_to_dict(url)
    except ProgrammingError:
        raise ValueError(message) from None
    params: dict[str, str] = {}
    for key, value in parsed.items():
        if not isinstance(value, str):
            raise ValueError(message)
        params[key] = value
    if (
        set(params) != {"host", "port", "dbname", "user", "password"}
        or params["host"] not in {"127.0.0.1", "::1", "localhost"}
        or params["dbname"] != "quezo_test_control"
        or params["user"] != "quezo_test_admin"
        or not params["password"]
        or not params["port"].isdigit()
        or not 1 <= int(params["port"]) <= 65535
    ):
        raise ValueError(message)
    return params


def assert_test_cluster(connection: psycopg.Connection[tuple[object, ...]]) -> None:
    row = connection.execute(
        "SELECT current_database(), current_user, "
        "shobj_description(oid, 'pg_database') "
        "FROM pg_database WHERE datname = current_database()"
    ).fetchone()
    if row != (
        "quezo_test_control",
        "quezo_test_admin",
        "quezo-f01-isolated-test-cluster",
    ):
        raise RuntimeError("Refusing database changes outside the isolated test cluster")


def drop_test_database(
    connection: psycopg.Connection[tuple[object, ...]], name: str, marker: str
) -> None:
    assert_test_cluster(connection)
    if re.fullmatch(r"quezo_test_[0-9a-f]{32}", name) is None:
        raise RuntimeError("Refusing to drop a non-test database")
    row = connection.execute(
        "SELECT pg_get_userbyid(datdba), shobj_description(oid, 'pg_database') "
        "FROM pg_database WHERE datname = %s", (name,)
    ).fetchone()
    if row != ("quezo_migrator", marker) or marker != f"f01-owned:{name}":
        raise RuntimeError("Refusing to drop an unowned test database")
    # Do not FORCE: leaked connections must fail cleanup, not be hidden.
    connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@contextmanager
def isolated_database() -> Iterator[IsolatedDatabase]:
    params = validate_test_admin_url(os.environ.get("QUEZO_TEST_ADMIN_URL", ""))
    migration_password = os.environ["QUEZO_TEST_MIGRATION_PASSWORD"]
    runtime_password = os.environ["QUEZO_TEST_RUNTIME_PASSWORD"]
    name = f"quezo_test_{uuid4().hex}"
    marker = f"f01-owned:{name}"
    with psycopg.connect(
        make_conninfo(**params), autocommit=True, connect_timeout=5
    ) as admin:
        assert_test_cluster(admin)
        admin.execute(
            sql.SQL("CREATE DATABASE {} OWNER quezo_migrator").format(
                sql.Identifier(name)
            )
        )
        admin.execute(
            sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(name), sql.Literal(marker)
            )
        )
        try:
            admin.execute(
                sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(name)
                )
            )
            # URLs are kept out of command arguments and dataclass representations.
            host = params["host"]
            if ":" in host:
                host = f"[{host}]"
            authority = f"{host}:{params['port']}/{name}"
            yield IsolatedDatabase(
                name,
                f"postgresql://quezo_migrator:{quote(migration_password, safe='')}@{authority}",
                f"postgresql://quezo_runtime:{quote(runtime_password, safe='')}@{authority}",
            )
        finally:
            drop_test_database(admin, name, marker)


def run_migrations(url: str, revision: str = "head") -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(BACKEND / "alembic.ini"),
         "upgrade", revision],
        env={**os.environ, "QUEZO_MIGRATION_URL": url},
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"Migration failed:\n{result.stdout}\n{result.stderr}")
