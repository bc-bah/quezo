from typing import Annotated, Literal

from pydantic import Field, StrictInt

from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.modules.quizzes.schemas import Instructions, PreviewQuestion, Title
from quezo_api.schemas import ApiModel, PublicId, UtcTimestamp


class StartCommand(ApiModel):
    pass


class AttemptQuestion(PreviewQuestion):
    attempt_question_id: PublicId
    question_id: PublicId
    version_id: PublicId


class Attempt(ApiModel):
    id: PublicId
    assignment_id: PublicId
    version_id: PublicId
    attempt_number: Annotated[StrictInt, Field(ge=1)]
    state: Literal["in_progress", "finalized", "expired"]
    title: Title
    instructions: Instructions
    policy: QuizPolicy
    started_at: UtcTimestamp
    deadline: UtcTimestamp | None
    possible_points: Annotated[StrictInt, Field(ge=1, le=2000000)]
    questions: Annotated[list[AttemptQuestion], Field(min_length=1, max_length=200)]
