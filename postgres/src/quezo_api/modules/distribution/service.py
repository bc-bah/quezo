from uuid import UUID, uuid4

from psycopg.rows import dict_row

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.access import require_role, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection, cursor_id
from quezo_api.modules.quizzes import service as quizzes
from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.modules.distribution.schemas import Assignment, AssignmentCreate, EligibleLearner
from quezo_api.schemas import Actor, Page, PaginationParams, Role


async def eligible_learners(
    connection: Connection, actor: Actor, page: PaginationParams,
) -> Page[EligibleLearner]:
    require_role(actor, Role.AUTHOR)
    after = cursor_id(page.cursor)
    # Accounts deliberately have no profile/email fields. Only application IDs are disclosed.
    rows = await (await connection.execute(
        "SELECT a.id FROM quezo.accounts a WHERE a.status = 'active' "
        "AND EXISTS (SELECT 1 FROM quezo.account_roles r WHERE r.account_id = a.id AND r.role = 'learner') "
        "AND EXISTS (SELECT 1 FROM quezo.identity_mappings m WHERE m.account_id = a.id AND m.active) "
        "AND (%s::uuid IS NULL OR a.id > %s) ORDER BY a.id LIMIT %s",
        (after, after, page.page_size + 1),
    )).fetchall()
    items = [EligibleLearner.model_validate({"userId": row[0]}) for row in rows[:page.page_size]]
    return Page[EligibleLearner].model_validate({
        "items": items, "nextCursor": str(items[-1].user_id) if len(rows) > page.page_size else None,
    })


async def get_assignment(
    connection: Connection, actor: Actor, assignment_id: UUID, *, author: bool = False,
) -> Assignment:
    require_role(actor, Role.AUTHOR if author else Role.LEARNER)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            'SELECT a.id, a.quiz_id AS "quizId", a.version_id AS "versionId", a.learner_id AS "learnerId", '
            "v.title, q.state AS quiz_state, v.policy, clock_timestamp() AS now, "
            "(SELECT count(*) FROM quezo.attempts t WHERE t.assignment_id = a.id) AS started, "
            "(SELECT count(*) FROM quezo.attempts t WHERE t.assignment_id = a.id AND t.state <> 'in_progress') AS completed, "
            "(SELECT t.id FROM quezo.attempts t WHERE t.assignment_id = a.id AND t.state = 'in_progress') AS active, "
            "(SELECT t.id FROM quezo.attempts t WHERE t.assignment_id = a.id AND t.state = 'finalized' "
            'ORDER BY t.attempt_number DESC LIMIT 1) AS "latestCompletedAttemptId" '
            "FROM quezo.assignments a JOIN quezo.quiz_versions v ON v.id = a.version_id "
            "JOIN quezo.quizzes q ON q.id = a.quiz_id WHERE a.id = %s AND "
            + ("q.owner_id = %s" if author else "a.learner_id = %s"),
            (assignment_id, actor.user_id),
        )
        row = await cursor.fetchone()
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND)
    policy = QuizPolicy.model_validate(row.pop("policy"))
    now, quiz_state = row.pop("now"), row.pop("quiz_state")
    started, completed, active = row.pop("started"), row.pop("completed"), row.pop("active")
    remaining = None if policy.attempt_limit is None else max(0, policy.attempt_limit - started)
    if active is not None:
        state = "in_progress"
    elif quiz_state != "published" or (policy.availability_end is not None and now >= policy.availability_end):
        state = "closed"
    elif remaining == 0:
        state = "exhausted"
    elif policy.availability_start is not None and now < policy.availability_start:
        state = "not_yet_available"
    else:
        state = "completed_remaining" if completed else "available"
    return Assignment.model_validate({
        **row, "state": state, "attemptsStarted": started, "attemptsCompleted": completed,
        "attemptsRemaining": remaining, "activeAttemptId": active,
        "availabilityStart": policy.availability_start, "availabilityEnd": policy.availability_end,
        "durationSeconds": policy.duration_seconds, "timeZone": policy.time_zone,
    })


async def list_assignments(
    connection: Connection, actor: Actor, page: PaginationParams,
) -> Page[Assignment]:
    require_role(actor, Role.LEARNER)
    after = cursor_id(page.cursor)
    if after is not None:
        await get_assignment(connection, actor, after)
    rows = await (await connection.execute(
        "SELECT id FROM quezo.assignments WHERE learner_id = %s AND (%s::uuid IS NULL OR id > %s) "
        "ORDER BY id LIMIT %s", (actor.user_id, after, after, page.page_size + 1),
    )).fetchall()
    items = [await get_assignment(connection, actor, UUID(str(row[0]))) for row in rows[:page.page_size]]
    return Page[Assignment].model_validate({
        "items": items, "nextCursor": str(items[-1].id) if len(rows) > page.page_size else None,
    })


async def assign(
    connection: Connection, actor: Actor, body: AssignmentCreate, identity: VerifiedIdentity,
) -> tuple[Assignment, bool]:
    quiz = await quizzes.get_quiz(connection, actor, body.quiz_id, lock=True)
    actor = await resolve_actor(connection, identity)
    require_role(actor, Role.AUTHOR)
    await quizzes.get_version(connection, actor, body.quiz_id, body.version_id)
    recipient = await (await connection.execute(
        "SELECT a.id FROM quezo.accounts a WHERE a.id = %s AND a.status = 'active' "
        "AND EXISTS (SELECT 1 FROM quezo.account_roles r WHERE r.account_id = a.id AND r.role = 'learner') "
        "AND EXISTS (SELECT 1 FROM quezo.identity_mappings m WHERE m.account_id = a.id AND m.active)",
        (body.learner_id,),
    )).fetchone()
    if recipient is None:
        raise ApiError(ErrorCode.NOT_FOUND)
    existing = await (await connection.execute(
        "SELECT id FROM quezo.assignments WHERE learner_id = %s AND version_id = %s",
        (body.learner_id, body.version_id),
    )).fetchone()
    if existing is not None:
        return await get_assignment(connection, actor, UUID(str(existing[0])), author=True), False
    if quiz.state != "published":
        raise ApiError(ErrorCode.ASSESSMENT_UNAVAILABLE)
    assignment_id = uuid4()
    await connection.execute(
        "INSERT INTO quezo.assignments (id, quiz_id, version_id, learner_id) VALUES (%s, %s, %s, %s)",
        (assignment_id, body.quiz_id, body.version_id, body.learner_id),
    )
    return await get_assignment(connection, actor, assignment_id, author=True), True
