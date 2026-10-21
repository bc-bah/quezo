from uuid import UUID, uuid4

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.access import require_owner, require_role
from quezo_api.modules.questions.schemas import (
    Bank, BankWrite, QuestionContent, QuestionCreate, QuestionEdit,
    QuestionListParams, QuestionSummary, QuestionVersion,
)
from quezo_api.schemas import Actor, Page, PaginationParams, Role

Connection = AsyncConnection[tuple[object, ...]]
VERSION_FIELDS = """
    q.id AS "questionId", q.bank_id AS "bankId", v.id AS "versionId",
    v.revision, v.question_type AS "questionType", v.prompt, v.options,
    v.correct_option_id AS "correctOptionId", v.default_points AS "defaultPoints",
    v.feedback, v.created_at AS "createdAt"
"""
SUMMARY_FIELDS = """
    q.id AS "questionId", q.bank_id AS "bankId", v.id AS "versionId",
    v.revision, v.question_type AS "questionType", left(v.prompt, 120) AS "promptExcerpt",
    v.default_points AS "defaultPoints"
"""


def cursor_id(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        parsed = UUID(value)
    except ValueError:
        raise ApiError(ErrorCode.VALIDATION_FAILED) from None
    if str(parsed) != value:
        raise ApiError(ErrorCode.VALIDATION_FAILED)
    return parsed


async def get_bank(connection: Connection, actor: Actor, bank_id: UUID) -> Bank:
    require_role(actor, Role.AUTHOR)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT id, name FROM quezo.question_banks WHERE id = %s AND owner_id = %s",
            (bank_id, actor.user_id),
        )
        row = await cursor.fetchone()
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND)
    return Bank.model_validate(row)


async def list_banks(connection: Connection, actor: Actor, page: PaginationParams) -> Page[Bank]:
    require_role(actor, Role.AUTHOR)
    after = cursor_id(page.cursor)
    if after is not None:
        await get_bank(connection, actor, after)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT id, name FROM quezo.question_banks WHERE owner_id = %s AND NOT archived "
            "AND (%s::uuid IS NULL OR id > %s) ORDER BY id LIMIT %s",
            (actor.user_id, after, after, page.page_size + 1),
        )
        rows = await cursor.fetchall()
    items = [Bank.model_validate(row) for row in rows[:page.page_size]]
    return Page[Bank].model_validate({
        "items": items, "nextCursor": str(items[-1].id) if len(rows) > page.page_size else None,
    })


async def write_bank(
    connection: Connection, actor: Actor, body: BankWrite, bank_id: UUID | None = None,
) -> Bank:
    require_role(actor, Role.AUTHOR)
    if bank_id is None:
        bank_id = uuid4()
        await connection.execute(
            "INSERT INTO quezo.question_banks (id, owner_id, name) VALUES (%s, %s, %s)",
            (bank_id, actor.user_id, body.name),
        )
    else:
        await get_bank(connection, actor, bank_id)
        result = await connection.execute(
            "UPDATE quezo.question_banks SET name = %s "
            "WHERE id = %s AND owner_id = %s AND NOT archived",
            (body.name, bank_id, actor.user_id),
        )
        if result.rowcount != 1:
            raise ApiError(ErrorCode.INVALID_STATE)
    return Bank.model_validate({"id": bank_id, "name": body.name})


async def get_question(
    connection: Connection, actor: Actor, question_id: UUID, version_id: UUID | None = None,
) -> QuestionVersion:
    require_role(actor, Role.AUTHOR)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT " + VERSION_FIELDS +
            " FROM quezo.questions q JOIN quezo.question_versions v ON v.question_id = q.id "
            "WHERE q.id = %s AND q.owner_id = %s "
            "AND ((%s::uuid IS NULL AND v.revision = q.revision) OR v.id = %s)",
            (question_id, actor.user_id, version_id, version_id),
        )
        row = await cursor.fetchone()
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND)
    return QuestionVersion.model_validate(row)


async def list_questions(
    connection: Connection, actor: Actor, page: QuestionListParams,
) -> Page[QuestionSummary]:
    require_role(actor, Role.AUTHOR)
    if page.bank_id is not None:
        await get_bank(connection, actor, page.bank_id)
    after = cursor_id(page.cursor)
    if after is not None:
        previous = await get_question(connection, actor, after)
        if page.bank_id is not None and previous.bank_id != page.bank_id:
            raise ApiError(ErrorCode.NOT_FOUND)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT " + SUMMARY_FIELDS +
            " FROM quezo.questions q JOIN quezo.question_versions v "
            "ON (v.question_id, v.revision) = (q.id, q.revision) "
            "JOIN quezo.question_banks b ON b.id = q.bank_id "
            "WHERE q.owner_id = %s AND NOT q.archived AND NOT b.archived "
            "AND (%s::uuid IS NULL OR q.bank_id = %s) "
            "AND (%s::uuid IS NULL OR q.id > %s) ORDER BY q.id LIMIT %s",
            (actor.user_id, page.bank_id, page.bank_id, after, after, page.page_size + 1),
        )
        rows = await cursor.fetchall()
    items = [QuestionSummary.model_validate(row) for row in rows[:page.page_size]]
    return Page[QuestionSummary].model_validate({
        "items": items,
        "nextCursor": str(items[-1].question_id) if len(rows) > page.page_size else None,
    })


async def list_versions(
    connection: Connection, actor: Actor, question_id: UUID, page: PaginationParams,
) -> Page[QuestionSummary]:
    await get_question(connection, actor, question_id)
    after = cursor_id(page.cursor)
    revision = 0
    if after is not None:
        revision = (await get_question(connection, actor, question_id, after)).revision
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT " + SUMMARY_FIELDS +
            " FROM quezo.questions q JOIN quezo.question_versions v ON v.question_id = q.id "
            "WHERE q.id = %s AND q.owner_id = %s AND v.revision > %s "
            "ORDER BY v.revision, v.id LIMIT %s",
            (question_id, actor.user_id, revision, page.page_size + 1),
        )
        rows = await cursor.fetchall()
    items = [QuestionSummary.model_validate(row) for row in rows[:page.page_size]]
    return Page[QuestionSummary].model_validate({
        "items": items,
        "nextCursor": str(items[-1].version_id) if len(rows) > page.page_size else None,
    })


async def insert_version(
    connection: Connection, question_id: UUID, revision: int, body: QuestionContent,
) -> UUID:
    version_id = uuid4()
    await connection.execute(
        "INSERT INTO quezo.question_versions "
        "(id, question_id, revision, question_type, prompt, options, correct_option_id, "
        "default_points, feedback) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (version_id, question_id, revision, body.question_type, body.prompt,
         Jsonb([option.model_dump(mode="json") for option in body.options]),
         body.correct_option_id, body.default_points, body.feedback),
    )
    return version_id


async def create_question(
    connection: Connection, actor: Actor, body: QuestionCreate,
) -> QuestionVersion:
    await get_bank(connection, actor, body.bank_id)
    cursor = await connection.execute(
        "SELECT archived FROM quezo.question_banks WHERE id = %s AND owner_id = %s FOR SHARE",
        (body.bank_id, actor.user_id),
    )
    if await cursor.fetchone() != (False,):
        raise ApiError(ErrorCode.INVALID_STATE)
    question_id = uuid4()
    await connection.execute(
        "INSERT INTO quezo.questions (id, bank_id, owner_id, revision) VALUES (%s, %s, %s, 1)",
        (question_id, body.bank_id, actor.user_id),
    )
    version_id = await insert_version(connection, question_id, 1, body)
    return await get_question(connection, actor, question_id, version_id)


async def edit_question(
    connection: Connection, actor: Actor, question_id: UUID, body: QuestionEdit,
) -> QuestionVersion:
    require_role(actor, Role.AUTHOR)
    cursor = await connection.execute(
        "SELECT owner_id, revision, archived FROM quezo.questions "
        "WHERE id = %s AND owner_id = %s FOR UPDATE",
        (question_id, actor.user_id),
    )
    row = await cursor.fetchone()
    require_owner(actor, UUID(str(row[0])) if row else None, Role.AUTHOR)
    assert row is not None
    if row[2] or row[1] == 2147483647:
        raise ApiError(ErrorCode.INVALID_STATE)
    if row[1] != body.expected_revision:
        raise ApiError(ErrorCode.DRAFT_REVISION_CONFLICT)
    revision = body.expected_revision + 1
    version_id = await insert_version(connection, question_id, revision, body)
    await connection.execute(
        "UPDATE quezo.questions SET revision = %s WHERE id = %s AND owner_id = %s",
        (revision, question_id, actor.user_id),
    )
    return await get_question(connection, actor, question_id, version_id)
