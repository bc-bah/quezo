from datetime import datetime, timedelta
import hashlib
import json
from random import SystemRandom
from uuid import UUID, uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.attempts.schemas import Attempt, StartCommand
from quezo_api.modules.identity.access import require_owner, require_role, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection
from quezo_api.modules.questions.schemas import QuestionVersion
from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.schemas import Actor, Role


def admit(policy: QuizPolicy, now: datetime) -> datetime | None:
    if ((policy.availability_start is not None and now < policy.availability_start)
            or (policy.availability_end is not None and now >= policy.availability_end)):
        raise ApiError(ErrorCode.ASSESSMENT_UNAVAILABLE)
    bounds = [bound for bound in (
        policy.availability_end,
        now + timedelta(seconds=policy.duration_seconds) if policy.duration_seconds is not None else None,
    ) if bound is not None]
    return min(bounds) if bounds else None


async def get_attempt(connection: Connection, actor: Actor, attempt_id: UUID) -> Attempt:
    require_role(actor, Role.LEARNER)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            'SELECT id, assignment_id AS "assignmentId", version_id AS "versionId", '
            'attempt_number AS "attemptNumber", state, title, instructions, policy, '
            'started_at AS "startedAt", deadline, possible_points AS "possiblePoints" '
            "FROM quezo.attempts WHERE id = %s AND learner_id = %s", (attempt_id, actor.user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        # Never serialize the private question snapshot, even for finalized attempts.
        await cursor.execute(
            'SELECT id AS "attemptQuestionId", question_id AS "questionId", '
            'question_version_id AS "versionId", position, question->>\'questionType\' AS "questionType", '
            'question->>\'prompt\' AS prompt, options, effective_points AS "effectivePoints" '
            "FROM quezo.attempt_questions WHERE attempt_id = %s ORDER BY position", (attempt_id,),
        )
        row["questions"] = await cursor.fetchall()
    return Attempt.model_validate(row)


async def start(
    connection: Connection, identity: VerifiedIdentity, assignment_id: UUID,
    body: StartCommand, request_id: UUID,
) -> tuple[Attempt, bool]:
    actor = await resolve_actor(connection, identity)
    require_role(actor, Role.LEARNER)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT * FROM quezo.assignments WHERE id = %s AND learner_id = %s FOR UPDATE",
            (assignment_id, actor.user_id),
        )
        assignment = await cursor.fetchone()
        if assignment is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        # A queued command must not retain privileges revoked while it waited.
        actor = await resolve_actor(connection, identity)
        require_owner(actor, assignment["learner_id"], Role.LEARNER)
        fingerprint = hashlib.sha256(json.dumps({
            "actor": str(actor.user_id), "target": str(assignment_id), "operation": "start",
            "key": str(request_id), "payload": body.model_dump(mode="json"),
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        await cursor.execute(
            "SELECT fingerprint, attempt_id FROM quezo.attempt_start_commands "
            "WHERE actor_id = %s AND assignment_id = %s AND operation = 'start' AND request_id = %s",
            (actor.user_id, assignment_id, request_id),
        )
        previous = await cursor.fetchone()
        if previous is not None:
            if previous["fingerprint"] != fingerprint:
                raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT)
            return await get_attempt(connection, actor, previous["attempt_id"]), False
        await cursor.execute(
            "SELECT id FROM quezo.attempts WHERE assignment_id = %s AND state = 'in_progress' FOR UPDATE",
            (assignment_id,),
        )
        active = await cursor.fetchone()
        actor = await resolve_actor(connection, identity)
        require_owner(actor, assignment["learner_id"], Role.LEARNER)
        created = active is None
        if active is not None:
            attempt_id = active["id"]
        else:
            # Assignment -> quiz share lock -> database wall clock; closure cannot race admission.
            await cursor.execute("SELECT state FROM quezo.quizzes WHERE id = %s FOR SHARE", (assignment["quiz_id"],))
            quiz = await cursor.fetchone()
            assert quiz is not None
            actor = await resolve_actor(connection, identity)
            require_owner(actor, assignment["learner_id"], Role.LEARNER)
            if quiz["state"] != "published":
                raise ApiError(ErrorCode.ASSESSMENT_UNAVAILABLE)
            await cursor.execute("SELECT * FROM quezo.quiz_versions WHERE id = %s", (assignment["version_id"],))
            version = await cursor.fetchone()
            assert version is not None
            policy = QuizPolicy.model_validate(version["policy"])
            await cursor.execute("SELECT clock_timestamp() AS now")
            clock = await cursor.fetchone()
            assert clock is not None
            now = clock["now"]
            deadline = admit(policy, now)
            await cursor.execute("SELECT count(*) AS count FROM quezo.attempts WHERE assignment_id = %s", (assignment_id,))
            count = await cursor.fetchone()
            assert count is not None
            number = count["count"] + 1
            if policy.attempt_limit is not None and number > policy.attempt_limit:
                raise ApiError(ErrorCode.ATTEMPT_LIMIT_REACHED)
            attempt_id = uuid4()
            await cursor.execute(
                "INSERT INTO quezo.attempts (id, assignment_id, learner_id, version_id, attempt_number, "
                "title, instructions, policy, started_at, deadline, possible_points) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (attempt_id, assignment_id, actor.user_id, version["id"], number, version["title"],
                 version["instructions"], Jsonb(version["policy"]), now, deadline, version["possible_points"]),
            )
            await cursor.execute(
                "SELECT * FROM quezo.quiz_questions WHERE quiz_version_id = %s ORDER BY position", (version["id"],),
            )
            questions = await cursor.fetchall()
            random = SystemRandom()
            if policy.randomize_questions:
                random.shuffle(questions)
            for position, item in enumerate(questions, 1):
                question = QuestionVersion.model_validate(item["question"])
                options = list(question.options)
                if policy.randomize_options:
                    random.shuffle(options)
                await cursor.execute(
                    "INSERT INTO quezo.attempt_questions (id, attempt_id, version_id, question_id, "
                    "question_version_id, position, question, options, effective_points) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (uuid4(), attempt_id, version["id"], question.question_id, question.version_id, position,
                     Jsonb(item["question"]), Jsonb([option.model_dump(mode="json") for option in options]),
                     item["effective_points"]),
                )
    await connection.execute(
        "INSERT INTO quezo.attempt_start_commands "
        "(actor_id, assignment_id, operation, request_id, fingerprint, attempt_id) VALUES (%s,%s,'start',%s,%s,%s)",
        (actor.user_id, assignment_id, request_id, fingerprint, attempt_id),
    )
    return await get_attempt(connection, actor, attempt_id), created
