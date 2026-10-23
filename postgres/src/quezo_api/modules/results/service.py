from datetime import datetime
from uuid import UUID

from psycopg.rows import dict_row

from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.attempts.finalization import database_time, finalize_locked, lock_attempt
from quezo_api.modules.identity.tokens import VerifiedIdentity
from quezo_api.modules.questions.service import Connection
from quezo_api.modules.quizzes.policies import QuizPolicy, Release
from quezo_api.modules.results.schemas import (
    LearnerResult, ReleasedAnswerKey, ReleasedExplanations, ReleasedScore, WithheldResult,
)


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
