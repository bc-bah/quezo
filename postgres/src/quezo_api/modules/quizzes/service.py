import hashlib
import json
from random import SystemRandom
from uuid import UUID, uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.access import require_role
from quezo_api.modules.questions import service as questions
from quezo_api.modules.questions.schemas import QuestionVersion
from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.modules.quizzes.schemas import (
    DraftCommand, DraftEdit, PublishedQuestion, PublishedQuiz, PublishAcknowledgement,
    PublicationSummary, Quiz, QuizComposition, QuizListParams, QuizPreview, QuizSummary,
)
from quezo_api.schemas import Actor, Page, PaginationParams, Role

Connection = questions.Connection


async def get_quiz(connection: Connection, actor: Actor, quiz_id: UUID, *, lock: bool = False) -> Quiz:
    require_role(actor, Role.AUTHOR)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            'SELECT id, title, state, draft_revision AS "draftRevision", '
            'draft IS NOT NULL AS "hasDraft", published_version_id AS "publishedVersionId", draft '
            "FROM quezo.quizzes WHERE id = %s AND owner_id = %s" + (" FOR UPDATE" if lock else ""),
            (quiz_id, actor.user_id),
        )
        row = await cursor.fetchone()
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND)
    return Quiz.model_validate(row)


async def list_quizzes(connection: Connection, actor: Actor, page: QuizListParams) -> Page[QuizSummary]:
    require_role(actor, Role.AUTHOR)
    after = questions.cursor_id(page.cursor)
    if after is not None:
        await get_quiz(connection, actor, after)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            'SELECT id, title, state, draft_revision AS "draftRevision", '
            'draft IS NOT NULL AS "hasDraft", published_version_id AS "publishedVersionId" '
            "FROM quezo.quizzes WHERE owner_id = %s AND (%s OR state <> 'archived') "
            "AND (%s::uuid IS NULL OR id > %s) "
            "ORDER BY id LIMIT %s",
            (actor.user_id, page.include_archived, after, after, page.page_size + 1),
        )
        rows = await cursor.fetchall()
    items = [QuizSummary.model_validate(row) for row in rows[:page.page_size]]
    return Page[QuizSummary].model_validate({
        "items": items, "nextCursor": str(items[-1].id) if len(rows) > page.page_size else None,
    })


async def selected_questions(
    connection: Connection, actor: Actor, body: QuizComposition,
    retained: QuizComposition | None = None,
) -> list[PublishedQuestion]:
    existing = {(item.question_id, item.version_id) for item in retained.questions} if retained else set()
    result = []
    for position, selection in enumerate(body.questions, 1):
        if (selection.question_id, selection.version_id) not in existing:
            await questions.require_selectable(connection, actor, selection.question_id)
        question = await questions.get_question(connection, actor, selection.question_id, selection.version_id)
        result.append(PublishedQuestion.model_validate({
            "position": position, "question": question, "pointOverride": selection.point_override,
            "effectivePoints": question.default_points if selection.point_override is None else selection.point_override,
        }))
    return result


async def create_quiz(connection: Connection, actor: Actor, body: QuizComposition) -> Quiz:
    require_role(actor, Role.AUTHOR)
    await selected_questions(connection, actor, body)
    quiz_id = uuid4()
    await connection.execute(
        "INSERT INTO quezo.quizzes (id, owner_id, title, draft) VALUES (%s, %s, %s, %s)",
        (quiz_id, actor.user_id, body.title, Jsonb(body.model_dump(mode="json"))),
    )
    return await get_quiz(connection, actor, quiz_id)


def check_revision(quiz: Quiz, expected: int) -> None:
    if quiz.draft_revision != expected:
        raise ApiError(ErrorCode.DRAFT_REVISION_CONFLICT)
    if quiz.state not in ("draft", "published"):
        raise ApiError(ErrorCode.INVALID_STATE)


async def edit_draft(connection: Connection, actor: Actor, quiz_id: UUID, body: DraftEdit) -> Quiz:
    quiz = await get_quiz(connection, actor, quiz_id, lock=True)
    check_revision(quiz, body.expected_revision)
    if quiz.draft is None or quiz.draft_revision == 2147483647:
        raise ApiError(ErrorCode.INVALID_STATE)
    draft = QuizComposition.model_validate(body.model_dump(exclude={"expected_revision"}))
    await selected_questions(connection, actor, draft, quiz.draft)
    await connection.execute(
        "UPDATE quezo.quizzes SET title = %s, draft = %s, draft_revision = draft_revision + 1 WHERE id = %s",
        (draft.title, Jsonb(draft.model_dump(mode="json")), quiz_id),
    )
    return await get_quiz(connection, actor, quiz_id)


async def get_version(
    connection: Connection, actor: Actor, quiz_id: UUID, version_id: UUID,
) -> PublishedQuiz:
    await get_quiz(connection, actor, quiz_id)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            'SELECT id, quiz_id AS "quizId", draft_revision AS "draftRevision", title, instructions, '
            'policy, possible_points AS "possiblePoints", published_at AS "publishedAt" '
            "FROM quezo.quiz_versions WHERE id = %s AND quiz_id = %s AND owner_id = %s",
            (version_id, quiz_id, actor.user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        await cursor.execute(
            'SELECT position, question, point_override AS "pointOverride", effective_points AS "effectivePoints" '
            "FROM quezo.quiz_questions WHERE quiz_version_id = %s ORDER BY position",
            (version_id,),
        )
        row["questions"] = await cursor.fetchall()
    return PublishedQuiz.model_validate(row)


async def new_draft(connection: Connection, actor: Actor, quiz_id: UUID, body: DraftCommand) -> Quiz:
    quiz = await get_quiz(connection, actor, quiz_id, lock=True)
    check_revision(quiz, body.expected_revision)
    if quiz.draft is not None or quiz.published_version_id is None or quiz.draft_revision == 2147483647:
        raise ApiError(ErrorCode.INVALID_STATE)
    published = await get_version(connection, actor, quiz_id, quiz.published_version_id)
    draft = QuizComposition.model_validate({
        "title": published.title, "instructions": published.instructions, "policy": published.policy,
        "questions": [
            {"questionId": item.question.question_id, "versionId": item.question.version_id,
             "pointOverride": item.point_override} for item in published.questions
        ],
    })
    await connection.execute(
        "UPDATE quezo.quizzes SET draft = %s, draft_revision = draft_revision + 1 WHERE id = %s",
        (Jsonb(draft.model_dump(mode="json")), quiz_id),
    )
    return await get_quiz(connection, actor, quiz_id)


def learner_preview(
    title: str, instructions: str, items: list[PublishedQuestion], policy: QuizPolicy,
) -> QuizPreview:
    # Explicit allowlist: private C01 content never crosses the presentation seam.
    random = SystemRandom()
    ordered = random.sample(items, len(items)) if policy.randomize_questions else items
    return QuizPreview.model_validate({
        "title": title, "instructions": instructions,
        "possiblePoints": sum(item.effective_points for item in items),
        "questions": [
            {"position": position, "questionType": item.question.question_type,
             "prompt": item.question.prompt, "options": (
                 random.sample(item.question.options, len(item.question.options))
                 if policy.randomize_options else item.question.options),
             "effectivePoints": item.effective_points} for position, item in enumerate(ordered, 1)
        ],
    })


async def preview(connection: Connection, actor: Actor, quiz_id: UUID, body: DraftCommand) -> QuizPreview:
    quiz = await get_quiz(connection, actor, quiz_id)
    check_revision(quiz, body.expected_revision)
    if quiz.draft is None:
        raise ApiError(ErrorCode.INVALID_STATE)
    items = await selected_questions(connection, actor, quiz.draft, quiz.draft)
    return learner_preview(quiz.draft.title, quiz.draft.instructions, items, quiz.draft.policy)


async def publish(
    connection: Connection, actor: Actor, quiz_id: UUID, body: DraftCommand, request_id: UUID,
    correlation_id: UUID,
) -> tuple[PublishAcknowledgement, bool]:
    # All draft and publication commands serialize on the owning quiz, before ledger lookup.
    quiz = await get_quiz(connection, actor, quiz_id, lock=True)
    fingerprint = hashlib.sha256(json.dumps({
        "actor": str(actor.user_id), "target": str(quiz_id), "operation": "publish",
        "key": str(request_id), "payload": body.model_dump(mode="json"),
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT fingerprint, acknowledgement FROM quezo.quiz_publication_commands "
            "WHERE actor_id = %s AND quiz_id = %s AND operation = 'publish' AND request_id = %s",
            (actor.user_id, quiz_id, request_id),
        )
        previous = await cursor.fetchone()
    if previous is not None:
        if previous["fingerprint"] != fingerprint:
            raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT)
        return PublishAcknowledgement.model_validate(previous["acknowledgement"]), False
    check_revision(quiz, body.expected_revision)
    if quiz.draft is None:
        raise ApiError(ErrorCode.INVALID_STATE)
    # Revalidate stored content/policies and every exact selection inside this transaction.
    draft = QuizComposition.model_validate(quiz.draft.model_dump())
    items = await selected_questions(connection, actor, draft, quiz.draft)
    total = sum(item.effective_points for item in items)
    if not items or total <= 0:
        raise ApiError(ErrorCode.VALIDATION_FAILED)
    version_id = uuid4()
    inserted = await connection.execute(
        "INSERT INTO quezo.quiz_versions "
        "(id, quiz_id, owner_id, draft_revision, title, instructions, policy, possible_points) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING published_at",
        (version_id, quiz_id, actor.user_id, quiz.draft_revision, draft.title, draft.instructions,
         Jsonb(draft.policy.model_dump(mode="json")), total),
    )
    row = await inserted.fetchone()
    assert row is not None
    for item in items:
        question: QuestionVersion = item.question
        await connection.execute(
            "INSERT INTO quezo.quiz_questions "
            "(quiz_version_id, owner_id, question_id, question_version_id, position, question, "
            "point_override, effective_points) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (version_id, actor.user_id, question.question_id, question.version_id, item.position,
             Jsonb(question.model_dump(mode="json")), item.point_override, item.effective_points),
        )
    acknowledgement = PublishAcknowledgement.model_validate({
        "requestId": request_id, "quizId": quiz_id, "versionId": version_id,
        "draftRevision": quiz.draft_revision, "publishedAt": row[0],
    })
    await connection.execute(
        "UPDATE quezo.quizzes SET state = 'published', draft = NULL, published_version_id = %s WHERE id = %s",
        (version_id, quiz_id),
    )
    await connection.execute(
        "INSERT INTO quezo.quiz_publication_commands "
        "(actor_id, quiz_id, operation, request_id, version_id, fingerprint, acknowledgement) "
        "VALUES (%s, %s, 'publish', %s, %s, %s, %s)",
        (actor.user_id, quiz_id, request_id, version_id, fingerprint, Jsonb(acknowledgement.model_dump(mode="json"))),
    )
    await connection.execute(
        "INSERT INTO quezo.quiz_publication_events (actor_id, quiz_id, version_id, request_id, correlation_id) "
        "VALUES (%s, %s, %s, %s, %s)",
        (actor.user_id, quiz_id, version_id, request_id, correlation_id),
    )
    return acknowledgement, True


async def list_publications(
    connection: Connection, actor: Actor, quiz_id: UUID, page: PaginationParams,
) -> Page[PublicationSummary]:
    await get_quiz(connection, actor, quiz_id)
    after = questions.cursor_id(page.cursor)
    revision = 0
    if after is not None:
        revision = (await get_version(connection, actor, quiz_id, after)).draft_revision
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            'SELECT id, quiz_id AS "quizId", draft_revision AS "draftRevision", title, '
            'possible_points AS "possiblePoints", published_at AS "publishedAt" '
            "FROM quezo.quiz_versions WHERE quiz_id = %s AND owner_id = %s AND draft_revision > %s "
            "ORDER BY draft_revision, id LIMIT %s",
            (quiz_id, actor.user_id, revision, page.page_size + 1),
        )
        rows = await cursor.fetchall()
    items = [PublicationSummary.model_validate(row) for row in rows[:page.page_size]]
    return Page[PublicationSummary].model_validate({
        "items": items, "nextCursor": str(items[-1].id) if len(rows) > page.page_size else None,
    })


async def transition(
    connection: Connection, actor: Actor, quiz_id: UUID, body: DraftCommand, target: str,
) -> Quiz:
    quiz = await get_quiz(connection, actor, quiz_id, lock=True)
    if quiz.draft_revision != body.expected_revision:
        raise ApiError(ErrorCode.DRAFT_REVISION_CONFLICT)
    if target == "closed":
        if quiz.state != "published":
            raise ApiError(ErrorCode.INVALID_STATE)
    elif target == "archived":
        if quiz.state not in ("draft", "closed"):
            raise ApiError(ErrorCode.INVALID_STATE)
        active = await connection.execute(
            "SELECT 1 FROM quezo.attempts t JOIN quezo.assignments a ON a.id = t.assignment_id "
            "WHERE a.quiz_id = %s AND t.state = 'in_progress' LIMIT 1", (quiz_id,),
        )
        if await active.fetchone() is not None:
            raise ApiError(ErrorCode.INVALID_STATE)
    else:
        raise ApiError(ErrorCode.INVALID_STATE)
    await connection.execute("UPDATE quezo.quizzes SET state = %s WHERE id = %s", (target, quiz_id))
    return await get_quiz(connection, actor, quiz_id)
