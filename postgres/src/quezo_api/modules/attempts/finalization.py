from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from psycopg.rows import dict_row

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.attempts.schemas import Completion
from quezo_api.modules.identity.access import require_owner, require_role, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection
from quezo_api.modules.scoring import QuestionSnapshot, SavedResponse, ScoringInput, score
from quezo_api.schemas import Role


async def lock_attempt(
    connection: Connection, attempt_id: UUID, identity: VerifiedIdentity | None,
) -> dict[str, Any]:
    # None is the internal expiry worker, never an HTTP authentication fallback.
    actor = await resolve_actor(connection, identity) if identity is not None else None
    if actor is not None:
        require_role(actor, Role.LEARNER)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT * FROM quezo.attempts WHERE id = %s"
            + (" AND learner_id = %s" if actor is not None else "") + " FOR UPDATE",
            (attempt_id, actor.user_id) if actor is not None else (attempt_id,),
        )
        attempt = await cursor.fetchone()
        if attempt is None:
            raise ApiError(ErrorCode.NOT_FOUND)
    if identity is not None:
        require_owner(await resolve_actor(connection, identity), attempt["learner_id"], Role.LEARNER)
    return attempt


async def database_time(connection: Connection) -> datetime:
    cursor = await connection.execute("SELECT clock_timestamp()")
    row = await cursor.fetchone()
    assert row is not None and isinstance(row[0], datetime)
    return row[0]


async def finalize_locked(
    connection: Connection, attempt: dict[str, Any], now: datetime, *, submit: bool = False,
) -> Completion | None:
    """Caller holds the parent lock and has sampled database time after that lock."""
    if attempt["state"] == "finalized":
        return Completion.model_validate({
            "attemptId": attempt["id"], "state": "finalized",
            "completionReason": attempt["completion_reason"], "finalizedAt": attempt["finalized_at"],
        })
    overdue = attempt["deadline"] is not None and now >= attempt["deadline"]
    if not submit and not overdue:
        return None
    reason = "expired" if overdue else "submitted"
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT q.id, q.question, q.options, q.effective_points, r.selected_option_id "
            "FROM quezo.attempt_questions q JOIN quezo.attempt_responses r ON r.question_id = q.id "
            "WHERE q.attempt_id = %s ORDER BY q.position", (attempt["id"],),
        )
        rows = await cursor.fetchall()
        result = score(ScoringInput(
            questions=tuple(QuestionSnapshot.model_validate({
                "attempt_question_id": row["id"], "question_type": row["question"]["questionType"],
                "option_ids": tuple(UUID(option["id"]) for option in row["options"]),
                "correct_option_id": UUID(row["question"]["correctOptionId"]), "points": row["effective_points"],
            }) for row in rows),
            responses=tuple(SavedResponse(
                attempt_question_id=row["id"], selected_option_id=row["selected_option_id"],
            ) for row in rows),
        ))
        grade_id = uuid4()
        await cursor.execute(
            "INSERT INTO quezo.grades (id, attempt_id, earned_points, possible_points) VALUES (%s,%s,%s,%s)",
            (grade_id, attempt["id"], result.earned_points, result.possible_points),
        )
        for item in result.items:
            await cursor.execute(
                "INSERT INTO quezo.grade_items (attempt_id, question_id, outcome, earned_points, possible_points) "
                "VALUES (%s,%s,%s,%s,%s)",
                (attempt["id"], item.attempt_question_id, item.outcome.value, item.earned_points, item.possible_points),
            )
        await cursor.execute(
            "UPDATE quezo.attempts SET state = 'finalized', completion_reason = %s, finalized_at = %s WHERE id = %s",
            (reason, now, attempt["id"]),
        )
        await cursor.execute(
            "INSERT INTO quezo.attempt_completion_events (attempt_id, reason, finalized_at) VALUES (%s,%s,%s)",
            (attempt["id"], reason, now),
        )
    attempt.update(state="finalized", completion_reason=reason, finalized_at=now)
    return Completion.model_validate({
        "attemptId": attempt["id"], "state": "finalized", "completionReason": reason, "finalizedAt": now,
    })


async def submit(connection: Connection, identity: VerifiedIdentity, attempt_id: UUID) -> Completion:
    attempt = await lock_attempt(connection, attempt_id, identity)
    result = await finalize_locked(connection, attempt, await database_time(connection), submit=True)
    assert result is not None
    return result
