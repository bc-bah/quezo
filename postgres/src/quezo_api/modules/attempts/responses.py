from datetime import datetime
import hashlib
import json
from uuid import UUID

from psycopg.rows import dict_row

from quezo_api.errors import ApiError, AttemptAdmissionDetails, ErrorCode, ResponseConflictDetails
from quezo_api.modules.attempts.schemas import SaveCommand, SaveResult
from quezo_api.modules.identity.access import require_owner, require_role, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection
from quezo_api.schemas import Role


def admit_save(state: str, deadline: datetime | None, now: datetime) -> None:
    details = AttemptAdmissionDetails.model_validate({
        "attemptState": state, "deadline": deadline, "serverTime": now,
    })
    if state != "in_progress":
        raise ApiError(ErrorCode.ATTEMPT_FINALIZED, details=details)
    if deadline is not None and now >= deadline:
        raise ApiError(ErrorCode.DEADLINE_PASSED, details=details)


async def save(
    connection: Connection, identity: VerifiedIdentity, attempt_id: UUID,
    question_id: UUID, body: SaveCommand,
) -> SaveResult:
    actor = await resolve_actor(connection, identity)
    require_role(actor, Role.LEARNER)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(
            "SELECT learner_id, state, deadline FROM quezo.attempts "
            "WHERE id = %s AND learner_id = %s FOR UPDATE", (attempt_id, actor.user_id),
        )
        attempt = await cursor.fetchone()
        if attempt is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        actor = await resolve_actor(connection, identity)
        require_owner(actor, attempt["learner_id"], Role.LEARNER)
        await cursor.execute(
            "SELECT q.options, r.selected_option_id, r.revision, r.saved_at "
            "FROM quezo.attempt_questions q JOIN quezo.attempt_responses r ON r.question_id = q.id "
            "WHERE q.id = %s AND q.attempt_id = %s", (question_id, attempt_id),
        )
        current = await cursor.fetchone()
        if current is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        fingerprint = hashlib.sha256(json.dumps({
            "actor": str(actor.user_id), "target": str(attempt_id), "operation": "save",
            "question": str(question_id), "payload": body.model_dump(mode="json"),
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        await cursor.execute(
            "SELECT fingerprint, response_revision, saved_at FROM quezo.response_commands "
            "WHERE actor_id = %s AND attempt_id = %s AND operation = 'save' AND request_id = %s",
            (actor.user_id, attempt_id, body.request_id),
        )
        previous = await cursor.fetchone()
        await cursor.execute("SELECT clock_timestamp() AS now")
        clock = await cursor.fetchone()
        assert clock is not None
        now = clock["now"]
        if previous is not None:
            if previous["fingerprint"] != fingerprint:
                raise ApiError(ErrorCode.IDEMPOTENCY_CONFLICT)
            revision, saved_at = previous["response_revision"], previous["saved_at"]
        else:
            admit_save(attempt["state"], attempt["deadline"], now)
            if body.selected_option_id is not None and str(body.selected_option_id) not in {
                option["id"] for option in current["options"]
            }:
                raise ApiError(ErrorCode.VALIDATION_FAILED)
            if current["revision"] != body.expected_revision:
                raise ApiError(ErrorCode.RESPONSE_REVISION_CONFLICT, details=ResponseConflictDetails.model_validate({
                    "currentRevision": current["revision"], "selectedOptionId": current["selected_option_id"],
                    "savedAt": current["saved_at"],
                }))
            revision, saved_at = current["revision"] + 1, now
            await cursor.execute(
                "UPDATE quezo.attempt_responses SET selected_option_id = %s, revision = %s, saved_at = %s "
                "WHERE question_id = %s AND revision = %s",
                (body.selected_option_id, revision, saved_at, question_id, body.expected_revision),
            )
            assert cursor.rowcount == 1
            await cursor.execute(
                "INSERT INTO quezo.response_commands (actor_id, attempt_id, operation, request_id, "
                "question_id, fingerprint, response_revision, selected_option_id, saved_at) "
                "VALUES (%s,%s,'save',%s,%s,%s,%s,%s,%s)",
                (actor.user_id, attempt_id, body.request_id, question_id, fingerprint,
                 revision, body.selected_option_id, saved_at),
            )
    return SaveResult.model_validate({
        "acknowledgement": {"requestId": body.request_id, "responseRevision": revision, "savedAt": saved_at},
        "attemptState": attempt["state"], "serverTime": now,
    })
