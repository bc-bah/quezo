from typing import Annotated, Literal

from pydantic import Field, StrictInt

from quezo_api.modules.attempts.schemas import Completion
from quezo_api.modules.questions.schemas import Feedback, Option, Points, Prompt
from quezo_api.modules.quizzes.schemas import Title
from quezo_api.schemas import ApiModel, PublicId, UtcTimestamp


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
