from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StrictInt, StrictStr, model_validator

from quezo_api.modules.questions.schemas import (
    Option, Points, Prompt, QuestionType, QuestionVersion, Revision, plain_text, required_text,
)
from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.schemas import ApiModel, PaginationParams, PublicId, UtcTimestamp

Title = Annotated[
    StrictStr, Field(min_length=1, max_length=200),
    AfterValidator(plain_text), AfterValidator(required_text),
]
Instructions = Annotated[StrictStr, Field(max_length=10000), AfterValidator(plain_text)]


class Selection(ApiModel):
    question_id: PublicId
    version_id: PublicId
    point_override: Points | None = None


class QuizComposition(ApiModel):
    title: Title
    instructions: Instructions = ""
    questions: Annotated[list[Selection], Field(max_length=200)] = Field(default_factory=list)
    policy: QuizPolicy = Field(default_factory=QuizPolicy)

    @model_validator(mode="after")
    def unique_questions(self) -> Self:
        ids = [item.question_id for item in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("A question identity may occur only once")
        return self


class DraftEdit(QuizComposition):
    expected_revision: Revision


class DraftCommand(ApiModel):
    expected_revision: Revision


class QuizSummary(ApiModel):
    id: PublicId
    title: Title
    state: Literal["draft", "published", "closed", "archived"]
    draft_revision: Revision
    has_draft: bool
    published_version_id: PublicId | None


class Quiz(QuizSummary):
    draft: QuizComposition | None


class QuizListParams(PaginationParams):
    include_archived: bool = False


class PublicationSummary(ApiModel):
    id: PublicId
    quiz_id: PublicId
    draft_revision: Revision
    title: Title
    possible_points: Annotated[StrictInt, Field(gt=0, le=2000000)]
    published_at: UtcTimestamp


class PublishedQuestion(ApiModel):
    position: Annotated[StrictInt, Field(ge=1, le=200)]
    question: QuestionVersion
    point_override: Points | None
    effective_points: Points


class PublishedQuiz(ApiModel):
    id: PublicId
    quiz_id: PublicId
    draft_revision: Revision
    title: Title
    instructions: Instructions
    policy: QuizPolicy
    questions: Annotated[list[PublishedQuestion], Field(min_length=1, max_length=200)]
    possible_points: Annotated[StrictInt, Field(gt=0, le=2000000)]
    published_at: UtcTimestamp


class PublishAcknowledgement(ApiModel):
    request_id: PublicId
    quiz_id: PublicId
    version_id: PublicId
    draft_revision: Revision
    published_at: UtcTimestamp


class PreviewQuestion(ApiModel):
    position: Annotated[StrictInt, Field(ge=1, le=200)]
    question_type: QuestionType
    prompt: Prompt
    options: list[Option]
    effective_points: Points


class QuizPreview(ApiModel):
    title: Title
    instructions: Instructions
    questions: list[PreviewQuestion]
    possible_points: Annotated[StrictInt, Field(ge=0, le=2000000)]
