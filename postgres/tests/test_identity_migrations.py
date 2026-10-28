from uuid import uuid4

import psycopg
import pytest

from db_helpers import IsolatedDatabase, run_migrations
from identity_helpers import SETTINGS, SUBJECT, seed_account


def test_actual_f03_head_upgrade_preserves_sessions(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0003_web_sessions")
    with psycopg.connect(empty_database.web_url) as connection:
        connection.execute(
            "INSERT INTO quezo_session.sessions "
            "(id_hash, login_hash, access_token, token_expires_at, expires_at, idle_expires_at) "
            "VALUES (%s, %s, %s, now() + interval '1 hour', now() + interval '30 minutes', "
            "now() + interval '20 minutes')",
            ("a" * 64, "b" * 64, "synthetic-session-secret"),
        )
    run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.web_url) as connection:
        assert connection.execute("SELECT access_token FROM quezo_session.sessions").fetchone() == (
            "synthetic-session-secret",
        )
    seed_account(empty_database)
    run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0011_account_administration",)
        assert connection.execute("SELECT count(*) FROM quezo.accounts").fetchone() == (1,)


@pytest.mark.parametrize(
    "table", ["accounts", "account_roles", "identity_mappings", "account_admin_events"],
)
def test_web_role_cannot_read_or_write_identity(database: IsolatedDatabase, table: str) -> None:
    with psycopg.connect(database.web_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(psycopg.sql.SQL("SELECT * FROM quezo.{}").format(psycopg.sql.Identifier(table)))
    with psycopg.connect(database.web_url) as connection:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(psycopg.sql.SQL("DELETE FROM quezo.{}").format(psycopg.sql.Identifier(table)))


def test_identity_relational_constraints_and_default_ineligibility(database: IsolatedDatabase) -> None:
    account_id = seed_account(database)
    statements: list[tuple[str, tuple[object, ...]]] = [
        ("INSERT INTO quezo.identity_mappings VALUES (%s, %s, %s, true)", (SETTINGS.issuer, SUBJECT, uuid4())),
        ("INSERT INTO quezo.identity_mappings VALUES (%s, 'other', %s, true)", (SETTINGS.issuer, account_id)),
        ("INSERT INTO quezo.account_roles VALUES (%s, 'learner')", (account_id,)),
        ("INSERT INTO quezo.account_roles VALUES (%s, 'superuser')", (account_id,)),
        ("INSERT INTO quezo.account_roles VALUES (%s, 'author')", (uuid4(),)),
        ("UPDATE quezo.accounts SET status = 'unknown' WHERE id = %s", (account_id,)),
    ]
    for statement, params in statements:
        with psycopg.connect(database.runtime_url) as connection:
            with pytest.raises(psycopg.IntegrityError):
                connection.execute(statement, params)
    with psycopg.connect(database.runtime_url) as connection:
        other_id = uuid4()
        connection.execute("INSERT INTO quezo.accounts (id) VALUES (%s)", (other_id,))
        connection.execute(
            "INSERT INTO quezo.identity_mappings (issuer, subject, account_id) VALUES (%s, 'other', %s)",
            (SETTINGS.issuer, other_id),
        )
        assert connection.execute("SELECT status FROM quezo.accounts WHERE id = %s", (other_id,)).fetchone() == ("disabled",)
        assert connection.execute("SELECT active FROM quezo.identity_mappings WHERE account_id = %s", (other_id,)).fetchone() == (False,)
        assert connection.execute(
            "SELECT provisioning_state, identity_sync_state, identity_desired_enabled "
            "FROM quezo.accounts WHERE id = %s", (other_id,),
        ).fetchone() == ("complete", "in_sync", False)


def test_failed_identity_upgrade_preserves_actual_prior_revision(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0003_web_sessions")
    with psycopg.connect(empty_database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo.identity_mappings (probe integer)")
    with pytest.raises(RuntimeError, match="DuplicateTable"):
        run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0003_web_sessions",)
        assert connection.execute("SELECT to_regclass('quezo.accounts')").fetchone() == (None,)
        connection.execute("DROP TABLE quezo.identity_mappings")
    run_migrations(empty_database.migration_url)
