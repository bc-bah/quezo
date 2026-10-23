from dataclasses import FrozenInstanceError
from typing import Literal
from uuid import UUID

import pytest
from pydantic import ValidationError

from quezo_api.modules.scoring import (
    ItemScore,
    Outcome,
    QuestionSnapshot,
    SavedResponse,
    Score,
    ScoringInput,
    score,
)


def question(
    index: int = 1,
    kind: Literal["mcq", "true_false"] = "mcq",
    points: int = 7,
    option_count: int = 2,
) -> QuestionSnapshot:
    options = tuple(UUID(int=index * 100 + offset) for offset in range(option_count))
    return QuestionSnapshot(
        attempt_question_id=UUID(int=index),
        question_type=kind,
        option_ids=options,
        correct_option_id=options[-1],
        points=points,
    )


def response(item: QuestionSnapshot, selected: UUID | None) -> SavedResponse:
    return SavedResponse(
        attempt_question_id=item.attempt_question_id,
        selected_option_id=selected,
    )


@pytest.mark.parametrize("kind", ["mcq", "true_false"])
@pytest.mark.parametrize("points", [0, 1, 10000])
@pytest.mark.parametrize("answer", ["correct", "wrong", "missing", "clear"])
def test_objective_outcomes(
    kind: Literal["mcq", "true_false"], points: int, answer: str,
) -> None:
    item = question(kind=kind, points=points)
    positive = question(index=2, points=1)
    selected = {
        "correct": item.correct_option_id,
        "wrong": item.option_ids[0],
        "clear": None,
    }
    responses = () if answer == "missing" else (response(item, selected[answer]),)
    result = score(ScoringInput(questions=(item, positive), responses=responses))
    expected_outcome = {
        "correct": Outcome.CORRECT,
        "wrong": Outcome.INCORRECT,
        "missing": Outcome.UNANSWERED,
        "clear": Outcome.UNANSWERED,
    }[answer]
    earned = points if answer == "correct" else 0
    assert result == Score(
        items=(
            ItemScore(item.attempt_question_id, expected_outcome, earned, points),
            ItemScore(positive.attempt_question_id, Outcome.UNANSWERED, 0, 1),
        ),
        earned_points=earned,
        possible_points=points + 1,
    )
    assert type(result.earned_points) is type(result.possible_points) is int
    assert all(type(value) is int for entry in result.items
               for value in (entry.earned_points, entry.possible_points))


def test_mixed_example_is_repeatable_and_preserves_delivered_order() -> None:
    items = (
        question(7, "mcq", 13, 10),
        question(2, "true_false", 5),
        question(9, "mcq", 17),
        question(4, "true_false", 19),
        question(1, "true_false", 0),
        question(6, "mcq", 0),
    )
    responses = (
        response(items[5], items[5].option_ids[0]),
        response(items[4], items[4].correct_option_id),
        response(items[3], None),
        response(items[1], items[1].option_ids[0]),
        response(items[0], items[0].correct_option_id),
    )
    snapshot = ScoringInput(questions=items, responses=responses)
    before = snapshot.model_dump()
    expected = Score(
        items=tuple(
            ItemScore(item.attempt_question_id, outcome, earned, item.points)
            for item, outcome, earned in zip(items, (
                Outcome.CORRECT, Outcome.INCORRECT, Outcome.UNANSWERED,
                Outcome.UNANSWERED, Outcome.CORRECT, Outcome.INCORRECT,
            ), (13, 0, 0, 0, 0, 0), strict=True)
        ),
        earned_points=13,
        possible_points=54,
    )
    for _ in range(10):
        assert score(snapshot) == expected
    assert snapshot.model_dump() == before
    assert score(ScoringInput(questions=items, responses=tuple(reversed(responses)))) == expected


@pytest.mark.parametrize(("kind", "count"), [("mcq", 2), ("mcq", 10), ("true_false", 2)])
def test_every_delivered_option_can_be_the_key_or_selection(kind: str, count: int) -> None:
    original = question(option_count=count)
    for correct in original.option_ids:
        item = QuestionSnapshot.model_validate({
            **original.model_dump(), "question_type": kind, "correct_option_id": correct,
            "option_ids": tuple(reversed(original.option_ids)),
        })
        for selected in original.option_ids:
            result = score(ScoringInput(
                questions=(item,), responses=(response(item, selected),),
            ))
            assert result == Score(
                items=(ItemScore(
                    item.attempt_question_id,
                    Outcome.CORRECT if selected == correct else Outcome.INCORRECT,
                    7 if selected == correct else 0,
                    7,
                ),),
                earned_points=7 if selected == correct else 0,
                possible_points=7,
            )


@pytest.mark.parametrize("answered", [False, True])
def test_maximum_possible_total_and_all_unanswered_expiry(answered: bool) -> None:
    items = tuple(
        question(index, "mcq" if index % 2 else "true_false", 10000)
        for index in range(1, 201)
    )
    responses = tuple(
        response(item, item.correct_option_id if answered else None)
        for item in items
    )
    result = score(ScoringInput(questions=items, responses=responses))
    assert result.possible_points == 2_000_000
    assert result.earned_points == (2_000_000 if answered else 0)
    assert len(result.items) == 200
    assert all(entry.outcome == (Outcome.CORRECT if answered else Outcome.UNANSWERED)
               for entry in result.items)
    if not answered:
        assert result == score(ScoringInput(questions=items))


def test_snapshot_is_independent_of_mutable_bank_and_saved_response_sources() -> None:
    source = question().model_dump()
    options = list(question().option_ids)
    source["option_ids"] = tuple(options)
    source["points"] = 23  # Delivered override, rather than the bank default of 7.
    saved = response(question(), question().correct_option_id).model_dump()
    snapshot = ScoringInput(
        questions=(QuestionSnapshot.model_validate(source),),
        responses=(SavedResponse.model_validate(saved),),
    )
    expected = score(snapshot)
    source.update(points=10000, correct_option_id=UUID(int=999), option_ids=())
    options.clear()
    saved["selected_option_id"] = None
    assert score(snapshot) == expected
    assert expected.earned_points == expected.possible_points == 23


def test_inputs_and_outputs_are_deeply_immutable() -> None:
    item = question()
    snapshot = ScoringInput(
        questions=(item,), responses=(response(item, item.correct_option_id),),
    )
    for target, name, value in (
        (snapshot, "questions", ()),
        (snapshot.questions[0], "points", 10000),
        (snapshot.questions[0], "option_ids", ()),
        (snapshot.responses[0], "selected_option_id", None),
    ):
        with pytest.raises(ValidationError, match="frozen"):
            setattr(target, name, value)
    result = score(snapshot)
    for output, name in ((result, "earned_points"), (result.items[0], "earned_points")):
        with pytest.raises(FrozenInstanceError):
            setattr(output, name, 0)
    assert isinstance(snapshot.questions, tuple)
    assert isinstance(snapshot.questions[0].option_ids, tuple)
    assert isinstance(snapshot.responses, tuple)
    assert isinstance(result.items, tuple)


@pytest.mark.parametrize(("field", "value"), [
    ("points", -1), ("points", 10001), ("points", 0.5), ("points", 1.0),
    ("points", True), ("points", False), ("points", "1"), ("points", None),
    ("points", float("inf")), ("points", float("nan")),
    ("attempt_question_id", "invalid"), ("attempt_question_id", str(UUID(int=1))),
    ("attempt_question_id", 1), ("correct_option_id", None),
    ("correct_option_id", str(UUID(int=101))), ("correct_option_id", UUID(int=999)),
    ("option_ids", (UUID(int=100), UUID(int=100))),
    ("option_ids", (UUID(int=100), "invalid")),
    ("option_ids", [UUID(int=100), UUID(int=101)]),
    ("question_type", "essay"), ("question_type", None), ("earned_points", 7),
])
def test_invalid_question_projection(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        QuestionSnapshot.model_validate({**question().model_dump(), field: value})


@pytest.mark.parametrize(("kind", "count"), [
    ("mcq", 0), ("mcq", 1), ("mcq", 11),
    ("true_false", 1), ("true_false", 3),
])
def test_invalid_option_counts(kind: str, count: int) -> None:
    with pytest.raises(ValidationError):
        QuestionSnapshot.model_validate({
            **question().model_dump(),
            "question_type": kind,
            "option_ids": tuple(UUID(int=100 + offset) for offset in range(count)),
        })


@pytest.mark.parametrize(("field", "value"), [
    ("attempt_question_id", "invalid"),
    ("attempt_question_id", str(UUID(int=1))),
    ("attempt_question_id", None),
    ("selected_option_id", "invalid"),
    ("selected_option_id", str(UUID(int=101))),
    ("selected_option_id", True),
    ("revision", 1),
])
def test_invalid_response_projection(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        SavedResponse.model_validate({
            **response(question(), None).model_dump(), field: value,
        })


def test_missing_selection_is_not_an_implicit_clear() -> None:
    with pytest.raises(ValidationError):
        SavedResponse.model_validate({"attempt_question_id": UUID(int=1)})


@pytest.mark.parametrize("case", [
    "empty", "too-many-questions", "zero-total", "duplicate-question",
    "duplicate-response", "conflicting-response", "foreign-question",
    "foreign-option", "wrong-question-option", "too-many-responses",
    "mutable-questions", "mutable-responses", "extra-field",
])
def test_inconsistent_input_is_rejected(case: str) -> None:
    first, second = question(), question(2)
    answered = response(first, first.correct_option_id)
    body: dict[str, object] = {"questions": (first, second), "responses": (answered,)}
    if case == "empty":
        body["questions"] = ()
    elif case == "too-many-questions":
        body["questions"] = tuple(question(index) for index in range(1, 202))
    elif case == "zero-total":
        body["questions"] = (question(points=0), question(2, points=0))
    elif case == "duplicate-question":
        body["questions"] = (first, first)
    elif case == "duplicate-response":
        body["responses"] = (answered, answered)
    elif case == "conflicting-response":
        body["responses"] = (answered, response(first, None))
    elif case == "foreign-question":
        body["responses"] = (response(question(3), None),)
    elif case == "foreign-option":
        body["responses"] = (response(first, UUID(int=999)),)
    elif case == "wrong-question-option":
        body["responses"] = (response(first, second.correct_option_id),)
    elif case == "too-many-responses":
        body["responses"] = (answered,) * 201
    elif case == "mutable-questions":
        body["questions"] = [first, second]
    elif case == "mutable-responses":
        body["responses"] = [answered]
    else:
        body["earned_points"] = 7
    with pytest.raises(ValidationError):
        ScoringInput.model_validate(body)


def test_option_ids_are_scoped_to_question_not_globally_unique() -> None:
    first = question()
    second = QuestionSnapshot.model_validate({
        **first.model_dump(), "attempt_question_id": UUID(int=2),
        "correct_option_id": first.option_ids[0],
    })
    result = score(ScoringInput(
        questions=(first, second),
        responses=(
            response(first, first.correct_option_id),
            response(second, first.correct_option_id),
        ),
    ))
    assert result.earned_points == 7
    assert result.possible_points == 14
    assert tuple(item.outcome for item in result.items) == (Outcome.CORRECT, Outcome.INCORRECT)


def test_validation_seam_rechecks_nested_instances() -> None:
    item = question()
    invalid_question = item.model_copy(update={"points": True})
    invalid_response = response(item, None).model_copy(update={"selected_option_id": 1})
    with pytest.raises(ValidationError):
        ScoringInput(questions=(invalid_question,))
    with pytest.raises(ValidationError):
        ScoringInput(questions=(item,), responses=(invalid_response,))
