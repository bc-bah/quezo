from typing import Annotated, Literal

from pydantic import Field, StrictInt

from quezo_api.modules.attempts.schemas import Completion, AttemptState, SavedResponse
from quezo_api.modules.questions.schemas import Feedback, Option, Points, Prompt
from quezo_api.modules.quizzes.schemas import Title
from quezo_api.schemas import ApiModel, NonNegativeInteger, Page, PublicId, UtcTimestamp


class WithheldResult(ApiModel):
    status: Literal["withheld"]


class ReleasedScore(ApiModel):
    status: Literal["released"]
    earned_points: Annotated[StrictInt, Field(ge=0, le=2000000)]
    possible_points: Annotated[StrictInt, Field(ge=1, le=2000000)]


class ResultItem(ApiModel):
    attempt_question_id: PublicId
    position: Annotated[StrictInt, Field(ge=1, le=200)]
    prompt: Prompt


class AnswerKeyItem(ResultItem):
    correct_option: Option
    outcome: Literal["correct", "incorrect", "unanswered"]
    earned_points: Points
    possible_points: Points


class ExplanationItem(ResultItem):
    feedback: Feedback


class ReleasedAnswerKey(ApiModel):
    status: Literal["released"]
    items: Annotated[list[AnswerKeyItem], Field(min_length=1, max_length=200)]


class ReleasedExplanations(ApiModel):
    status: Literal["released"]
    items: Annotated[list[ExplanationItem], Field(min_length=1, max_length=200)]


class LearnerResult(ApiModel):
    completion: Completion
    title: Title
    version_id: PublicId
    attempt_number: Annotated[StrictInt, Field(ge=1)]
    server_time: UtcTimestamp
    score: Annotated[ReleasedScore | WithheldResult, Field(discriminator="status")]
    answer_key: Annotated[ReleasedAnswerKey | WithheldResult, Field(discriminator="status")]
    explanations: Annotated[ReleasedExplanations | WithheldResult, Field(discriminator="status")]


class PendingScore(ApiModel):
    status: Literal["not_finalized"]


class AttemptHistoryItem(ApiModel):
    id: PublicId
    assignment_id: PublicId
    learner_id: PublicId
    version_id: PublicId
    title: Title
    attempt_number: Annotated[StrictInt, Field(ge=1)]
    state: AttemptState
    started_at: UtcTimestamp
    deadline: UtcTimestamp | None
    timing_choice: Literal["standard", "adjusted", "off"]
    adjusted_duration_seconds: Annotated[StrictInt, Field(ge=60, le=6048000)] | None
    completion: Completion | None
    score: Annotated[ReleasedScore | WithheldResult | PendingScore, Field(discriminator="status")]


class AssignedLearnerReport(ApiModel):
    learner_id: PublicId
    assignment_count: NonNegativeInteger
    started_attempts: NonNegativeInteger
    in_progress_attempts: NonNegativeInteger
    finalized_attempts: NonNegativeInteger
    submitted_attempts: NonNegativeInteger
    expired_attempts: NonNegativeInteger


class ReportSummary(ApiModel):
    assigned_learners: NonNegativeInteger
    participating_learners: NonNegativeInteger
    completed_learners: NonNegativeInteger
    started_attempts: NonNegativeInteger
    in_progress_attempts: NonNegativeInteger
    finalized_attempts: NonNegativeInteger
    submitted_attempts: NonNegativeInteger
    expired_attempts: NonNegativeInteger
    score_denominator: Literal["released_finalized_attempts"]
    released_score_attempts: NonNegativeInteger
    withheld_score_attempts: NonNegativeInteger
    mean_score_percent: Annotated[float, Field(ge=0, le=100)] | None


class QuizReport(ApiModel):
    quiz_id: PublicId
    title: Title
    server_time: UtcTimestamp
    summary: ReportSummary
    learners: Page[AssignedLearnerReport]


class SubmissionResponse(ResultItem):
    options: Annotated[list[Option], Field(min_length=2, max_length=10)]
    response: SavedResponse


class FinalizedSubmission(ApiModel):
    attempt: AttemptHistoryItem
    result: LearnerResult
    responses: Annotated[list[SubmissionResponse], Field(min_length=1, max_length=200)]
