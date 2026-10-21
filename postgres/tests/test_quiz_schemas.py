from itertools import product
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from quezo_api.modules.quizzes.policies import QuizPolicy
from quezo_api.modules.quizzes.schemas import QuizComposition


@pytest.mark.parametrize("change", [
    {"title": ""}, {"title": " \n"}, {"title": "t" * 201}, {"title": "\x00"},
    {"instructions": "i" * 10001}, {"instructions": "\ud800"},
    {"questions": [{"questionId": "bad", "versionId": str(uuid4())}]},
    {"ownerId": str(uuid4())},
])
def test_composition_invalid(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        QuizComposition.model_validate({"title": "Quiz", **change})


@pytest.mark.parametrize("field,invalid", [
    ("durationSeconds", 59), ("durationSeconds", 604801), ("durationSeconds", 1.5),
    ("durationSeconds", True), ("durationSeconds", "60"), ("attemptLimit", 0),
    ("attemptLimit", 101), ("attemptLimit", False), ("randomizeQuestions", 1),
    ("randomizeOptions", "false"), ("timeZone", "Invalid/Zone"), ("timeZone", "../UTC"),
    ("scoreRelease", "immediately"), ("answerKeyRelease", None),
    ("availabilityEnd", "infinity"), ("availabilityStart", "2026-10-21T09:00:00-04:00"),
])
def test_invalid_policy(field: str, invalid: object) -> None:
    with pytest.raises(ValidationError):
        QuizPolicy.model_validate({field: invalid})


@pytest.mark.parametrize("field", ["scoreRelease", "answerKeyRelease", "explanationRelease"])
def test_end_release_requires_finite_end(field: str) -> None:
    with pytest.raises(ValidationError):
        QuizPolicy.model_validate({field: "after_availability_end"})


@pytest.mark.parametrize("modes", list(product(["never", "after_finalization", "after_availability_end"], repeat=3)))
def test_independent_release_combinations(modes: tuple[str, str, str]) -> None:
    policy = QuizPolicy.model_validate({
        **dict(zip(["scoreRelease", "answerKeyRelease", "explanationRelease"], modes, strict=True)),
        "availabilityEnd": "2026-10-21T12:00:00Z",
    })
    assert (policy.score_release, policy.answer_key_release, policy.explanation_release) == modes


def test_boundaries_defaults_and_duplicate_identity() -> None:
    assert QuizPolicy().model_dump(mode="json") == {
        "durationSeconds": None, "attemptLimit": 1, "availabilityStart": None, "availabilityEnd": None,
        "timeZone": "UTC", "randomizeQuestions": False, "randomizeOptions": False,
        "scoreRelease": "after_finalization", "answerKeyRelease": "never", "explanationRelease": "never",
    }
    for duration, attempts in [(None, None), (60, 1), (604800, 100)]:
        QuizPolicy.model_validate({"durationSeconds": duration, "attemptLimit": attempts})
    for title, instructions in [("t", ""), ("t" * 200, "i" * 10000)]:
        QuizComposition.model_validate({"title": title, "instructions": instructions})
    question = {"questionId": str(uuid4()), "versionId": str(uuid4())}
    for points in [0, 10000, None]:
        QuizComposition.model_validate({"title": "q", "questions": [{**question, "pointOverride": points}]})
    for invalid_points in [-1, 10001, 1.1, True, "3"]:
        with pytest.raises(ValidationError):
            QuizComposition.model_validate({"title": "q", "questions": [{**question, "pointOverride": invalid_points}]})
    with pytest.raises(ValidationError):
        QuizComposition.model_validate({"title": "q", "questions": [question, {**question, "versionId": str(uuid4())}]})
    with pytest.raises(ValidationError):
        QuizComposition.model_validate({"title": "q", "questions": [
            {"questionId": str(uuid4()), "versionId": str(uuid4())} for _ in range(201)
        ]})
    for end in ["2026-10-21T12:00:00Z", "2026-10-21T11:59:59Z"]:
        with pytest.raises(ValidationError):
            QuizPolicy.model_validate({"availabilityStart": "2026-10-21T12:00:00Z", "availabilityEnd": end})
