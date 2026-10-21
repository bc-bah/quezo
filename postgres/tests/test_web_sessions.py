import os
from pathlib import Path
import subprocess

import psycopg
import pytest

from db_helpers import IsolatedDatabase, run_migrations

ROOT = Path(__file__).resolve().parents[2]


def test_session_upgrade_from_integrated_f01_head(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0002_runtime_grants")
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute(
            "SELECT to_regnamespace('quezo_session')"
        ).fetchone() == (None,)
    run_migrations(empty_database.migration_url)
    run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.web_url) as connection:
        assert connection.execute(
            "SELECT count(*) FROM quezo_session.sessions"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT count(*) FROM quezo_session.login_transactions"
        ).fetchone() == (0,)


@pytest.mark.parametrize("statement", [
    "SELECT * FROM quezo_session.sessions",
    "SELECT * FROM quezo_session.login_transactions",
    "SET ROLE quezo_web",
])
def test_backend_cannot_read_session_secrets(database: IsolatedDatabase, statement: str) -> None:
    with psycopg.connect(database.runtime_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(statement)


@pytest.mark.parametrize("statement", [
    "SELECT * FROM quezo.assessment_probe",
    "INSERT INTO quezo.assessment_probe VALUES (1)",
    "CREATE TABLE quezo_session.forbidden (id integer)",
    "CREATE TEMP TABLE forbidden (id integer)",
    "SELECT * FROM public.alembic_version",
    "SET ROLE quezo_migrator",
    "SET ROLE quezo_runtime",
    "CREATE ROLE forbidden",
    "CREATE SCHEMA forbidden",
    "TRUNCATE quezo_session.sessions",
])
def test_web_cannot_access_assessments_or_administer(database: IsolatedDatabase, statement: str) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo.assessment_probe (id integer)")
    with psycopg.connect(database.web_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(statement)


def test_no_backend_default_grants_in_session_schema(database: IsolatedDatabase) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo_session.future_probe (secret text)")
        for role in ("quezo_runtime", "quezo_web"):
            assert connection.execute(
                "SELECT has_table_privilege(%s, 'quezo_session.future_probe', 'SELECT')",
                (role,),
            ).fetchone() == (False,)


def test_web_sessions_against_real_postgres(database: IsolatedDatabase) -> None:
    result = subprocess.run(
        ["node", "--conditions=react-server", "--import", "tsx", "--test",
         "frontend/quezo/tests/storage.test.ts"],
        cwd=ROOT,
        env={**os.environ, "QUEZO_WEB_TEST_URL": database.web_url,
             "QUEZO_WEB_TEST_MIGRATION_URL": database.migration_url},
        timeout=180, check=False,
    )
    assert result.returncode == 0, "Focused Node session checks failed"
