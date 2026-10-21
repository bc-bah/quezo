from uuid import uuid4

import pytest
from pydantic import ValidationError

from question_helpers import content
from quezo_api.modules.questions.schemas import BankWrite, QuestionContent, QuestionCreate, QuestionEdit


@pytest.mark.parametrize("kind", ["mcq", "true_false"])
@pytest.mark.parametrize("points", [0, 10000])
@pytest.mark.parametrize("maximum", [False, True])
def test_content_boundaries_preserve_plain_text(kind: str, points: int, maximum: bool) -> None:
    body = content(kind)
    body.update(prompt="p" * (4000 if maximum else 1), feedback="f" * (4000 if maximum else 0),
                defaultPoints=points)
    if kind == "mcq":
        body["options"] = [
            {"id": str(uuid4()), "text": "o" * (1000 if maximum else 1)}
            for _ in range(10 if maximum else 2)
        ]
        body["correctOptionId"] = body["options"][0]["id"]
    assert QuestionContent.model_validate(body).model_dump(mode="json") == body
    literal = "  <b>literal text</b>\n\tnot markup  "
    body["prompt"] = literal
    assert QuestionContent.model_validate(body).prompt == literal


@pytest.mark.parametrize(("field", "value"), [
    ("prompt", ""), ("prompt", " \n\t\u2003"), ("prompt", "p" * 4001),
    ("prompt", 1), ("prompt", "bad\x00text"), ("prompt", "bad\x01text"), ("prompt", "\ud800"),
    ("feedback", None), ("feedback", "f" * 4001), ("feedback", "bad\x07"),
    ("defaultPoints", -1), ("defaultPoints", 10001), ("defaultPoints", 1.5),
    ("defaultPoints", 1.0), ("defaultPoints", True), ("defaultPoints", "1"),
    ("questionType", "essay"), ("correctOptionId", str(uuid4())),
    ("correctOptionId", "bad"), ("ownerId", str(uuid4())), ("default_points", 1),
])
def test_invalid_content(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        QuestionContent.model_validate({**content(), field: value})


@pytest.mark.parametrize("case", ["one", "eleven", "duplicate", "missing-key", "blank", "long", "bad-id", "extra", "missing-text"])
def test_invalid_options(case: str) -> None:
    body = content()
    options = body["options"]
    if case == "one":
        options.pop()
    elif case == "eleven":
        options.extend({"id": str(uuid4()), "text": "x"} for _ in range(9))
    elif case == "duplicate":
        options[1]["id"] = options[0]["id"]
    elif case == "missing-key":
        del body["correctOptionId"]
    elif case == "blank":
        options[0]["text"] = " \t\n"
    elif case == "long":
        options[0]["text"] = "x" * 1001
    elif case == "bad-id":
        options[0]["id"] = "invalid"
    elif case == "extra":
        options[0]["correct"] = True
    else:
        del options[0]["text"]
    with pytest.raises(ValidationError):
        QuestionContent.model_validate(body)


@pytest.mark.parametrize("labels", [["Yes", "No"], ["True", "True"], ["true", "false"], ["True", "False", "Maybe"]])
def test_true_false_requires_exact_semantic_choices(labels: list[str]) -> None:
    body = content("true_false")
    body["options"] = [{"id": str(uuid4()), "text": label} for label in labels]
    body["correctOptionId"] = body["options"][0]["id"]
    with pytest.raises(ValidationError):
        QuestionContent.model_validate(body)


@pytest.mark.parametrize("name", ["n", "n" * 100, "  preserve  "])
def test_bank_name_boundaries(name: str) -> None:
    assert BankWrite(name=name).name == name


@pytest.mark.parametrize("name", ["", " \n\t", "n" * 101, "bad\x00"])
def test_invalid_bank_names(name: str) -> None:
    with pytest.raises(ValidationError):
        BankWrite(name=name)


def test_write_shapes_are_strict() -> None:
    body = content()
    with pytest.raises(ValidationError):
        QuestionCreate.model_validate(body)
    for revision in [0, -1, True, 1.0, "1", 2147483648]:
        with pytest.raises(ValidationError):
            QuestionEdit.model_validate({**body, "expectedRevision": revision})
    with pytest.raises(ValidationError):
        QuestionEdit.model_validate({**body, "expectedRevision": 1, "bankId": str(uuid4())})
