from typing import Annotated, Literal, Self

from pydantic import Field, StrictInt, model_validator

from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.modules.quizzes.schemas import Instructions, PreviewQuestion, Title
from quezo_api.schemas import ApiModel, PublicId, UtcTimestamp


class StartCommand(ApiModel):
    timing_choice: Literal["standard", "adjusted", "off"] = "standard"
    adjusted_duration_seconds: Annotated[StrictInt, Field(ge=60, le=6048000)] | None = None

    @model_validator(mode="after")
    def timing_duration(self) -> Self:
        if (self.timing_choice == "adjusted") != (self.adjusted_duration_seconds is not None):
            raise ValueError("Only adjusted timing requires a chosen duration")
        return self


ResponseRevision = Annotated[StrictInt, Field(ge=0, le=9007199254740991)]
AttemptState = Literal["in_progress", "finalized"]


class SubmissionCommand(ApiModel):
    pass


class Completion(ApiModel):
    attempt_id: PublicId
    state: Literal["finalized"]
    completion_reason: Literal["submitted", "expired"]
    finalized_at: UtcTimestamp


class SavedResponse(ApiModel):
    selected_option_id: PublicId | None
    revision: ResponseRevision
    saved_at: UtcTimestamp | None


class SaveCommand(ApiModel):
    request_id: PublicId
    expected_revision: ResponseRevision
    selected_option_id: PublicId | None


class SaveAcknowledgement(ApiModel):
    request_id: PublicId
    response_revision: ResponseRevision
    saved_at: UtcTimestamp


class SaveResult(ApiModel):
    acknowledgement: SaveAcknowledgement
    attempt_state: AttemptState
    server_time: UtcTimestamp


class AttemptQuestion(PreviewQuestion):
    attempt_question_id: PublicId
    question_id: PublicId
    version_id: PublicId
    response: SavedResponse


class Attempt(ApiModel):
    id: PublicId
    assignment_id: PublicId
    version_id: PublicId
    attempt_number: Annotated[StrictInt, Field(ge=1)]
    state: AttemptState
    completion: Completion | None
    title: Title
    instructions: Instructions
    policy: QuizPolicy
    started_at: UtcTimestamp
    deadline: UtcTimestamp | None
    timing_choice: Literal["standard", "adjusted", "off"]
    adjusted_duration_seconds: Annotated[StrictInt, Field(ge=60, le=6048000)] | None
    possible_points: Annotated[StrictInt, Field(ge=1, le=2000000)]
    questions: Annotated[list[AttemptQuestion], Field(min_length=1, max_length=200)]
