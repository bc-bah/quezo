from typing import Any
from uuid import uuid4


def content(kind: str = "mcq") -> dict[str, Any]:
    options = [
        {"id": str(uuid4()), "text": text}
        for text in (["First", "Second"] if kind == "mcq" else ["True", "False"])
    ]
    return {
        "questionType": kind, "prompt": "Synthetic question", "options": options,
        "correctOptionId": options[0]["id"], "defaultPoints": 3, "feedback": "Synthetic feedback",
    }
