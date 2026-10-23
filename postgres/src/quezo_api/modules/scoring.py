"""Pure SCORE-01 calculation over private, delivered attempt snapshots.

D03 constructs ScoringInput from the complete frozen question sequence and the
latest accepted saved responses, under its finalization lock. It supplies the
delivered effective points (including overrides), never current bank content.
Authoring/publication own content validation, including True/False labels;
this seam validates only the scoring projection and its cross-item invariants.
These are internal value types, not HTTP DTOs or persistence models.

Construct inputs normally (or use model_validate), not with validation-bypassing
model_construct/model_copy updates. Construction rejects impossible inputs with
ValidationError; callers must surface that failure, not substitute a zero grade.
Strict UUID objects, strict integer points and immutable tuples are required.
Missing responses and explicit null both mean unanswered. Revisions, admission,
completion reason, transactions, Grade writes and disclosure remain outside
this module. In particular, expiry needs no special scoring mode.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quezo_api.schemas import NonNegativeInteger, PublicId


class _Snapshot(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


class QuestionSnapshot(_Snapshot):
    attempt_question_id: PublicId
    question_type: Literal["mcq", "true_false"]
    option_ids: Annotated[tuple[PublicId, ...], Field(min_length=2, max_length=10)]
    correct_option_id: PublicId
    points: Annotated[NonNegativeInteger, Field(le=10000)]

    @model_validator(mode="after")
    def valid_options(self) -> Self:
        if len(set(self.option_ids)) != len(self.option_ids):
            raise ValueError("Delivered option IDs must be unique within each question")
        if self.correct_option_id not in self.option_ids:
            raise ValueError("The correct option must belong to the delivered question")
        if self.question_type == "true_false" and len(self.option_ids) != 2:
            raise ValueError("True/false requires exactly two delivered options")
        return self


class SavedResponse(_Snapshot):
    attempt_question_id: PublicId
    selected_option_id: PublicId | None


class ScoringInput(_Snapshot):
    questions: Annotated[
        tuple[QuestionSnapshot, ...], Field(min_length=1, max_length=200)
    ]
    responses: Annotated[tuple[SavedResponse, ...], Field(max_length=200)] = ()

    @model_validator(mode="after")
    def consistent_snapshot(self) -> Self:
        questions = {question.attempt_question_id: question for question in self.questions}
        if len(questions) != len(self.questions):
            raise ValueError("Delivered question IDs must be unique")
        if sum(question.points for question in self.questions) == 0:
            raise ValueError("The delivered possible-points total must be positive")
        seen: set[PublicId] = set()
        for response in self.responses:
            if response.attempt_question_id in seen:
                raise ValueError("Only one saved response per delivered question is allowed")
            seen.add(response.attempt_question_id)
            question = questions.get(response.attempt_question_id)
            if question is None:
                raise ValueError("Saved responses must belong to delivered questions")
            if (
                response.selected_option_id is not None
                and response.selected_option_id not in question.option_ids
            ):
                raise ValueError("A saved selection must belong to its delivered question")
        return self


class Outcome(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNANSWERED = "unanswered"


@dataclass(frozen=True)
class ItemScore:
    attempt_question_id: PublicId
    outcome: Outcome
    earned_points: int
    possible_points: int


@dataclass(frozen=True)
class Score:
    items: tuple[ItemScore, ...]
    earned_points: int
    possible_points: int


def score(snapshot: ScoringInput) -> Score:
    """Return exact totals and outcomes in delivered question order.

    Requires a normally validated ScoringInput. All arithmetic is integer-only;
    correctness is independent of the point value, including zero-point items.
    The returned values are private finalization data, not a learner projection.
    """
    responses = {
        response.attempt_question_id: response.selected_option_id
        for response in snapshot.responses
    }
    items: list[ItemScore] = []
    for question in snapshot.questions:
        selected = responses.get(question.attempt_question_id)
        if selected is None:
            outcome = Outcome.UNANSWERED
        elif selected == question.correct_option_id:
            outcome = Outcome.CORRECT
        else:
            outcome = Outcome.INCORRECT
        items.append(ItemScore(
            attempt_question_id=question.attempt_question_id,
            outcome=outcome,
            earned_points=question.points if outcome == Outcome.CORRECT else 0,
            possible_points=question.points,
        ))
    return Score(
        items=tuple(items),
        earned_points=sum(item.earned_points for item in items),
        possible_points=sum(item.possible_points for item in items),
    )
