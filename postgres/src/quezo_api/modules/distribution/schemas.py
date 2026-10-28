from typing import Annotated, Literal

from pydantic import Field, StrictInt

from quezo_api.modules.quizzes.schemas import Title
from quezo_api.schemas import ApiModel, NonNegativeInteger, PublicId, UtcTimestamp


class EligibleLearner(ApiModel):
    user_id: PublicId


class AssignmentCreate(ApiModel):
    quiz_id: PublicId
    version_id: PublicId
    learner_id: PublicId


class Assignment(ApiModel):
    id: PublicId
    quiz_id: PublicId
    version_id: PublicId
    learner_id: PublicId
    title: Title
    state: Literal["not_yet_available", "available", "in_progress", "completed_remaining", "exhausted", "closed"]
    attempts_started: NonNegativeInteger
    attempts_completed: NonNegativeInteger
    attempts_remaining: NonNegativeInteger | None
    active_attempt_id: PublicId | None
    latest_completed_attempt_id: PublicId | None
    availability_start: UtcTimestamp | None
    availability_end: UtcTimestamp | None
    duration_seconds: Annotated[StrictInt, Field(ge=60, le=604800)] | None
    time_zone: str
