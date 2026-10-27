from typing import Annotated, Literal, Self

from pydantic import AfterValidator, Field, StrictInt, StrictStr, model_validator

from quezo_api.schemas import ApiModel, PaginationParams, PublicId, UtcTimestamp


def plain_text(value: str) -> str:
    # Text is stored verbatim and rendered as text, never HTML or Markdown.
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError("Text must be valid Unicode") from None
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError("Unsupported control character")
    return value


def required_text(value: str) -> str:
    if not value.strip():
        raise ValueError("Text is required")
    return value


BankName = Annotated[
    StrictStr, Field(min_length=1, max_length=100),
    AfterValidator(plain_text), AfterValidator(required_text),
]
Prompt = Annotated[
    StrictStr, Field(min_length=1, max_length=4000),
    AfterValidator(plain_text), AfterValidator(required_text),
]
OptionText = Annotated[
    StrictStr, Field(min_length=1, max_length=1000),
    AfterValidator(plain_text), AfterValidator(required_text),
]
Feedback = Annotated[StrictStr, Field(max_length=4000), AfterValidator(plain_text)]
Points = Annotated[StrictInt, Field(ge=0, le=10000)]
Revision = Annotated[StrictInt, Field(ge=1, le=2147483647)]
QuestionType = Literal["mcq", "true_false"]


class BankWrite(ApiModel):
    name: BankName


class Bank(BankWrite):
    id: PublicId
    archived: bool = False


Category = Annotated[
    StrictStr, Field(min_length=1, max_length=100),
    AfterValidator(plain_text), AfterValidator(required_text),
]
Tag = Annotated[
    StrictStr, Field(min_length=1, max_length=50),
    AfterValidator(plain_text), AfterValidator(required_text),
]


class QuestionMetadata(ApiModel):
    category: Category | None = None
    tags: Annotated[list[Tag], Field(max_length=20)] = Field(default_factory=list)


class Organization(QuestionMetadata):
    question_id: PublicId
    bank_id: PublicId
    archived: bool
    bank_archived: bool


class QuestionMove(ApiModel):
    bank_id: PublicId
    expected_revision: Revision


class Option(ApiModel):
    id: PublicId
    text: OptionText


class QuestionContent(ApiModel):
    question_type: QuestionType
    prompt: Prompt
    options: Annotated[list[Option], Field(min_length=2, max_length=10)]
    correct_option_id: PublicId
    default_points: Points
    feedback: Feedback

    @model_validator(mode="after")
    def valid_choices(self) -> Self:
        ids = [option.id for option in self.options]
        if len(set(ids)) != len(ids) or self.correct_option_id not in ids:
            raise ValueError("Options require unique IDs and one matching correct option")
        if self.question_type == "true_false" and (
            len(self.options) != 2 or {option.text for option in self.options} != {"True", "False"}
        ):
            raise ValueError("True/false requires exactly the True and False choices")
        return self


class QuestionCreate(QuestionContent, QuestionMetadata):
    bank_id: PublicId


class QuestionEdit(QuestionContent, QuestionMetadata):
    expected_revision: Revision


class QuestionVersion(QuestionContent):
    question_id: PublicId
    bank_id: PublicId
    version_id: PublicId
    revision: Revision
    created_at: UtcTimestamp


class QuestionSummary(ApiModel):
    question_id: PublicId
    bank_id: PublicId
    version_id: PublicId
    revision: Revision
    question_type: QuestionType
    prompt_excerpt: Annotated[str, Field(max_length=120)]
    default_points: Points
    category: Category | None = None
    tags: Annotated[list[Tag], Field(max_length=20)] = Field(default_factory=list)
    archived: bool = False
    bank_archived: bool = False


class QuestionListParams(PaginationParams):
    bank_id: PublicId | None = None
    include_archived: bool = False
    text: Annotated[str, Field(min_length=1, max_length=4000), AfterValidator(plain_text)] | None = None
    category: Category | None = None
    tag: Tag | None = None


class BankListParams(PaginationParams):
    include_archived: bool = False
