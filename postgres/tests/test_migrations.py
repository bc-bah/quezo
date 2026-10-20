import psycopg
import pytest

from db_helpers import IsolatedDatabase, run_migrations


def test_clean_database_migrates_without_domain_tables(
    empty_database: IsolatedDatabase,
) -> None:
    run_migrations(empty_database.migration_url, "head")
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute(
            "SELECT version_num FROM public.alembic_version"
        ).fetchone() == ("0002_runtime_grants",)
        assert connection.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'quezo'"
        ).fetchall() == []
        assert connection.execute(
            "SELECT has_schema_privilege('quezo_runtime', 'quezo', 'USAGE')"
        ).fetchone() == (True,)


def test_previous_schema_revision_upgrades_to_runtime_privileges(
    empty_database: IsolatedDatabase,
) -> None:
    run_migrations(empty_database.migration_url, "0001_application_schema")
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute(
            "SELECT version_num FROM public.alembic_version"
        ).fetchone() == ("0001_application_schema",)
        assert connection.execute(
            "SELECT has_schema_privilege('quezo_runtime', 'quezo', 'USAGE')"
        ).fetchone() == (False,)
    run_migrations(empty_database.migration_url)
    run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.runtime_url) as connection:
        assert connection.execute(
            "SELECT has_schema_privilege(current_user, 'quezo', 'USAGE')"
        ).fetchone() == (True,)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute(
            "SELECT version_num FROM public.alembic_version"
        ).fetchone() == ("0002_runtime_grants",)


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE quezo.forbidden (id integer)",
        "CREATE TABLE public.forbidden (id integer)",
        "CREATE SCHEMA forbidden",
        "CREATE TEMP TABLE forbidden (id integer)",
        "SELECT * FROM public.alembic_version",
        "SET ROLE quezo_migrator",
        "CREATE ROLE forbidden",
    ],
)
def test_runtime_cannot_administer_schema_or_migrations(
    database: IsolatedDatabase, statement: str
) -> None:
    with psycopg.connect(database.runtime_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(statement)


def test_future_tables_inherit_only_runtime_data_privileges(
    database: IsolatedDatabase,
) -> None:
    with psycopg.connect(database.migration_url) as connection:
        connection.execute(
            "CREATE TABLE quezo.f01_probe (id integer GENERATED ALWAYS AS IDENTITY, "
            "value text NOT NULL)"
        )
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute("INSERT INTO quezo.f01_probe (value) VALUES (%s)", ("first",))
        connection.execute("UPDATE quezo.f01_probe SET value = %s", ("updated",))
        assert connection.execute("SELECT value FROM quezo.f01_probe").fetchall() == [
            ("updated",)
        ]
        connection.execute("DELETE FROM quezo.f01_probe")
    with psycopg.connect(database.runtime_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("TRUNCATE quezo.f01_probe")


def test_competing_migration_fails_without_partial_revision(
    empty_database: IsolatedDatabase,
) -> None:
    with psycopg.connect(empty_database.migration_url) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(716269001)")
        with pytest.raises(RuntimeError, match="Another Quezo migration is running"):
            run_migrations(empty_database.migration_url)
        assert connection.execute(
            "SELECT to_regclass('public.alembic_version')"
        ).fetchone() == (None,)
    run_migrations(empty_database.migration_url)


def test_runtime_identity_cannot_run_migration_runner(database: IsolatedDatabase) -> None:
    with pytest.raises(RuntimeError, match="quezo_migrator identity"):
        run_migrations(database.runtime_url)


def test_failed_migration_rolls_back_ddl_and_version_record(
    empty_database: IsolatedDatabase,
) -> None:
    with psycopg.connect(empty_database.migration_url) as connection:
        connection.execute("CREATE SCHEMA quezo")
        connection.execute("GRANT CREATE ON SCHEMA public TO PUBLIC")
    with pytest.raises(RuntimeError, match="DuplicateSchema"):
        run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute(
            "SELECT to_regclass('public.alembic_version')"
        ).fetchone() == (None,)
        assert connection.execute(
            "SELECT has_schema_privilege('quezo_runtime', 'public', 'CREATE')"
        ).fetchone() == (True,)
        connection.execute("DROP SCHEMA quezo")
    run_migrations(empty_database.migration_url)
