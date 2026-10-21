from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

from quezo_api.schemas import ApiModel, UtcTimestamp

Release = Literal["after_finalization", "after_availability_end", "never"]


class QuizPolicy(ApiModel):
    duration_seconds: Annotated[StrictInt, Field(ge=60, le=604800)] | None = None
    attempt_limit: Annotated[StrictInt, Field(ge=1, le=100)] | None = 1
    availability_start: UtcTimestamp | None = None
    availability_end: UtcTimestamp | None = None
    time_zone: Annotated[StrictStr, Field(min_length=1, max_length=100)] = "UTC"
    randomize_questions: StrictBool = False
    randomize_options: StrictBool = False
    score_release: Release = "after_finalization"
    answer_key_release: Release = "never"
    explanation_release: Release = "never"

    @field_validator("time_zone")
    @classmethod
    def valid_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("An IANA time zone is required") from None
        return value

    @model_validator(mode="after")
    def compatible(self) -> Self:
        if self.availability_start is not None and self.availability_end is not None:
            if self.availability_start >= self.availability_end:
                raise ValueError("Availability end must follow start")
        if self.availability_end is None and "after_availability_end" in (
            self.score_release, self.answer_key_release, self.explanation_release,
        ):
            raise ValueError("Release after availability requires a finite end")
        return self
