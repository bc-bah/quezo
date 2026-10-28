from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.attempts.finalization import database_time, finalize_locked, lock_attempt
from quezo_api.modules.attempts.schemas import Completion
from quezo_api.modules.identity.access import require_role, resolve_actor
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection, cursor_id
from quezo_api.modules.quizzes import service as quizzes
from quezo_api.modules.quizzes.policies import QuizPolicy, Release
from quezo_api.modules.results.schemas import (
    AssignedLearnerReport, AttemptHistoryItem, FinalizedSubmission, LearnerResult,
    QuizReport, ReleasedAnswerKey, ReleasedExplanations, ReleasedScore, WithheldResult,
)
from quezo_api.schemas import Actor, Page, PaginationParams, Role


def released(mode: Release, availability_end: datetime | None, now: datetime) -> bool:
    if mode == "after_finalization":
        return True
    if mode == "after_availability_end":
        if availability_end is None:
            raise ValueError("Release after availability requires a finite end")
        return now >= availability_end
    return False


async def get_result(connection: Connection, identity: VerifiedIdentity, attempt_id: UUID) -> LearnerResult:
    attempt = await lock_attempt(connection, attempt_id, identity)
    now = await database_time(connection)
    completion = await finalize_locked(connection, attempt, now)
    if completion is None:
        raise ApiError(ErrorCode.INVALID_STATE)
    return await project_result(connection, attempt, completion, now)


async def project_result(
    connection: Connection, attempt: dict[str, Any], completion: Completion, now: datetime,
) -> LearnerResult:
    """Only call after authorizing the attempt relationship and finalization."""
    attempt_id = attempt["id"]
    policy = QuizPolicy.model_validate(attempt["policy"])
    score: ReleasedScore | WithheldResult = WithheldResult(status="withheld")
    key: ReleasedAnswerKey | WithheldResult = WithheldResult(status="withheld")
    explanations: ReleasedExplanations | WithheldResult = WithheldResult(status="withheld")
    async with connection.cursor(row_factory=dict_row) as cursor:
        # Fetch only permitted data, never the full scorer or private question object.
        if released(policy.score_release, policy.availability_end, now):
            await cursor.execute(
                'SELECT earned_points AS "earnedPoints", possible_points AS "possiblePoints" '
                "FROM quezo.grades WHERE attempt_id = %s", (attempt_id,),
            )
            grade = await cursor.fetchone()
            assert grade is not None
            score = ReleasedScore.model_validate({"status": "released", **grade})
        if released(policy.answer_key_release, policy.availability_end, now):
            await cursor.execute(
                'SELECT q.id AS "attemptQuestionId", q.position, q.question->>\'prompt\' AS prompt, '
                'o.option AS "correctOption", i.outcome, i.earned_points AS "earnedPoints", '
                'i.possible_points AS "possiblePoints" FROM quezo.attempt_questions q '
                "JOIN quezo.grade_items i ON i.question_id = q.id AND i.attempt_id = q.attempt_id "
                "CROSS JOIN LATERAL jsonb_array_elements(q.options) AS o(option) "
                "WHERE q.attempt_id = %s AND o.option->>'id' = q.question->>'correctOptionId' "
                "ORDER BY q.position", (attempt_id,),
            )
            key = ReleasedAnswerKey.model_validate({"status": "released", "items": await cursor.fetchall()})
        if released(policy.explanation_release, policy.availability_end, now):
            await cursor.execute(
                'SELECT id AS "attemptQuestionId", position, question->>\'prompt\' AS prompt, '
                "question->>'feedback' AS feedback FROM quezo.attempt_questions "
                "WHERE attempt_id = %s ORDER BY position", (attempt_id,),
            )
            explanations = ReleasedExplanations.model_validate({"status": "released", "items": await cursor.fetchall()})
    return LearnerResult.model_validate({
        "completion": completion, "title": attempt["title"], "versionId": attempt["version_id"],
        "attemptNumber": attempt["attempt_number"], "serverTime": now,
        "score": score, "answerKey": key, "explanations": explanations,
    })


def history_item(row: dict[str, Any], now: datetime) -> AttemptHistoryItem:
    policy = QuizPolicy.model_validate(row["policy"])
    completion = None
    score: dict[str, Any] = {"status": "not_finalized"}
    if row["state"] == "finalized":
        completion = {
            "attemptId": row["id"], "state": "finalized",
            "completionReason": row["completion_reason"], "finalizedAt": row["finalized_at"],
        }
        score = {"status": "withheld"}
        if released(policy.score_release, policy.availability_end, now):
            score = {"status": "released", "earnedPoints": row["earned_points"],
                     "possiblePoints": row["grade_possible_points"]}
    return AttemptHistoryItem.model_validate({
        "id": row["id"], "assignmentId": row["assignment_id"], "learnerId": row["learner_id"],
        "versionId": row["version_id"], "title": row["title"], "attemptNumber": row["attempt_number"],
        "state": row["state"], "startedAt": row["started_at"], "deadline": row["deadline"],
        "timingChoice": row["timing_choice"], "adjustedDurationSeconds": row["adjusted_duration_seconds"],
        "completion": completion, "score": score,
    })


# Do not load protected Grade values for rows whose pinned score policy withholds them.
ATTEMPT_ROWS = """
    SELECT t.*, g.earned_points, g.possible_points AS grade_possible_points
    FROM quezo.attempts t
    JOIN quezo.assignments a ON a.id = t.assignment_id
    LEFT JOIN quezo.grades g ON g.attempt_id = t.id AND t.state = 'finalized'
        AND (t.policy->>'scoreRelease' = 'after_finalization'
            OR (t.policy->>'scoreRelease' = 'after_availability_end'
                AND (t.policy->>'availabilityEnd')::timestamptz <= %s))
"""


async def attempt_page(
    connection: Connection, actor: Actor, page: PaginationParams, *, quiz_id: UUID | None = None,
) -> Page[AttemptHistoryItem]:
    require_role(actor, Role.LEARNER if quiz_id is None else Role.AUTHOR)
    if quiz_id is not None:
        await quizzes.get_quiz(connection, actor, quiz_id)
    after = cursor_id(page.cursor)
    scope = "t.learner_id = %s" if quiz_id is None else "a.quiz_id = %s"
    scope_id = actor.user_id if quiz_id is None else quiz_id
    async with connection.cursor(row_factory=dict_row) as cursor:
        if after is not None:
            await cursor.execute(
                "SELECT t.id FROM quezo.attempts t JOIN quezo.assignments a ON a.id = t.assignment_id "
                f"WHERE {scope} AND t.id = %s", (scope_id, after),
            )
            if await cursor.fetchone() is None:
                raise ApiError(ErrorCode.NOT_FOUND)
        now = await database_time(connection)
        await cursor.execute(
            ATTEMPT_ROWS + f" WHERE {scope} AND (%s::uuid IS NULL OR t.id > %s) ORDER BY t.id LIMIT %s",
            (now, scope_id, after, after, page.page_size + 1),
        )
        rows = await cursor.fetchall()
    items = [history_item(row, now) for row in rows[:page.page_size]]
    return Page[AttemptHistoryItem].model_validate({
        "items": items, "nextCursor": str(items[-1].id) if len(rows) > page.page_size else None,
    })


async def learner_history(
    connection: Connection, identity: VerifiedIdentity, page: PaginationParams,
) -> Page[AttemptHistoryItem]:
    return await attempt_page(connection, await resolve_actor(connection, identity), page)


async def quiz_report(
    connection: Connection, identity: VerifiedIdentity, quiz_id: UUID, page: PaginationParams,
) -> QuizReport:
    actor = await resolve_actor(connection, identity)
    quiz = await quizzes.get_quiz(connection, actor, quiz_id)
    after = cursor_id(page.cursor)
    now = await database_time(connection)
    async with connection.cursor(row_factory=dict_row) as cursor:
        if after is not None:
            await cursor.execute(
                "SELECT id FROM quezo.assignments WHERE quiz_id = %s AND learner_id = %s", (quiz_id, after),
            )
            if await cursor.fetchone() is None:
                raise ApiError(ErrorCode.NOT_FOUND)
        await cursor.execute("""
            SELECT count(DISTINCT a.learner_id) AS "assignedLearners",
                count(DISTINCT a.learner_id) FILTER (WHERE t.id IS NOT NULL) AS "participatingLearners",
                count(DISTINCT a.learner_id) FILTER (WHERE t.state = 'finalized') AS "completedLearners",
                count(t.id) AS "startedAttempts",
                count(t.id) FILTER (WHERE t.state = 'in_progress') AS "inProgressAttempts",
                count(t.id) FILTER (WHERE t.state = 'finalized') AS "finalizedAttempts",
                count(t.id) FILTER (WHERE t.completion_reason = 'submitted') AS "submittedAttempts",
                count(t.id) FILTER (WHERE t.completion_reason = 'expired') AS "expiredAttempts"
            FROM quezo.assignments a LEFT JOIN quezo.attempts t ON t.assignment_id = a.id
            WHERE a.quiz_id = %s
        """, (quiz_id,))
        summary = await cursor.fetchone()
        assert summary is not None
        await cursor.execute("""
            SELECT count(g.attempt_id) AS released,
                avg(100.0 * g.earned_points / g.possible_points) AS mean
            FROM quezo.assignments a JOIN quezo.attempts t ON t.assignment_id = a.id
            JOIN quezo.grades g ON g.attempt_id = t.id
            WHERE a.quiz_id = %s AND t.state = 'finalized'
                AND (t.policy->>'scoreRelease' = 'after_finalization'
                    OR (t.policy->>'scoreRelease' = 'after_availability_end'
                        AND (t.policy->>'availabilityEnd')::timestamptz <= %s))
        """, (quiz_id, now))
        scores = await cursor.fetchone()
        assert scores is not None
        summary.update(
            scoreDenominator="released_finalized_attempts", releasedScoreAttempts=scores["released"],
            withheldScoreAttempts=summary["finalizedAttempts"] - scores["released"],
            meanScorePercent=float(scores["mean"]) if scores["mean"] is not None else None,
        )
        await cursor.execute("""
            SELECT a.learner_id AS "learnerId", count(DISTINCT a.id) AS "assignmentCount",
                count(t.id) AS "startedAttempts",
                count(t.id) FILTER (WHERE t.state = 'in_progress') AS "inProgressAttempts",
                count(t.id) FILTER (WHERE t.state = 'finalized') AS "finalizedAttempts",
                count(t.id) FILTER (WHERE t.completion_reason = 'submitted') AS "submittedAttempts",
                count(t.id) FILTER (WHERE t.completion_reason = 'expired') AS "expiredAttempts"
            FROM quezo.assignments a LEFT JOIN quezo.attempts t ON t.assignment_id = a.id
            WHERE a.quiz_id = %s AND (%s::uuid IS NULL OR a.learner_id > %s)
            GROUP BY a.learner_id ORDER BY a.learner_id LIMIT %s
        """, (quiz_id, after, after, page.page_size + 1))
        rows = await cursor.fetchall()
    items = [AssignedLearnerReport.model_validate(row) for row in rows[:page.page_size]]
    return QuizReport.model_validate({
        "quizId": quiz_id, "title": quiz.title, "serverTime": now, "summary": summary,
        "learners": {"items": items, "nextCursor": str(items[-1].learner_id) if len(rows) > page.page_size else None},
    })


async def author_attempts(
    connection: Connection, identity: VerifiedIdentity, quiz_id: UUID, page: PaginationParams,
) -> Page[AttemptHistoryItem]:
    return await attempt_page(connection, await resolve_actor(connection, identity), page, quiz_id=quiz_id)


async def finalized_submission(
    connection: Connection, identity: VerifiedIdentity, quiz_id: UUID, attempt_id: UUID,
) -> FinalizedSubmission:
    actor = await resolve_actor(connection, identity)
    await quizzes.get_quiz(connection, actor, quiz_id)
    now = await database_time(connection)
    async with connection.cursor(row_factory=dict_row) as cursor:
        await cursor.execute(ATTEMPT_ROWS + " WHERE a.quiz_id = %s AND t.id = %s", (now, quiz_id, attempt_id))
        row = await cursor.fetchone()
        if row is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        if row["state"] != "finalized":
            raise ApiError(ErrorCode.INVALID_STATE)
        item = history_item(row, now)
        assert item.completion is not None
        result = await project_result(connection, row, item.completion, now)
        await cursor.execute(
            'SELECT q.id AS "attemptQuestionId", q.position, q.question->>\'prompt\' AS prompt, q.options, '
            'jsonb_build_object(\'selectedOptionId\', r.selected_option_id, \'revision\', r.revision, '
            "'savedAt', r.saved_at) AS response FROM quezo.attempt_questions q "
            "JOIN quezo.attempt_responses r ON r.question_id = q.id AND r.attempt_id = q.attempt_id "
            "WHERE q.attempt_id = %s ORDER BY q.position", (attempt_id,),
        )
        responses = await cursor.fetchall()
    return FinalizedSubmission.model_validate({"attempt": item, "result": result, "responses": responses})
