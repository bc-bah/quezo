from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from db_helpers import IsolatedDatabase, run_migrations
from identity_helpers import seed_account
from question_helpers import content


def insert_question(
    connection: psycopg.Connection[tuple[Any, ...]], owner: UUID, bank: UUID,
    body: dict[str, Any],
) -> tuple[UUID, UUID]:
    question, version = uuid4(), uuid4()
    connection.execute(
        "INSERT INTO quezo.questions (id, bank_id, owner_id, revision) VALUES (%s, %s, %s, 1)",
        (question, bank, owner),
    )
    connection.execute(
        "INSERT INTO quezo.question_versions "
        "(id, question_id, revision, question_type, prompt, options, correct_option_id, default_points, feedback) "
        "VALUES (%s, %s, 1, %s, %s, %s, %s, %s, %s)",
        (version, question, body["questionType"], body["prompt"], Jsonb(body["options"]),
         body["correctOptionId"], body["defaultPoints"], body["feedback"]),
    )
    return question, version


def seed_bank(database: IsolatedDatabase) -> tuple[UUID, UUID]:
    owner, bank = seed_account(database, roles=("author",)), uuid4()
    with psycopg.connect(database.runtime_url) as connection:
        connection.execute(
            "INSERT INTO quezo.question_banks (id, owner_id, name) VALUES (%s, %s, 'Synthetic bank')",
            (bank, owner),
        )
    return owner, bank


def test_actual_identity_head_upgrade_preserves_accounts_and_sessions(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0004_identity")
    owner = seed_account(empty_database, roles=("author",))
    with psycopg.connect(empty_database.web_url) as connection:
        connection.execute(
            "INSERT INTO quezo_session.sessions "
            "(id_hash, login_hash, access_token, token_expires_at, expires_at, idle_expires_at) "
            "VALUES (%s, %s, 'synthetic-session', now() + interval '1 hour', "
            "now() + interval '30 minutes', now() + interval '20 minutes')",
            ("a" * 64, "b" * 64),
        )
    run_migrations(empty_database.migration_url)
    run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0012_delivery_controls",)
        assert connection.execute("SELECT id FROM quezo.accounts").fetchone() == (owner,)
        assert connection.execute("SELECT role FROM quezo.account_roles").fetchone() == ("author",)
    with psycopg.connect(empty_database.web_url) as connection:
        assert connection.execute("SELECT access_token FROM quezo_session.sessions").fetchone() == ("synthetic-session",)


def test_failed_upgrade_rolls_back_to_actual_prior_head(empty_database: IsolatedDatabase) -> None:
    run_migrations(empty_database.migration_url, "0004_identity")
    with psycopg.connect(empty_database.migration_url) as connection:
        connection.execute("CREATE TABLE quezo.questions (probe integer)")
    with pytest.raises(RuntimeError, match="DuplicateTable"):
        run_migrations(empty_database.migration_url)
    with psycopg.connect(empty_database.migration_url) as connection:
        assert connection.execute("SELECT version_num FROM public.alembic_version").fetchone() == ("0004_identity",)
        assert connection.execute("SELECT to_regclass('quezo.question_banks')").fetchone() == (None,)
        assert connection.execute("SELECT to_regprocedure('quezo.question_text_valid(text,integer,boolean)')").fetchone() == (None,)
        connection.execute("DROP TABLE quezo.questions")
    run_migrations(empty_database.migration_url)


@pytest.mark.parametrize("kind", ["mcq", "true_false"])
def test_versions_are_immutable_and_relational(database: IsolatedDatabase, kind: str) -> None:
    owner, bank = seed_bank(database)
    with psycopg.connect(database.runtime_url) as connection:
        question, version = insert_question(connection, owner, bank, content(kind))
    for url, error in [
        (database.runtime_url, psycopg.errors.InsufficientPrivilege),
        (database.migration_url, psycopg.errors.CheckViolation),
    ]:
        for statement in [
            "UPDATE quezo.question_versions SET feedback = 'changed' WHERE id = %s",
            "DELETE FROM quezo.question_versions WHERE id = %s",
        ]:
            with psycopg.connect(url) as connection, pytest.raises(error):
                connection.execute(statement, (version,))
    for statement, values in [
        ("DELETE FROM quezo.questions WHERE id = %s", (question,)),
        ("UPDATE quezo.questions SET revision = 2 WHERE id = %s", (question,)),
        ("DELETE FROM quezo.question_banks WHERE id = %s", (bank,)),
    ]:
        with pytest.raises(psycopg.IntegrityError), psycopg.connect(database.runtime_url) as connection:
            connection.execute(statement, values)
    other = seed_account(database, roles=("author",), subject="other")
    with pytest.raises(psycopg.IntegrityError), psycopg.connect(database.runtime_url) as connection:
        insert_question(connection, other, bank, content())


@pytest.mark.parametrize("case", [
    "negative", "too-many-points", "blank-prompt", "long-prompt", "long-feedback", "control",
    "one-option", "too-many-options", "duplicate", "bad-id", "bad-key",
    "empty-option", "long-option", "extra-option-field", "null-option", "not-array",
    "wrong-type", "false-labels", "extra-false", "null-text",
])
def test_database_independently_rejects_invalid_content(database: IsolatedDatabase, case: str) -> None:
    owner, bank = seed_bank(database)
    body = content()
    if case == "negative":
        body["defaultPoints"] = -1
    elif case == "too-many-points":
        body["defaultPoints"] = 10001
    elif case == "blank-prompt":
        body["prompt"] = " \t\n"
    elif case == "long-prompt":
        body["prompt"] = "x" * 4001
    elif case == "long-feedback":
        body["feedback"] = "x" * 4001
    elif case == "control":
        body["prompt"] = "bad\x01"
    elif case == "one-option":
        body["options"].pop()
    elif case == "too-many-options":
        body["options"].extend({"id": str(uuid4()), "text": "x"} for _ in range(9))
    elif case == "duplicate":
        body["options"][1]["id"] = body["options"][0]["id"]
    elif case == "bad-id":
        body["options"][0]["id"] = "bad"
    elif case == "bad-key":
        body["correctOptionId"] = str(uuid4())
    elif case == "empty-option":
        body["options"][0]["text"] = " \t"
    elif case == "long-option":
        body["options"][0]["text"] = "x" * 1001
    elif case == "extra-option-field":
        body["options"][0]["key"] = True
    elif case == "null-option":
        body["options"][0] = None
    elif case == "not-array":
        body["options"] = {}
    elif case == "wrong-type":
        body["questionType"] = "essay"
    elif case == "null-text":
        body["options"][0]["text"] = None
    else:
        body["questionType"] = "true_false"
        if case == "extra-false":
            body["options"] = [
                {"id": str(uuid4()), "text": value} for value in ["True", "False", "Extra"]
            ]
            body["correctOptionId"] = body["options"][0]["id"]
    with pytest.raises(psycopg.IntegrityError), psycopg.connect(database.runtime_url) as connection:
        insert_question(connection, owner, bank, body)
    with psycopg.connect(database.runtime_url) as connection:
        assert connection.execute("SELECT count(*) FROM quezo.questions").fetchone() == (0,)


@pytest.mark.parametrize("table", ["question_banks", "questions", "question_versions"])
def test_web_cannot_access_questions(database: IsolatedDatabase, table: str) -> None:
    for command in ["SELECT * FROM", "DELETE FROM"]:
        with psycopg.connect(database.web_url) as connection, pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute(psycopg.sql.SQL(command + " quezo.{}").format(psycopg.sql.Identifier(table)))
